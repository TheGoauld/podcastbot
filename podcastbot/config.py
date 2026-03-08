"""
Configuration — loads all settings from .env file.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(_env_path)

# --- Data paths ---
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PODCAST_DIR = DATA_DIR / "podcast"
EPISODES_DIR = PODCAST_DIR / "episodes"
ASSETS_DIR = PODCAST_DIR / "assets"
DB_PATH = DATA_DIR / "podcastbot.db"
RSS_PATH = PODCAST_DIR / "feed.xml"
SYNC_TOKEN_FILE = DATA_DIR / "matrix-sync-token"

# --- Podcast metadata ---
PODCAST_NAME = os.environ.get("PODCAST_NAME", "My Morning Brief")
PODCAST_AUTHOR = os.environ.get("PODCAST_AUTHOR", "PodcastBot")
PODCAST_DESC = os.environ.get("PODCAST_DESC", "AI-generated podcast from curated articles.")
PODCAST_BASE_URL = os.environ.get("PODCAST_BASE_URL", "")

# --- LLM ---
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-chat")

# --- OpenAI TTS ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# --- Matrix ---
MATRIX_HOMESERVER = os.environ.get("MATRIX_HOMESERVER", "")
MATRIX_ACCESS_TOKEN = os.environ.get("MATRIX_ACCESS_TOKEN", "")
MATRIX_USER_ID = os.environ.get("MATRIX_USER_ID", "")
MATRIX_ROOM_ID = os.environ.get("MATRIX_ROOM_ID", "")


def llm_chat(prompt: str, max_tokens: int = 1000, temperature: float = 0.4) -> str:
    """Send a prompt to the configured LLM and return the response text."""
    import requests

    if LLM_PROVIDER == "ollama":
        r = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            },
            timeout=180,
        )
        r.raise_for_status()
        return r.json()["message"]["content"].strip()

    elif LLM_PROVIDER == "openrouter":
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")
