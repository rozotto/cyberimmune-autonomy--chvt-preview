# ваш код
from src.control_system import BaseControlSystem
from src.config import SERVOS_QUEUE_NAME, CARGO_BAY_QUEUE_NAME
from src.navigation_system import BaseNavigationSystem
from multiprocessing import Queue
from src.communication_gateway import BaseCommunicationGateway
from src.config import CONTROL_SYSTEM_QUEUE_NAME
from src.event_types import Event


class CommunicationGateway(BaseCommunicationGateway):
    """CommunicationGateway класс для реализации логики взаимодействия
    с системой планирования заданий

    Работает в отдельном процессе, поэтому создаётся как наследник класса Process
    """
    def _send_mission_to_consumers(self):
        """ метод для отправки сообщения с маршрутным заданием в систему управления """

        # имена очередей блоков находятся в файле src/config.py
        # события нужно отправлять в соответствие с диаграммой информационных потоков
        control_q_name = CONTROL_SYSTEM_QUEUE_NAME

        # события передаются в виде экземпляров класса Event,
        # описание класса находится в файле src/event_types.py
        event = Event(source=BaseCommunicationGateway.event_source_name,
                      destination=control_q_name,
                      operation="set_mission", parameters=self._mission
                    )

        # поиск в каталоге нужной очереди (в данном случае - системы управления)
        control_q: Queue = self._queues_dir.get_queue(control_q_name)
        # отправка события в найденную очередь
        control_q.put(event)


class NavigationSystem(BaseNavigationSystem):
    """ класс навигационного блока """
    def _send_position_to_consumers(self):
        control_q_name = CONTROL_SYSTEM_QUEUE_NAME # замените на правильное название очереди
        event = Event(source=self.event_source_name,
                            destination=control_q_name,
                            operation="position_update",
                            parameters=self._position) # замените на код создания сообщения с координатами для системы управления
                     # подсказка, требуемая операция - position_update
        control_q: Queue = self._queues_dir.get_queue(control_q_name)
        control_q.put(event)


class ControlSystem(BaseControlSystem):
    """ControlSystem блок расчёта управления """

    def _send_speed_and_direction_to_consumers(self, speed, direction):
        servos_q_name = SERVOS_QUEUE_NAME
        servos_q: Queue = self._queues_dir.get_queue(servos_q_name)

        # инициализация сообщения с желаемой скоростью
        # подсказка: блок Приводы ожидает команду "set_speed" с параметром в виде скорости
        event_speed = Event(
            source=self.event_source_name,
            destination=servos_q_name,
            operation="set_speed",
            parameters=speed
        )

        # отправка сообщения с желаемым направлением
        # подсказка: блок Приводы ожидает команду "set_direction" с параметром в виде направления
        event_direction = Event(
            source=self.event_source_name,
            destination=servos_q_name,
            operation="set_direction",
            parameters=direction
        )

        servos_q.put(event_speed)
        servos_q.put(event_direction)

    def _lock_cargo(self):
        """ заблокировать грузовой отсек """
        cargo_q = self._queues_dir.get_queue(CARGO_BAY_QUEUE_NAME)
        # инициализация сообщения с командой на блокировку грузового отсека
        # подсказка: блок CargoBay ожидает команду "lock_cargo" без параметров
        event = Event(
            source=self.event_source_name,
            destination=CARGO_BAY_QUEUE_NAME,
            operation="lock_cargo",
            parameters=None
        )
        cargo_q.put(event)

    def _release_cargo(self):
        """ открыть грузовой отсек """
        cargo_q = self._queues_dir.get_queue(CARGO_BAY_QUEUE_NAME)
        # инициализация сообщения с командой на блокировку грузового отсека
        # подсказка: блок CargoBay ожидает команду "release_cargo" без параметров
        event = Event(
            source=self.event_source_name,
            destination=CARGO_BAY_QUEUE_NAME,
            operation="release_cargo",
            parameters=None
        )

        cargo_q.put(event)


afcs_present = True
car_id = "m2"

