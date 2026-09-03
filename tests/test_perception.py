import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import cv2
from src.zone_intrusion import ZoneIntrusionDetector
from src.temporal_tracker import TemporalTracker
from src.ppe_detector import PPEDetector

class TestVisionGuardPerception(unittest.TestCase):
    def setUp(self):
        self.blank_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        self.zone_poly = [[400, 200], [600, 200], [600, 600], [400, 600]]

    def test_zone_intrusion_negative(self):
        detector = ZoneIntrusionDetector(history=2)
        _ = detector.process_frame(self.blank_frame, 1, 0.0, "zone_1", self.zone_poly)
        result = detector.process_frame(self.blank_frame, 2, 0.1, "zone_1", self.zone_poly)
        
        self.assertFalse(result["intrusion_detected"])
        self.assertEqual(result["overall_confidence"], 0.0)
        self.assertEqual(result["intruder_count"], 0)

    def test_zone_intrusion_positive(self):
        detector = ZoneIntrusionDetector(history=2)
        _ = detector.process_frame(self.blank_frame, 1, 0.0, "zone_1", self.zone_poly)
        
        motion_frame = self.blank_frame.copy()
        cv2.rectangle(motion_frame, (450, 300), (550, 500), (255, 255, 255), -1)
        
        result = detector.process_frame(motion_frame, 2, 0.1, "zone_1", self.zone_poly)
        
        self.assertTrue(result["intrusion_detected"])
        self.assertGreater(result["overall_confidence"], 0.60)

    def test_temporal_tracker_persistence(self):
        tracker = TemporalTracker(track_id="trk_1", initial_bbox={"x_min": 0, "y_min": 0, "x_max": 10, "y_max": 10}, fps=30.0)
        tracker.update(1, 0.0, {"x_min": 10, "y_min": 10, "x_max": 20, "y_max": 20})
        tracker.update(2, 0.1, {"x_min": 20, "y_min": 20, "x_max": 30, "y_max": 30})
        tracker.update(3, 0.2, {"x_min": 30, "y_min": 30, "x_max": 40, "y_max": 40})
        
        summary = tracker.generate_summary()
        self.assertGreater(summary["temporal_persistence_score"], 0.0)
        self.assertEqual(summary["persistence_frames"], 3)

    @patch("cv2.dnn.readNetFromONNX")
    def test_ppe_detector_min_formula(self, mock_read_net):
        mock_net = MagicMock()
        mock_output = np.zeros((1, 9, 8400), dtype=np.float32)
        mock_output[0, 4, 0] = 0.95
        mock_output[0, 6, 0] = 0.80
        mock_net.forward.return_value = [mock_output]
        mock_read_net.return_value = mock_net
        
        with patch("os.path.exists", return_value=True):
            detector = PPEDetector(onnx_model_path="dummy.onnx")
            
        bbox = {"x_min": 100, "y_min": 100, "x_max": 300, "y_max": 500}
        result = detector.analyze_person_roi(self.blank_frame, bbox, "ent_1", 1)
        
        self.assertFalse(result["ppe_violation"])
        self.assertEqual(result["overall_confidence"], 0.80)

if __name__ == '__main__':
    unittest.main()
