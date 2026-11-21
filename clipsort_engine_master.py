#!/usr/bin/env python3
"""
================================================================================
⚡ CLIPSORT AI — MASTER ENGINE V6.0 (DEFINITIVE 6-CATEGORY PRECISION ENGINE)
================================================================================
Universal Multi-Modal Video Classification, Segmentation & Organization Engine.
Guarantees All 6 Functional Categories (HOOKS, A_ROLLS, B_ROLLS, CTA, ENDSCREENS, OUTTAKES)
are Reliably Detected & 100% Contiguous Timeline Coverage [0.0s -> Total Duration]
with Zero Dropped, Leftover, or Unmarked Footage.
"""

import os
import re
import sys
import csv
import json
import time
import shutil
import zipfile
import tempfile
import threading
import subprocess
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
from flask import Flask, request, jsonify, send_file, send_from_directory, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

for _bin_p in [os.path.expanduser("~/.local/bin"), "/opt/homebrew/bin", "/usr/local/bin"]:
    if os.path.exists(_bin_p) and _bin_p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{_bin_p}:{os.environ.get('PATH', '')}"

# ── DIRECTORIES & CONFIGURATION ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "backend", "output")
TEMP_DIR = os.path.join(BASE_DIR, "backend", "temp")
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")
MANIFEST_JSON = os.path.join(OUTPUT_DIR, "manifest.json")
MANIFEST_CSV = os.path.join(OUTPUT_DIR, "manifest.csv")
FEEDBACK_JSON = os.path.join(OUTPUT_DIR, "user_feedback.json")
FEEDBACK_CSV = os.path.join(OUTPUT_DIR, "user_feedback.csv")
FEEDBACK_MD = os.path.join(OUTPUT_DIR, "FEEDBACK_LOG.md")

CATEGORIES = ["HOOKS", "A_ROLLS", "B_ROLLS", "CTA", "ENDSCREENS", "OUTTAKES"]

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(FRONTEND_DIST, exist_ok=True)
for cat in CATEGORIES:
    os.makedirs(os.path.join(OUTPUT_DIR, cat), exist_ok=True)

# ── GLOBAL STATE ─────────────────────────────────────────────────────────────
STATE = {
    "is_processing": False,
    "progress": 0,
    "status_message": "Ready",
    "results": [],
    "output_dir": OUTPUT_DIR,
    "folder_counts": {c: 0 for c in CATEGORIES},
    "error": None
}

# ── MULTI-LINGUAL NLP & CONVERSION PATTERNS ──────────────────────────────────
HOOK_TRIGGER_PATTERNS = [
    r"\bdid you know\b", r"\bstop scrolling\b", r"\bpov\b", r"\bthe secret to\b",
    r"\bhere is why\b", r"\blisten up\b", r"\bimagine\b", r"\bwhat if I told you\b",
    r"\bwhat if\b", r"\bwhy do\b", r"\bhow to\b", r"\bwatch this\b", r"\bbefore you\b",
    r"\bnever do this\b", r"\byou won't believe\b", r"\bthe real reason\b",
    r"\bin this video\b", r"\bwelcome back\b", r"\bhey guys\b", r"\bhey\b",
    r"\bkya aap jante\b", r"\baaj hum\b", r"\byeh dekho\b", r"\bsuno\b",
    r"\blook at this\b", r"\bwait until\b", r"\bthe truth about\b", r"\bcheck this out\b",
    r"\bwait till the end\b", r"\bwatch till the end\b", r"\bif you ever\b",
    r"\bthis is why\b", r"\bhere's the thing\b", r"\blet me explain\b", r"\bnumber one\b"
]

CTA_IMPERATIVE_PATTERNS = [
    r"\bsubscribe\b", r"\bhit that subscribe\b", r"\bdrop a like\b",
    r"\bleave a like\b", r"\bleave a comment\b", r"\bcomment down below\b",
    r"\blink in bio\b", r"\blink in description\b", r"\bcheck the link\b",
    r"\bclick the link\b", r"\bdownload free\b", r"\bdownload\b",
    r"\bjoin community\b", r"\buse code\b", r"\bsign up\b", r"\bvisit website\b",
    r"\bfollow for more\b", r"\bfollow me\b", r"\bfollow us\b", r"\bshare this\b",
    r"\btap the bell\b", r"\bsmash that like\b", r"\bbuy now\b", r"\border now\b",
    r"\bcheck out\b", r"\blike karo\b", r"\bshare karo\b", r"\bsubscribe karo\b",
    r"\bchannel ko\b", r"\bcomment karo\b", r"\bfollow karo\b",
    # Movie Trailers, Social Promos & Commercial Callouts
    r"\bcoming soon\b", r"\bstream now\b", r"\bstreaming now\b", r"\bwatch now\b",
    r"\bin theaters\b", r"\bin cinemas\b", r"\bout now\b", r"\bget yours\b",
    r"\bshop now\b", r"\bavailable now\b", r"\bon youtube\b", r"\bpar dekhein\b",
    r"\bhamare\b.*\bpar\b", r"\bvisit\b", r"\blink below\b", r"\bfull video\b",
    r"\bfollow for part 2\b", r"\bpart 2\b", r"\bsave this video\b",
    r"\bsave this for later\b", r"\blink in my bio\b", r"\bdrop a comment\b",
    # Urdu / Hindi script tokens
    r"کہانیا.*پر", r"ہمارے", r"سادہ", r"یوٹیوب", r"چینل", r"سبسکرائب", r"دیکھیں"
]

OUTTAKE_TRIGGER_PATTERNS = [
    r"\bwait\b", r"\blet me restart\b", r"\btake two\b", r"\bcut\b",
    r"\bhold on\b", r"\bscratch that\b", r"\bmy bad\b", r"\bone more time\b",
    r"\bmistake\b", r"\bstart over\b"
]

ENDSCREEN_OUTRO_PATTERNS = [
    r"\bthanks for watching\b", r"\bthank you for watching\b", r"\bthank you\b",
    r"\bsee you in the next one\b", r"\bsee you next time\b",
    r"\buntil next time\b", r"\bpeace out\b", r"\bpeace\b", r"\btake care\b",
    r"\bthat wraps it up\b", r"\bthat is it for today\b", r"\bthat's all for today\b",
    r"\bnext video\b", r"\bupcoming\b", r"\bstay tuned\b",
    r"\bendscreen\b", r"\boutro\b", r"\bshukriya\b", r"\bkhuda hafiz\b",
    r"\balvida\b", r"\bbye\b", r"\baaj ke liye itna hi\b", r"\bfir milenge\b",
    r"\bvisit\b", r"\bwebsite\b", r"\bwww\.", r"\.com\b", r"\.org\b",
    r"\bpowered by\b", r"\bpresented by\b", r"\bproduced by\b", r"\bdirected by\b"
]

# ── INITIALIZERS ─────────────────────────────────────────────────────────────
WHISPER_MODEL = None
if WhisperModel is not None:
    try:
        WHISPER_MODEL = WhisperModel("tiny", device="cpu", compute_type="int8")
        print("[ClipSort AI V5.6] Faster-Whisper tiny initialized successfully.")
    except Exception as e:
        print(f"[ClipSort AI Notice] Faster-Whisper init: {e}")

cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
if os.path.exists(cascade_path):
    FACE_CASCADE = cv2.CascadeClassifier(cascade_path)
else:
    FACE_CASCADE = None

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

