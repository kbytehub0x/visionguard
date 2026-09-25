import argparse
import time
import json
import platform
import cv2
import numpy as np
import resource
import os

# ─── Fargate Pricing Constants (per vCPU-hour) ───────────────────────────────
# Source: AWS Fargate pricing page, us-east-1 region (Sep 2026)
# On-demand x86: $0.04048 / vCPU-hr  (c6i equivalent task)
# On-demand ARM (Graviton3): $0.03238 / vCPU-hr  (c7g equivalent task)
# Fargate Spot ARM (Graviton3): $0.03238 * 0.30 = $0.009714 / vCPU-hr
#   (70% spot discount — VisionGuard secondary tasks are idempotent /
#    Step Functions will auto-retry on Spot reclamation)
X86_ONDEMAND_RATE   = 0.04048    # USD/vCPU-hr — x86 Fargate on-demand
ARM_ONDEMAND_RATE   = 0.03238    # USD/vCPU-hr — Graviton Fargate on-demand
ARM_SPOT_RATE       = 0.03238 * (1 - 0.70)   # = 0.009714 USD/vCPU-hr

# ─── Adaptive Frame Decimation Constants ─────────────────────────────────────
# When the Bedrock agent triggers a secondary verification (inspect_more_frames),
# it samples at 5 FPS instead of the primary 30 FPS stream.
# Based on synthetic_pass4.json: ~20% of clips (10/50) trigger agent loops.
SECONDARY_TRIGGER_RATE = 0.20   # fraction of clips triggering secondary verify
DECIMATED_SAMPLE_FPS   = 5.0    # agent-requested sampling rate (fps)
PRIMARY_STREAM_FPS     = 30.0   # live CCTV stream fps


def get_max_memory_mb():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        return rss / (1024 * 1024)
    return rss / 1024.0


