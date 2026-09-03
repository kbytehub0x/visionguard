import argparse
import json
import sys
import cv2
from src.zone_intrusion import ZoneIntrusionDetector
from src.temporal_tracker import TemporalTracker
from src.ppe_detector import PPEDetector

def main():
    parser = argparse.ArgumentParser(description="VisionGuard OpenCV 5 Tool Runner")
    parser.add_argument("--tool", required=True, choices=["zone_intrusion", "track_object", "ppe_detection"])
    parser.add_argument("--payload", required=True, help="JSON input string")
    args = parser.parse_args()

    data = json.loads(args.payload)

    if args.tool == "zone_intrusion":
        detector = ZoneIntrusionDetector(history=500, var_threshold=24.0)
        frame = cv2.imread(data["frame_path"])
        if frame is None:
            print(json.dumps({"error": "frame_load_failed", "path": data["frame_path"]}))
            sys.exit(1)
        result = detector.process_frame(
            frame=frame,
            frame_id=data["frame_id"],
            timestamp_sec=data["timestamp_sec"],
            zone_id=data["zone_id"],
            zone_polygon_pts=data["zone_polygon_pts"]
        )
        print(json.dumps(result))

    elif args.tool == "track_object":
        tracker = TemporalTracker(
            track_id=data["track_id"],
            initial_bbox=data["initial_bbox"]
        )
        for update in data["frame_updates"]:
            tracker.update(
                frame_id=update["frame_id"],
                timestamp_sec=update["timestamp_sec"],
                bbox=update["bbox"]
            )
        print(json.dumps(tracker.generate_summary()))

    elif args.tool == "ppe_detection":
        detector = PPEDetector(onnx_model_path=data.get("model_path", "/tmp/models/yolov8n_ppe_v1.onnx"))
        frame = cv2.imread(data["frame_path"])
        if frame is None:
            print(json.dumps({"error": "frame_load_failed", "path": data["frame_path"]}))
            sys.exit(1)
        result = detector.analyze_person_roi(
            full_frame=frame,
            person_bbox=data["bbox"],
            entity_id=data["entity_id"],
            frame_id=data["frame_id"]
        )
        print(json.dumps(result))

if __name__ == "__main__":
    main()
