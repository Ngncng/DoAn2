"""
models.py — Định nghĩa cấu trúc dữ liệu và thao tác với database.

Mỗi class tương ứng 1 bảng trong database.
Mỗi method thực hiện 1 thao tác cụ thể (thêm, xóa, lấy dữ liệu).

Các bảng:
- Document     → tài liệu được upload
- DocumentChunk → đoạn văn nhỏ từ tài liệu (dùng cho RAG)
- Conversation → phiên chat
- Message      → tin nhắn trong phiên chat
"""

import json
from datetime import datetime
from typing import Optional
from app.database.db_connection import get_connection
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ================================================================
# MODEL: Document
# Tương ứng bảng Documents trong database
# ================================================================

class DocumentModel:
    """Thao tác với bảng Documents."""

    @staticmethod
    def create(title: str, file_path: str, content: str) -> int:
        """
        Thêm tài liệu mới vào database.

        Args:
            title: Tên tài liệu (vd: "Hịch Tướng Sĩ")
            file_path: Đường dẫn file đã lưu
            content: Toàn bộ nội dung văn bản

        Returns:
            id của tài liệu vừa tạo
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO Documents (title, file_path, content)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?)
                """,
                (title, file_path, content)
            )
            doc_id = cursor.fetchone()[0]
            conn.commit()
            logger.info(f"✅ Đã lưu tài liệu: {title} (id={doc_id})")
            return doc_id

        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Lỗi lưu tài liệu: {e}")
            raise
        finally:
            conn.close()

    @staticmethod
    def get_all() -> list[dict]:
        """
        Lấy danh sách toàn bộ tài liệu.

        Returns:
            Danh sách dict, mỗi dict là 1 tài liệu
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, title, file_path, uploaded_at, is_processed
                FROM Documents
                ORDER BY uploaded_at DESC
                """
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "title": row[1],
                    "file_path": row[2],
                    "uploaded_at": str(row[3]),
                    "is_processed": bool(row[4])
                }
                for row in rows
            ]
        finally:
            conn.close()

    @staticmethod
    def get_by_id(doc_id: int) -> Optional[dict]:
        """
        Lấy thông tin 1 tài liệu theo id.

        Args:
            doc_id: ID tài liệu cần tìm

        Returns:
            dict thông tin tài liệu, hoặc None nếu không tìm thấy
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title, file_path, content, uploaded_at, is_processed "
                "FROM Documents WHERE id = ?",
                (doc_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "title": row[1],
                "file_path": row[2],
                "content": row[3],
                "uploaded_at": str(row[4]),
                "is_processed": bool(row[5])
            }
        finally:
            conn.close()

    @staticmethod
    def mark_as_processed(doc_id: int) -> None:
        """
        Đánh dấu tài liệu đã được xử lý (chunk + embedding).

        Args:
            doc_id: ID tài liệu cần cập nhật
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE Documents SET is_processed = 1 WHERE id = ?",
                (doc_id,)
            )
            conn.commit()
            logger.info(f"✅ Đã đánh dấu tài liệu id={doc_id} là đã xử lý")
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Lỗi cập nhật trạng thái tài liệu: {e}")
            raise
        finally:
            conn.close()

    @staticmethod
    def delete(doc_id: int) -> bool:
        """
        Xóa tài liệu (và tự động xóa chunks nhờ CASCADE).

        Args:
            doc_id: ID tài liệu cần xóa

        Returns:
            True nếu xóa thành công
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM Documents WHERE id = ?",
                (doc_id,)
            )
            conn.commit()
            logger.info(f"✅ Đã xóa tài liệu id={doc_id}")
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Lỗi xóa tài liệu: {e}")
            raise
        finally:
            conn.close()


# ================================================================
# MODEL: DocumentChunk
# Tương ứng bảng DocumentChunks trong database
# ================================================================

class DocumentChunkModel:
    """Thao tác với bảng DocumentChunks."""

    @staticmethod
    def create_batch(doc_id: int, chunks: list[dict]) -> None:
        """
        Lưu nhiều chunks cùng lúc (hiệu quả hơn lưu từng cái).

        Args:
            doc_id: ID tài liệu gốc
            chunks: Danh sách dict, mỗi dict gồm:
                    - content (str): nội dung đoạn
                    - chunk_index (int): thứ tự đoạn
                    - embedding (list[float]): vector số
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            for chunk in chunks:
                # Chuyển list số thành chuỗi JSON để lưu vào DB
                embedding_json = json.dumps(chunk["embedding"])
                cursor.execute(
                    """
                    INSERT INTO DocumentChunks
                        (document_id, chunk_index, content, embedding)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        doc_id,
                        chunk["chunk_index"],
                        chunk["content"],
                        embedding_json
                    )
                )
            conn.commit()
            logger.info(
                f"✅ Đã lưu {len(chunks)} chunks cho tài liệu id={doc_id}"
            )
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Lỗi lưu chunks: {e}")
            raise
        finally:
            conn.close()

    @staticmethod
    def get_all_with_embeddings() -> list[dict]:
        """
        Lấy toàn bộ chunks kèm embedding.
        Dùng cho bước tìm kiếm RAG (cosine similarity).

        Returns:
            Danh sách dict, mỗi dict gồm id, content, embedding (list số)
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, document_id, chunk_index, content, embedding
                FROM DocumentChunks
                WHERE embedding IS NOT NULL
                """
            )
            rows = cursor.fetchall()
            result = []
            for row in rows:
                # Chuyển chuỗi JSON ngược lại thành list số
                embedding = json.loads(row[4]) if row[4] else []
                result.append({
                    "id": row[0],
                    "document_id": row[1],
                    "chunk_index": row[2],
                    "content": row[3],
                    "embedding": embedding
                })
            return result
        finally:
            conn.close()

    @staticmethod
    def delete_by_document(doc_id: int) -> None:
        """
        Xóa toàn bộ chunks của 1 tài liệu.
        Thường dùng khi cần xử lý lại tài liệu.

        Args:
            doc_id: ID tài liệu cần xóa chunks
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM DocumentChunks WHERE document_id = ?",
                (doc_id,)
            )
            conn.commit()
            logger.info(f"✅ Đã xóa chunks của tài liệu id={doc_id}")
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Lỗi xóa chunks: {e}")
            raise
        finally:
            conn.close()


