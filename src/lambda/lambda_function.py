import json
import boto3
import os

bedrock = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"

TOOLS = [
    {
        "toolSpec": {
            "name": "inspect_more_frames",
            "description": "Triggered when detection confidence is below 0.75. Samples preceding and succeeding video frames to average temporal features.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "s3_video_uri": {"type": "string"},
                        "start_time_sec": {"type": "number"},
                        "end_time_sec": {"type": "number"},
                        "zone_id": {"type": "string"},
                        "sampling_rate_fps": {"type": "integer"}
                    },
                    "required": ["s3_video_uri", "start_time_sec", "end_time_sec", "zone_id"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "crop_region",
            "description": "Extracts high-resolution bounding box sub-images with histogram equalization for ambiguous PPE detection.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "s3_frame_uri": {"type": "string"},
                        "bbox": {"type": "object"},
                        "enhance_contrast": {"type": "boolean"}
                    },
                    "required": ["s3_frame_uri", "bbox"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "track_object",
            "description": "Performs geometric tracking and Kalman persistence for a bounding box across a frame window.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "track_id": {"type": "string"},
                        "initial_bbox": {"type": "object"},
                        "frame_updates": {"type": "array"}
                    },
                    "required": ["track_id", "initial_bbox", "frame_updates"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "request_human_review",
            "description": "Escalates unresolvable detections or confirmed safety breaches to a human supervisor.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "incident_id": {"type": "string"},
                        "reason": {"type": "string"}
                    },
                    "required": ["incident_id", "reason"]
                }
            }
        }
    }
]

SYSTEM_PROMPT = """You are VisionGuard AI, an agentic security orchestrator. 
Analyze the provided OpenCV JSON output. 
If the overall_confidence is < 0.75, or the situation is ambiguous, you MUST call a tool to investigate further (e.g., inspect_more_frames, crop_region, track_object).
If confidence >= 0.75 and severity is LOW or MEDIUM, call request_human_review.
If confidence >= 0.75 and severity is HIGH or CRITICAL, return tool_name='AUTO_ALERT' — the system will handle automated escalation.
You must also assess the severity of the incident based on the context: LOW, MEDIUM, HIGH, or CRITICAL."""

def lambda_handler(event, context):
    cv_result = event.get("cv_result", {})
    incident_context = event.get("incident_context", {})
    
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "text": f"Incident Context: {json.dumps(incident_context)}\nOpenCV Result: {json.dumps(cv_result)}"
                }
            ]
        }
    ]
    
    try:
        response = bedrock.converse(
            modelId=MODEL_ID,
            messages=messages,
            system=[{"text": SYSTEM_PROMPT}],
            toolConfig={"tools": TOOLS}
        )
        
        output_message = response['output']['message']
        
        tool_name = "request_human_review"
        tool_args = json.dumps({
            "incident_id": incident_context.get("incident_id", "UNKNOWN"),
            "reason": "Bedrock failed to select a tool or returned text instead of a tool call."
        })
        severity = "MEDIUM"
        
        for content_block in output_message.get('content', []):
            if 'toolUse' in content_block:
                tool_use = content_block['toolUse']
                tool_name = tool_use['name']
                tool_args = json.dumps(tool_use['input'])
                
                if tool_name == "request_human_review":
                    if cv_result.get("intrusion_detected"):
                        severity = "CRITICAL" if cv_result.get("overall_confidence", 0) > 0.90 else "HIGH"
                else:
                    confidence = cv_result.get("overall_confidence", 0)
                    severity = "MEDIUM" if confidence >= 0.60 else "LOW"
                break
                
        return {
            "tool_name": tool_name,
            "tool_args": tool_args,
            "severity": severity
        }
        
    except Exception as e:
        return {
            "tool_name": "request_human_review",
            "tool_args": json.dumps({
                "incident_id": incident_context.get("incident_id", "UNKNOWN"),
                "reason": f"Bedrock API Exception: {str(e)}"
            }),
            "severity": "CRITICAL"
        }