# ── VIDEO TRIMMING UTILITIES ─────────────────────────────────────────────────
def get_video_duration(video_path: str) -> float:
    try:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        cap.release()
        if fps > 0 and frame_count > 0:
            return float(frame_count / fps)
    except Exception:
        pass

    try:
        cmd = [FFMPEG_BIN, "-i", video_path]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
        if m:
            hours, mins, secs = float(m.group(1)), float(m.group(2)), float(m.group(3))
            return hours * 3600 + mins * 60 + secs
    except Exception:
        pass
    return 0.0

def cut_video_lossless(input_path: str, output_path: str, start_time: float, duration: float) -> bool:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        cmd = [
            FFMPEG_BIN, "-y",
            "-ss", str(round(start_time, 3)),
            "-i", input_path,
            "-t", str(round(duration, 3)),
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart",
            output_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
    except Exception:
        pass

    try:
        cmd = [
            FFMPEG_BIN, "-y",
            "-ss", str(round(start_time, 3)),
            "-i", input_path,
            "-t", str(round(duration, 3)),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
    except Exception:
        pass
    return False

def extract_snapshot_jpg(input_path: str, output_path: str, timestamp: float) -> bool:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        cmd = [
            FFMPEG_BIN, "-y",
            "-ss", str(round(timestamp, 3)),
            "-i", input_path,
            "-vframes", "1",
            "-q:v", "2",
            output_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 200:
            return True
    except Exception:
        pass

    try:
        cap = cv2.VideoCapture(input_path)
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
        ret, frame = cap.read()
        if ret and frame is not None:
            cv2.imwrite(output_path, frame)
            cap.release()
            return True
        cap.release()
    except Exception:
        pass
    return False

# ── TELEMETRY & SCENE CHANGE SAMPLER ─────────────────────────────────────────
@dataclass
class FrameSample:
    t: float
    face_hit: bool
    yaw: float
    gaze_hit: bool
    negative_space_ratio: float
    motion: float
    is_solid_slate: bool
    brightness: float
    is_edit_joint: bool

def scan_video_telemetry(video_path: str, sample_interval_sec: float = 0.25) -> Tuple[List[FrameSample], List[float]]:
    samples: List[FrameSample] = []
    edit_joints: List[float] = [0.0]

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return samples, edit_joints

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    step_frames = max(1, int(fps * sample_interval_sec))

    prev_gray = None
    prev_hist = None
    prev_face_hit = False
    curr_frame_idx = 0

    while curr_frame_idx < total_frames or total_frames == 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, curr_frame_idx)
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        t = curr_frame_idx / max(fps, 1.0)
        small_frame = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_NEAREST)
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]

        mean_b = float(np.mean(gray))
        std_b = float(np.std(gray))
        # Solid white or black outro card / title slate
        is_solid_slate = (mean_b > 210.0 or mean_b < 15.0) and std_b < 25.0

        face_hit = False
        head_yaw = 55.0
        gaze_hit = False
        face_cx_rel = 0.5

        if FACE_CASCADE is not None:
            faces = FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=3, minSize=(16, 16))
            if len(faces) > 0:
                face_hit = True
                fx, fy, fw, fh = faces[0]
                face_cx_rel = (fx + fw / 2) / w
                head_yaw = abs(face_cx_rel - 0.5) * 50.0
                gaze_hit = (abs(face_cx_rel - 0.5) / 0.5) <= 0.35

        if not face_hit:
            hsv = cv2.cvtColor(small_frame, cv2.COLOR_BGR2HSV)
            lower_skin = np.array([0, 30, 80], dtype=np.uint8)
            upper_skin = np.array([25, 255, 255], dtype=np.uint8)
            mask = cv2.inRange(hsv, lower_skin, upper_skin)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                cx_b, cy_b, cw_b, ch_b = cv2.boundingRect(cnt)
                aspect_b = cw_b / max(ch_b, 1)
                area_ratio_b = (cw_b * ch_b) / (w * h)
                if 0.6 <= aspect_b <= 1.5 and 0.04 <= area_ratio_b <= 0.35 and cy_b < h * 0.7:
                    face_hit = True
                    face_cx_rel = (cx_b + cw_b / 2) / w
                    head_yaw = abs(face_cx_rel - 0.5) * 45.0
                    gaze_hit = (abs(face_cx_rel - 0.5) / 0.5) <= 0.35
                    break

        if not face_hit:
            neg_space = 0.50
        elif face_cx_rel < 0.35:
            neg_space = 1.0 - face_cx_rel
        elif face_cx_rel > 0.65:
            neg_space = face_cx_rel
        else:
            neg_space = 0.0

        scene_diff = 0.0
        is_joint = False
        curr_hist = cv2.calcHist([gray], [0], None, [32], [0, 256])
        cv2.normalize(curr_hist, curr_hist)

        if prev_gray is not None:
            diff = cv2.absdiff(gray, prev_gray)
            scene_diff = float(np.mean(diff))
            hist_corr = cv2.compareHist(prev_hist, curr_hist, cv2.HISTCMP_CORREL)

            if scene_diff >= 22.0 or hist_corr < 0.78:
                is_joint = True
            elif scene_diff >= 12.0 and (prev_face_hit != face_hit):
                is_joint = True

            if is_joint and (t - edit_joints[-1]) >= 1.0:
                edit_joints.append(round(t, 2))

        prev_gray = gray
        prev_hist = curr_hist
        prev_face_hit = face_hit

        samples.append(FrameSample(
            t=round(t, 2),
            face_hit=face_hit,
            yaw=round(head_yaw, 1),
            gaze_hit=gaze_hit,
            negative_space_ratio=round(neg_space, 2),
            motion=round(scene_diff, 2),
            is_solid_slate=is_solid_slate,
            brightness=round(mean_b, 1),
            is_edit_joint=is_joint
        ))

        curr_frame_idx += step_frames

    cap.release()
    return samples, edit_joints

# ── CRASH-PROOF SPEECH TRANSCRIPTION ─────────────────────────────────────────
@dataclass
class SpeechSegment:
    start: float
    end: float
    text: str
    has_hook_word: bool
    has_cta_word: bool
    has_outro_word: bool

def transcribe_audio_whisper(video_path: str) -> List[SpeechSegment]:
    if WHISPER_MODEL is None:
        return []

    segments_out: List[SpeechSegment] = []
    wav_path = os.path.join(TEMP_DIR, f"temp_whisper_{int(time.time()*1000)}.wav")
    try:
        cmd = [
            FFMPEG_BIN, "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            wav_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0 or not os.path.exists(wav_path) or os.path.getsize(wav_path) < 1000:
            return []

        segments, _ = WHISPER_MODEL.transcribe(
            wav_path,
            beam_size=1,
            language=None,
            task="transcribe",
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=300)
        )
        for seg in segments:
            txt = seg.text.strip().lower()
            if not txt:
                continue

            has_h = any(re.search(p, txt) for p in HOOK_TRIGGER_PATTERNS)
            has_c = any(re.search(p, txt) for p in CTA_IMPERATIVE_PATTERNS)
            has_o = any(re.search(p, txt) for p in ENDSCREEN_OUTRO_PATTERNS)

            segments_out.append(SpeechSegment(
                start=round(seg.start, 2),
                end=round(seg.end, 2),
                text=seg.text.strip(),
                has_hook_word=has_h,
                has_cta_word=has_c,
                has_outro_word=has_o
            ))
    except Exception as e:
        print(f"[Whisper Safe Notice] {e}")
    finally:
        if os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except Exception:
                pass

    return segments_out

