"""
config.py — Cấu hình toàn bộ ứng dụng
Đọc giá trị từ file .env, cung cấp cho toàn bộ hệ thống.
"""

import os
from dotenv import load_dotenv

# Tải biến môi trường từ file .env
load_dotenv()


class Config:
    """
    Lớp chứa toàn bộ cấu hình của ứng dụng.
    Mọi module đều import từ đây — không hardcode ở nơi khác.
    """

    # --- Groq API ---
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama3-70b-8192")

    # --- SQL Server ---
    DB_SERVER: str = os.getenv("DB_SERVER", "localhost")
    DB_NAME: str = os.getenv("DB_NAME", "HUNGDAO_CHATBOT")
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    # --- App ---
    APP_HOST: str = os.getenv("APP_HOST", "127.0.0.1")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # --- Upload ---
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))

    # --- RAG ---
    TOP_K_CHUNKS: int = int(os.getenv("TOP_K_CHUNKS", "5"))
    MIN_SIMILARITY_SCORE: float = float(os.getenv("MIN_SIMILARITY_SCORE", "0.3"))

    # --- Chunking ---
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))

    @classmethod
    def validate(cls) -> None:
        """
        Kiểm tra các config bắt buộc khi khởi động app.
        Nếu thiếu sẽ báo lỗi ngay, không để lỗi âm thầm.
        """
        if not cls.GROQ_API_KEY:
            raise ValueError("❌ Thiếu GROQ_API_KEY trong file .env")

        if not cls.DB_SERVER:
            raise ValueError("❌ Thiếu DB_SERVER trong file .env")

        print("✅ Config hợp lệ — Hệ thống sẵn sàng khởi động")


# Tạo instance dùng chung toàn hệ thống
config = Config()