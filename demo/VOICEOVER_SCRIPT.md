# VisionGuard Demo Video Script & Voiceover Guide
**Target Total Duration**: 4:30 (Max Allowed: 5:00)  
**Tracks**: Agentic Vision & Best Use of COOL  

---

## 🎙️ The 6 Voiceover Sections (Clean Text for TTS / Recording)

### Section 1: Hook & Ingestion
* **Timestamp**: `0:00 – 0:35` (Duration: ~35s)
* **On-Screen Action**: Split screen showing AWS Step Functions Console and CCTV feed (`cam_warehouse_02`). Raw video lands in S3 bucket, EventBridge triggers `VisionGuard-Agentic-Loop`. Click "Start execution".
* **Voiceover Script**:
> "Standard video analytics tools swamp safety teams with alerts every time a shadow moves or a worker walks by. VisionGuard changes that by pairing OpenCV 5 running on AWS Graviton with Amazon Bedrock into an active agentic loop. Vision doesn't just summarize—it directs the next computational step."

---

### Section 2: Perception & Borderline Detection
* **Timestamp**: `0:35 – 1:20` (Duration: ~45s)
* **On-Screen Action**: Terminal / CloudWatch logs showing ECS Fargate (Graviton) running `zone_intrusion.py`. Step Functions advances to `EvaluateConfidence`. Fade in `Trace 1 JSON`.
* **Voiceover Script**:
> "A worker enters crane buffer zone 2. Our initial MOG2 background subtractor and polygon test detect motion, but with 0.68 confidence due to low ambient lighting and partial occlusions. Because confidence is under our 0.75 threshold, the pipeline does not fire a noisy alert."

---

### Section 3: Autonomous Agentic Reasoning
* **Timestamp**: `1:20 – 2:10` (Duration: ~50s)
* **On-Screen Action**: Step Functions visual graph transitions into `BedrockToolRouter`. Bedrock Converse API logs displayed. Fade in `Trace 2 JSON`.
* **Voiceover Script**:
> "Claude 3.5 Sonnet inspects the OpenCV payload, identifies the ambiguity, and calls the allowlisted tool inspect_more_frames over a 4-second temporal window to verify persistence and trajectory."

---

### Section 4: Verification & False Positive Suppression
* **Timestamp**: `2:10 – 3:00` (Duration: ~50s)
* **On-Screen Action**: Play `demo/sample_videos/cam_warehouse_02.mp4` full screen showing ROI zoom, Kalman trajectory trail, and YOLOv8 PPE detection. Fade in `Trace 3a` and `Trace 3b JSON`. (Brief PiP at 2:45 of a forklift shadow being suppressed).
* **Voiceover Script**:
> "The ECS task executes temporal tracking and PPE inspection on Graviton. The Kalman filter confirms the worker remained stationary in the hazard zone for 3.8 seconds. Simultaneously, the ONNX model verifies the absence of a hard hat. Meanwhile, transient false positives like forklift shadows are automatically suppressed."

---

### Section 5: Human-in-the-Loop Gateway
* **Timestamp**: `3:00 – 3:45` (Duration: ~45s)
* **On-Screen Action**: Step Functions pauses on `RequestHumanReview` (blue). Supervisor dashboard / SQS token notification pops up with presigned S3 evidence URL. Fade in `Trace 4 JSON`. Supervisor clicks 'Acknowledge & Dispatch'. State machine resumes and completes green.
* **Voiceover Script**:
> "Because this is a confirmed high-severity violation, VisionGuard invokes our human-in-the-loop safety gateway using Step Functions task tokens. The supervisor receives the cropped evidence frame, clicks 'Acknowledge & Dispatch', and the state machine resumes."

---

### Section 6: Performance Benchmark & COOL Prize Track
* **Timestamp**: `3:45 – 4:30` (Duration: ~45s)
* **On-Screen Action**: Terminal window running `python3 benchmarks/run_benchmark.py ...` then `python3 benchmarks/compare_results.py`. Delta table prints on screen. Fade in the COOL comparison table.
* **Voiceover Script**:
> "Finally, performance: running our OpenCV 5 pipeline on AWS Graviton3 with COOL and KleidiCV ARM vector extensions delivered a 38% reduction in p95 frame latency, 61.5% higher throughput, and 58.4% lower cost per thousand frames compared to a standard x86 on-demand pipeline — fully reproducible with a single benchmark command in our repository."

> **Cost Model (for on-screen graphic)**: x86 baseline = full pipeline on-demand at $0.04048/vCPU-hr (primary + secondary @ 30 FPS). ARM candidate = primary on-demand Graviton @ $0.03238/vCPU-hr + secondary via **Fargate Spot** @ $0.009714/vCPU-hr with **Adaptive 5 FPS Decimation** (83% fewer secondary frames). Net: $0.000577 → $0.000240 per 1k frames = **−58.4%**.


---

## 🗣️ ElevenLabs Phonetic Guide (Use This in ElevenLabs)

AI voice engines often mispronounce engineering acronyms. Paste these phonetic versions into ElevenLabs if the default pronunciation sounds robotic:

* **MOG2** $\rightarrow$ `Em Oh Gee Two`
* **YOLOv8** $\rightarrow$ `Yo-Lo Version Eight`
* **KleidiCV** $\rightarrow$ `Kly-dee C-V`
* **ONNX** $\rightarrow$ `On-nix`
* **p95** $\rightarrow$ `P ninety-five`
* **vCPU** $\rightarrow$ `V-C-P-U`
* **inspect_more_frames** $\rightarrow$ `inspect more frames`
