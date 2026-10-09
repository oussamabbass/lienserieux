import os
import re
import json
import sqlite3
from flask import Flask, Response, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cle_secrete_celibataire_app')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['STATIC_ASSET_VERSION'] = '20261008-darkshare'
app.config['STATIC_IMMUTABLE_MAX_AGE'] = 31536000
app.config['STATIC_REVALIDATE_MAX_AGE'] = 300

_VERSIONED_STATIC_ASSET = re.compile(r'\.[a-f0-9]{12,64}\.')

@app.after_request
def set_static_cache_headers(response):
    if request.endpoint != 'static' or response.status_code != 200:
        return response
    filename = request.view_args.get('filename', '') if request.view_args else ''
    if _VERSIONED_STATIC_ASSET.search(filename):
        max_age = app.config['STATIC_IMMUTABLE_MAX_AGE']
        response.headers['Cache-Control'] = f'public, max-age={max_age}, immutable'
    else:
        max_age = app.config['STATIC_REVALIDATE_MAX_AGE']
        response.headers['Cache-Control'] = f'public, max-age={max_age}, must-revalidate'
    return response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'app.db')
UPLOAD_AUDIO = os.path.join(BASE_DIR, 'static', 'uploads', 'audio')
UPLOAD_AVATAR = os.path.join(BASE_DIR, 'static', 'uploads', 'avatars')
UPLOAD_MEDIA = os.path.join(BASE_DIR, 'static', 'uploads', 'media')
app.config['UPLOAD_AUDIO'] = UPLOAD_AUDIO
app.config['UPLOAD_AVATAR'] = UPLOAD_AVATAR
app.config['UPLOAD_MEDIA'] = UPLOAD_MEDIA

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = get_db_connection()
    try:
        schema_path = os.path.join(BASE_DIR, 'database', 'schema.sql')
        if os.path.isfile(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                conn.executescript(f.read())
        settings_columns = {row['name'] for row in conn.execute('PRAGMA table_info(user_settings)')}
        if settings_columns and 'allow_audio' not in settings_columns:
            conn.execute('ALTER TABLE user_settings ADD COLUMN allow_audio INTEGER NOT NULL DEFAULT 1')
        conn.commit()
    finally:
        conn.close()

init_db()

def require_login():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return None

def get_user_settings(conn, user_id):
    conn.execute('INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)', (user_id,))
    return conn.execute('SELECT * FROM user_settings WHERE user_id = ?', (user_id,)).fetchone()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    users = conn.execute('''
        SELECT id, username, bio, avatar_url FROM users
        WHERE id != ? AND COALESCE(
            (SELECT profile_visible FROM user_settings WHERE user_id = users.id), 1
        ) = 1
    ''', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('index.html', users=users)

@app.route('/status')
def status():
    return redirect(url_for('index'))

@app.route('/calls')
def calls():
    return redirect(url_for('conversations'))

@app.route('/communities')
def communities():
    return redirect(url_for('index'))

@app.route('/premium')
def premium():
    r = require_login()
    if r: return r
    conn = get_db_connection()
    user = conn.execute('SELECT id, username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    is_premium = session.get('is_premium', False)
    conn.close()
    return render_template('premium.html', user=user, is_premium=is_premium)

@app.route('/conversations')
def conversations():
    r = require_login()
    if r: return r
    user_id = session['user_id']
    conn = get_db_connection()
    chats = conn.execute('''
        SELECT u.id, u.username, u.avatar_url,
            (SELECT content FROM messages
             WHERE (sender_id = ? AND receiver_id = u.id) OR (sender_id = u.id AND receiver_id = ?)
             ORDER BY id DESC LIMIT 1) AS last_message,
            (SELECT message_type FROM messages
             WHERE (sender_id = ? AND receiver_id = u.id) OR (sender_id = u.id AND receiver_id = ?)
             ORDER BY id DESC LIMIT 1) AS last_message_type,
            MAX(m.created_at) AS last_message_at
        FROM messages AS m
        JOIN users AS u ON u.id = CASE WHEN m.sender_id = ? THEN m.receiver_id ELSE m.sender_id END
        WHERE m.sender_id = ? OR m.receiver_id = ?
        GROUP BY u.id
        ORDER BY last_message_at DESC
    ''', (user_id, user_id, user_id, user_id, user_id, user_id, user_id)).fetchall()
    conn.close()
    return render_template('conversations.html', conversations=chats)

@app.route('/profile', methods=['GET', 'POST'])
@app.route('/settings', methods=['GET', 'POST'])
def profile():
    r = require_login()
    if r: return r
    conn = get_db_connection()
    user_id = session['user_id']
    user = conn.execute('SELECT id, username, email, bio, avatar_url, password_hash FROM users WHERE id = ?', (user_id,)).fetchone()
    if user is None:
        conn.close()
        session.clear()
        return redirect(url_for('login'))
    settings = get_user_settings(conn, user_id)
    if request.method == 'POST':
        section = request.form.get('section')
        error = None
        updated_username = None
        if section == 'profile':
            bio = request.form.get('bio', '').strip()[:500]
            avatar = request.files.get('avatar')
            avatar_url = user['avatar_url']
            if avatar and avatar.filename:
                extension = os.path.splitext(avatar.filename)[1].lower()
                signature = avatar.stream.read(12)
                avatar.stream.seek(0)
                is_valid_image = (
                    (extension == '.png' and signature.startswith(b'\x89PNG\r\n\x1a\n'))
                    or (extension in {'.jpg', '.jpeg'} and signature.startswith(b'\xff\xd8\xff'))
                    or (extension == '.webp' and signature.startswith(b'RIFF') and signature[8:12] == b'WEBP')
                )
                if not is_valid_image:
                    error = 'avatar_type'
                else:
                    os.makedirs(app.config['UPLOAD_AVATAR'], exist_ok=True)
                    filename = f"avatar_{user_id}_{os.urandom(8).hex()}{extension}"
                    avatar.save(os.path.join(app.config['UPLOAD_AVATAR'], filename))
                    avatar_url = f'uploads/avatars/{filename}'
            if not error:
                conn.execute('UPDATE users SET bio = ?, avatar_url = ? WHERE id = ?', (bio, avatar_url, user_id))
        elif section == 'account':
            username = request.form.get('username', '').strip()[:50]
            email = request.form.get('email', '').strip()[:100]
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            if not username or '@' not in email:
                error = 'account_invalid'
            elif not check_password_hash(user['password_hash'], current_password):
                error = 'password_invalid'
            elif new_password and len(new_password) < 8:
                error = 'password_short'
            else:
                try:
                    if new_password:
                        conn.execute('UPDATE users SET username = ?, email = ?, password_hash = ? WHERE id = ?',
                                     (username, email, generate_password_hash(new_password), user_id))
                    else:
                        conn.execute('UPDATE users SET username = ?, email = ? WHERE id = ?', (username, email, user_id))
                    updated_username = username
                except sqlite3.IntegrityError:
                    error = 'account_exists'
        elif section == 'privacy':
            conn.execute('''UPDATE user_settings SET profile_visible = ?, allow_messages = ?
                WHERE user_id = ?''', (
                int(request.form.get('profile_visible') == 'on'),
                int(request.form.get('allow_messages') == 'on'), user_id))
        elif section == 'discussions':
            conn.execute('UPDATE user_settings SET read_receipts = ?, allow_audio = ? WHERE user_id = ?', (
                int(request.form.get('read_receipts') == 'on'),
                int(request.form.get('allow_audio') == 'on'), user_id))
        elif section == 'appearance':
            theme = request.form.get('theme', 'ivoire-rose')
            if theme not in {'ivoire-rose', 'porcelaine-bleue', 'soiree-feutree', 'mode-sombre'}:
                theme = 'ivoire-rose'
            conn.execute('UPDATE user_settings SET theme = ? WHERE user_id = ?', (theme, user_id))
            session['theme'] = theme
        elif section == 'notifications':
            enabled = int(request.form.get('notifications_enabled') == 'on')
            conn.execute('UPDATE user_settings SET notifications_enabled = ? WHERE user_id = ?', (enabled, user_id))
        else:
            error = 'section_invalid'
        if not error:
            conn.commit()
            if updated_username:
                session['username'] = updated_username
        user = conn.execute('SELECT id, username, email, bio, avatar_url, password_hash FROM users WHERE id = ?', (user_id,)).fetchone()
        settings = get_user_settings(conn, user_id)
        conn.close()
        if error:
            return redirect(url_for('profile', error=error, section=section or 'profile'))
        return redirect(url_for('profile', saved=section, _anchor=section))
    audio_rows = conn.execute("SELECT content FROM messages WHERE sender_id = ? AND message_type = 'audio'", (user_id,)).fetchall()
    audio_count = len(audio_rows)
    audio_bytes = 0
    avatar_bytes = 0
    conn.commit()
    conn.close()
    session['theme'] = settings['theme']
    return render_template('profile.html', user=user, settings=settings, audio_count=audio_count,
                           audio_bytes=audio_bytes, avatar_bytes=avatar_bytes, saved=request.args.get('saved'),
                           error=request.args.get('error'), active_section=request.args.get('section', 'profile'))

@app.route('/settings/export')
def export_data():
    r = require_login()
    if r: return r
    user_id = session['user_id']
    conn = get_db_connection()
    user = conn.execute('SELECT username, email, bio, avatar_url, created_at FROM users WHERE id = ?', (user_id,)).fetchone()
    settings = conn.execute('SELECT profile_visible, show_online, allow_messages, read_receipts, allow_audio, theme, notifications_enabled FROM user_settings WHERE user_id = ?', (user_id,)).fetchone()
    messages = conn.execute('''SELECT sender_id, receiver_id, message_type, content, created_at
        FROM messages WHERE sender_id = ? OR receiver_id = ? ORDER BY created_at''', (user_id, user_id)).fetchall()
    conn.close()
    payload = {'account': dict(user) if user else {}, 'settings': dict(settings) if settings else {},
               'messages': [dict(message) for message in messages]}
    return Response(json.dumps(payload, ensure_ascii=False, default=str), mimetype='application/json',
                    headers={'Content-Disposition': 'attachment; filename="mes-donnees.json"'})

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_pw = generate_password_hash(password)
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                         (username, email, hashed_pw))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('login.html', mode='register',
                error="Ce nom d'utilisateur ou cette adresse e-mail existe d\u00e9j\u00e0.",
                username=username, email=email)
    return render_template('login.html', mode='register', error=None, username='', email='')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            settings = get_user_settings(conn, user['id'])
            conn.commit()
            conn.close()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['theme'] = settings['theme']
            return redirect(url_for('index'))
        else:
            conn.close()
            return render_template('login.html', mode='login',
                error="Nom d'utilisateur ou mot de passe incorrect.", username=username)
    return render_template('login.html', mode='login', error=None, username='')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/chat/<int:receiver_id>')
def chat(receiver_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    sender_id = session['user_id']
    conn = get_db_connection()
    receiver = conn.execute('SELECT id, username, avatar_url FROM users WHERE id = ?', (receiver_id,)).fetchone()
    if receiver is None or receiver_id == sender_id:
        conn.close()
        return redirect(url_for('index'))
    receiver_settings = conn.execute('''
        SELECT COALESCE(allow_messages, 1) AS allow_messages, COALESCE(allow_audio, 1) AS allow_audio
        FROM user_settings WHERE user_id = ?
    ''', (receiver_id,)).fetchone()
    sender_settings = get_user_settings(conn, sender_id)
    can_message = receiver_settings is None or bool(receiver_settings['allow_messages'])
    can_send_audio = receiver_settings is None or bool(receiver_settings['allow_audio'])
    if sender_settings['read_receipts']:
        conn.execute('UPDATE messages SET is_read = 1 WHERE sender_id = ? AND receiver_id = ?', (receiver_id, sender_id))
        conn.commit()
    messages = conn.execute('''
        SELECT * FROM messages
        WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
        ORDER BY created_at ASC
    ''', (sender_id, receiver_id, receiver_id, sender_id)).fetchall()
    conn.close()
    return render_template('chat.html', receiver=receiver, messages=messages,
                           can_message=can_message, can_send_audio=can_send_audio)

@app.route('/chat/<int:receiver_id>/updates')
def chat_updates(receiver_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Non autoris\u00e9'}), 401
    try:
        after_id = max(0, int(request.args.get('after', '0')))
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'Curseur invalide'}), 400
    user_id = session['user_id']
    conn = get_db_connection()
    recipient = conn.execute('SELECT 1 FROM users WHERE id = ?', (receiver_id,)).fetchone()
    if recipient is None or receiver_id == user_id:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Discussion introuvable'}), 404
    settings = get_user_settings(conn, user_id)
    if settings['read_receipts']:
        conn.execute('UPDATE messages SET is_read = 1 WHERE sender_id = ? AND receiver_id = ?', (receiver_id, user_id))
        conn.commit()
    messages = conn.execute('''
        SELECT id, sender_id, receiver_id, message_type, content, is_read, created_at
        FROM messages
        WHERE id > ? AND ((sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?))
        ORDER BY id ASC
    ''', (after_id, user_id, receiver_id, receiver_id, user_id)).fetchall()
    read_ids = [row['id'] for row in conn.execute('''
        SELECT id FROM messages WHERE sender_id = ? AND receiver_id = ? AND is_read = 1
    ''', (user_id, receiver_id)).fetchall()]
    conn.close()
    return jsonify({'messages': [dict(message) for message in messages], 'read_ids': read_ids})

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Non autoris\u00e9'}), 401
    sender_id = session['user_id']
    try:
        receiver_id = int(request.form.get('receiver_id', ''))
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'Destinataire invalide'}), 400
    if receiver_id == sender_id:
        return jsonify({'status': 'error', 'message': 'Destinataire invalide'}), 400
    message_type = request.form.get('message_type', 'text')
    conn = get_db_connection()
    recipient = conn.execute('''
        SELECT COALESCE((SELECT allow_messages FROM user_settings WHERE user_id = users.id), 1) AS allow_messages,
               COALESCE((SELECT allow_audio FROM user_settings WHERE user_id = users.id), 1) AS allow_audio
        FROM users WHERE id = ?
    ''', (receiver_id,)).fetchone()
    if recipient is None:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Destinataire introuvable'}), 404
    if not recipient['allow_messages']:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Cette personne n\u2019accepte pas les messages'}), 403
    if message_type == 'text':
        content = (request.form.get('content') or '').strip()
        if content:
            conn.execute('INSERT INTO messages (sender_id, receiver_id, message_type, content) VALUES (?, ?, ?, ?)',
                         (sender_id, receiver_id, 'text', content))
            conn.commit()
        else:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Le message est vide'}), 400
    elif message_type == 'audio':
        if not recipient['allow_audio']:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Cette personne n\u2019accepte pas les messages vocaux'}), 403
        if 'audio_data' in request.files and request.files['audio_data'].filename:
            file = request.files['audio_data']
            os.makedirs(app.config['UPLOAD_AUDIO'], exist_ok=True)
            filename = f"vocal_{sender_id}_{receiver_id}_{os.urandom(4).hex()}.webm"
            file_path = os.path.join(app.config['UPLOAD_AUDIO'], filename)
            file.save(file_path)
            db_audio_path = f"uploads/audio/{filename}"
            conn.execute('INSERT INTO messages (sender_id, receiver_id, message_type, content) VALUES (?, ?, ?, ?)',
                         (sender_id, receiver_id, 'audio', db_audio_path))
            conn.commit()
        else:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Fichier audio manquant'}), 400
    elif message_type in ('image', 'video'):
        media_file = request.files.get('media_file')
        if not media_file or not media_file.filename:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Fichier manquant'}), 400
        original = media_file.filename.lower()
        ext = os.path.splitext(original)[1]
        allowed_images = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
        allowed_videos = {'.mp4', '.webm', '.mov'}
        if message_type == 'image' and ext not in allowed_images:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Format image non support\u00e9'}), 400
        if message_type == 'video' and ext not in allowed_videos:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Format vid\u00e9o non support\u00e9'}), 400
        media_file.seek(0, os.SEEK_END)
        size = media_file.tell()
        media_file.seek(0)
        max_size = 12 * 1024 * 1024 if message_type == 'image' else 40 * 1024 * 1024
        if size > max_size:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Fichier trop volumineux'}), 400
        os.makedirs(app.config['UPLOAD_MEDIA'], exist_ok=True)
        filename = f"{message_type}_{sender_id}_{receiver_id}_{os.urandom(6).hex()}{ext}"
        file_path = os.path.join(app.config['UPLOAD_MEDIA'], filename)
        media_file.save(file_path)
        db_path = f"uploads/media/{filename}"
        conn.execute('INSERT INTO messages (sender_id, receiver_id, message_type, content) VALUES (?, ?, ?, ?)',
                     (sender_id, receiver_id, message_type, db_path))
        conn.commit()
    else:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Type de message invalide'}), 400
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/delete_message', methods=['POST'])
def delete_message():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Non autoris\u00e9'}), 401
    user_id = session['user_id']
    try:
        message_id = int(request.form.get('message_id') or 0)
    except (TypeError, ValueError):
        data = request.get_json(silent=True) or {}
        try:
            message_id = int(data.get('message_id', 0))
        except (TypeError, ValueError):
            return jsonify({'status': 'error', 'message': 'ID invalide'}), 400
    if not message_id:
        return jsonify({'status': 'error', 'message': 'ID manquant'}), 400
    conn = get_db_connection()
    msg = conn.execute('SELECT id, sender_id, message_type, content FROM messages WHERE id = ?', (message_id,)).fetchone()
    if msg is None:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Message introuvable'}), 404
    if msg['sender_id'] != user_id:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Tu ne peux supprimer que tes propres messages'}), 403
    if msg['message_type'] in ('audio', 'image', 'video') and msg['content']:
        file_path = os.path.join(BASE_DIR, 'static', msg['content'])
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
    conn.execute('DELETE FROM messages WHERE id = ?', (message_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG') == '1')
