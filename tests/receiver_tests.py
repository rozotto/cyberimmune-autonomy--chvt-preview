import unittest
import os
from unittest.mock import MagicMock, patch, mock_open
from tempfile import TemporaryDirectory
from Receiver import ReceiverProcess
from src.mission_type import Mission
from src.event_types import Event, ControlEvent
from queue import Empty
from dataclasses import dataclass
from typing import List

# pytest tests/receiver_tests.py -v

@dataclass
class Point:
    x: float
    y: float

@dataclass 
class GeoSpecificSpeedLimit:
    max_speed: float
    area: List[Point]  # полигон, где действует ограничение

def create_simple_mission(x1, y1, x2, y2, armed=True):
    """Создает простое тестовое задание с двумя точками"""
    return Mission(
        home=Point(x1, y1),
        waypoints=[Point(x2, y2)],
        speed_limits=[GeoSpecificSpeedLimit(
            max_speed=30,
            area=[Point(x1, y1), Point(x2, y2)]
        )],
        armed=armed
    )

class TestReceiverProcess(unittest.TestCase):
    def setUp(self):
        """Настройка тестового окружения перед каждым тестом"""
        # Мокируем зависимости
        self.mock_queues_dir = MagicMock()
        
        # Инициализируем тестируемый объект
        self.receiver = ReceiverProcess(queues_dir=self.mock_queues_dir, log_level=3)
        
        # Подменяем реальные очереди на моки
        self.receiver._events_q = MagicMock()
        self.receiver._control_q = MagicMock()
        
        # Временная директория для тестовых файлов
        self.temp_dir = TemporaryDirectory()
        self.test_file_path = os.path.join(self.temp_dir.name, "telemetry.txt")
        
        # Подменяем путь к файлу в тестируемом классе
        self.receiver._write_coordinates_to_file = lambda: self._mock_write_coordinates()

    def tearDown(self):
        """Очистка после каждого теста"""
        self.temp_dir.cleanup()
    
    def _mock_write_coordinates(self):
        """Мок-реализация записи в файл для тестов"""
        with open(self.test_file_path, 'a', encoding='utf-8') as f:
            for mission in self.receiver.unique_coordinates:
                f.write(f"{mission}\n")
        self.receiver.unique_coordinates.clear()


    def test_write_on_stop(self):
        """Тест записи координат при остановке"""
        # Создаем тестовые миссии
        missions = [
            create_simple_mission(1, 2, 3, 4),
            create_simple_mission(5, 6, 7, 8),
            create_simple_mission(9, 10, 11, 12)
        ]
        
        # Добавляем миссии
        for mission in missions:
            self.receiver._set_mission(mission)
        
        # Имитируем команду остановки
        self.receiver._control_q.get_nowait.return_value = ControlEvent(operation='stop')
        self.receiver._check_control_q()
        
        # Проверяем запись в файл
        self.assertTrue(os.path.exists(self.test_file_path))
        
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            for mission in missions:
                self.assertIn(str(mission.home), content)
                for wp in mission.waypoints:
                    self.assertIn(str(wp), content)
        
        self.assertEqual(len(self.receiver.unique_coordinates), 0)

if __name__ == '__main__':
    unittest.main()