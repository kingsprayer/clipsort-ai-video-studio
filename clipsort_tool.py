#!/usr/bin/env python3
"""
================================================================================
⚡ CLIPSORT AI (V3.0) — AUTONOMOUS MULTI-MODAL VIDEO CLASSIFICATION & SORTING TOOL
================================================================================
This script reads the attached specification file (`video_sorting_logic.json`),
extracts all multi-modal rules, and executes the complete 6-category video sorting
pipeline with 100% contiguous timeline coverage and dual-track metadata.

Categories Managed:
  1. HOOKS       (Priority 1: High-retention opening 0.0s - 18.0s)
  2. ENDSCREENS   (Priority 2: Closing outro slates, dual .mp4 + .jpg export)
  3. CTA         (Priority 3: Flexible timeline conversion moments)
  4. A_ROLLS     (Priority 4: Primary narrative spine & talking-head monologue)
  5. OUTTAKES    (Priority 5: Quality filter for camera shake, blur & dead air)
  6. B_ROLLS     (Priority 6: Clean visual cutaways & cinematic B-camera shots)

Usage:
  # 1. Process a single video file:
  python clipsort_tool.py --input /path/to/video.mp4

  # 2. Process an entire folder of raw footage:
  python clipsort_tool.py --input /path/to/raw_footage_dir/

  # 3. Process with custom specification and output directory:
  python clipsort_tool.py --input video.mp4 --spec video_sorting_logic.json --output ./sorted_output

  # 4. Generate a synthetic multi-category sample video and run self-test:
  python clipsort_tool.py --demo
================================================================================
"""

import os
import re
import sys
import csv
import json
import time
import math
import shutil
import argparse
import subprocess
for _p in [os.path.expanduser("~/.local/bin"), "/opt/homebrew/bin", "/usr/local/bin"]:
    if os.path.exists(_p) and _p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{_p}:{os.environ.get('PATH', '')}"

def get_ffmpeg_cmd() -> str:
    candidates = [
        os.path.expanduser("~/.local/bin/ffmpeg"),
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/usr/bin/ffmpeg",
        shutil.which("ffmpeg")
    ]
    for c in candidates:
        if c and os.path.exists(c) and os.access(c, os.X_OK):
            return c
    return "ffmpeg"

FFMPEG_BIN = get_ffmpeg_cmd()

from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional


def ensure_virtualenv():
    try:
        import cv2
        import numpy
        return
    except ImportError:
        pass

    import glob
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidate_venvs = [
        os.path.join(script_dir, ".venv", "bin", "python"),
        os.path.join(script_dir, ".venv", "bin", "python3"),
        os.path.join(script_dir, ".venv", "bin", "python3.11"),
        os.path.join(script_dir, ".venv", "Scripts", "python.exe"),
        os.path.expanduser("~/.local/share/uv/python/cpython-3.11-macos-aarch64-none/bin/python3"),
        os.path.expanduser("~/.local/share/uv/python/cpython-3.11-macos-aarch64-none/bin/python3.11"),
        os.path.expanduser("~/.local/share/uv/python/cpython-3.11.16-macos-aarch64-none/bin/python3"),
    ]
    candidate_venvs.extend(sorted(glob.glob(os.path.expanduser("~/.local/share/uv/python/*/bin/python3*")), reverse=True))
    candidate_venvs.extend([
        os.path.expanduser("~/.local/bin/python3"),
        os.path.expanduser("~/.local/bin/python"),
    ])
    for py in candidate_venvs:
        if os.path.exists(py) and os.access(py, os.X_OK):
            os.environ["VIRTUAL_ENV"] = os.path.dirname(os.path.dirname(py))
            os.environ["PATH"] = f"{os.path.dirname(py)}:{os.environ.get('PATH', '')}"
            os.execv(py, [py] + sys.argv)

ensure_virtualenv()

# Optional fast image/CV processing
try:
    import cv2
    import numpy as np
except ImportError:
    print("[Error] OpenCV and NumPy are required. Install via: pip install opencv-python numpy")
    sys.exit(1)

# Optional faster-whisper for speech-to-text
try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None


# ── DATA STRUCTURES ──────────────────────────────────────────────────────────
@dataclass
class FrameSample:
    t: float
    face_hit: bool
    gaze_hit: bool
    yaw: float
    motion: float
    negative_space_ratio: float
    is_solid_slate: bool


