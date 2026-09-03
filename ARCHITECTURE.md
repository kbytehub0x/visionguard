**`visionguard/ARCHITECTURE.md`**
```markdown
# VisionGuard Architecture

```text
                                [ Video Input / CCTV Stream ]
                                              │
                                              ▼
                                   ┌─────────────────────┐
                                   │   Amazon S3 (Raw)   │
                                   └──────────┬──────────┘
                                              │ S3 ObjectCreated Event
                                              ▼
                                   ┌─────────────────────┐
                                   │   AWS EventBridge   │
                                   └──────────┬──────────┘
                                              │
                                              ▼
                                   ┌─────────────────────┐
                                   │ AWS Step Functions  │ ◄─────────────┐
                                   │ (State Machine Loop)│               │
                                   └──────────┬──────────┘               │
                                              │                          │
                 ┌────────────────────────────┴──────────────────────────┼───────────────┐
                 ▼                                                       ▼               │
      ┌─────────────────────┐                                 ┌─────────────────────┐   │
      │  AWS Lambda Router  │                                 │ Amazon Bedrock      │   │
      │ (Fast Triage/State) │                                 │ (Reasoning Agent)   │   │
      └──────────┬──────────┘                                 └──────────┬──────────┘   │
                 │                                                       │              │
                 │ Dispatches Compute Task                               │ Tool Calls   │
                 ▼                                                       │              │
  ┌─────────────────────────────────────────────────┐                    │              │
  │ ECS Fargate (AWS Graviton3 / ARM64)             │                    │              │
  │ ─────────────────────────────────────────────── │                    │              │
  │ OpenCV 5 + COOL (KleidiCV ARM-optimized build)  │                    │              │
  │                                                 │                    │              │
  │  [Tool 1] Motion Subtraction & Zone Intrusion   │                    │              │
  │  [Tool 2] Temporal Trajectory Tracking (Kalman) │                    │              │
  │  [Tool 3] PPE Attribute Classifier (DNN)        │                    │              │
  └────────────────────────┬────────────────────────┘                    │              │
                           │                                             │              │
                           ▼ (Structured JSON Detection Payload)         │              │
               ┌───────────────────────┐                                 │              │
               │ DynamoDB State Table  ├─────────────────────────────────┘              │
               └───────────┬───────────┘                                                │
                           │                                                            │
                           ▼                                                            │
               ┌───────────────────────┐                                                │
               │ Decision Gate Engine  │                                                │
               └───────────┬───────────┘                                                │
                           │                                                            │
           ┌───────────────┴──────────────────────────┐                                 │
           ▼                                          ▼                                 │
 [Confidence < 0.75]                        [Confidence ≥ 0.75]                         │
 (Triggers Bedrock Tool Loop)               (Definitive Classification)                 │
           │                                          │                                 │
           ├─► inspect_more_frames ───────────────────┼─────────────────────────────────┘
           ├─► crop_region                            │
           ├─► compare_temporal_consistency           ▼
           │                                ┌───────────────────┐
           │                                │ Severity Filter   │
           │                                └─────────┬─────────┘
           │                                          │
           │                     ┌────────────────────┴───────────────────┐
           │                     ▼                                        ▼
           │             [Low / Medium Risk]                      [High / Critical Risk]
           │                     │                                        │
           │                     ▼                                        ▼
           │            ┌─────────────────┐                     ┌─────────────────────┐
           └───────────►│ request_human_  │                     │ Automated Action:   │
                        │ review (SNS/UI) │                     │ SNS Alert / Webhook │
                        └─────────────────┘                     └─────────────────────┘
                                   │                                       │
                                   └──────────────────┬────────────────────┘
                                                      │
                                                      ▼
                                         ┌────────────────────────┐
                                         │ Observability Layer    │
                                         │ AWS CloudWatch & X-Ray │
                                         │ (p95, FPS, Graviton $) │
                                         └────────────────────────┘
