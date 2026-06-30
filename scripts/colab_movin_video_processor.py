# Movin Marketing Technology OS — Rich Final Google Colab Video Processor
# Paste this entire file into one Google Colab cell and run it.
# Upload the 4 original Movin recordings. The processor will create GitHub-safe clips under 20MB,
# preserve the full Section 2 lead-generation recording, crop Section 4 meeting video to the product screen,
# and generate assets/video-manifest.json + data/narration.json.

import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

# =========================
# 1) CONFIGURATION
# =========================
TARGET_CLIP_MB = 18.5       # Keep every uploaded clip under 20MB for GitHub web upload.
VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
VIDEO_FPS = 15              # Efficient and readable for screen recordings.
VIDEO_CRF = 31              # Higher = smaller/lower quality. Try 33 or 34 if a clip exceeds 20MB.
BUILD_PREVIEW_MP4 = False   # Set True only if you want Colab to also build a preview MP4.

# Important final fixes:
# - Section 2 uses the full original recording and is slowed into a 120s rich narration section.
# - Section 4 starts after the meeting intro and is cropped to the browser/demo area only.
SEQUENCE_PLAN = [
    {
        "label": "01_aeo_geo_intelligence",
        "chapter": "AEO + GEO Intelligence / Opportunity Engine",
        "match_any": ["06-04", "12.11.10", "12.11", "screen recording 2026-06-04"],
        "fallback_order": 1,
        "start_seconds": 0,
        "target_duration": 108,
        "use_full_remaining_source": False,
        "crop": None,
        "narrationSegmentIds": ["opening", "aeo_geo", "prompt_intelligence", "opportunity_engine"]
    },
    {
        "label": "02_lead_generation",
        "chapter": "WarmLead AI / Lead Generation",
        "match_any": ["06-02", "6.26.34", "6.26", "screen recording 2026-06-02", "lead"],
        "fallback_order": 2,
        "start_seconds": 0,
        "target_duration": 120,
        "use_full_remaining_source": True,
        "crop": None,
        "narrationSegmentIds": ["lead_generation_overview", "lead_signal_sources", "lead_scoring_enrichment", "lead_alerts_workflow", "lead_crm_activation"]
    },
    {
        "label": "03_autonomous_campaigns_syndication",
        "chapter": "Autonomous Campaign Generation + Syndication",
        "match_any": ["elevateos", "campaign", "demo_elevate"],
        "fallback_order": 3,
        "start_seconds": 0,
        "target_duration": 75,
        "use_full_remaining_source": False,
        "crop": None,
        "narrationSegmentIds": ["campaign_generation", "syndication"]
    },
    {
        "label": "04_data_monetization",
        "chapter": "B2B Shipment Data Monetization",
        "match_any": ["de3mo", "meeting recording", "20260609", "data monetization"],
        "fallback_order": 4,
        "start_seconds": 6,
        "target_duration": 90,
        "use_full_remaining_source": True,
        # Crop observed on the meeting recording: removes participant tile and black meeting canvas.
        # If your future recording layout changes, edit this to crop=w:h:x:y, or set to None.
        "crop": "1664:870:0:100",
        "narrationSegmentIds": ["data_monetization_foundation", "data_to_marketplace", "data_commercial_model", "close"]
    }
]