# ================================================================
# MODEL: Conversation
# Tương ứng bảng Conversations trong database
# ================================================================

class ConversationModel:
    """Thao tác với bảng Conversations."""

    @staticmethod
    def create(session_id: str) -> int:
        """
        Tạo phiên chat mới.

        Args:
            session_id: ID phiên chat (tạo từ frontend)

        Returns:
            id của conversation vừa tạo
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO Conversations (session_id)
                OUTPUT INSERTED.id
                VALUES (?)
                """,
                (session_id,)
            )
            conv_id = cursor.fetchone()[0]
            conn.commit()
            logger.info(
                f"✅ Tạo conversation mới: session={session_id} id={conv_id}"
            )
            return conv_id
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Lỗi tạo conversation: {e}")
            raise
        finally:
            conn.close()

    @staticmethod
    def get_by_session(session_id: str) -> Optional[dict]:
        """
        Tìm conversation theo session_id.

        Args:
            session_id: ID phiên chat

        Returns:
            dict thông tin conversation, hoặc None nếu không tìm thấy
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, session_id, created_at, updated_at "
                "FROM Conversations WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "session_id": row[1],
                "created_at": str(row[2]),
                "updated_at": str(row[3])
            }
        finally:
            conn.close()

    @staticmethod
    def delete_by_session(session_id: str) -> bool:
        """
        Xóa toàn bộ lịch sử chat của 1 phiên.
        (Messages sẽ tự xóa nhờ CASCADE)

        Args:
            session_id: ID phiên chat cần xóa

        Returns:
            True nếu xóa thành công
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM Conversations WHERE session_id = ?",
                (session_id,)
            )
            conn.commit()
            logger.info(f"✅ Đã xóa lịch sử chat session={session_id}")
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Lỗi xóa conversation: {e}")
            raise
        finally:
            conn.close()


# ================================================================
# MODEL: Message
# Tương ứng bảng Messages trong database
# ================================================================

class MessageModel:
    """Thao tác với bảng Messages."""

    @staticmethod
    def create(
        conversation_id: int,
        role: str,
        user_message: str,
        bot_response: str
    ) -> int:
        """
        Lưu 1 cặp hội thoại (câu hỏi + trả lời).

        Args:
            conversation_id: ID phiên chat
            role: "user" hoặc "assistant"
            user_message: Câu hỏi của người dùng
            bot_response: Câu trả lời của AI

        Returns:
            id của message vừa lưu
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO Messages
                    (conversation_id, role, user_message, bot_response)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, role, user_message, bot_response)
            )
            msg_id = cursor.fetchone()[0]

            # Cập nhật thời gian conversation
            cursor.execute(
                "UPDATE Conversations SET updated_at = GETDATE() "
                "WHERE id = ?",
                (conversation_id,)
            )
            conn.commit()
            return msg_id
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Lỗi lưu message: {e}")
            raise
        finally:
            conn.close()

    @staticmethod
    def get_by_conversation(conversation_id: int) -> list[dict]:
        """
        Lấy toàn bộ lịch sử chat của 1 phiên.

        Args:
            conversation_id: ID phiên chat

        Returns:
            Danh sách tin nhắn theo thứ tự thời gian
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, role, user_message, bot_response, created_at
                FROM Messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                """,
                (conversation_id,)
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "role": row[1],
                    "user_message": row[2],
                    "bot_response": row[3],
                    "created_at": str(row[4])
                }
                for row in rows
            ]
        finally:
            conn.close()