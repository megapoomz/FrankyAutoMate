"""
Low-level mouse control using Win32 SendInput API
Harder to detect than PyAutoGUI
"""
import ctypes
from ctypes import wintypes
import time
import random

# Constants for SendInput
INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_ABSOLUTE = 0x8000


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    _anonymous_ = ("_input",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("_input", _INPUT),
    ]


def get_screen_size():
    """Get screen dimensions"""
    return (
        ctypes.windll.user32.GetSystemMetrics(0),
        ctypes.windll.user32.GetSystemMetrics(1)
    )


def send_input_move(x, y):
    """Move mouse using Win32 SendInput API"""
    screen_w, screen_h = get_screen_size()
    abs_x = int(x * 65535 / screen_w)
    abs_y = int(y * 65535 / screen_h)
    
    move_input = INPUT(type=INPUT_MOUSE)
    move_input.mi.dx = abs_x
    move_input.mi.dy = abs_y
    move_input.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
    ctypes.windll.user32.SendInput(1, ctypes.byref(move_input), ctypes.sizeof(INPUT))


def send_input_click(x, y, button="left"):
    """Perform a mouse click using Win32 SendInput API"""
    screen_w, screen_h = get_screen_size()
    abs_x = int(x * 65535 / screen_w)
    abs_y = int(y * 65535 / screen_h)
    
    # Move mouse
    move_input = INPUT(type=INPUT_MOUSE)
    move_input.mi.dx = abs_x
    move_input.mi.dy = abs_y
    move_input.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
    ctypes.windll.user32.SendInput(1, ctypes.byref(move_input), ctypes.sizeof(INPUT))
    
    time.sleep(random.uniform(0.01, 0.03))
    
    # Mouse down
    down_input = INPUT(type=INPUT_MOUSE)
    if button == "left":
        down_input.mi.dwFlags = MOUSEEVENTF_LEFTDOWN
    else:
        down_input.mi.dwFlags = MOUSEEVENTF_RIGHTDOWN
    ctypes.windll.user32.SendInput(1, ctypes.byref(down_input), ctypes.sizeof(INPUT))
    
    time.sleep(random.uniform(0.03, 0.08))
    
    # Mouse up
    up_input = INPUT(type=INPUT_MOUSE)
    if button == "left":
        up_input.mi.dwFlags = MOUSEEVENTF_LEFTUP
    else:
        up_input.mi.dwFlags = MOUSEEVENTF_RIGHTUP
    ctypes.windll.user32.SendInput(1, ctypes.byref(up_input), ctypes.sizeof(INPUT))
