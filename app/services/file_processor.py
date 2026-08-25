"""
file_processor.py — Đọc file và cắt thành các đoạn nhỏ (chunks).

Quy trình:
1. Nhận file PDF hoặc TXT
2. Trích xuất toàn bộ text
3. Cắt text thành các đoạn nhỏ có overlap
   (overlap giúp không mất ngữ cảnh ở ranh giới đoạn)

Ví dụ chunk_size=500, overlap=50:
   Đoạn 1: ký tự 0   → 500
   Đoạn 2: ký tự 450 → 950   ← lùi lại 50 ký tự (overlap)
   Đoạn 3: ký tự 900 → 1400
"""

import os
import PyPDF2
from app.config import config
from app.utils.logger import get_logger

logger = get_logger(__name__)


def read_pdf(file_path: str) -> str:
    """
    Đọc toàn bộ text từ file PDF.

    Args:
        file_path: Đường dẫn tới file PDF

    Returns:
        Toàn bộ nội dung text của PDF

    Raises:
        FileNotFoundError: Nếu file không tồn tại
        Exception: Nếu không đọc được PDF
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            total_pages = len(reader.pages)
            logger.info(f"📄 Đọc PDF: {total_pages} trang")

            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                text += page_text + "\n"
                logger.debug(f"  Trang {i+1}/{total_pages}: {len(page_text)} ký tự")

        logger.info(f"✅ Đọc PDF xong: tổng {len(text)} ký tự")
        return text

    except Exception as e:
        logger.error(f"❌ Lỗi đọc PDF {file_path}: {e}")
        raise


def read_txt(file_path: str) -> str:
    """
    Đọc toàn bộ text từ file TXT.

    Tự động thử các encoding phổ biến:
    utf-8 → utf-8-sig → cp1252

    Args:
        file_path: Đường dẫn tới file TXT

    Returns:
        Toàn bộ nội dung text
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

    # Thử lần lượt các encoding — tiếng Việt hay gặp vấn đề encoding
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]

    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                text = f.read()
            logger.info(
                f"✅ Đọc TXT xong ({encoding}): {len(text)} ký tự"
            )
            return text
        except UnicodeDecodeError:
            logger.debug(f"  Thử encoding {encoding} thất bại, thử tiếp...")
            continue

    raise Exception(f"Không đọc được file TXT: {file_path}")


def extract_text(file_path: str) -> str:
    """
    Tự động nhận diện loại file và đọc nội dung.

    Args:
        file_path: Đường dẫn tới file (PDF hoặc TXT)

    Returns:
        Toàn bộ nội dung text đã được làm sạch
    """
    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".pdf":
        text = read_pdf(file_path)
    elif extension == ".txt":
        text = read_txt(file_path)
    else:
        raise ValueError(
            f"Định dạng file không hỗ trợ: {extension}. "
            f"Chỉ hỗ trợ PDF và TXT."
        )

    # Làm sạch text cơ bản
    text = clean_text(text)
    return text


def clean_text(text: str) -> str:
    """
    Làm sạch text trước khi xử lý.

    Xử lý:
    - Xóa dòng trắng thừa
    - Chuẩn hóa khoảng trắng
    - Giữ lại ký tự xuống dòng

    Args:
        text: Text thô cần làm sạch

    Returns:
        Text đã được làm sạch
    """
    import re

    # Xóa khoảng trắng đầu/cuối mỗi dòng
    lines = [line.strip() for line in text.splitlines()]

    # Xóa dòng trắng liên tiếp (giữ lại tối đa 1 dòng trắng)
    cleaned_lines = []
    prev_empty = False
    for line in lines:
        if line == "":
            if not prev_empty:
                cleaned_lines.append(line)
            prev_empty = True
        else:
            cleaned_lines.append(line)
            prev_empty = False

    text = "\n".join(cleaned_lines)

    # Xóa khoảng trắng thừa giữa các từ
    text = re.sub(r" {2,}", " ", text)

    return text.strip()


