import json
import time
from typing import Dict, Any, List
import cv2
import numpy as np

class ZoneIntrusionDetector:
    def __init__(self, history: int = 500, var_threshold: float = 24.0, detect_shadows: bool = False):
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history,
            varThreshold=var_threshold,
            detectShadows=detect_shadows
        )
        self.morph_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

    def process_frame(
        self,
        frame: np.ndarray,
        frame_id: int,
        timestamp_sec: float,
        zone_id: str,
        zone_polygon_pts: List[List[int]],
        min_area_px: int = 5000
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()
        h, w = frame.shape[:2]

        fg_mask = self.bg_subtractor.apply(frame)
        fg_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self.morph_kernel)
        fg_clean = cv2.morphologyEx(fg_clean, cv2.MORPH_DILATE, self.morph_kernel)

        contours, _ = cv2.findContours(fg_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        zone_poly = np.array(zone_polygon_pts, dtype=np.int32)
        
        entities = []
        intrusion_detected = False

        for idx, cnt in enumerate(contours):
            area = cv2.contourArea(cnt)
            if area < min_area_px:
                continue

            x, y, bw, bh = cv2.boundingRect(cnt)
            cx, cy = int(x + bw / 2), int(y + bh / 2)

            inside_dist = cv2.pointPolygonTest(zone_poly, (float(cx), float(cy)), measureDist=True)
            
            mask_box = np.zeros((h, w), dtype=np.uint8)
            cv2.rectangle(mask_box, (x, y), (x + bw, y + bh), 255, -1)

            mask_zone = np.zeros((h, w), dtype=np.uint8)
            cv2.fillPoly(mask_zone, [zone_poly], 255)

            intersection = cv2.bitwise_and(mask_box, mask_zone)
            overlap_px = cv2.countNonZero(intersection)
            box_area = bw * bh
            overlap_pct = round((overlap_px / float(box_area)) * 100.0, 2) if box_area > 0 else 0.0

            is_inside = inside_dist >= 0 or overlap_pct > 30.0

            if is_inside:
                intrusion_detected = True
                confidence = round(min(0.99, 0.60 + (overlap_pct / 100.0) * 0.35 + (area / (h * w)) * 0.05), 2)
                entities.append({
                    "entity_id": f"ent_{frame_id}_{idx}",
                    "bbox": {"x_min": int(x), "y_min": int(y), "x_max": int(x + bw), "y_max": int(y + bh)},
                    "centroid": {"x": cx, "y": cy},
                    "motion_area_px": int(area),
                    "zone_overlap_pct": overlap_pct,
                    "confidence": confidence
                })

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        overall_confidence = max([e["confidence"] for e in entities], default=0.0) if intrusion_detected else 0.0

        return {
            "capability": "zone_intrusion",
            "execution_runtime": "COOL_GRAVITON_ARM64",
            "frame_id": frame_id,
            "timestamp_sec": round(timestamp_sec, 3),
            "zone_id": zone_id,
            "intrusion_detected": intrusion_detected,
            "intruder_count": len(entities),
            "entities": entities,
            "overall_confidence": overall_confidence,
            "metrics": {"opencv_latency_ms": latency_ms, "resolution": f"{w}x{h}"}
        }
