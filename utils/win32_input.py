import ctypes
import time
import random
from core.constants import (
    INPUT_MOUSE,
    INPUT_KEYBOARD,
    MOUSEEVENTF_MOVE,
    MOUSEEVENTF_ABSOLUTE,
    MOUSEEVENTF_LEFTDOWN,
    MOUSEEVENTF_LEFTUP,
    MOUSEEVENTF_RIGHTDOWN,
    MOUSEEVENTF_RIGHTUP,
    MOUSEEVENTF_MIDDLEDOWN,
    MOUSEEVENTF_MIDDLEUP,
    KEYEVENTF_UNICODE,
    KEYEVENTF_KEYUP,
    INPUT,
)

# Cached virtual screen dimensions
_screen_x = ctypes.windll.user32.GetSystemMetrics(76)
_screen_y = ctypes.windll.user32.GetSystemMetrics(77)
_screen_w = ctypes.windll.user32.GetSystemMetrics(78)
_screen_h = ctypes.windll.user32.GetSystemMetrics(79)

if _screen_w == 0:
    _screen_w = ctypes.windll.user32.GetSystemMetrics(0)
    _screen_h = ctypes.windll.user32.GetSystemMetrics(1)
    _screen_x = 0
    _screen_y = 0

# COMPAT-04: Validate INPUT struct size at module load
# Expected: 28 bytes (x86) or 40 bytes (x64)
_input_size = ctypes.sizeof(INPUT)
import struct as _struct
_expected = 40 if _struct.calcsize("P") == 8 else 28
if _input_size != _expected:
    import logging as _logging
    _logging.warning(
        f"INPUT struct size mismatch: got {_input_size}, expected {_expected}. "
        f"SendInput may fail silently. Python arch: {'x64' if _struct.calcsize('P') == 8 else 'x86'}"
    )

_metrics_last_refresh = time.monotonic()
_METRICS_REFRESH_INTERVAL = 30  # seconds between auto-refreshes

def _get_screen_metrics():
    """Return cached virtual screen metrics, auto-refresh every 30s."""
    global _metrics_last_refresh
    now = time.monotonic()
    if _screen_w == 0 or _screen_h == 0 or (now - _metrics_last_refresh > _METRICS_REFRESH_INTERVAL):
        refresh_screen_metrics()
        _metrics_last_refresh = now
    # Fallback to sane defaults if metrics are still 0
    w = _screen_w if _screen_w > 0 else 1920
    h = _screen_h if _screen_h > 0 else 1080
    return w, h, _screen_x, _screen_y

def refresh_screen_metrics():
    """Force refresh virtual screen dimensions (call after display changes)."""
    global _screen_w, _screen_h, _screen_x, _screen_y
    _screen_w = ctypes.windll.user32.GetSystemMetrics(78)
    _screen_h = ctypes.windll.user32.GetSystemMetrics(79)
    _screen_x = ctypes.windll.user32.GetSystemMetrics(76)
    _screen_y = ctypes.windll.user32.GetSystemMetrics(77)
    if _screen_w == 0:
        _screen_w = ctypes.windll.user32.GetSystemMetrics(0)
        _screen_h = ctypes.windll.user32.GetSystemMetrics(1)
        _screen_x = 0
        _screen_y = 0

