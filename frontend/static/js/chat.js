/**
 * chat.js — Toàn bộ logic cho trang Chat
 *
 * Chức năng:
 * - Quản lý session_id (tạo mới hoặc lấy từ localStorage)
 * - Gửi câu hỏi lên API /api/chat
 * - Hiển thị tin nhắn người dùng & bot
 * - Tải lịch sử chat khi vào trang
 * - Xóa lịch sử chat
 * - Auto-resize textarea
 * - Gửi bằng phím Enter
 */

// ============================================================
// 1. KHỞI TẠO — Chạy khi trang load xong
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  initSession();
  loadChatHistory();
  bindEvents();
});

// ============================================================
// 2. QUẢN LÝ SESSION
// ============================================================

/** Tên key lưu session_id trong localStorage */
const SESSION_KEY = 'hungdao_session_id';

/**
 * Lấy session_id hiện tại.
 * Nếu chưa có → tạo mới và lưu vào localStorage.
 * @returns {string} session_id
 */
function getSessionId() {
  let sessionId = localStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId = generateId();
    localStorage.setItem(SESSION_KEY, sessionId);
  }
  return sessionId;
}

/**
 * Khởi tạo phiên chat.
 * Gọi API tạo session trên server nếu cần.
 */
async function initSession() {
  const sessionId = getSessionId();
  try {
    await fetch('/api/chat/new-session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    });
  } catch (err) {
    // Không cần báo lỗi — session sẽ tự tạo khi chat
    console.warn('Không tạo được session trước:', err.message);
  }
}

/**
 * Tạo ID ngẫu nhiên dạng hex.
 * @returns {string} 16 ký tự hex
 */
function generateId() {
  return Array.from(crypto.getRandomValues(new Uint8Array(8)))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

// ============================================================
// 3. LOAD LỊCH SỬ CHAT
// ============================================================

/**
 * Tải lịch sử chat từ server và hiển thị lên giao diện.
 * Gọi khi vào trang để khôi phục cuộc trò chuyện trước.
 */
async function loadChatHistory() {
  const sessionId = getSessionId();
  try {
    const res = await fetch(`/api/chat/history/${sessionId}`);
    const data = await res.json();

    if (data.success && data.messages && data.messages.length > 0) {
      // Ẩn tin nhắn chào mừng nếu đã có lịch sử
      hideWelcome();

      data.messages.forEach(msg => {
        appendMessage('user', msg.user_message);
        appendMessage('bot', msg.bot_response);
      });

      scrollToBottom();
    }
  } catch (err) {
    console.warn('Không tải được lịch sử chat:', err.message);
  }
}

// ============================================================
// 4. GỬI TIN NHẮN
// ============================================================

/** Biến theo dõi trạng thái đang chờ phản hồi */
let isWaiting = false;

/**
 * Xử lý khi người dùng gửi câu hỏi.
 * Kiểm tra input → gửi API → hiển thị kết quả.
 */
async function sendMessage() {
  if (isWaiting) return;

  const input = document.getElementById('chat-input');
  const question = input.value.trim();

  // Không gửi nếu câu hỏi rỗng
  if (!question) return;

  // Xóa input ngay
  input.value = '';
  autoResizeTextarea(input);

  // Ẩn welcome nếu còn hiển thị
  hideWelcome();

  // Hiển thị tin nhắn người dùng
  appendMessage('user', question);
  scrollToBottom();

  // Bật trạng thái chờ
  setWaiting(true);

  // Hiện typing indicator
  const typingId = showTyping();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: question,
        session_id: getSessionId()
      })
    });

    const data = await res.json();

    // Xóa typing indicator
    removeTyping(typingId);

    if (data.success) {
      appendMessage('bot', data.data.answer);

      // Cảnh báo nếu không tìm được tài liệu liên quan
      if (!data.data.context_found) {
        showToast(
          '⚠️ Không tìm thấy sử liệu liên quan — hãy upload thêm tài liệu',
          'error',
          4000
        );
      }
    } else {
      appendMessage('bot', 'Ta gặp sự cố, hậu sinh hãy hỏi lại sau.');
      showToast('❌ Lỗi: ' + (data.detail || 'Không xác định'), 'error');
    }

  } catch (err) {
    removeTyping(typingId);
    appendMessage('bot', 'Kết nối gián đoạn, hậu sinh hãy thử lại.');
    showToast('❌ Mất kết nối máy chủ', 'error');
    console.error('Lỗi gửi tin nhắn:', err);

  } finally {
    setWaiting(false);
    scrollToBottom();
  }
}

// ============================================================
// 5. HIỂN THỊ TIN NHẮN
// ============================================================

/**
 * Thêm 1 tin nhắn vào khung hội thoại.
 * @param {'user'|'bot'} role  - Người gửi
 * @param {string}       text  - Nội dung tin nhắn
 */
function appendMessage(role, text) {
  const container = document.getElementById('chat-messages');

  const msgEl = document.createElement('div');
  msgEl.classList.add('message', role);

  // Avatar
  const avatar = document.createElement('div');
  avatar.classList.add('message-avatar');
  avatar.textContent = role === 'bot' ? '🏯' : '👤';

  // Bong bóng tin nhắn
  const bubble = document.createElement('div');
  bubble.classList.add('message-bubble');
  // Cho phép xuống dòng và giữ khoảng trắng
  bubble.style.whiteSpace = 'pre-wrap';
  bubble.textContent = text;

  msgEl.appendChild(avatar);
  msgEl.appendChild(bubble);
  container.appendChild(msgEl);
}

