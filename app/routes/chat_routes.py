"""
chat_routes.py — API endpoints cho chức năng chat.

Các endpoint:
POST /api/chat                          → Gửi câu hỏi, nhận trả lời
GET  /api/chat/history/{session_id}     → Lấy lịch sử chat
DELETE /api/chat/history/{session_id}   → Xóa lịch sử chat
POST /api/chat/new-session              → Tạo phiên chat mới
"""

import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from app.services.rag_service import rag_service
from app.services.llm_service import llm_service
from app.models.models import ConversationModel, MessageModel
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Tạo router — nhóm các endpoint liên quan đến chat
router = APIRouter(prefix="/api/chat", tags=["Chat"])


# ================================================================
# Pydantic Models — định nghĩa cấu trúc request body
# ================================================================

class ChatRequest(BaseModel):
    """Cấu trúc request gửi lên khi chat."""
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Câu hỏi của người dùng"
    )
    session_id: str = Field(
        ...,
        min_length=1,
        description="ID phiên chat (tạo từ frontend)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "question": "Ngài đã chỉ huy trận Bạch Đằng như thế nào?",
                "session_id": "abc123"
            }
        }


class NewSessionRequest(BaseModel):
    """Request tạo phiên chat mới."""
    session_id: str = Field(
        default_factory=lambda: uuid.uuid4().hex,
        description="ID phiên chat (tự tạo nếu không truyền)"
    )


# ================================================================
# Endpoints
# ================================================================

@router.post("/new-session")
async def create_new_session():
    """
    Tạo phiên chat mới với session_id ngẫu nhiên.
    Frontend gọi khi người dùng bấm 'Chat mới'.

    Returns:
        JSON chứa session_id mới
    """
    session_id = uuid.uuid4().hex
    try:
        conv_id = ConversationModel.create(session_id)
        logger.info(f"✅ Tạo phiên chat mới: {session_id}")
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "session_id": session_id,
                "conversation_id": conv_id
            }
        )
    except Exception as e:
        logger.error(f"❌ Lỗi tạo phiên chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def chat(request: ChatRequest):
    """
    Xử lý câu hỏi và trả về câu trả lời từ AI Trần Hưng Đạo.

    Pipeline đầy đủ:
    1. Kiểm tra / tạo conversation theo session_id
    2. Tìm context liên quan (RAG)
    3. Gọi LLM tạo câu trả lời
    4. Lưu tin nhắn vào database
    5. Trả về câu trả lời cho frontend

    Args:
        request: ChatRequest gồm question và session_id

    Returns:
        JSON chứa câu trả lời và thông tin context
    """
    logger.info(
        f"💬 Chat request | session={request.session_id} "
        f"| câu hỏi: {request.question[:60]}..."
    )

    # Bước 1: Lấy hoặc tạo conversation
    conversation = ConversationModel.get_by_session(request.session_id)
    if not conversation:
        # Tự tạo conversation nếu chưa có
        conv_id = ConversationModel.create(request.session_id)
    else:
        conv_id = conversation["id"]

    try:
        # Bước 2: RAG — tìm tài liệu liên quan
        retrieval_result = rag_service.retrieve_context(request.question)
        context_text = retrieval_result["context_text"]
        context_found = retrieval_result["found"]

        # Bước 3: Gọi LLM tạo câu trả lời
        answer = llm_service.generate_answer(
            question=request.question,
            context=context_text
        )

        # Bước 4: Lưu tin nhắn vào database
        MessageModel.create(
            conversation_id=conv_id,
            role="user",
            user_message=request.question,
            bot_response=answer
        )

        # Bước 5: Trả về kết quả
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "answer": answer,
                    "session_id": request.session_id,
                    "context_found": context_found,
                    "chunks_used": len(retrieval_result["source_chunks"])
                }
            }
        )

    except Exception as e:
        logger.error(
            f"❌ Lỗi xử lý chat | session={request.session_id}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi xử lý câu hỏi: {str(e)}"
        )


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    """
    Lấy toàn bộ lịch sử chat của 1 phiên.

    Args:
        session_id: ID phiên chat

    Returns:
        JSON danh sách tin nhắn theo thứ tự thời gian
    """
    try:
        conversation = ConversationModel.get_by_session(session_id)
        if not conversation:
            # Trả về rỗng thay vì lỗi — phiên mới chưa có tin nhắn
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "session_id": session_id,
                    "messages": [],
                    "total": 0
                }
            )

        messages = MessageModel.get_by_conversation(conversation["id"])
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "session_id": session_id,
                "messages": messages,
                "total": len(messages)
            }
        )

    except Exception as e:
        logger.error(f"❌ Lỗi lấy lịch sử chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{session_id}")
async def delete_chat_history(session_id: str):
    """
    Xóa toàn bộ lịch sử chat của 1 phiên.
    (Messages tự xóa nhờ CASCADE trong database)

    Args:
        session_id: ID phiên chat cần xóa

    Returns:
        JSON xác nhận đã xóa
    """
    try:
        conversation = ConversationModel.get_by_session(session_id)
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy phiên chat này"
            )

        ConversationModel.delete_by_session(session_id)
        logger.info(f"🗑️ Đã xóa lịch sử chat session={session_id}")

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Đã xóa toàn bộ lịch sử chat"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Lỗi xóa lịch sử chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))