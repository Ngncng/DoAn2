"""
llm_service.py — Gọi Groq API và tạo câu trả lời theo persona.

Quy trình:
1. Đọc persona prompt từ file txt
2. Nhận context từ RAG
3. Xây dựng prompt hoàn chỉnh
4. Gọi Groq API (LLaMA3-70b)
5. Trả về câu trả lời
"""

import os
from groq import Groq
from app.config import config
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Đường dẫn file persona prompt
PERSONA_PROMPT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "prompts", "persona_prompt.txt"
)


def load_persona_prompt() -> str:
    """
    Đọc persona prompt từ file txt.
    Tách ra file riêng để dễ chỉnh sửa mà không cần sửa code.

    Returns:
        Nội dung persona prompt
    """
    try:
        with open(PERSONA_PROMPT_PATH, "r", encoding="utf-8") as f:
            prompt = f.read().strip()
        logger.debug("✅ Đã load persona prompt")
        return prompt
    except FileNotFoundError:
        logger.error(f"❌ Không tìm thấy file persona: {PERSONA_PROMPT_PATH}")
        # Fallback prompt tối thiểu
        return (
            "Ngươi là Trần Hưng Đạo. Xưng 'Ta', "
            "gọi người hỏi là 'Hậu sinh'. "
            "Chỉ trả lời dựa trên tài liệu được cung cấp."
        )


def build_prompt(question: str, context: str) -> str:
    """
    Xây dựng prompt hoàn chỉnh gửi tới LLM.

    Cấu trúc prompt:
    [PERSONA] → AI biết mình là ai
    [TÀI LIỆU] → context từ RAG
    [CÂU HỎI] → câu hỏi người dùng

    Args:
        question: Câu hỏi của người dùng
        context: Nội dung tài liệu liên quan từ RAG

    Returns:
        Prompt hoàn chỉnh
    """
    persona = load_persona_prompt()

    if context:
        prompt = f"""
{persona}

[TÀI LIỆU THAM KHẢO]
{context}

[CÂU HỎI CỦA HẬU SINH]
{question}

[CÂU TRẢ LỜI CỦA TRẦN HƯNG ĐẠO]
"""
    else:
        # Không có context — yêu cầu AI thừa nhận không có thông tin
        prompt = f"""
{persona}

[LƯU Ý]
Sử sách không có ghi chép liên quan đến câu hỏi này trong kho tài liệu hiện có.

[CÂU HỎI CỦA HẬU SINH]
{question}

[CÂU TRẢ LỜI CỦA TRẦN HƯNG ĐẠO]
"""

    return prompt.strip()


class LLMService:
    """
    Service gọi Groq API để tạo câu trả lời.
    """

    def __init__(self):
        """Khởi tạo Groq client."""
        if not config.GROQ_API_KEY:
            raise ValueError("❌ Thiếu GROQ_API_KEY trong .env")

        self.client = Groq(api_key=config.GROQ_API_KEY)
        self.model = config.GROQ_MODEL
        logger.info(f"✅ LLM Service khởi tạo, model: {self.model}")

    def generate_answer(
        self,
        question: str,
        context: str,
        max_tokens: int = 1024
    ) -> str:
        """
        Gọi Groq API để tạo câu trả lời theo persona Trần Hưng Đạo.

        Args:
            question: Câu hỏi của người dùng
            context: Nội dung tài liệu liên quan (từ RAG)
            max_tokens: Độ dài tối đa câu trả lời

        Returns:
            Câu trả lời từ AI
        """
        logger.info(f"🤖 Gọi LLM cho câu hỏi: {question[:80]}...")

        # Xây dựng prompt
        full_prompt = build_prompt(question, context)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=0.7,   # 0=nghiêm túc, 1=sáng tạo
                top_p=0.9,
            )

            answer = response.choices[0].message.content.strip()
            logger.info(f"✅ LLM trả lời: {len(answer)} ký tự")
            return answer

        except Exception as e:
            logger.error(f"❌ Lỗi gọi Groq API: {e}")
            raise Exception(f"Không thể kết nối tới AI: {e}")


# Instance dùng chung toàn hệ thống
llm_service = LLMService()