"""
main.py — Điểm khởi động của toàn bộ ứng dụng.

Chịu trách nhiệm:
- Khởi tạo FastAPI app
- Đăng ký tất cả routes
- Phục vụ file frontend (HTML, CSS, JS)
- Kiểm tra hệ thống khi khởi động
- Chạy server uvicorn
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from app.routes.chat_routes import router as chat_router
from app.routes.upload_routes import router as upload_router
from app.database.db_connection import test_connection
from app.services.embedding_service import embedding_service
from app.config import config
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Đường dẫn tới thư mục frontend
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
TEMPLATES_DIR = os.path.join(FRONTEND_DIR, "templates")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")


# ================================================================
# Startup / Shutdown lifecycle
# ================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Chạy khi app khởi động và khi tắt.
    Dùng để kiểm tra hệ thống và load model.
    """
    # ---- KHỞI ĐỘNG ----
    logger.info("=" * 50)
    logger.info("🏯 HUNGDAO_CHATBOT đang khởi động...")
    logger.info("=" * 50)

    # Kiểm tra config
    try:
        config.validate()
    except ValueError as e:
        logger.error(str(e))
        raise

    # Kiểm tra database
    if test_connection():
        logger.info("✅ Database: Kết nối thành công")
    else:
        logger.error("❌ Database: Không kết nối được")
        raise RuntimeError("Không thể kết nối database")

    # Load embedding model trước (tránh delay lần đầu chat)
    logger.info("⏳ Đang load embedding model...")
    embedding_service.load_model()

    # Tạo thư mục uploads nếu chưa có
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    logger.info(f"📁 Thư mục upload: {config.UPLOAD_DIR}")

    logger.info("=" * 50)
    logger.info(f"🚀 Server sẵn sàng: http://{config.APP_HOST}:{config.APP_PORT}")
    logger.info("=" * 50)

    yield  # App đang chạy

    # ---- TẮT MÁY ----
    logger.info("👋 HUNGDAO_CHATBOT đang tắt...")


# ================================================================
# Khởi tạo FastAPI App
# ================================================================

app = FastAPI(
    title="HUNGDAO_CHATBOT",
    description="Chatbot lịch sử AI đóng vai Trần Hưng Đạo",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",       # Swagger UI — để test API
    redoc_url="/redoc"
)


# ================================================================
# Mount static files và templates
# ================================================================

# Phục vụ file CSS, JS, Images
app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static"
)

# Template engine cho HTML
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# ================================================================
# Đăng ký API routes
# ================================================================

app.include_router(upload_router)
app.include_router(chat_router)


# ================================================================
# Frontend routes — trả về HTML
# ================================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Trang chủ → chuyển về trang chat."""
    return templates.TemplateResponse(
        "chat.html",
        {"request": request}
    )


@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """Trang chat với AI Trần Hưng Đạo."""
    return templates.TemplateResponse(
        "chat.html",
        {"request": request}
    )


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """Trang admin upload tài liệu."""
    return templates.TemplateResponse(
        "upload.html",
        {"request": request}
    )


# ================================================================
# Health check endpoint
# ================================================================

@app.get("/api/health")
async def health_check():
    """
    Kiểm tra trạng thái hoạt động của hệ thống.
    Dùng để verify app đang chạy bình thường.
    """
    db_ok = test_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "model": "loaded" if embedding_service._model else "not loaded",
        "version": "1.0.0"
    }


# ================================================================
# Chạy server
# ================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config.APP_HOST,
        port=config.APP_PORT,
        reload=config.DEBUG,    # Auto-reload khi sửa code (chỉ dev)
        log_level="info"
    )