wpl_file_content =  """QGC WPL 110
0	1	0	16	0	5	0	0	59.8746946570238379	29.8298710584640503	0	1
1	0	3	16	0	5	0	0	59.8743984958028932	29.8298978805541992	20	1
2	0	3	16	0	5	0	0	59.8741157939945907	29.8296511173248291	20	1
3	0	3	16	0	5	0	0	59.8739380944847426	29.8291575908660889	20	1
4	0	3	16	0	5	0	0	59.8739004005272264	29.8288142681121826	20	1
5	0	3	16	0	5	0	0	59.8737011603275562	29.8287981748580933	20	1
6	0	3	16	0	5	0	0	59.8736876981088386	29.8291361331939697	20	1
7	0	3	16	0	5	0	0	59.8732999838707869	29.8294526338577271	20	1
8	0	3	16	0	5	0	0	59.8732192095021247	29.8293507099151611	20	1
9	0	3	16	0	5	0	0	59.873138434937232	29.8293828964233398	20	1
10	0	3	16	0	5	0	0	59.8721125808917094	29.829753041267395	20	1
11	0	3	16	0	5	0	0	59.8707985798712627	29.8302143812179565	20	1
12	0	3	16	0	5	0	0	59.8707931945143343	29.8310619592666626	20	1
13	0	3	16	0	5	0	0	59.8705508525499752	29.8311156034469604	20	1
14	0	3	16	0	5	0	0	59.8704727642074488	29.8297101259231567	20	1
15	0	3	16	0	5	0	0	59.8703650558478842	29.8288679122924805	20	1
16	0	3	16	0	5	0	0	59.8702061853806953	29.8282885551452637	20	1
17	0	3	16	0	5	0	0	59.8692421754226274	29.8292005062103271	20	1
"""

wpl_file = "module2.wpl"

with open(wpl_file, "w") as f:
    f.write(wpl_file_content)

from src.wpl_parser import WPLParser

parser = WPLParser(wpl_file)
points = parser.parse()
print(points)

from src.mission_type import GeoSpecificSpeedLimit
speed_limits = [
    GeoSpecificSpeedLimit(0, 20),
    GeoSpecificSpeedLimit(9, 60),
    GeoSpecificSpeedLimit(11, 20),
    GeoSpecificSpeedLimit(13, 60),
]

from src.mission_planner import Mission

home = points[0]
mission = Mission(home=home, waypoints=points,speed_limits=speed_limits, armed=True)

from time import sleep
from geopy import Point as GeoPoint


from src.queues_dir import QueuesDirectory
from src.servos import Servos
from src.sitl import SITL
from src.cargo_bay import CargoBay
from src.mission_planner import MissionPlanner
from src.config import LOG_ERROR, LOG_INFO
from src.mission_planner_mqtt import MissionSender
from src.sitl_mqtt import TelemetrySender
from src.system_wrapper import SystemComponentsContainer


# координата текущего положения машинки
home = GeoPoint(59.8746946570238379,	29.8298710584640503)


# каталог очередей для передачи сообщений между блоками
queues_dir = QueuesDirectory()

if afcs_present:
    mission_sender = MissionSender(
        queues_dir=queues_dir, client_id=car_id, log_level=LOG_ERROR)
    telemetry_sender = TelemetrySender(
        queues_dir=queues_dir, client_id=car_id, log_level=LOG_ERROR)

mission_planner = MissionPlanner(
    queues_dir, afcs_present=afcs_present, mission=mission)

sitl = SITL(
    queues_dir=queues_dir, position=home,
    car_id=car_id, post_telemetry=afcs_present, log_level=LOG_ERROR)


communication_gateway = CommunicationGateway(
    queues_dir=queues_dir, log_level=LOG_ERROR)
control_system = ControlSystem(queues_dir=queues_dir, log_level=LOG_INFO)

navigation_system = NavigationSystem(
    queues_dir=queues_dir, log_level=LOG_ERROR)

servos = Servos(queues_dir=queues_dir, log_level=LOG_ERROR)
cargo_bay = CargoBay(queues_dir=queues_dir, log_level=LOG_INFO)

# у нас получилось довольно много блоков, используем класс SystemComponentsContainer
# для упрощения рутинной работы с ними - таким образом мы собираем все блоки машинки в одном "кузове"
system_components = SystemComponentsContainer(
    components=[
        mission_sender,
        telemetry_sender,
        sitl,
        mission_planner,
        navigation_system,
        servos,
        cargo_bay,
        communication_gateway,
        control_system
    ] if afcs_present else [
        sitl,
        mission_planner,
        navigation_system,
        servos,
        cargo_bay,
        communication_gateway,
        control_system
    ])

system_components.start()

# ограничение поездки по времени
# параметр sleep - время в секундах,
# настройте этот параметр так, чтобы ваша машинка завершила маршрут
# в случае превышения времени выполнения ячейки на более чем 10 секунд от заданного,
# допустимо перезапустить вычислительное ядро и повторно выполнить весь блокнот, штрафные очки за это не начисляются
# при условии, что повторный запуск закончился успешно
sleep(100)

# останавливаем все компоненты
system_components.stop()

# удалим все созданные компоненты
system_components.clean()