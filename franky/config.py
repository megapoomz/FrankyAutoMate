"""
Configuration and constants for Franky AutoMate
"""
import customtkinter as ctk
import pyautogui
import logging
import os

# --- Appearance ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# --- PyAutoGUI Settings ---
pyautogui.FAILSAFE = True

# --- App Info ---
APP_NAME = "Franky AutoMate"
APP_VERSION = "1.6.0"
APP_TITLE = f"{APP_NAME} - โปรแกรมช่วยทำงานอัตโนมัติ"
APP_SUBTITLE = f"ระบบจัดการคำสั่งอัตโนมัติระดับมืออาชีพ [v{APP_VERSION} Premium]"

# --- File Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRESETS_FILE = os.path.join(BASE_DIR, "..", "presets.json")
LOG_FILE = os.path.join(BASE_DIR, "..", "automate.log")

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- UI Colors ---
COLORS = {
    "primary": "#3498db",
    "secondary": "#2980b9",
    "success": "#27ae60",
    "danger": "#e74c3c",
    "warning": "#f1c40f",
    "info": "#17a2b8",
    "dark": "#1e1e1e",
    "darker": "#1a1a1a",
    "light_gray": "#7f8c8d",
    "border": "#333333",
}

# --- Stealth Fake App Names ---
FAKE_APP_NAMES = [
    "Microsoft Excel",
    "Notepad",
    "Calculator",
    "Windows Settings",
    "File Explorer",
    "Chrome",
    "Edge",
    "System32"
]