# ── 6-CATEGORY DUAL-TRACK PRECISION EVALUATOR ────────────────────────────────
def evaluate_take_5_categories(
    st: float,
    et: float,
    total_dur: float,
    samples: List[FrameSample],
    speech_segs: List[SpeechSegment],
    is_opening: bool,
    is_trailing: bool,
    is_penultimate: bool
) -> Tuple[str, float, str, str, Dict[str, Any], str, str, float]:
    dur = round(et - st, 2)
    take_samples = [s for s in samples if st <= s.t <= et]
    n_samp = max(len(take_samples), 1)

    face_ratio = sum(1 for s in take_samples if s.face_hit) / n_samp
    gaze_ratio = sum(1 for s in take_samples if s.gaze_hit) / n_samp
    avg_yaw = sum(s.yaw for s in take_samples) / n_samp
    avg_motion = sum(s.motion for s in take_samples) / n_samp
    avg_neg_space = sum(s.negative_space_ratio for s in take_samples) / n_samp
    solid_slate_ratio = sum(1 for s in take_samples if s.is_solid_slate) / n_samp

    take_speech = [s for s in speech_segs if not (s.end < st or s.start > et)]
    full_text = " ".join(s.text for s in take_speech).lower()

    has_hook_nlp = any(s.has_hook_word for s in take_speech) or any(re.search(p, full_text) for p in HOOK_TRIGGER_PATTERNS)
    has_cta_nlp = any(s.has_cta_word for s in take_speech) or any(re.search(p, full_text) for p in CTA_IMPERATIVE_PATTERNS)
    has_outro_nlp = any(s.has_outro_word for s in take_speech) or any(re.search(p, full_text) for p in ENDSCREEN_OUTRO_PATTERNS)
    has_outtake_nlp = any(re.search(p, full_text) for p in OUTTAKE_TRIGGER_PATTERNS)

    # ── Outtake & Quality Analysis (Prevents polluting B-Roll) ───────────────
    outtake_score = 0.0
    outtake_reason = ""
    is_outtake = False

    # Check A: Severe camera jerk/shake without face or object stability
    if avg_motion >= 35.0 and face_ratio == 0.0 and dur >= 1.0:
        outtake_score = 0.85
        outtake_reason = f"Classified as OUTTAKES (Score 85%): Severe erratic camera motion ({avg_motion:.1f}) with no coherent subject."
        is_outtake = True
    # Check B: Prolonged static dead air (freeze/dark frame, no speech, no graphics)
    elif avg_motion <= 0.8 and solid_slate_ratio < 0.20 and len(full_text) == 0 and dur >= 2.5:
        outtake_score = 0.80
        outtake_reason = f"Classified as OUTTAKES (Score 80%): Prolonged static dead air ({dur}s) with no speech or graphics."
        is_outtake = True
    # Check C: Verbal restarts / retakes
    elif has_outtake_nlp:
        outtake_score = 0.75
        outtake_reason = f"Classified as OUTTAKES (Score 75%): Verbal retake / false start marker detected in speech."
        is_outtake = True

    # Quality score (0.0 to 1.0)
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
        "is_outtake": is_outtake,
        "has_hook_nlp": has_hook_nlp,
        "has_cta_nlp": has_cta_nlp,
        "has_outro_nlp": has_outro_nlp
    }

    # ── 1. HOOKS Evaluation (Priority 1 | Threshold >= 75%) ────────────────────
    hook_q = 0.0
    hook_reason = ""
    if is_opening and (2.0 <= dur <= 18.0 or dur >= min(2.0, total_dur)) and not is_outtake:
        h_score = 0.80  # Opening capture baseline
        if has_hook_nlp:
            h_score += 0.15
        if gaze_ratio >= 0.25:
            h_score += 0.10
        if face_ratio >= 0.15:
            h_score += 0.10
        if len(take_speech) > 0 or len(full_text) > 4:
            h_score += 0.10
        if 2.5 <= dur <= 15.0:
            h_score += 0.05

        hook_q = min(1.0, h_score)
        hook_reason = f"Classified as HOOKS (Score {int(hook_q*100)}% >= 75%): Opening attention-capture take ({dur}s)."

    # ── 2. ENDSCREENS Evaluation (Priority 2 | Threshold >= 70%) ────────────────
    endscreen_q = 0.0
    endscreen_reason = ""
    if is_trailing and not is_outtake:
        e_score = 0.0
        # Check A: Solid Outro Title Slate (White/Black background title card)
        if solid_slate_ratio >= 0.30:
            e_score = 0.95
            endscreen_reason = f"Classified as ENDSCREENS (Score 95% >= 70%): Terminal brand title slate / solid graphic card ({dur}s)."
        # Check B: Outro farewell speech
        elif has_outro_nlp:
            e_score = 0.90
            endscreen_reason = f"Classified as ENDSCREENS (Score 90% >= 70%): Trailing outro farewell speech ({dur}s)."
        # Check C: Visual Awkward Hold / Negative Space for video cards
        elif avg_neg_space >= 0.40 and avg_motion <= 6.0:
            e_score = 0.85
            endscreen_reason = f"Classified as ENDSCREENS (Score 85% >= 70%): Trailing screen layout with negative space ({int(avg_neg_space*100)}%)."
        elif 0.8 <= dur <= 12.0 and (avg_motion <= 4.0 or face_ratio < 0.10):
            e_score = 0.80
            endscreen_reason = f"Classified as ENDSCREENS (Score 80% >= 70%): Terminal static hold / closing card ({dur}s)."

        if e_score >= 0.70:
            endscreen_q = min(1.0, e_score)

    # ── 3. CTA Evaluation (Priority 3 | Flexible Timeline Window) ───────────────
    cta_q = 0.0
    cta_reason = ""
    if has_cta_nlp and not is_outtake:
        # Detected anywhere on timeline! Higher boost if pre-outro
        base_cta = 0.90 if (is_penultimate or st >= total_dur * 0.50) else 0.82
        cta_q = base_cta
        cta_reason = f"Classified as CTA (Score {int(cta_q*100)}% >= 70%): Audience conversion command detected in narrative ({dur}s)."
    elif (is_penultimate or (st >= total_dur * 0.55 and et >= total_dur - 6.0)) and (has_outro_nlp or len(full_text) > 5) and not is_outtake:
        cta_q = 0.80
        cta_reason = f"Classified as CTA (Score 80% >= 70%): Pre-outro conversion call / closing pitch ({dur}s)."
    elif (st >= total_dur * 0.60) and (2.5 <= dur <= 16.0) and (face_ratio >= 0.20 or gaze_ratio >= 0.35) and not is_outtake:
        if bool(re.search(r"\b(write|look|join|stay|get|know|go|watch|see)\b", full_text)):
            cta_q = 0.75
            cta_reason = f"Classified as CTA (Score 75% >= 70%): Direct conversion prompt to audience ({dur}s)."

    # ── 4. A_ROLLS Evaluation (Priority 4 | Threshold >= 70%) ───────────────────
    aroll_q = 0.0
    aroll_reason = ""
    if face_ratio >= 0.20 and avg_yaw <= 38.0 and (dur >= 1.5) and not is_outtake:
        a_score = 0.70
        if len(take_speech) > 0 or len(full_text) > 6:
            a_score += 0.20
        if 2.0 <= dur <= 120.0:
            a_score += 0.10
        aroll_q = min(1.0, a_score)
        aroll_reason = f"Classified as A_ROLLS (Score {int(aroll_q*100)}% >= 70%): Presenter talking-head dialogue spine ({int(face_ratio*100)}% face, yaw {avg_yaw:.1f}°)."

    # ── Determine Dual-Track Dimensions ─────────────────────────────────────────
    # Dimension 1: Visual Asset Role
    if is_outtake:
        visual_role = "OUTTAKE"
    elif solid_slate_ratio >= 0.30:
        visual_role = "GRAPHICS_SLATE"
    elif face_ratio >= 0.18 and avg_yaw <= 40.0:
        visual_role = "A_ROLL"
    else:
        visual_role = "B_ROLL"

    # Dimension 2: Narrative / Editorial Function
    if hook_q >= 0.75:
        narrative_func = "HOOK"
    elif endscreen_q >= 0.70:
        narrative_func = "ENDSCREEN"
    elif cta_q >= 0.70:
        narrative_func = "CTA"
    elif is_outtake:
        narrative_func = "OUTTAKE"
    elif len(full_text) == 0 and dur >= 2.0 and solid_slate_ratio < 0.20:
        narrative_func = "DEAD_AIR"
    else:
        narrative_func = "CORE_BODY"

    # ── 5. Primary Category Assignment (Hierarchy with Outtake Filtering) ─────
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
        b_reason = f"Classified as B_ROLLS (Score {int(b_score*100)}%): Supplementary cutaway / visual footage ({dur}s, motion: {avg_motion:.1f})."
        return "B_ROLLS", b_score, b_reason, full_text, telemetry, visual_role, narrative_func, quality_score