NARRATION_DATA = {
  "title": "Movin Marketing Technology OS — From AI Discovery to Monetized Growth",
  "durationSeconds": 393,
  "segments": [
    {
      "id": "opening",
      "start": 0,
      "end": 18,
      "chapter": "Opening",
      "headline": "Movin’s full-funnel AI growth engine",
      "text": "This walkthrough shows Movin as an AI powered growth operating system. We will move from AI discovery, to buyer intent, to warm lead generation, to autonomous campaigns, to channel syndication, and finally to shipment data monetization. The story is simple: Movin can sense demand, act on demand, convert demand, and monetize the data created by every shipment.",
      "voiceRate": "-8%"
    },
    {
      "id": "aeo_geo",
      "start": 18,
      "end": 50,
      "chapter": "AEO + GEO Intelligence",
      "headline": "Own the answers before buyers reach a website",
      "text": "We begin with AEO and GEO intelligence. Buyers are no longer discovering logistics partners only through search, events or sales calls. They ask ChatGPT, Perplexity, Gemini, Copilot and AI Overviews which logistics provider can handle tracking, cross border movement, last mile reliability, warehousing and freight cost certainty. This command center tells Movin where it appears, where it gets cited, which prompts trigger visibility, which pages are being referenced, and where competitors are being recommended instead.",
      "voiceRate": "-8%"
    },
    {
      "id": "prompt_intelligence",
      "start": 50,
      "end": 81,
      "chapter": "Prompt + Intent Intelligence",
      "headline": "Turn AI questions into a real demand map",
      "text": "The next layer is prompt intelligence. The platform converts customer questions into an intent map: real time shipment tracking, India to UAE freight, enterprise last mile SLA, reverse logistics, fulfilment comparison, cross border ecommerce and pricing transparency. These are not just keywords. They are buying questions. Each prompt is scored for volume, quality of Movin’s answer, competitive risk and recommended action.",
      "voiceRate": "-8%"
    },
    {
      "id": "opportunity_engine",
      "start": 81,
      "end": 108,
      "chapter": "Opportunity Engine",
      "headline": "Convert visibility gaps into execution priorities",
      "text": "The Opportunity Engine then rank orders the actions. It tells marketing what to build, where to build it and why it matters. For example: create an India to UAE lane calculator, strengthen pages around tracking and SLA assurance, publish reverse logistics proof points, or build comparison content where AI engines are already recommending competitors. Movin now has an execution backlog driven by demand signals, not guesswork.",
      "voiceRate": "-8%"
    },
    {
      "id": "lead_generation_overview",
      "start": 108,
      "end": 132,
      "chapter": "Lead Generation",
      "headline": "WarmLead AI turns demand into account lists",
      "text": "Section two is now intentionally richer and longer because this is where Movin moves from insight to revenue. WarmLead AI acts as the revenue sensing layer. It continuously scans companies, signals, contacts and trigger events to identify accounts that are most likely to need Movin’s logistics capabilities now, not six months later.",
      "voiceRate": "-8%"
    },
    {
      "id": "lead_signal_sources",
      "start": 132,
      "end": 156,
      "chapter": "Lead Signal Sources",
      "headline": "Signals come from the market, not only the CRM",
      "text": "The system looks beyond traditional CRM data. It reads company websites, hiring patterns, procurement movements, public announcements, expansion news, LinkedIn activity, logistics forums, funding signals and intent topics. If a business is opening new fulfilment locations, hiring supply chain roles, launching cross border commerce, complaining about delays, or expanding into new lanes, that becomes a lead signal.",
      "voiceRate": "-8%"
    },
    {
      "id": "lead_scoring_enrichment",
      "start": 156,
      "end": 181,
      "chapter": "Lead Scoring + Enrichment",
      "headline": "Fit, intent and timing are scored together",
      "text": "Warm accounts are then scored across three lenses. First, fit: industry, shipment profile, geography and service need. Second, intent: topics they are researching and problems they are signaling. Third, timing: whether a trigger suggests near term buying urgency. The platform enriches contacts, maps decision makers and creates segments that sales can immediately act on.",
      "voiceRate": "-8%"
    },
    {
      "id": "lead_alerts_workflow",
      "start": 181,
      "end": 205,
      "chapter": "Lead Alerts + Workflow",
      "headline": "Marketing and sales get action-ready alerts",
      "text": "The alert layer makes the system operational. Movin teams can see high intent accounts, negative vendor mentions, competitive displacement opportunities, procurement signals and campaign ready audiences. Instead of broad cold outreach, the team gets a prioritized list with the reason to contact, the message angle and the right Movin capability to position.",
      "voiceRate": "-8%"
    },
    {
      "id": "lead_crm_activation",
      "start": 205,
      "end": 228,
      "chapter": "CRM + Sales Activation",
      "headline": "A live revenue signal graph feeds the funnel",
      "text": "The output is not a static spreadsheet. It is a live revenue signal graph. Qualified accounts, contacts, triggers, recommended offers and campaign audiences can be pushed into CRM, outbound sequences, WhatsApp journeys or account based marketing. This is how Movin turns AI discovery and market signals into pipeline creation.",
      "voiceRate": "-8%"
    },
    {
      "id": "campaign_generation",
      "start": 228,
      "end": 273,
      "chapter": "Autonomous Campaign Generation",
      "headline": "Agents build the campaign factory",
      "text": "Once the audience and opportunity are clear, the campaign layer becomes autonomous. The system can generate the campaign objective, target audience, platform mix, budget, duration, offer, creative tone and landing page structure. Multiple agents then work together: competitive intelligence, social listening, opportunity analysis, strategy synthesis, creative generation, budget optimization, pixel setup and launch readiness. Movin can generate campaigns for tracking assurance, India to UAE freight, last mile SLA, reverse logistics and cross border logistics growth.",
      "voiceRate": "-8%"
    },
    {
      "id": "syndication",
      "start": 273,
      "end": 303,
      "chapter": "Campaign Syndication",
      "headline": "One intelligence layer powers every channel",
      "text": "The same intelligence is then syndicated across channels. A prompt gap becomes an AEO page. A buyer question becomes a landing page. A lead signal becomes an outbound sequence. A campaign concept becomes paid social, search, email, WhatsApp and CRM activity. This connects marketing and sales around one operating rhythm: identify demand, create the asset, launch the campaign and route the lead.",
      "voiceRate": "-8%"
    },
    {
      "id": "data_monetization_foundation",
      "start": 303,
      "end": 333,
      "chapter": "Data Monetization",
      "headline": "Shipment data becomes a new commercial layer",
      "text": "Section four focuses only on the Movin product video, with the meeting view cropped out. This is the data monetization layer. Every B2B shipment captures origin, destination, weight, dimensions, category, service level, frequency and procurement context. That information is operationally useful, but it is also commercially valuable because it reveals what the customer is likely to need next.",
      "voiceRate": "-8%"
    },
    {
      "id": "data_to_marketplace",
      "start": 333,
      "end": 363,
      "chapter": "Contextual Marketplace",
      "headline": "Every shipment can trigger relevant offers",
      "text": "When a customer books electronics, components, apparel or industrial goods, Movin can infer adjacent needs: packaging, labels, insurance, pallets, compliance material, warehouse support, freight upgrades or supplier discounts. The platform can recommend the right offer inside the shipping journey itself, not after the customer has left. This creates contextual commerce from logistics metadata.",
      "voiceRate": "-8%"
    },
    {
      "id": "data_commercial_model",
      "start": 363,
      "end": 383,
      "chapter": "Commercial Model",
      "headline": "Movin monetizes intelligence around shipments",
      "text": "The commercial model can include partner funded offers, supplier marketplace revenue, premium logistics add ons, data backed procurement savings and route specific promotions. Movin does not need to sell only transportation. It can monetize the intelligence around transportation, while still improving customer savings and experience.",
      "voiceRate": "-8%"
    },
    {
      "id": "close",
      "start": 383,
      "end": 393,
      "chapter": "Close",
      "headline": "From AI discovery to monetized growth",
      "text": "That is the complete product flow: sense demand, create pipeline, launch campaigns, activate channels and monetize shipment intelligence. This is Movin’s AI powered growth operating system.",
      "voiceRate": "-8%"
    }
  ],
  "intro": {
    "id": "intro",
    "voice": "en-GB-RyanNeural",
    "output": "assets/generated/intro.mp3",
    "text": "Welcome to the Movin Marketing Technology OS. This experience is now optimized for a richer lead generation walkthrough and a focused, cropped data monetization video. Choose a section to explore the product flow."
  },
  "voice": "en-GB-RyanNeural",
  "output": "assets/generated/narration.mp3"
}

