"""Test kết nối database và models."""

from app.database.db_connection import test_connection
from app.models.models import DocumentModel

def test_ket_noi():
    ket_qua = test_connection()
    assert ket_qua == True, "❌ Kết nối database thất bại"
    print("✅ Kết nối database OK")

def test_document_model():
    # Thử tạo 1 tài liệu mẫu
    doc_id = DocumentModel.create(
        title="Test tài liệu",
        file_path="/test/test.pdf",
        content="Nội dung test"
    )
    print(f"✅ Tạo tài liệu thành công, id = {doc_id}")

    # Lấy lại và kiểm tra
    doc = DocumentModel.get_by_id(doc_id)
    assert doc["title"] == "Test tài liệu"
    print("✅ Lấy tài liệu thành công")

    # Xóa tài liệu test
    DocumentModel.delete(doc_id)
    print("✅ Xóa tài liệu test thành công")

if __name__ == "__main__":
    test_ket_noi()
    test_document_model()
    print("\n🎉 Tất cả test Giai đoạn 2 PASSED!")