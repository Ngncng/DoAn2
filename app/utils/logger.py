"""
logger.py — Cấu hình logging cho toàn bộ hệ thống.
Mọi module import logger từ đây để ghi log thống nhất.
"""

import logging
import os
from datetime import datetime

# Tạo thư mục logs nếu chưa có
os.makedirs("logs", exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    """
    Tạo logger cho từng module.

    Cách dùng:
        from app.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Đây là log thông tin")
        logger.error("Đây là log lỗi")

    Args:
        name: Tên module (thường truyền __name__)

    Returns:
        Logger đã được cấu hình
    """
    logger = logging.getLogger(name)

    # Tránh thêm handler trùng lặp
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # --- Format log ---
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # --- Ghi ra console ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # --- Ghi ra file theo ngày ---
    today = datetime.now().strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(
        f"logs/app_{today}.log",
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger