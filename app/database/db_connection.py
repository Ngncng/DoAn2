"""
db_connection.py — Quản lý kết nối SQL Server.

Module này chịu trách nhiệm:
- Tạo connection string từ config
- Cung cấp connection cho toàn hệ thống
- Đảm bảo đóng connection đúng cách (tránh memory leak)
"""

import pyodbc
from app.config import config
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_connection_string() -> str:
    """
    Tạo connection string để kết nối SQL Server.

    Hỗ trợ 2 kiểu xác thực:
    - Windows Authentication: không cần user/password
    - SQL Server Authentication: cần user + password

    Returns:
        Chuỗi kết nối đầy đủ
    """
    # Kiểu 1 — Windows Authentication (DB_USER để trống)
    if not config.DB_USER:
        return (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={config.DB_SERVER};"
            f"DATABASE={config.DB_NAME};"
            f"Trusted_Connection=yes;"
        )

    # Kiểu 2 — SQL Server Authentication
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={config.DB_SERVER};"
        f"DATABASE={config.DB_NAME};"
        f"UID={config.DB_USER};"
        f"PWD={config.DB_PASSWORD};"
    )


def get_connection() -> pyodbc.Connection:
    """
    Tạo và trả về một connection mới tới SQL Server.

    ⚠️ Quan trọng: Sau khi dùng xong phải đóng connection.
    Nên dùng với 'with' statement hoặc try/finally.

    Returns:
        pyodbc.Connection — đối tượng kết nối database

    Raises:
        Exception: Nếu không kết nối được database
    """
    try:
        conn = pyodbc.connect(get_connection_string())
        logger.debug("✅ Kết nối database thành công")
        return conn

    except pyodbc.Error as e:
        logger.error(f"❌ Lỗi kết nối database: {e}")
        raise Exception(f"Không thể kết nối database: {e}")


def test_connection() -> bool:
    """
    Kiểm tra kết nối database có hoạt động không.
    Dùng khi khởi động app để xác nhận DB sẵn sàng.

    Returns:
        True nếu kết nối OK, False nếu lỗi
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        logger.info("✅ Test kết nối database: OK")
        return True

    except Exception as e:
        logger.error(f"❌ Test kết nối database thất bại: {e}")
        return False