# =========================
# 2) INSTALL + HELPERS
# =========================
def run(cmd, check=True, quiet=False):
    print("+", " ".join(map(str, cmd)) if isinstance(cmd, (list, tuple)) else cmd)
    return subprocess.run(cmd, shell=isinstance(cmd, str), check=check, stdout=subprocess.DEVNULL if quiet else None, stderr=subprocess.STDOUT if quiet else None)

run("apt-get -qq update && apt-get -qq install -y ffmpeg", quiet=False)
# edge-tts is only needed if BUILD_PREVIEW_MP4=True or you want narration generated in Colab.
run([sys.executable, "-m", "pip", "install", "-q", "edge-tts", "gTTS"], quiet=False)

ROOT = Path("/content/movin_colab_output")
RAW_DIR = ROOT / "raw_uploads"
WORK_DIR = ROOT / "work"
ASSET_DIR = ROOT / "github_assets"
CLIPS_DIR = ASSET_DIR / "assets" / "clips"
GEN_DIR = ASSET_DIR / "assets" / "generated"
DATA_DIR = ASSET_DIR / "data"
for d in [RAW_DIR, WORK_DIR, CLIPS_DIR, GEN_DIR, DATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def ffprobe_duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], text=True).strip()
    return float(out)


def size_mb(path):
    return Path(path).stat().st_size / (1024 * 1024)


