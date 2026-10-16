"""
desktop_app.py — Native Desktop Application Launcher for AgenticAim

Embeds the modern React Esports Dashboard into a native, high-performance
Windows desktop window (via Edge WebView2) while running the FastAPI backend
and hardware/gameplay telemetry tracker concurrently.

Resilient Design:
  1. Auto-detects if AgenticAim backend is already running on port 8000 to prevent [Errno 10048] port collision.
  2. Dynamically finds an open port (8000, 8001, 8002...) if 8000 is occupied by another application.
  3. Gracefully falls back to the system default browser if native WebView2 runtime encounters any display issue.

AMD Developer Hackathon III | AI-Powered Esports Aim Coach
"""

import os
import sys
import socket
import threading
import time
import urllib.request
import webbrowser
import logging

# Ensure AgenticAim package directory is on path (handles both dev and PyInstaller frozen modes)
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    BASE_DIR = getattr(sys, "_MEIPASS")
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

AGENTIC_DIR = os.path.join(BASE_DIR, "AgenticAim")
if os.path.exists(AGENTIC_DIR) and AGENTIC_DIR not in sys.path:
    sys.path.insert(0, AGENTIC_DIR)

# Force UTF-8 on Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import uvicorn
import webview
from main import app

SERVER_HOST = "127.0.0.1"


def is_port_in_use(port: int) -> bool:
    """Check if a local TCP port is already open/listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((SERVER_HOST, port)) == 0


def is_server_healthy(port: int) -> bool:
    """Verify if the running service on port is indeed AgenticAim API."""
    url = f"http://{SERVER_HOST}:{port}/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AgenticAimDesktop/1.0"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False


def find_available_port(start_port: int = 8000) -> int:
    """Find the first free TCP port starting from start_port."""
    for p in range(start_port, start_port + 25):
        if not is_port_in_use(p):
            return p
    return start_port


def start_fastapi_server(port: int):
    """Run uvicorn server in a dedicated background daemon thread."""
    config = uvicorn.Config(
        app,
        host=SERVER_HOST,
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    server.run()


def wait_for_server(port: int, timeout_sec: float = 12.0) -> bool:
    """Poll health check until backend responds."""
    start = time.time()
    while time.time() - start < timeout_sec:
        if is_server_healthy(port):
            return True
        time.sleep(0.3)
    return False


def main():
    print("=" * 65)
    print("  AGENTICAIM — AI-POWERED ESPORTS AIM COACH (DESKTOP)")
    print("=" * 65)

    target_port = 8000
    need_spawn_server = True

    # 1. Check if AgenticAim is already running on port 8000
    if is_server_healthy(target_port):
        print(f"  [✓] Existing AgenticAim backend detected on port {target_port} — attaching GUI.")
        need_spawn_server = False
    elif is_port_in_use(target_port):
        # Port 8000 occupied by foreign process — find next free port
        target_port = find_available_port(8001)
        print(f"  [i] Port 8000 occupied. Automatically assigned open port {target_port}.")

    if need_spawn_server:
        print(f"  • Starting local FastAPI + Telemetry backend daemon on port {target_port}...")
        server_thread = threading.Thread(
            target=start_fastapi_server,
            args=(target_port,),
            daemon=True,
        )
        server_thread.start()

        print("  • Initializing Windows native hardware telemetry...")
        if not wait_for_server(target_port):
            print("  [!] Error: Backend server did not respond in time.")
            sys.exit(1)

    app_url = f"http://{SERVER_HOST}:{target_port}/"
    print(f"  [✓] Connected to local runtime: {app_url}")
    print("  • Launching native Cyberpunk Esports HUD Window...")

    # 2. Launch native Windows Edge WebView2 window with automatic fallback
    try:
        window = webview.create_window(
            title="AgenticAim — AI Esports Aim Coach & Hardware Advisor",
            url=app_url,
            width=1380,
            height=880,
            min_size=(1024, 680),
            background_color="#0a0b10",
            text_select=False,
        )
        webview.start(debug=False)
    except Exception as e:
        print(f"  [!] Native WebView2 window could not initialize ({e}).")
        print(f"  [✓] Opening AgenticAim Dashboard in default web browser: {app_url}")
        webbrowser.open(app_url)
        print("  • Press Ctrl+C in this terminal when you want to exit AgenticAim.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    print("  • AgenticAim Desktop closed cleanly.")


if __name__ == "__main__":
    main()
