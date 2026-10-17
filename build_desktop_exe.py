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
        "--hidden-import=aiosqlite",
        "--hidden-import=sqlite3",
        "--hidden-import=speech_recognition",
        "--hidden-import=edge_tts",
        "--hidden-import=openai",
        "--hidden-import=httpx",
        "--hidden-import=dotenv",
        "--hidden-import=pygetwindow",
        "--hidden-import=cpuinfo",
        "--hidden-import=GPUtil",
        "--hidden-import=numpy",
        "--hidden-import=psutil",
        "--hidden-import=pynput",
        "--hidden-import=mss",
        "--hidden-import=cv2",
        "--hidden-import=qdrant_client",
        "--hidden-import=langgraph",
        "--hidden-import=langchain_core",
        "--hidden-import=langchain_openai",
        "--hidden-import=ormsgpack",
        "--noconfirm",
        "desktop_app.py",
    ]

    icon_path = os.path.join(BASE_DIR, "app_icon.ico")
    if os.path.exists(icon_path):
        print(f"[*] Found custom app icon: {icon_path}")
        pyinstaller_args.insert(5, f"--icon={icon_path}")

    print("[*] Running PyInstaller command:")
    print("    " + " ".join(pyinstaller_args[:5]) + " ...")
    subprocess.run(pyinstaller_args, cwd=BASE_DIR, check=True)

    dist_app_dir = os.path.join(BASE_DIR, "dist", "AgenticAim")
    zip_dest = os.path.join(BASE_DIR, "AgenticAim_v1.0_Windows.zip")

    print("[*] Packaging clean standalone ZIP (preserving base_library.zip)...")
    import zipfile
    temp_zip = zip_dest + ".tmp"
    if os.path.exists(temp_zip):
        os.remove(temp_zip)

    file_count = 0
    with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, dirs, files in os.walk(dist_app_dir):
            for f in files:
                full_path = os.path.join(root, f)
                arcname = os.path.relpath(full_path, dist_app_dir)
                z.write(full_path, arcname)
                file_count += 1

    if os.path.exists(zip_dest):
        os.remove(zip_dest)
    os.rename(temp_zip, zip_dest)

    print("\n" + "=" * 65)
    print("  [SUCCESS] Executable built & packaged successfully!")
    print(f"  App Folder: {dist_app_dir}")
    print(f"  Release Zip: {zip_dest} ({file_count} files, {os.path.getsize(zip_dest) / (1024*1024):.1f} MB)")
    print("=" * 65)


if __name__ == "__main__":
    main()
