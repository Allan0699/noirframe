"""
Application configuration.

All secrets and environment-specific values are read from environment
variables (loaded from a .env file via python-dotenv). Never commit a real
.env file -- only .env.example is tracked.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


class Config:
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"

    # Database
    DATABASE_PATH = str(BASE_DIR / "database" / "noirframe.db")
    SCHEMA_PATH = str(BASE_DIR / "database" / "schema.sql")

    # Uploads
    UPLOAD_FOLDER = str(BASE_DIR / "static" / "uploads")
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB per upload

    # Google Gemini API
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    GEMINI_API_URL = (
        "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    )

    # Branding
    COMPANY_NAME = "NOIRFRAME"
    COMPANY_TAGLINE = "Cinematic craft. Engineered delivery."
