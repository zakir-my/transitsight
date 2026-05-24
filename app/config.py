"""Application configuration from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


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
