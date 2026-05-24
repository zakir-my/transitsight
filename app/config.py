"""Application configuration from environment variables."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Try multiple locations for .env to support Windows and different working dirs
dotenv_paths = [
    Path.cwd() / ".env",
    Path(__file__).parent.parent / ".env",  # project root relative to this file
    Path.home() / "transitsight" / ".env",
]
for dotenv_path in dotenv_paths:
    if dotenv_path.exists():
        load_dotenv(dotenv_path, override=True)
        print(f"  [config] Loaded .env from {dotenv_path}", file=sys.stderr)
        break
else:
    # Try load_dotenv() with no args as last resort
    load_dotenv(override=True)


class Settings:
    PROJECT_NAME: str = "TransitSight"
    VERSION: str = "1.0.0"

    # Gemini API
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # data.gov.my (free tier - no API key required for basic access)
    GTFS_STATIC_BASE_URL: str = "https://api.data.gov.my/gtfs-static"
    GTFS_REALTIME_BASE_URL: str = "https://api.data.gov.my/gtfs-realtime"
    WEATHER_BASE_URL: str = "https://api.data.gov.my/weather"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./transitsight.db")

    # Admin credentials
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))


settings = Settings()
