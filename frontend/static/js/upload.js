/**
 * upload.js — Toàn bộ logic cho trang Quản Lý Tài Liệu
 *
 * Chức năng:
 * - Upload file PDF/TXT lên server
 * - Kéo thả file vào vùng upload
 * - Hiển thị danh sách tài liệu đã upload
 * - Xóa tài liệu
 * - Thanh tiến trình upload
 * - Toast thông báo kết quả
 */

// ============================================================
// 1. KHỞI TẠO
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  loadDocuments();
  bindEvents();
});

// ============================================================
// 2. UPLOAD FILE
// ============================================================

/**
 * Xử lý upload 1 file lên server.
 *
 * Quy trình:
 * 1. Kiểm tra loại file hợp lệ
 * 2. Hiển thị loading overlay
 * 3. Gửi file qua FormData
 * 4. Cập nhật danh sách tài liệu
 *
 * @param {File} file - File cần upload
 */
async function uploadFile(file) {
  // Kiểm tra loại file
  const allowedTypes = ['.pdf', '.txt'];
  const ext = '.' + file.name.split('.').pop().toLowerCase();
  if (!allowedTypes.includes(ext)) {
    showToast(`❌ Chỉ hỗ trợ PDF và TXT. File: ${ext}`, 'error');
    return;
  }

  // Kiểm tra dung lượng (50MB)
  const maxSize = 50 * 1024 * 1024;
  if (file.size > maxSize) {
    showToast(
      `❌ File quá lớn: ${(file.size / 1024 / 1024).toFixed(1)}MB (tối đa 50MB)`,
      'error'
    );
    return;
  }

  // Hiện loading
  showLoading(`Đang xử lý: ${file.name}`);
  showProgress(0, 'Đang gửi tài liệu lên máy chủ...');

  const formData = new FormData();
  formData.append('file', file);

  try {
    // Giả lập thanh tiến trình (API không hỗ trợ stream progress)
    animateProgress(0, 30, 800, 'Đang đọc tài liệu...');

    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });

    animateProgress(30, 70, 1000, 'Đang tạo embedding...');

    const data = await res.json();

    animateProgress(70, 100, 600, 'Hoàn tất!');

    if (data.success) {
      showToast(
        `✅ Upload thành công: ${data.data.title} (${data.data.total_chunks} đoạn)`,
        'success',
        4000
      );
      // Tải lại danh sách tài liệu
      await loadDocuments();
    } else {
      showToast(`❌ Lỗi: ${data.detail || 'Không xác định'}`, 'error');
    }

  } catch (err) {
    showToast('❌ Mất kết nối máy chủ. Hãy thử lại.', 'error');
    console.error('Lỗi upload:', err);
  } finally {
    setTimeout(() => {
      hideLoading();
      hideProgress();
    }, 800);
  }
}

// ============================================================
// 3. DANH SÁCH TÀI LIỆU
// ============================================================

/**
 * Tải và hiển thị danh sách tất cả tài liệu từ server.
 */
async function loadDocuments() {
  try {
    const res  = await fetch('/api/documents');
    const data = await res.json();

    if (data.success) {
      renderDocuments(data.data);
      updateDocCount(data.total);
    }
  } catch (err) {
    console.error('Không tải được danh sách tài liệu:', err);
    showToast('⚠️ Không tải được danh sách tài liệu', 'error');
  }
}

/**
 * Render danh sách tài liệu ra giao diện.
 * @param {Array} documents - Danh sách tài liệu từ API
 */
function renderDocuments(documents) {
  const list       = document.getElementById('documents-list');
  const emptyState = document.getElementById('empty-state');

  // Xóa nội dung cũ (trừ empty-state)
  Array.from(list.children).forEach(child => {
    if (child.id !== 'empty-state') child.remove();
  });

  if (!documents || documents.length === 0) {
    emptyState.style.display = 'block';
    return;
  }

  emptyState.style.display = 'none';

  documents.forEach(doc => {
    const item = createDocumentItem(doc);
    list.appendChild(item);
  });
}

/**
 * Tạo element HTML cho 1 tài liệu trong danh sách.
 * @param {Object} doc - Thông tin tài liệu
 * @returns {HTMLElement}
 */
