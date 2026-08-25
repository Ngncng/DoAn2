"""Test toàn bộ business logic Giai đoạn 3."""

def test_file_processor():
    """Test đọc file và cắt chunks."""
    from app.services.file_processor import clean_text, split_into_chunks

    # Test clean_text
    text = "Trần Hưng Đạo   sinh năm  1228.\n\n\nÔng là danh tướng."
    cleaned = clean_text(text)
    assert "  " not in cleaned
    print("✅ clean_text OK")

    # Test split_into_chunks
    long_text = "Đây là câu văn mẫu. " * 100
    chunks = split_into_chunks(long_text, chunk_size=200, overlap=20)
    assert len(chunks) > 0
    assert all("content" in c for c in chunks)
    print(f"✅ split_into_chunks OK → {len(chunks)} chunks")


def test_embedding():
    """Test tạo embedding."""
    from app.services.embedding_service import embedding_service

    embedding_service.load_model()
    vector = embedding_service.embed_text("Trần Hưng Đạo đánh giặc Nguyên Mông")

    assert len(vector) == 384
    assert all(isinstance(v, float) for v in vector)
    print(f"✅ embed_text OK → vector {len(vector)} chiều")


def test_cosine_similarity():
    """Test tìm chunks liên quan."""
    from app.services.embedding_service import embedding_service
    from app.utils.embedding_utils import find_top_k_chunks

    embedding_service.load_model()

    # Tạo 3 câu mẫu
    sentences = [
        "Trận Bạch Đằng năm 1288 đánh bại quân Nguyên",
        "Hịch Tướng Sĩ kêu gọi tướng sĩ chiến đấu",
        "Mùa xuân Hà Nội đẹp lắm"
    ]
    embeddings = embedding_service.embed_batch(sentences)
    chunks = [
        {"id": i, "content": s, "embedding": e, "document_id": 1}
        for i, (s, e) in enumerate(zip(sentences, embeddings))
    ]

    # Tìm chunk liên quan đến Bạch Đằng
    query_emb = embedding_service.embed_text("chiến thắng sông Bạch Đằng")
    results = find_top_k_chunks(query_emb, chunks, top_k=2, min_score=0.0)

    assert len(results) > 0
    # Chunk đầu tiên phải là câu về Bạch Đằng
    assert "Bạch Đằng" in results[0]["content"]
    print(f"✅ Cosine similarity OK → chunk liên quan nhất: '{results[0]['content'][:50]}...'")
    print(f"   Điểm: {results[0]['similarity_score']}")


def test_llm():
    """Test gọi Groq API."""
    from app.services.llm_service import llm_service

    answer = llm_service.generate_answer(
        question="Ngài đã đánh trận Bạch Đằng như thế nào?",
        context="Năm 1288, Trần Hưng Đạo dùng kế cắm cọc trên sông Bạch Đằng đánh tan quân Nguyên.",
        max_tokens=200
    )
    assert len(answer) > 0
    print(f"✅ LLM OK → Trả lời: {answer[:100]}...")


if __name__ == "__main__":
    print("=" * 50)
    print("TEST GIAI ĐOẠN 3 — BUSINESS LOGIC")
    print("=" * 50)

    test_file_processor()
    test_embedding()       # ⏳ Lần đầu tải model ~80MB
    test_cosine_similarity()
    test_llm()             # Cần GROQ_API_KEY hợp lệ

    print("\n🎉 Tất cả test Giai đoạn 3 PASSED!")