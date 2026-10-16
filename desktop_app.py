"""
desktop_app.py — Native Desktop Application Launcher for AgenticAim

Embeds the modern React Esports Dashboard into a native, high-performance
Windows desktop window (via Edge WebView2) while running the FastAPI backend
and hardware/gameplay telemetry tracker concurrently.

AMD Developer Hackathon III | AI-Powered Esports Aim Coach
"""

import os
import sys
import threading
import time
import urllib.request
import logging

# Ensure AgenticAim package directory is on path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTIC_DIR = os.path.join(BASE_DIR, "AgenticAim")
if os.path.exists(AGENTIC_DIR) and AGENTIC_DIR not in sys.path:
    sys.path.insert(0, AGENTIC_DIR)

# Force UTF-8 on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import uvicorn
import webview
from main import app

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}/"
HEALTH_URL = f"http://{SERVER_HOST}:{SERVER_PORT}/health"


def start_fastapi_server():
    """Run uvicorn server in a dedicated background daemon thread."""
    config = uvicorn.Config(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    server.run()


def wait_for_server(timeout_sec: float = 12.0) -> bool:
    """Wait until FastAPI is responsive on localhost before rendering UI."""
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def main():
    print("=" * 60)
    print("  AGENTICAIM — AI-POWERED ESPORTS AIM COACH (DESKTOP)")
    print("=" * 60)
    print("  • Starting local FastAPI + Telemetry backend daemon...")

    server_thread = threading.Thread(target=start_fastapi_server, daemon=True)
    server_thread.start()

    print("  • Initializing Windows native hardware telemetry...")
    if not wait_for_server():
        print("  [!] Error: Backend server did not respond in time.")
        sys.exit(1)

    print(f"  • Connected to local runtime: {SERVER_URL}")
    print("  • Launching native Cyberpunk Esports HUD Window...")

    # Create native Windows Edge/WebView2 desktop window
    window = webview.create_window(
        title="AgenticAim — AI Esports Aim Coach & Hardware Advisor",
        url=SERVER_URL,
        width=1380,
        height=880,
        min_size=(1024, 680),
        background_color="#0a0b10",
        text_select=False,
    )

    webview.start(debug=False)
    print("  • AgenticAim Desktop closed cleanly.")


if __name__ == "__main__":
    main()
