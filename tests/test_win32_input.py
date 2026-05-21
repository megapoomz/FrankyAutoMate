"""
Unit tests for the win32_input low-level simulation module.
Tests: screen metrics caching, precise sleep, SCAN_CODES, admin status,
and SendInput structure layouts for keyboard, mouse, and unicode characters.
"""
import ctypes
import time
import pytest
from unittest.mock import patch, MagicMock

import utils.win32_input as win32_input
from core.constants import (
    INPUT_MOUSE, INPUT_KEYBOARD, MOUSEEVENTF_MOVE, MOUSEEVENTF_ABSOLUTE,
    MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP, KEYEVENTF_UNICODE, KEYEVENTF_KEYUP,
    KEYEVENTF_SCANCODE
)


def test_scan_codes_mapping():
    """Verify key scan codes map correctly to expected values."""
    assert win32_input.SCAN_CODES["a"] == 0x1E
    assert win32_input.SCAN_CODES["w"] == 0x11
    assert win32_input.SCAN_CODES["esc"] == 0x01
    assert win32_input.SCAN_CODES["space"] == 0x39
    assert win32_input.SCAN_CODES["f1"] == 0x3B


def test_precise_sleep_short():
    """Verify precise sleep runs accurately without raising exceptions."""
    t0 = time.perf_counter()
    win32_input.precise_sleep(0.005)
    t1 = time.perf_counter()
    # It should sleep at least approximately the requested duration
    assert (t1 - t0) >= 0.004


def test_is_admin():
    """Verify is_admin returns a boolean value."""
    admin = win32_input.is_admin()
    assert isinstance(admin, bool)


def test_screen_metrics_caching():
    """Verify screen metrics caching gets sensible multi-monitor bounds."""
    w, h, x, y = win32_input._get_screen_metrics()
    assert w > 0
    assert h > 0
    # Refresh metrics explicitly
    win32_input.refresh_screen_metrics()
    assert win32_input._screen_w > 0


@patch("ctypes.byref", lambda x: x)
@patch("ctypes.windll.user32.SendInput")
def test_send_hardware_key(mock_send_input):
    """Verify send_hardware_key constructs the keyboard INPUT structure correctly."""
    mock_send_input.return_value = 1

    # Key down
    res1 = win32_input.send_hardware_key("a", down=True)
    assert res1 is True
    assert mock_send_input.call_count == 1
    args, _ = mock_send_input.call_args
    assert args[0] == 1  # 1 structure
    input_struct = args[1]
    assert input_struct.type == INPUT_KEYBOARD
    assert input_struct.ki.wScan == 0x1E
    assert input_struct.ki.wVk == 0
    assert input_struct.ki.dwFlags == KEYEVENTF_SCANCODE

    # Key up
    res2 = win32_input.send_hardware_key("a", down=False)
    assert res2 is True
    assert mock_send_input.call_count == 2
    args, _ = mock_send_input.call_args
    input_struct = args[1]
    assert input_struct.ki.dwFlags == (KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP)


@patch("ctypes.windll.user32.SendInput")
def test_send_hardware_key_invalid(mock_send_input):
    """Verify invalid key names are rejected with False."""
    res = win32_input.send_hardware_key("invalid_key_name")
    assert res is False
    assert mock_send_input.call_count == 0


@patch("ctypes.byref", lambda x: x)
@patch("ctypes.windll.user32.SendInput")
def test_send_unicode_char(mock_send_input):
    """Verify send_unicode_char passes correct down and up inputs."""
    mock_send_input.return_value = 2
    win32_input.send_unicode_char("A")

    assert mock_send_input.call_count == 1
    args, _ = mock_send_input.call_args
    assert args[0] == 2  # Sends 2 inputs (down and up array)
    
    input_array = args[1]
    
    # Down key
    assert input_array[0].type == INPUT_KEYBOARD
    assert input_array[0].ki.wScan == ord("A")
    assert input_array[0].ki.dwFlags == KEYEVENTF_UNICODE

    # Up key
    assert input_array[1].type == INPUT_KEYBOARD
    assert input_array[1].ki.wScan == ord("A")
    assert input_array[1].ki.dwFlags == (KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)


@patch("ctypes.byref", lambda x: x)
@patch("ctypes.windll.user32.SendInput")
@patch("time.sleep")
def test_send_input_click(mock_sleep, mock_send_input):
    """Verify send_input_click moves and clicks correctly."""
    mock_send_input.return_value = 1
    
    # Left click at (100, 200)
    win32_input.send_input_click(100, 200, button="left")
    
    # We expect 3 SendInput calls:
    # 1. Mouse move
    # 2. Mouse down
    # 3. Mouse up
    assert mock_send_input.call_count == 3
    
    # First call: Move
    move_args = mock_send_input.call_args_list[0][0]
    assert move_args[0] == 1
    move_struct = move_args[1]
    assert move_struct.type == INPUT_MOUSE
    assert move_struct.mi.dwFlags == (MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | 0x4000)
    
    # Second call: Left down
    down_args = mock_send_input.call_args_list[1][0]
    down_struct = down_args[1]
    assert down_struct.type == INPUT_MOUSE
    assert down_struct.mi.dwFlags == MOUSEEVENTF_LEFTDOWN

    # Third call: Left up
    up_args = mock_send_input.call_args_list[2][0]
    up_struct = up_args[1]
    assert up_struct.type == INPUT_MOUSE
    assert up_struct.mi.dwFlags == MOUSEEVENTF_LEFTUP


@patch("ctypes.byref", lambda x: x)
@patch("ctypes.windll.user32.SendInput")
def test_send_input_move(mock_send_input):
    """Verify send_input_move shifts mouse accurately."""
    mock_send_input.return_value = 1
    win32_input.send_input_move(500, 600)
    
    assert mock_send_input.call_count == 1
    args = mock_send_input.call_args[0]
    assert args[0] == 1
    move_struct = args[1]
    assert move_struct.type == INPUT_MOUSE
    assert move_struct.mi.dwFlags == (MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | 0x4000)


@patch("utils.win32_input.send_unicode_char")
@patch("time.sleep")
def test_send_input_text(mock_sleep, mock_send_unicode_char):
    """Verify send_input_text loops correctly over chars."""
    win32_input.send_input_text("Hello", delay=0.0)
    
    assert mock_send_unicode_char.call_count == 5
    mock_send_unicode_char.assert_any_call("H")
    mock_send_unicode_char.assert_any_call("e")
    mock_send_unicode_char.assert_any_call("l")
    mock_send_unicode_char.assert_any_call("o")
