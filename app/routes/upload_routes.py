"""
upload_routes.py — API endpoints cho việc upload và quản lý tài liệu.

Các endpoint:
POST   /api/upload          → Upload file PDF/TXT
GET    /api/documents        → Lấy danh sách tài liệu
DELETE /api/documents/{id}   → Xóa tài liệu
GET    /api/documents/{id}   → Xem chi tiết 1 tài liệu
"""

import os
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from app.services.file_processor import process_file
from app.services.rag_service import rag_service
from app.models.models import DocumentModel
from app.config import config
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Tạo router — nhóm các endpoint liên quan đến upload
router = APIRouter(prefix="/api", tags=["Documents"])

# Định dạng file được phép upload
ALLOWED_EXTENSIONS = {".pdf", ".txt"}


def validate_file(filename: str, file_size: int) -> None:
    """
    Kiểm tra file upload có hợp lệ không.

    Args:
        filename: Tên file
        file_size: Kích thước file (bytes)

    Raises:
        HTTPException: Nếu file không hợp lệ
    """
    # Kiểm tra đuôi file
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Chỉ hỗ trợ file PDF và TXT. File của bạn: {ext}"
        )

    # Kiểm tra dung lượng
    max_bytes = config.MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File quá lớn. "
                f"Tối đa {config.MAX_FILE_SIZE_MB}MB, "
                f"file của bạn: {file_size / 1024 / 1024:.1f}MB"
            )
        )


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload tài liệu lịch sử lên hệ thống.

    Quy trình:
    1. Nhận file từ frontend
    2. Kiểm tra hợp lệ (đuôi file, dung lượng)
    3. Lưu file vào thư mục uploads/
    4. Đọc và cắt thành chunks
    5. Tạo embedding và lưu vào database

    Args:
        file: File upload từ form

    Returns:
        JSON thông tin tài liệu vừa upload
    """
    logger.info(f"📥 Nhận upload: {file.filename}")

    # Đọc nội dung file vào bộ nhớ để kiểm tra size
    file_content = await file.read()
    file_size = len(file_content)

    # Kiểm tra file hợp lệ
    validate_file(file.filename, file_size)

    # Tạo tên file unique để tránh trùng lặp
    ext = os.path.splitext(file.filename)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(config.UPLOAD_DIR, unique_filename)

    # Đảm bảo thư mục uploads tồn tại
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)

    try:
        # Bước 1: Lưu file vào disk
        with open(save_path, "wb") as f:
            f.write(file_content)
        logger.info(f"💾 Đã lưu file: {save_path}")

        # Bước 2: Đọc và cắt chunks
        process_result = process_file(save_path)

        # Bước 3: Lưu thông tin tài liệu vào database
        doc_id = DocumentModel.create(
            title=file.filename,
            file_path=save_path,
            content=process_result["text"]
        )

        # Bước 4: Tạo embedding và lưu chunks
        await _process_embeddings(doc_id, process_result["chunks"])

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Upload và xử lý tài liệu thành công",
                "data": {
                    "doc_id": doc_id,
                    "title": file.filename,
                    "total_chars": process_result["total_chars"],
                    "total_chunks": process_result["total_chunks"]
                }
            }
        )

    except Exception as e:
        # Nếu lỗi → xóa file đã lưu để tránh rác
        if os.path.exists(save_path):
            os.remove(save_path)
        logger.error(f"❌ Lỗi xử lý upload: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi xử lý tài liệu: {str(e)}"
        )


async def _process_embeddings(doc_id: int, chunks: list[dict]) -> None:
    """
    Xử lý embedding trong background (hàm nội bộ).
    Tách ra để upload_document() gọn hơn.

    Args:
        doc_id: ID tài liệu
        chunks: Danh sách chunks từ file_processor
    """
    try:
        rag_service.process_document(doc_id, chunks)
        logger.info(f"✅ Embedding xong tài liệu id={doc_id}")
    except Exception as e:
        logger.error(f"❌ Lỗi tạo embedding cho doc_id={doc_id}: {e}")
        raise


@router.get("/documents")
async def get_documents():
    """
    Lấy danh sách tất cả tài liệu đã upload.

    Returns:
        JSON danh sách tài liệu
    """
    try:
        documents = DocumentModel.get_all()
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": documents,
                "total": len(documents)
            }
        )
    except Exception as e:
        logger.error(f"❌ Lỗi lấy danh sách tài liệu: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{doc_id}")
async def get_document(doc_id: int):
    """
    Lấy thông tin chi tiết 1 tài liệu.

    Args:
        doc_id: ID tài liệu cần xem

    Returns:
        JSON thông tin tài liệu
    """
    try:
        doc = DocumentModel.get_by_id(doc_id)
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy tài liệu id={doc_id}"
            )
        return JSONResponse(
            status_code=200,
            content={"success": True, "data": doc}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Lỗi lấy tài liệu id={doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int):
    """
    Xóa tài liệu và toàn bộ chunks liên quan.
    File vật lý cũng được xóa khỏi disk.

    Args:
        doc_id: ID tài liệu cần xóa

    Returns:
        JSON xác nhận đã xóa
    """
    try:
        # Lấy thông tin trước khi xóa (để xóa file vật lý)
        doc = DocumentModel.get_by_id(doc_id)
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy tài liệu id={doc_id}"
            )

        # Xóa file vật lý
        if os.path.exists(doc["file_path"]):
            os.remove(doc["file_path"])
            logger.info(f"🗑️ Đã xóa file: {doc['file_path']}")

        # Xóa trong database (cascade → tự xóa chunks)
        DocumentModel.delete(doc_id)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Đã xóa tài liệu '{doc['title']}'"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Lỗi xóa tài liệu id={doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))