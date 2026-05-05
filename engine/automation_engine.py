import time
import sys
import threading
import random
import math
import logging
import os
import ctypes
import numpy as np
import cv2
import mss
import pyautogui
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

    def run_automation(self):
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

    def stop_automation(self):
        self.is_running = False
        self.is_paused = False
        self.next_step.set() # Release if waiting
        self.stealth_on_run_stop() # Restore window
        self.hide_running_overlay() # Hide overlay
        self.safe_update_ui('lbl_status', text="[STOP] กำลังสั่งหยุดทำงาน...", text_color="#e67e22")

    def bg_runner(self, loops):
        count = 0
        self.log_message("=== เริ่มทำงานอัตโนมัติ ===")
        self.perf_metrics["start_time"] = time.perf_counter()
        self.perf_metrics["actions_exec"] = []
        
        # Precompute labels for O(1) jump lookups
        self._label_map = {}
        for idx, act in enumerate(self.actions):
            if act["type"] == "logic_label" and act.get("name"):
                self._label_map[act["name"]] = idx
                
        while self.is_running:
            if loops > 0 and count >= loops: break
            count += 1
            loop_msg = f"รอบที่ {count}" + (f" /{loops}" if loops > 0 else "")
            self.log_message(f"--- {loop_msg} ---")
            
            i = 0
            while i < len(self.actions):
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
                        except: pass

                # 2. Ensure context focus (If a target is locked/followed)
                if self.target_hwnd and win32gui.IsWindow(self.target_hwnd):
                    try:
                        if win32gui.GetForegroundWindow() != self.target_hwnd:
                            # Use Alt-key trick but with minimal delay during steps
                            win32api.keybd_event(18, 0, 0, 0)
                            win32gui.SetForegroundWindow(self.target_hwnd)
                            win32api.keybd_event(18, 0, 2, 0)
                            time.sleep(0.05) # Brief focus wait
                    except: pass
                # --- END STEP CONTEXT ---
                
                action = self.actions[i]
                
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
                        except: pass

                if not self.is_running: break
                self.highlight_action(i)
                
                try:
                    # Execute and handle jumping logic
                    jump_to = self.execute_one(action, i)
                    
                    if jump_to is not None:
                        i = jump_to
                        continue # Skip standard increment
                        
                except pyautogui.FailSafeException:
                     self.is_running = False
                     self.log_message("[FAILSAFE] หยุดระบบฉุกเฉิน: เมาส์ชนขอบจอ (Fail-safe)", "red")
                     self.safe_update_ui('lbl_status', text="[FAILSAFE] หยุดฉุกเฉิน: เมาส์ชนขอบจอ (FailSafe)", text_color="#e74c3c")
                     break
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

    def execute_one(self, action: Dict[str, Any], current_index: int) -> Optional[int]:
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
            elif t == "logic_if": jump_target = self._execute_logic_if(action, current_index)
            elif t == "logic_jump" or t == "logic_else": jump_target = self._execute_logic_jump(action, current_index)
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

    def _human_move(self, tx, ty):
        """Move mouse in a human-like curve using Bezier points"""
        start_x, start_y = pyautogui.position()
        dist = math.hypot(tx - start_x, ty - start_y)
        if dist < 20:
            pyautogui.moveTo(tx, ty, duration=random.uniform(0.05, 0.15))
            return

        cp1_x = start_x + (tx - start_x) * random.uniform(0.1, 0.4) + random.randint(-50, 50)
        cp1_y = start_y + (ty - start_y) * random.uniform(0.1, 0.4) + random.randint(-50, 50)
        cp2_x = start_x + (tx - start_x) * random.uniform(0.6, 0.9) + random.randint(-50, 50)
        cp2_y = start_y + (ty - start_y) * random.uniform(0.6, 0.9) + random.randint(-50, 50)
        steps = int(max(10, dist / random.uniform(15, 25)))
        
        for i in range(steps + 1):
            t = i / steps
            x = (1-t)**3 * start_x + 3*(1-t)**2 * t * cp1_x + 3*(1-t) * t**2 * cp2_x + t**3 * tx
            y = (1-t)**3 * start_y + 3*(1-t)**2 * t * cp1_y + 3*(1-t) * t**2 * cp2_y + t**3 * ty
            pyautogui.moveTo(x, y)
            if i % 2 == 0:
                target_time = time.perf_counter() + random.uniform(0.001, 0.003)
                while time.perf_counter() < target_time:
                    pass

    def _get_abs_coords(self, x, y, relative=False):
        """Standardized conversion of relative/client coordinates to absolute screen coordinates"""
        if not relative: return int(x), int(y)
        if self.target_hwnd and win32gui.IsWindow(self.target_hwnd):
            try:
                rect = win32gui.GetWindowRect(self.target_hwnd)
                return int(x + rect[0]), int(y + rect[1])
            except: pass
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
                    except: pass
                return

        # Normal/Foreground Logic
        if self.target_hwnd and win32gui.IsWindow(self.target_hwnd):
            # Always try to focus before typing if possible
            try:
                if win32gui.GetForegroundWindow() != self.target_hwnd:
                    win32gui.SetForegroundWindow(self.target_hwnd)
                    time.sleep(0.2)
            except: pass
            
        # Execute typing using the most robust method available
        if self.var_stealth_sendinput.get():
            send_input_text(c, delay=0.01)
        else:
            try:
                # Primary method: Clipboard Paste (Fast & Reliable)
                try:
                    pyperclip.copy(c)
                except Exception:
                    time.sleep(0.1)
                    pyperclip.copy(c) # Retry once
                time.sleep(0.03)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.02)
            except Exception as e:
                self.log_message(f"[WARN] Clipboard Paste failed, falling back to SendInput: {e}", level=logging.DEBUG)
                # Fallback: SendInput character by character
                send_input_text(c, delay=0.01)
        time.sleep(0.03)

    def _execute_hotkey(self, action: Dict[str, Any]) -> None:
        key = action["content"]
        mode = action.get("mode", "normal")
        dry = self.var_dry_run.get()
        prefix = "[DRY RUN] " if dry else ""
        self.log_message(f"{prefix}[KEY] กดคีย์ลัด: {key} ({mode})")
        if dry: return

        # Background Hotkey Logic (Limited Support -> Optimized for common cases)
        if mode == "background":
            target = getattr(self, 'last_child_hwnd', self.target_hwnd)
            if not target: target = self.target_hwnd
            if target:
                keys_clean = key.lower().replace(" ", "")
                
                # Special Handler 1: CTRL+A (Select All)
                # Instead of simulating keys, we send the "Select All" message directly to the control
                if keys_clean in ["ctrl+a", "^a"]:
                    try:
                        # 1. Force Focus logic for background control
                        win32gui.PostMessage(target, win32con.WM_SETFOCUS, 0, 0)
                        time.sleep(0.02)

                        # 2. Try Standard EM_SETSEL (Works on standard Edits)
                        ctypes.windll.user32.SendMessageW(target, 0x00B1, 0, -1)
                        
                        # 3. REINFORCEMENT: Send Low-Level Input Sequence with Scan Codes
                        # scan_code (16-23 bit) | repeat (0-15)
                        # CTRL: Scan 0x1D -> 0x001D0001
                        # A:    Scan 0x1E -> 0x001E0001
                        
                        # Ctrl Down
                        win32gui.PostMessage(target, win32con.WM_KEYDOWN, 0x11, 0x001D0001) 
                        time.sleep(0.01)
                        # A Down
                        win32gui.PostMessage(target, win32con.WM_KEYDOWN, 0x41, 0x001E0001) 
                        time.sleep(0.01)
                        # Char (Ctrl+A = ASCII 1)
                        win32gui.PostMessage(target, win32con.WM_CHAR, 1, 0x001E0001)       
                        time.sleep(0.01)
                        # A Up (C0000000 mask for Previous Key State/Transition)
                        win32gui.PostMessage(target, win32con.WM_KEYUP, 0x41, 0xC01E0001)   
                        # Ctrl Up
                        win32gui.PostMessage(target, win32con.WM_KEYUP, 0x11, 0xC01D0001)   
                        return
                    except: pass

                # Special Handler 2: DELETE / BACKSPACE
                vk_map = {
                    'delete': 0x2E, 
                    'enter': 0x0D, 
                    'tab': 0x09, 
                    'backspace': 0x08,
                    'esc': 0x1B
                }
                
                vk = vk_map.get(keys_clean)
                if vk:
                    win32gui.PostMessage(target, win32con.WM_KEYDOWN, vk, 0)
                    time.sleep(0.05)
                    win32gui.PostMessage(target, win32con.WM_KEYUP, vk, 0)
                    return
                
                # General case (Attempt simple key presses)
                # Note: Complex combinations like Ctrl+Shift+X are largely irrelevant in BG mode for standard input
                # We focus on single keys or very specific combos handled above
                parts = key.lower().split('+')
                for k in parts:
                     vk = vk_map.get(k.strip())
                     if vk:
                         win32gui.PostMessage(target, win32con.WM_KEYDOWN, vk, 0)
                         time.sleep(0.02)
                         win32gui.PostMessage(target, win32con.WM_KEYUP, vk, 0)
            return

        # Normal Mode
        time.sleep(0.03)
        keys = [k.strip().lower() for k in key.split('+')]
        keys = ["ctrl" if k in ["control", "ctlr"] else k for k in keys]
        pyautogui.hotkey(*keys)
        time.sleep(0.03)

    def _execute_wait(self, action: Dict[str, Any]) -> None:
        secs = float(action["seconds"])
        if self.var_stealth_timing.get():
            variance = self.var_stealth_timing_val.get()
            factor = 1.0 + random.uniform(-variance, variance)
            secs *= factor
            self.log_message(f"[WAIT] รอ: {secs:.2f} วินาที (สุ่มจาก {action['seconds']}s)", level=logging.DEBUG)
        else:
            self.log_message(f"[WAIT] รอ: {secs:.2f} วินาที")
        time.sleep(secs)
        time.sleep(random.uniform(0.01, 0.05))

    def _execute_image_search(self, action: Dict[str, Any]) -> None:
        path, mode = action["path"], action.get("mode", "wait")
        do_click, off_x, off_y = action.get("do_click", True), action.get("off_x", 0), action.get("off_y", 0)
        region = action.get("region")
        confidence = action.get("confidence", 0.75) # Allow dynamic confidence, default slightly lower
        img_match_mode = action.get("img_match_mode", "grayscale")
        
        m_txt = "รอจนกว่าจะเจอ" if mode == "wait" else "เช็คครั้งเดียว"
        self.log_message(f"[FIND] ค้นหารูป: {os.path.basename(path)} ({m_txt}, {img_match_mode})")
        
        found_loc = None
        if path not in self.image_cache: self.image_cache[path] = cv2.imread(path)
            
        while self.is_running:
            try:
                screen = self.get_cached_screenshot(region=region)
                template = self.image_cache[path]
                
                if img_match_mode == "color":
                    # Color matching — convert both to BGR for comparison
                    screen_bgr = cv2.cvtColor(screen, cv2.COLOR_RGB2BGR)
                    if len(template.shape) == 2:
                        template = cv2.cvtColor(template, cv2.COLOR_GRAY2BGR)
                    res = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
                else:
                    # Grayscale matching (default, faster)
                    screen_gray = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)
                    if len(template.shape) == 3:
                        template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
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
            time.sleep(0.15)
            
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
                    except: pass

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
        self.log_message(f"[COLOR] ค้นหาสี {rgb} ({mode})")
        match_found, last_pos = False, (tx, ty)
        
        def check():
            nonlocal last_pos
            try:
                img_np = self.get_cached_screenshot(region=region)
                if not region:
                    pixel = img_np[ty, tx]
                    return np.all(np.abs(pixel - rgb) <= tol)
                else:
                    diff = np.abs(img_np - rgb)
                    matches = np.all(diff <= tol, axis=-1)
                    if np.any(matches):
                        y_idx, x_idx = np.where(matches)
                        last_pos = (x_idx[0] + region[0], y_idx[0] + region[1])
                        return True
            except: pass
            return False
            
        while self.is_running:
            if check():
                match_found = True
                break
            if mode != "wait": break
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
                    px, py, rgb, tol = int(pt["x"]), int(pt["y"]), pt["rgb"], pt.get("tolerance", 10)
                    if 0 <= py < ss.shape[0] and 0 <= px < ss.shape[1]:
                        match = np.all(np.abs(ss[py, px][:3] - rgb) <= tol)
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

    def do_background_click(self, x, y, button="left"):
        """Refined background click: Finds specific child windows for better compatibility"""
        # If no target Locked, try to find window at point
        target_hwnd = getattr(self, 'target_hwnd', None)
        try:
            # 1. Identify the specific sub-window (control) at this screen coordinate
            real_hwnd = win32gui.WindowFromPoint((int(x), int(y)))
            
            # Safety: Ensure the found window is the target or a descendant of it
            is_descendant = False
            curr = real_hwnd
            if target_hwnd:
                while curr:
                    if curr == target_hwnd:
                        is_descendant = True
                        break
                    curr = win32gui.GetParent(curr)
            
            # If target_hwnd set, only allow clicking it or its children.
            # If target_hwnd is None (Global), allow clicking any window found at point.
            target = real_hwnd if (is_descendant or not target_hwnd) else target_hwnd
            
            # Store for subsequent typing actions
            self.last_child_hwnd = target
            
            # 2. Coordinate conversion to the specific target HWND
            try:
                cx, cy = win32gui.ScreenToClient(target, (int(x), int(y)))
            except:
                # Fallback to manual if ScreenToClient fails (rare)
                rect = win32gui.GetWindowRect(target)
                cx, cy = int(x) - rect[0], int(y) - rect[1]
                
            lParam = win32api.MAKELONG(cx, cy)
            
            # 3. Message Sequence for High Compatibility (Client Area Only)
            is_right = (button == "right")
            btn_down = win32con.WM_RBUTTONDOWN if is_right else win32con.WM_LBUTTONDOWN
            btn_up = win32con.WM_RBUTTONUP if is_right else win32con.WM_LBUTTONUP
            wparam = win32con.MK_RBUTTON if is_right else win32con.MK_LBUTTON
            
            def _send_single(h, d, u, w, lp):
                # Ensure the control is active/focused
                win32gui.PostMessage(h, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
                win32gui.PostMessage(h, win32con.WM_SETFOCUS, 0, 0)
                
                # Clean-up: Send an UP message first
                win32gui.PostMessage(h, u, 0, lp)
                time.sleep(0.02)
                
                win32gui.PostMessage(h, win32con.WM_SETCURSOR, h, win32api.MAKELONG(win32con.HTCLIENT, d))
                win32gui.PostMessage(h, win32con.WM_MOUSEMOVE, 0, lp)
                win32gui.PostMessage(h, d, w, lp)
                
                # High precision hold duration
                hold_time = random.uniform(0.08, 0.15)
                start_t = time.perf_counter()
                while time.perf_counter() - start_t < hold_time:
                    pass
                    
                win32gui.PostMessage(h, u, 0, lp)

            if button == "double":
                # Double Click Sequence: Down -> Up -> DblClk -> Up
                btn_dbl = win32con.WM_RBUTTONDBLCLK if is_right else win32con.WM_LBUTTONDBLCLK
                
                _send_single(target, btn_down, btn_up, wparam, lParam)
                time.sleep(0.04)
                
                # Second click MUST be the DBLCLK message for many apps to register it
                win32gui.PostMessage(target, btn_dbl, wparam, lParam)
                time.sleep(random.uniform(0.04, 0.07))
                win32gui.PostMessage(target, btn_up, 0, lParam)
            else:
                _send_single(target, btn_down, btn_up, wparam, lParam)
                
        except Exception as e:
            if self.var_debug_mode.get(): print(f"[BG CLICK ERR] {e}")
            pass

    def perform_click(self, x, y, button="left", mode="normal"):
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
            except: pass
        
        if self.var_stealth_sendinput.get():
             if mode != "background": # Explicitly ensure we don't mix up
                 send_input_click(x, y, button)
        else:
            if self.var_stealth_move.get():
                 # For stealth move, we utilize human_move then click
                 pyautogui.mouseDown(button=button)
                 time.sleep(random.uniform(0.05, 0.15))
                 pyautogui.mouseUp(button=button)
                 if button == "double":
                     time.sleep(0.06)
                     pyautogui.mouseDown(button=button)
                     time.sleep(random.uniform(0.05, 0.15))
                     pyautogui.mouseUp(button=button)
            else:
                if button == "double":
                     pyautogui.doubleClick(x, y)
                else:
                     pyautogui.click(x, y, button=button)


    def get_cached_screenshot(self, region=None):
        current_time = time.perf_counter()
        # 1. Check valid full-screen cache
        if self.screenshot_cache is not None and current_time - self.screenshot_cache_time < self.screenshot_cache_ttl:
            ss = self.screenshot_cache
            if region:
                rx, ry, rw, rh = region
                
                # Safety check for bounds
                if ry+rh <= ss.shape[0] and rx+rw <= ss.shape[1]:
                    return ss[ry:ry+rh, rx:rx+rw]
            return ss

        # 2. Capture new frame
        if not hasattr(self, 'sct'): self.sct = mss.mss()
        try:
            if region:
                rx, ry, rw, rh = region
                
                # mss requires dict for region
                monitor = {"top": int(ry), "left": int(rx), "width": int(rw), "height": int(rh)}
                sct_img = self.sct.grab(monitor)
                # Don't cache partials as full screen
                return cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2RGB)
            else:
                monitor = self.sct.monitors[1] if len(self.sct.monitors) > 1 else self.sct.monitors[0]
                sct_img = self.sct.grab(monitor)
                full_ss = cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2RGB)
                self.screenshot_cache = full_ss
                self.screenshot_cache_time = current_time
                return full_ss
        except Exception as e:
            # Fallback to pyautogui if mss fails
            full_ss = np.array(pyautogui.screenshot())
            self.screenshot_cache = full_ss
            self.screenshot_cache_time = current_time
            if region:
                 rx, ry, rw, rh = region
                 return full_ss[ry:ry+rh, rx:rx+rw]
            return full_ss

    def _execute_logic_if(self, action: Dict[str, Any], current_index: int) -> Optional[int]:
        condition = action.get("condition", "image_found")
        target_label = action.get("target_label")
        met = False
        
        self.log_message(f"[LOGIC] [IF] ตรวจสอบเงื่อนไข: {condition}")
        
        if condition == "image_found":
            path = action.get("path")
            region = action.get("region")
            if path:
                if path not in self.image_cache: self.image_cache[path] = cv2.imread(path)
                screen = self.get_cached_screenshot(region=region)
                screen_gray = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)
                template = self.image_cache[path]
                if len(template.shape) == 3: template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
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
                    pixel = ss[ty, tx]
                    met = np.all(np.abs(pixel[:3] - rgb) <= tol)

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
            return self._find_label_index(target_label)
        return None

    def _execute_logic_jump(self, action: Dict[str, Any], current_index: int) -> Optional[int]:
        target_label = action.get("target_label")
        self.log_message(f"[JUMP] กระโดดไปที่: {target_label}")
        return self._find_label_index(target_label)

    def _find_label_index(self, label_name: str) -> Optional[int]:
        if not label_name: return None
        if hasattr(self, '_label_map') and label_name in self._label_map:
            return self._label_map[label_name]
        for idx, act in enumerate(self.actions):
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

        # Auto-detect Tesseract path (Priority: Local Project -> Common Windows Paths)
        local_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "bin", "tesseract", "tesseract.exe")
        if os.path.exists(local_path):
            pytesseract.pytesseract.tesseract_cmd = local_path
        elif os.name == 'nt':
            common_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Tesseract-OCR", "tesseract.exe")
            ]
            for p in common_paths:
                if os.path.exists(p):
                    pytesseract.pytesseract.tesseract_cmd = p
                    break

        self.log_message(f"[OCR] ค้นหาข้อความ: \"{target_text}\" ({mode})")
        
        found_loc = None
        while self.is_running:
            try:
                # Capture and process
                img = self.get_cached_screenshot(region=region)
                # Tesseract works better with grayscale or high contrast
                gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
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
            time.sleep(0.5)

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
        
        # Support OCR as value if specified
        if action.get("from_ocr"):
            # This would be updated to capture last OCR result or rerun OCR
            pass 

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
        except:
            # Fallback to string comparison
            sl, sr = str(l_val), str(r_val)
            if op == "==": return sl == sr
            if op == "!=": return sl != sr
            return False
        return False
