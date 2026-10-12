#!/usr/bin/env bash
# VisionGuard Demo Video - Section 2 Helper Script
# Runs the OpenCV 5 MOG2 Zone Intrusion detection and outputs formatted JSON

PYTHONPATH=. python3 -m src.entrypoint \
  --tool zone_intrusion \
  --payload '{"frame_path":"benchmarks/datasets/frames/clip_000.png","frame_id":1,"timestamp_sec":0.0,"zone_id":"ZONE_CRANE_RESTRICTED","zone_polygon_pts":[[400,200],[800,200],[800,600],[400,600]]}' | python3 -m json.tool
