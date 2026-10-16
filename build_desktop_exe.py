"""
build_desktop_exe.py — PyInstaller Build Script for AgenticAim Desktop Application

Builds a standalone Windows executable with native WebView2 integration,
FastAPI backend, hardware telemetry, and compiled React frontend.

Usage:
    python build_desktop_exe.py
"""

import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    print("=" * 65)
    print("       BUILDING AGENTICAIM WINDOWS STANDALONE EXECUTABLE        ")
    print("=" * 65)

    dist_dir = os.path.join(BASE_DIR, "frontend", "dist")
    if not os.path.exists(dist_dir) or not os.listdir(dist_dir):
        print("[*] Rebuilding fresh React production bundle in frontend/...")
        subprocess.run(["npm", "run", "build"], cwd=os.path.join(BASE_DIR, "frontend"), check=True, shell=True)

    agentic_dir = os.path.join(BASE_DIR, "AgenticAim")
    frontend_dist = os.path.join(BASE_DIR, "frontend", "dist")

    pyinstaller_args = [
        "pyinstaller",
        "--name=AgenticAim",
        "--onedir",
        "--windowed",
        f"--add-data={agentic_dir};AgenticAim",
        f"--add-data={frontend_dist};frontend/dist",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.lifespans",
        "--hidden-import=uvicorn.lifespans.on",
        "--hidden-import=webview",
        "--hidden-import=webview.platforms.winforms",
        "--hidden-import=webview.platforms.edgechromium",
        "--hidden-import=clr",
        "--hidden-import=pythonnet",
        "--hidden-import=psutil",
        "--hidden-import=pynput",
        "--hidden-import=mss",
        "--hidden-import=cv2",
        "--hidden-import=qdrant_client",
        "--hidden-import=langgraph",
        "--hidden-import=langchain_core",
        "--hidden-import=langchain_openai",
        "--noconfirm",
        "desktop_app.py",
    ]

    print("[*] Running PyInstaller command:")
    print("    " + " ".join(pyinstaller_args[:5]) + " ...")
    subprocess.run(pyinstaller_args, cwd=BASE_DIR, check=True)

    print("\n" + "=" * 65)
    print("  [SUCCESS] Executable built successfully!")
    print(f"  Path: {os.path.join(BASE_DIR, 'dist', 'AgenticAim', 'AgenticAim.exe')}")
    print("=" * 65)


if __name__ == "__main__":
    main()
