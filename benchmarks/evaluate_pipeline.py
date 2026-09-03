import json
import argparse
import cv2
import numpy as np
import os
from src.zone_intrusion import ZoneIntrusionDetector
from src.ppe_detector import PPEDetector

def calculate_f1(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return round(precision, 3), round(recall, 3), round(f1, 3)

def evaluate_pipeline(labels_path, output_path, model_path="/tmp/models/yolov8n_ppe_v1.onnx"):
    with open(labels_path) as f:
        dataset = json.load(f)

    metrics = {
        "intrusion": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "ppe_violation": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "agent_loop_triggers": 0,
        "total_false_alert_seconds": 0.0,
        "total_footage_seconds": 0.0
    }

    ppe_available = os.path.exists(model_path)
    ppe_detector = PPEDetector(model_path) if ppe_available else None

    for clip in dataset:
        gt_intrusion = clip["expected_intrusion"]
        gt_ppe = clip["expected_ppe_violation"]
        clip_duration = clip.get("clip_duration_seconds", 10.0)
        metrics["total_footage_seconds"] += clip_duration

        detector = ZoneIntrusionDetector(history=2, var_threshold=24.0)
        bg_frame = cv2.imread(clip["background_frame_path"])
        if bg_frame is None:
            continue
        detector.process_frame(bg_frame, 0, 0.0, clip["zone_id"], clip["zone_polygon_pts"])

        frame = cv2.imread(clip["frame_path"])
        if frame is None:
            continue

        result = detector.process_frame(frame, 1, 0.1, clip["zone_id"], clip["zone_polygon_pts"])
        pred_intrusion = result["intrusion_detected"]
        pred_confidence = result["overall_confidence"]

        if pred_intrusion and pred_confidence < 0.75:
            metrics["agent_loop_triggers"] += 1

        if pred_intrusion and gt_intrusion: metrics["intrusion"]["tp"] += 1
        elif pred_intrusion and not gt_intrusion: 
            metrics["intrusion"]["fp"] += 1
            metrics["total_false_alert_seconds"] += clip_duration
        elif not pred_intrusion and gt_intrusion: metrics["intrusion"]["fn"] += 1
        else: metrics["intrusion"]["tn"] += 1

        if pred_intrusion and ppe_detector and result["entities"]:
            entity = result["entities"][0]
            ppe_result = ppe_detector.analyze_person_roi(frame, entity["bbox"], entity["entity_id"], 1)
            pred_ppe = ppe_result["ppe_violation"]

            if pred_ppe and gt_ppe: metrics["ppe_violation"]["tp"] += 1
            elif pred_ppe and not gt_ppe: metrics["ppe_violation"]["fp"] += 1
            elif not pred_ppe and gt_ppe: metrics["ppe_violation"]["fn"] += 1
            else: metrics["ppe_violation"]["tn"] += 1

    total_hours = metrics["total_footage_seconds"] / 3600.0
    false_alerts_per_hour = round(metrics["intrusion"]["fp"] / total_hours, 2) if total_hours > 0 else 0.0

    int_p, int_r, int_f1 = calculate_f1(**{k: metrics["intrusion"][k] for k in ["tp","fp","fn"]})
    ppe_p, ppe_r, ppe_f1 = calculate_f1(**{k: metrics["ppe_violation"][k] for k in ["tp","fp","fn"]})

    report = {
        "total_clips_evaluated": len(dataset),
        "agent_loops_triggered": metrics["agent_loop_triggers"],
        "false_alerts_per_hour": false_alerts_per_hour,
        "zone_intrusion_metrics": {"precision": int_p, "recall": int_r, "f1_score": int_f1, "confusion_matrix": metrics["intrusion"]},
        "ppe_violation_metrics": {"precision": ppe_p, "recall": ppe_r, "f1_score": ppe_f1, "confusion_matrix": metrics["ppe_violation"], "note": "PPE model not available — skipped" if not ppe_available else "evaluated"}
    }

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="/tmp/models/yolov8n_ppe_v1.onnx")
    args = parser.parse_args()
    evaluate_pipeline(args.labels, args.output, args.model)
