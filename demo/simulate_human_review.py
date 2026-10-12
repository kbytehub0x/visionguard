#!/usr/bin/env python3
"""
VisionGuard Demo Video - Section 5: Human-in-the-Loop Gateway
Simulates the Step Functions Task Token workflow: pausing on RequestHumanReview,
emitting a secure presigned S3 evidence URL, and resuming upon supervisor approval.
"""

import time
import json

def main():
    print("=" * 70)
    print("  AWS STEP FUNCTIONS — HUMAN-IN-THE-LOOP SAFETY GATEWAY")
    print("=" * 70)
    time.sleep(0.4)

    print("\n[Severity Evaluation] Incident Severity: HIGH (Unhelmeted Worker in Restricted Zone)")
    print("[State Machine] State Transition -> 'RequestHumanReview'")
    print("[Task Token] Generated Step Functions Token: AAAAIBoZ... [WAIT_FOR_TASK_TOKEN]")
    time.sleep(0.6)

    print("\n[Supervisor Notification Dispatched via Amazon SNS / SQS]")
    notification = {
        "incident_id": "inc_8f3a9b",
        "severity": "HIGH",
        "zone_id": "ZONE_CRANE_RESTRICTED",
        "evidence_frame_url": "https://visionguard-evidence.s3.amazonaws.com/annotated/inc_8f3a9b_final.jpg?X-Amz-Expires=3600",
        "audit_trail": [
            "00:12.0 - Zone intrusion detected (conf: 0.68, unverified)",
            "00:13.1 - Bedrock tool call: inspect_more_frames",
            "00:15.8 - Temporal confirmation: worker stationary in zone for 3.8s",
            "00:15.9 - PPE violation confirmed: hard hat absent (conf: 0.94)"
        ]
    }
    print(json.dumps(notification, indent=2))
    time.sleep(0.8)

    print("\n[Supervisor Action]")
    print("  > Reviewing cropped evidence frame...")
    time.sleep(0.5)
    print("  > Supervisor Clicked: [ Acknowledge & Dispatch ]")
    time.sleep(0.5)

    print("\n[Step Functions API Call]")
    print("  aws stepfunctions send-task-success --task-token AAAAIBoZ... --output '{\"decision\": \"APPROVE\"}'")
    time.sleep(0.4)

    print("\n[State Machine] Task Token Verified! State Machine Resumed -> Status: RESOLVED_HUMAN")
    print("=" * 70)

if __name__ == "__main__":
    main()
