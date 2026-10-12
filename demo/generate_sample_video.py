import os
import cv2
import numpy as np

def create_warehouse_cctv_video(output_path, width=1280, height=720, fps=30, duration_sec=10):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    total_frames = fps * duration_sec
    
    # Use temporary file then convert with ffmpeg for best H.264 playback compatibility
    temp_path = "/tmp/temp_cctv.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(temp_path, fourcc, fps, (width, height))
    
    # Static elements
    zone_pts = np.array([[400, 200], [800, 200], [800, 600], [400, 600]], dtype=np.int32)
    
    # Trajectory history for Kalman trail
    trajectory_trail = []
    
    for frame_idx in range(total_frames):
        # 1. Base CCTV Background (Warehouse floor aesthetic)
        frame = np.full((height, width, 3), (38, 42, 45), dtype=np.uint8)
        
        # Grid tiles on floor
        for x in range(0, width, 80):
            cv2.line(frame, (x, 150), (int(x * 1.1), height), (50, 55, 60), 1)
        for y in range(150, height, 60):
            cv2.line(frame, (0, y), (width, y), (50, 55, 60), 1)
            
        # Overhead warehouse beams
        cv2.line(frame, (0, 80), (width, 80), (70, 75, 80), 3)
        cv2.rectangle(frame, (50, 40), (120, 150), (60, 65, 70), -1)
        cv2.rectangle(frame, (1160, 40), (1230, 150), (60, 65, 70), -1)
        cv2.putText(frame, "BAY 02 - OVERHEAD CRANE BUFFER", (460, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (140, 150, 160), 2)
        
        # 2. Draw Crane Restricted Zone
        zone_overlay = frame.copy()
        cv2.fillPoly(zone_overlay, [zone_pts], (20, 80, 120))  # Amber translucent tint
        cv2.addWeighted(zone_overlay, 0.35, frame, 0.65, 0, frame)
        
        # Dashed/Striped Zone Border
        cv2.polylines(frame, [zone_pts], isClosed=True, color=(0, 200, 255), thickness=2, lineType=cv2.LINE_AA)
        
        # Zone Label
        cv2.putText(frame, "ZONE_CRANE_RESTRICTED", (410, 230),
                    cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 220, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, "[AUTHORIZATION REQUIRED]", (410, 255),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 180, 220), 1, cv2.LINE_AA)
        
        # 3. Worker Movement & Kalman Path
        # Movement trajectory:
        # Frames 0-90 (0 - 3.0s): Walk from (220, 360) into zone at (560, 360)
        # Frames 90-300 (3.0 - 10.0s): Stationary inside zone (with subtle natural jitter)
        if frame_idx < 90:
            progress = frame_idx / 90.0
            cur_cx = int(220 + (560 - 220) * progress)
            cur_cy = int(360 + (375 - 360) * np.sin(progress * np.pi))
        else:
            # Stationary in hazard zone
            jitter_x = int(1.5 * np.sin(frame_idx * 0.2))
            jitter_y = int(1.0 * np.cos(frame_idx * 0.15))
            cur_cx = 560 + jitter_x
            cur_cy = 360 + jitter_y
            
        trajectory_trail.append((cur_cx, cur_cy))
        if len(trajectory_trail) > 100:
            trajectory_trail.pop(0)
            
        # Draw Trajectory Trail (Simulated Kalman Filter)
        for t_i in range(1, len(trajectory_trail)):
            alpha = t_i / len(trajectory_trail)
            thickness = 2 if alpha > 0.6 else 1
            color = (int(0 * alpha), int(220 * alpha), int(255 * alpha))
            cv2.line(frame, trajectory_trail[t_i - 1], trajectory_trail[t_i], color, thickness, cv2.LINE_AA)
            
        # 4. Render Worker Figure
        w, h = 64, 140
        x1, y1 = cur_cx - w // 2, cur_cy - h // 2
        x2, y2 = cur_cx + w // 2, cur_cy + h // 2
        
        # Person shadow
        cv2.ellipse(frame, (cur_cx, y2 - 4), (32, 12), 0, 0, 360, (20, 20, 20), -1)
        
        # Legs / Pants (dark navy)
        cv2.rectangle(frame, (x1 + 12, y1 + 75), (x1 + 28, y2 - 4), (60, 45, 35), -1)
        cv2.rectangle(frame, (x1 + 36, y1 + 75), (x1 + 52, y2 - 4), (60, 45, 35), -1)
        
        # High-Vis Vest Body (fluorescent neon yellow-green)
        cv2.rectangle(frame, (x1 + 10, y1 + 32), (x2 - 10, y1 + 75), (25, 215, 230), -1)
        # Silver reflective stripes on vest
        cv2.line(frame, (x1 + 10, y1 + 45), (x2 - 10, y1 + 45), (220, 220, 220), 2)
        cv2.line(frame, (x1 + 10, y1 + 60), (x2 - 10, y1 + 60), (220, 220, 220), 2)
        cv2.line(frame, (x1 + 24, y1 + 32), (x1 + 24, y1 + 75), (220, 220, 220), 2)
        cv2.line(frame, (x2 - 24, y1 + 32), (x2 - 24, y1 + 75), (220, 220, 220), 2)
        
        # Head (NO HARD HAT - dark hair clearly visible)
        cv2.circle(frame, (cur_cx, y1 + 18), 14, (30, 40, 50), -1)
        cv2.circle(frame, (cur_cx, y1 + 20), 11, (130, 160, 190), -1)  # skin tone
        
        # Centroid Marker
        cv2.drawMarker(frame, (cur_cx, cur_cy), (0, 255, 255), cv2.MARKER_CROSS, 14, 2)
        
        # 5. Dynamic Detection States & Annotations
        time_sec = frame_idx / fps
        
        if frame_idx < 45:
            # Safe monitoring outside zone
            box_color = (0, 220, 0)
            status_text = "MONITORING - SAFE (NO INTRUSION)"
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
            cv2.putText(frame, "ent_0 [CLEAR]", (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, box_color, 1)
            
        elif frame_idx < 90:
            # Entering Zone: Borderline Confidence 0.68
            box_color = (0, 165, 255)
            status_text = "MOG2 INTRUSION DETECTED | CONF: 0.68 (< 0.75 THRESHOLD)"
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
            cv2.putText(frame, "ent_360_0 | CONF: 0.68 (BORDERLINE)", (x1 - 30, y1 - 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, box_color, 2)
            cv2.putText(frame, "STATUS: SUPPRESSING PREMATURE ALERT", (x1 - 30, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1)
            
        elif frame_idx < 180:
            # Bedrock Agent Loop: Temporal tracking active
            box_color = (0, 140, 255)
            pers_sec = round((frame_idx - 90) / fps, 1)
            status_text = f"BEDROCK AGENT ACTIVE: inspect_more_frames | TRACKING PERSISTENCE: {pers_sec}s"
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
            cv2.putText(frame, "ent_360_0 | TEMPORAL VERIFYING...", (x1 - 30, y1 - 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, box_color, 2)
            cv2.putText(frame, f"PERSISTENCE: {pers_sec}s / 3.8s", (x1 - 30, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 240, 255), 1)
            
        else:
            # Verified Violation (High Severity: Missing Hard Hat, Persisted 3.8s)
            box_color = (0, 0, 240)
            status_text = "HIGH SEVERITY VIOLATION: HUMAN GATEWAY ESCALATION (TASK TOKEN)"
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 3)
            
            # Badge 1: Entity & Overall Conf
            cv2.rectangle(frame, (x1 - 40, y1 - 65), (x1 + 220, y1 - 4), (15, 15, 20), -1)
            cv2.rectangle(frame, (x1 - 40, y1 - 65), (x1 + 220, y1 - 4), box_color, 2)
            cv2.putText(frame, "VIOLATION: ent_360_0 | CONF: 0.94", (x1 - 32, y1 - 46),
                        cv2.FONT_HERSHEY_DUPLEX, 0.46, (0, 255, 255), 1)
            cv2.putText(frame, "! NO HARD HAT (conf: 0.94)", (x1 - 32, y1 - 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 80, 255), 1)
            cv2.putText(frame, "+ HIGH-VIS VEST (conf: 0.96)", (x1 - 32, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 220, 100), 1)
            
            # Callout to head
            cv2.line(frame, (cur_cx, y1 + 10), (x1 + 90, y1 - 28), (0, 0, 255), 2)
            cv2.circle(frame, (cur_cx, y1 + 10), 4, (0, 0, 255), -1)

        # 6. CCTV HUD Overlays
        # Top HUD bar
        cv2.rectangle(frame, (0, 0), (width, 42), (18, 20, 22), -1)
        cv2.line(frame, (0, 42), (width, 42), (55, 60, 65), 1)
        
        cv2.circle(frame, (25, 21), 6, (0, 0, 230), -1)  # Red recording dot
        cv2.putText(frame, "REC", (38, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (230, 230, 230), 1)
        cv2.putText(frame, "CAM_WAREHOUSE_02", (90, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 2)
        cv2.putText(frame, f"2026-09-01 14:22:{12 + int(time_sec):02d}.{int((time_sec % 1) * 100):02d}",
                    (310, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 190, 200), 1)
        cv2.putText(frame, "AWS GRAVITON3 COOL PIPELINE | OPENCV 5", (780, 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 100), 1)
        cv2.putText(frame, f"T+{time_sec:04.1f}s", (1200, 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # Bottom Status Banner
        cv2.rectangle(frame, (0, height - 38), (width, height), (18, 20, 22), -1)
        cv2.line(frame, (0, height - 38), (width, height - 38), (55, 60, 65), 1)
        cv2.putText(frame, status_text, (25, height - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (240, 240, 240), 1, cv2.LINE_AA)
        
        writer.write(frame)
        
    writer.release()
    print(f"Raw video written to {temp_path}")
    
    # Transcode with ffmpeg for universal H.264 browser & editor compatibility
    cmd = f"ffmpeg -y -i {temp_path} -c:v libx264 -pix_fmt yuv420p -r {fps} {output_path}"
    ret = os.system(cmd)
    if ret == 0:
        print(f"Successfully generated H.264 video: {output_path}")
    else:
        # Fallback if ffmpeg fails: copy raw
        os.system(f"cp {temp_path} {output_path}")
        print(f"Copied raw video to {output_path}")

if __name__ == "__main__":
    out1 = "demo/sample_videos/cam_warehouse_02.mp4"
    create_warehouse_cctv_video(out1)
