import unittest
import os
from unittest.mock import MagicMock, patch
from tempfile import TemporaryDirectory
from Receiver import ReceiverProcess
from src.mission_type import Mission
from src.event_types import Event, ControlEvent
from queue import Empty

# Helper to create a simple mission
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __str__(self):
        return f"Point(x={self.x}, y={self.y})"

def create_simple_mission(x1, y1, x2, y2, armed=True):
    return Mission(
        home=Point(x1, y1),
        waypoints=[Point(x2, y2)],
        speed_limits=[],
        armed=armed
    )

class TestReceiverProcess(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_queues_dir = MagicMock()
        self.receiver = ReceiverProcess(queues_dir=self.mock_queues_dir, log_level=3)
        # Ensure fresh state for unique_coordinates
        self.receiver.unique_coordinates.clear()

        # Replace queues with mocks
        self.receiver._events_q = MagicMock()
        self.receiver._control_q = MagicMock()

        # Temporary file path for telemetry output
        self.temp_dir = TemporaryDirectory()
        self.test_file = os.path.join(self.temp_dir.name, "telemetry.txt")

        # Save original write method
        self._original_write = ReceiverProcess._write_coordinates_to_file
        # Override write method to use temp file
        def _write_override():
            try:
                with open(self.test_file, 'a', encoding='utf-8') as f:
                    for coord in self.receiver.unique_coordinates:
                        f.write(f"{coord}\n")
            finally:
                self.receiver.unique_coordinates.clear()
        self.receiver._write_coordinates_to_file = _write_override

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_write_on_stop(self):
        # Add missions
        ms = [create_simple_mission(1,2,3,4), create_simple_mission(5,6,7,8)]
        for m in ms:
            self.receiver._set_mission(m)
        # Simulate stop command
        self.receiver._control_q.get_nowait.return_value = ControlEvent(operation='stop')
        self.receiver._check_control_q()

        # File should exist and contain mission coords
        self.assertTrue(os.path.exists(self.test_file))
        content = open(self.test_file).read()
        for m in ms:
            self.assertIn(str(m), content)
        # Unique coords cleared
        self.assertEqual(len(self.receiver.unique_coordinates), 0)

    def test_duplicate_mission_not_added_twice(self):
        m = create_simple_mission(1,2,3,4)
        self.receiver._set_mission(m)
        count1 = len(self.receiver.unique_coordinates)
        self.receiver._set_mission(m)
        self.assertEqual(len(self.receiver.unique_coordinates), count1)

    def test_non_stop_control_event_ignored(self):
        self.receiver._control_q.get_nowait.return_value = ControlEvent(operation='noop')
        self.receiver._write_coordinates_to_file = MagicMock()
        self.receiver._check_control_q()
        self.receiver._write_coordinates_to_file.assert_not_called()

    def test_invalid_event_in_control_q(self):
        self.receiver._control_q.get_nowait.side_effect = Empty
        self.receiver._events_q.get_nowait.return_value = "invalid_event"
        # Should not raise
        self.receiver._check_control_q()

    def test_unknown_event_operation_ignored(self):
        ev = Event(source="s", destination="d", operation="unknown", parameters=None)
        # First get_nowait returns control Empty, second returns event
        self.receiver._control_q.get_nowait.side_effect = Empty
        self.receiver._events_q.get_nowait.side_effect = [ev, Empty()]
        self.receiver._check_control_q()
        self.assertEqual(len(self.receiver.unique_coordinates), 0)

    def test_set_mission_adds_coordinate(self):
        m = create_simple_mission(10,20,30,40)
        self.receiver._set_mission(m)
        self.assertIn(str(m), self.receiver.unique_coordinates)

    def test_set_mission_raises_if_str_fails(self):
        broken = MagicMock()
        broken.__str__.side_effect = Exception("fail_str")
        with self.assertRaises(Exception):
            self.receiver._set_mission(broken)

    def test_write_coordinates_handles_file_error(self):
        # Restore original write method
        self.receiver._write_coordinates_to_file = self._original_write.__get__(self.receiver)
        # Prepare a coordinate
        self.receiver.unique_coordinates.add("coord")
        with patch("builtins.open", side_effect=IOError("fail")):
            self.receiver._log_message = MagicMock()
            # Should catch internal error and log
            self.receiver._write_coordinates_to_file()
            self.receiver._log_message.assert_called()

if __name__ == '__main__':
    unittest.main()