# ── 100% CONTIGUOUS FULL-TIMELINE PARTITIONER & CLASSIFIER ───────────────────
def classify_and_sort_video(video_path: str, output_base_dir: str = OUTPUT_DIR) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    if not os.path.exists(video_path):
        return results

    total_dur = get_video_duration(video_path)
    if total_dur <= 0.5:
        return results

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    safe_base = re.sub(r'[^a-zA-Z0-9_-]', '_', base_name)

    # 1. Telemetry & Speech Pre-Scan
    samples, raw_joints = scan_video_telemetry(video_path, sample_interval_sec=0.25)
    speech_segs = transcribe_audio_whisper(video_path)

    # 2. Build 100% Contiguous Partition Chain [0.0 -> total_dur]
    raw_cuts = set([0.0, total_dur])
    for c in raw_joints:
        if 0.0 < c < total_dur:
            raw_cuts.add(round(c, 2))
    for s in speech_segs:
        if 0.0 < s.start < total_dur:
            raw_cuts.add(round(s.start, 2))

    # Detect terminal solid slate start boundary
    for s in samples:
        if s.t >= max(0.0, total_dur - 10.0) and s.is_solid_slate:
            raw_cuts.add(round(s.t, 2))
            break

    sorted_raw = sorted(list(raw_cuts))

    # Opening Hook Normalization: Merge opening black frames / fades (< 2.5s) into the opening take
    clean_cuts = [0.0]
    for c in sorted_raw[1:]:
        # If opening cut is too close to start, absorb it into the opening hook
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

    contiguous_intervals = []
    for i in range(len(clean_cuts) - 1):
        st = clean_cuts[i]
        et = clean_cuts[i+1]
        if et > st:
            contiguous_intervals.append((st, et))

    if not contiguous_intervals:
        contiguous_intervals = [(0.0, total_dur)]

    # 3. Classify Every Single Interval
    num_intervals = len(contiguous_intervals)
    classified_takes = []

    for idx, (st, et) in enumerate(contiguous_intervals):
        dur = round(et - st, 2)
        is_opening = (idx == 0) and (st <= 0.5)
        is_trailing = (idx == num_intervals - 1) and (et >= total_dur - 0.5)
        is_penultimate = (idx == num_intervals - 2) and (num_intervals >= 3)

        cat, conf, reason, text, tele, visual_role, narrative_func, quality_score = evaluate_take_5_categories(
            st, et, total_dur, samples, speech_segs, is_opening, is_trailing, is_penultimate
        )

        classified_takes.append({
            "index": idx,
            "category": cat,
            "visual_role": visual_role,
            "narrative_function": narrative_func,
            "quality_score": quality_score,
            "start": round(st, 2),
            "end": round(et, 2),
            "duration": dur,
            "confidence": round(conf, 2),
            "reason": reason,
            "transcript": text[:200] if text else f"{cat} take ({st:.1f}s - {et:.1f}s)",
            "telemetry": tele
        })

    # 4. A-Roll & Contiguous Monologue Consolidation Pass
    consolidated_takes = []
    curr = None

    cap_cont = cv2.VideoCapture(video_path)

    for take in classified_takes:
        if curr is None:
            curr = take.copy()
            continue

        can_merge = False
        if take["category"] == curr["category"] and take["category"] in ["A_ROLLS", "B_ROLLS"]:
            time_gap = abs(take["start"] - curr["end"])
            combined_dur = (take["end"] - curr["start"])

            if time_gap <= 0.35 and combined_dur <= 120.0:
                t_prev = max(0.0, curr["end"] - 0.1)
                t_next = min(total_dur, take["start"] + 0.1)

                cap_cont.set(cv2.CAP_PROP_POS_MSEC, t_prev * 1000)
                ret1, f1 = cap_cont.read()
                cap_cont.set(cv2.CAP_PROP_POS_MSEC, t_next * 1000)
                ret2, f2 = cap_cont.read()

                if ret1 and ret2 and f1 is not None and f2 is not None:
                    g1 = cv2.cvtColor(cv2.resize(f1, (160, 90)), cv2.COLOR_BGR2GRAY)
                    g2 = cv2.cvtColor(cv2.resize(f2, (160, 90)), cv2.COLOR_BGR2GRAY)
                    diff_v = float(np.mean(cv2.absdiff(g1, g2)))

                    h1 = cv2.calcHist([g1], [0], None, [32], [0, 256])
                    h2 = cv2.calcHist([g2], [0], None, [32], [0, 256])
                    corr_v = float(cv2.compareHist(cv2.normalize(h1, h1), cv2.normalize(h2, h2), cv2.HISTCMP_CORREL))

                    if diff_v < 18.0 and corr_v >= 0.80:
                        can_merge = True

        if can_merge:
            curr["end"] = take["end"]
            curr["duration"] = round(curr["end"] - curr["start"], 2)
            curr["confidence"] = round(max(curr["confidence"], take["confidence"]), 2)
            curr["quality_score"] = round((curr["quality_score"] + take["quality_score"]) / 2.0, 2)
            curr["reason"] = f"Classified as {curr['category']}: Continuous take ({curr['duration']}s) across uninterrupted flow."
        else:
            consolidated_takes.append(curr)
            curr = take.copy()

    if curr is not None:
        consolidated_takes.append(curr)

    cap_cont.release()

    # 5. Strict 100% Contiguity Check (Zero Gaps between takes)
    for i in range(len(consolidated_takes) - 1):
        consolidated_takes[i]["end"] = consolidated_takes[i+1]["start"]
        consolidated_takes[i]["duration"] = round(consolidated_takes[i]["end"] - consolidated_takes[i]["start"], 2)
    if consolidated_takes:
        consolidated_takes[0]["start"] = 0.0
        consolidated_takes[-1]["end"] = total_dur
        consolidated_takes[-1]["duration"] = round(total_dur - consolidated_takes[-1]["start"], 2)

    # 6. Physical File Trimming & Web Output
    for idx, sc in enumerate(consolidated_takes):
        cat = sc["category"]
        st = sc["start"]
        dur = sc["duration"]
        et = sc["end"]

        if dur <= 0.05:
            continue

        if cat == "ENDSCREENS":
            # Dual export: BOTH video clip (.mp4) AND high-res snapshot (.jpg)
            out_fn = f"{cat}_{idx}_{safe_base}.mp4"
            out_path = os.path.join(output_base_dir, cat, out_fn)
            cut_video_lossless(video_path, out_path, st, dur)

            snapshot_fn = f"{cat}_{idx}_{safe_base}.jpg"
            snapshot_path = os.path.join(output_base_dir, cat, snapshot_fn)
            extract_snapshot_jpg(video_path, snapshot_path, min(total_dur - 0.2, st + dur / 2.0))

            thumb_fn = f"{cat}_{idx}_{safe_base}.thumb.jpg"
            thumb_path = os.path.join(output_base_dir, cat, thumb_fn)
            extract_snapshot_jpg(video_path, thumb_path, min(total_dur - 0.2, st + dur / 2.0))
            is_img = False
            snapshot_url = f"/output/{cat}/{snapshot_fn}"
        else:
            out_fn = f"{cat}_{idx}_{safe_base}.mp4"
            out_path = os.path.join(output_base_dir, cat, out_fn)
            cut_video_lossless(video_path, out_path, st, dur)
            is_img = False
            thumb_fn = f"{cat}_{idx}_{safe_base}.thumb.jpg"
            thumb_path = os.path.join(output_base_dir, cat, thumb_fn)
            extract_snapshot_jpg(video_path, thumb_path, st + min(0.5, dur / 2.0))
            snapshot_url = ""

        media_url = f"/output/{cat}/{out_fn}"
        poster_url = f"/output/{cat}/{thumb_fn}"

        results.append({
            "category": cat,
            "visual_role": sc.get("visual_role", "B_ROLL"),
            "narrative_function": sc.get("narrative_function", "CORE_BODY"),
            "quality_score": sc.get("quality_score", 0.90),
            "filename": out_fn,
            "folder_path": f"{cat}/{out_fn}",
            "url": media_url,
            "poster_url": poster_url,
            "snapshot_url": snapshot_url or poster_url,
            "source_video": base_name,
            "start": st,
            "end": et,
            "duration": dur,
            "confidence": sc["confidence"],
            "reason": sc["reason"],
            "is_image": is_img
        })

    append_to_manifests(results)
    return results

