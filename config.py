import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or os.urandom(32)
    DATABASE = os.environ.get("DATABASE_PATH", str(BASE_DIR / "database" / "plaza_segura.db"))
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(BASE_DIR / "static" / "uploads"))
    PRIVATE_UPLOAD_FOLDER = os.environ.get(
        "PRIVATE_UPLOAD_FOLDER", str(BASE_DIR / "database" / "private_uploads")
    )
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8
