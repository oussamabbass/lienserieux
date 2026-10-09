import os
import sqlite3
from flask import redirect, url_for, session, render_template
from werkzeug.security import generate_password_hash
from authlib.integrations.flask_client import OAuth


def init_google(app, get_db_connection, get_user_settings):
    oauth = OAuth(app)
    google = oauth.register(
        name='google',
        client_id=os.environ.get('GOOGLE_CLIENT_ID', ''),
        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET', ''),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )
    google_enabled = bool(os.environ.get('GOOGLE_CLIENT_ID') and os.environ.get('GOOGLE_CLIENT_SECRET'))

    @app.route('/login/google')
    def login_google():
        if not google_enabled:
            return render_template('login.html', mode='login', error='Connexion Google non configurée sur ce serveur.', username='')
        redirect_uri = url_for('login_google_callback', _external=True)
        return google.authorize_redirect(redirect_uri)

    @app.route('/login/google/callback')
    def login_google_callback():
        if not google_enabled:
            return redirect(url_for('login'))
        try:
            token = google.authorize_access_token()
            userinfo = token.get('userinfo')
            if not userinfo:
                userinfo = google.parse_id_token(token)
        except Exception:
            return render_template('login.html', mode='login', error='Connexion Google échouée. Réessaie.', username='')

        google_id = str(userinfo.get('sub') or '')
        email = (userinfo.get('email') or '').strip().lower()
        name = (userinfo.get('name') or (email.split('@')[0] if email else 'user')).strip()[:50]
        picture = userinfo.get('picture') or ''

        if not google_id or not email:
            return render_template('login.html', mode='login', error='Google n’a pas fourni assez d’informations.', username='')

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE google_id = ? OR email = ?', (google_id, email)).fetchone()

        if user is None:
            base_username = ''.join(c for c in name.lower().replace(' ', '_') if c.isalnum() or c == '_')[:30] or 'user'
            username = base_username
            n = 0
            while conn.execute('SELECT 1 FROM users WHERE username = ?', (username,)).fetchone():
                n += 1
                username = f'{base_username}{n}'
            random_pw = generate_password_hash(os.urandom(16).hex())
            try:
                conn.execute(
                    'INSERT INTO users (username, email, password_hash, google_id, avatar_url, bio) VALUES (?, ?, ?, ?, ?, ?)',
                    (username, email, random_pw, google_id, picture or 'default_avatar.png', '')
                )
                conn.commit()
                user = conn.execute('SELECT * FROM users WHERE google_id = ?', (google_id,)).fetchone()
            except sqlite3.IntegrityError:
                conn.close()
                return render_template('login.html', mode='login', error='Impossible de créer le compte Google.', username='')
        else:
            if not user['google_id']:
                conn.execute('UPDATE users SET google_id = ? WHERE id = ?', (google_id, user['id']))
                conn.commit()
                user = conn.execute('SELECT * FROM users WHERE id = ?', (user['id'],)).fetchone()

        settings = get_user_settings(conn, user['id'])
        conn.commit()
        conn.close()
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['theme'] = settings['theme'] if settings else 'ivoire-rose'
        return redirect(url_for('index'))

    return google_enabled
