# AI Video Classification & Categorization Logic Specification

**Version:** 3.0.0  
**Architecture:** Dual-Track Multi-Dimensional Classification  
**Status:** Production-Ready  
**Core Guarantees:** 100% Contiguous Timeline Coverage [0.0s to T] • Max Gap: 0.0s • B-Roll Integrity Protected via Outtake Quality Gate

---

## 1. Dual-Track Classification Architecture

Every frame and take is evaluated across two synchronized dimensions:

### 1.1 Dimension 1: Visual Asset Layer
Physical camera and subject composition:
- **`A_ROLL`**: Subject talking head facing camera, synchronous dialogue, or interview framing.
- **`B_ROLL`**: Intentional supplementary visual cutaway, product demonstration, environment, or cinematic movement.
- **`GRAPHICS_SLATE`**: Title slate, brand logo, full-screen text, or color card.
- **`SCREENCAST`**: Screen recordings or software demonstrations.
- **`OUTTAKE`**: Unusable footage, camera jerks, flubbed lines, or dead air quarantined to prevent polluting B-Roll.

### 1.2 Dimension 2: Narrative & Editorial Layer
Storytelling function and viewer engagement role:
- **`HOOK`**: Scroll-stopping opening moments delivering premise, problem, or intrigue.
- **`CORE_BODY`**: Central narrative, storytelling explanation, or interview delivery.
- **`CTA` (Call To Action)**: Conversion prompts directing viewers to subscribe, buy, or visit.
- **`ENDSCREEN`**: Closing moments reserved for clickable video cards, channel subscribe logos, or outro slates.
- **`SPONSOR`**: Dedicated brand sponsorship reads or partner promos.
- **`DEAD_AIR`**: Pauses, camera resets, or unusable silence before or after takes.

---

## 2. Priority Hierarchy & Decision Arbitration

When any contiguous video segment is evaluated, classification resolves in this strict priority order:

> **`HOOKS` ➔ `ENDSCREENS` ➔ `CTA` ➔ `A_ROLLS` ➔ `OUTTAKES` ➔ `B_ROLLS` (Fallback)**

1. **`HOOKS` (Priority 1 — Threshold ≥ 75%)**: Opening capture window.
2. **`ENDSCREENS` (Priority 2 — Threshold ≥ 70%)**: Outro card / farewell hold (only if present in footage).
3. **`CTA` (Priority 3 — Threshold ≥ 70%)**: Conversion moments (flexible anywhere on timeline).
4. **`A_ROLLS` (Priority 4 — Threshold ≥ 70%)**: Talking-head narrative spine.
5. **`OUTTAKES` (Priority 5 — Threshold ≥ 60%)**: Unusable footage quarantined to protect B-Roll.
6. **`B_ROLLS` (Priority 6 — Threshold ≥ 65%)**: Clean, intentional visual cutaways and guaranteed fallback.

---

## 3. Detailed Category Specifications

---

### 🎣 1. HOOKS (Priority 1)
- **Qualification Threshold**: ≥ 75% Confidence
- **Primary Layer**: Narrative Function (`HOOK`)
- **Export Format**: Video MP4 with Web Poster Thumbnail
- **Temporal Rules**:
  - Search Window: 0.0s to first scene transition (max 18.0s).
  - Minimum Duration: 2.0s (recommended 3.0s).
  - Maximum Duration: 18.0s.
  - Fade Absorption Cutoff: 2.5s (absorbs opening black frames / fades into the hook).
- **Computer Vision (CV) Signals**:
  - Direct Lens Gaze Ratio: ≥ 0.25 (optimal ≥ 0.90).
  - Framing: Medium close-up or close-up portrait framing.
  - Motion Energy: High dynamic entry into frame or visual pattern interrupt.
- **Speech & Linguistic (NLP) Signals**:
  - Narrative Role: Premise setup, curiosity gap, interrogative opening.
  - Multilingual Keywords: `"did you know"`, `"stop scrolling"`, `"pov"`, `"the secret to"`, `"here is why"`, `"listen up"`, `"imagine"`, `"what if I told you"`, `"what if"`, `"why do"`, `"how to"`, `"watch this"`, `"before you"`, `"never do this"`, `"you won't believe"`, `"the real reason"`, `"in this video"`, `"welcome back"`, `"hey guys"`, `"kya aap jante"`, `"aaj hum"`, `"yeh dekho"`, `"suno"`, `"wait until you see"`, `"this is why"`, `"here's the thing"`, `"let me explain"`, `"number one"`.

