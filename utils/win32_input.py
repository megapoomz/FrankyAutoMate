import ctypes
import time
import random
import time as _time
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

# Cache virtual screen dimensions at module level
# SM_XVIRTUALSCREEN=76, SM_YVIRTUALSCREEN=77, SM_CXVIRTUALSCREEN=78, SM_CYVIRTUALSCREEN=79
_screen_x = ctypes.windll.user32.GetSystemMetrics(76)  # Virtual screen left
_screen_y = ctypes.windll.user32.GetSystemMetrics(77)  # Virtual screen top
_screen_w = ctypes.windll.user32.GetSystemMetrics(78)  # Virtual screen width
_screen_h = ctypes.windll.user32.GetSystemMetrics(79)  # Virtual screen height
# Fallback to primary if virtual returns 0
if _screen_w == 0:
    _screen_w = ctypes.windll.user32.GetSystemMetrics(0)
    _screen_h = ctypes.windll.user32.GetSystemMetrics(1)
    _screen_x = 0
    _screen_y = 0


_metrics_last_refresh = _time.monotonic()
_METRICS_REFRESH_INTERVAL = 30  # COMPAT-1: seconds between auto-refreshes


def _get_screen_metrics():
    """Return cached virtual screen metrics, auto-refresh every 30s."""
    global _metrics_last_refresh
    if _screen_w == 0 or _screen_h == 0 or (_time.monotonic() - _metrics_last_refresh > _METRICS_REFRESH_INTERVAL):
        refresh_screen_metrics()
        _metrics_last_refresh = _time.monotonic()
    return _screen_w, _screen_h, _screen_x, _screen_y


def refresh_screen_metrics():
    """COMPAT-1: Force refresh virtual screen dimensions (call after display changes)"""
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
    """Perform a mouse click using Win32 SendInput API"""
    screen_w, screen_h, screen_x, screen_y = _get_screen_metrics()
    abs_x = int((x - screen_x) * 65535 / screen_w)
    abs_y = int((y - screen_y) * 65535 / screen_h)

    # Move mouse
    move_input = INPUT(type=INPUT_MOUSE)
    move_input.mi.dx = abs_x
    move_input.mi.dy = abs_y
    move_input.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
    ctypes.windll.user32.SendInput(1, ctypes.byref(move_input), ctypes.sizeof(INPUT))

    time.sleep(random.uniform(0.01, 0.03))

    # Mouse down
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
    """Move mouse using Win32 SendInput API"""
    screen_w, screen_h, screen_x, screen_y = _get_screen_metrics()
    abs_x = int((x - screen_x) * 65535 / screen_w)
    abs_y = int((y - screen_y) * 65535 / screen_h)

    move_input = INPUT(type=INPUT_MOUSE)
    move_input.mi.dx = abs_x
    move_input.mi.dy = abs_y
    move_input.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
    ctypes.windll.user32.SendInput(1, ctypes.byref(move_input), ctypes.sizeof(INPUT))


def send_unicode_char(char):
    """Send a single unicode character using SendInput"""
    unicode_val = ord(char)

    # Key down
    ki_down = INPUT(type=INPUT_KEYBOARD)
    ki_down.ki.wScan = unicode_val
    ki_down.ki.dwFlags = KEYEVENTF_UNICODE

    # Key up
    ki_up = INPUT(type=INPUT_KEYBOARD)
    ki_up.ki.wScan = unicode_val
    ki_up.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP

    inputs = (INPUT * 2)(ki_down, ki_up)
    ctypes.windll.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))


def send_input_text(text, delay=0.01):
    """Broadcasting text using low-level SendInput for maximum compatibility"""
    for char in text:
        send_unicode_char(char)
        if delay > 0:
            time.sleep(random.uniform(delay, delay * 1.5))


def is_admin():
    """Check if the process is running with administrative privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False
