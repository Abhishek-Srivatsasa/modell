import traceback
try:
    from app.config import get_settings
    s = get_settings()
    print('Settings OK, cors:', s.cors_origins)
    from app.main import app
    print('App import OK')
except Exception as e:
    traceback.print_exc()
