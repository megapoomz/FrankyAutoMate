import time
import sys
import threading
import random
import math
import logging
import os
import ctypes
import ctypes.wintypes
import numpy as np
import cv2
import mss
import pyautogui
# SEC-6: Keep failsafe disabled by default for automation compatibility,
# but wrap pyautogui calls to handle FailSafeException gracefully
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0
import pyperclip
import win32gui
import win32con
import win32api
try:
    import pytesseract
except ImportError:
    pytesseract = None

from typing import Dict, Any, List, Optional
from core.constants import (
    COLOR_ACCENT, COLOR_BG, COLOR_DANGER, COLOR_SUCCESS, COLOR_WARNING,
    INPUT_MOUSE, INPUT_KEYBOARD, MOUSEEVENTF_MOVE, MOUSEEVENTF_ABSOLUTE,
    MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP, MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP,
    KEYEVENTF_UNICODE, KEYEVENTF_KEYUP, INPUT
)
from utils.win32_input import send_input_click, send_input_move, send_input_text

class EngineMixin:
    """Handles automation execution, background runner, and single action logic"""
    # --- Thread-Safe UI Helpers ---
    def safe_update_ui(self, widget_name: str, **kwargs):
        """Schedule UI updates on the main thread to prevent crashes"""
        def _update():
            try:
                # Find widget by name if possible, or assume it's an attribute
                widget = getattr(self, widget_name, None)
                if widget:
                    widget.configure(**kwargs)
            except Exception as e:
                print(f"UI Update Error ({widget_name}): {e}")
        
        # If we are already on main thread, just run it (simple check)
        if threading.current_thread() is threading.main_thread():
             _update()
        else:
             self.after(0, _update)

    def run_automation(self) -> None:
        if self.is_running:
            # Step Mode: If paused in step mode, advance to next step
            if self.is_paused and self.var_step_mode.get():
                self.is_paused = False
                self.next_step.set()
                return
            # Normal Mode: STOP immediately
            self.stop_automation()
            return

        self.save_current_to_preset()
        self.auto_save_presets()
        try: loops = int(self.entry_loop.get())
        except (ValueError, TypeError): loops = 1
        self.is_running = True
        self.safe_update_ui('btn_run', text="หยุด (STOP)", fg_color="#c0392b")
        self.stealth_on_run_start() # Apply stealth settings
        self.show_running_overlay() # Show overlay warning
        self.execution_thread = threading.Thread(target=self.bg_runner, args=(loops,))
        self.execution_thread.daemon = True
        self.execution_thread.start()

    def stop_automation(self) -> None:
        self.is_running = False
        self.is_paused = False
        self.next_step.set() # Release if waiting
        self.stealth_on_run_stop() # Restore window
        self.hide_running_overlay() # Hide overlay
        self.safe_update_ui('btn_run', text="เริ่มทำงาน (START)", fg_color="#27ae60")
        self.safe_update_ui('lbl_status', text="[STOP] กำลังสั่งหยุดทำงาน...", text_color="#e67e22")

    def bg_runner(self, loops: int) -> None:
        import copy
        count = 0
        self.log_message("=== เริ่มทำงานอัตโนมัติ ===")
        self.perf_metrics["start_time"] = time.perf_counter()
        self.perf_metrics["actions_exec"] = []
        # INCMP-1: Reset variables at run start
        with self.variable_lock:
            self.variables.clear()
        # Initialize mss instance in the worker thread (GDI handles are thread-local)
        try:
            self.sct = mss.mss()
        except Exception:
            self.sct = None
        while self.is_running:
            if loops > 0 and count >= loops: break
            count += 1
            loop_msg = f"รอบที่ {count}" + (f" /{loops}" if loops > 0 else "")
            self.log_message(f"--- {loop_msg} ---")
            
            i = 0
            # BUG-2: Deep copy to prevent mutation from UI thread
            with self.actions_lock:
                run_actions = copy.deepcopy(self.actions)
            # Rebuild label index cache each loop for sync safety
            self._label_index_cache = {}
            for idx, act in enumerate(run_actions):
                if act.get("type") == "logic_label":
                    self._label_index_cache[act.get("name", "")] = idx
            num_actions = len(run_actions)
            while i < num_actions:
                if not self.is_running: break

                # --- STEP START: High Frequency Window Context Check ---
                # 1. Dynamic Following (If enabled)
                if getattr(self, 'var_follow_window', None) and self.var_follow_window.get():
                    fw = win32gui.GetForegroundWindow()
                    if fw and fw != self.target_hwnd and win32gui.IsWindowVisible(fw):
                        try:
                            title = win32gui.GetWindowText(fw)
                            if title and title != self.original_title and "Franky" not in title:
                                self.target_hwnd = fw
                                self.target_title = title
                                self.safe_update_ui('lbl_target', text=f"เป้าหมาย (Auto): {self.target_title}")
                        except Exception: pass
                # INST-4: Validate target_hwnd is still valid (not recycled)
                elif self.target_hwnd:
                    if hasattr(self, '_validate_target_hwnd'):
                        self._validate_target_hwnd()

                # 2. Ensure context focus (If a target is locked/followed)
                # Skip forcing focus if the current action uses background mode
                action_mode = run_actions[i].get("mode", "normal") if i < num_actions else "normal"
                click_mode = run_actions[i].get("click_mode", "normal") if i < num_actions else "normal"
                is_bg_action = (action_mode == "background" or click_mode == "background")
                if self.target_hwnd and win32gui.IsWindow(self.target_hwnd) and not is_bg_action:
                    try:
                        if win32gui.GetForegroundWindow() != self.target_hwnd:
                            # Use Alt-key trick but with minimal delay during steps
                            win32api.keybd_event(18, 0, 0, 0)
                            win32gui.SetForegroundWindow(self.target_hwnd)
                            win32api.keybd_event(18, 0, 2, 0)
                            time.sleep(0.05) # Brief focus wait
                    except Exception: pass
                # --- END STEP CONTEXT ---
                
                action = run_actions[i]
                
                # Handling Paused State (General or Step Mode)
                if self.is_paused or self.var_step_mode.get():
                    if self.var_step_mode.get():
                        self.safe_update_ui('btn_run', text="[NEXT] ต่อไป (NEXT STEP)", fg_color="#3498db")
                        self.safe_update_ui('lbl_status', text=f"[PAUSED] ขั้นตอน {i+1}: รอคำสั่ง...", text_color="#f1c40f")
                    
                    self.is_paused = True # Force pause if step mode
                    self.next_step.clear()
                    while self.is_paused and self.is_running:
                        if self.next_step.wait(0.1): break
                    
                    # Reset button after resume
                    self.safe_update_ui('btn_run', text="[STOP] หยุด (STOP)", fg_color="#c0392b")

                    # Recover focus to target window if using foreground methods
                    if self.target_hwnd and win32gui.IsWindow(self.target_hwnd):
                        try:
                            if win32gui.GetForegroundWindow() != self.target_hwnd:
                                win32api.keybd_event(18, 0, 0, 0)
                                win32gui.SetForegroundWindow(self.target_hwnd)
                                win32api.keybd_event(18, 0, 2, 0)
                                win32gui.BringWindowToTop(self.target_hwnd)
                                time.sleep(0.3)
                        except Exception: pass

                if not self.is_running: break
                self.highlight_action(i)
                
                try:
                    # Execute and handle jumping logic
                    jump_to = self.execute_one(action, i, run_actions)
                    
                    if jump_to is not None:
                        i = jump_to
                        continue # Skip standard increment
                        
                except Exception as e:
                    self.log_message(f"[ERROR] เกิดข้อผิดพลาดที่ขั้นตอน {i+1}: {e}", "red")
                    self.is_running = False
                    self.safe_update_ui('lbl_status', text=f"[ERROR] ข้อผิดพลาด: {e}", text_color="red")
                    break
                
                # Default increment
                i += 1
                
                # Delay between steps
                if i < len(self.actions) and not self.var_step_mode.get():
                    time.sleep(0.005 + self.speed_delay)
        
        self.is_running = False
        # Release mss GDI handle to prevent resource leak
        if getattr(self, 'sct', None) is not None:
            try: self.sct.close()
            except Exception: pass
            self.sct = None
        self.after(0, self.hide_running_overlay) # Thread-safe overlay hide
        duration = time.perf_counter() - self.perf_metrics.get("start_time", time.perf_counter())
        self.highlight_action(-1)
        self.safe_update_ui('btn_run', text="เริ่มทำงาน (START)", fg_color="#27ae60")
        self.safe_update_ui('lbl_status', text="จบการทำงาน", text_color="#2ecc71")
        
        # Performance Summary
        total_actions = len(self.perf_metrics.get("actions_exec", []))
        self.log_message(f"=== จบการทำงาน (รวม {total_actions} ขั้นตอน, ใช้เวลา {duration:.1f}s) ===")
        if total_actions > 0 and self.var_debug_mode.get():
             avg = (duration * 1000) / total_actions
             self.log_message(f"📊 เฉลี่ย: {avg:.0f}ms ต่อขั้นตอน", level=logging.DEBUG)

    def execute_one(self, action: Dict[str, Any], current_index: int, run_actions: list = None) -> Optional[int]:
        start_time = time.perf_counter()
        t = action["type"]
        jump_target = None
        
        try:
            if t == "click": self._execute_click(action)
            elif t == "text": self._execute_text(action)
            elif t == "hotkey": self._execute_hotkey(action)
            elif t == "wait": self._execute_wait(action)
            elif t == "image_search": self._execute_image_search(action)
            elif t == "color_search": self._execute_color_search(action)
            elif t == "multi_color_check": self._execute_multi_color_check(action)
            elif t == "ocr_search": self._execute_ocr_search(action)
            
            # Variable & Logic Engine (NEW Phase 3)
            elif t == "var_set": self._execute_var_set(action)
            elif t == "var_math": self._execute_var_math(action)
            elif t == "logic_if": jump_target = self._execute_logic_if(action, current_index, run_actions)
            elif t == "logic_jump" or t == "logic_else": jump_target = self._execute_logic_jump(action, current_index, run_actions)
            elif t == "logic_label": pass # Labels do nothing when hit sequentially
            
            elapsed = (time.perf_counter() - start_time) * 1000
            self.perf_metrics.setdefault("actions_exec", []).append(elapsed)
            
            # Simplified log if not debug
            if self.var_debug_mode.get():
                self.log_message(f"  [TIME] {t}: {elapsed:.0f}ms", "#7f8c8d", level=logging.DEBUG)
            
            self.safe_update_ui('lbl_status', text=f"รัน {t}: {elapsed:.0f}ms", text_color="#3498db")
            
            # Universal stop_after check for all action types
            if action.get("stop_after", False) and self.is_running:
                self.is_running = False
                self.log_message("[STOP] จบการทำงานตามเงื่อนไข 'จบงานทันที'")
            
            return jump_target
        except Exception as e:
            self.log_message(f"[FAIL] คำสั่ง {t} ล้มเหลว: {e}", "red")
            raise

    def _human_move(self, tx: float, ty: float) -> None:
        """Move mouse in a human-like curve using Bezier points (uses SendInput for speed)"""
        start_x, start_y = pyautogui.position()
        dist = math.hypot(tx - start_x, ty - start_y)
        if dist < 20:
            send_input_move(int(tx), int(ty))
            return

        cp1_x = start_x + (tx - start_x) * random.uniform(0.1, 0.4) + random.randint(-50, 50)
        cp1_y = start_y + (ty - start_y) * random.uniform(0.1, 0.4) + random.randint(-50, 50)
        cp2_x = start_x + (tx - start_x) * random.uniform(0.6, 0.9) + random.randint(-50, 50)
        cp2_y = start_y + (ty - start_y) * random.uniform(0.6, 0.9) + random.randint(-50, 50)
        # PERF-5: Cap max steps at 80 to prevent slow moves on 4K displays
        steps = int(min(80, max(10, dist / random.uniform(15, 25))))
        
        for i in range(steps + 1):
            t = i / steps
            x = (1-t)**3 * start_x + 3*(1-t)**2 * t * cp1_x + 3*(1-t) * t**2 * cp2_x + t**3 * tx
            y = (1-t)**3 * start_y + 3*(1-t)**2 * t * cp1_y + 3*(1-t) * t**2 * cp2_y + t**3 * ty
            send_input_move(int(x), int(y))
            if i % 2 == 0:
                time.sleep(random.uniform(0.001, 0.003))

    def _get_abs_coords(self, x: float, y: float, relative: bool = False) -> tuple[int, int]:
        """Standardized conversion of relative/client coordinates to absolute screen coordinates"""
        if not relative: return int(x), int(y)
        if self.target_hwnd and win32gui.IsWindow(self.target_hwnd):
            try:
                rect = win32gui.GetWindowRect(self.target_hwnd)
                return int(x + rect[0]), int(y + rect[1])
            except Exception: pass
        return int(x), int(y)

    def _execute_click(self, action: Dict[str, Any]) -> None:
        fx, fy = action["x"], action["y"]
        mode = action.get("mode", "normal")
        button = action["button"]
        is_rel = action.get("relative", False)
        
        target_x, target_y = fx, fy
        if self.var_stealth_jitter.get():
            r = self.var_stealth_jitter_radius.get()
            target_x += random.uniform(-r, r)
            target_y += random.uniform(-r, r)

        # Always convert to absolute for consistency
        final_x, final_y = self._get_abs_coords(target_x, target_y, is_rel)
        
        self.log_message(f"[CLICK] คลิก {button} ที่ {target_x:.1f},{target_y:.1f} ({mode})")
        
        self.perform_click(final_x, final_y, button, mode)

    def _execute_text(self, action: Dict[str, Any]) -> None:
        c = action["content"]
        dry = self.var_dry_run.get()
        prefix = "[DRY RUN] " if dry else ""
        self.log_message(f"{prefix}[TYPE] พิมพ์: {c}")
        if dry: return
        
        mode = action.get("mode", "normal")
        
        # Background Mode Logic
        if mode == "background":
            target = getattr(self, 'last_child_hwnd', self.target_hwnd)
            if not target or not win32gui.IsWindow(target):
                 # Fallback if window handle is invalid
                 target = self.target_hwnd
            
            if target:
                for char in c:
                    try:
                        win32gui.PostMessage(target, win32con.WM_CHAR, ord(char), 0)
                        time.sleep(random.uniform(0.02, 0.05))
                    except Exception: pass
                return

        # Normal/Foreground Logic
        if self.target_hwnd and win32gui.IsWindow(self.target_hwnd):
            # Always try to focus before typing if possible
            try:
                if win32gui.GetForegroundWindow() != self.target_hwnd:
                    win32gui.SetForegroundWindow(self.target_hwnd)
                    time.sleep(0.2)
            except Exception: pass
            
        # Execute typing using the most robust method available
        if self.var_stealth_sendinput.get():
            send_input_text(c, delay=0.01)
        else:
            # POT-5: Use try-finally to ensure clipboard is always restored
            old_clip = None
            try:
                try:
                    old_clip = pyperclip.paste()
                except Exception: pass
                pyperclip.copy(c)
                time.sleep(0.03)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.05)
            except Exception:
                # Fallback: SendInput character by character
                send_input_text(c, delay=0.01)
            finally:
                # Always restore original clipboard
                if old_clip is not None:
                    try: pyperclip.copy(old_clip)
                    except Exception: pass
        time.sleep(0.03)

    def _execute_hotkey(self, action: Dict[str, Any]) -> None:
        key = action["content"]
        mode = action.get("mode", "normal")
        dry = self.var_dry_run.get()
        prefix = "[DRY RUN] " if dry else ""
        self.log_message(f"{prefix}[KEY] กดคีย์ลัด: {key} ({mode})")
        if dry: return

        # --- Comprehensive VK Code Map (shared by BG and normal fallback) ---
        vk_map = {
            # Modifier keys
            'ctrl': 0x11, 'control': 0x11, 'lctrl': 0x11, 'rctrl': 0x11,
            'alt': 0x12, 'menu': 0x12, 'lalt': 0x12, 'ralt': 0x12,
            'shift': 0x10, 'lshift': 0x10, 'rshift': 0x10,
            'win': 0x5B, 'lwin': 0x5B, 'rwin': 0x5C,
            # Navigation / editing
            'enter': 0x0D, 'return': 0x0D,
            'tab': 0x09, 'backspace': 0x08, 'delete': 0x2E,
            'esc': 0x1B, 'escape': 0x1B, 'space': 0x20,
            'insert': 0x2D, 'home': 0x24, 'end': 0x23,
            'pgup': 0x21, 'pageup': 0x21, 'page_up': 0x21,
            'pgdn': 0x22, 'pagedown': 0x22, 'page_down': 0x22,
            # Arrow keys
            'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27,
            # Function keys
            'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
            'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
            'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
            # Misc
            'capslock': 0x14, 'numlock': 0x90, 'scrolllock': 0x91,
            'printscreen': 0x2C, 'prtsc': 0x2C, 'pause': 0x13,
        }
        # Scan code map for proper lParam construction
        scan_map = {
            0x11: 0x1D, 0x12: 0x38, 0x10: 0x2A,  # Ctrl, Alt, Shift
            0x0D: 0x1C, 0x09: 0x0F, 0x08: 0x0E,   # Enter, Tab, Backspace
            0x2E: 0x53, 0x1B: 0x01, 0x20: 0x39,    # Delete, Esc, Space
            0x2D: 0x52, 0x24: 0x47, 0x23: 0x4F,    # Insert, Home, End
            0x21: 0x49, 0x22: 0x51,                 # PgUp, PgDn
            0x26: 0x48, 0x28: 0x50, 0x25: 0x4B, 0x27: 0x4D,  # Arrows
        }
        modifier_set = {'ctrl', 'control', 'lctrl', 'rctrl', 'alt', 'menu', 'lalt', 'ralt',
                        'shift', 'lshift', 'rshift', 'win', 'lwin', 'rwin'}

        # Background Hotkey Logic
        if mode == "background":
            target = getattr(self, 'last_child_hwnd', self.target_hwnd)
            # POT-4: Validate cached child handle is still valid
            if target and not win32gui.IsWindow(target):
                target = self.target_hwnd
            if not target: target = self.target_hwnd
            if target:
                keys_clean = key.lower().replace(" ", "")
                
                # Special Handler: CTRL+A (Select All) — use EM_SETSEL for reliability
                if keys_clean in ["ctrl+a", "^a"]:
                    try:
                        win32gui.PostMessage(target, win32con.WM_SETFOCUS, 0, 0)
                        time.sleep(0.02)
                        ctypes.windll.user32.SendMessageW(target, 0x00B1, 0, -1)
                        # Reinforcement with key messages
                        win32gui.PostMessage(target, win32con.WM_KEYDOWN, 0x11, 0x001D0001)
                        time.sleep(0.01)
                        win32gui.PostMessage(target, win32con.WM_KEYDOWN, 0x41, 0x001E0001)
                        time.sleep(0.01)
                        win32gui.PostMessage(target, win32con.WM_CHAR, 1, 0x001E0001)
                        time.sleep(0.01)
                        win32gui.PostMessage(target, win32con.WM_KEYUP, 0x41, 0xC01E0001)
                        win32gui.PostMessage(target, win32con.WM_KEYUP, 0x11, 0xC01D0001)
                        return
                    except Exception: pass

                # Parse key combination into parts
                parts = [k.strip().lower() for k in key.split('+')]
                modifiers = [p for p in parts if p in modifier_set]
                main_keys = [p for p in parts if p not in modifier_set]
                
                has_alt = any(m in ('alt', 'menu', 'lalt', 'ralt') for m in modifiers)
                has_ctrl = any(m in ('ctrl', 'control', 'lctrl', 'rctrl') for m in modifiers)
                has_shift = any(m in ('shift', 'lshift', 'rshift') for m in modifiers)
                
                # Build lParam helper
                def make_lparam(scan, repeat=1, extended=False, prev_state=False, transition=False):
                    lp = repeat & 0xFFFF
                    lp |= (scan & 0xFF) << 16
                    if extended: lp |= (1 << 24)
                    if prev_state: lp |= (1 << 30)
                    if transition: lp |= (1 << 31)
                    return lp
                
                try:
                    # For Alt combos, use WM_SYSKEYDOWN/WM_SYSKEYUP
                    # This is how Windows processes Alt+key combinations
                    
                    # 1. Press modifier keys down
                    if has_ctrl:
                        sc = scan_map.get(0x11, 0x1D)
                        win32gui.PostMessage(target, win32con.WM_KEYDOWN, 0x11, make_lparam(sc))
                        time.sleep(0.01)
                    if has_shift:
                        sc = scan_map.get(0x10, 0x2A)
                        win32gui.PostMessage(target, win32con.WM_KEYDOWN, 0x10, make_lparam(sc))
                        time.sleep(0.01)
                    if has_alt:
                        sc = scan_map.get(0x12, 0x38)
                        win32gui.PostMessage(target, win32con.WM_SYSKEYDOWN, 0x12, make_lparam(sc))
                        time.sleep(0.01)
                    
                    # 2. Press and release main keys
                    key_down_msg = win32con.WM_SYSKEYDOWN if has_alt else win32con.WM_KEYDOWN
                    key_up_msg = win32con.WM_SYSKEYUP if has_alt else win32con.WM_KEYUP
                    
                    for mk in main_keys:
                        vk = vk_map.get(mk)
                        if vk is None:
                            # Single character: use VkKeyScan to get VK code
                            if len(mk) == 1:
                                vk = win32api.VkKeyScan(mk) & 0xFF
                            else:
                                continue
                        sc = scan_map.get(vk, 0)
                        lp_down = make_lparam(sc)
                        if has_alt: lp_down |= (1 << 29)  # Context code: ALT is held
                        
                        win32gui.PostMessage(target, key_down_msg, vk, lp_down)
                        time.sleep(0.02)
                        
                        lp_up = make_lparam(sc, prev_state=True, transition=True)
                        if has_alt: lp_up |= (1 << 29)
                        win32gui.PostMessage(target, key_up_msg, vk, lp_up)
                        time.sleep(0.01)
                    
                    # 3. Release modifier keys (reverse order)
                    if has_alt:
                        sc = scan_map.get(0x12, 0x38)
                        win32gui.PostMessage(target, win32con.WM_KEYUP, 0x12, make_lparam(sc, prev_state=True, transition=True))
                    if has_shift:
                        sc = scan_map.get(0x10, 0x2A)
                        win32gui.PostMessage(target, win32con.WM_KEYUP, 0x10, make_lparam(sc, prev_state=True, transition=True))
                    if has_ctrl:
                        sc = scan_map.get(0x11, 0x1D)
                        win32gui.PostMessage(target, win32con.WM_KEYUP, 0x11, make_lparam(sc, prev_state=True, transition=True))
                    
                except Exception as e:
                    self.log_message(f"[BG KEY ERR] {e}", "red", level=logging.WARNING)
            return

        # Normal Mode
        time.sleep(0.03)
        keys = [k.strip().lower() for k in key.split('+')]
        # Normalize key names for pyautogui compatibility
        name_fix = {
            "control": "ctrl", "ctlr": "ctrl",
            "return": "enter", "esc": "escape",
            "pgup": "pageup", "pgdn": "pagedown",
            "page_up": "pageup", "page_down": "pagedown",
            "prtsc": "printscreen",
        }
        keys = [name_fix.get(k, k) for k in keys]
        pyautogui.hotkey(*keys)
        time.sleep(0.03)

    def _execute_wait(self, action: Dict[str, Any]) -> None:
        secs = float(action["seconds"])
        if self.var_stealth_timing.get():
            variance = self.var_stealth_timing_val.get()
            # BUG-5: Clamp factor to prevent zero/negative wait
            factor = max(0.1, 1.0 + random.uniform(-variance, variance))
            secs *= factor
            self.log_message(f"[WAIT] รอ: {secs:.2f} วินาที (สุ่มจาก {action['seconds']}s)", level=logging.DEBUG)
        else:
            self.log_message(f"[WAIT] รอ: {secs:.2f} วินาที")
        
        wait_time = max(0, secs)
        start_wait = time.perf_counter()
        # Active wait loop to allow for immediate stop
        while self.is_running and (time.perf_counter() - start_wait) < wait_time:
            time.sleep(0.01)

    def _execute_image_search(self, action: Dict[str, Any]) -> None:
        path, mode = action["path"], action.get("mode", "wait")
        do_click, off_x, off_y = action.get("do_click", True), action.get("off_x", 0), action.get("off_y", 0)
        region = action.get("region")
        confidence = action.get("confidence", 0.75)
        max_wait_time = action.get("max_wait_time", 120)  # POT-1: Default 120s timeout for wait mode
        
        m_txt = "รอจนกว่าจะเจอ" if mode == "wait" else "เช็คครั้งเดียว"
        self.log_message(f"[FIND] ค้นหารูป: {os.path.basename(path)} ({m_txt}, grayscale)")
        
        found_loc = None
        max_val = 0  # Initialize to prevent UnboundLocalError on fallback path
        
        # Validate image file exists and refresh cache if file was modified
        if not os.path.exists(path):
            self.log_message(f"[ERROR] ไม่พบไฟล์รูปภาพ: {path}", "red")
            return
        
        # BUG-1: Check file modification time to detect stale cache
        file_mtime = os.path.getmtime(path)
        cache_mtime = self.image_cache.get((path, "mtime"), 0)
        if path not in self.image_cache or file_mtime != cache_mtime:
            self.image_cache[path] = cv2.imread(path)
            self.image_cache[(path, "mtime")] = file_mtime
            # Invalidate grayscale cache for this path
            self.image_cache.pop((path, "gray"), None)
        
        # POT-6: LRU limit — evict oldest entries if cache exceeds limit
        _MAX_IMAGE_CACHE = 100
        if len(self.image_cache) > _MAX_IMAGE_CACHE:
            # Remove first 20 entries (approx oldest)
            keys_to_remove = list(self.image_cache.keys())[:20]
            for k in keys_to_remove:
                self.image_cache.pop(k, None)
        
        # Pre-convert template to grayscale (cached separately to avoid contaminating BGR cache)
        gray_key = (path, "gray")
        template_bgr = self.image_cache[path]
        if template_bgr is None:
            self.log_message(f"[ERROR] อ่านไฟล์รูปภาพไม่ได้: {path}", "red")
            return
        if gray_key not in self.image_cache:
            if len(template_bgr.shape) == 3:
                self.image_cache[gray_key] = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
            else:
                self.image_cache[gray_key] = template_bgr
        template = self.image_cache[gray_key]
        
        wait_start = time.perf_counter()
        while self.is_running:
            try:
                # Always grayscale — faster and cached
                screen_gray = self.get_cached_screenshot(region=region, as_gray=True)
                res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
                
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                
                if max_val >= confidence:
                    tw, th = template.shape[1], template.shape[0]
                    rx = max_loc[0] + (region[0] if region else 0)
                    ry = max_loc[1] + (region[1] if region else 0)
                    found_loc = (rx + tw//2, ry + th//2)
                    break
            except Exception as e:
                try: found_loc = pyautogui.locateCenterOnScreen(path, confidence=confidence, region=region)
                except Exception: pass
            
            if found_loc or mode != "wait": break
            # POT-1: Timeout check for wait mode
            if time.perf_counter() - wait_start > max_wait_time:
                self.log_message(f"[TIMEOUT] หมดเวลารอรูป ({max_wait_time}s)", "#f59e0b")
                break
            time.sleep(0.05)
            
        if found_loc:
            # 1. Fresh Window Context Sync (If following)
            if getattr(self, 'var_follow_window', None) and self.var_follow_window.get():
                fw = win32gui.GetForegroundWindow()
                if fw and fw != self.target_hwnd and win32gui.IsWindowVisible(fw):
                    try:
                        title = win32gui.GetWindowText(fw)
                        if title and title != self.original_title and "Franky" not in title:
                            self.target_hwnd = fw
                            self.target_title = title
                            self.safe_update_ui('lbl_target', text=f"เป้าหมาย (Auto): {self.target_title}")
                    except Exception: pass

            time.sleep(0.03) 
            
            dry = self.var_dry_run.get()
            prefix = "[DRY RUN] " if dry else ""
            self.log_message(f"{prefix}[FOUND] พบรูปที่: {found_loc} (Conf: {max_val:.2f})")
            self.show_found_marker(found_loc[0], found_loc[1])
            if dry: return
            if do_click:
                tx, ty = found_loc[0] + off_x, found_loc[1] + off_y
                cm = action.get("click_mode", "normal")
                btn = action.get("button", "left")
                if cm == "background": self.do_background_click(tx, ty, btn)
                else: self.perform_click(tx, ty, button=btn, mode=cm)
            
            if mode == "break": self.is_running = False
        else: self.log_message("[NOT FOUND] ไม่พบรูปภาพ")

    def _execute_color_search(self, action: Dict[str, Any]) -> None:
        tx, ty, rgb = action["x"], action["y"], action["rgb"]
        tol, mode = action.get("tolerance", 10), action.get("mode", "wait")
        do_click, region = action.get("do_click", True), action.get("region")
        max_wait_time = action.get("max_wait_time", 120)  # POT-2: Default 120s timeout
        self.log_message(f"[COLOR] ค้นหาสี {rgb} ({mode})")
        match_found, last_pos = False, (tx, ty)
        
        # Cast rgb to int16 to prevent uint8 underflow in subtraction
        rgb_arr = np.array(rgb, dtype=np.int16)
        
        def check():
            nonlocal last_pos
            try:
                img_np = self.get_cached_screenshot(region=region)
                if not region:
                    pixel = img_np[ty, tx].astype(np.int16)
                    return np.all(np.abs(pixel - rgb_arr) <= tol)
                else:
                    diff = np.abs(img_np.astype(np.int16) - rgb_arr)
                    matches = np.all(diff <= tol, axis=-1)
                    if np.any(matches):
                        y_idx, x_idx = np.where(matches)
                        last_pos = (x_idx[0] + region[0], y_idx[0] + region[1])
                        return True
            except Exception: pass
            return False
        
        wait_start = time.perf_counter()
        while self.is_running:
            if check():
                match_found = True
                break
            if mode != "wait": break
            # POT-2: Timeout check for wait mode
            if time.perf_counter() - wait_start > max_wait_time:
                self.log_message(f"[TIMEOUT] หมดเวลารอสี ({max_wait_time}s)", "#f59e0b")
                break
            time.sleep(0.05)
            
        if match_found:
            dry = self.var_dry_run.get()
            prefix = "[DRY RUN] " if dry else ""
            self.log_message(f"{prefix}[FOUND] พบสีที่: {last_pos}")
            self.show_found_marker(last_pos[0], last_pos[1])
            if dry: return
            if do_click:
                cm = action.get("click_mode", "normal")
                btn = action.get("button", "left")
                if cm == "background": self.do_background_click(last_pos[0], last_pos[1], btn)
                else: self.perform_click(last_pos[0], last_pos[1], button=btn, mode=cm)
            if mode == "break": self.is_running = False
        else: self.log_message("[NOT FOUND] ไม่พบสี")

    def _execute_multi_color_check(self, action: Dict[str, Any]) -> None:
        points, logic = action.get("points", []), action.get("logic", "AND")
        mode, do_click = action.get("mode", "once"), action.get("do_click", False)
        click_x, click_y = action.get("click_x", 0), action.get("click_y", 0)
        if not points: return
        self.log_message(f"[MULTI-COLOR] เช็คหลายสี: {len(points)} จุด (โหมด {logic})")
        
        def check_all_points():
            try:
                ss = self.get_cached_screenshot()
                results = []
                for pt in points:
                    px, py, pt_rgb, pt_tol = int(pt["x"]), int(pt["y"]), pt["rgb"], pt.get("tolerance", 10)
                    if 0 <= py < ss.shape[0] and 0 <= px < ss.shape[1]:
                        pixel_val = ss[py, px][:3].astype(np.int16)
                        rgb_val = np.array(pt_rgb, dtype=np.int16)
                        match = np.all(np.abs(pixel_val - rgb_val) <= pt_tol)
                        results.append(match)
                    else: results.append(False)
                return all(results) if logic == "AND" else any(results)
            except Exception: return False
        
        match_found = False
        while self.is_running:
            if check_all_points():
                match_found = True
                break
            if mode != "wait": break
            time.sleep(0.05)
        
        if match_found:
            dry = self.var_dry_run.get()
            prefix = "[DRY RUN] " if dry else ""
            self.log_message(f"{prefix}[PASS] เงื่อนไขสีตรง ({logic})")
            if dry: return
            if do_click and click_x and click_y:
                cm = action.get("click_mode", "normal")
                btn = action.get("button", "left")
                if cm == "background": self.do_background_click(click_x, click_y, btn)
                else: self.perform_click(click_x, click_y, button=btn, mode=cm)
        else: self.log_message(f"[FAIL] เงื่อนไขสีไม่ตรง ({logic})")

    def _bg_send_click(self, h, d, u, w, lp, is_nc=False, hit_test=0, lp_screen=0, is_right=False, button="left"):
        """Reusable method for sending background click messages to a window handle."""
        # Always send activation messages to ensure the target processes mouse input
        # (Some controls lose internal focus state between clicks)
        try:
            parent = win32gui.GetParent(h) or h
            # WM_MOUSEACTIVATE: Tell the control's parent we intend to click
            # (MA_ACTIVATE = 1, HTCLIENT = 1)
            win32gui.PostMessage(parent, win32con.WM_MOUSEACTIVATE, parent,
                                 win32api.MAKELONG(win32con.HTCLIENT, d))
            win32gui.PostMessage(h, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
            win32gui.PostMessage(h, win32con.WM_SETFOCUS, 0, 0)
            time.sleep(0.03)  # Let activation settle
        except Exception:
            pass
        
        if is_nc:
            # Non-Client Area Click (e.g. Title Bar, Close Button)
            self.log_message(f"[CLICK] ตรวจพบการคลิกปุ่มระบบ (NC Code: {hit_test})")
            
            # Warm up the button with a move message
            win32gui.PostMessage(h, win32con.WM_NCMOUSEMOVE, hit_test, lp_screen)
            time.sleep(0.05)

            if hit_test == 20: # HTCLOSE (The X button)
                 self.log_message("[CLICK] ส่งคำสั่งปิดหน้าต่าง (SC_CLOSE)")
                 win32gui.PostMessage(h, win32con.WM_SYSCOMMAND, 0xF060, 0) # SC_CLOSE
            else:
                nc_d = win32con.WM_NCRBUTTONDOWN if is_right else win32con.WM_NCLBUTTONDOWN
                nc_u = win32con.WM_NCRBUTTONUP if is_right else win32con.WM_NCLBUTTONUP
                win32gui.PostMessage(h, nc_d, hit_test, lp_screen)
                time.sleep(random.uniform(0.12, 0.18))
                win32gui.PostMessage(h, nc_u, hit_test, lp_screen)
            return

        # Check control class to avoid redundant messages
        try:
            cls_name = win32gui.GetClassName(h)
            is_btn = (cls_name.lower() == "button")
        except Exception:
            is_btn = False

        if is_btn and button == "left":
            # For standard Windows Buttons/Checkboxes, BM_CLICK is perfect
            win32gui.PostMessage(h, 0x00F5, 0, 0) # BM_CLICK
        else:
            # Full message sequence: SetCursor → MouseMove → (delay) → ButtonDown → (hold) → ButtonUp
            win32gui.PostMessage(h, win32con.WM_SETCURSOR, h, win32api.MAKELONG(win32con.HTCLIENT, d))
            win32gui.PostMessage(h, win32con.WM_MOUSEMOVE, 0, lp)
            time.sleep(0.03)  # Give app time to process hover state
            win32gui.PostMessage(h, d, w, lp)
            
            # Hold duration (slightly longer for reliability)
            time.sleep(random.uniform(0.08, 0.14)) 
            win32gui.PostMessage(h, u, 0, lp)

    def do_background_click(self, x: float, y: float, button: str = "left") -> None:
        """Refined background click: Finds specific child windows for better compatibility"""
        target_hwnd = getattr(self, 'target_hwnd', None)
        try:
            # Setup ctypes properly for ChildWindowFromPointEx (64-bit safe)
            _ChildWindowFromPointEx = ctypes.windll.user32.ChildWindowFromPointEx
            _ChildWindowFromPointEx.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.POINT, ctypes.c_uint]
            _ChildWindowFromPointEx.restype = ctypes.wintypes.HWND

            # 1. Identify the specific sub-window (control) at this screen coordinate
            used_child_lookup = False
            if target_hwnd and win32gui.IsWindow(target_hwnd):
                try:
                    # ChildWindowFromPointEx finds child directly within target — 
                    # accurate even when target is occluded by other windows
                    client_pt = win32gui.ScreenToClient(target_hwnd, (int(x), int(y)))
                    real_hwnd = _ChildWindowFromPointEx(
                        target_hwnd, ctypes.wintypes.POINT(client_pt[0], client_pt[1]), 0x0001
                    )
                    if not real_hwnd or real_hwnd == target_hwnd:
                        real_hwnd = target_hwnd
                    used_child_lookup = True
                except Exception:
                    real_hwnd = target_hwnd
                    used_child_lookup = True
            else:
                # Global mode: find whatever is at the screen point
                real_hwnd = win32gui.WindowFromPoint((int(x), int(y)))
            
            # Descendant safety check — only needed for Global mode (WindowFromPoint)
            # ChildWindowFromPointEx already guarantees the result is a child of target_hwnd
            if target_hwnd and not used_child_lookup:
                is_descendant = False
                curr = real_hwnd
                depth = 0
                while curr and depth < 50:
                    if curr == target_hwnd:
                        is_descendant = True
                        break
                    curr = win32gui.GetParent(curr)
                    depth += 1
                target = real_hwnd if is_descendant else target_hwnd
            else:
                target = real_hwnd
            
            # Store for subsequent typing actions
            self.last_child_hwnd = target
            
            # Debug: log the target handle and class for troubleshooting
            try:
                cls = win32gui.GetClassName(target)
                self.log_message(f"[BG] HWND:{target} Class:{cls} @ ({int(x)},{int(y)})", level=logging.DEBUG)
            except Exception: pass
            
            # 2. Coordinate conversion to the specific target HWND
            try:
                cx, cy = win32gui.ScreenToClient(target, (int(x), int(y)))
            except Exception:
                rect = win32gui.GetWindowRect(target)
                cx, cy = int(x) - rect[0], int(y) - rect[1]
                
            lParam = win32api.MAKELONG(cx, cy)
            
            # 3. Hit-Testing — only needed when clicking the parent window itself
            #    (child controls are always HTCLIENT, skip the blocking call)
            is_nc = False
            hit_test = win32con.HTCLIENT
            lParam_screen = win32api.MAKELONG(int(x), int(y))
            
            if target == target_hwnd or not target_hwnd:
                # Clicking the main window — check for title bar / system buttons
                SMTO_ABORTIFHUNG = 0x0002
                result = ctypes.wintypes.DWORD()
                ret = ctypes.windll.user32.SendMessageTimeoutW(
                    target, win32con.WM_NCHITTEST, 0, lParam_screen,
                    SMTO_ABORTIFHUNG, 100, ctypes.byref(result)
                )
                hit_test = result.value if ret else win32con.HTCLIENT
                is_nc = (hit_test != win32con.HTCLIENT and hit_test != 0)
            
            # 4. Execute Click
            is_right = (button == "right")
            btn_down = win32con.WM_RBUTTONDOWN if is_right else win32con.WM_LBUTTONDOWN
            btn_up = win32con.WM_RBUTTONUP if is_right else win32con.WM_LBUTTONUP
            wparam = win32con.MK_RBUTTON if is_right else win32con.MK_LBUTTON

            if button == "double":
                btn_dbl = win32con.WM_LBUTTONDBLCLK  # Double-click is always left-button
                
                self._bg_send_click(target, btn_down, btn_up, wparam, lParam,
                    is_nc=is_nc, hit_test=hit_test, lp_screen=lParam_screen,
                    is_right=is_right, button=button)
                time.sleep(0.04)
                
                # Re-send cursor context before DBLCLK
                win32gui.PostMessage(target, win32con.WM_SETCURSOR, target, win32api.MAKELONG(win32con.HTCLIENT, btn_down))
                win32gui.PostMessage(target, win32con.WM_MOUSEMOVE, 0, lParam)
                time.sleep(0.01)
                win32gui.PostMessage(target, btn_dbl, wparam, lParam)
                time.sleep(random.uniform(0.04, 0.07))
                win32gui.PostMessage(target, btn_up, 0, lParam)
            else:
                self._bg_send_click(target, btn_down, btn_up, wparam, lParam,
                    is_nc=is_nc, hit_test=hit_test, lp_screen=lParam_screen,
                    is_right=is_right, button=button)
                
        except Exception as e:
            self.log_message(f"[BG CLICK ERR] {e}", "red", level=logging.WARNING)


    def perform_click(self, x: float, y: float, button: str = "left", mode: str = "normal") -> None:
        """Centralized click method handling stealth, dry-run, and background modes"""
        # Dry Run Check
        if self.var_dry_run.get():
             self.show_click_marker(x, y)
             self.log_message(f"[DRY RUN] [CLICK] Click {button} at {x},{y} ({mode})")
             return

        # Background Mode
        if mode == "background":
            self.show_click_marker(x, y) # Also show marker in background mode for visual debugging
            self.do_background_click(x, y, button)
            return

        # Normal/Stealth Mode
        self.show_click_marker(x, y)
        
        # Stealth Movement
        if self.var_stealth_move.get():
            self._human_move(x, y)
        
        # --- Normal Mode Focus Recovery ---
        if mode == "normal" and self.target_hwnd and win32gui.IsWindow(self.target_hwnd):
            try:
                if win32gui.GetForegroundWindow() != self.target_hwnd:
                    win32api.keybd_event(18, 0, 0, 0)
                    win32gui.SetForegroundWindow(self.target_hwnd)
                    win32api.keybd_event(18, 0, 2, 0)
                    time.sleep(0.08) # Focus stabilization
            except Exception: pass
        
        if self.var_stealth_sendinput.get():
             if mode != "background": # Explicitly ensure we don't mix up
                 send_input_click(x, y, button)
        else:
            if self.var_stealth_move.get():
                 # For stealth move, we utilize human_move then click
                 # pyautogui.mouseDown/Up only accepts "left"/"right"/"middle"
                 actual_btn = "left" if button == "double" else button
                 pyautogui.mouseDown(button=actual_btn)
                 time.sleep(random.uniform(0.05, 0.15))
                 pyautogui.mouseUp(button=actual_btn)
                 if button == "double":
                     time.sleep(0.06)
                     pyautogui.mouseDown(button="left")
                     time.sleep(random.uniform(0.05, 0.15))
                     pyautogui.mouseUp(button="left")
            else:
                if button == "double":
                     pyautogui.doubleClick(x, y)
                else:
                     pyautogui.click(x, y, button=button)


    def get_cached_screenshot(self, region: Optional[tuple] = None, as_gray: bool = False) -> np.ndarray:
        current_time = time.perf_counter()
        cache_valid = (self.screenshot_cache is not None and 
                       current_time - self.screenshot_cache_time < self.screenshot_cache_ttl)
        
        if not cache_valid:
            # Always capture full-screen and cache it (slicing is cheaper than separate grabs)
            if not self.sct:
                try: self.sct = mss.mss()
                except Exception: self.sct = None
            try:
                sct_img = self.sct.grab(self.sct.monitors[0])
                # PERF-3: Store as RGB for color operations
                raw = np.array(sct_img)
                self.screenshot_cache = raw[:, :, :3][:, :, ::-1]  # BGRA -> BGR -> RGB (no copy, just view)
                # Also prepare grayscale directly from BGRA for faster gray path
                self._screenshot_gray_cache_raw = cv2.cvtColor(raw, cv2.COLOR_BGRA2GRAY)
            except Exception:
                self.log_message("[WARN] mss failed, falling back to pyautogui (slower)", level=logging.WARNING)
                self.screenshot_cache = np.array(pyautogui.screenshot())
            self.screenshot_cache_time = current_time
            self._screenshot_gray_cache = None  # Invalidate grayscale cache
        
        ss = self.screenshot_cache
        
        # Grayscale conversion (cached — only computed once per frame)
        if as_gray:
            # PERF-3: Use pre-computed grayscale from BGRA if available
            gray = getattr(self, '_screenshot_gray_cache_raw', None)
            if gray is not None:
                ss = gray
            elif self._screenshot_gray_cache is None:
                self._screenshot_gray_cache = cv2.cvtColor(ss, cv2.COLOR_RGB2GRAY)
                ss = self._screenshot_gray_cache
            else:
                ss = self._screenshot_gray_cache
        
        # Region slicing (cheap numpy view, no copy)
        if region:
            rx, ry, rw, rh = region
            if ry+rh <= ss.shape[0] and rx+rw <= ss.shape[1]:
                return ss[ry:ry+rh, rx:rx+rw]
        return ss

    def _execute_logic_if(self, action: Dict[str, Any], current_index: int, run_actions: list = None) -> Optional[int]:
        condition = action.get("condition", "image_found")
        target_label = action.get("target_label")
        met = False
        
        self.log_message(f"[LOGIC] [IF] ตรวจสอบเงื่อนไข: {condition}")
        
        if condition == "image_found":
            path = action.get("path")
            region = action.get("region")
            if path:
                if path not in self.image_cache: self.image_cache[path] = cv2.imread(path)
                screen_gray = self.get_cached_screenshot(region=region, as_gray=True)
                gray_key = (path, "gray")
                if gray_key not in self.image_cache:
                    raw = self.image_cache[path]
                    self.image_cache[gray_key] = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY) if raw is not None and len(raw.shape) == 3 else raw
                template = self.image_cache[gray_key]
                res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                conf = action.get("confidence", 0.75) # Default 0.75 or from action
                met = (max_val >= conf)
        
        elif condition == "color_match":
            rgb = action.get("rgb")
            tx, ty = action.get("x", 0), action.get("y", 0)
            tol = action.get("tolerance", 10)
            if rgb:
                ss = self.get_cached_screenshot()
                if 0 <= ty < ss.shape[0] and 0 <= tx < ss.shape[1]:
                    pixel = ss[ty, tx].astype(np.int16)
                    rgb_arr = np.array(rgb, dtype=np.int16)
                    met = np.all(np.abs(pixel[:3] - rgb_arr) <= tol)

        elif condition == "var_compare":
            left = action.get("left")
            op = action.get("op", "==")
            right = action.get("right")
            met = self._evaluate_expression(left, op, right)
            self.log_message(f"[LOGIC] [IF] เปรียบเทียบ: {left} {op} {right} -> {'จริง' if met else 'เท็จ'}")

        jump_on = action.get("jump_on", "true") # true=Jump if Met, false=Jump if Not Met
        should_jump = False
        
        if jump_on == "true":
             if met: 
                 self.log_message(f"[PASS] เงื่อนไขเป็นจริง! กำลังกระโดดไปที่: {target_label}")
                 should_jump = True
             else:
                 self.log_message(f"[FAIL] เงื่อนไขไม่เป็นจริง ข้ามไปขั้นตอนถัดไป")
        else: # jump_on == "false" (Standard IF Block logic)
             if not met:
                 self.log_message(f"[FAIL] เงื่อนไขไม่เป็นจริง (Jump on False) -> ข้ามไปที่: {target_label}")
                 should_jump = True
             else:
                 self.log_message(f"[PASS] เงื่อนไขเป็นจริง (เข้าสู่ Block)")

        if should_jump:
            return self._find_label_index(target_label, run_actions)
        return None

    def _execute_logic_jump(self, action: Dict[str, Any], current_index: int, run_actions: list = None) -> Optional[int]:
        target_label = action.get("target_label")
        self.log_message(f"[JUMP] กระโดดไปที่: {target_label}")
        return self._find_label_index(target_label, run_actions)

    def _find_label_index(self, label_name: str, run_actions: list = None) -> Optional[int]:
        if not label_name: return None
        # Use cached lookup dict built at run start (O(1) instead of O(n))
        cache = getattr(self, '_label_index_cache', None)
        if cache and label_name in cache:
            return cache[label_name]
        # BUG-3: Fallback uses run_actions (snapshot) instead of self.actions (live)
        search_list = run_actions if run_actions is not None else self.actions
        for idx, act in enumerate(search_list):
            if act["type"] == "logic_label" and act.get("name") == label_name:
                return idx
        self.log_message(f"[ERROR] ไม่พบ Label ชื่อ '{label_name}'", "red")
        return None

    def _execute_ocr_search(self, action: Dict[str, Any]) -> None:
        target_text = action.get("text", "").lower()
        mode = action.get("mode", "wait")
        region = action.get("region")
        do_click = action.get("do_click", True)
        
        if pytesseract is None:
            self.log_message("[ERROR] ข้อผิดพลาด: ไม่พบไลบรารี pytesseract กรุณาติดตั้ง 'pip install pytesseract'", "red")
            self.is_running = False
            return

        # Auto-detect Tesseract path (cached after first discovery)
        if not getattr(self, '_tesseract_path_set', False):
            local_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "bin", "tesseract", "tesseract.exe")
            if os.path.exists(local_path):
                pytesseract.pytesseract.tesseract_cmd = local_path
            elif os.name == 'nt':
                for p in [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                    os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Tesseract-OCR", "tesseract.exe")
                ]:
                    if os.path.exists(p):
                        pytesseract.pytesseract.tesseract_cmd = p
                        break
            self._tesseract_path_set = True

        self.log_message(f"[OCR] ค้นหาข้อความ: \"{target_text}\" ({mode})")
        # PERF-5: Warn if no region set (OCR on full screen is very slow)
        if not region:
            self.log_message("[WARN] OCR ค้นหาทั้งจอ แนะนำให้กำหนดพื้นที่ (Region) เพื่อความเร็วที่ดีขึ้น", "#f59e0b", level=logging.WARNING)
        
        found_loc = None
        while self.is_running:
            try:
                # Use cached grayscale screenshot (avoids redundant cv2.cvtColor)
                gray = self.get_cached_screenshot(region=region, as_gray=True)
                # Get data including positions
                data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT, lang='tha+eng')
                
                for i, text in enumerate(data['text']):
                    if target_text in text.lower():
                        # Found! Calculate coordinates relative to screen
                        tw, th = data['width'][i], data['height'][i]
                        rx = data['left'][i] + (region[0] if region else 0)
                        ry = data['top'][i] + (region[1] if region else 0)
                        found_loc = (rx + tw//2, ry + th//2)
                        break
            except Exception as e:
                self.log_message(f"[WARN] OCR Error: {e}", level=logging.DEBUG)
            
            if found_loc or mode != "wait": break
            time.sleep(1.0)  # PERF-5: Increased from 0.5s — OCR is expensive

        if found_loc:
            dry = self.var_dry_run.get()
            prefix = "[DRY RUN] " if dry else ""
            self.log_message(f"{prefix}[FOUND] พบข้อความที่: {found_loc}")
            self.show_found_marker(found_loc[0], found_loc[1])
            if dry: return
            if do_click:
                cm = action.get("click_mode", "normal")
                btn = action.get("button", "left")
                if cm == "background": self.do_background_click(found_loc[0], found_loc[1], btn)
                else: self.perform_click(found_loc[0], found_loc[1], button=btn, mode=cm)
        else:
            self.log_message(f"[NOT FOUND] ไม่พบข้อความ: \"{target_text}\"")

    # --- Variable System Methods (Phase 3) ---

    def _execute_var_set(self, action: Dict[str, Any]) -> None:
        name = action.get("name")
        val = action.get("value")
        if not name: return

        with self.variable_lock:
            self.variables[name] = self._resolve_value(val)
        
        self.log_message(f"[VAR] ตั้งค่า {name} = {self.variables[name]}")

    def _execute_var_math(self, action: Dict[str, Any]) -> None:
        name = action.get("name")
        op = action.get("op", "add") # add, sub, mul, div
        val = action.get("value", 1)
        
        if not name: return
        
        with self.variable_lock:
            current = self.variables.get(name, 0)
            try:
                current = float(current)
                change = float(self._resolve_value(val))
                
                if op == "add": current += change
                elif op == "sub": current -= change
                elif op == "mul": current *= change
                elif op == "div": current = current / change if change != 0 else 0
                
                # Format as int if possible
                if current.is_integer(): current = int(current)
                self.variables[name] = current
                self.log_message(f"[VAR] {name} {op} {change} -> {current}")
            except Exception as e:
                self.log_message(f"[ERROR] Math Error ({name}): {e}", "red")

    def _resolve_value(self, val: Any) -> Any:
        """If val is a string starting with $, treat it as a variable name"""
        if isinstance(val, str) and val.startswith("$"):
            var_name = val[1:]
            return self.variables.get(var_name, 0)
        return val

    def _evaluate_expression(self, left: Any, op: str, right: Any) -> bool:
        """Evaluates a comparison between two values"""
        l_val = self._resolve_value(left)
        r_val = self._resolve_value(right)
        
        try:
            # Try numeric comparison first
            fl = float(l_val)
            fr = float(r_val)
            if op == "==": return fl == fr
            if op == "!=": return fl != fr
            if op == ">": return fl > fr
            if op == "<": return fl < fr
            if op == ">=": return fl >= fr
            if op == "<=": return fl <= fr
        except (ValueError, TypeError):
            # Fallback to string comparison
            sl, sr = str(l_val), str(r_val)
            if op == "==": return sl == sr
            if op == "!=": return sl != sr
            return False
        return False
