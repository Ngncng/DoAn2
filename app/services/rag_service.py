"""
rag_service.py — Điều phối toàn bộ pipeline RAG.

RAG = Retrieval-Augmented Generation
→ Tìm kiếm tài liệu liên quan TRƯỚC khi hỏi LLM.
→ LLM chỉ trả lời dựa trên tài liệu tìm được.

Pipeline:
1. Nhận câu hỏi từ người dùng
2. Tạo embedding cho câu hỏi
3. So sánh với embedding của tất cả chunks trong DB
4. Lấy top-K chunks giống nhất
5. Trả về context (nội dung các chunks ghép lại)
"""

from app.services.embedding_service import embedding_service
from app.models.models import DocumentChunkModel, DocumentModel
from app.utils.embedding_utils import find_top_k_chunks
from app.config import config
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RAGService:
    """
    Service điều phối pipeline RAG.
    """

    def process_document(self, doc_id: int, chunks: list[dict]) -> None:
        """
        Tạo embedding cho tất cả chunks của 1 tài liệu và lưu vào DB.
        Gọi sau khi upload và cắt chunks xong.

        Args:
            doc_id: ID tài liệu cần xử lý
            chunks: Danh sách chunks từ file_processor
        """
        logger.info(
            f"🔄 Bắt đầu tạo embedding cho tài liệu id={doc_id}, "
            f"{len(chunks)} chunks"
        )

        # Lấy nội dung text của tất cả chunks
        texts = [chunk["content"] for chunk in chunks]

        # Tạo embedding hàng loạt (nhanh hơn từng cái)
        embeddings = embedding_service.embed_batch(texts)

        # Gắn embedding vào từng chunk
        chunks_with_embeddings = []
        for chunk, embedding in zip(chunks, embeddings):
            chunks_with_embeddings.append({
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "embedding": embedding
            })

        # Lưu vào database
        DocumentChunkModel.create_batch(doc_id, chunks_with_embeddings)

        # Đánh dấu tài liệu đã xử lý xong
        DocumentModel.mark_as_processed(doc_id)

        logger.info(f"✅ Xử lý embedding xong cho tài liệu id={doc_id}")

    def retrieve_context(self, question: str) -> dict:
        """
        Tìm các đoạn tài liệu liên quan nhất với câu hỏi.

        Args:
            question: Câu hỏi của người dùng

        Returns:
            dict gồm:
            - context_text: nội dung ghép từ các chunks tìm được
            - source_chunks: danh sách chunks gốc (để debug)
            - found: True nếu tìm được tài liệu liên quan
        """
        logger.info(f"🔍 Tìm context cho câu hỏi: {question[:80]}...")

        # Bước 1: Tạo embedding cho câu hỏi
        query_embedding = embedding_service.embed_text(question)

        # Bước 2: Lấy tất cả chunks từ database
        all_chunks = DocumentChunkModel.get_all_with_embeddings()

        if not all_chunks:
            logger.warning("⚠️ Database chưa có tài liệu nào được xử lý")
            return {
                "context_text": "",
                "source_chunks": [],
                "found": False
            }

        # Bước 3: Tìm top-K chunks liên quan nhất
        relevant_chunks = find_top_k_chunks(
            query_embedding=query_embedding,
            all_chunks=all_chunks,
            top_k=config.TOP_K_CHUNKS,
            min_score=config.MIN_SIMILARITY_SCORE
        )

        if not relevant_chunks:
            logger.warning("⚠️ Không tìm thấy chunks liên quan")
            return {
                "context_text": "",
                "source_chunks": [],
                "found": False
            }

        # Bước 4: Ghép nội dung các chunks thành context
        context_parts = []
        for i, chunk in enumerate(relevant_chunks):
            context_parts.append(
                f"[Đoạn {i+1} - Độ liên quan: {chunk['similarity_score']}]\n"
                f"{chunk['content']}"
            )

        context_text = "\n\n---\n\n".join(context_parts)

        logger.info(
            f"✅ Tìm được {len(relevant_chunks)} chunks liên quan"
        )

        return {
            "context_text": context_text,
            "source_chunks": relevant_chunks,
            "found": True
        }


# Instance dùng chung toàn hệ thống
rag_service = RAGService()