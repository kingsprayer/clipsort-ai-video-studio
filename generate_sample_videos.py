#!/usr/bin/env python3
"""
Synthetic Sample Video Generator for ClipSort AI.
Generates multi-segment MP4 videos with distinct visual characteristics:
1. 0s - 4s: Hook (Opening window with direct text & simulated centered face)
2. 4s - 10s: A-Roll (Presenter talking head with simulated face movement)
3. 10s - 16s: B-Roll (High motion energy dynamic particles and shapes, no face)
4. 16s - 20s: CTA (Call to Action graphic card with subscribe/follow badge)
5. 20s - 24s: Endscreen (Outro farewell card template with video placeholders)
"""

import os
import math
import numpy as np
import cv2

def create_synthetic_video(output_path: str, width: int = 1280, height: int = 720, fps: int = 30):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    total_duration = 24  # 24 seconds total
    total_frames = total_duration * fps

    print(f"[Video Generator] Generating synthetic sample video: {output_path} ({total_duration}s, {total_frames} frames)...")

    for f in range(total_frames):
        t = f / fps
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # ── SEGMENT 1: 0s - 4s HOOK ──────────────────────────────────────────
        if t < 4.0:
            # Gradient background
            for y in range(height):
                frame[y, :] = [int(30 + 30 * (y / height)), int(10 + 20 * (y / height)), int(60 + 50 * (y / height))]
            
            # Simulated Presenter Face (centered, direct gaze)
            cx, cy = width // 2, height // 2 - 20
            # Face oval (skin tone)
            cv2.ellipse(frame, (cx, cy), (100, 130), 0, 0, 360, (180, 205, 235), -1)
            # Eyes
            cv2.circle(frame, (cx - 35, cy - 20), 12, (255, 255, 255), -1)
            cv2.circle(frame, (cx + 35, cy - 20), 12, (255, 255, 255), -1)
            cv2.circle(frame, (cx - 35, cy - 20), 6, (40, 40, 40), -1)
            cv2.circle(frame, (cx + 35, cy - 20), 6, (40, 40, 40), -1)
            # Mouth (speaking)
            mouth_h = int(8 + 6 * math.sin(t * 12))
            cv2.ellipse(frame, (cx, cy + 50), (25, mouth_h), 0, 0, 360, (50, 50, 180), -1)

            # Hook Headline
            cv2.putText(frame, "DID YOU KNOW THIS SECRET?", (width // 2 - 320, 100),
                        cv2.FONT_HERSHEY_DUPLEX, 1.3, (0, 255, 255), 3, cv2.LINE_AA)
            cv2.putText(frame, "[HOOK: 0s - 4s] Direct Eye Contact & Hook Cue", (width // 2 - 310, height - 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2, cv2.LINE_AA)

        # ── SEGMENT 2: 4s - 10s A-ROLL (TALKING HEAD) ────────────────────────
        elif t < 10.0:
            # Studio backdrop
            frame[:] = (35, 25, 25)
            # Soft ambient light
            cv2.circle(frame, (width // 2, height // 2), 350, (60, 45, 45), -1)

            # Presenter talking head with natural subtle sway
            sway_x = int(15 * math.sin(t * 2))
            cx, cy = width // 2 + sway_x, height // 2 - 10
            # Body shoulders
            cv2.ellipse(frame, (cx, height + 100), (240, 200), 0, 0, 360, (80, 50, 40), -1)
            # Face oval
            cv2.ellipse(frame, (cx, cy), (110, 140), 0, 0, 360, (180, 205, 235), -1)
            # Eyes
            cv2.circle(frame, (cx - 38, cy - 22), 12, (255, 255, 255), -1)
            cv2.circle(frame, (cx + 38, cy - 22), 12, (255, 255, 255), -1)
            cv2.circle(frame, (cx - 38, cy - 22), 6, (40, 40, 40), -1)
            cv2.circle(frame, (cx + 38, cy - 22), 6, (40, 40, 40), -1)
            # Speaking mouth
            mouth_h = int(10 + 8 * math.sin(t * 15))
            cv2.ellipse(frame, (cx, cy + 55), (28, mouth_h), 0, 0, 360, (50, 50, 180), -1)

            # Presenter Dialogue Banner
            cv2.putText(frame, "PRESENTER TALKING HEAD (A-ROLL)", (width // 2 - 300, 90),
                        cv2.FONT_HERSHEY_DUPLEX, 1.1, (255, 200, 50), 2, cv2.LINE_AA)
            cv2.putText(frame, f"Continuous Dialogue Speech... [{t:.1f}s]", (width // 2 - 200, height - 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2, cv2.LINE_AA)

        # ── SEGMENT 3: 10s - 16s B-ROLL (HIGH MOTION CUTAWAY) ────────────────
        elif t < 16.0:
            # Dynamic animated abstract grid with high optical motion energy
            rel_t = t - 10.0
            frame[:] = (15, 15, 20)
            
            # Moving colorful geometric objects
            num_bars = 12
            for i in range(num_bars):
                bx = int((i * 110 + rel_t * 220) % width)
                by = int(height / 2 + 180 * math.sin(rel_t * 4 + i))
                bh = int(80 + 50 * math.cos(rel_t * 3 + i))
                color = (int((i * 35) % 255), int((i * 65 + 100) % 255), int((i * 95 + 150) % 255))
                cv2.rectangle(frame, (bx, by - bh // 2), (bx + 60, by + bh // 2), color, -1)

            # Flowing lines
            for l in range(5):
                y_pos = int(120 * l + 50 * math.sin(rel_t * 5 + l))
                cv2.line(frame, (0, y_pos), (width, height - y_pos), (0, 255, 200), 3)

            cv2.putText(frame, "VISUAL B-ROLL CUTAWAY / DEMO", (width // 2 - 270, 90),
                        cv2.FONT_HERSHEY_DUPLEX, 1.1, (0, 255, 180), 2, cv2.LINE_AA)
            cv2.putText(frame, "[B-ROLL: 10s - 16s] High Motion Dynamics, No Face", (width // 2 - 290, height - 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2, cv2.LINE_AA)

        # ── SEGMENT 4: 16s - 20s CTA (CALL TO ACTION) ────────────────────────
        elif t < 20.0:
            # Vibrant gradient background
            frame[:] = (20, 40, 80)
            
            # Call to Action card box
            cv2.rectangle(frame, (width // 2 - 380, height // 2 - 160),
                          (width // 2 + 380, height // 2 + 160), (40, 70, 150), -1)
            cv2.rectangle(frame, (width // 2 - 380, height // 2 - 160),
                          (width // 2 + 380, height // 2 + 160), (0, 200, 255), 4)

            # Pulsing subscribe button
            pulse = math.sin(t * 8) * 6
            cv2.rectangle(frame, (width // 2 - 220 + int(pulse), height // 2 + 20),
                          (width // 2 + 220 - int(pulse), height // 2 + 100), (0, 50, 230), -1)

            cv2.putText(frame, "SUBSCRIBE & DROP A LIKE!", (width // 2 - 290, height // 2 - 50),
                        cv2.FONT_HERSHEY_DUPLEX, 1.3, (255, 255, 255), 3, cv2.LINE_AA)
            cv2.putText(frame, "CLICK LINK IN BIO", (width // 2 - 150, height // 2 + 70),
                        cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, "[CTA: 16s - 20s] Conversion Action Cue", (width // 2 - 220, height - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2, cv2.LINE_AA)

        # ── SEGMENT 5: 20s - 24s ENDSCREEN (OUTRO CARD TEMPLATE) ─────────────
        else:
            # Dark clean outro template
            frame[:] = (18, 18, 22)

            # Endscreen Video Placeholders
            cv2.rectangle(frame, (120, 180), (560, 480), (45, 45, 55), -1)
            cv2.rectangle(frame, (120, 180), (560, 480), (100, 100, 130), 3)
            cv2.putText(frame, "RECOMMENDED VIDEO", (180, 340), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (180, 180, 200), 2)

            # Subscribe Circle
            cv2.circle(frame, (width - 340, 330), 110, (50, 50, 65), -1)
            cv2.circle(frame, (width - 340, 330), 110, (200, 80, 120), 3)
            cv2.putText(frame, "CHANNEL", (width - 400, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(frame, "SUBSCRIBE", (width - 410, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 100, 140), 2)

            # Farewell Header
            cv2.putText(frame, "THANKS FOR WATCHING! SEE YOU NEXT TIME", (width // 2 - 420, 100),
                        cv2.FONT_HERSHEY_DUPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, "[ENDSCREEN SNAPSHOT: 20s - 24s] 4K Outro Card Template", (width // 2 - 340, height - 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (220, 100, 150), 2, cv2.LINE_AA)

        out.write(frame)

    out.release()
    print(f"[Video Generator] Successfully generated: {output_path}")
    return output_path

if __name__ == "__main__":
    demo_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "temp", "sample_creator_master.mp4")
    create_synthetic_video(demo_file)
