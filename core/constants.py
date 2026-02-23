import ctypes
from ctypes import wintypes

# --- App Info ---
APP_VERSION = "1.6.0"
GITHUB_REPO = "megapoomz/FrankyAutoMate"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# --- Premium UI Constants (Theme-aware) ---
COLOR_BG = ("#f8fafc", "#020408")  # Slate 50 / Deep Void
COLOR_CARD = ("#ffffff", "#0f172a")  # White / Slate 900
COLOR_INNER = ("#f1f5f9", "#1e293b")  # Slate 100 / Slate 800
COLOR_ACCENT = ("#0891b2", "#06b6d4")  # Cyan 600 / Cyan 500
COLOR_SUCCESS = ("#059669", "#10b981")  # Emerald 600 / Emerald 500
COLOR_DANGER = ("#e11d48", "#f43f5e")  # Rose 600 / Rose 500
COLOR_WARNING = ("#d97706", "#f59e0b")  # Amber 600 / Amber 500
COLOR_MUTED = ("#64748b", "#94a3b8")  # Slate 500 / Slate 400
GRADIENT_START = ("#2563eb", "#3b82f6")  # Blue 600 / Blue 500
GRADIENT_END = ("#7c3aed", "#8b5cf6")  # Violet 600 / Violet 500
BORDER_COLOR = ("#e2e8f0", "#334155")  # Slate 200 / Slate 700

# --- Win32 Input Constants ---
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_ABSOLUTE = 0x8000
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004


# --- Win32 Structures ---
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]

    _anonymous_ = ("_input",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("_input", _INPUT),
    ]