def send_input_click(x, y, button="left"):
    """Perform a mouse click using Win32 SendInput API."""
    screen_w, screen_h, screen_x, screen_y = _get_screen_metrics()
    clamped_x = max(screen_x, min(x, screen_x + screen_w - 1))
    clamped_y = max(screen_y, min(y, screen_y + screen_h - 1))
    # MED-08: Use 65535 (not 65536) — SendInput absolute range is [0, 65535]
    abs_x = int((clamped_x - screen_x) * 65535 / screen_w)
    abs_y = int((clamped_y - screen_y) * 65535 / screen_h)

    # Move mouse
    move_input = INPUT(type=INPUT_MOUSE)
    move_input.mi.dx = abs_x
    move_input.mi.dy = abs_y
    move_input.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
    ctypes.windll.user32.SendInput(1, ctypes.byref(move_input), ctypes.sizeof(INPUT))

    time.sleep(random.uniform(0.02, 0.05))

    # Mouse down/up
    down_input = INPUT(type=INPUT_MOUSE)
    up_input = INPUT(type=INPUT_MOUSE)

    if button == "left" or button == "double":
        down_input.mi.dwFlags = MOUSEEVENTF_LEFTDOWN
        up_input.mi.dwFlags = MOUSEEVENTF_LEFTUP
    elif button == "right":
        down_input.mi.dwFlags = MOUSEEVENTF_RIGHTDOWN
        up_input.mi.dwFlags = MOUSEEVENTF_RIGHTUP
    elif button == "middle":
        down_input.mi.dwFlags = MOUSEEVENTF_MIDDLEDOWN
        up_input.mi.dwFlags = MOUSEEVENTF_MIDDLEUP
    else:
        down_input.mi.dwFlags = MOUSEEVENTF_LEFTDOWN
        up_input.mi.dwFlags = MOUSEEVENTF_LEFTUP

    def _do_click():
        ctypes.windll.user32.SendInput(1, ctypes.byref(down_input), ctypes.sizeof(INPUT))
        time.sleep(random.uniform(0.03, 0.08))
        ctypes.windll.user32.SendInput(1, ctypes.byref(up_input), ctypes.sizeof(INPUT))

    _do_click()
    if button == "double":
        time.sleep(0.05)
        _do_click()

def send_input_move(x, y):
    """Move mouse using Win32 SendInput API."""
    screen_w, screen_h, screen_x, screen_y = _get_screen_metrics()
    clamped_x = max(screen_x, min(x, screen_x + screen_w - 1))
    clamped_y = max(screen_y, min(y, screen_y + screen_h - 1))
    # MED-08: Use 65535 (not 65536) — SendInput absolute range is [0, 65535]
    abs_x = int((clamped_x - screen_x) * 65535 / screen_w)
    abs_y = int((clamped_y - screen_y) * 65535 / screen_h)

    move_input = INPUT(type=INPUT_MOUSE)
    move_input.mi.dx = abs_x
    move_input.mi.dy = abs_y
    move_input.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
    ctypes.windll.user32.SendInput(1, ctypes.byref(move_input), ctypes.sizeof(INPUT))

def send_unicode_char(char):
    """Send a single unicode character using SendInput."""
    unicode_val = ord(char)

    ki_down = INPUT(type=INPUT_KEYBOARD)
    ki_down.ki.wScan = unicode_val
    ki_down.ki.dwFlags = KEYEVENTF_UNICODE

    ki_up = INPUT(type=INPUT_KEYBOARD)
    ki_up.ki.wScan = unicode_val
    ki_up.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP

    inputs = (INPUT * 2)(ki_down, ki_up)
    ctypes.windll.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))

def send_input_text(text, delay=0.01):
    """Send text using low-level SendInput for maximum compatibility."""
    for char in text:
        send_unicode_char(char)
        if delay > 0:
            time.sleep(random.uniform(delay, delay * 1.5))

def is_admin():
    """Check if the process is running with administrative privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def fast_get_pixel(x, y):
    """COMPAT-03: Get pixel color using Win32 GetPixel (< 1ms vs pyautogui 50-200ms).
    Returns (R, G, B) tuple. Falls back to pyautogui.pixel on failure."""
    try:
        hdc = ctypes.windll.user32.GetDC(0)
        color = ctypes.windll.gdi32.GetPixel(hdc, int(x), int(y))
        ctypes.windll.user32.ReleaseDC(0, hdc)
        if color == -1:  # CLR_INVALID — pixel outside screen or error
            import pyautogui
            return pyautogui.pixel(int(x), int(y))
        # GetPixel returns COLORREF (0x00BBGGRR)
        r = color & 0xFF
        g = (color >> 8) & 0xFF
        b = (color >> 16) & 0xFF
        return (r, g, b)
    except Exception:
        import pyautogui
        return pyautogui.pixel(int(x), int(y))