def safe_filter_join(parts):
    return ",".join([p for p in parts if p])


def fit_atempo_chain(factor):
    parts = []
    while factor > 2.0:
        parts.append(2.0)
        factor /= 2.0
    while factor < 0.5:
        parts.append(0.5)
        factor /= 0.5
    parts.append(factor)
    return ",".join(f"atempo={p:.6f}" for p in parts)

# =========================
# 3) UPLOAD THE 4 VIDEOS
# =========================
try:
    from google.colab import files
    print("Upload the 4 original Movin videos now. Select all four together.")
    uploaded = files.upload()
    for name, content in uploaded.items():
        out = RAW_DIR / name
        out.write_bytes(content)
except Exception:
    print("Not running inside Colab upload UI. Put your 4 videos in:", RAW_DIR)

videos = sorted([p for p in RAW_DIR.iterdir() if p.suffix.lower() in [".mp4", ".mov", ".m4v", ".webm", ".mkv"]])
if len(videos) < 4:
    raise SystemExit(f"Expected 4 videos, found {len(videos)} in {RAW_DIR}. Upload all 4 recordings and re-run.")

print("\nUploaded videos:")
for p in videos:
    print(f"- {p.name} | {ffprobe_duration(p):.1f}s | {size_mb(p):.1f} MB")

# =========================
# 4) MAP VIDEOS TO MOVIN STORY SEQUENCE
# =========================
def match_video(plan_item, remaining):
    keys = [k.lower() for k in plan_item["match_any"]]
    for p in remaining:
        name = p.name.lower()
        if any(k in name for k in keys):
            return p
    return None

remaining = videos[:]
assignments = []
for plan in SEQUENCE_PLAN:
    found = match_video(plan, remaining)
    if found is None:
        idx = min(max(plan.get("fallback_order", 1) - 1, 0), len(remaining) - 1)
        found = remaining[idx]
    remaining.remove(found)
    assignments.append((plan, found))

print("\nStory mapping:")
for plan, src in assignments:
    print(f"- {plan['label']}  <=  {src.name}")