---

### 🖼️ 2. ENDSCREENS (Priority 2)
- **Qualification Threshold**: ≥ 70% Confidence
- **Primary Layer**: Hybrid (`GRAPHICS_SLATE` / `A_ROLL` + `ENDSCREEN`)
- **Export Format**: Dual Export — BOTH Video `.mp4` and High-Res Image Snapshot `.jpg`
- **Presence Rule**: Only classified if video actually contains an outro card or farewell hold.
- **Temporal Rules**:
  - Search Window: Terminal segment (`et >= TotalDuration - 0.5s` or final 10% of timeline).
  - Duration Range: 0.8s to 25.0s.
- **Detection Criteria**:
  - Solid White Slate: Mean brightness ≥ 210.0 and std deviation ≤ 25.0.
  - Solid Dark Slate: Mean brightness ≤ 15.0 and std deviation ≤ 25.0.
  - The "Awkward Hold": Presenter holds static pose leaving empty room for video cards (motion variance ≤ 5.0, negative space ratio ≥ 0.40).
  - Outro Speech Keywords: `"thanks for watching"`, `"thank you for watching"`, `"thank you"`, `"see you in the next one"`, `"see you next time"`, `"until next time"`, `"peace out"`, `"peace"`, `"take care"`, `"that wraps it up"`, `"that's all for today"`, `"stay tuned"`, `"endscreen"`, `"outro"`, `"shukriya"`, `"khuda hafiz"`, `"alvida"`, `"fir milenge"`.

---

### ⚡ 3. CTA — CALL TO ACTION (Priority 3)
- **Qualification Threshold**: ≥ 70% Confidence
- **Primary Layer**: Narrative Function (`CTA`)
- **Export Format**: Video MP4 with Web Poster Thumbnail
- **Temporal Rules**:
  - Search Window: Flexible across the timeline (Early Hook, Mid-Roll, or Pre-Outro).
  - Duration Range: 1.5s to 25.0s.
- **Detection Criteria**:
  - Imperative Action Keywords: `"subscribe"`, `"hit that subscribe"`, `"drop a like"`, `"leave a comment"`, `"comment down below"`, `"link in bio"`, `"link in description"`, `"check the link"`, `"click the link"`, `"download free"`, `"download"`, `"join community"`, `"use code"`, `"sign up"`, `"visit website"`, `"follow for more"`, `"follow me"`, `"share this"`, `"tap the bell"`, `"buy now"`, `"order now"`, `"shop now"`, `"follow for part 2"`, `"like karo"`, `"share karo"`, `"subscribe karo"`, `"channel ko"`, `"comment karo"`, `"stream now"`, `"watch now"`, `"in theaters"`, `"out now"`, `"get yours"`.
  - Computer Vision: Pointing gestures toward UI borders, lower-thirds, or bio links; on-screen typography containing conversion links or promo codes.

---

### 🗣️ 4. A_ROLLS (Priority 4)
- **Qualification Threshold**: ≥ 70% Confidence
- **Primary Layer**: Visual Asset (`A_ROLL`)
- **Export Format**: Video MP4 with Web Poster Thumbnail
- **Temporal Rules**:
  - Duration Range: 1.5s to 120.0s.
  - Monologue Consolidation: Continuous speech takes across brief pauses (up to 0.35s) without camera angle cuts are consolidated into cohesive takes.
- **Computer Vision (CV) Signals**:
  - Face Presence Ratio: ≥ 0.20 of sampled frames.
  - Head Yaw: ≤ 38.0° (subject facing front toward camera/audience).
  - Framing: Medium shot or talking head facing audience.
- **Acoustic Signals**:
  - Continuous dialogue, synchronous speech.

---

