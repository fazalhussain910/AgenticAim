import os
import shutil
import site

site_packages = site.getsitepackages()[1]  # or the primary one
print("Site packages:", site_packages)

internal_dir = os.path.abspath(r"dist\AgenticAim\_internal")
print("Target internal:", internal_dir)

packages_to_copy = [
    "langgraph",
    "langgraph_sdk",
    "langchain_core",
    "langchain",
    "langchain_openai",
    "langchain_community",
    "openai",
    "qdrant_client",
    "aiosqlite",
    "speech_recognition",
    "edge_tts",
    "dotenv",
    "mss",
    "cv2",
    "psutil",
    "pynput",
    "pygetwindow",
    "cpuinfo",
    "GPUtil",
]

for pkg in packages_to_copy:
    src = os.path.join(site_packages, pkg)
    dst = os.path.join(internal_dir, pkg)
    if os.path.exists(src):
        if not os.path.exists(dst):
            print(f"[*] Copying {pkg} -> {dst}...")
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        else:
            print(f"[OK] Already present: {pkg}")
    else:
        # Check if it has .py
        src_py = src + ".py"
        if os.path.exists(src_py):
            dst_py = dst + ".py"
            if not os.path.exists(dst_py):
                print(f"[*] Copying {src_py} -> {dst_py}...")
                shutil.copy2(src_py, dst_py)
            else:
                print(f"[OK] Already present: {pkg}.py")
        else:
            print(f"[?] Not found in primary site-packages: {pkg}")

print("\nDone syncing dependencies!")
