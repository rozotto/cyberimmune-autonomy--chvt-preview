from asyncio import sleep
from queue import Empty
from src.control_system import BaseControlSystem
from src.config import (
    SERVOS_QUEUE_NAME,
    CARGO_BAY_QUEUE_NAME,
    MISSION_RECEIVER_QUEUE_NAME,
    TELEMETRY_TRANSMITTER_QUEUE_NAME,
    OPERATOR_QUEUE_NAME,
    LOG_ERROR,
    LOG_INFO
)
from src.navigation_system import BaseNavigationSystem
from multiprocessing import Queue
from src.communication_gateway import BaseCommunicationGateway
from src.event_types import Event, ControlEvent

class MissionReceiver(BaseCommunicationGateway):
    """Прием и обработка маршрутных заданий"""
    event_source_name = MISSION_RECEIVER_QUEUE_NAME
    log_prefix = "[MISSION RECEIVER]"

    def _send_mission_to_consumers(self):
        event = Event(
            source=self.event_source_name,
            destination=MISSION_RECEIVER_QUEUE_NAME,  # Исправлено
            operation="set_mission",
            parameters=self._mission
        )
        queue = self._queues_dir.get_queue(MISSION_RECEIVER_QUEUE_NAME)
        queue.put(event)

    def _check_events_q(self):
        try:
            event: Event = self._events_q.get_nowait()
            if event.operation == 'set_mission':
                self._set_mission(event.parameters)
        except Empty:
            pass

class TelemetryTransmitter(BaseCommunicationGateway):
    """Сбор и передача телеметрии"""
    event_source_name = TELEMETRY_TRANSMITTER_QUEUE_NAME
    log_prefix = "[TELEMETRY]"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._telemetry = {}

    def _check_events_q(self):
        try:
            event: Event = self._events_q.get_nowait()
            if event.operation == 'telemetry_update':
                self._telemetry.update(event.parameters)
                self._send_to_operator()
        except Empty:
            pass

    def _send_to_operator(self):
        operator_q = self._queues_dir.get_queue(OPERATOR_QUEUE_NAME)
        event = Event(
            source=self.event_source_name,
            destination=OPERATOR_QUEUE_NAME,
            operation="telemetry_update",
            parameters=self._telemetry
        )
        operator_q.put(event)

    def _send_mission_to_consumers(self):
        pass

class NavigationSystem(BaseNavigationSystem):
    def _send_position_to_consumers(self):
        event = Event(
            source=self.event_source_name,
            destination=MISSION_RECEIVER_QUEUE_NAME,
            operation="position_update",
            parameters=self._position
        )
        control_q = self._queues_dir.get_queue(MISSION_RECEIVER_QUEUE_NAME)
        control_q.put(event)


class ControlSystem(BaseControlSystem):
    def _send_speed_and_direction_to_consumers(self, speed, direction):
        servos_q = self._queues_dir.get_queue(SERVOS_QUEUE_NAME)
        servos_q.put(Event(
            source=self.event_source_name,
            destination=SERVOS_QUEUE_NAME,
            operation="set_speed",
            parameters=speed
        ))
        servos_q.put(Event(
            source=self.event_source_name,
            destination=SERVOS_QUEUE_NAME,
            operation="set_direction",
            parameters=direction
        ))

    def _lock_cargo(self):
        cargo_q = self._queues_dir.get_queue(CARGO_BAY_QUEUE_NAME)
        cargo_q.put(Event(
            source=self.event_source_name,
            destination=CARGO_BAY_QUEUE_NAME,
            operation="lock_cargo",
            parameters=None
        ))

    def _release_cargo(self):
        cargo_q = self._queues_dir.get_queue(CARGO_BAY_QUEUE_NAME)
        cargo_q.put(Event(
            source=self.event_source_name,
            destination=CARGO_BAY_QUEUE_NAME,
            operation="release_cargo",
            parameters=None
        ))

# Инициализация системы
afcs_present = True
car_id = "m2"

# Создание маршрута
wpl_file = "module2.wpl"
with open(wpl_file, "w") as f:
    f.write("""QGC WPL 110
0	1	0	16	0	5	0	0	59.8746946570238379	29.8298710584640503	0	1
1	0	3	16	0	5	0	0	59.8743984958028932	29.8298978805541992	20	1
2	0	3	16	0	5	0	0	59.8741157939945907	29.8296511173248291	20	1
17	0	3	16	0	5	0	0	59.8692421754226274	29.8292005062103271	20	1
""")

from src.wpl_parser import WPLParser
parser = WPLParser(wpl_file)
points = parser.parse()

from src.mission_type import GeoSpecificSpeedLimit
speed_limits = [
    GeoSpecificSpeedLimit(0, 20),
    GeoSpecificSpeedLimit(9, 60),
    GeoSpecificSpeedLimit(11, 20),
    GeoSpecificSpeedLimit(13, 60),
]

from src.mission_planner import Mission, MissionPlanner
from src.queues_dir import QueuesDirectory

mission = Mission(
    home=points[0],
    waypoints=points,
    speed_limits=speed_limits,
    armed=True
)

# Инициализация компонентов
queues_dir = QueuesDirectory()

from src.mission_planner_mqtt import MissionSender
from src.sitl_mqtt import TelemetrySender
mission_sender = MissionSender(queues_dir, car_id, LOG_ERROR)
telemetry_sender = TelemetrySender(queues_dir, car_id, LOG_ERROR)

from src.queues_dir import QueuesDirectory
from src.servos import Servos
from src.sitl import SITL
from src.cargo_bay import CargoBay
from src.system_wrapper import SystemComponentsContainer

system_components = SystemComponentsContainer(
    components=[
        mission_sender,
        telemetry_sender,
        SITL(queues_dir, points[0], car_id, afcs_present, LOG_ERROR),
        MissionPlanner(queues_dir, afcs_present, mission),
        NavigationSystem(queues_dir, LOG_ERROR),
        Servos(queues_dir, LOG_ERROR),
        CargoBay(queues_dir, LOG_INFO),
        MissionReceiver(queues_dir, LOG_ERROR),
        TelemetryTransmitter(queues_dir, LOG_ERROR),
        ControlSystem(queues_dir, LOG_INFO)
    ] if afcs_present else [
        SITL(queues_dir, points[0], car_id, False, LOG_ERROR),
        MissionPlanner(queues_dir, False, mission),
        NavigationSystem(queues_dir, LOG_ERROR),
        Servos(queues_dir, LOG_ERROR),
        CargoBay(queues_dir, LOG_INFO),
        MissionReceiver(queues_dir, LOG_ERROR),
        TelemetryTransmitter(queues_dir, LOG_ERROR),
        ControlSystem(queues_dir, LOG_INFO)
    ]
)

system_components.start()
from time import sleep  # Исправленный импорт
sleep(100)
system_components.stop()
system_components.clean()