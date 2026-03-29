let currentSessionId = null;
let currentRole = null;
let isSending = false;

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
}

async function authenticate() {
    const code = document.getElementById('access-code').value;
    const errorEl = document.getElementById('auth-error');
    errorEl.classList.add('hidden');

    try {
        const resp = await fetch('/api/auth', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ passphrase: code }),
        });

        if (resp.ok) {
            showScreen('home-screen');
        } else {
            errorEl.textContent = 'Invalid access code';
            errorEl.classList.remove('hidden');
        }
    } catch (e) {
        errorEl.textContent = 'Connection error. Please try again.';
        errorEl.classList.remove('hidden');
    }
}

async function checkAuth() {
    try {
        const resp = await fetch('/api/auth/check');
        if (resp.ok) {
            showScreen('home-screen');
            return;
        }
    } catch (e) {
        // Fall through to auth screen
    }
    showScreen('auth-screen');
}

async function startSession(role) {
    try {
        const resp = await fetch('/api/session/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role }),
        });

        if (!resp.ok) throw new Error('Failed to start session');

        const data = await resp.json();
        currentSessionId = data.session_id;
        currentRole = role;

        document.getElementById('chat-messages').innerHTML = '';

        if (role === 'clinician') {
            document.getElementById('clinician-controls').classList.remove('hidden');
            document.getElementById('disorder-panel').classList.add('hidden');
        } else {
            document.getElementById('clinician-controls').classList.add('hidden');
            document.getElementById('disorder-panel').classList.remove('hidden');
            renderDisorderInfo(data.disorder_info);
            await sendInitialMessage();
        }

        showScreen('chat-screen');
    } catch (e) {
        alert('Error starting session: ' + e.message);
    }
}

function renderDisorderInfo(info) {
    const details = document.getElementById('disorder-details');
    details.innerHTML = `
        <h4>Disorder: ${info.name}</h4>
        <p>${info.symptoms}</p>
        <h4>Brain Region</h4>
        <p>${info.brain_region}</p>
        <h4>How to Test</h4>
        <p>${info.how_to_test}</p>
    `;
}

function toggleDisorderPanel() {
    const details = document.getElementById('disorder-details');
    const toggleText = document.getElementById('panel-toggle-text');
    if (details.classList.contains('hidden')) {
        details.classList.remove('hidden');
        toggleText.textContent = 'Hide Disorder Info';
    } else {
        details.classList.add('hidden');
        toggleText.textContent = 'Show Disorder Info';
    }
}

function newSession() {
    currentSessionId = null;
    currentRole = null;
    closeDiagnoseModal();
    showScreen('home-screen');
}

async function sendInitialMessage() {
    await streamResponse('');
}

async function sendMessage() {
    if (isSending) return;

    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    input.value = '';
    input.style.height = 'auto';

    appendMessage('user', message);
    await streamResponse(message);
}

async function streamResponse(message) {
    isSending = true;
    document.getElementById('send-btn').disabled = true;

    try {
        const resp = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: currentSessionId, message }),
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || 'Chat request failed');
        }

        const msgEl = appendMessage('assistant', '');
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const dataStr = line.slice(6);
                let data;
                try {
                    data = JSON.parse(dataStr);
                } catch {
                    continue;
                }

                if (data.token) {
                    msgEl.textContent += data.token;
                    scrollToBottom();
                }

                if (data.done && data.diagnosis_proposed) {
                    showDiagnosisResult(data);
                }
            }
        }
    } catch (e) {
        appendMessage('assistant', 'Error: ' + e.message);
    } finally {
        isSending = false;
        document.getElementById('send-btn').disabled = false;
    }
}

function appendMessage(role, content) {
    const container = document.getElementById('chat-messages');
    const el = document.createElement('div');
    el.className = `message ${role}`;
    el.textContent = content;
    container.appendChild(el);
    scrollToBottom();
    return el;
}

function scrollToBottom() {
    const container = document.getElementById('chat-messages');
    container.scrollTop = container.scrollHeight;
}

function handleChatKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function openDiagnoseModal() {
    document.getElementById('diagnose-modal').classList.remove('hidden');
    document.getElementById('diagnosis-input').value = '';
    document.getElementById('diagnosis-input').focus();
    const feedback = document.getElementById('diagnose-feedback');
    feedback.classList.add('hidden');
    feedback.className = 'hidden';
}

function closeDiagnoseModal() {
    document.getElementById('diagnose-modal').classList.add('hidden');
}

async function submitDiagnosis() {
    const diagnosis = document.getElementById('diagnosis-input').value.trim();
    if (!diagnosis) return;

    const feedback = document.getElementById('diagnose-feedback');

    try {
        const resp = await fetch('/api/diagnose', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: currentSessionId, diagnosis }),
        });

        const data = await resp.json();

        if (data.correct) {
            closeDiagnoseModal();
            showResult('correct', data.disorder, `You correctly diagnosed: ${data.disorder.name}`);
        } else {
            feedback.textContent = data.message;
            feedback.className = 'incorrect';
            feedback.classList.remove('hidden');
        }
    } catch (e) {
        feedback.textContent = 'Error submitting diagnosis';
        feedback.className = 'incorrect';
        feedback.classList.remove('hidden');
    }
}

async function revealDiagnosis() {
    if (!confirm('Are you sure you want to reveal the diagnosis?')) return;

    try {
        const resp = await fetch('/api/reveal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: currentSessionId }),
        });

        const data = await resp.json();
        showResult('revealed', data.disorder, `The diagnosis was: ${data.disorder.name}`, data.feedback);
    } catch (e) {
        alert('Error revealing diagnosis');
    }
}

function showDiagnosisResult(data) {
    const outcomeType = data.correct ? 'correct' : 'incorrect';
    const outcomeMsg = data.correct
        ? `The clinician correctly diagnosed: ${data.disorder.name}. You portrayed the disorder convincingly!`
        : `The clinician diagnosed: ${data.diagnosed_as}, but the actual disorder was: ${data.disorder.name}.`;
    showResult(outcomeType, data.disorder, outcomeMsg, data.feedback);
}

function showResult(outcomeType, disorder, outcomeMessage, feedback) {
    const content = document.getElementById('result-content');
    const feedbackHtml = feedback
        ? `<h3>Feedback</h3><p class="detail-text">${feedback}</p>`
        : '';
    content.innerHTML = `
        <h2>Session Complete</h2>
        <div class="result-outcome ${outcomeType}">${outcomeMessage}</div>
        ${feedbackHtml}
        <h3>Disorder: ${disorder.name}</h3>
        <h3>Category</h3>
        <p class="detail-text">${disorder.category || ''}</p>
        <h3>Symptoms</h3>
        <p class="detail-text">${disorder.symptoms}</p>
        <h3>Brain Region</h3>
        <p class="detail-text">${disorder.brain_region}</p>
        <h3>How to Test</h3>
        <p class="detail-text">${disorder.how_to_test}</p>
    `;
    showScreen('result-screen');
}

document.addEventListener('DOMContentLoaded', () => {
    const textarea = document.getElementById('chat-input');
    if (textarea) {
        textarea.addEventListener('input', () => {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
        });
    }

    checkAuth();
});
