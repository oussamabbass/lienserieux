const chatBox = document.getElementById('chatBox');
const chatForm = document.getElementById('chatForm');
const textInput = document.getElementById('textInput');
const sendButton = document.getElementById('sendBtn');
const chatStatus = document.getElementById('chatStatus');
const mediaInput = document.getElementById('mediaInput');
const mediaPreview = document.getElementById('mediaPreview');

if (chatBox) {
    chatBox.scrollTop = chatBox.scrollHeight;
}

let lastMessageId = Number(chatBox?.dataset.lastMessageId || 0);

function appendMessage(message) {
    if (!chatBox) return;

    const wasNearBottom = chatBox.scrollHeight - chatBox.scrollTop - chatBox.clientHeight < 100;
    chatBox.querySelector('.chat-empty')?.remove();

    const isSent = Number(message.sender_id) === Number(currentUserId);
    const row = document.createElement('div');
    row.className = `message-row${isSent ? ' message-row--sent' : ''}`;
    row.dataset.messageId = String(message.id);

    const bubble = document.createElement('div');
    bubble.className = `message-bubble message-bubble--${isSent ? 'sent' : 'received'}`;

    const content = String(message.content || '');

    if (message.message_type === 'audio' && content.startsWith('uploads/audio/')) {
        const audio = document.createElement('audio');
        audio.className = 'message-audio';
        audio.controls = true;
        audio.preload = 'metadata';
        audio.src = `/static/${content}`;
        audio.setAttribute('aria-label', 'Message vocal');
        bubble.append(audio);
    } else if (message.message_type === 'image' && content.startsWith('uploads/media/')) {
        const link = document.createElement('a');
        link.href = `/static/${content}`;
        link.target = '_blank';
        link.rel = 'noopener';
        const img = document.createElement('img');
        img.className = 'message-media message-media--image';
        img.src = `/static/${content}`;
        img.alt = 'Photo';
        img.loading = 'lazy';
        link.append(img);
        bubble.append(link);
    } else if (message.message_type === 'video' && content.startsWith('uploads/media/')) {
        const video = document.createElement('video');
        video.className = 'message-media message-media--video';
        video.controls = true;
        video.preload = 'metadata';
        video.src = `/static/${content}`;
        bubble.append(video);
    } else if (message.message_type === 'text') {
        const text = document.createElement('p');
        text.textContent = content;
        bubble.append(text);
    }

    const time = document.createElement('time');
    time.className = 'message-time';
    time.dateTime = message.created_at || '';
    time.textContent = (message.created_at || '').slice(11, 16);
    bubble.append(time);

    if (isSent && message.is_read) {
        const readStatus = document.createElement('small');
        readStatus.className = 'message-read-status';
        readStatus.textContent = 'Lu';
        bubble.append(readStatus);
    }

    if (isSent) {
        const delBtn = document.createElement('button');
        delBtn.type = 'button';
        delBtn.className = 'message-delete';
        delBtn.dataset.messageId = String(message.id);
        delBtn.setAttribute('aria-label', 'Supprimer ce message');
        delBtn.title = 'Supprimer';
        delBtn.textContent = '×';
        bubble.append(delBtn);
    }

    row.append(bubble);
    chatBox.append(row);
    lastMessageId = Math.max(lastMessageId, Number(message.id) || 0);
    chatBox.dataset.lastMessageId = String(lastMessageId);
    if (wasNearBottom) chatBox.scrollTop = chatBox.scrollHeight;
}

async function refreshMessages() {
    if (!chatBox || document.hidden || !receiverId) return;
    try {
        const response = await fetch(`/chat/${receiverId}/updates?after=${lastMessageId}`, { cache: 'no-store' });
        if (!response.ok) return;
        const data = await response.json();
        data.messages?.forEach(appendMessage);
        data.read_ids?.forEach((id) => {
            const row = chatBox.querySelector(`[data-message-id="${Number(id)}"]`);
            if (!row || !row.classList.contains('message-row--sent')) return;
            const bubble = row.querySelector('.message-bubble');
            if (bubble && !bubble.querySelector('.message-read-status')) {
                const readStatus = document.createElement('small');
                readStatus.className = 'message-read-status';
                readStatus.textContent = 'Lu';
                bubble.append(readStatus);
            }
        });
    } catch (error) {
        // ignore
    }
}

