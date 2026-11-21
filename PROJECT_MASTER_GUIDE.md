# ⚡ ClipSort AI — Master Project Documentation & Technical Reference

> **Comprehensive Technical Guide, Architecture Blueprint, Specification Rules, and Operational Manual**  
> **Engine Version:** 5.0.0 (Specification V2.0 Compliant)  
> **Host Server:** `http://localhost:5005`  
> **Workspace Directory:** `./clipsort-ai-video-studio`

---

## 📑 Table of Contents
1. [Project Overview & Objectives](#1-project-overview--objectives)
2. [System Architecture & Technology Stack](#2-system-architecture--technology-stack)
3. [Specification Rules & Classification Priority Matrix](#3-specification-rules--classification-priority-matrix)
4. [Deep Dive: All 5 Video Categories](#4-deep-dive-all-5-video-categories)
5. [Core Algorithmic Engines & Pipelines](#5-core-algorithmic-engines--pipelines)
   - [Editing Joint & Jump Cut Pre-Scanner](#51-editing-joint--jump-cut-pre-scanner)
   - [A-Roll Continuity Synthesis](#52-a-roll-continuity-synthesis)
   - [Per-Category Scene Deduplication & Non-Repetition](#53-per-category-scene-deduplication--non-repetition)
   - [Lossless Cutting & Web-Compatible Fallback](#54-lossless-cutting--web-compatible-fallback)
6. [Complete REST API Reference](#6-complete-rest-api-reference)
7. [User Interface & Operations Guide](#7-user-interface--operations-guide)
8. [Feedback Logging & Quality Review System](#8-feedback-logging--quality-review-system)
9. [Project Directory Layout & File Inventory](#9-project-directory-layout--file-inventory)
10. [Setup, Execution & Maintenance Guide](#10-setup-execution--maintenance-guide)

---

## 1. Project Overview & Objectives

**ClipSort AI** is an autonomous, multi-modal video processing engine and studio application designed to ingest raw or long-form video footage, detect internal editing joints, classify individual scenes into standardized video production categories, and automatically organize the segmented clips into dedicated category subfolders on disk.

### 🎯 Key Goals:
- **Intelligent Scene Segmentation:** Automatically identify cuts, camera angle changes, and jump cuts to preserve atomic takes without manual timeline cutting.
- **Multi-Modal AI Classification:** Combine **Computer Vision** (face tracking, head yaw, eye gaze, optical flow motion, negative space), **Audio/Speech NLP** (`faster-whisper` transcription, command verb/platform noun scanning), and **Temporal Rules** to categorize takes accurately.
- **A-Roll Continuity Preservation:** Merge continuous dialogue takes across natural speech pauses while strictly breaking at true editing cuts.
- **Zero-False-Alarm CTA & Outro Logic:** Prevent regular narrative dialogue or background scenery from falsely triggering conversion actions; generate `.jpg` endscreen snapshots only for genuine outro brand cards.
- **Singular Server Architecture:** Serve the entire modern web UI, REST API, feedback logger, and video streaming backend from a single unified localhost port (`5005`).

---

## 2. System Architecture & Technology Stack

```
                                  +-------------------------------------------------------+
                                  |                 ClipSort AI Web Studio                |
                                  |         (HTML5 / CSS3 / Vanilla JavaScript ES6)       |
                                  +---------------------------+---------------------------+
                                                              | HTTP / REST (Port 5005)
                                                              v
+-------------------------------------------------------------------------------------------------------------------------+
|                                              Flask Python Master Engine                                                 |
|                                            (clipsort_engine_master.py)                                                  |
+------------------------------------+------------------------------------+-----------------------------------------------+
|        Computer Vision Layer       |         Audio / Speech Layer       |             FFmpeg Processing Layer           |
+------------------------------------+------------------------------------+-----------------------------------------------+
| • OpenCV VideoCapture & Telemetry  | • Faster-Whisper (tiny int8)       | • Lossless Stream Copying (-c copy)           |
| • Haar Frontal Face & HSV Skin     | • Speech-to-Text Transcription     | • Ultrafast H.264 Web Re-Encode Fallback      |
| • Head Yaw & Lens Gaze Directness  | • Lexical Pattern Matcher (Regex)  | • High-Resolution JPG Snapshot Extraction     |
| • 32-Bin Color Histograms          | • Interrogative & Imperative NLP   | • ZIP Archive Bundler (manifest + clips)      |
| • Optical Flow & Motion Variance   | • Outro Semantics Analyzer         | • Manifest Synchronizer (JSON + CSV)          |
+------------------------------------+------------------------------------+-----------------------------------------------+
                                                              |
                                                              v
+-------------------------------------------------------------------------------------------------------------------------+
|                                                Physical Output Directory                                                |
|                                       (/backend/output/ and /backend/temp/)                                             |
|                                                                                                                         |
|  📁 HOOKS/        📁 A_ROLLS/        📁 B_ROLLS/        📁 CTA/        📁 ENDSCREENS/ (.jpg)                            |
|  📄 manifest.json 📄 manifest.csv    📄 user_feedback.json             📄 FEEDBACK_LOG.md                               |
+-------------------------------------------------------------------------------------------------------------------------+
```

### 🛠️ Core Technologies:
1. **Python 3.11 Environment:** Isolated virtual environment (`.venv`) for maximum stability.
2. **Flask & Flask-CORS:** Lightweight REST backend serving web pages and API endpoints.
3. **OpenCV (`cv2`):** Real-time frame decoding, histogram correlation, facial feature extraction, and motion variance calculations.
4. **Faster-Whisper:** Hardware-accelerated Whisper speech-to-text inference for precise sentence boundary detection and spoken keyword extraction.
5. **FFmpeg:** High-performance media utility for frame-accurate sub-second trimming and thumbnail generation.
6. **Concurrent ThreadPoolExecutor:** Multi-threaded parallel clip extraction for sub-second sorting throughput.

---

## 3. Specification Rules & Classification Priority Matrix

ClipSort AI enforces the **Version 3.0 Dual-Track Architecture**, combining an orthogonal visual layer (`A_ROLL`, `B_ROLL`, `GRAPHICS_SLATE`, `OUTTAKE`) with a narrative function layer (`HOOK`, `BODY`, `CTA`, `ENDSCREEN`, `SPONSOR`, `DEAD_AIR`), while assigning a primary physical category:

```
+-------------------------------------------------------------------------+
|                        CLASSIFICATION PRIORITY                          |
+-------------------------------------------------------------------------+
|  1. HOOKS      (Threshold >= 75% | Priority 1 - Narrative Opening)      |
|        │                                                                |
|        ▼ (If not qualified)                                             |
|  2. ENDSCREENS (Threshold >= 70% | Priority 2 - Dual Video + Poster)    |
|        │                                                                |
|        ▼ (If not qualified)                                             |
|  3. CTA        (Threshold >= 70% | Priority 3 - Flexible Timeline)      |
|        │                                                                |
|        ▼ (If not qualified)                                             |
|  4. A_ROLLS    (Threshold >= 70% | Priority 4 - Talking Head Spine)     |
|        │                                                                |
|        ▼ (If not qualified)                                             |
|  5. OUTTAKES   (Quality Gate     | Priority 5 - Jerk/Blur/Dead Air)     |
|        │                                                                |
|        ▼ (If clean and usable)                                          |
|  6. B_ROLLS    (Threshold >= 65% | Priority 6 - Intentional Cutaways)   |
+-------------------------------------------------------------------------+
```

### 📊 Parameter & Threshold Comparison Matrix (Specification V3.0)

| Category | Priority | Qualification Threshold | Duration Range | Output Format | Primary Visual & NLP Markers | Output Folder |
| :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| **🎣 HOOK** | **1** | **$\ge 75\%$** | **$2.0 - 18.0\text{s}$** | `.mp4` Video | Direct eye contact ($\ge 25\% - 90\%$), opening window ($0.0\text{s}$), curiosity & setup triggers (`"Did you know"`, `"POV"`, `"Stop scrolling"`). | `backend/output/HOOKS/` |
| **🖼️ ENDSCREEN** | **2** | **$\ge 70\%$** | $0.8 - 25.0\text{s}$ | **Dual: `.mp4` + `.jpg`** | Trailing 10% search window, negative space ($> 40\%$), awkward hold smile, outro sign-off (`"thanks for watching"`, `"see you next time"`). | `backend/output/ENDSCREENS/` |
| **⚡ CTA** | **3** | **$\ge 70\%$** | $1.5 - 25.0\text{s}$ | `.mp4` Video | Explicit imperative verbs (`"click"`, `"buy"`, `"order"`), platform nouns (`"subscribe"`, `"follow"`, `"link in bio"`), flexible placement (early hook, mid-roll, pre-outro). | `backend/output/CTA/` |
| **🗣️ A-ROLL** | **4** | **$\ge 70\%$** | $1.5 - 120.0\text{s}$ | `.mp4` Video | Primary narrative dialogue, continuous speech monologue, frontal face ($\ge 20\%$), head yaw ($\le 38^\circ$). Merged across continuous speech. | `backend/output/A_ROLLS/` |
| **🗑️ OUTTAKES** | **5** | **$\ge 60\%$** | $0.5 - 60.0\text{s}$ | `.mp4` Quarantined | Severe motion jitter ($> 35.0$), prolonged dead air ($> 2.5\text{s}$), verbal retakes (`"wait"`, `"take two"`, `"cut"`). Protects B-Roll purity. | `backend/output/OUTTAKES/` |
| **🎬 B-ROLL** | **6** | **$\ge 65\%$** | $1.0 - 30.0\text{s}$ | `.mp4` Video | Intentional visual cutaways, product demonstrations, screens, landscapes, smooth camera motion ($1.2\times - 2.5\times$), verified quality score $\ge 0.50$. | `backend/output/B_ROLLS/` |

---

## 4. Deep Dive: All 5 Video Categories

### 🎣 Category 1: HOOK (High-Energy Opening / Pattern Interrupt)
- **Plain English Purpose:** The opening seconds engineered to grab viewers' attention, generate curiosity, and stop them from scrolling away.
- **Threshold:** $\ge 75\%$ | **Priority:** 1 (Top Priority)
- **Duration Constraint:** **Minimum 3.0 seconds** ($3.0\text{s}$ to $15.0\text{s}$).
- **Search Window:** The very beginning of the source clip ($0.0\text{s}$ up to the opening cut).
- **Linguistic / Speech Triggers:**
  - `"did you know"`, `"stop scrolling"`, `"pov"`, `"the secret to"`, `"here is why"`, `"listen up"`, `"imagine"`, `"what if"`, `"watch this"`, `"before you"`, `"kya aap jante hain"`, `"suno"`.
- **Computer Vision Markers:**
  - Eye Gaze: Directed towards the camera lens $\ge 90\%$ of frames.
  - Framing: Medium close-up crop with centered subject.

---

### 🖼️ Category 2: ENDSCREEN (Outro, UI Overlay Space & Graphic Card)
- **Plain English Purpose:** The closing moments of a video designed for YouTube video card overlays, brand logos, contact details, or lingering farewell poses.
- **Threshold:** $\ge 70\%$ | **Priority:** 2
- **Duration Constraint:** $5.0\text{s}$ to $25.0\text{s}$ (or trailing section).
- **Format:** **High-Resolution `.jpg` Image Snapshot**.
- **Search Window:** Trailing 10% of the video clip.
- **Linguistic / Speech Triggers:**
  - `"thanks for watching"`, `"see you next time"`, `"peace out"`, `"bye"`, `"that is it for today"`, `"next video"`, `"upcoming"`, `"khuda hafiz"`, `"shukriya"`, website URLs (`.com`, `.org`, `www.`).
- **Computer Vision Markers:**
  - Negative Space Ratio $> 40\%$ (subject shifted to side, leaving space for video cards).
  - The "Awkward Hold": Motion variance $< 5\%$ (holding a pose without talking).

---

### ⚡ Category 3: CTA (Call To Action - Audience Conversion)
- **Plain English Purpose:** Moments where the creator explicitly asks the viewer to take an action (subscribe, follow, click link, leave comment, buy product).
- **Threshold:** $\ge 70\%$ | **Priority:** 3
- **Duration Constraint:** $3.0\text{s}$ to $15.0\text{s}$.
- **Linguistic / Speech Triggers:**
  - Imperative Verbs: `"subscribe"`, `"click"`, `"hit the bell"`, `"drop a like"`, `"leave a comment"`, `"buy now"`, `"order now"`, `"sign up"`, `"download free"`, `"use code"`, `"channel ko subscribe karo"`, `"like karo"`, `"share karo"`.
- **Computer Vision Markers:**
  - Pointing gestures toward UI text/button regions.
  - Verified on-screen action badge overlays.

---

### 🗣️ Category 4: A-ROLL (Primary Talking-Head & Core Dialogue)
- **Plain English Purpose:** The core narrative driver where the creator or speaker talks directly to the audience, explaining the subject or delivering an interview.
- **Threshold:** $\ge 70\%$ | **Priority:** 4
- **Duration Constraint:** $3.0\text{s}$ to $120.0\text{s}$.
- **Linguistic / Speech Triggers:**
  - Continuous explanation, storytelling, sentence completions, structured thoughts.
- **Computer Vision Markers:**
  - Face Presence Ratio $\ge 30\%$ across frames.
  - Frontal Head Yaw $\le 30^\circ$ (facing the audience).

---

### 🎬 Category 5: B-ROLL (Supplementary Cutaways & Visuals)
- **Plain English Purpose:** Contextual visual footage used over voiceovers (products, environments, action shots, screens, b-roll footage) where there is no synchronous talking head.
- **Threshold:** $\ge 65\%$ | **Priority:** 5 (Fallback)
- **Duration Constraint:** $2.0\text{s}$ to $30.0\text{s}$.
- **Computer Vision Markers:**
  - Face Presence $< 18\%$ or Profile Yaw $> 45^\circ$.
  - High camera motion / optical flow $> 1.5\times$ baseline.
  - High dominance of objects, screens, keyboards, landscapes.

---

## 5. Core Algorithmic Engines & Pipelines

### 5.1 Editing Joint & Jump Cut Pre-Scanner
The engine analyzes frames at high frequency ($0.25\text{s}$ intervals) using a dual-metric detection model:
1. **Frame Difference:** Mean absolute pixel difference $\Delta_{\text{gray}} \ge 24.0$.
2. **Color Histogram Correlation:** 32-bin normalized HSV/Gray histogram correlation $r < 0.78$.
3. **Face Switch / Scale Jump Cut:** Sudden appearance, disappearance, or $> 40\%$ bounding box area change with $\Delta_{\text{gray}} \ge 14.0$.
4. **Minimum Hook Rule:** Cut points occurring before $3.0\text{s}$ are merged into the opening take to guarantee that the Hook is at least 3 seconds long.

### 5.2 A-Roll Continuity Synthesis
To avoid creating fragmented micro-takes from natural speech pauses:
1. When consecutive scenes are both classified as `A_ROLLS`:
2. The engine tests boundary continuity:
   - Pixel delta $< 18.0$ and color histogram correlation $r \ge 0.80$.
   - Uninterrupted frontal face presence and camera framing.
3. If continuous flow is detected, they are **merged into one unified take** (up to $120\text{s}$).
4. If a real jump cut or angle switch is detected, the break is preserved.

### 5.3 Per-Category Scene Deduplication & Non-Repetition
To prevent identical or near-identical footage from cluttering the editor's bin:
1. Each scene's midpoint is fingerprinted with a normalized 32-bin visual histogram and transcript hash.
2. If a newly evaluated scene in category $C$ has:
   - Visual histogram correlation $r \ge 0.96$ and motion variance delta $< 3.0$, OR
   - Identical spoken dialogue string, OR
   - Overlapping time slice from the same source file,
3. The duplicate is **suppressed and excluded** from being repeated in category $C$.

### 5.4 Lossless Cutting & Web-Compatible Fallback
1. **Pass 1 (Lossless):** `ffmpeg -ss {start} -i {source} -t {duration} -c copy -avoid_negative_ts make_zero {out}` (instantaneous, 0% CPU loss).
2. **Pass 2 (Web Fallback):** If stream copy fails or keyframe alignment fails, triggers `ffmpeg -c:v libx264 -preset ultrafast -crf 22 -c:a aac -movflags +faststart` to guarantee 100% playable web MP4 video.

---

## 6. Complete REST API Reference

The server runs on **Port 5005** (`http://localhost:5005`):

| Endpoint | Method | Payload / Params | Description |
| :--- | :---: | :--- | :--- |
| **`/`** | `GET` | None | Serves the web studio interface (`index.html`). |
| **`/api/info`** | `GET` | None | Returns engine version, status, output folder path, and live category file counts. |
| **`/api/status`** | `GET` | None | Returns real-time processing status, progress percentage, and current result list. |
| **`/api/results`** | `GET` | None | Returns the full list of sorted clips with metadata. |
| **`/api/upload`** | `POST` | `multipart/form-data` (`files`) | Ingests and batch-sorts uploaded video files. |
| **`/api/process-path`** | `POST` | `{"path": "/path/to/videos"}` | Scans a local system directory (e.g. `~/Downloads`) and sorts all video files. |
| **`/api/generate-demo`** | `POST` | None | Generates a 24s synthetic test video covering all 5 categories for automated testing. |
| **`/api/export-zip`** | `GET` | None | Downloads a structured `.zip` containing all sorted category folders and manifests. |
| **`/api/feedback`** | `GET` | None | Returns all logged feedback entries in JSON. |
| **`/api/feedback`** | `POST` | `{"filename", "category", "rating", "suggested_category", "comment"}` | Saves feedback into `FEEDBACK_LOG.md`, `user_feedback.json`, and `user_feedback.csv`. |
| **`/api/feedback/export-md`** | `GET` | None | Downloads `FEEDBACK_LOG.md`. |
| **`/api/feedback/export-csv`** | `GET` | None | Downloads `user_feedback.csv`. |
| **`/api/delete`** | `POST` | `{"filename", "folder_path"}` | Deletes a specific clip from disk and removes it from the results state. |
| **`/api/clear`** | `POST` | None | Wipes all sorted clips and manifests from output folders. |
| **`/output/<cat>/<file>`** | `GET` | URL parameter | Direct streaming endpoint for video playback and image previews. |

---

## 7. User Interface & Operations Guide

### 🖥️ Using the Web Studio
1. Open **[http://localhost:5005](http://localhost:5005)** in any web browser.
2. **Ingest Footage:**
   - **Method A:** Click or drag-and-drop video files into the upload box.
   - **Method B:** Enter a directory path (e.g. `~/Downloads`) in the text box and click **"Sort Folder"**.
   - **Method C:** Click **"⚡ Demo"** in the topbar to test all 5 categories with synthetic video.
3. **Filter & Review Clips:**
   - Click the category filter tabs (`All`, `🎣 Hooks`, `🗣️ A-Rolls`, `🎬 B-Rolls`, `⚡ CTA`, `🖼️ Endscreens`).
   - Play video clips directly in the embedded HTML5 player.
   - Click `.jpg` Endscreens to open the high-resolution lightbox modal.
4. **Export Results:**
   - Click **"📦 Export ZIP"** to download all organized folders as a single archive.
   - Or browse files directly in `./clipsort-ai-video-studio/backend/output/`.

---

## 8. Feedback Logging & Quality Review System

Each result card includes an interactive feedback form:
- **Rating Buttons:** 👍 **Accurate** / 👎 **Inaccurate**
- **Category Suggestion:** Dropdown to propose a corrected classification (`HOOKS`, `A_ROLLS`, `B_ROLLS`, `CTA`, `ENDSCREENS`).
- **Review Notes:** Custom text area for timing corrections, joint adjustments, or commentary.
- **Centralized Logs:**
  - **`FEEDBACK_LOG.md`**: Human-readable Markdown summary table with timestamps and notes.
  - **`user_feedback.json`**: Structured JSON database.
  - **`user_feedback.csv`**: Spreadsheet format for tracking model accuracy over time.
- **UI Viewer:** Click **"📝 Feedback Log"** in the topbar to view all filed feedback in a live modal table or download Markdown/CSV reports.

---

## 9. Project Directory Layout & File Inventory

```
./clipsort-ai-video-studio/
├── clipsort_engine_master.py       # Core Engine (Classification, Telemetry, Whisper, Flask API)
├── generate_sample_videos.py       # Synthetic Multi-Category Test Video Generator
├── run_studio.sh                   # Startup shell script with environment setup
├── PROJECT_MASTER_GUIDE.md         # This Master Documentation File
│
├── frontend/
│   └── dist/
│       ├── index.html              # Minimal Web Studio HTML Layout & Feedback Modals
│       ├── style.css               # Clean Modern Dark Theme Styling
│       └── app.js                  # Single-Page Controller, Polling, and Feedback Handlers
│
├── backend/
│   ├── temp/                       # Temporary staging for uploads & synthetic masters
│   └── output/                     # Physical Category Sorting Destination on Disk
│       ├── HOOKS/                  # 🎣 Opening Hook Videos (.mp4)
│       ├── A_ROLLS/                # 🗣️ Continuous Dialogue & Interview Takes (.mp4)
│       ├── B_ROLLS/                # 🎬 Cutaways, Action, Products, & Visual B-Roll (.mp4)
│       ├── CTA/                    # ⚡ Call-To-Action Conversion Clips (.mp4)
│       ├── ENDSCREENS/             # 🖼️ Brand Outro & Social Card Snapshots (.jpg)
│       ├── manifest.json           # Machine-readable inventory of all sorted clips
│       ├── manifest.csv            # Spreadsheet inventory of all sorted clips
│       ├── user_feedback.json      # Structured user feedback database
│       ├── user_feedback.csv       # Spreadsheet user feedback log
│       └── FEEDBACK_LOG.md         # Formatted Markdown Review Log
│
└── .venv/                          # Python 3.11 Virtual Environment (OpenCV, Whisper, Flask)
```

---

## 10. Setup, Execution & Maintenance Guide

### 🚀 Starting the Server:
```bash
cd ./clipsort-ai-video-studio
./run_studio.sh
```

### 🔍 Verifying Server Health:
```bash
curl -s http://localhost:5005/api/info
```

### 🧪 Running Automated Verification via Python:
```bash
cd ./clipsort-ai-video-studio
source .venv/bin/activate
python -c "
from clipsort_engine_master import classify_and_sort_video, OUTPUT_DIR
res = classify_and_sort_video('~/Downloads/BST_CBO001-0812_19_08_2026.mp4', OUTPUT_DIR)
print(f'Successfully sorted {len(res)} clips!')
"
```

### 🧹 Clearing Output Files:
Click **"🗑️"** in the web studio UI, or trigger via terminal:
```bash
curl -s -X POST http://localhost:5005/api/clear
```

---
*Documentation compiled and verified for ClipSort AI Engine V5.0.*
