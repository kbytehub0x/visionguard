@patch("cv2.dnn.readNetFromONNX")
def test_ppe_detector_min_formula(self, mock_read_net):
    mock_net = MagicMock()
    
    # Shape [1, 9, 8400] — after .T becomes [8400, 9]
    # row[4:] = scores for classes: hard_hat, no_hard_hat, vest, no_vest, person
    mock_output = np.zeros((1, 9, 8400), dtype=np.float32)
    
    # Anchor 0: high confidence hard_hat (class index 0 → scores col 4)
    mock_output[0, 4, 0] = 0.95   # hard_hat present
    # Anchor 1: high confidence vest (class index 2 → scores col 6)  
    mock_output[0, 6, 1] = 0.80   # vest present
    
    # Make sure no_hard_hat and no_vest scores are zero (don't override)
    # mock_output[0, 5, :] = 0  # no_hard_hat — already zero
    # mock_output[0, 7, :] = 0  # no_vest — already zero

    mock_net.forward.return_value = [mock_output]
    mock_read_net.return_value = mock_net

    with patch("os.path.exists", return_value=True):
        detector = PPEDetector(onnx_model_path="dummy.onnx")

    bbox = {"x_min": 100, "y_min": 100, "x_max": 300, "y_max": 500}
    result = detector.analyze_person_roi(self.blank_frame, bbox, "ent_1", 1)

    # Both present → no violation
    self.assertTrue(result["attributes"]["hard_hat"]["present"])
    self.assertTrue(result["attributes"]["high_vis_vest"]["present"])
    self.assertFalse(result["ppe_violation"])
    # min(0.95, 0.80) = 0.80
    self.assertEqual(result["overall_confidence"], 0.80)
