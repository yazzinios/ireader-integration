"""
install.py – One-click dependency installer for the Arcade Kiosk.
Run this once before using run.bat.
"""
import subprocess, sys

packages = ["customtkinter", "pyserial", "pygame", "pillow", "opencv-python", "pynput"]

print("=== Arcade Kiosk – Dependency Installer ===")
for pkg in packages:
    print(f"  Installing {pkg}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])

print("\n✅  All dependencies installed!")
print("   You can now run the kiosk using: run.bat")
input("\nPress Enter to exit...")
