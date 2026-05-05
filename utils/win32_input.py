import ctypes
import time
import random
from core.constants import (
    INPUT_MOUSE, INPUT_KEYBOARD, MOUSEEVENTF_MOVE, MOUSEEVENTF_ABSOLUTE,
    MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP, MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP,
    KEYEVENTF_UNICODE, KEYEVENTF_KEYUP, INPUT
)

def send_input_click(x, y, button="left"):
    """Perform a mouse click using Win32 SendInput API"""
    screen_w = ctypes.windll.user32.GetSystemMetrics(78)
    screen_h = ctypes.windll.user32.GetSystemMetrics(79)
    v_left = ctypes.windll.user32.GetSystemMetrics(76)
    v_top = ctypes.windll.user32.GetSystemMetrics(77)
    if screen_w == 0: screen_w = ctypes.windll.user32.GetSystemMetrics(0)
    if screen_h == 0: screen_h = ctypes.windll.user32.GetSystemMetrics(1)
    
    abs_x = int(((x - v_left) * 65535) / screen_w)
    abs_y = int(((y - v_top) * 65535) / screen_h)
    
    # Move mouse
    move_input = INPUT(type=INPUT_MOUSE)
    move_input.mi.dx = abs_x
    move_input.mi.dy = abs_y
    move_input.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | 0x4000
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
    else:
        # middle or other fallbacks
        down_input.mi.dwFlags = MOUSEEVENTF_LEFTDOWN
        up_input.mi.dwFlags = MOUSEEVENTF_LEFTUP
        
    def _do_click():
        ctypes.windll.user32.SendInput(1, ctypes.byref(down_input), ctypes.sizeof(INPUT))
        
        # High precision hold duration to prevent missed clicks
        hold_time = random.uniform(0.06, 0.12)
        start_t = time.perf_counter()
        while time.perf_counter() - start_t < hold_time:
            pass
            
        ctypes.windll.user32.SendInput(1, ctypes.byref(up_input), ctypes.sizeof(INPUT))

    _do_click()
    if button == "double":
        time.sleep(0.05)
        _do_click()

def send_input_move(x, y):
    """Move mouse using Win32 SendInput API"""
    screen_w = ctypes.windll.user32.GetSystemMetrics(78)
    screen_h = ctypes.windll.user32.GetSystemMetrics(79)
    v_left = ctypes.windll.user32.GetSystemMetrics(76)
    v_top = ctypes.windll.user32.GetSystemMetrics(77)
    if screen_w == 0: screen_w = ctypes.windll.user32.GetSystemMetrics(0)
    if screen_h == 0: screen_h = ctypes.windll.user32.GetSystemMetrics(1)
    
    abs_x = int(((x - v_left) * 65535) / screen_w)
    abs_y = int(((y - v_top) * 65535) / screen_h)
    
    move_input = INPUT(type=INPUT_MOUSE)
    move_input.mi.dx = abs_x
    move_input.mi.dy = abs_y
    move_input.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | 0x4000
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
    except:
        return False
