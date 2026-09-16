# Podcast from README

<p align="center">
  <img src="https://img.shields.io/badge/Sarvam%20AI-sarvam--105b%20%7C%20bulbul%3Av3-FF6B6B?style=for-the-badge&logo=ai&logoColor=white" alt="Sarvam AI" />
  <img src="https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Deploy%20with-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white" alt="Vercel" />
</p>

Paste a project README or documentation, and get back a **2-host conversational podcast clip** in your target language! Powered by Sarvam AI (`sarvam-105b` chat model and `bulbul:v3` text-to-speech engine).

Built as part of the **Sarvam AI Build Sprint**.

---

## 🚀 Features

- 🌐 **Multi-Language Generation:** Supports **9 Indian Languages** (`English`, `Hindi`, `Telugu`, `Tamil`, `Bengali`, `Kannada`, `Malayalam`, `Marathi`, `Gujarati`).
- 🎙️ **Customizable Voice Cast:** Choose distinct voices for Host A (Curious) and Host B (Explainer) from Bulbul v3 speakers (`anushka`, `karun`, `meera`, `arvind`, `pavithra`, `hitesh`, `vidya`, `ratan`).
- ⏱️ **Adjustable Duration & Pause:** Select target speaking length (*Short*, *Medium*, *Detailed*) and pause gaps between turns (100ms – 750ms).
- 📻 **Instant MP3 Export:** Generates downloadable `.mp3` tracks stitched cleanly with `pydub`.
- ⚡ **Zero-Build Frontend:** Lightweight static HTML5/CSS3/Vanilla JS single-page interface.

---

## 🛠️ Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **LLM Model** | `sarvam-105b` | Writes natural 2-host dialogue scripts from raw README text |
| **TTS Engine** | `bulbul:v3` | Synthesizes Indian English & regional language audio |
| **Backend API** | `FastAPI` (Python 3.10+) | Handles script generation, TTS conversion, and audio stitching |
| **Audio Processing**| `pydub` + `imageio-ffmpeg` | Concatenates turn clips with configurable silence gaps |
| **Frontend UI** | HTML5 / CSS3 / Vanilla JS | Responsive interface with interactive control panel |
| **Deployment** | Vercel Serverless Functions | Serverless deployment via `vercel.json` & `@vercel/python` |

---

## ⚡ How It Works

```
README Text ──► Sarvam Chat (sarvam-105b) ──► 2-Host Script (JSON)
                                                    │
                                                    ▼
MP3 Download ◄── pydub Audio Stitching ◄── Bulbul TTS (bulbul:v3)
```

---

## 💻 Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/SriRamkunamsetty/Sarvam-Podcast-Generator.git
cd Sarvam-Podcast-Generator

# 2. Install backend dependencies
cd backend
pip install -r requirements.txt

# 3. Set your Sarvam AI API Key
export SARVAM_API_KEY="your_api_key_here"

# 4. Start the FastAPI backend
uvicorn main:app --reload
```

Open `frontend/index.html` in your browser.

---

## 🌐 Vercel Deployment

Deploy directly to Vercel with zero configuration:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FSriRamkunamsetty%2FSarvam-Podcast-Generator)

### Environment Variables required on Vercel:
- `SARVAM_API_KEY`: Your Sarvam AI API key.
