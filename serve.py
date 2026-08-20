"""Production entry point for Windows.

Runs the Flask app with Waitress (a pure-Python WSGI server that works
natively on Windows, unlike Gunicorn). Bind to 0.0.0.0 so other devices
on the local network can reach the app via this machine's IP address.

Usage:
    python serve.py

Environment variables (optional):
    ECG_HOST  - interface to bind to (default: 0.0.0.0, i.e. all interfaces)
    ECG_PORT  - port to listen on (default: 8000)
"""

import os

from waitress import serve

from app import app

if __name__ == "__main__":
    host = os.environ.get("ECG_HOST", "0.0.0.0")
    port = int(os.environ.get("ECG_PORT", "8000"))
    print(f"Serwer EKG nasłuchuje na http://{host}:{port} (Ctrl+C aby zatrzymać)")
    serve(app, host=host, port=port, threads=4)
