import os
import json
import random
import cv2
import numpy as np

def generate_synthetic_dataset(output_dir="benchmarks/datasets", num_clips=50):
    frames_dir = os.path.join(output_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    
    background = np.full((720, 1280, 3), 100, dtype=np.uint8)
    bg_path = os.path.join(frames_dir, "background_base.png")
    cv2.imwrite(bg_path, background)
    
    dataset_labels = []
    zone_pts = [[400, 200], [800, 200], [800, 600], [400, 600]]
    
    category_schedule = (
        ["clear_intrusion"] * 15 +
        ["safe_zone"] * 12 +
        ["shadow_noise"] * 13 +
        ["occluded_person"] * 10
    )
    random.shuffle(category_schedule)
    
    for i, category in enumerate(category_schedule):
        clip_id = f"clip_{i:03d}"
        frame_path = os.path.join(frames_dir, f"{clip_id}.png")
        
        frame = np.full((720, 1280, 3), 100, dtype=np.uint8)
        
        expected_intrusion = False
        expected_ppe = False
        
        if category == "clear_intrusion":
            cv2.rectangle(frame, (500, 300), (600, 500), (0, 165, 255), -1)
            expected_intrusion = True
            expected_ppe = True
            
        elif category == "safe_zone":
            cv2.rectangle(frame, (100, 100), (200, 300), (0, 165, 255), -1)
            
        elif category == "shadow_noise":
            overlay = frame.copy()
            cv2.rectangle(overlay, (450, 400), (750, 500), (50, 50, 50), -1)
            cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
            
        elif category == "occluded_person":
            cv2.rectangle(frame, (360, 180), (440, 260), (0, 60, 120), -1)
            expected_intrusion = True
            expected_ppe = True

        cv2.imwrite(frame_path, frame)
        
        dataset_labels.append({
            "clip_id": clip_id,
            "frame_path": frame_path,
            "background_frame_path": bg_path,
            "category": category,
            "expected_intrusion": expected_intrusion,
            "expected_ppe_violation": expected_ppe,
            "clip_duration_seconds": 10.0,
            "zone_id": "ZONE_CRANE_RESTRICTED",
            "zone_polygon_pts": zone_pts
        })

    labels_path = os.path.join(output_dir, "labels.json")
    with open(labels_path, "w") as f:
        json.dump(dataset_labels, f, indent=2)

if __name__ == "__main__":
    generate_synthetic_dataset()
