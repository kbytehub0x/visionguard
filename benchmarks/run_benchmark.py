import argparse
import time
import json
import platform
import cv2
import numpy as np
import resource
import os

def get_max_memory_mb():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        return rss / (1024 * 1024)
    return rss / 1024.0

def run_pipeline(args):
    width, height = map(int, args.resolution.split('x'))
    frames = args.frames
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=24.0)
    morph_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    
    base_frame = np.random.randint(0, 256, (height, width), dtype=np.uint8)
    prev_frame = base_frame.copy()
    
    latencies = []
    start_total = time.perf_counter()
    
    for i in range(frames):
        t0 = time.perf_counter()
        curr_frame = np.roll(base_frame, i % width, axis=1)
        enhanced = clahe.apply(curr_frame)
        flow = cv2.calcOpticalFlowFarneback(prev_frame, enhanced, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        fg_mask = bg_subtractor.apply(enhanced)
        fg_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, morph_kernel)
        contours, _ = cv2.findContours(fg_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        latencies.append((time.perf_counter() - t0) * 1000.0)
        prev_frame = enhanced

    total_time = time.perf_counter() - start_total
    p95_latency = np.percentile(latencies, 95)
    fps = frames / total_time
    mem_usage = get_max_memory_mb()
    
    arch = platform.machine().lower()
    is_arm = arch in ["aarch64", "arm64"]
    hourly_rate = 0.03238 if is_arm else 0.04048
    cost_per_1k = (total_time / frames) * 1000 * (hourly_rate / 3600)

    return {
        "architecture": arch,
        "p95_latency_ms": round(p95_latency, 2),
        "fps": round(fps, 2),
        "memory_mb": round(mem_usage, 2),
        "cost_per_1k": round(cost_per_1k, 6)
    }

def main():
    parser = argparse.ArgumentParser(description="COOL vs x86 OpenCV Benchmark")
    parser.add_argument("--frames", type=int, default=10000)
    parser.add_argument("--resolution", type=str, default="1280x720")
    parser.add_argument("--output", type=str, default="results/benchmark_results.json")
    args = parser.parse_args()

    print(f"Executing {args.frames} frames at {args.resolution}...")
    candidate_metrics = run_pipeline(args)
    
    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(candidate_metrics, f, indent=2)

if __name__ == "__main__":
    main()
