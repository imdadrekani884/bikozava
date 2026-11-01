"""
Bikozava — Production WSGI Entrypoint (`wsgi.py`)
Run with Gunicorn:
    gunicorn -c gunicorn.conf.py wsgi:app
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