def run_pipeline(args):
    width, height = map(int, args.resolution.split("x"))
    frames = args.frames

    # ── OpenCV 5 COOL Pipeline ──────────────────────────────────────────────
    # CLAHE preprocessing + MOG2 background subtraction + Optical Flow +
    # Morphological cleanup + Contour detection
    # (Mirrors src/zone_intrusion.py execution path used in production)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    bg_subtractor = cv2.createBackgroundSubtractorMOG2(
        history=500, varThreshold=24.0
    )
    morph_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

    base_frame = np.random.randint(0, 256, (height, width), dtype=np.uint8)
    prev_frame = base_frame.copy()

    latencies = []
    start_total = time.perf_counter()

    for i in range(frames):
        t0 = time.perf_counter()
        curr_frame = np.roll(base_frame, i % width, axis=1)
        enhanced = clahe.apply(curr_frame)
        _ = cv2.calcOpticalFlowFarneback(
            prev_frame, enhanced, None, 0.5, 3, 15, 3, 5, 1.2, 0
        )
        fg_mask = bg_subtractor.apply(enhanced)
        fg_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, morph_kernel)
        _ = cv2.findContours(fg_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        latencies.append((time.perf_counter() - t0) * 1000.0)
        prev_frame = enhanced

    total_time = time.perf_counter() - start_total
    p95_latency = float(np.percentile(latencies, 95))
    fps = frames / total_time
    mem_usage = get_max_memory_mb()

    return {
        "total_time_sec": total_time,
        "p95_latency_ms": round(p95_latency, 2),
        "fps": round(fps, 2),
        "memory_mb": round(mem_usage, 2),
    }


def compute_pipeline_cost(metrics, arch):
    """
    Compute the full end-to-end pipeline cost per 1,000 primary frames.

    For x86 (no VisionGuard agentic architecture):
        - Primary pass: all frames at x86 on-demand rate, 30 FPS
        - Secondary verification: 20% of clips re-processed at 30 FPS
          on-demand (no agentic decimation available)

    For ARM Graviton (VisionGuard COOL + Agentic Decimation):
        - Primary pass: all frames at ARM on-demand rate (SLA-critical)
        - Secondary verification: Bedrock agent triggers on 20% of clips,
          samples at 5 FPS on Fargate Spot (tasks are idempotent/Step-Functions-retryable)
          → 83.3% fewer secondary frames processed, at 70% lower rate
    """
    fps = metrics["fps"]
    total_time_sec = metrics["total_time_sec"]

    # Seconds of vCPU compute consumed per 1,000 primary frames
    sec_per_1k = (total_time_sec / metrics.get("_frames", 1)) * 1000.0

    if arch in ("aarch64", "arm64"):
        # ARM primary pass: on-demand pricing (must meet SLA latency)
        primary_cost = sec_per_1k * (ARM_ONDEMAND_RATE / 3600.0)

        # ARM secondary pass: Spot pricing + Adaptive Decimation
        # Fraction of 1k primary frames needing secondary processing:
        secondary_frame_fraction = SECONDARY_TRIGGER_RATE * (
            DECIMATED_SAMPLE_FPS / PRIMARY_STREAM_FPS
        )  # = 0.20 * (5/30) = 0.0333
        secondary_sec = sec_per_1k * secondary_frame_fraction
        secondary_cost = secondary_sec * (ARM_SPOT_RATE / 3600.0)

        total_cost = primary_cost + secondary_cost

    else:  # x86 — standard pipeline, no agentic decimation
        # Primary pass: on-demand
        primary_cost = sec_per_1k * (X86_ONDEMAND_RATE / 3600.0)

        # Secondary pass: on-demand, full 30 FPS (no agent, no Spot, no decimation)
        secondary_frame_fraction = SECONDARY_TRIGGER_RATE  # 20% at full fps
        secondary_sec = sec_per_1k * secondary_frame_fraction
        secondary_cost = secondary_sec * (X86_ONDEMAND_RATE / 3600.0)

        total_cost = primary_cost + secondary_cost

    return round(total_cost, 6)


def main():
    parser = argparse.ArgumentParser(
        description="VisionGuard COOL vs x86 Full-Pipeline Benchmark\n"
                    "Measures per-frame latency, FPS, memory, and\n"
                    "end-to-end Fargate compute cost including both\n"
                    "primary (on-demand) and secondary (Spot + Adaptive\n"
                    "Decimation) pipeline stages.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--frames", type=int, default=10000,
                        help="Number of frames to process (default: 10000)")
    parser.add_argument("--resolution", type=str, default="1280x720",
                        help="Frame resolution WxH (default: 1280x720)")
    parser.add_argument("--output", type=str,
                        default="results/benchmark_results.json",
                        help="Output JSON path")
    args = parser.parse_args()

    print(f"Executing {args.frames} frames at {args.resolution}...")
    print(f"Pipeline mode: Primary on-demand + Secondary Spot+Decimated (ARM) "
          f"/ Full on-demand (x86)")

    raw = run_pipeline(args)
    raw["_frames"] = args.frames   # carry frame count for cost calc

    arch = platform.machine().lower()
    is_arm = arch in ("aarch64", "arm64")

    cost_per_1k = compute_pipeline_cost(raw, arch)

    # Clean up internal key
    del raw["_frames"]

    result = {
        "architecture": arch,
        "execution_mode": (
            "COOL_GRAVITON_ARM64_SPOT_DECIMATED" if is_arm else "x86_ONDEMAND_FULL_PIPELINE"
        ),
        "p95_latency_ms": raw["p95_latency_ms"],
        "fps": raw["fps"],
        "memory_mb": raw["memory_mb"],
        "cost_per_1k": cost_per_1k,
        "cost_model": {
            "primary_rate_usd_vcpu_hr": ARM_ONDEMAND_RATE if is_arm else X86_ONDEMAND_RATE,
            "secondary_rate_usd_vcpu_hr": ARM_SPOT_RATE if is_arm else X86_ONDEMAND_RATE,
            "secondary_trigger_rate": SECONDARY_TRIGGER_RATE,
            "secondary_sample_fps": DECIMATED_SAMPLE_FPS if is_arm else PRIMARY_STREAM_FPS,
            "spot_discount_pct": 70 if is_arm else 0,
        },
    }

    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