function createDocumentItem(doc) {
  const item = document.createElement('div');
  item.classList.add('document-item');
  item.dataset.docId = doc.id;

  // Xác định icon theo loại file
  const isProcessed = doc.is_processed;
  const ext         = doc.file_path.split('.').pop().toUpperCase();
  const icon        = ext === 'PDF' ? '📄' : '📝';

  // Format ngày giờ
  const uploadDate = new Date(doc.uploaded_at).toLocaleDateString('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });

  item.innerHTML = `
    <div class="doc-info">
      <div class="doc-icon">${icon}</div>
      <div>
        <div class="doc-title" title="${escapeHtml(doc.title)}">${escapeHtml(doc.title)}</div>
        <div class="doc-meta">Upload: ${uploadDate} · ${ext}</div>
      </div>
    </div>
    <span class="doc-status ${isProcessed ? 'processed' : 'pending'}">
      ${isProcessed ? '✅ Sẵn sàng' : '⏳ Đang xử lý'}
    </span>
    <button
      class="btn btn-danger"
      data-doc-id="${doc.id}"
      data-doc-title="${escapeHtml(doc.title)}"
      title="Xóa tài liệu này"
    >
      🗑️
    </button>
  `;

  // Gắn sự kiện xóa cho nút trong item này
  const deleteBtn = item.querySelector('.btn-danger');
  deleteBtn.addEventListener('click', () => {
    deleteDocument(doc.id, doc.title);
  });

  return item;
}

/**
 * Cập nhật badge số lượng tài liệu.
 * @param {number} count
 */
function updateDocCount(count) {
  const badge = document.getElementById('doc-count');
  if (badge) badge.textContent = count;
}

// ============================================================
// 4. XÓA TÀI LIỆU
// ============================================================

/**
 * Xóa 1 tài liệu khỏi hệ thống.
 * @param {number} docId    - ID tài liệu
 * @param {string} docTitle - Tên tài liệu (để hiển thị confirm)
 */
async function deleteDocument(docId, docTitle) {
  const confirmed = confirm(
    `Xóa tài liệu "${docTitle}"?\n\nViệc này sẽ xóa toàn bộ dữ liệu đã embedding và không thể hoàn tác.`
  );
  if (!confirmed) return;

  try {
    const res  = await fetch(`/api/documents/${docId}`, { method: 'DELETE' });
    const data = await res.json();

    if (data.success) {
      showToast(`🗑️ Đã xóa: ${docTitle}`, 'success');
      await loadDocuments();
    } else {
      showToast(`❌ Lỗi xóa: ${data.detail}`, 'error');
    }
  } catch (err) {
    showToast('❌ Không thể xóa tài liệu', 'error');
    console.error('Lỗi xóa tài liệu:', err);
  }
}

// ============================================================
// 5. UI HELPERS
// ============================================================

/**
 * Hiện loading overlay với text tùy chỉnh.
 * @param {string} text - Nội dung loading text
 */
function showLoading(text = 'Đang xử lý...') {
  const overlay = document.getElementById('loading-overlay');
  const textEl  = document.getElementById('loading-text');
  if (textEl) textEl.textContent = text;
  overlay.classList.add('visible');
}

/** Ẩn loading overlay */
function hideLoading() {
  document.getElementById('loading-overlay').classList.remove('visible');
}

/**
 * Hiện thanh tiến trình.
 * @param {number} percent  - Phần trăm (0-100)
 * @param {string} text     - Text mô tả bước đang làm
 */
function showProgress(percent, text) {
  const wrap = document.getElementById('upload-progress-wrap');
  const bar  = document.getElementById('upload-progress-bar');
  const txt  = document.getElementById('upload-progress-text');

  wrap.classList.add('visible');
  bar.style.width  = `${percent}%`;
  txt.textContent  = text;
}

/** Ẩn thanh tiến trình */
function hideProgress() {
  const wrap = document.getElementById('upload-progress-wrap');
  const bar  = document.getElementById('upload-progress-bar');
  wrap.classList.remove('visible');
  bar.style.width = '0%';
}

/**
 * Animate thanh tiến trình từ from → to trong duration ms.
 * @param {number} from       - % bắt đầu
 * @param {number} to         - % kết thúc
 * @param {number} duration   - Thời gian (ms)
 * @param {string} text       - Text mô tả
 */
function animateProgress(from, to, duration, text) {
  const bar = document.getElementById('upload-progress-bar');
  const txt = document.getElementById('upload-progress-text');

  if (txt) txt.textContent = text;

  const start     = performance.now();
  const startPct  = from;
  const deltaPct  = to - from;

  function step(now) {
    const elapsed  = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const current  = startPct + deltaPct * progress;
    if (bar) bar.style.width = `${current}%`;
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

/**
 * Hiển thị toast thông báo.
 * @param {string} message            - Nội dung
 * @param {'success'|'error'} type    - Loại
 * @param {number} duration           - Thời gian hiển thị (ms)
 */
function showToast(message, type = 'success', duration = 3000) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className   = `toast ${type} show`;
  setTimeout(() => toast.classList.remove('show'), duration);
}

/**
 * Escape HTML để tránh XSS khi render tên file từ server.
 * @param {string} str
 * @returns {string}
 */
function escapeHtml(str) {
  const map = { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#039;' };
  return String(str).replace(/[&<>"']/g, m => map[m]);
}

// ============================================================
// 6. GẮN SỰ KIỆN
// ============================================================

/**
 * Gắn tất cả event listeners cho trang upload.
 */
function bindEvents() {
  const zone      = document.getElementById('upload-zone');
  const fileInput = document.getElementById('file-input');
  const chooseBtn = document.getElementById('btn-choose-file');

  // Nút "Chọn Tài Liệu" → mở hộp thoại file
  chooseBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
  });

  // Bấm vào zone cũng mở file picker
  zone.addEventListener('click', () => fileInput.click());

  // Chọn file qua input
  fileInput.addEventListener('change', (e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
      // Upload tuần tự từng file
      uploadFilesSequentially(files);
    }
    // Reset input để có thể chọn lại cùng file
    e.target.value = '';
  });

  // ---- Kéo thả file ----
  zone.addEventListener('dragenter', (e) => {
    e.preventDefault();
    zone.classList.add('dragover');
  });

  zone.addEventListener('dragover', (e) => {
    e.preventDefault(); // Bắt buộc để cho phép drop
    zone.classList.add('dragover');
  });

  zone.addEventListener('dragleave', (e) => {
    // Chỉ bỏ class khi rời khỏi zone thật sự (không phải vào element con)
    if (!zone.contains(e.relatedTarget)) {
      zone.classList.remove('dragover');
    }
  });

  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('dragover');
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      uploadFilesSequentially(files);
    }
  });
}

/**
 * Upload nhiều file tuần tự (1 xong mới upload cái tiếp).
 * @param {File[]} files - Danh sách file cần upload
 */
async function uploadFilesSequentially(files) {
  for (const file of files) {
    await uploadFile(file);
  }
}