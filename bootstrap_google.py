"""Entrypoint Render: active Google login si les clés sont configurées."""
from app import app, get_db_connection, get_user_settings

try:
    from google_auth import init_google
    GOOGLE_ENABLED = init_google(app, get_db_connection, get_user_settings)
except Exception:
    GOOGLE_ENABLED = False


@app.context_processor
def inject_globals():
    return {'google_enabled': GOOGLE_ENABLED}
