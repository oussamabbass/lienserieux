let mediaRecorder;
let audioChunks = [];
let isRecording = false;

const recordButton = document.getElementById('recordBtn');
const recordingStatus = document.getElementById('recordingStatus');
const recordingFeedback = document.getElementById('chatStatus');

function setRecordingStatus(isActive) {
    if (!recordButton) return;
    recordButton.setAttribute('aria-pressed', String(isActive));
    recordButton.setAttribute('aria-label', isActive ? 'Arrêter l’enregistrement vocal' : 'Démarrer un message vocal');
    recordButton.textContent = isActive ? 'Arrêter le message vocal' : 'Message vocal';
    if (recordingStatus) recordingStatus.hidden = !isActive;
}

function setRecordingFeedback(message, isError = false) {
    if (!recordingFeedback) return;
    recordingFeedback.textContent = message;
    recordingFeedback.hidden = !message;
    recordingFeedback.classList.toggle('chat-feedback--error', isError);
}

async function toggleRecording() {
    if (!recordButton) return;

    if (!isRecording) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) audioChunks.push(event.data);
            };

            mediaRecorder.onerror = () => {
                setRecordingFeedback('L’enregistrement vocal a été interrompu. Réessayez.', true);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                const formData = new FormData();
                formData.append('audio_data', audioBlob, 'message-vocal.webm');
                formData.append('receiver_id', receiverId);
                formData.append('message_type', 'audio');

                recordButton.disabled = true;
                setRecordingFeedback('Envoi du message vocal…');

                try {
                    const response = await fetch('/send_message', {
                        method: 'POST',
                        body: formData
                    });
                    if (!response.ok) throw new Error('Message vocal non envoyé');
                    window.location.reload();
                } catch (error) {
                    setRecordingFeedback('Le message vocal n’a pas été envoyé. Réessayez.', true);
                } finally {
                    stream.getTracks().forEach((track) => track.stop());
                    recordButton.disabled = false;
                }
            };

            mediaRecorder.start();
            isRecording = true;
            setRecordingFeedback('');
            setRecordingStatus(true);
        } catch (error) {
            setRecordingFeedback('Impossible d’accéder au microphone. Vérifiez les autorisations.', true);
        }
        return;
    }

    if (mediaRecorder?.state === 'recording') {
        isRecording = false;
        setRecordingStatus(false);
        mediaRecorder.stop();
    }
}

recordButton?.addEventListener('click', toggleRecording);
