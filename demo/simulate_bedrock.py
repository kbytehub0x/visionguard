#!/usr/bin/env python3
"""
VisionGuard Demo Video - Section 3: Bedrock Agentic Reasoning
Simulates the Bedrock Claude 3.5 Sonnet invocation from src/lambda/lambda_function.py
showing the model analyzing the ambiguous OpenCV confidence (0.68) and issuing
the allowlisted tool call: 'inspect_more_frames' at 5 FPS sampling.
"""

import time
import json
import sys

def main():
    print("=" * 70)
    print("  AMAZON BEDROCK AGENTIC ORCHESTRATION — INFERENCE PIPELINE")
    print("=" * 70)
    time.sleep(0.5)

    print("\n[AWS Step Functions] State Transition -> 'BedrockToolRouter'")
    print("[Bedrock Runtime] Connecting to endpoint: bedrock-runtime.us-east-1.amazonaws.com")
    print("[Bedrock Runtime] Invoking Model: anthropic.claude-3-5-sonnet-20241022-v2:0")
    time.sleep(0.8)

    print("\n[Input Context]")
    input_payload = {
        "incident_id": "inc_8f3a9b",
        "zone_id": "ZONE_CRANE_RESTRICTED",
        "detector": "OpenCV_5_MOG2_COOL",
        "confidence": 0.68,
        "status": "AMBIGUOUS (Threshold: 0.75)"
    }
    print(json.dumps(input_payload, indent=2))
    time.sleep(0.8)

    print("\n[Claude 3.5 Sonnet Agentic Reasoning]")
    reasoning_text = (
        "Observation: Detection confidence 0.68 is below 0.75 threshold.\n"
        "Analysis: Low ambient lighting and overhead crane motion induce shadow variance.\n"
        "Decision: Calling allowlisted tool 'inspect_more_frames' over a 4-second temporal window (5 FPS decimation) to verify stationary worker persistence."
    )
    for line in reasoning_text.split("\n"):
        print(f"  > {line}")
        time.sleep(0.4)

    time.sleep(0.6)
    print("\n[Claude 3.5 Sonnet Tool Call Result]")
    tool_decision = {
        "tool_name": "inspect_more_frames",
        "tool_args": {
            "s3_video_uri": "s3://visionguard-raw-video/raw/cam_warehouse_02/2026-09-01/inc_8f3a9b.mp4",
            "start_time_sec": 12.0,
            "end_time_sec": 16.0,
            "zone_id": "ZONE_CRANE_RESTRICTED",
            "sampling_rate_fps": 5
        },
        "severity": "MEDIUM",
        "reasoning": "Intrusion confidence 0.68 is below 0.75 threshold. Requesting temporal verification across 4.0s window at 5 FPS."
    }
    print(json.dumps(tool_decision, indent=2))
    time.sleep(0.5)

    print("\n[AWS Step Functions] State Dispatched -> 'RunToolOnFargate' (Graviton3 / ARM64)")
    print("=" * 70)

if __name__ == "__main__":
    main()