if (chatBox) window.setInterval(refreshMessages, 4000);

function showChatStatus(message, isError = false) {
    if (!chatStatus) return;
    chatStatus.textContent = message;
    chatStatus.hidden = !message;
    chatStatus.classList.toggle('chat-feedback--error', isError);
}

async function sendTextMessage(event) {
    event?.preventDefault();
    const content = textInput?.value.trim();
    if (!content || !chatForm || !sendButton) return;

    const formData = new FormData(chatForm);
    formData.set('message_type', 'text');
    formData.set('content', content);
    sendButton.disabled = true;
    sendButton.textContent = 'Envoi…';
    showChatStatus('Envoi du message…');

    try {
        const response = await fetch(chatForm.action, { method: 'POST', body: formData });
        if (!response.ok) throw new Error('fail');
        textInput.value = '';
        window.location.reload();
    } catch (error) {
        showChatStatus('Le message n’a pas été envoyé. Réessayez.', true);
    } finally {
        if (sendButton.isConnected) {
            sendButton.disabled = false;
            sendButton.textContent = 'Envoyer';
        }
    }
}

async function sendMediaFile(file) {
    if (!file || !chatForm || !sendButton) return;

    const isVideo = file.type.startsWith('video/');
    const isImage = file.type.startsWith('image/');
    if (!isImage && !isVideo) {
        showChatStatus('Choisis une photo ou une vidéo.', true);
        return;
    }

    const formData = new FormData();
    formData.set('receiver_id', chatForm.querySelector('[name="receiver_id"]').value);
    formData.set('message_type', isVideo ? 'video' : 'image');
    formData.set('media_file', file);

    sendButton.disabled = true;
    showChatStatus(isVideo ? 'Envoi de la vidéo…' : 'Envoi de la photo…');

    try {
        const response = await fetch(chatForm.action, { method: 'POST', body: formData });
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.message || 'fail');
        }
        if (mediaInput) mediaInput.value = '';
        if (mediaPreview) {
            mediaPreview.hidden = true;
            mediaPreview.textContent = '';
        }
        window.location.reload();
    } catch (error) {
        showChatStatus(error.message || 'Envoi impossible. Réessayez.', true);
    } finally {
        if (sendButton.isConnected) {
            sendButton.disabled = false;
            sendButton.textContent = 'Envoyer';
        }
    }
}

chatForm?.addEventListener('submit', sendTextMessage);

textInput?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        chatForm?.requestSubmit();
    }
});

mediaInput?.addEventListener('change', () => {
    const file = mediaInput.files?.[0];
    if (!file) return;
    if (mediaPreview) {
        mediaPreview.hidden = false;
        mediaPreview.textContent = `Sélectionné : ${file.name} (${Math.round(file.size / 1024)} Ko) — envoi…`;
    }
    sendMediaFile(file);
});


/* Suppression de messages */
async function deleteMessage(messageId, rowEl) {
    if (!messageId) return;
    if (!confirm('Supprimer ce message ?')) return;

    try {
        const formData = new FormData();
        formData.set('message_id', messageId);
        const response = await fetch('/delete_message', { method: 'POST', body: formData });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            showChatStatus(data.message || 'Suppression impossible', true);
            return;
        }
        rowEl?.remove();
        if (chatBox && !chatBox.querySelector('.message-row')) {
            const empty = document.createElement('p');
            empty.className = 'chat-empty';
            empty.textContent = 'Aucun message pour le moment.';
            chatBox.append(empty);
        }
    } catch (err) {
        showChatStatus('Erreur lors de la suppression.', true);
    }
}

document.addEventListener('click', (e) => {
    const btn = e.target.closest('.message-delete');
    if (!btn) return;
    e.preventDefault();
    const id = btn.dataset.messageId;
    const row = btn.closest('.message-row');
    deleteMessage(id, row);
});
