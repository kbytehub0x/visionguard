import time
from typing import Dict, Any, List
import cv2
import numpy as np

class TemporalTracker:
    def __init__(self, track_id: str, initial_bbox: Dict[str, int], fps: float = 30.0):
        self.track_id = track_id
        self.history: List[Dict[str, Any]] = []
        self.fps = fps
        
        self.kf = cv2.KalmanFilter(4, 2)
        self.kf.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], np.float32)
        self.kf.transitionMatrix = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], np.float32)
        self.kf.processNoiseCov = np.eye(4, dtype=np.float32) * 1e-2
        self.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 1e-1

        cx = (initial_bbox["x_min"] + initial_bbox["x_max"]) / 2.0
        cy = (initial_bbox["y_min"] + initial_bbox["y_max"]) / 2.0
        self.kf.statePre = np.array([[cx], [cy], [0.0], [0.0]], np.float32)
        self.kf.statePost = np.array([[cx], [cy], [0.0], [0.0]], np.float32)

    def update(self, frame_id: int, timestamp_sec: float, bbox: Dict[str, int]) -> Dict[str, Any]:
        cx = (bbox["x_min"] + bbox["x_max"]) / 2.0
        cy = (bbox["y_min"] + bbox["y_max"]) / 2.0

        predicted = self.kf.predict()
        measurement = np.array([[cx], [cy]], np.float32)
        estimated = self.kf.correct(measurement)

        est_x, est_y = float(estimated[0][0]), float(estimated[1][0])
        vx, vy = float(estimated[2][0]), float(estimated[3][0])
        velocity = float(np.sqrt(vx**2 + vy**2))

        entry = {
            "frame_id": frame_id,
            "timestamp_sec": round(timestamp_sec, 3),
            "centroid": {"x": round(est_x, 1), "y": round(est_y, 1)},
            "velocity_px_per_sec": round(velocity * self.fps, 2)
        }
        self.history.append(entry)
        return entry

    def generate_summary(self) -> Dict[str, Any]:
        t0 = time.perf_counter()
        if not self.history:
            return {"error": "no_tracking_history"}

        duration = self.history[-1]["timestamp_sec"] - self.history[0]["timestamp_sec"]
        persistence_frames = len(self.history)
        avg_velocity = np.mean([p["velocity_px_per_sec"] for p in self.history])

        persistence_score = round(min(1.0, persistence_frames / 15.0), 2)
        confidence = round(min(0.98, 0.70 + (persistence_score * 0.25)), 2)

        return {
            "capability": "temporal_tracking",
            "track_id": self.track_id,
            "frame_window": {"start_frame": self.history[0]["frame_id"], "end_frame": self.history[-1]["frame_id"]},
            "duration_seconds": round(duration, 2),
            "persistence_frames": persistence_frames,
            "avg_velocity_px_s": round(float(avg_velocity), 2),
            "stationary": bool(avg_velocity < 15.0),
            "trajectory": [{"frame": p["frame_id"], "x": p["centroid"]["x"], "y": p["centroid"]["y"]} for p in self.history[::max(1, len(self.history) // 5)]],
            "temporal_persistence_score": persistence_score,
            "confidence": confidence,
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2)
        }