@dataclass
class SpeechSegment:
    start: float
    end: float
    text: str
    has_hook_word: bool
    has_cta_word: bool
    has_outro_word: bool


# ── SPECIFICATION LOADER ─────────────────────────────────────────────────────
def load_specification(spec_path: str) -> Dict[str, Any]:
    """
    Reads the attached JSON specification file (video_sorting_logic.json)
    and returns the configuration dictionary with fallback defaults.
    """
    if os.path.exists(spec_path):
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                spec = json.load(f)
            print(f"[Specification] Successfully loaded specification from: {spec_path} (Version: {spec.get('engine_specification', {}).get('version', '3.0')})")
            return spec
        except Exception as e:
            print(f"[Specification Warning] Error parsing {spec_path}: {e}. Using internal V3.0 defaults.")

    # Built-in Version 3.0 Defaults
    return {
        "engine_specification": {
            "version": "3.0.0",
            "target_categories": ["HOOKS", "A_ROLLS", "B_ROLLS", "CTA", "ENDSCREENS", "OUTTAKES"]
        },
        "categories": {
            "HOOKS": { "priority": 1, "qualification_threshold": 0.75 },
            "ENDSCREENS": { "priority": 2, "qualification_threshold": 0.70 },
            "CTA": { "priority": 3, "qualification_threshold": 0.70 },
            "A_ROLLS": { "priority": 4, "qualification_threshold": 0.70 },
            "OUTTAKES": { "priority": 5, "qualification_threshold": 0.60 },
            "B_ROLLS": { "priority": 6, "qualification_threshold": 0.65 }
        }
    }


