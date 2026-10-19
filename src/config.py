"""Configuration and environment variables for Thesis Engine."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root if present
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DOSSIERS_DIR = DATA_DIR / "dossiers"

# LLM Providers Configuration
DEFAULT_GENERATOR_PROVIDER = os.getenv("GENERATOR_PROVIDER", os.getenv("LLM_PROVIDER", "google"))
DEFAULT_JUDGE_PROVIDER = os.getenv("JUDGE_PROVIDER", os.getenv("LLM_PROVIDER", "google"))

# Models
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Optional External Detector
PANGRAM_API_KEY = os.getenv("PANGRAM_API_KEY")
