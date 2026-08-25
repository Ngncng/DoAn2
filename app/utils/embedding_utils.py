"""
embedding_utils.py — Công cụ tính toán vector embedding.

Embedding là gì?
→ Chuyển đoạn văn bản thành 1 danh sách số (vector).
→ Các đoạn có nghĩa giống nhau sẽ có vector "gần nhau".
→ Dùng cosine similarity để đo độ giống nhau giữa 2 vector.

Ví dụ:
  "Trận Bạch Đằng" → [0.12, -0.45, 0.78, ...]  (384 số)
  "Chiến thắng sông Bạch Đằng" → [0.11, -0.43, 0.79, ...]  (gần giống)
  "Mùa xuân Hà Nội" → [-0.33, 0.21, -0.15, ...]  (rất khác)
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from app.utils.logger import get_logger

logger = get_logger(__name__)


def compute_cosine_similarity(
    query_embedding: list[float],
    chunk_embeddings: list[list[float]]
) -> list[float]:
    """
    Tính độ tương đồng cosine giữa câu hỏi và tất cả chunks.

    Cosine similarity trả về giá trị từ -1 đến 1:
    - 1.0  = giống hệt nhau
    - 0.0  = không liên quan
    - -1.0 = trái nghĩa hoàn toàn

    Args:
        query_embedding: Vector của câu hỏi người dùng
        chunk_embeddings: Danh sách vector của các chunks

    Returns:
        Danh sách điểm similarity, index tương ứng với chunk
    """
    if not chunk_embeddings:
        return []

    # Chuyển thành numpy array để tính toán nhanh
    query_vec = np.array(query_embedding).reshape(1, -1)
    chunks_vec = np.array(chunk_embeddings)

    # Tính cosine similarity — trả về ma trận (1 x n_chunks)
    similarities = cosine_similarity(query_vec, chunks_vec)[0]

    return similarities.tolist()


def find_top_k_chunks(
    query_embedding: list[float],
    all_chunks: list[dict],
    top_k: int,
    min_score: float
) -> list[dict]:
    """
    Tìm top-K chunks có độ liên quan cao nhất với câu hỏi.

    Args:
        query_embedding: Vector của câu hỏi
        all_chunks: Danh sách tất cả chunks (có trường 'embedding')
        top_k: Số lượng chunks muốn lấy
        min_score: Điểm tối thiểu để chunk được chọn

    Returns:
        Danh sách chunks liên quan nhất, đã sắp xếp theo điểm giảm dần
        Mỗi chunk có thêm trường 'similarity_score'
    """
    if not all_chunks:
        logger.warning("⚠️ Không có chunks nào trong database")
        return []

    # Lấy tất cả embedding từ chunks
    chunk_embeddings = [chunk["embedding"] for chunk in all_chunks]

    # Tính similarity
    scores = compute_cosine_similarity(query_embedding, chunk_embeddings)

    # Gắn điểm vào từng chunk
    scored_chunks = []
    for chunk, score in zip(all_chunks, scores):
        if score >= min_score:
            chunk_with_score = {**chunk, "similarity_score": round(float(score), 4)}
            scored_chunks.append(chunk_with_score)

    # Sắp xếp theo điểm từ cao xuống thấp
    scored_chunks.sort(key=lambda x: x["similarity_score"], reverse=True)

    # Lấy top-K
    result = scored_chunks[:top_k]

    logger.info(
        f"🔍 Tìm được {len(result)}/{len(all_chunks)} chunks "
        f"(min_score={min_score}, top_k={top_k})"
    )
    for i, chunk in enumerate(result):
        logger.debug(
            f"  #{i+1} score={chunk['similarity_score']} "
            f"| {chunk['content'][:60]}..."
        )

    return result