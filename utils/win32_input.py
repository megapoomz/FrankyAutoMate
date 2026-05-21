import ctypes
import time
import random
from core.constants import (
    INPUT_MOUSE, INPUT_KEYBOARD, MOUSEEVENTF_MOVE, MOUSEEVENTF_ABSOLUTE,
    MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP, MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP,
    KEYEVENTF_UNICODE, KEYEVENTF_KEYUP, KEYEVENTF_SCANCODE, INPUT
)

# Hardware scan codes for DirectInput games
SCAN_CODES = {
    'esc': 0x01, '1': 0x02, '2': 0x03, '3': 0x04, '4': 0x05, '5': 0x06, '6': 0x07, '7': 0x08, '8': 0x09, '9': 0x0A, '0': 0x0B,
    '-': 0x0C, '=': 0x0D, 'backspace': 0x0E, 'tab': 0x0F, 'q': 0x10, 'w': 0x11, 'e': 0x12, 'r': 0x13, 't': 0x14, 'y': 0x15,
    'u': 0x16, 'i': 0x17, 'o': 0x18, 'p': 0x19, '[': 0x1A, ']': 0x1B, 'enter': 0x1C, 'ctrl': 0x1D, 'a': 0x1E, 's': 0x1F,
    'd': 0x20, 'f': 0x21, 'g': 0x22, 'h': 0x23, 'j': 0x24, 'k': 0x25, 'l': 0x26, ';': 0x27, "'": 0x28, '`': 0x29, 'shift': 0x2A,
    '\\': 0x2B, 'z': 0x2C, 'x': 0x2D, 'c': 0x2E, 'v': 0x2F, 'b': 0x30, 'n': 0x31, 'm': 0x32, ',': 0x33, '.': 0x34, '/': 0x35,
    'alt': 0x38, 'space': 0x39, 'capslock': 0x3A, 'f1': 0x3B, 'f2': 0x3C, 'f3': 0x3D, 'f4': 0x3E, 'f5': 0x3F, 'f6': 0x40,
    'f7': 0x41, 'f8': 0x42, 'f9': 0x43, 'f10': 0x44, 'numlock': 0x45, 'scrolllock': 0x46, 'up': 0xC8, 'down': 0xD0,
    'left': 0xCB, 'right': 0xCD, 'pgup': 0xC9, 'pgdn': 0xD1, 'home': 0xC7, 'end': 0xCF, 'insert': 0xD2, 'delete': 0xD3,
    'f11': 0x57, 'f12': 0x58, 'win': 0xDB
}

def send_hardware_key(key_str, down=True):
    """Sends a hardware scan code keypress that works in ALL DirectInput games"""
    key_str = key_str.lower()
    scan_code = SCAN_CODES.get(key_str)
    if scan_code is None:
        return False # Fallback to pyautogui if key not in map

    flags = KEYEVENTF_SCANCODE
    if not down:
        flags |= KEYEVENTF_KEYUP
        
    # Extended keys need the extended flag (e.g. arrow keys)
    if scan_code > 0x7F:
        flags |= 0x0001 # KEYEVENTF_EXTENDEDKEY
        scan_code = scan_code & 0xFF

    ki = INPUT(type=INPUT_KEYBOARD)
    ki.ki.wScan = scan_code
    ki.ki.wVk = 0 # 0 tells Windows to use wScan
    ki.ki.dwFlags = flags
    
    ctypes.windll.user32.SendInput(1, ctypes.byref(ki), ctypes.sizeof(INPUT))
    return True


def precise_sleep(duration):
    """High-precision sleep that doesn't consume 100% CPU like a traditional spinlock."""
    if duration <= 0:
        return
    start_t = time.perf_counter()
    # If duration is long enough, use standard time.sleep to yield CPU to the OS
    if duration > 0.015:
        time.sleep(duration - 0.005)
    # Spin lock only the remaining milliseconds for sub-millisecond precision
    while time.perf_counter() - start_t < duration:
        pass


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
    
    # Mouse down & up
    down_input = INPUT(type=INPUT_MOUSE)
    up_input = INPUT(type=INPUT_MOUSE)
    
    down_input.mi.dx = abs_x
    down_input.mi.dy = abs_y
    up_input.mi.dx = abs_x
    up_input.mi.dy = abs_y
    
    if button == "left" or button == "double":
        down_input.mi.dwFlags = MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE | 0x4000
        up_input.mi.dwFlags = MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE | 0x4000
    elif button == "right":
        down_input.mi.dwFlags = MOUSEEVENTF_RIGHTDOWN | MOUSEEVENTF_ABSOLUTE | 0x4000
        up_input.mi.dwFlags = MOUSEEVENTF_RIGHTUP | MOUSEEVENTF_ABSOLUTE | 0x4000
    else:
        # middle or other fallbacks
        down_input.mi.dwFlags = MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE | 0x4000
        up_input.mi.dwFlags = MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE | 0x4000
        
    def _do_click():
        # Move mouse
        move_input = INPUT(type=INPUT_MOUSE)
        move_input.mi.dx = abs_x
        move_input.mi.dy = abs_y
        move_input.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | 0x4000
        ctypes.windll.user32.SendInput(1, ctypes.byref(move_input), ctypes.sizeof(INPUT))
        
        time.sleep(random.uniform(0.01, 0.02))
        
        # Mouse down
        ctypes.windll.user32.SendInput(1, ctypes.byref(down_input), ctypes.sizeof(INPUT))
        
        # High precision hold duration to prevent missed clicks without burning CPU
        hold_time = random.uniform(0.06, 0.12)
        precise_sleep(hold_time)
            
        # Mouse up
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
