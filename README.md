# ClipSort AI — Multimodal Video Segmentation & Classification Studio

Automated computer-vision + speech-NLP studio that parses raw long-form shoot footage into **6 contiguous editorial categories** (`HOOKS`, `A_ROLLS`, `B_ROLLS`, `CTA`, `ENDSCREENS`, `OUTTAKES`) with full timeline coverage, zero dropped frames, and lossless FFmpeg `-c copy` cutting — reducing manual video curation time by ~70%.

## Architecture & Signals
- **Computer Vision (OpenCV):** Haar face & HSV skin tracking, head yaw/gaze estimation, 32-bin histogram cut detection, and optical flow motion scoring.
- **Speech NLP (Faster-Whisper Int8):** Local transcription and semantic cue detection for hooks, calls-to-action, and speech/silence boundaries.
- **Lossless Export Pipeline:** Parallel `ThreadPoolExecutor` processing with FFmpeg stream-copy cutting and interactive web studio (`http://localhost:5005`).

## Tech Stack
Python · Flask · OpenCV · Faster-Whisper (Int8) · FFmpeg · NumPy

## Quick Start
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Ensure ffmpeg is installed (e.g., brew install ffmpeg)
python run_studio.py
# Open http://localhost:5005
```

See [PROJECT_MASTER_GUIDE.md](PROJECT_MASTER_GUIDE.md) and [video_sorting_logic.md](video_sorting_logic.md) for detailed classification heuristics.
