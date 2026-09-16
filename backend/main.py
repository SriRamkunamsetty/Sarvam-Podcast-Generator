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
    {"id": "priya", "name": "Priya (Female)", "gender": "Female"},
    {"id": "tarun", "name": "Tarun (Male)", "gender": "Male"},
    {"id": "neha", "name": "Neha (Female)", "gender": "Female"},
    {"id": "rahul", "name": "Rahul (Male)", "gender": "Male"},
    {"id": "pooja", "name": "Pooja (Female)", "gender": "Female"},
    {"id": "rohan", "name": "Rohan (Male)", "gender": "Male"},
    {"id": "simran", "name": "Simran (Female)", "gender": "Female"},
    {"id": "kavya", "name": "Kavya (Female)", "gender": "Female"},
    {"id": "ratan", "name": "Ratan (Male)", "gender": "Male"},
    {"id": "aditya", "name": "Aditya (Male)", "gender": "Male"},
    {"id": "ishita", "name": "Ishita (Female)", "gender": "Female"},
    {"id": "dev", "name": "Dev (Male)", "gender": "Male"},
    {"id": "shreya", "name": "Shreya (Female)", "gender": "Female"},
    {"id": "amit", "name": "Amit (Male)", "gender": "Male"},
]

VALID_VOICE_IDS = {v["id"] for v in SUPPORTED_VOICES}

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
    host_a_voice: str = Field("priya", description="Bulbul voice for Host A")
    host_b_voice: str = Field("tarun", description="Bulbul voice for Host B")
    script_length: str = Field("medium", description="Length: short, medium, or long")
    gap_duration_ms: int = Field(250, description="Pause gap between speakers in ms (50-2000)")


@app.get("/config")
def get_config():
    return {
        "languages": SUPPORTED_LANGUAGES,
        "voices": SUPPORTED_VOICES,
        "lengths": ["short", "medium", "long"],
    }


import re


import re


def extract_script(text: str) -> List[dict]:
    text = text.strip()
    clean_text = text
    if "```" in text:
        clean_text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        clean_text = re.sub(r"\s*```$", "", clean_text, flags=re.MULTILINE).strip()

    # 1. Try finding JSON array
    match = re.search(r"\[\s*\{.*\}\s*\]", clean_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    # 2. Try parsing entire clean_text as JSON
    try:
        res = json.loads(clean_text)
        if isinstance(res, list):
            return res
    except Exception:
        pass

    # 3. Fallback: Parse line-by-line dialogue format e.g. "A: ..." / "Host A: ..." / "B: ..."
    lines = []
    dialogue_matches = re.findall(r"^(?:Host\s+)?([AB])\s*[:\-]\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
    for speaker, line in dialogue_matches:
        cleaned_line = line.strip().strip('"').strip("'")
        if cleaned_line:
            lines.append({"speaker": speaker.upper(), "line": cleaned_line})

    if lines:
        return lines

    raise ValueError(f"Could not parse valid script from LLM output. Raw snippet: {text[:250]}")


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
            max_tokens=2000,
        )

        choices = getattr(completion, "choices", [])
        if not choices and isinstance(completion, dict):
            choices = completion.get("choices", [])

        if not choices:
            raise ValueError(f"No choices returned from Sarvam API. Full response: {completion}")

        first_choice = choices[0]
        message = getattr(first_choice, "message", first_choice.get("message") if isinstance(first_choice, dict) else None)

        if message is None:
            raise ValueError(f"No message object in choice. Choice data: {first_choice}")

        # Extract content first
        raw = getattr(message, "content", None)
        if raw is None and isinstance(message, dict):
            raw = message.get("content")

        # Fallback to reasoning_content for sarvam-105b reasoning outputs
        if not raw:
            raw = getattr(message, "reasoning_content", None)
            if raw is None and isinstance(message, dict):
                raw = message.get("reasoning_content")

        if not raw:
            raise ValueError(f"Sarvam AI chat response content is empty. Message object: {message}")

        return extract_script(raw)
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
    host_a = req.host_a_voice if req.host_a_voice in VALID_VOICE_IDS else "priya"
    host_b = req.host_b_voice if req.host_b_voice in VALID_VOICE_IDS else "tarun"

    script = generate_script(req.readme_text, lang_code, length)

    gap_ms = max(50, min(req.gap_duration_ms, 2000))
    gap = AudioSegment.silent(duration=gap_ms)
    combined = AudioSegment.silent(duration=0)

    for turn in script:
        voice = host_a if turn.get("speaker") == "A" else host_b
        combined += line_to_audio(turn["line"], voice, lang_code) + gap

    buf = io.BytesIO()
    combined.export(buf, format="mp3")
    audio_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    return {
        "script": script,
        "audio_base64": audio_b64,
        "duration_seconds": round(len(combined) / 1000, 1),
        "language_code": lang_code,
        "host_a_voice": host_a,
        "host_b_voice": host_b,
    }

