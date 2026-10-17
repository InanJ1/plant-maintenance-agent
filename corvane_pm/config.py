"""Paths and environment settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
RAW_DIR = ROOT / "data" / "raw"
MANUALS_DIR = ROOT / "data" / "manuals"
CMMS_DIR = ROOT / "build" / "cmms"
DOCS_DIR = ROOT / "docs"
EVAL_FILE = ROOT / "eval" / "alarms.yaml"


@dataclass(frozen=True)
class LLMSettings:
    """OpenAI-compatible LLM settings (the shared local Ollama by default)."""

    base_url: str
    api_key: str
    model: str
    embed_model: str
    timeout_s: float
    max_tokens: int


def load_settings() -> LLMSettings:
    """Read LLM_* variables, loading a local .env first if python-dotenv is installed."""
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    return LLMSettings(
        base_url=os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/"),
        api_key=os.environ.get("LLM_API_KEY", "ollama"),
        model=os.environ.get("LLM_MODEL", "qwen2.5:7b"),
        embed_model=os.environ.get("EMBED_MODEL", "nomic-embed-text"),
        timeout_s=float(os.environ.get("LLM_TIMEOUT_S", "600")),
        max_tokens=int(os.environ.get("LLM_MAX_TOKENS", "400")),
    )