### ⚠️ 5. OUTTAKES (Priority 5 — Quality Gate Layer)
- **Qualification Threshold**: ≥ 60% Confidence
- **Primary Layer**: Quality Gate (`OUTTAKE`)
- **Export Format**: Video MP4 Quarantined
- **Primary Function**: Quarantines unusable, damaged, or flubbed footage to protect B-Roll purity.
- **Detection Criteria**:
  - Camera Jerk Motion: Average motion difference ≥ 35.0 (erratic shake, accidental whip pan, ground drops).
  - Dead Air / Frozen Rig: Motion variance ≤ 0.8 with duration ≥ 2.5s without speech.
  - Verbal Retake Keywords: Spoken flub phrases: `"wait"`, `"let me restart"`, `"take two"`, `"cut"`, `"hold on"`, `"scratch that"`, `"my bad"`, `"start over"`.
  - Quality Score: Low quality rating (< 0.50).

---

### 🎬 6. B_ROLLS (Priority 6 — Guaranteed Clean Fallback)
- **Qualification Threshold**: ≥ 65% Confidence
- **Primary Layer**: Visual Asset (`B_ROLL`)
- **Export Format**: Video MP4 with Web Poster Thumbnail
- **Primary Function**: Clean, intentional supplementary visual cutaways and cinematic footage.
- **Temporal Rules**:
  - Duration Range: 1.0s to 30.0s.
- **Computer Vision (CV) Signals**:
  - Face Presence: Low face ratio (≤ 0.20) or no face.
  - Head Pose: Profile view (yaw ≥ 45.0°).
  - Camera Motion Multiplier: 1.2× to 2.5× baseline (smooth pans, tracking, or handheld movement).
  - Object Dominance: Hands, products, screens, clothing, environments, landscapes.
- **Quality Gate Integration**:
  - Requires Quality Score ≥ 0.50 (all outtakes and camera jerks are filtered out into `OUTTAKES`).
  - Serves as the guaranteed fallback for all clean footage so 100% of the timeline is covered.

---

## 4. Scene Cut & Joint Detection Metrics

Scene boundaries are calculated using dual-modality computer vision and audio VAD:

1. **Pixel-Level Absolute Motion Difference**:
   - Formula: `Δ_motion = (1 / (W × H)) × Σ |I_t(x, y) - I_{t-1}(x, y)|`
   - Cut Threshold: **Δ_motion ≥ 22.0**.
2. **Normalized Color Histogram Correlation**:
   - Formula: `r(H₁, H₂) = Cov(H₁, H₂) / (Std(H₁) × Std(H₂))`
   - Cut Threshold: **r < 0.78**.
3. **Face Transition Cut**:
   - Abrupt appearance or disappearance of a face with **motion diff ≥ 12.0**.
4. **Voice Activity Detection (VAD) Silence Boundaries**:
   - Speech silence gaps (**> 300ms**) align cuts with natural speech pauses to prevent mid-word clipping.

---

## 5. Export Specifications & Manifest Schema

### 5.1 Output Directory Structure
```
backend/output/
├── HOOKS/
├── A_ROLLS/
├── B_ROLLS/
├── CTA/
├── ENDSCREENS/
└── OUTTAKES/
```

### 5.2 Manifest Fields
The export manifest files (`manifest.json` and `manifest.csv`) include:
- `category`: Primary classification category.
- `visual_role`: Visual layer (`A_ROLL`, `B_ROLL`, `GRAPHICS_SLATE`, `OUTTAKE`).
- `narrative_function`: Narrative layer (`HOOK`, `CORE_BODY`, `CTA`, `ENDSCREEN`, `DEAD_AIR`).
- `quality_score`: Production quality rating (0.0 to 1.0).
- `filename`: Standardized clip filename.
- `folder_path`: Relative output path.
- `source_video`: Original source filename.
- `start`: Segment start timestamp in seconds.
- `end`: Segment end timestamp in seconds.
- `duration`: Duration in seconds.
- `confidence`: Algorithmic confidence score (0.0 to 1.0).
- `reason`: Explanation of classification decision.

### 5.3 Non-Linear Editor (NLE) Support
- **DaVinci Resolve**: Standard CMX 3600 Edit Decision List (`.edl`).
- **Final Cut Pro**: Apple FCPXML 1.8+ (`.fcpxml`).
- **Adobe Premiere Pro**: Markers CSV (`.csv`).
