import os
import time
from typing import Dict, Any
import cv2
import numpy as np

class PPEDetector:
    def __init__(self, onnx_model_path: str = "/tmp/models/yolov8n_ppe_v1.onnx"):
        if not os.path.exists(onnx_model_path):
            raise FileNotFoundError(f"ONNX model missing at {onnx_model_path}")

        self.net = cv2.dnn.readNetFromONNX(onnx_model_path)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        self.classes = ["hard_hat", "no_hard_hat", "vest", "no_vest", "person"]

    def analyze_person_roi(
        self,
        full_frame: np.ndarray,
        person_bbox: Dict[str, int],
        entity_id: str,
        frame_id: int
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()
        
        h_img, w_img = full_frame.shape[:2]
        x1 = max(0, person_bbox["x_min"])
        y1 = max(0, person_bbox["y_min"])
        x2 = min(w_img, person_bbox["x_max"])
        y2 = min(h_img, person_bbox["y_max"])

        roi = full_frame[y1:y2, x1:x2]
        if roi.size == 0 or (y2 - y1) < 20 or (x2 - x1) < 20:
            return {"capability": "ppe_detection", "entity_id": entity_id, "error": "invalid_roi_dimensions", "overall_confidence": 0.0}

        blob = cv2.dnn.blobFromImage(roi, scalefactor=1.0 / 255.0, size=(640, 640), mean=(0, 0, 0), swapRB=True, crop=False)
        self.net.setInput(blob)
        outputs = self.net.forward()

        predictions = np.squeeze(outputs[0]).T

        hardhat_present = False
        hardhat_conf = 0.50
        vest_present = False
        vest_conf = 0.50

        # Note: In production add cv2.dnn.NMSBoxes() for multi-detection cleanup.
        # For single-ROI PPE check, highest-confidence class per attribute is sufficient.
        for row in predictions:
            scores = row[4:]
            class_id = int(np.argmax(scores))
            conf = float(scores[class_id])
            if conf < 0.40:
                continue

            class_name = self.classes[class_id] if class_id < len(self.classes) else "unknown"
            
            if class_name == "hard_hat" and conf > hardhat_conf:
                hardhat_present = True
                hardhat_conf = float(conf)
            elif class_name == "no_hard_hat" and conf > (1.0 - hardhat_conf):
                hardhat_present = False
                hardhat_conf = float(conf)

            if class_name == "vest" and conf > vest_conf:
                vest_present = True
                vest_conf = float(conf)
            elif class_name == "no_vest" and conf > (1.0 - vest_conf):
                vest_present = False
                vest_conf = float(conf)

        overall_conf = round(float(min(hardhat_conf, vest_conf)), 2)
        ppe_violation = (not hardhat_present) or (not vest_present)
        ambiguous_flag = overall_conf < 0.75

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        return {
            "capability": "ppe_detection",
            "target_entity_id": entity_id,
            "frame_id": frame_id,
            "attributes": {
                "hard_hat": {"present": hardhat_present, "confidence": round(hardhat_conf, 2)},
                "high_vis_vest": {"present": vest_present, "confidence": round(vest_conf, 2)}
            },
            "ppe_violation": ppe_violation,
            "ambiguous_flag": ambiguous_flag,
            "overall_confidence": overall_conf,
            "metrics": {"inference_latency_ms": latency_ms}
        }