def split_into_chunks(
    text: str,
    chunk_size: int = None,
    overlap: int = None
) -> list[dict]:
    """
    Cắt text thành các đoạn nhỏ có overlap.

    Tại sao cần overlap?
    → Để không mất ngữ cảnh ở ranh giới giữa 2 đoạn.
    → Ví dụ: "...Trần Hưng Đạo sinh năm [hết đoạn 1] 1228..."
      Nếu không overlap, đoạn 2 sẽ không biết ai sinh năm 1228.

    Args:
        text: Nội dung cần cắt
        chunk_size: Số ký tự mỗi đoạn (mặc định từ config)
        overlap: Số ký tự lấy chồng lên (mặc định từ config)

    Returns:
        Danh sách dict, mỗi dict gồm:
        - chunk_index: thứ tự đoạn
        - content: nội dung đoạn
        - char_start: vị trí bắt đầu trong text gốc
        - char_end: vị trí kết thúc trong text gốc
    """
    # Dùng config nếu không truyền tham số
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP

    if not text.strip():
        logger.warning("⚠️ Text rỗng, không thể cắt chunks")
        return []

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        end = start + chunk_size

        # Nếu chưa hết text, cố gắng cắt tại ranh giới câu
        if end < len(text):
            # Tìm dấu chấm câu gần nhất để cắt tự nhiên hơn
            natural_end = find_sentence_boundary(text, end)
            if natural_end > start:
                end = natural_end

        chunk_content = text[start:end].strip()

        # Bỏ qua chunk rỗng hoặc quá ngắn
        if len(chunk_content) > 50:
            chunks.append({
                "chunk_index": chunk_index,
                "content": chunk_content,
                "char_start": start,
                "char_end": end
            })
            chunk_index += 1

        # Bước tiếp theo: lùi lại overlap ký tự
        start = end - overlap

    logger.info(
        f"✅ Cắt xong: {len(chunks)} chunks "
        f"(chunk_size={chunk_size}, overlap={overlap})"
    )
    return chunks


def find_sentence_boundary(text: str, position: int) -> int:
    """
    Tìm vị trí kết thúc câu gần nhất tính từ position.
    Giúp cắt chunk tại ranh giới câu tự nhiên hơn.

    Args:
        text: Toàn bộ nội dung
        position: Vị trí muốn cắt

    Returns:
        Vị trí cắt tốt nhất (tại dấu câu hoặc xuống dòng)
    """
    # Tìm trong khoảng 100 ký tự sau position
    search_end = min(position + 100, len(text))
    search_text = text[position:search_end]

    # Ưu tiên: xuống dòng > dấu chấm > dấu chấm hỏi > dấu chấm than
    for char in ["\n", ".", "?", "!"]:
        idx = search_text.find(char)
        if idx != -1:
            return position + idx + 1

    return position


def process_file(file_path: str) -> dict:
    """
    Hàm tổng hợp: đọc file và cắt thành chunks.
    Đây là hàm được gọi từ bên ngoài.

    Args:
        file_path: Đường dẫn tới file cần xử lý

    Returns:
        dict gồm:
        - text: toàn bộ nội dung
        - chunks: danh sách các đoạn đã cắt
        - total_chars: tổng số ký tự
        - total_chunks: số lượng chunks
    """
    logger.info(f"🔄 Bắt đầu xử lý file: {file_path}")

    # Bước 1: Đọc file
    text = extract_text(file_path)

    # Bước 2: Cắt chunks
    chunks = split_into_chunks(text)

    result = {
        "text": text,
        "chunks": chunks,
        "total_chars": len(text),
        "total_chunks": len(chunks)
    }

    logger.info(
        f"✅ Xử lý file xong: "
        f"{result['total_chars']} ký tự, "
        f"{result['total_chunks']} chunks"
    )
    return result