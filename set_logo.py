"""
set_logo.py — Automated App Logo & Icon Installer for AgenticAim

Usage:
    python set_logo.py path/to/your_logo.png
    (Supports .png, .jpg, .jpeg, .webp)
"""

import sys
import os
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "frontend", "public")
APP_LOGO_PNG = os.path.join(PUBLIC_DIR, "app_logo.png")
APP_ICON_ICO = os.path.join(BASE_DIR, "app_icon.ico")

def set_app_logo(input_path: str):
    if not os.path.exists(input_path):
        print(f"[ERROR] File not found: {input_path}")
        return False

    os.makedirs(PUBLIC_DIR, exist_ok=True)

    print(f"[*] Processing source logo: {input_path}")
    with Image.open(input_path) as img:
        img_rgba = img.convert("RGBA")
        
        # 1. Save standard high-res PNG for React Dashboard UI and Favicon
        img_rgba.save(APP_LOGO_PNG, format="PNG")
        print(f"[+] Saved UI Dashboard Logo: {APP_LOGO_PNG}")

        # 2. Save multi-resolution Windows .ico for Desktop .exe & Taskbar
        sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
        img_rgba.save(APP_ICON_ICO, format="ICO", sizes=sizes)
        print(f"[+] Saved Desktop Windows Icon: {APP_ICON_ICO}")

    print("\n[SUCCESS] Logo installed successfully!")
    print("Next steps:")
    print(" 1. Web / Desktop UI me logo foran live dekhne ke liye browser refresh karein.")
    print(" 2. Naya .exe banane ke liye run karein: python build_desktop_exe.py")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python set_logo.py <path_to_your_image.png>")
        # If there is already an image in frontend/public/app_logo.png, generate the .ico
        if os.path.exists(APP_LOGO_PNG):
            print(f"[*] Found existing {APP_LOGO_PNG}, generating {APP_ICON_ICO}...")
            set_app_logo(APP_LOGO_PNG)
        else:
            sys.exit(1)
    else:
        set_app_logo(sys.argv[1])
