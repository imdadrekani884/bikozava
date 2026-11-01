"""
Bikozava — Local & Production Server Runner (`run.py`)
Works natively on Windows, macOS, and Linux.

Usage on Windows (PowerShell or CMD):
    python run.py

If `waitress` is installed (default on Windows via `requirements.txt`), `run.py`
automatically serves the application using the production-ready multi-threaded
Waitress WSGI server unless `FLASK_DEBUG=1` is set.
"""

import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("FLASK_DEBUG", "0") in ("1", "true", "True")

    print("=" * 72)
    print(f" * Bikozava Wedding Platform running on http://localhost:{port}")
    print(f" * Demo Invitation (Badini):  http://localhost:{port}/ismail_shrin")
    print(f" * Demo Invitation (Arabic):  http://localhost:{port}/ismail_shrin?lang=ar")
    print(f" * Demo Invitation (English): http://localhost:{port}/ismail_shrin?lang=en")
    print(f" * Admin Studio Login:        http://localhost:{port}/admin/login")
    print("=" * 72)

    if not debug:
        try:
            from waitress import serve  # type: ignore
            print(" * Serving with Waitress production WSGI server (Windows/Cross-Platform)")
            serve(app, host=host, port=port, threads=6)
        except ImportError:
            app.run(host=host, port=port, debug=debug)
    else:
        app.run(host=host, port=port, debug=debug)
