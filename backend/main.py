"""
Podcast-from-README Generator — backend

Takes a README (or any project description) and turns it into a short
two-host podcast: Sarvam's chat model writes a conversational script, then
Bulbul reads each line in a different voice, and the clips are stitched
into one audio file with pydub.

Run it with:
  export SARVAM_API_KEY="your_key_here"
  uvicorn main:app --reload
"""

import base64
import io
import json
import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydub import AudioSegment
from sarvamai import SarvamAI

# Configure ffmpeg path dynamically for serverless environments (e.g., Vercel)
try:
    import imageio_ffmpeg
    AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    pass

app = FastAPI(title="Podcast-from-README Generator")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPPORTED_LANGUAGES = {
    "en-IN": "English",
    "hi-IN": "Hindi (हिन्दी)",
    "te-IN": "Telugu (తెలుగు)",
    "ta-IN": "Tamil (தமிழ்)",
    "kn-IN": "Kannada (ಕನ್ನಡ)",
    "ml-IN": "Malayalam (മലയാളം)",
    "mr-IN": "Marathi (मराठी)",
    "bn-IN": "Bengali (বাংলা)",
    "gu-IN": "Gujarati (ગુજરાતી)",
    "pa-IN": "Punjabi (ਪੰਜਾਬੀ)",
    "od-IN": "Odia (ଓଡ଼ିଆ)",
}

SUPPORTED_VOICES = [
    {"id": "anushka", "name": "Anushka (Female)", "gender": "Female"},
    {"id": "karun", "name": "Karun (Male)", "gender": "Male"},
    {"id": "meera", "name": "Meera (Female)", "gender": "Female"},
    {"id": "arvind", "name": "Arvind (Male)", "gender": "Male"},
    {"id": "pavithra", "name": "Pavithra (Female)", "gender": "Female"},
    {"id": "hitesh", "name": "Hitesh (Male)", "gender": "Male"},
    {"id": "vidya", "name": "Vidya (Female)", "gender": "Female"},
    {"id": "ratan", "name": "Ratan (Male)", "gender": "Male"},
]

LENGTH_PROMPTS = {
    "short": "about 30-45 seconds of total speaking time (roughly 4-6 short dialogue lines)",
    "medium": "about 45-75 seconds of total speaking time (roughly 6-10 short dialogue lines)",
    "long": "about 90-120 seconds of total speaking time (roughly 10-14 short dialogue lines)",
}


def get_sarvam_client() -> SarvamAI:
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="SARVAM_API_KEY environment variable is not set. Please set it before running generation.",
        )
    return SarvamAI(api_subscription_key=api_key)


class PodcastRequest(BaseModel):
    readme_text: str = Field(..., description="Project README or text content")
    language_code: str = Field("en-IN", description="Language code for script & TTS")
    host_a_voice: str = Field("anushka", description="Bulbul voice for Host A")
    host_b_voice: str = Field("karun", description="Bulbul voice for Host B")
    script_length: str = Field("medium", description="Length: short, medium, or long")
    gap_duration_ms: int = Field(250, description="Pause gap between speakers in ms (50-2000)")


@app.get("/config")
def get_config():
    return {
        "languages": SUPPORTED_LANGUAGES,
        "voices": SUPPORTED_VOICES,
        "lengths": ["short", "medium", "long"],
    }


def generate_script(readme_text: str, language_code: str, script_length: str) -> List[dict]:
    client = get_sarvam_client()
    lang_name = SUPPORTED_LANGUAGES.get(language_code, "English")
    length_desc = LENGTH_PROMPTS.get(script_length, LENGTH_PROMPTS["medium"])

    system_prompt = (
        f"You turn a project README into a short, upbeat 2-host tech podcast script, {length_desc}.\n"
        f"Host A is curious and asks questions. Host B explains, with energy, in plain language.\n"
        f"Language requirement: Write the dialogue ENTIRELY in {lang_name} ({language_code}). Make it natural and conversational.\n"
        "No sound-effect descriptions, no music cues, no speaker labels inside the line text — dialogue only.\n\n"
        "Respond with ONLY a JSON array, nothing else, no markdown code fences. Each item must look like:\n"
        '{"speaker": "A", "line": "..."}'
    )

    try:
        completion = client.chat.completions(
            model="sarvam-105b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"README:\n\n{readme_text[:4000]}"},
            ],
        )
        raw = completion.choices[0].message.content.strip()
        # Strip markdown fences if present
        if "```" in raw:
            raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate podcast script: {str(e)}")


def line_to_audio(line: str, speaker_voice: str, language_code: str) -> AudioSegment:
    client = get_sarvam_client()
    try:
        response = client.text_to_speech.convert(
            text=line,
            language_code=language_code,
            speaker=speaker_voice,
            model="bulbul:v3",
        )
        raw_bytes = base64.b64decode(response.audios[0])
        return AudioSegment.from_file(io.BytesIO(raw_bytes))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"TTS conversion failed for line '{line[:30]}...': {str(e)}",
        )


@app.post("/generate")
def generate(req: PodcastRequest):
    if not req.readme_text or not req.readme_text.strip():
        raise HTTPException(status_code=400, detail="README text cannot be empty.")

    lang_code = req.language_code if req.language_code in SUPPORTED_LANGUAGES else "en-IN"
    length = req.script_length if req.script_length in LENGTH_PROMPTS else "medium"

    script = generate_script(req.readme_text, lang_code, length)

    gap_ms = max(50, min(req.gap_duration_ms, 2000))
    gap = AudioSegment.silent(duration=gap_ms)
    combined = AudioSegment.silent(duration=0)

    for turn in script:
        voice = req.host_a_voice if turn.get("speaker") == "A" else req.host_b_voice
        combined += line_to_audio(turn["line"], voice, lang_code) + gap

    buf = io.BytesIO()
    combined.export(buf, format="mp3")
    audio_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    return {
        "script": script,
        "audio_base64": audio_b64,
        "duration_seconds": round(len(combined) / 1000, 1),
        "language_code": lang_code,
        "host_a_voice": req.host_a_voice,
        "host_b_voice": req.host_b_voice,
    }