# =========================
# 5) CREATE RICH, GITHUB-SAFE CLIPS
# =========================
def build_highlight_clip(src, plan):
    source_duration = ffprobe_duration(src)
    start = float(plan.get("start_seconds", 0))
    target = float(plan["target_duration"])
    available = max(1.0, source_duration - start)
    capture_duration = available if plan.get("use_full_remaining_source") else min(target, available)
    speed_ratio = target / capture_duration

    filters = []
    if plan.get("crop"):
        filters.append(f"crop={plan['crop']}")
    filters.extend([
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease",
        f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2",
        f"fps={VIDEO_FPS}",
        f"setpts={speed_ratio:.8f}*PTS",
        f"tpad=stop_mode=clone:stop_duration=6",
        f"trim=duration={target:.3f}",
        "setpts=PTS-STARTPTS",
        "format=yuv420p"
    ])
    vf = safe_filter_join(filters)
    out = WORK_DIR / f"{plan['label']}_highlight.mp4"

    # Put -ss and -t before -i so ffmpeg limits the source read, not the filtered output.
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", str(start), "-t", f"{capture_duration:.3f}", "-i", str(src),
        "-vf", vf,
        "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", str(VIDEO_CRF),
        "-movflags", "+faststart", str(out)
    ]
    run(cmd)
    print(f"Created highlight: {out.name} | {ffprobe_duration(out):.1f}s | {size_mb(out):.1f} MB | crop={plan.get('crop')}")
    return out


def segment_file(src, label):
    duration = ffprobe_duration(src)
    total_mb = size_mb(src)
    if total_mb <= TARGET_CLIP_MB:
        dest = CLIPS_DIR / f"{label}_part_001.mp4"
        shutil.copy2(src, dest)
        return [dest]

    segment_time = max(8.0, duration * (TARGET_CLIP_MB / total_mb) * 0.82)
    for attempt in range(8):
        pattern = CLIPS_DIR / f"{label}_part_%03d.mp4"
        for old in CLIPS_DIR.glob(f"{label}_part_*.mp4"):
            old.unlink()
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
            "-c", "copy", "-map", "0", "-f", "segment",
            "-segment_time", f"{segment_time:.2f}", "-reset_timestamps", "1",
            "-segment_format", "mp4", "-segment_format_options", "movflags=+faststart", str(pattern)
        ]
        run(cmd)
        parts = sorted(CLIPS_DIR.glob(f"{label}_part_*.mp4"))
        max_mb = max(size_mb(p) for p in parts) if parts else 0
        print(f"Segmentation attempt {attempt+1}: {len(parts)} parts, largest {max_mb:.1f} MB, segment_time {segment_time:.1f}s")
        if parts and max_mb <= TARGET_CLIP_MB:
            return parts
        segment_time *= 0.70

    raise SystemExit(f"Could not split {src.name} below {TARGET_CLIP_MB} MB. Increase VIDEO_CRF or reduce VIDEO_WIDTH/FPS.")

manifest = {
    "version": "2.0-rich-final",
    "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "clipTargetMB": TARGET_CLIP_MB,
    "videoWidth": VIDEO_WIDTH,
    "videoHeight": VIDEO_HEIGHT,
    "videoFPS": VIDEO_FPS,
    "videoCRF": VIDEO_CRF,
    "notes": "Section 2 preserves the full lead-generation recording. Section 4 is cropped to product screen focus only.",
    "clips": []
}

cumulative = 0.0
for order, (plan, src) in enumerate(assignments, start=1):
    highlight = build_highlight_clip(src, plan)
    parts = segment_file(highlight, plan["label"])
    for part_index, part in enumerate(parts, start=1):
        part_duration = ffprobe_duration(part)
        manifest["clips"].append({
            "sequence": len(manifest["clips"]) + 1,
            "src": f"assets/clips/{part.name}",
            "chapter": plan["chapter"],
            "sourceOriginal": src.name,
            "sourceStartSeconds": plan.get("start_seconds", 0),
            "parentLabel": plan["label"],
            "part": part_index,
            "duration": round(part_duration, 3),
            "globalStart": round(cumulative, 3),
            "globalEnd": round(cumulative + part_duration, 3),
            "narrationSegmentIds": plan["narrationSegmentIds"],
            "sizeMB": round(size_mb(part), 2),
            "processing": "full-source-rich-section" if plan.get("use_full_remaining_source") else "highlight-section",
            "crop": plan.get("crop")
        })
        cumulative += part_duration