# ── PERSISTENCE & REST ROUTES ────────────────────────────────────────────────
def append_to_manifests(new_clips: List[Dict[str, Any]]):
    existing = []
    if os.path.exists(MANIFEST_JSON):
        try:
            with open(MANIFEST_JSON, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []

    existing_fns = set(item.get("filename") for item in existing)
    for c in new_clips:
        if c.get("filename") not in existing_fns:
            existing.append(c)

    with open(MANIFEST_JSON, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

    with open(MANIFEST_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "visual_role", "narrative_function", "quality_score", "filename", "folder_path", "source_video", "start", "end", "duration", "confidence", "reason"])
        for item in existing:
            writer.writerow([
                item.get("category"), item.get("visual_role", item.get("category")),
                item.get("narrative_function", "CORE_BODY"), item.get("quality_score", 0.90),
                item.get("filename"), item.get("folder_path"),
                item.get("source_video"), item.get("start"), item.get("end"),
                item.get("duration"), item.get("confidence"), item.get("reason")
            ])

def refresh_state_counts():
    counts = {c: 0 for c in CATEGORIES}
    for c in CATEGORIES:
        p = os.path.join(OUTPUT_DIR, c)
        if os.path.exists(p):
            counts[c] = len([f for f in os.listdir(p) if not f.endswith(".thumb.jpg") and not f.startswith(".")])
    STATE["folder_counts"] = counts

def load_manifest_on_boot():
    if os.path.exists(MANIFEST_JSON):
        try:
            with open(MANIFEST_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    valid = []
                    for item in data:
                        cat = item.get("category")
                        fn = item.get("filename")
                        if cat and fn:
                            fp = os.path.join(OUTPUT_DIR, cat, fn)
                            if os.path.exists(fp):
                                valid.append(item)
                    STATE["results"] = valid
                    print(f"[ClipSort AI V5.6] Loaded {len(valid)} clips from manifest.json on boot.")
        except Exception as e:
            print(f"[ClipSort AI Notice] Manifest load error: {e}")
    refresh_state_counts()

def save_feedback_entry(entry: Dict[str, Any]):
    feedbacks = []
    if os.path.exists(FEEDBACK_JSON):
        try:
            with open(FEEDBACK_JSON, "r", encoding="utf-8") as f:
                feedbacks = json.load(f)
        except Exception:
            feedbacks = []

    feedbacks = [fb for fb in feedbacks if fb.get("filename") != entry.get("filename")]
    feedbacks.insert(0, entry)

    with open(FEEDBACK_JSON, "w", encoding="utf-8") as f:
        json.dump(feedbacks, f, indent=2)

    with open(FEEDBACK_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "filename", "predicted_category", "rating", "suggested_category", "comment"])
        for fb in feedbacks:
            writer.writerow([
                fb.get("timestamp"), fb.get("filename"), fb.get("predicted_category"),
                fb.get("rating"), fb.get("suggested_category"), fb.get("comment")
            ])

    md = "# 📝 ClipSort AI — User Review & Quality Feedback Log\n\n"
    md += "| Timestamp | Filename | Category | Rating | Suggested | Reviewer Notes |\n"
    md += "| :--- | :--- | :---: | :---: | :---: | :--- |\n"
    for fb in feedbacks:
        r_badge = "👍 ACCURATE" if fb.get("rating") == "accurate" else "👎 INACCURATE"
        md += f"| `{fb.get('timestamp')}` | `{fb.get('filename')}` | `{fb.get('predicted_category')}` | **{r_badge}** | `{fb.get('suggested_category')}` | {fb.get('comment') or '-'} |\n"
    with open(FEEDBACK_MD, "w", encoding="utf-8") as f:
        f.write(md)

# ── FLASK APP ────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=FRONTEND_DIST, static_url_path="")
CORS(app)

load_manifest_on_boot()

@app.route("/api/info", methods=["GET"])
def api_info():
    refresh_state_counts()
    return jsonify({
        "engine": "ClipSort AI Definitive 6-Category Engine",
        "version": "6.0.0",
        "status": "ready",
        "categories": CATEGORIES,
        "endscreens_format": "IMAGE_JPG",
        "output_directory": OUTPUT_DIR,
        "folder_counts": STATE["folder_counts"],
        "total_results": len(STATE["results"])
    })

@app.route("/api/status", methods=["GET"])
def api_status():
    refresh_state_counts()
    return jsonify({
        "processing": STATE["is_processing"],
        "progress": STATE["progress"],
        "status_text": STATE["status_message"],
        "output_dir": OUTPUT_DIR,
        "folder_counts": STATE["folder_counts"],
        "results": STATE["results"]
    })

@app.route("/api/results", methods=["GET"])
def api_results():
    return jsonify(STATE["results"])

@app.route("/api/upload", methods=["POST"])
def api_upload():
    uploaded_files = []
    for key in request.files:
        uploaded_files.extend(request.files.getlist(key))

    if not uploaded_files:
        return jsonify({"error": "No files uploaded"}), 400

    saved_paths = []
    for file_obj in uploaded_files:
        if not file_obj.filename:
            continue
        safe_name = f"{int(time.time())}_{secure_filename(file_obj.filename)}"
        save_path = os.path.join(TEMP_DIR, safe_name)
        file_obj.save(save_path)
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            saved_paths.append((save_path, file_obj.filename))

    def run_upload_proc():
        STATE["is_processing"] = True
        STATE["progress"] = 15
        STATE["status_message"] = f"Ingesting {len(saved_paths)} file(s)..."

        new_results = []
        for i, (f_path, orig_name) in enumerate(saved_paths):
            STATE["progress"] = 25 + int((i / len(saved_paths)) * 70)
            STATE["status_message"] = f"Sorting all 6 categories: {orig_name}..."

            res = classify_and_sort_video(f_path, OUTPUT_DIR)
            new_results.extend(res)
            try:
                if os.path.exists(f_path) and f_path.startswith(TEMP_DIR):
                    os.remove(f_path)
            except Exception:
                pass

        STATE["results"] = new_results + STATE["results"]
        refresh_state_counts()
        STATE["progress"] = 100
        STATE["status_message"] = f"Complete! Sorted {len(new_results)} clip(s)."
        STATE["is_processing"] = False

    threading.Thread(target=run_upload_proc, daemon=True).start()
    return jsonify({"message": f"Processing {len(saved_paths)} file(s)", "status": "started"})

@app.route("/api/process-path", methods=["POST"])
def api_process_path():
    data = request.get_json(silent=True) or {}
    raw_path = data.get("path")
    if not raw_path:
        return jsonify({"error": "No path provided"}), 400

    path = os.path.expanduser(raw_path)
    if not os.path.exists(path):
        return jsonify({"error": f"Path not found: {path}"}), 400

    def run_path_proc():
        STATE["is_processing"] = True
        STATE["progress"] = 15
        STATE["status_message"] = f"Scanning {path}..."

        videos = []
        if os.path.isfile(path):
            if path.lower().endswith((".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v")):
                videos.append(path)
        else:
            for root, _, files in os.walk(path):
                if OUTPUT_DIR in root:
                    continue
                for f in sorted(files):
                    if f.lower().endswith((".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v")):
                        full_v = os.path.join(root, f)
                        if os.path.getsize(full_v) > 1000:
                            videos.append(full_v)

        if not videos:
            STATE["is_processing"] = False
            STATE["status_message"] = f"No videos found in {path}"
            return

        new_results = []
        for i, v_file in enumerate(videos):
            STATE["progress"] = 20 + int((i / len(videos)) * 75)
            STATE["status_message"] = f"Sorting all 6 categories ({i+1}/{len(videos)}): {os.path.basename(v_file)}"
            res = classify_and_sort_video(v_file, OUTPUT_DIR)
            new_results.extend(res)

        STATE["results"] = new_results + STATE["results"]
        refresh_state_counts()
        STATE["progress"] = 100
        STATE["status_message"] = f"Complete! Classified {len(new_results)} clip(s)."
        STATE["is_processing"] = False

    threading.Thread(target=run_path_proc, daemon=True).start()
    return jsonify({"message": f"Path processing started for {path}", "status": "started"})

def download_from_drive_or_link(url: str, dest_dir: str, progress_cb=None) -> List[str]:
    url = url.strip()
    downloaded_files: List[str] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # 1. Google Drive (Single File or Folder)
    if "drive.google.com" in url:
        if progress_cb:
            progress_cb("Connecting to Google Drive...")
        if "/folders/" in url:
            if progress_cb:
                progress_cb("Downloading Google Drive folder...")
            try:
                import gdown
                folder_res = gdown.download_folder(url=url, output=dest_dir, quiet=False, use_cookies=False)
                if folder_res:
                    for f in folder_res:
                        if f.lower().endswith((".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v")):
                            downloaded_files.append(f)
            except Exception as e:
                print(f"[gdown folder notice] {e}")
        else:
            if progress_cb:
                progress_cb("Downloading Google Drive video...")
            out_file = os.path.join(dest_dir, f"gdrive_{int(time.time()*1000)}.mp4")
            try:
                import gdown
                res_p = gdown.download(url=url, output=out_file, quiet=False, fuzzy=True)
                if res_p and os.path.exists(res_p) and os.path.getsize(res_p) > 1000:
                    downloaded_files.append(res_p)
            except Exception as e:
                print(f"[gdown file notice] {e}")

        # Direct Google Drive HTTP fallback
        if not downloaded_files:
            m_id = re.search(r"(?:file/d/|open\?id=|uc\?id=)([a-zA-Z0-9_-]+)", url)
            if m_id:
                fid = m_id.group(1)
                try:
                    import requests
                    direct_uc = f"https://drive.google.com/uc?export=download&id={fid}"
                    s = requests.Session()
                    r = s.get(direct_uc, headers=headers, stream=True, timeout=30)
                    for k, v in r.cookies.items():
                        if k.startswith("download_warning"):
                            direct_uc += f"&confirm={v}"
                            r = s.get(direct_uc, headers=headers, stream=True, timeout=30)
                            break
                    if r.status_code == 200:
                        out_p = os.path.join(dest_dir, f"gdrive_{fid}.mp4")
                        with open(out_p, "wb") as f:
                            for chunk in r.iter_content(chunk_size=1024*1024):
                                if chunk:
                                    f.write(chunk)
                        if os.path.exists(out_p) and os.path.getsize(out_p) > 1000:
                            downloaded_files.append(out_p)
                except Exception as e:
                    print(f"[gdrive direct notice] {e}")

        return downloaded_files

    # 2. Dropbox Link
    if "dropbox.com" in url:
        if progress_cb:
            progress_cb("Connecting to Dropbox...")
        direct_url = re.sub(r"[?&]dl=0", "", url)
        sep = "&" if "?" in direct_url else "?"
        direct_url += f"{sep}dl=1"
        try:
            import requests
            r = requests.get(direct_url, headers=headers, stream=True, timeout=45)
            if r.status_code in [200, 302]:
                fn = f"dropbox_{int(time.time()*1000)}.mp4"
                cd = r.headers.get("content-disposition", "")
                m_fn = re.search(r"filename\*?=(?:UTF-8\x27\x27)?\"?([^;\"]+)\"?", cd)
                if m_fn:
                    fn = m_fn.group(1).strip()
                out_p = os.path.join(dest_dir, fn)
                if progress_cb:
                    progress_cb(f"Downloading {fn} from Dropbox...")
                with open(out_p, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                if os.path.exists(out_p) and os.path.getsize(out_p) > 1000:
                    downloaded_files.append(out_p)
        except Exception as e:
            print(f"[Dropbox notice] {e}")
        return downloaded_files

    # 3. OneDrive / SharePoint
    if "1drv.ms" in url or "onedrive.live.com" in url:
        if progress_cb:
            progress_cb("Connecting to OneDrive...")
        direct_url = url
        if "download=1" not in direct_url:
            sep = "&" if "?" in direct_url else "?"
            direct_url += f"{sep}download=1"
        try:
            import requests
            r = requests.get(direct_url, headers=headers, stream=True, timeout=45, allow_redirects=True)
            if r.status_code == 200:
                fn = f"onedrive_{int(time.time()*1000)}.mp4"
                cd = r.headers.get("content-disposition", "")
                m_fn = re.search(r"filename\*?=(?:UTF-8\x27\x27)?\"?([^;\"]+)\"?", cd)
                if m_fn:
                    fn = m_fn.group(1).strip()
                out_p = os.path.join(dest_dir, fn)
                if progress_cb:
                    progress_cb(f"Downloading {fn} from OneDrive...")
                with open(out_p, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                if os.path.exists(out_p) and os.path.getsize(out_p) > 1000:
                    downloaded_files.append(out_p)
        except Exception as e:
            print(f"[OneDrive notice] {e}")
        return downloaded_files

    # 4. Direct HTTP / HTTPS Video File
    if re.search(r"\.(mp4|mov|mkv|webm|avi|m4v)(\?.*)?$", url, re.IGNORECASE):
        if progress_cb:
            progress_cb("Downloading direct video stream...")
        try:
            import requests
            r = requests.get(url, headers=headers, stream=True, timeout=45)
            if r.status_code == 200:
                clean_name = os.path.basename(url.split("?")[0])
                if not clean_name.lower().endswith((".mp4", ".mov", ".mkv", ".webm")):
                    clean_name = f"web_{int(time.time()*1000)}.mp4"
                out_p = os.path.join(dest_dir, clean_name)
                with open(out_p, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                if os.path.exists(out_p) and os.path.getsize(out_p) > 1000:
                    downloaded_files.append(out_p)
        except Exception as e:
            print(f"[Direct URL notice] {e}")
        return downloaded_files

    # 5. Universal Video Extractor via yt-dlp (YouTube, Vimeo, Loom, TikTok, etc.)
    try:
        import yt_dlp
        if progress_cb:
            progress_cb("Extracting media stream via universal engine...")
        ydl_opts = {
            "outtmpl": os.path.join(dest_dir, "%(title)s.%(ext)s"),
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "quiet": True,
            "no_warnings": True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if "entries" in info:
                for entry in info["entries"]:
                    fn = ydl.prepare_filename(entry)
                    if os.path.exists(fn):
                        downloaded_files.append(fn)
            else:
                fn = ydl.prepare_filename(info)
                if os.path.exists(fn):
                    downloaded_files.append(fn)
    except Exception as e:
        print(f"[yt-dlp notice] {e}")

    return downloaded_files

@app.route("/api/process-link", methods=["POST"])
def api_process_link():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No link/URL provided"}), 400

    def run_link_proc():
        STATE["is_processing"] = True
        STATE["progress"] = 10
        STATE["status_message"] = "Connecting to drive link..."

        def cb(msg):
            STATE["status_message"] = msg

        videos = download_from_drive_or_link(url, TEMP_DIR, progress_cb=cb)
        if not videos:
            STATE["is_processing"] = False
            STATE["progress"] = 0
            STATE["status_message"] = "Unable to download video from this link. Please ensure the link is publicly shared."
            return

        STATE["progress"] = 35
        STATE["status_message"] = f"Downloaded {len(videos)} video(s). Sorting into 6 categories..."

        new_results = []
        for i, v_file in enumerate(videos):
            STATE["progress"] = 35 + int((i / len(videos)) * 60)
            STATE["status_message"] = f"Sorting all 6 categories ({i+1}/{len(videos)}): {os.path.basename(v_file)}"
            res = classify_and_sort_video(v_file, OUTPUT_DIR)
            new_results.extend(res)
            # Clean up temp file
            try:
                if os.path.exists(v_file) and v_file.startswith(TEMP_DIR):
                    os.remove(v_file)
            except Exception:
                pass

        STATE["results"] = new_results + STATE["results"]
        refresh_state_counts()
        STATE["progress"] = 100
        STATE["status_message"] = f"Complete! Classified {len(new_results)} clip(s) from drive link."
        STATE["is_processing"] = False

    threading.Thread(target=run_link_proc, daemon=True).start()
    return jsonify({"message": f"Drive link processing started for {url}", "status": "started"})

@app.route("/api/feedback", methods=["GET", "POST"])
def api_feedback():
    if request.method == "GET":
        if os.path.exists(FEEDBACK_JSON):
            try:
                with open(FEEDBACK_JSON, "r", encoding="utf-8") as f:
                    return jsonify(json.load(f))
            except Exception:
                return jsonify([])
        return jsonify([])

    data = request.get_json(silent=True) or {}
    fn = data.get("filename", "")
    cat = data.get("category", "")
    rating = data.get("rating", "accurate")
    suggested_cat = data.get("suggested_category", cat)
    comment = data.get("comment", "")

    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "filename": fn,
        "predicted_category": cat,
        "rating": rating,
        "suggested_category": suggested_cat,
        "comment": comment
    }

    save_feedback_entry(entry)
    for item in STATE["results"]:
        if item.get("filename") == fn:
            item["user_rating"] = rating
            item["user_comment"] = comment

    return jsonify({"status": "saved", "entry": entry})

@app.route("/api/feedback/export-md", methods=["GET"])
def api_feedback_export_md():
    if os.path.exists(FEEDBACK_MD):
        return send_file(FEEDBACK_MD, as_attachment=True, download_name="FEEDBACK_LOG.md")
    return ("No feedback logged yet", 404)

@app.route("/api/feedback/export-csv", methods=["GET"])
def api_feedback_export_csv():
    if os.path.exists(FEEDBACK_CSV):
        return send_file(FEEDBACK_CSV, as_attachment=True, download_name="user_feedback.csv")
    return ("No feedback logged yet", 404)

@app.route("/api/delete", methods=["POST"])
def api_delete():
    data = request.get_json(silent=True) or {}
    fn = data.get("filename", "")
    folder_path = data.get("folder_path", "")

    if folder_path:
        p = os.path.join(OUTPUT_DIR, folder_path)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    if fn:
        for c in CATEGORIES:
            p = os.path.join(OUTPUT_DIR, c, fn)
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
            p_th = os.path.join(OUTPUT_DIR, c, f"{os.path.splitext(fn)[0]}.thumb.jpg")
            if os.path.exists(p_th):
                try:
                    os.remove(p_th)
                except Exception:
                    pass

    STATE["results"] = [r for r in STATE["results"] if r.get("filename") != fn]
    refresh_state_counts()
    return jsonify({"status": "deleted", "filename": fn})

@app.route("/api/clear", methods=["POST"])
def api_clear():
    STATE["results"] = []
    for c in CATEGORIES:
        cat_dir = os.path.join(OUTPUT_DIR, c)
        if os.path.exists(cat_dir):
            for f in os.listdir(cat_dir):
                p = os.path.join(cat_dir, f)
                try:
                    if os.path.isfile(p):
                        os.remove(p)
                except Exception:
                    pass
    if os.path.exists(MANIFEST_JSON):
        os.remove(MANIFEST_JSON)
    if os.path.exists(MANIFEST_CSV):
        os.remove(MANIFEST_CSV)
    if os.path.exists(FEEDBACK_JSON):
        os.remove(FEEDBACK_JSON)
    if os.path.exists(FEEDBACK_CSV):
        os.remove(FEEDBACK_CSV)
    if os.path.exists(FEEDBACK_MD):
        os.remove(FEEDBACK_MD)

    refresh_state_counts()
    return jsonify({"status": "cleared"})

# ── NLE TIMELINE GENERATORS (EDL, FCPXML, PREMIERE) ──────────────────────────
def format_timecode_edl(seconds: float, fps: int = 24) -> str:
    total_frames = int(round(seconds * fps))
    ff = total_frames % fps
    total_secs = total_frames // fps
    ss = total_secs % 60
    total_mins = total_secs // 60
    mm = total_mins % 60
    hh = total_mins // 60
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"

def generate_cmx3600_edl(clips: List[Dict[str, Any]], fps: int = 24) -> str:
    lines = [
        "TITLE: CLIPSORT_AI_V3_TIMELINE",
        "FCM: NON-DROP FRAME",
        ""
    ]
    rec_in = 0.0
    for idx, c in enumerate(clips, 1):
        st = float(c.get("start", 0.0))
        dur = float(c.get("duration", 0.0))
        et = float(c.get("end", st + dur))
        rec_out = rec_in + dur

        src_in = format_timecode_edl(st, fps)
        src_out = format_timecode_edl(et, fps)
        r_in = format_timecode_edl(rec_in, fps)
        r_out = format_timecode_edl(rec_out, fps)

        fn = c.get("filename", "")
        cat = c.get("category", "")
        role = c.get("visual_role", cat)
        narrative = c.get("narrative_function", "CORE_BODY")
        quality = c.get("quality_score", 0.90)

        lines.append(f"{idx:03d}  AX       V     C        {src_in} {src_out} {r_in} {r_out}")
        lines.append(f"* FROM CLIP NAME: {fn}")
        lines.append(f"* CATEGORY: {cat} | ROLE: {role} | NARRATIVE: {narrative} | QUALITY: {quality}")
        lines.append("")
        rec_in = rec_out

    return "\n".join(lines)

def generate_fcpxml_18(clips: List[Dict[str, Any]], fps: int = 24) -> str:
    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE fcpxml>',
        '<fcpxml version="1.8">',
        '  <resources>',
        f'    <format id="r1" name="FFVideoFormat1080p{fps}" frameDuration="1/{fps}s" width="1920" height="1080"/>',
        '  </resources>',
        '  <library>',
        '    <event name="ClipSort AI V3 Library">',
        '      <project name="ClipSort AI Timeline">',
        '        <sequence format="r1">',
        '          <spine>'
    ]
    for c in clips:
        st = float(c.get("start", 0.0))
        dur = float(c.get("duration", 0.0))
        cat = c.get("category", "")
        fn = c.get("filename", "")
        role = c.get("visual_role", "")
        narrative = c.get("narrative_function", "")
        quality = c.get("quality_score", 0.90)
        xml.append(f'            <clip name="{cat} - {fn}" offset="{st:.2f}s" duration="{dur:.2f}s" start="{st:.2f}s">')
        xml.append(f'              <note>Category: {cat}, Role: {role}, Narrative: {narrative}, Quality: {quality}</note>')
        xml.append('            </clip>')
    xml.extend([
        '          </spine>',
        '        </sequence>',
        '      </project>',
        '    </event>',
        '  </library>',
        '</fcpxml>'
    ])
    return "\n".join(xml)

def generate_premiere_marker_csv(clips: List[Dict[str, Any]], fps: int = 24) -> str:
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Marker Name", "Description", "In", "Out", "Duration", "Marker Type"])
    for c in clips:
        st_tc = format_timecode_edl(float(c.get("start", 0.0)), fps)
        et_tc = format_timecode_edl(float(c.get("end", 0.0)), fps)
        dur_tc = format_timecode_edl(float(c.get("duration", 0.0)), fps)
        name = f"{c.get('category')} - {c.get('visual_role', '')}"
        desc = f"Narrative: {c.get('narrative_function')} | Conf: {c.get('confidence')} | Quality: {c.get('quality_score')}"
        writer.writerow([name, desc, st_tc, et_tc, dur_tc, "Comment"])
    return output.getvalue()

@app.route("/api/export-zip", methods=["GET"])
def api_export_zip():
    zip_path = os.path.join(BASE_DIR, "clipsort_sorted_export.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for cat in CATEGORIES:
            cat_dir = os.path.join(OUTPUT_DIR, cat)
            if os.path.exists(cat_dir):
                for file in os.listdir(cat_dir):
                    if not file.endswith(".thumb.jpg") and not file.startswith("."):
                        full_p = os.path.join(cat_dir, file)
                        zipf.write(full_p, f"{cat}/{file}")
        if os.path.exists(MANIFEST_JSON):
            zipf.write(MANIFEST_JSON, "manifest.json")
        if os.path.exists(MANIFEST_CSV):
            zipf.write(MANIFEST_CSV, "manifest.csv")
        if os.path.exists(FEEDBACK_MD):
            zipf.write(FEEDBACK_MD, "FEEDBACK_LOG.md")

        if STATE["results"]:
            edl_content = generate_cmx3600_edl(STATE["results"])
            zipf.writestr("timeline_davinci_resolve.edl", edl_content)
            fcpxml_content = generate_fcpxml_18(STATE["results"])
            zipf.writestr("timeline_final_cut_pro.fcpxml", fcpxml_content)
            prem_content = generate_premiere_marker_csv(STATE["results"])
            zipf.writestr("timeline_premiere_markers.csv", prem_content)

    if os.path.exists(zip_path):
        return send_file(zip_path, as_attachment=True, download_name="clipsort_sorted_export.zip")
    return ("No export zip available", 404)

@app.route("/api/export/edl", methods=["GET"])
def api_export_edl():
    content = generate_cmx3600_edl(STATE["results"])
    return Response(content, mimetype="text/plain", headers={"Content-Disposition": "attachment; filename=timeline_davinci.edl"})

@app.route("/api/export/fcpxml", methods=["GET"])
def api_export_fcpxml():
    content = generate_fcpxml_18(STATE["results"])
    return Response(content, mimetype="application/xml", headers={"Content-Disposition": "attachment; filename=timeline_fcp.fcpxml"})

@app.route("/api/export/premiere-csv", methods=["GET"])
def api_export_premiere_csv():
    content = generate_premiere_marker_csv(STATE["results"])
    return Response(content, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=timeline_premiere_markers.csv"})

@app.route("/api/export-project-zip", methods=["GET"])
def api_export_project_zip():
    pkg_zip = os.path.join(BASE_DIR, "clipsort_ai_v3_master_project.zip")
    if os.path.exists(pkg_zip):
        return send_file(pkg_zip, as_attachment=True, download_name="clipsort_ai_v3_master_project.zip")
    return ("Project zip not found", 404)

@app.route("/api/download-vercel-zip", methods=["GET"])
def api_download_vercel_zip():
    pkg_zip = os.path.join(BASE_DIR, "clipsort_vercel_github_deployment.zip")
    if os.path.exists(pkg_zip):
        return send_file(pkg_zip, as_attachment=True, download_name="clipsort_vercel_github_deployment.zip")
    return ("Deployment zip not found", 404)

@app.route("/api/download-logic-pdf", methods=["GET"])
def api_download_logic_pdf():
    pdf_path = os.path.join(BASE_DIR, "video_sorting_logic.pdf")
    if os.path.exists(pdf_path):
        return send_file(pdf_path, as_attachment=True, download_name="video_sorting_logic.pdf")
    return ("Logic PDF not found", 404)

@app.route("/output/<path:filename>")
def serve_output(filename):
    direct_p = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(direct_p) and os.path.isfile(direct_p):
        return send_from_directory(os.path.dirname(direct_p), os.path.basename(direct_p))

    for c in CATEGORIES:
        sub_p = os.path.join(OUTPUT_DIR, c, filename)
        if os.path.exists(sub_p) and os.path.isfile(sub_p):
            return send_from_directory(os.path.join(OUTPUT_DIR, c), filename)

    if filename.endswith(".thumb.jpg"):
        base_video_fn = filename.replace(".thumb.jpg", ".mp4")
        for c in CATEGORIES:
            possible_video = os.path.join(OUTPUT_DIR, c, os.path.basename(base_video_fn))
            if os.path.exists(possible_video):
                target_thumb = os.path.join(OUTPUT_DIR, c, os.path.basename(filename))
                if extract_snapshot_jpg(possible_video, target_thumb, 0.5):
                    return send_from_directory(os.path.dirname(target_thumb), os.path.basename(target_thumb))

    return ("File not found", 404)

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if FRONTEND_DIST and os.path.exists(os.path.join(FRONTEND_DIST, path)) and path != "":
        return send_from_directory(FRONTEND_DIST, path)
    if FRONTEND_DIST and os.path.exists(os.path.join(FRONTEND_DIST, "index.html")):
        return send_from_directory(FRONTEND_DIST, "index.html")
    return "<h2>ClipSort AI Master Engine Running (Specification V2.2)</h2>"

# ── ENTRY POINT ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5005))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"\n==================================================================")
    print(f"[ClipSort AI V6.0] Output Directory: {OUTPUT_DIR}")
    print(f"[ClipSort AI V6.0] Definitive 6-Category Engine at: http://localhost:{port}")
    print(f"==================================================================\n")
    app.run(host=host, port=port, debug=False)