/**
 * Hiển thị typing indicator (3 chấm nhảy).
 * @returns {string} id của element để xóa sau
 */
function showTyping() {
  const container = document.getElementById('chat-messages');
  const id = 'typing-' + Date.now();

  const el = document.createElement('div');
  el.classList.add('typing-indicator');
  el.id = id;
  el.innerHTML = `
    <div class="message-avatar" style="
      background: linear-gradient(135deg,#8b1a1a,#5a1010);
      border:1px solid #9b7228; width:38px; height:38px;
      border-radius:50%; display:flex; align-items:center;
      justify-content:center; font-size:1.1rem; flex-shrink:0;">
      🏯
    </div>
    <div class="typing-bubble">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>
  `;
  container.appendChild(el);
  scrollToBottom();
  return id;
}

/**
 * Xóa typing indicator khỏi giao diện.
 * @param {string} id - id của element cần xóa
 */
function removeTyping(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

// ============================================================
// 6. XÓA LỊCH SỬ CHAT
// ============================================================

/**
 * Xóa toàn bộ lịch sử chat:
 * - Gọi API xóa trên server
 * - Xóa session cũ, tạo session mới
 * - Làm sạch giao diện
 */
async function clearChat() {
  const confirmed = confirm(
    'Xóa toàn bộ lịch sử hội thoại?\nViệc này không thể hoàn tác.'
  );
  if (!confirmed) return;

  const sessionId = getSessionId();

  try {
    await fetch(`/api/chat/history/${sessionId}`, { method: 'DELETE' });
  } catch (err) {
    console.warn('Không xóa được lịch sử trên server:', err.message);
  }

  // Tạo session mới
  const newSession = generateId();
  localStorage.setItem(SESSION_KEY, newSession);

  // Xóa toàn bộ tin nhắn trên giao diện
  const container = document.getElementById('chat-messages');
  container.innerHTML = '';

  // Hiện lại welcome message
  showWelcome();

  showToast('🗑️ Đã xóa lịch sử hội thoại', 'success');
}

// ============================================================
// 7. HELPER FUNCTIONS
// ============================================================

/** Cuộn xuống cuối khung chat */
function scrollToBottom() {
  const container = document.getElementById('chat-messages');
  container.scrollTop = container.scrollHeight;
}

/** Ẩn tin nhắn chào mừng */
function hideWelcome() {
  const el = document.getElementById('welcome-message');
  if (el) el.style.display = 'none';
}

/** Hiện lại tin nhắn chào mừng */
function showWelcome() {
  const container = document.getElementById('chat-messages');

  // Tạo lại welcome message
  const welcome = document.createElement('div');
  welcome.className = 'welcome-message';
  welcome.id = 'welcome-message';
  welcome.innerHTML = `
    <span class="welcome-emblem">⚔️</span>
    <div class="welcome-title">Kính chào Hậu Sinh</div>
    <div class="ornament-divider">❖</div>
    <p class="welcome-text">
      Ta là Trần Hưng Đạo, Quốc Công Tiết Chế của Đại Việt.<br/>
      Hậu sinh có điều gì muốn hỏi về lịch sử, trận mạc,<br/>
      hay binh pháp của ta, cứ hỏi, ta sẽ thuật lại.
    </p>
  `;
  container.appendChild(welcome);
}

/**
 * Bật / tắt trạng thái chờ phản hồi.
 * @param {boolean} waiting - true = đang chờ
 */
function setWaiting(waiting) {
  isWaiting = waiting;
  const btn   = document.getElementById('chat-send-btn');
  const input = document.getElementById('chat-input');
  const dot   = document.getElementById('status-dot');
  const text  = document.getElementById('status-text');

  btn.disabled   = waiting;
  input.disabled = waiting;

  if (waiting) {
    dot.style.background  = '#c9983a';
    text.textContent      = 'Đang trả lời...';
  } else {
    dot.style.background  = '#5a8a5a';
    text.textContent      = 'Sẵn sàng';
  }
}

/**
 * Auto-resize textarea theo nội dung.
 * @param {HTMLTextAreaElement} el
 */
function autoResizeTextarea(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

/**
 * Hiển thị toast thông báo.
 * @param {string} message  - Nội dung thông báo
 * @param {'success'|'error'} type - Loại thông báo
 * @param {number} duration - Thời gian hiển thị (ms)
 */
function showToast(message, type = 'success', duration = 3000) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className   = `toast ${type} show`;

  setTimeout(() => {
    toast.classList.remove('show');
  }, duration);
}

// ============================================================
// 8. GẮN SỰ KIỆN
// ============================================================

/**
 * Gắn tất cả event listeners cho giao diện.
 * Gọi 1 lần khi DOMContentLoaded.
 */
function bindEvents() {
  const input   = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send-btn');
  const clearBtn = document.getElementById('btn-clear-chat');

  // Nút gửi
  sendBtn.addEventListener('click', sendMessage);

  // Phím Enter → gửi, Shift+Enter → xuống dòng
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Auto-resize textarea khi gõ
  input.addEventListener('input', () => autoResizeTextarea(input));

  // Nút xóa lịch sử
  clearBtn.addEventListener('click', clearChat);
}