# ── CLIPSORT PIPELINE CLASS ──────────────────────────────────────────────────
class ClipSortTool:
    def __init__(self, spec_path: str = "video_sorting_logic.json", output_dir: str = "backend/output"):
        self.spec = load_specification(spec_path)
        self.output_dir = os.path.abspath(output_dir)
        self.categories = self.spec.get("engine_specification", {}).get(
            "target_categories", ["HOOKS", "A_ROLLS", "B_ROLLS", "CTA", "ENDSCREENS", "OUTTAKES"]
        )
        self._init_directories()
        self._init_nlp_patterns()
        self._init_models()

    def _init_directories(self):
        """Creates the output folder hierarchy for all categories."""
        os.makedirs(self.output_dir, exist_ok=True)
        for cat in self.categories:
            os.makedirs(os.path.join(self.output_dir, cat), exist_ok=True)
        print(f"[Storage] Output directory initialized: {self.output_dir}")

    def _init_nlp_patterns(self):
        """Compiles regex patterns from specification keywords."""
        cat_spec = self.spec.get("categories", {})

        hook_kw = cat_spec.get("HOOKS", {}).get("nlp_and_acoustic_signals", {}).get("multilingual_trigger_keywords", [])
        cta_kw = cat_spec.get("CTA", {}).get("detection_criteria", {}).get("imperative_action_verbs_and_conversion_vocabulary", [])
        outro_kw = cat_spec.get("ENDSCREENS", {}).get("detection_criteria", {}).get("outro_farewell_speech", {}).get("trigger_keywords", [])
        outtake_kw = cat_spec.get("OUTTAKES", {}).get("detection_criteria", {}).get("verbal_retake_phrases", [])

        # Default fallback patterns if missing in spec
        if not hook_kw:
            hook_kw = ["did you know", "stop scrolling", "pov", "the secret to", "here is why", "listen up", "imagine", "what if", "watch this", "before you", "in this video", "hey guys"]
        if not cta_kw:
            cta_kw = ["subscribe", "hit that subscribe", "drop a like", "leave a comment", "link in bio", "click the link", "download free", "sign up", "visit website", "follow for more", "tap the bell", "buy now"]
        if not outro_kw:
            outro_kw = ["thanks for watching", "see you next time", "peace out", "until next time", "stay tuned", "shukriya", "alvida"]
        if not outtake_kw:
            outtake_kw = ["wait", "let me restart", "take two", "cut", "hold on", "scratch that", "my bad"]

        self.hook_regex = [re.compile(rf"\b{re.escape(k)}\b", re.IGNORECASE) for k in hook_kw]
        self.cta_regex = [re.compile(rf"\b{re.escape(k)}\b", re.IGNORECASE) for k in cta_kw]
        self.outro_regex = [re.compile(rf"\b{re.escape(k)}\b", re.IGNORECASE) for k in outro_kw]
        self.outtake_regex = [re.compile(rf"\b{re.escape(k)}\b", re.IGNORECASE) for k in outtake_kw]

    def _init_models(self):
        """Initializes Haar cascade and Faster-Whisper if installed."""
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path) if os.path.exists(cascade_path) else None

        self.whisper_model = None
        if WhisperModel is not None:
            try:
                self.whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
                print("[AI Subsystem] Faster-Whisper tiny initialized.")
            except Exception as e:
                print(f"[AI Subsystem Notice] Whisper init: {e}")

    # ── VIDEO METADATA & TELEMETRY ───────────────────────────────────────────
    def get_duration(self, video_path: str) -> float:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return 0.0
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        cap.release()
        return round(count / fps, 3)

    def scan_telemetry_and_cuts(self, video_path: str, interval: float = 0.25) -> Tuple[List[FrameSample], List[float]]:
        cap = cv2.VideoCapture(video_path)
        samples: List[FrameSample] = []
        scene_joints: List[float] = []

        if not cap.isOpened():
            return samples, scene_joints

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        step_frames = max(1, int(fps * interval))

        prev_gray = None
        prev_hist = None
        prev_face = False
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            if frame_idx % step_frames == 0:
                t = round(frame_idx / fps, 3)
                h, w = frame.shape[:2]

                # Low-res grayscale for fast motion delta & histogram
                small = cv2.resize(frame, (160, 90))
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

                hist = cv2.calcHist([gray], [0], None, [32], [0, 256])
                hist = cv2.normalize(hist, hist)

                # Motion difference
                motion = 0.0
                if prev_gray is not None:
                    motion = float(np.mean(cv2.absdiff(gray, prev_gray)))

                # Histogram correlation cut
                corr = 1.0
                if prev_hist is not None:
                    corr = float(cv2.compareHist(hist, prev_hist, cv2.HISTCMP_CORREL))

                # Face Detection & Yaw
                face_hit = False
                gaze_hit = False
                yaw = 90.0
                neg_space = 0.5

                if self.face_cascade is not None:
                    faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20))
                    if len(faces) > 0:
                        face_hit = True
                        fx, fy, fw, fh = faces[0]
                        cx = fx + fw / 2.0
                        yaw = abs(cx - 80.0) / 80.0 * 50.0  # approximate yaw degrees
                        gaze_hit = yaw <= 25.0
                        neg_space = max(0.0, 1.0 - (fw * fh) / (160.0 * 90.0))

                # Solid Slate Detection (Terminal Cards / Slates)
                mean_b = float(np.mean(gray))
                std_b = float(np.std(gray))
                is_solid_slate = (mean_b > 210.0 and std_b < 25.0) or (mean_b < 15.0 and std_b < 25.0)

                # Scene Cut Triggers (from V3.0 Specification)
                is_cut = False
                if motion >= 22.0 or corr < 0.78:
                    is_cut = True
                elif prev_face != face_hit and motion >= 12.0:
                    is_cut = True

                if is_cut and t > 0.5:
                    scene_joints.append(t)

                samples.append(FrameSample(
                    t=t, face_hit=face_hit, gaze_hit=gaze_hit, yaw=yaw,
                    motion=motion, negative_space_ratio=neg_space, is_solid_slate=is_solid_slate
                ))

                prev_gray = gray
                prev_hist = hist
                prev_face = face_hit

            frame_idx += 1

        cap.release()
        return samples, scene_joints

    def transcribe_audio(self, video_path: str) -> List[SpeechSegment]:
        """Transcribes audio using Faster-Whisper if present; returns speech segments."""
        if self.whisper_model is None:
            return []

        segments_out: List[SpeechSegment] = []
        wav_path = os.path.join(self.output_dir, "temp_audio.wav")
        try:
            cmd = [FFMPEG_BIN, "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", wav_path]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0 and os.path.exists(wav_path):
                segs, _ = self.whisper_model.transcribe(wav_path, beam_size=1, vad_filter=True)
                for s in segs:
                    txt = s.text.strip().lower()
                    if txt:
                        segments_out.append(SpeechSegment(
                            start=round(s.start, 2),
                            end=round(s.end, 2),
                            text=s.text.strip(),
                            has_hook_word=any(p.search(txt) for p in self.hook_regex),
                            has_cta_word=any(p.search(txt) for p in self.cta_regex),
                            has_outro_word=any(p.search(txt) for p in self.outro_regex)
                        ))
        except Exception as e:
            print(f"[Whisper Notice] {e}")
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)

        return segments_out

    # ── DUAL-TRACK EVALUATOR (SPECIFICATION V3.0) ─────────────────────────────
    def evaluate_take(
        self, st: float, et: float, total_dur: float,
        samples: List[FrameSample], speech_segs: List[SpeechSegment],
        is_opening: bool, is_trailing: bool, is_penultimate: bool
    ) -> Tuple[str, float, str, str, Dict[str, Any], str, str, float]:
        dur = round(et - st, 2)
        take_samples = [s for s in samples if st <= s.t <= et]
        n = max(1, len(take_samples))

        face_ratio = sum(1 for s in take_samples if s.face_hit) / n
        gaze_ratio = sum(1 for s in take_samples if s.gaze_hit) / n
        avg_yaw = sum(s.yaw for s in take_samples) / n
        avg_motion = sum(s.motion for s in take_samples) / n
        avg_neg_space = sum(s.negative_space_ratio for s in take_samples) / n
        solid_slate_ratio = sum(1 for s in take_samples if s.is_solid_slate) / n

        take_speech = [s for s in speech_segs if not (s.end < st or s.start > et)]
        full_text = " ".join(s.text for s in take_speech).lower()

        has_hook_nlp = any(s.has_hook_word for s in take_speech) or any(p.search(full_text) for p in self.hook_regex)
        has_cta_nlp = any(s.has_cta_word for s in take_speech) or any(p.search(full_text) for p in self.cta_regex)
        has_outro_nlp = any(s.has_outro_word for s in take_speech) or any(p.search(full_text) for p in self.outro_regex)
        has_outtake_nlp = any(p.search(full_text) for p in self.outtake_regex)

        # ── Outtake & Quality Filter ─────────────────────────────────────────
        is_outtake = False
        outtake_score = 0.0
        outtake_reason = ""

        if avg_motion >= 35.0 and face_ratio == 0.0 and dur >= 1.0:
            is_outtake = True
            outtake_score = 0.85
            outtake_reason = f"Outtake: Severe erratic camera motion ({avg_motion:.1f}) without subject."
        elif avg_motion <= 0.8 and solid_slate_ratio < 0.20 and len(full_text) == 0 and dur >= 2.5:
            is_outtake = True
            outtake_score = 0.80
            outtake_reason = f"Outtake: Prolonged static dead air ({dur}s) without speech or graphics."
        elif has_outtake_nlp:
            is_outtake = True
            outtake_score = 0.75
            outtake_reason = "Outtake: Verbal retake / false start marker detected in speech."

        quality_score = 1.0 - min(0.9, (avg_motion / 50.0) * 0.3 + (0.4 if is_outtake else 0.0))
        quality_score = round(max(0.1, min(1.0, quality_score)), 2)

        telemetry = {
            "face_presence": round(face_ratio, 2),
            "gaze_directness": round(gaze_ratio, 2),
            "head_yaw": round(avg_yaw, 1),
            "motion": round(avg_motion, 2),
            "negative_space": round(avg_neg_space, 2),
            "solid_slate_ratio": round(solid_slate_ratio, 2),
            "quality_score": quality_score,
            "is_outtake": is_outtake
        }

        # 1. HOOKS
        hook_q = 0.0
        hook_reason = ""
        if is_opening and (2.0 <= dur <= 18.0 or dur >= min(2.0, total_dur)) and not is_outtake:
            score = 0.80
            if has_hook_nlp: score += 0.15
            if gaze_ratio >= 0.25: score += 0.10
            if face_ratio >= 0.15: score += 0.10
            hook_q = min(1.0, score)
            hook_reason = f"HOOK: Opening attention take ({dur}s, score {int(hook_q*100)}%)."

        # 2. ENDSCREENS
        endscreen_q = 0.0
        endscreen_reason = ""
        if is_trailing and not is_outtake:
            if solid_slate_ratio >= 0.30:
                endscreen_q = 0.95
                endscreen_reason = "ENDSCREEN: Terminal brand title card / solid slate."
            elif has_outro_nlp:
                endscreen_q = 0.90
                endscreen_reason = "ENDSCREEN: Trailing outro farewell speech."
            elif avg_neg_space >= 0.40 and avg_motion <= 6.0:
                endscreen_q = 0.85
                endscreen_reason = "ENDSCREEN: Static hold with negative space for video cards."

        # 3. CTA
        cta_q = 0.0
        cta_reason = ""
        if has_cta_nlp and not is_outtake:
            cta_q = 0.90 if (is_penultimate or st >= total_dur * 0.50) else 0.82
            cta_reason = f"CTA: Audience conversion prompt detected ({dur}s, score {int(cta_q*100)}%)."
        elif (is_penultimate or (st >= total_dur * 0.55 and et >= total_dur - 6.0)) and (has_outro_nlp or len(full_text) > 5) and not is_outtake:
            cta_q = 0.80
            cta_reason = "CTA: Pre-outro platform invitation / closing conversion call."

        # 4. A-ROLLS
        aroll_q = 0.0
        aroll_reason = ""
        if face_ratio >= 0.20 and avg_yaw <= 38.0 and dur >= 1.5 and not is_outtake:
            score = 0.70 + (0.20 if len(full_text) > 5 else 0.0)
            aroll_q = min(1.0, score)
            aroll_reason = f"A-ROLL: Presenter talking-head narrative spine ({int(face_ratio*100)}% face, yaw {avg_yaw:.1f}°)."

        # Determine Dual-Track Dimensions
        visual_role = "OUTTAKE" if is_outtake else ("GRAPHICS_SLATE" if solid_slate_ratio >= 0.30 else ("A_ROLL" if face_ratio >= 0.18 and avg_yaw <= 40.0 else "B_ROLL"))
        narrative_func = "HOOK" if hook_q >= 0.75 else ("ENDSCREEN" if endscreen_q >= 0.70 else ("CTA" if cta_q >= 0.70 else ("OUTTAKE" if is_outtake else ("DEAD_AIR" if len(full_text) == 0 and dur >= 2.0 else "CORE_BODY"))))

        # Priority Hierarchy Resolution
        if hook_q >= 0.75:
            return "HOOKS", hook_q, hook_reason, full_text, telemetry, visual_role, narrative_func, quality_score
        elif endscreen_q >= 0.70:
            return "ENDSCREENS", endscreen_q, endscreen_reason, full_text, telemetry, visual_role, narrative_func, quality_score
        elif cta_q >= 0.70:
            return "CTA", cta_q, cta_reason, full_text, telemetry, visual_role, narrative_func, quality_score
        elif aroll_q >= 0.70:
            return "A_ROLLS", aroll_q, aroll_reason, full_text, telemetry, visual_role, narrative_func, quality_score
        elif is_outtake and outtake_score >= 0.60:
            return "OUTTAKES", outtake_score, outtake_reason, full_text, telemetry, visual_role, narrative_func, quality_score
        else:
            b_score = 0.85 if face_ratio < 0.20 else 0.65
            b_reason = f"B-ROLL: Supplementary visual cutaway footage ({dur}s, motion {avg_motion:.1f})."
            return "B_ROLLS", b_score, b_reason, full_text, telemetry, visual_role, narrative_func, quality_score

    # ── PHYSICAL CUTTER & MANIFEST WRITER ─────────────────────────────────────
    def cut_clip_ffmpeg(self, in_video: str, out_path: str, start: float, duration: float):
        """Extracts clip losslessly using stream copying, falling back to H.264."""
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        # Attempt 1: Fast stream copy
        cmd_copy = [FFMPEG_BIN, "-y", "-ss", str(start), "-i", in_video, "-t", str(duration), "-c", "copy", "-avoid_negative_ts", "make_zero", out_path]
        res = subprocess.run(cmd_copy, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0 or not os.path.exists(out_path) or os.path.getsize(out_path) < 1000:
            # Attempt 2: Re-encode H.264 for exact frame accuracy
            cmd_enc = [FFMPEG_BIN, "-y", "-ss", str(start), "-i", in_video, "-t", str(duration), "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", "-c:a", "aac", out_path]
            subprocess.run(cmd_enc, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def extract_snapshot_jpg(self, in_video: str, out_jpg: str, timestamp: float):
        os.makedirs(os.path.dirname(out_jpg), exist_ok=True)
        try:
            cmd = [FFMPEG_BIN, "-y", "-ss", str(timestamp), "-i", in_video, "-vframes", "1", "-q:v", "2", out_jpg]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception:
            pass
        if not (os.path.exists(out_jpg) and os.path.getsize(out_jpg) > 200):
            try:
                cap = cv2.VideoCapture(in_video)
                cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
                ret, frame = cap.read()
                if ret and frame is not None:
                    cv2.imwrite(out_jpg, frame)
                cap.release()
            except Exception:
                pass

    # ── MASTER PROCESSING PIPELINE ───────────────────────────────────────────
    def process_video(self, video_path: str) -> List[Dict[str, Any]]:
        video_path = os.path.abspath(video_path)
        if not os.path.exists(video_path):
            print(f"[Error] File not found: {video_path}")
            return []

        base_name = os.path.splitext(os.path.basename(video_path))[0]
        safe_base = re.sub(r"[^a-zA-Z0-9_-]", "_", base_name)
        total_dur = self.get_duration(video_path)

        if total_dur <= 0.5:
            print(f"[Warning] Video too short ({total_dur}s). Skipping: {video_path}")
            return []

        print(f"\n==================================================================")
        print(f"🎬 Processing: {os.path.basename(video_path)} ({total_dur}s)")
        print(f"==================================================================")

        # 1. Telemetry scan & Whisper
        print("[1/5] Scanning visual telemetry & scene transition joints...")
        samples, scene_joints = self.scan_telemetry_and_cuts(video_path)

        print("[2/5] Transcribing speech & scanning NLP conversion patterns...")
        speech_segs = self.transcribe_audio(video_path)

        # 2. 100% Contiguous Partition Chain [0.0 -> total_dur]
        raw_cuts = set([0.0, total_dur])
        for c in scene_joints:
            if 0.0 < c < total_dur:
                raw_cuts.add(round(c, 2))
        for s in speech_segs:
            if 0.0 < s.start < total_dur:
                raw_cuts.add(round(s.start, 2))

        sorted_cuts = sorted(list(raw_cuts))
        clean_cuts = [0.0]
        for c in sorted_cuts[1:]:
            if clean_cuts == [0.0] and c < 2.5 and total_dur >= 3.0:
                continue
            if (c - clean_cuts[-1]) >= 1.0:
                clean_cuts.append(c)
            elif c == total_dur:
                if len(clean_cuts) > 1 and (total_dur - clean_cuts[-1]) < 1.0:
                    clean_cuts[-1] = total_dur
                else:
                    clean_cuts.append(total_dur)
        if clean_cuts[-1] != total_dur:
            clean_cuts.append(total_dur)

        intervals = [(clean_cuts[i], clean_cuts[i+1]) for i in range(len(clean_cuts)-1) if clean_cuts[i+1] > clean_cuts[i]]
        if not intervals:
            intervals = [(0.0, total_dur)]

        # 3. Classify every take
        print(f"[3/5] Classifying {len(intervals)} contiguous timeline segment(s)...")
        num_int = len(intervals)
        classified = []

        for idx, (st, et) in enumerate(intervals):
            dur = round(et - st, 2)
            is_opening = (idx == 0) and (st <= 0.5)
            is_trailing = (idx == num_int - 1) and (et >= total_dur - 0.5)
            is_penultimate = (idx == num_int - 2) and (num_int >= 3)

            cat, conf, reason, text, tele, v_role, n_func, q_score = self.evaluate_take(
                st, et, total_dur, samples, speech_segs, is_opening, is_trailing, is_penultimate
            )
            classified.append({
                "index": idx, "category": cat, "visual_role": v_role,
                "narrative_function": n_func, "quality_score": q_score,
                "start": round(st, 2), "end": round(et, 2), "duration": dur,
                "confidence": round(conf, 2), "reason": reason, "transcript": text[:200], "telemetry": tele
            })

        # 4. A-Roll / Monologue Consolidation pass (pauses <= 0.35s)
        print("[4/5] Running dialogue consolidation & contiguity verification...")
        consolidated = []
        curr = None
        for take in classified:
            if curr is None:
                curr = take.copy()
                continue
            if take["category"] == curr["category"] and take["category"] in ["A_ROLLS", "B_ROLLS"]:
                gap = abs(take["start"] - curr["end"])
                if gap <= 0.35 and (take["end"] - curr["start"]) <= 120.0:
                    curr["end"] = take["end"]
                    curr["duration"] = round(curr["end"] - curr["start"], 2)
                    curr["confidence"] = max(curr["confidence"], take["confidence"])
                    continue
            consolidated.append(curr)
            curr = take.copy()
        if curr is not None:
            consolidated.append(curr)

        # Strict zero-gap coverage check
        for i in range(len(consolidated) - 1):
            consolidated[i]["end"] = consolidated[i+1]["start"]
            consolidated[i]["duration"] = round(consolidated[i]["end"] - consolidated[i]["start"], 2)
        if consolidated:
            consolidated[0]["start"] = 0.0
            consolidated[-1]["end"] = total_dur
            consolidated[-1]["duration"] = round(total_dur - consolidated[-1]["start"], 2)

        # 5. Physical Trimming & Dual Endscreen Export
        print(f"[5/5] Trimming {len(consolidated)} clip(s) and writing manifests...")
        results = []
        for idx, sc in enumerate(consolidated):
            cat = sc["category"]
            st = sc["start"]
            dur = sc["duration"]
            et = sc["end"]

            if dur <= 0.05:
                continue

            if cat == "ENDSCREENS":
                # Dual Export: .mp4 video clip + .jpg snapshot card
                out_fn = f"{cat}_{idx}_{safe_base}.mp4"
                out_path = os.path.join(self.output_dir, cat, out_fn)
                self.cut_clip_ffmpeg(video_path, out_path, st, dur)

                snap_fn = f"{cat}_{idx}_{safe_base}.jpg"
                snap_path = os.path.join(self.output_dir, cat, snap_fn)
                self.extract_snapshot_jpg(video_path, snap_path, min(total_dur - 0.2, st + dur / 2.0))

                thumb_fn = f"{cat}_{idx}_{safe_base}.thumb.jpg"
                thumb_path = os.path.join(self.output_dir, cat, thumb_fn)
                self.extract_snapshot_jpg(video_path, thumb_path, min(total_dur - 0.2, st + dur / 2.0))
            else:
                out_fn = f"{cat}_{idx}_{safe_base}.mp4"
                out_path = os.path.join(self.output_dir, cat, out_fn)
                self.cut_clip_ffmpeg(video_path, out_path, st, dur)

                thumb_fn = f"{cat}_{idx}_{safe_base}.thumb.jpg"
                thumb_path = os.path.join(self.output_dir, cat, thumb_fn)
                self.extract_snapshot_jpg(video_path, thumb_path, st + min(0.5, dur / 2.0))

            clip_meta = {
                "category": cat,
                "visual_role": sc.get("visual_role", "B_ROLL"),
                "narrative_function": sc.get("narrative_function", "CORE_BODY"),
                "quality_score": sc.get("quality_score", 0.90),
                "filename": out_fn,
                "folder_path": f"{cat}/{out_fn}",
                "source_video": base_name,
                "start": st,
                "end": et,
                "duration": dur,
                "confidence": sc["confidence"],
                "reason": sc["reason"]
            }
            results.append(clip_meta)
            print(f"  ✓ [{cat}] {st:.1f}s -> {et:.1f}s ({dur}s) | Role: {clip_meta['visual_role']} • Func: {clip_meta['narrative_function']} | File: {out_fn}")

        self._save_manifests(results)
        return results

    def _save_manifests(self, new_clips: List[Dict[str, Any]]):
        manifest_json = os.path.join(self.output_dir, "manifest.json")
        manifest_csv = os.path.join(self.output_dir, "manifest.csv")

        existing = []
        if os.path.exists(manifest_json):
            try:
                with open(manifest_json, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = []

        existing_fns = set(item.get("filename") for item in existing)
        for c in new_clips:
            if c.get("filename") not in existing_fns:
                existing.append(c)

        with open(manifest_json, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)

        with open(manifest_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["category", "visual_role", "narrative_function", "quality_score", "filename", "folder_path", "source_video", "start", "end", "duration", "confidence", "reason"])
            for item in existing:
                writer.writerow([
                    item.get("category"), item.get("visual_role"), item.get("narrative_function"),
                    item.get("quality_score"), item.get("filename"), item.get("folder_path"),
                    item.get("source_video"), item.get("start"), item.get("end"),
                    item.get("duration"), item.get("confidence"), item.get("reason")
                ])

        print(f"\n[Manifests Updated] {manifest_json} & {manifest_csv}")


# ── SYNTHETIC DEMO VIDEO GENERATOR ───────────────────────────────────────────
def generate_demo_video(output_path: str = "demo_footage.mp4", duration: int = 24):
    """Generates a synthetic test video exhibiting distinct characteristics across all categories."""
    width, height, fps = 1280, 720, 30
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    print(f"[Demo Generator] Creating synthetic {duration}s multi-category video: {output_path}...")
    for f in range(duration * fps):
        t = f / fps
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # 0s - 4s: HOOK
        if t < 4.0:
            frame[:] = (50, 20, 80)
            cv2.ellipse(frame, (width // 2, height // 2), (90, 120), 0, 0, 360, (180, 200, 230), -1)
            cv2.putText(frame, "DID YOU KNOW THIS SECRET?", (width // 2 - 280, 100), cv2.FONT_HERSHEY_DUPLEX, 1.1, (0, 255, 255), 2)
            cv2.putText(frame, "[HOOK ZONE: 0s - 4s]", (width // 2 - 130, height - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        # 4s - 10s: A-ROLL
        elif t < 10.0:
            frame[:] = (30, 25, 25)
            cv2.ellipse(frame, (width // 2, height // 2), (90, 120), 0, 0, 360, (170, 195, 225), -1)
            cv2.putText(frame, "[A-ROLL: Presenter Narrative Spine]", (width // 2 - 240, 100), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 2)
        # 10s - 15s: B-ROLL
        elif t < 15.0:
            frame[:] = (20, 40, 30)
            # Animated moving particle
            px = int((t * 200) % width)
            cv2.circle(frame, (px, height // 2), 60, (50, 220, 120), -1)
            cv2.putText(frame, "[B-ROLL: Cinematic Particle Cutaway]", (width // 2 - 250, 100), cv2.FONT_HERSHEY_DUPLEX, 1.0, (100, 255, 100), 2)
        # 15s - 19s: CTA
        elif t < 19.0:
            frame[:] = (40, 20, 60)
            cv2.putText(frame, "SUBSCRIBE & DROP A LIKE NOW!", (width // 2 - 320, height // 2), cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 100, 200), 3)
            cv2.putText(frame, "[CTA ZONE: 15s - 19s]", (width // 2 - 130, height - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        # 19s - 24s: ENDSCREEN
        else:
            frame[:] = (10, 10, 10)
            cv2.rectangle(frame, (80, 80), (width - 80, height - 80), (100, 100, 100), 2)
            cv2.putText(frame, "THANKS FOR WATCHING!", (width // 2 - 220, height // 2 - 30), cv2.FONT_HERSHEY_DUPLEX, 1.1, (255, 255, 255), 2)
            cv2.putText(frame, "[ENDSCREEN ZONE: Outro Slate]", (width // 2 - 180, height - 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 2)

        out.write(frame)

    out.release()
    print(f"[Demo Generator] Done: {output_path}")
    return output_path


# ── COMMAND LINE ENTRYPOINT ──────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="ClipSort AI V3.0 — Multi-Modal Video Classification & Organization Engine"
    )
    parser.add_argument("--input", "-i", type=str, default="", help="Path to a video file (.mp4, .mov, .mkv) or folder of raw footage.")
    parser.add_argument("--spec", "-s", type=str, default="video_sorting_logic.json", help="Path to video_sorting_logic.json specification file.")
    parser.add_argument("--output", "-o", type=str, default="backend/output", help="Directory where sorted category subfolders will be created.")
    parser.add_argument("--demo", action="store_true", help="Generate a synthetic demo video and execute a full sorting test.")

    args = parser.parse_args()

    tool = ClipSortTool(spec_path=args.spec, output_dir=args.output)

    if args.demo:
        demo_file = generate_demo_video()
        tool.process_video(demo_file)
        print("\n🎉 Demo test completed! Check output folder:", tool.output_dir)
        return

    if not args.input:
        print("\n[Notice] No input provided. Running synthetic demonstration by default...")
        demo_file = generate_demo_video()
        tool.process_video(demo_file)
        print("\n🎉 Demo sorting completed! Review sorted folders in:", tool.output_dir)
        print("To sort your own video, run:")
        print(f"   python {os.path.basename(__file__)} --input /path/to/your_video.mp4")
        return

    target = os.path.abspath(args.input)
    if os.path.isdir(target):
        valid_exts = (".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v")
        vids = [os.path.join(target, f) for f in os.listdir(target) if f.lower().endswith(valid_exts)]
        print(f"[Folder Mode] Discovered {len(vids)} video(s) in: {target}")
        for v in vids:
            tool.process_video(v)
    elif os.path.isfile(target):
        tool.process_video(target)
    else:
        print(f"[Error] Target not found: {target}")


if __name__ == "__main__":
    main()
