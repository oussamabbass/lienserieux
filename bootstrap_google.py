"""Entrypoint Render: active Google login si les clés sont configurées."""
from app import app, get_db_connection, get_user_settings

# Colonne google_id si absente
try:
    conn = get_db_connection()
    cols = {row['name'] for row in conn.execute('PRAGMA table_info(users)')}
    if 'google_id' not in cols:
        conn.execute('ALTER TABLE users ADD COLUMN google_id VARCHAR(255) UNIQUE')
        conn.commit()
    conn.close()
except Exception:
    pass

try:
    from google_auth import init_google
    GOOGLE_ENABLED = init_google(app, get_db_connection, get_user_settings)
except Exception:
    GOOGLE_ENABLED = False


@app.context_processor
def inject_globals():
    return {'google_enabled': GOOGLE_ENABLED}
