"""
embedding_service.py — Quản lý model embedding và tạo vectors.

Sử dụng sentence-transformers với model all-MiniLM-L6-v2:
- Model nhỏ gọn (~80MB), chạy được trên CPU
- Tạo vector 384 chiều cho mỗi đoạn văn bản
- Hỗ trợ tiếng Việt ở mức độ chấp nhận được

Quan trọng: Model được load 1 lần duy nhất khi khởi động
→ Tránh load lại nhiều lần gây chậm
"""

from sentence_transformers import SentenceTransformer
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Tên model sử dụng — khai báo ở đây để dễ thay đổi sau
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


class EmbeddingService:
    """
    Service quản lý model embedding.
    Dùng pattern Singleton — chỉ load model 1 lần.
    """

    _instance = None
    _model = None

    def __new__(cls):
        """Đảm bảo chỉ tạo 1 instance duy nhất (Singleton)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_model(self) -> None:
        """
        Load model embedding vào bộ nhớ.
        Lần đầu sẽ tải model từ internet (~80MB).
        Các lần sau dùng cache local.
        """
        if self._model is not None:
            logger.debug("Model đã được load sẵn, bỏ qua")
            return

        logger.info(f"⏳ Đang load model: {EMBEDDING_MODEL_NAME}")
        logger.info("  (Lần đầu sẽ tải ~80MB, vui lòng chờ...)")

        try:
            self._model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            logger.info(f"✅ Load model thành công: {EMBEDDING_MODEL_NAME}")
        except Exception as e:
            logger.error(f"❌ Không load được model: {e}")
            raise

    def embed_text(self, text: str) -> list[float]:
        """
        Tạo vector embedding cho 1 đoạn văn bản.

        Args:
            text: Văn bản cần tạo embedding

        Returns:
            List các số float (384 phần tử)
        """
        if self._model is None:
            self.load_model()

        if not text or not text.strip():
            raise ValueError("Không thể tạo embedding cho text rỗng")

        try:
            # encode() trả về numpy array → chuyển thành list
            vector = self._model.encode(text, convert_to_numpy=True)
            return vector.tolist()
        except Exception as e:
            logger.error(f"❌ Lỗi tạo embedding: {e}")
            raise

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Tạo embedding cho nhiều đoạn văn cùng lúc.
        Nhanh hơn gọi embed_text() nhiều lần.

        Args:
            texts: Danh sách các đoạn văn bản

        Returns:
            Danh sách vectors, mỗi vector là list float
        """
        if self._model is None:
            self.load_model()

        if not texts:
            return []

        logger.info(f"⏳ Tạo embedding cho {len(texts)} đoạn văn...")

        try:
            # batch_size=32 — xử lý 32 đoạn cùng lúc
            vectors = self._model.encode(
                texts,
                batch_size=32,
                convert_to_numpy=True,
                show_progress_bar=len(texts) > 10
            )
            logger.info(f"✅ Tạo embedding xong: {len(vectors)} vectors")
            return [v.tolist() for v in vectors]
        except Exception as e:
            logger.error(f"❌ Lỗi tạo batch embedding: {e}")
            raise


# Instance dùng chung toàn hệ thống
embedding_service = EmbeddingService()  