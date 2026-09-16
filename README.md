# Podcast from README

Paste a project README, get back a 2-host podcast clip. Sarvam's chat model
writes a short conversational script about the project; Bulbul reads it
aloud with two different voices; the clips are stitched into one MP3.

Built as part of a Sarvam AI build sprint.

## How it works

```
README text
     │
     ▼
Sarvam Chat Completions (sarvam-105b)  ──►  2-host script as JSON
     │
     ▼
Bulbul TTS, once per line               ──►  one voice for Host A, another for Host B
     │
     ▼
pydub stitches the clips together       ──►  single MP3, returned as base64
```

## Setup

```bash
cd backend
pip install -r requirements.txt
export SARVAM_API_KEY="your_key_here"
uvicorn main:app --reload
```

Then open `frontend/index.html`. No backend running? Click "Load an example
README" and "Generate podcast" anyway — it'll show the script (using
Scheme Sahayak's own README as the example) with a note that you need the
backend running to hear the actual audio.

## Notes

- Scripts are capped at roughly 45-75 seconds of speaking time by the system
  prompt — long enough to be a real clip, short enough to generate in one
  request.
- The two voices are hardcoded (`anushka` for Host A, `karun` for Host B) in
  `backend/main.py` — swap in any of Bulbul's 30+ speakers.
- If the model's JSON response ever comes back wrapped in a code fence
  despite the system prompt saying not to, `generate_script()` strips it
  before parsing — LLMs don't always follow formatting instructions exactly.

## Stack

- **Backend:** FastAPI, `pydub` for stitching audio, Sarvam AI SDK
- **Frontend:** single-file HTML/CSS/JS, no build step
- **Models:** `sarvam-105b` for the script, `bulbul:v3` for voices
