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
        ("dwExtraInfo", ctypes.c_void_p),  # ULONG_PTR: must be pointer-sized for x64
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),  # ULONG_PTR: must be pointer-sized for x64
    ]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]

    _anonymous_ = ("_input",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("_input", _INPUT),
    ]

# --- Engine Timing & Behavior Constants ---
WAIT_MODE_TIMEOUT = 120        # Max seconds for image/color/OCR wait mode
IMAGE_CACHE_MAX_SIZE = 256     # Max entries in template image cache
IMAGE_CACHE_EVICT_COUNT = 50   # Entries to remove when cache is full
SCREENSHOT_CACHE_TTL = 0.25    # Seconds to keep cached screenshot (per-instance)
EMERGENCY_CORNER_PX = 5        # Pixels from corner for emergency stop
EMERGENCY_CORNER_HOLD = 0.5    # Seconds to hold in corner to trigger stop
FOCUS_DELAY_DEFAULT = 0.05     # Default focus delay in bg_runner (seconds)
FOCUS_DELAY_STANDALONE = 0.15  # Focus delay for standalone perform_click
HUMAN_MOVE_MAX_STEPS = 80     # Max steps for human-like mouse curves
AUTO_SAVE_DEBOUNCE_MS = 1000  # Debounce interval for preset auto-save
HOTKEY_COMMIT_DELAY_MS = 800  # Delay before committing recorded hotkey

# --- Timing Delays (consolidated magic numbers) ---
BG_ACTIVATION_SETTLE = 0.03    # Delay after window activation messages
BG_HOVER_SETTLE = 0.03        # Delay for hover state before click
BG_CLICK_HOLD_MIN = 0.08      # Min hold duration for bg clicks
BG_CLICK_HOLD_MAX = 0.14      # Max hold duration for bg clicks
PRE_CLICK_SETTLE = 0.03       # Delay before foreground click
CLIPBOARD_SETTLE = 0.03       # Delay after clipboard copy
PASTE_SETTLE = 0.05           # Delay after Ctrl+V paste
TYPE_FINISH_SETTLE = 0.05     # Delay after typing finishes
HOTKEY_INTER_KEY = 0.04       # Delay between key presses in hotkey
HOTKEY_HOLD_DELAY = 0.05      # Hold time between press and release
HOTKEY_PRE_DELAY = 0.03       # Delay before hotkey sequence