(ASSET_DIR / "assets" / "video-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
DATA_DIR.mkdir(exist_ok=True, parents=True)
(DATA_DIR / "narration.json").write_text(json.dumps(NARRATION_DATA, indent=2), encoding="utf-8")

print("\nGenerated clip manifest:")
for c in manifest["clips"]:
    print(f"{c['sequence']:02d}. {c['src']} | {c['duration']:.1f}s | {c['sizeMB']:.1f} MB | {c['chapter']}")
print(f"Total story video duration: {cumulative:.1f}s")

# =========================
# 6) OPTIONAL NARRATION/PREVIEW IN COLAB
# =========================
def make_narration_mp3():
    import asyncio
    import edge_tts

    async def synthesize_edge(text, out, rate="+0%"):
        communicate = edge_tts.Communicate(text, voice="en-GB-RyanNeural", rate=rate)
        await communicate.save(str(out))

    parts_dir = GEN_DIR / "narration_parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    fitted = []
    for idx, seg in enumerate(NARRATION_DATA["segments"], start=1):
        target = float(seg["end"] - seg["start"])
        raw = parts_dir / f"{idx:02d}_{seg['id']}_raw.mp3"
        wav = parts_dir / f"{idx:02d}_{seg['id']}_fitted.wav"
        asyncio.run(synthesize_edge(seg["text"], raw, seg.get("voiceRate", "+0%")))
        actual = ffprobe_duration(raw)
        if actual > target:
            filter_audio = f"{fit_atempo_chain(actual / target)},atrim=0:{target:.3f},asetpts=N/SR/TB"
        else:
            filter_audio = f"apad=pad_dur={target-actual:.3f},atrim=0:{target:.3f},asetpts=N/SR/TB"
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw), "-af", filter_audio, "-ar", "44100", "-ac", "2", str(wav)])
        fitted.append(wav)
    concat = parts_dir / "concat.txt"
    concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in fitted), encoding="utf-8")
    out = GEN_DIR / "narration.mp3"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-codec:a", "libmp3lame", "-q:a", "3", str(out)])
    print(f"Narration created: {out} | {ffprobe_duration(out):.1f}s")
    return out


def make_preview_mp4(narration_mp3):
    concat = GEN_DIR / "video_concat.txt"
    concat.write_text("".join(f"file '{(ASSET_DIR / c['src']).as_posix()}'\n" for c in manifest["clips"]), encoding="utf-8")
    silent = GEN_DIR / "movin_martech_silent_stitch.mp4"
    final = ROOT / "movin_martech_weaved_preview.mp4"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30", "-an", "-movflags", "+faststart", str(silent)])
    video_duration = ffprobe_duration(silent)
    narration_duration = ffprobe_duration(narration_mp3)
    delta = narration_duration - video_duration
    filters = []
    if delta > 0.05:
        filters.append(f"tpad=stop_mode=clone:stop_duration={delta:.3f}")
    filters.append(f"trim=duration={narration_duration:.3f}")
    filters.append("setpts=PTS-STARTPTS")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(silent), "-i", str(narration_mp3), "-filter:v", ",".join(filters), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(final)])
    print(f"Preview MP4 created: {final} | {size_mb(final):.1f} MB")
    return final

if BUILD_PREVIEW_MP4:
    narration_mp3 = make_narration_mp3()
    make_preview_mp4(narration_mp3)

# =========================
# 7) ZIP GITHUB ASSETS FOR UPLOAD
# =========================
assets_zip = ROOT / "movin_github_assets_under_20mb_rich_final.zip"
with zipfile.ZipFile(assets_zip, "w", zipfile.ZIP_DEFLATED) as z:
    for p in (ASSET_DIR / "assets" / "clips").glob("*.mp4"):
        z.write(p, p.relative_to(ASSET_DIR))
    z.write(ASSET_DIR / "assets" / "video-manifest.json", Path("assets/video-manifest.json"))
    z.write(DATA_DIR / "narration.json", Path("data/narration.json"))

print("\nDONE")
print(f"Download this and unzip it into your GitHub repo root: {assets_zip}")
print("Every individual clip is below the target size. GitHub Actions will create the narration MP3 and final stitched MP4 during deployment.")

try:
    from google.colab import files
    files.download(str(assets_zip))
except Exception:
    pass
