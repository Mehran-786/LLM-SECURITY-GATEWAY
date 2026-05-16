// =========================================================
// Secure AI Gateway — Frontend Logic (app.js)
// =========================================================

const chatContainer = document.getElementById('chatContainer');
const userInput     = document.getElementById('userInput');
const typingRow     = document.getElementById('typingRow');
const sendBtn       = document.getElementById('sendBtn');

// ── Auto-resize textarea ──────────────────────────────────
function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
}

// ── Enter to send (Shift+Enter = newline) ─────────────────
function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

// ── Scroll helper ─────────────────────────────────────────
function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// ── Syntax highlight JSON ─────────────────────────────────
function syntaxHighlight(json) {
    if (typeof json !== 'string') {
        json = JSON.stringify(json, null, 2);
    }
    json = json
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    return json.replace(
        /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
        match => {
            let cls = 'sh-num';
            if (/^"/.test(match)) {
                cls = /:$/.test(match) ? 'sh-key' : 'sh-str';
            } else if (/true|false/.test(match)) {
                cls = 'sh-bool';
            } else if (/null/.test(match)) {
                cls = 'sh-null';
            }
            return `<span class="${cls}">${match}</span>`;
        }
    );
}

// ── Toggle audit accordion ────────────────────────────────
function toggleAudit(id) {
    const content  = document.getElementById(id);
    const chevron  = document.getElementById('chev-' + id);
    const isOpen   = content.classList.toggle('open');
    chevron.style.transform = isOpen ? 'rotate(180deg)' : 'rotate(0deg)';
}

// ── Build audit accordion block ───────────────────────────
function buildAuditBlock(auditData, colorClass, label) {
    const id = 'audit-' + Math.random().toString(36).slice(2, 9);
    return `
        <div class="audit-wrapper ${colorClass}">
            <div class="audit-header" onclick="toggleAudit('${id}')">
                <span class="audit-header-left">
                    <span class="audit-dot"></span>
                    ${label}
                </span>
                <span class="audit-chevron" id="chev-${id}">▼</span>
            </div>
            <pre class="audit-content" id="${id}">${syntaxHighlight(auditData)}</pre>
        </div>
    `;
}

// ── Append a message row ──────────────────────────────────
function appendMessage({ role, bubbleClass, avatarClass, avatarLabel, html }) {
    const row = document.createElement('div');
    row.className = `msg-row ${role}-row`;

    const avatar = document.createElement('div');
    avatar.className = `avatar ${avatarClass}`;
    avatar.textContent = avatarLabel;

    const bubble = document.createElement('div');
    bubble.className = `bubble ${bubbleClass}`;
    bubble.innerHTML = html;

    if (role === 'user') {
        row.appendChild(bubble);
        row.appendChild(avatar);
    } else {
        row.appendChild(avatar);
        row.appendChild(bubble);
    }

    // Insert before typing indicator
    chatContainer.insertBefore(row, typingRow);
    scrollToBottom();
    return bubble;
}

// ── Show / hide typing indicator ──────────────────────────
function showTyping()  { typingRow.style.display = 'flex'; scrollToBottom(); }
function hideTyping()  { typingRow.style.display = 'none'; }

// ── Disable / enable send button ─────────────────────────
function setLoading(on) {
    sendBtn.disabled   = on;
    userInput.disabled = on;
    sendBtn.style.opacity = on ? '0.5' : '1';
}

// ── Main send handler ─────────────────────────────────────
async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    // Render user bubble
    appendMessage({
        role: 'user',
        bubbleClass: 'user-bubble',
        avatarClass: 'user-avatar',
        avatarLabel: '👤',
        html: escapeHtml(text)
    });

    userInput.value = '';
    userInput.style.height = 'auto';
    setLoading(true);
    showTyping();

    try {
        // 1. Run security analysis
        const analyzeRes = await fetch('/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: text })
        });
        const auditData = await analyzeRes.json();

        hideTyping();

        // ── BLOCK ─────────────────────────────────────────
        if (auditData.decision === 'Block') {
            appendMessage({
                role: 'ai',
                bubbleClass: 'blocked-bubble',
                avatarClass: 'ai-avatar',
                avatarLabel: 'AI',
                html: `
                    <div class="blocked-header">🚨 Access Denied</div>
                    <div class="blocked-sub">Your request was blocked by the security policy.</div>
                    ${buildAuditBlock(auditData, 'red-audit', '🔴 Security Audit Log')}
                `
            });
            return;
        }

        // ── ALLOW or MASK ─────────────────────────────────
        showTyping();

        const chatRes = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: auditData.safe_text })
        });
        const chatData = await chatRes.json();

        hideTyping();

        if (auditData.decision === 'Mask') {
            appendMessage({
                role: 'ai',
                bubbleClass: 'ai-bubble',
                avatarClass: 'ai-avatar',
                avatarLabel: 'AI',
                html: `
                    <span class="badge mask-badge">🛡️ Privacy Mask Applied</span>
                    <div>${escapeHtml(chatData.response)}</div>
                    ${buildAuditBlock(auditData, 'amber-audit', '🟡 Privacy Audit Log')}
                `
            });
        } else {
            // Allow
            appendMessage({
                role: 'ai',
                bubbleClass: 'ai-bubble',
                avatarClass: 'ai-avatar',
                avatarLabel: 'AI',
                html: escapeHtml(chatData.response)
            });
        }

    } catch (err) {
        hideTyping();
        appendMessage({
            role: 'ai',
            bubbleClass: 'ai-bubble',
            avatarClass: 'ai-avatar',
            avatarLabel: 'AI',
            html: `<span style="color:var(--red)">⚠️ Connection error. Please check the server.</span>`
        });
    } finally {
        setLoading(false);
    }
}

// ── Simple HTML escape ────────────────────────────────────
function escapeHtml(str) {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;')
        .replace(/\n/g, '<br>');
}
