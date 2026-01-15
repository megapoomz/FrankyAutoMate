import customtkinter as ctk
import pyautogui
import threading
import time
import json
import os
import win32gui
import win32con
import win32api # Added for background click
from tkinter import filedialog, messagebox
from pynput import mouse, keyboard
import cv2
import builtins
import numpy as np
import logging
import random
import math
import ctypes
from ctypes import wintypes
from typing import Optional, List, Dict, Tuple, Any, Union
import urllib.request
import webbrowser

# --- SendInput Low-Level Mouse Control ---
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

def send_input_click(x, y, button="left"):
    """Perform a mouse click using Win32 SendInput API"""
    # Convert to absolute coordinates (0-65535)
    screen_w = ctypes.windll.user32.GetSystemMetrics(0)
    screen_h = ctypes.windll.user32.GetSystemMetrics(1)
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

def send_input_move(x, y):
    """Move mouse using Win32 SendInput API"""
    screen_w = ctypes.windll.user32.GetSystemMetrics(0)
    screen_h = ctypes.windll.user32.GetSystemMetrics(1)
    abs_x = int(x * 65535 / screen_w)
    abs_y = int(y * 65535 / screen_h)
    
    move_input = INPUT(type=INPUT_MOUSE)
    move_input.mi.dx = abs_x
    move_input.mi.dy = abs_y
    move_input.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
    ctypes.windll.user32.SendInput(1, ctypes.byref(move_input), ctypes.sizeof(INPUT))


# --- Configuration & Setup ---
APP_VERSION = "1.5.0"
GITHUB_REPO = "megapoomz/FrankyAutoMate"  # Change to your actual repo
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

pyautogui.FAILSAFE = True

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("automate.log", encoding="utf-8"),
        logging.StreamHandler() # Also print to console
    ]
)
logger = logging.getLogger(__name__)

# --- Mixins for Modularization ---

class HotkeyMixin:
    """Handles global hotkeys, key recording, and key normalization"""
    def _key_to_string(self, key):
        if isinstance(key, str): return key.lower()
        try:
            if hasattr(key, 'char') and key.char:
                c = key.char
                if ord(c) < 32: return chr(ord(c) + 96)
                return c.lower()
            name = str(key).replace("Key.", "").lower()
            mapping = {
                "ctrl_l": "ctrl", "ctrl_r": "ctrl",
                "alt_l": "alt", "alt_r": "alt", "alt_gr": "alt",
                "shift_l": "shift", "shift_r": "shift",
                "cmd": "win", "cmd_l": "win", "cmd_r": "win",
                "caps_lock": "capslock",
                "page_up": "pgup", "page_down": "pgdn"
            }
            return mapping.get(name, name)
        except:
            return str(key).lower()

    def on_global_hotkey(self, key):
        key_str = self._key_to_string(key)
        if key_str not in self.held_keys:
            self.held_keys.add(key_str)

        if getattr(self, 'recording_state', None):
            if key_str not in self.recorded_keys:
                self.recorded_keys.add(key_str)
                modifiers_list = ["ctrl", "alt", "shift", "win"]
                modifiers = [k for k in self.recorded_keys if k in modifiers_list]
                others = [k for k in self.recorded_keys if k not in modifiers_list]
                all_keys = [k for k in (sorted(modifiers) + sorted(others)) if k]
                self.current_recorded_str = "+".join(all_keys)
                
                if self.recording_state == "main_hotkey":
                    self.after(0, lambda: self.lbl_hotkey.configure(text=f"[ {self.current_recorded_str.upper()} ]"))
                elif self.recording_state == "preset_hotkey":
                    self.after(0, lambda: self.lbl_preset_hotkey.configure(text=f"[ {self.current_recorded_str} ]"))
                elif self.recording_state == "action_hotkey":
                    self.after(0, lambda: self.entry_text.delete(0, "end"))
                    self.after(0, lambda: self.entry_text.insert(0, self.current_recorded_str))
                    self.after(0, lambda: self.var_input_mode.set("hotkey"))
            
            if hasattr(self, '_commit_timer'): self.after_cancel(self._commit_timer)
            self._commit_timer = self.after(800, self.commit_recorded_keys)
            return

        # Trigger logic
        modifiers_list = ["ctrl", "alt", "shift", "win"]
        current_modifiers = [k for k in self.held_keys if k in modifiers_list]
        current_others = [k for k in self.held_keys if k not in modifiers_list]
        current_full = "+".join(sorted(current_modifiers) + sorted(current_others))
        
        if current_full == self._key_to_string(self.toggle_key):
            self.after(0, self.run_automation)
            self.held_keys.clear()
            return

        if not self.is_running:
            for i, preset in enumerate(self.presets):
                preset_hotkey = str(preset.get("hotkey")).lower()
                if preset_hotkey == current_full or preset_hotkey == key_str:
                    self.after(0, lambda idx=i: self.run_preset(idx))
                    self.held_keys.clear()
                    return

    def on_global_release(self, key):
        key_str = self._key_to_string(key)
        if key_str in self.held_keys: self.held_keys.remove(key_str)

    def commit_recorded_keys(self):
        if not self.recording_state or not self.current_recorded_str:
            self.recording_state = None
            return
        final_str = self.current_recorded_str
        state = self.recording_state
        self.recording_state = None
        self.recorded_keys = set()
        self.current_recorded_str = ""
        
        if state == "main_hotkey":
            self.toggle_key = final_str
            self.lbl_status.configure(text=f"ตั้งค่า Hotkey หลักเป็น {final_str.upper()} แล้ว", text_color="#2ecc71")
        elif state == "preset_hotkey":
            if 0 <= self.waiting_for_preset_key < len(self.presets):
                self.presets[self.waiting_for_preset_key]["hotkey"] = final_str
            self.waiting_for_preset_key = None
            self.auto_save_presets()
            self.lbl_status.configure(text=f"ตั้งปุ่มลัดชุดนี้เป็น {final_str} แล้ว", text_color="#2ecc71")
        elif state == "action_hotkey":
            self.btn_record_key.configure(text="⌨️ Record Key", fg_color="#34495e")
            self.lbl_status.configure(text=f"บันทึกปุ่มลัด '{final_str}' เรียบร้อย", text_color="#2ecc71")

    def start_change_hotkey(self):
        self.recording_state = "main_hotkey"
        self.recorded_keys = set()
        self.lbl_hotkey.configure(text="[ กดปุ่ม... ]", text_color="#e74c3c")
        self.lbl_status.configure(text="กรุณากดปุ่มที่ต้องการตั้งเป็น Hotkey (เริ่ม/หยุด)...", text_color="#e67e22")
        self.focus()

    def start_recording_action_hotkey(self):
        self.recording_state = "action_hotkey"
        self.recorded_keys = set()
        self.btn_record_key.configure(text="🔴 Recording...", fg_color="#c0392b")
        self.lbl_status.configure(text="กดปุ่มลัดที่ต้องการบันทึก...", text_color="#e67e22")
        self.focus()

class PresetMixin:
    """Handles preset loading, saving, and switching"""
    def create_default_preset(self):
        self.presets = [{"name": "ชุดที่ 1", "hotkey": None, "actions": [], "loop_count": 1, "target_hwnd": None, "target_title": "ทั้งหน้าจอ (Global)"}]
        self.current_preset_index = 0

    def get_current_preset(self):
        if 0 <= self.current_preset_index < len(self.presets): return self.presets[self.current_preset_index]
        return None

    def save_current_to_preset(self):
        preset = self.get_current_preset()
        if preset:
            preset["actions"] = self.actions.copy()
            preset["target_hwnd"] = self.target_hwnd
            preset["target_title"] = self.target_title
            try: preset["loop_count"] = int(self.entry_loop.get())
            except: preset["loop_count"] = 1
            
            # Stealth Settings
            preset["stealth_move"] = self.var_stealth_move.get()
            preset["stealth_jitter"] = self.var_stealth_jitter.get()
            preset["stealth_jitter_radius"] = self.var_stealth_jitter_radius.get()
            preset["stealth_timing"] = self.var_stealth_timing.get()
            preset["stealth_timing_val"] = self.var_stealth_timing_val.get()

    def load_preset_to_ui(self, index):
        if 0 <= index < len(self.presets):
            # Clear old cache to save memory
            self.image_cache.clear()
            
            preset = self.presets[index]
            self.actions = preset.get("actions", []).copy()
            self.target_hwnd = preset.get("target_hwnd")
            self.target_title = preset.get("target_title", "ทั้งหน้าจอ (Global)")
            self.lbl_target.configure(text=f"เป้าหมาย: {self.target_title}")
            self.entry_loop.delete(0, "end")
            self.entry_loop.insert(0, str(preset.get("loop_count", 1)))
            
            # Restore Stealth Settings
            self.var_stealth_move.set(preset.get("stealth_move", False))
            self.var_stealth_jitter.set(preset.get("stealth_jitter", False))
            self.var_stealth_jitter_radius.set(preset.get("stealth_jitter_radius", 3.0))
            self.var_stealth_timing.set(preset.get("stealth_timing", False))
            self.var_stealth_timing_val.set(preset.get("stealth_timing_val", 0.2))
            
            self.update_list_display()

    def update_preset_ui(self):
        if not self.presets: return
        names = [p["name"] for p in self.presets]
        self.preset_dropdown.configure(values=names)
        preset = self.get_current_preset()
        if preset:
            self.preset_dropdown.set(preset["name"])
            self.entry_preset_name.delete(0, "end")
            self.entry_preset_name.insert(0, preset["name"])
            hotkey = preset.get("hotkey")
            self.lbl_preset_hotkey.configure(text=f"[ {hotkey} ]" if hotkey else "[ - ]")

    def save_presets_logic(self, filepath):
        save_data = []
        for preset in self.presets:
            p = preset.copy()
            p["target_hwnd"] = None
            save_data.append(p)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

    def load_presets_logic(self, filepath, is_startup=False):
        try:
            with open(filepath, "r", encoding="utf-8") as f: loaded = json.load(f)
            if loaded and isinstance(loaded, list):
                self.presets = loaded
                self.current_preset_index = 0
                self.load_preset_to_ui(0)
                self.update_preset_ui()
                self.preload_images()
                msg = f"โหลดแล้ว: {len(self.presets)} ชุด"
                self.lbl_status.configure(text=msg, text_color="#27ae60")
        except: pass

    def add_new_preset(self):
        self.save_current_to_preset()
        new_idx = len(self.presets) + 1
        new_p = {"name": f"ชุดที่ {new_idx}", "hotkey": None, "actions": [], "loop_count": 1, "target_hwnd": None, "target_title": "ทั้งหน้าจอ (Global)"}
        self.presets.append(new_p)
        self.current_preset_index = len(self.presets) - 1
        self.load_preset_to_ui(self.current_preset_index)
        self.update_preset_ui()
        self.auto_save_presets()
        self.lbl_status.configure(text=f"สร้างชุดใหม่: {new_p['name']}", text_color="#27ae60")

    def delete_current_preset(self):
        if len(self.presets) <= 1:
            messagebox.showwarning("แจ้งเตือน", "ต้องมีอย่างน้อย 1 ชุดคำสั่ง")
            return
        p = self.get_current_preset()
        if messagebox.askyesno("ยืนยันลบ", f"ลบชุด '{p['name']}' ?"):
            self.presets.pop(self.current_preset_index)
            self.current_preset_index = max(0, self.current_preset_index - 1)
            self.load_preset_to_ui(self.current_preset_index)
            self.update_preset_ui()
            self.auto_save_presets()
            self.lbl_status.configure(text="ลบชุดคำสั่งแล้ว", text_color="#e74c3c")

    def on_preset_changed(self, selected_name):
        self.save_current_to_preset()
        for i, p in enumerate(self.presets):
            if p["name"] == selected_name:
                self.current_preset_index = i
                self.load_preset_to_ui(i)
                self.update_preset_ui()
                break

    def on_preset_name_changed(self, event=None):
        p = self.get_current_preset()
        if p:
            new_name = self.entry_preset_name.get().strip()
            if new_name:
                p["name"] = new_name
                self.update_preset_ui()
                self.auto_save_presets()

    def start_change_preset_hotkey(self):
        self.recording_state = "preset_hotkey"
        self.waiting_for_preset_key = self.current_preset_index
        self.recorded_keys = set()
        self.lbl_preset_hotkey.configure(text="[ กดปุ่ม... ]", text_color="#e74c3c")
        self.lbl_status.configure(text="กรุณากดปุ่มที่ต้องการตั้งเป็นปุ่มลัดสำหรับชุดนี้...", text_color="#e67e22")
        self.focus()

    def save_presets_to_file(self):
        self.save_current_to_preset()
        try:
            path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("ไฟล์ JSON", "*.json")], initialfile="presets.json")
            if path:
                self.save_presets_logic(path)
                self.lbl_status.configure(text=f"บันทึกแล้ว: {os.path.basename(path)}", text_color="#27ae60")
        except: pass

    def auto_save_presets(self):
        self.save_current_to_preset()
        self.save_presets_logic(self.presets_file)

    def load_presets_from_file(self):
        try:
            path = filedialog.askopenfilename(filetypes=[("ไฟล์ JSON", "*.json")])
            if path: self.load_presets_logic(path)
        except: pass

    def run_preset(self, index):
        if self.is_running: return
        self.save_current_to_preset()
        self.current_preset_index = index
        self.load_preset_to_ui(index)
        self.update_preset_ui()
        p = self.get_current_preset()
        if p: self.log_message(f"เริ่มทำงานชุด: {p['name']}")
        self.run_automation()

    def load_presets_on_startup(self):
        if os.path.exists(self.presets_file):
            self.load_presets_logic(self.presets_file, is_startup=True)

class EngineMixin:
    """Handles automation execution, background runner, and single action logic"""
    def run_automation(self):
        if self.is_running:
            if getattr(self, 'is_paused', False):
                self.is_paused = False
                self.btn_run.configure(text="🛑 หยุด (STOP)", fg_color="#c0392b")
                self.next_step.set()
                return
            else:
                self.is_paused = True
                self.btn_run.configure(text="▶️ ดำเนินการต่อ (RESUME)", fg_color="#2ecc71")
                self.lbl_status.configure(text="⏸️ หยุดชั่วคราว", text_color="#f1c40f")
                return
        self.save_current_to_preset()
        self.auto_save_presets()
        try: loops = int(self.entry_loop.get())
        except: loops = 1
        self.is_running = True
        self.btn_run.configure(text="หยุด (STOP)", fg_color="#c0392b")
        self.stealth_on_run_start() # Apply stealth settings
        self.execution_thread = threading.Thread(target=self.bg_runner, args=(loops,))
        self.execution_thread.daemon = True
        self.execution_thread.start()

    def stop_automation(self):
        self.is_running = False
        self.is_paused = False
        self.next_step.set() # Release if waiting
        self.stealth_on_run_stop() # Restore window
        self.lbl_status.configure(text="🛑 กำลังสั่งหยุดทำงาน...", text_color="#e67e22")

    def bg_runner(self, loops):
        count = 0
        self.log_message("=== เริ่มทำงานอัตโนมัติ ===")
        while self.is_running:
            if loops > 0 and count >= loops: break
            count += 1
            loop_msg = f"รอบที่ {count}" + (f" /{loops}" if loops > 0 else "")
            self.log_message(f"--- {loop_msg} ---")
            
            if self.target_hwnd and win32gui.IsWindow(self.target_hwnd):
                try: 
                    win32gui.SetForegroundWindow(self.target_hwnd)
                    win32gui.BringWindowToTop(self.target_hwnd)
                    time.sleep(0.3) 
                except: pass
            
            for i, action in enumerate(self.actions):
                if not self.is_running: break
                
                # Handling Paused State (General or Step Mode)
                if self.is_paused or self.var_step_mode.get():
                    if self.var_step_mode.get():
                        self.btn_run.configure(text="⏭️ ต่อไป (NEXT STEP)", fg_color="#3498db")
                        self.lbl_status.configure(text=f"⏸️ ขั้นตอน {i+1}: รอคำสั่ง...", text_color="#f1c40f")
                    
                    self.is_paused = True # Force pause if step mode
                    self.next_step.clear()
                    while self.is_paused and self.is_running:
                        if self.next_step.wait(0.1): break
                    
                    # Reset button after resume
                    self.btn_run.configure(text="🛑 หยุด (STOP)", fg_color="#c0392b")

                if not self.is_running: break
                self.highlight_action(i)
                try:
                    self.execute_one(action)
                except pyautogui.FailSafeException:
                     self.is_running = False
                     self.log_message("⚠️ หยุดระบบฉุกเฉิน: เมาส์ชนขอบจอ (Fail-safe)", "red")
                     self.lbl_status.configure(text="⚠️ หยุดฉุกเฉิน: เมาส์ชนขอบจอ (FailSafe)", text_color="#e74c3c")
                     break
                except Exception as e:
                    self.log_message(f"❌ เกิดข้อผิดพลาด: {e}", "red")
                    self.is_running = False
                    self.lbl_status.configure(text=f"❌ ข้อผิดพลาด: {e}", text_color="red")
                    break
                
                # Delay between steps
                if not self.var_step_mode.get():
                    time.sleep(0.1 + self.speed_delay)
        
        self.is_running = False
        self.highlight_action(-1)
        self.btn_run.configure(text="เริ่มทำงาน (START)", fg_color="#27ae60")
        self.lbl_status.configure(text="จบการทำงาน", text_color="#2ecc71")
        self.log_message("=== จบการทำงาน ===")

    def execute_one(self, action: Dict[str, Any]) -> None:
        start_time = time.perf_counter()
        t = action["type"]
        
        try:
            if t == "click": self._execute_click(action)
            elif t == "text": self._execute_text(action)
            elif t == "hotkey": self._execute_hotkey(action)
            elif t == "wait": self._execute_wait(action)
            elif t == "image_search": self._execute_image_search(action)
            elif t == "color_search": self._execute_color_search(action)
            elif t == "multi_color_check": self._execute_multi_color_check(action)
            
            elapsed = (time.perf_counter() - start_time) * 1000
            self.log_message(f"  ⏱️ ใช้เวลา: {elapsed:.0f}ms", "#7f8c8d")
            
            # Update status with speed info
            self.lbl_status.configure(text=f"รันคำสั่ง {t}: {elapsed:.0f}ms", text_color="#3498db")
                
        except Exception as e:
            self.log_message(f"❌ คำสั่ง {t} ล้มเหลว: {e}", "red")
            raise e

    def _human_move(self, tx, ty):
        """Move mouse in a human-like curve using Bezier points"""
        start_x, start_y = pyautogui.position()
        
        # If distance is small, just move directly with a bit of duration
        dist = math.hypot(tx - start_x, ty - start_y)
        if dist < 20:
            pyautogui.moveTo(tx, ty, duration=random.uniform(0.05, 0.15))
            return

        # Create control points for a cubic Bezier curve
        # We pick two random points 'between' start and end to create a curve
        cp1_x = start_x + (tx - start_x) * random.uniform(0.1, 0.4) + random.randint(-50, 50)
        cp1_y = start_y + (ty - start_y) * random.uniform(0.1, 0.4) + random.randint(-50, 50)
        
        cp2_x = start_x + (tx - start_x) * random.uniform(0.6, 0.9) + random.randint(-50, 50)
        cp2_y = start_y + (ty - start_y) * random.uniform(0.6, 0.9) + random.randint(-50, 50)
        
        # Steps based on distance
        steps = int(max(10, dist / random.uniform(15, 25)))
        
        for i in range(steps + 1):
            t = i / steps
            # Cubic Bezier formula: (1-t)^3*P0 + 3(1-t)^2*t*P1 + 3(1-t)*t^2*P2 + t^3*P3
            x = (1-t)**3 * start_x + 3*(1-t)**2 * t * cp1_x + 3*(1-t) * t**2 * cp2_x + t**3 * tx
            y = (1-t)**3 * start_y + 3*(1-t)**2 * t * cp1_y + 3*(1-t) * t**2 * cp2_y + t**3 * ty
            
            pyautogui.moveTo(x, y)
            if i % 2 == 0: # Small micro-delays to make it look less robotic
                time.sleep(random.uniform(0.001, 0.003))

    def _execute_click(self, action: Dict[str, Any]) -> None:
        fx, fy = action["x"], action["y"]
        mode = action.get("mode", "normal")
        button = action["button"]
        
        dry = self.var_dry_run.get()
        prefix = "[DRY RUN] " if dry else ""
        
        # 1. Apply Jitter if enabled
        target_x, target_y = fx, fy
        if self.var_stealth_jitter.get():
            r = self.var_stealth_jitter_radius.get()
            target_x += random.uniform(-r, r)
            target_y += random.uniform(-r, r)

        self.log_message(f"{prefix}🖱️ คลิก {button} ที่ {target_x:.1f},{target_y:.1f} ({mode})")
        
        if dry:
            self.show_found_marker(target_x, target_y, 20, 20)
            return

        if mode == "background":
            self.do_background_click(target_x, target_y, button)
        else:
            final_x, final_y = target_x, target_y
            if action.get("relative") and self.target_hwnd and win32gui.IsWindow(self.target_hwnd):
                rect = win32gui.GetWindowRect(self.target_hwnd)
                final_x += rect[0]
                final_y += rect[1]
            
            self.show_click_marker(final_x, final_y)
            
            # 2. Apply Human Movement if enabled
            if self.var_stealth_move.get():
                self._human_move(final_x, final_y)
                # Random hold duration
                if self.var_stealth_sendinput.get():
                    send_input_click(final_x, final_y, button)
                else:
                    pyautogui.mouseDown(button=button)
                    time.sleep(random.uniform(0.05, 0.15))
                    pyautogui.mouseUp(button=button)
            else:
                # Use SendInput or PyAutoGUI based on setting
                if self.var_stealth_sendinput.get():
                    send_input_click(final_x, final_y, button)
                else:
                    pyautogui.click(final_x, final_y, button=button)
            
        if action.get("stop_after", False):
            self.is_running = False

    def _execute_text(self, action: Dict[str, Any]) -> None:
        c = action["content"]
        dry = self.var_dry_run.get()
        prefix = "[DRY RUN] " if dry else ""
        self.log_message(f"{prefix}⌨️ พิมพ์: {c}")
        if dry: return
        time.sleep(0.1)
        pyautogui.write(c, interval=0.02)
        time.sleep(0.1)

    def _execute_hotkey(self, action: Dict[str, Any]) -> None:
        c = action["content"]
        dry = self.var_dry_run.get()
        prefix = "[DRY RUN] " if dry else ""
        self.log_message(f"{prefix}🎹 กดปุ่มลัด: {c}")
        if dry: return
        time.sleep(0.1)
        keys = [k.strip().lower() for k in c.split('+')]
        keys = ["ctrl" if k in ["control", "ctlr"] else k for k in keys]
        pyautogui.hotkey(*keys)
        time.sleep(0.1)

    def _execute_wait(self, action: Dict[str, Any]) -> None:
        secs = float(action["seconds"])
        
        # Apply Timing Jitter if enabled
        if self.var_stealth_timing.get():
            variance = self.var_stealth_timing_val.get()
            factor = 1.0 + random.uniform(-variance, variance)
            secs *= factor
            self.log_message(f"⌛ รอ: {secs:.2f} วินาที (สุ่มจาก {action['seconds']}s)", level=logging.DEBUG)
        else:
            self.log_message(f"⏳ รอ: {secs:.2f} วินาที")
            
        time.sleep(secs)
        # Small additional overhead jitter
        time.sleep(random.uniform(0.01, 0.05))

    def _execute_image_search(self, action: Dict[str, Any]) -> None:
        path, mode = action["path"], action.get("mode", "wait")
        do_click = action.get("do_click", True)
        off_x, off_y = action.get("off_x", 0), action.get("off_y", 0)
        region = action.get("region")
        
        m_txt = "รอจนกว่าจะเจอ" if mode == "wait" else "เช็คครั้งเดียว"
        self.log_message(f"🔍 ค้นหารูป: {os.path.basename(path)} ({m_txt})")
        
        found_loc = None
        if path not in self.image_cache:
            self.image_cache[path] = cv2.imread(path)
            
        while self.is_running:
            try:
                # Screen capture
                screen = np.array(pyautogui.screenshot(region=region))
                screen_gray = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)
                
                # Use cached template
                template = self.image_cache[path]
                # Ensure template is grayscale
                if len(template.shape) == 3:
                    template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                    self.image_cache[path] = template # Update cache with grayscale version
                
                res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                
                if max_val >= 0.8:
                    tw, th = template.shape[1], template.shape[0]
                    rx = max_loc[0] + (region[0] if region else 0)
                    ry = max_loc[1] + (region[1] if region else 0)
                    found_loc = (rx + tw//2, ry + th//2)
                    break
            except Exception as e:
                # Fallback to pyautogui if CV2 fails
                try: found_loc = pyautogui.locateCenterOnScreen(path, confidence=0.8, region=region)
                except: pass
            
            if found_loc or mode != "wait": break
            time.sleep(0.2)
            
        if found_loc:
            dry = self.var_dry_run.get()
            prefix = "[DRY RUN] " if dry else ""
            self.log_message(f"{prefix}✨ พบรูปที่: {found_loc}")
            self.show_found_marker(found_loc[0], found_loc[1])
            
            if dry: return

            if do_click:
                tx, ty = found_loc[0] + off_x, found_loc[1] + off_y
                cm = action.get("click_mode", "normal")
                if cm == "background":
                    self.do_background_click(tx, ty, "left")
                else:
                    self.perform_click(tx, ty, button="left", mode=cm)
            if mode == "break": self.is_running = False
        else:
            self.log_message("⚠️ ไม่พบรูปภาพ")

    def _execute_color_search(self, action: Dict[str, Any]) -> None:
        tx, ty, rgb = action["x"], action["y"], action["rgb"]
        tol = action.get("tolerance", 10)
        mode = action.get("mode", "wait")
        do_click = action.get("do_click", True)
        region = action.get("region")
        
        self.log_message(f"🎨 ค้นหาสี {rgb} ({mode})")
        match_found, last_pos = False, (tx, ty)
        
        def check():
            nonlocal last_pos
            try:
                # OPTIMIZATION: Take one screenshot and check
                ss = pyautogui.screenshot(region=region)
                img_np = np.array(ss)
                if not region: # Full screen - check target point
                    pixel = img_np[ty, tx]
                    diff = np.abs(pixel - rgb)
                    return np.all(diff <= tol)
                else: # Regional search
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
            time.sleep(0.25)
            
        if match_found:
            dry = self.var_dry_run.get()
            prefix = "[DRY RUN] " if dry else ""
            self.log_message(f"{prefix}✨ พบสีที่: {last_pos}")
            self.show_found_marker(last_pos[0], last_pos[1])
            
            if dry: return

            if do_click:
                cm = action.get("click_mode", "normal")
                if cm == "background":
                    self.do_background_click(last_pos[0], last_pos[1], "left")
                else:
                    self.perform_click(last_pos[0], last_pos[1], button="left", mode=cm)
            if mode == "break": self.is_running = False
        else:
            self.log_message("⚠️ ไม่พบสี")

    def _execute_multi_color_check(self, action: Dict[str, Any]) -> None:
        """Check multiple color points simultaneously with AND/OR logic"""
        points = action.get("points", [])  # List of {x, y, rgb, tolerance}
        logic = action.get("logic", "AND")  # "AND" or "OR"
        mode = action.get("mode", "once")  # "once" or "wait"
        do_click = action.get("do_click", False)
        click_x, click_y = action.get("click_x", 0), action.get("click_y", 0)
        
        if not points:
            self.log_message("⚠️ ไม่มีจุดสีที่ต้องเช็ค")
            return
            
        self.log_message(f"🎨 เช็คหลายสี: {len(points)} จุด (โหมด {logic})")
        
        def check_all_points():
            """Check all color points and return True/False based on logic"""
            try:
                ss = np.array(pyautogui.screenshot())
                results = []
                
                for pt in points:
                    px, py = int(pt["x"]), int(pt["y"])
                    rgb = pt["rgb"]
                    tol = pt.get("tolerance", 10)
                    
                    if 0 <= py < ss.shape[0] and 0 <= px < ss.shape[1]:
                        pixel = ss[py, px]
                        diff = np.abs(pixel[:3] - rgb)
                        match = np.all(diff <= tol)
                        results.append(match)
                    else:
                        results.append(False)
                
                if logic == "AND":
                    return all(results)
                else:  # OR
                    return any(results)
            except:
                return False
        
        match_found = False
        while self.is_running:
            if check_all_points():
                match_found = True
                break
            if mode != "wait":
                break
            time.sleep(0.2)
        
        if match_found:
            dry = self.var_dry_run.get()
            prefix = "[DRY RUN] " if dry else ""
            self.log_message(f"{prefix}✅ เงื่อนไขสีตรง ({logic})")
            
            if dry:
                return
            
            if do_click and click_x and click_y:
                cm = action.get("click_mode", "normal")
                if cm == "background":
                    self.do_background_click(click_x, click_y, "left")
                else:
                    self.perform_click(click_x, click_y, button="left", mode=cm)
        else:
            self.log_message(f"⚠️ เงื่อนไขสีไม่ตรง ({logic})")

    def do_background_click(self, x, y, button="left"):
        """
        Enhanced background click using AttachThreadInput for better compatibility.
        Level 3: Works with more programs including some DirectX games and modern UIs.
        """
        if not self.target_hwnd:
            return
        
        try:
            # Get thread IDs
            current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
            target_thread = ctypes.windll.user32.GetWindowThreadProcessId(self.target_hwnd, None)
            
            # Attach to target thread for better message delivery
            attached = False
            if current_thread != target_thread:
                attached = ctypes.windll.user32.AttachThreadInput(current_thread, target_thread, True)
            
            try:
                # Convert to client coordinates
                # Get window rect to calculate relative position
                rect = win32gui.GetWindowRect(self.target_hwnd)
                client_x = int(x) - rect[0]
                client_y = int(y) - rect[1]
                
                # Handle negative coordinates (use absolute if needed)
                if client_x < 0 or client_y < 0:
                    client_x, client_y = int(x), int(y)
                
                lParam = win32api.MAKELONG(client_x, client_y)
                
                # Set focus to target window (helps with some apps)
                ctypes.windll.user32.SetForegroundWindow(self.target_hwnd)
                time.sleep(0.01)
                
                # Button constants
                if button == "left":
                    btn_down = win32con.WM_LBUTTONDOWN
                    btn_up = win32con.WM_LBUTTONUP
                    wparam = win32con.MK_LBUTTON
                else:
                    btn_down = win32con.WM_RBUTTONDOWN
                    btn_up = win32con.WM_RBUTTONUP
                    wparam = win32con.MK_RBUTTON
                
                # Try SendMessage first (synchronous, more reliable)
                result = ctypes.windll.user32.SendMessageW(self.target_hwnd, btn_down, wparam, lParam)
                time.sleep(random.uniform(0.03, 0.08))
                ctypes.windll.user32.SendMessageW(self.target_hwnd, btn_up, 0, lParam)
                
                # Fallback to PostMessage if SendMessage failed
                if result == 0:
                    win32gui.PostMessage(self.target_hwnd, btn_down, wparam, lParam)
                    time.sleep(0.05)
                    win32gui.PostMessage(self.target_hwnd, btn_up, 0, lParam)
                
                if self.var_debug_mode.get():
                    self.log_message(f"🔧 BG Click: ({client_x},{client_y}) attached={attached}", level=logging.DEBUG)
                    
            finally:
                # Always detach thread
                if attached:
                    ctypes.windll.user32.AttachThreadInput(current_thread, target_thread, False)
                    
        except Exception as e:
            if self.var_debug_mode.get():
                self.log_message(f"🔧 Background click error: {e}", level=logging.DEBUG)
            # Fallback to simple PostMessage
            try:
                lParam = win32api.MAKELONG(int(x), int(y))
                btn_down = win32con.WM_LBUTTONDOWN if button == "left" else win32con.WM_RBUTTONDOWN
                btn_up = win32con.WM_LBUTTONUP if button == "left" else win32con.WM_RBUTTONUP
                win32gui.PostMessage(self.target_hwnd, btn_down, win32con.MK_LBUTTON if button == "left" else win32con.MK_RBUTTON, lParam)
                time.sleep(0.05)
                win32gui.PostMessage(self.target_hwnd, btn_up, 0, lParam)
            except:
                pass

    def get_cached_screenshot(self, region=None):
        """Get screenshot with caching for performance optimization"""
        current_time = time.perf_counter()
        
        # Check if cache is still valid (region=None only for now)
        if region is None and self.screenshot_cache is not None:
            if current_time - self.screenshot_cache_time < self.screenshot_cache_ttl:
                if self.var_debug_mode.get():
                    self.log_message("📸 Using cached screenshot", level=logging.DEBUG)
                return self.screenshot_cache
        
        # Take new screenshot
        ss = np.array(pyautogui.screenshot(region=region))
        
        # Cache only full screenshots
        if region is None:
            self.screenshot_cache = ss
            self.screenshot_cache_time = current_time
        
        return ss

class UIMixin:
    """Handles UI tab setups, list displays, and visual feedback"""
    def log_message(self, message: str, color: str = "white", level: int = logging.INFO):
        """Standardized logging to UI and File"""
        now = time.strftime("%H:%M:%S")
        
        # Log to file
        if level == logging.ERROR: logger.error(message)
        elif level == logging.WARNING: logger.warning(message)
        else: logger.info(message)
        
        # Log to UI
        def _log():
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", f"[{now}] {message}\n", color)
            self.txt_log.see("end")
            self.txt_log.configure(state="disabled")
        self.after(0, _log)

    def highlight_action(self, index):
        def _highlight():
            for i, frame in enumerate(self.action_widgets):
                if i == index: frame.configure(fg_color="#3e6643", border_color="#2ecc71")
                else:
                    is_sel = (i == getattr(self, 'selected_index', -1))
                    frame.configure(fg_color="#3498db" if is_sel else "#3d3d3d", border_color="#2980b9" if is_sel else "#2b2b2b")
        self.after(0, _highlight)

    def show_click_marker(self, x, y):
        if not getattr(self, 'show_marker', True): return
        def _show():
            m = ctk.CTkToplevel(self)
            m.overrideredirect(True)
            # Red ring for click
            m.attributes("-topmost", True, "-transparentcolor", "white", "-alpha", 0.7)
            c = ctk.CTkCanvas(m, width=30, height=30, bg="white", highlightthickness=0)
            c.pack()
            c.create_oval(2, 2, 28, 28, outline="red", width=3)
            c.create_oval(12, 12, 18, 18, fill="red")
            m.geometry(f"30x30+{int(x-15)}+{int(y-15)}")
            self.after(500, m.destroy)
        self.after(0, _show)

    def show_found_marker(self, x, y, w=40, h=40):
        """Green rectangle for found items"""
        if not getattr(self, 'show_marker', True): return
        def _show():
            m = ctk.CTkToplevel(self)
            m.overrideredirect(True)
            m.attributes("-topmost", True, "-transparentcolor", "white", "-alpha", 0.6)
            c = ctk.CTkCanvas(m, width=w, height=h, bg="white", highlightthickness=0)
            c.pack()
            # Green border
            c.create_rectangle(2, 2, w-2, h-2, outline="#2ecc71", width=3)
            m.geometry(f"{w}x{h}+{int(x-w/2)}+{int(y-h/2)}")
            self.after(600, m.destroy)
        self.after(0, _show)

class AutoMationApp(ctk.CTk, HotkeyMixin, PresetMixin, EngineMixin, UIMixin):
    def __init__(self):
        super().__init__()

        self.title("Franky AutoMate - โปรแกรมช่วยทำงานอัตโนมัติ")
        self.geometry("1100x850")
        self.minsize(1000, 700)
        
        # Data
        self.actions = []
        self.is_running = False
        self.execution_thread = None
        
        self.target_hwnd = None
        self.target_title = "ทั้งหน้าจอ (Global)"
        self.current_img_path = ""
        self.current_color_data = None # (x, y, (r, g, b))
        self.current_region = None # (x, y, w, h)
        self.image_cache = {} # path -> opencv image
        self.action_widgets = [] # List of frames for highlighting
        self.toggle_key = keyboard.Key.f6
        self.speed_delay = 0.0 # Additional delay between steps
        self.show_marker = True # Show red circle on click
        self.waiting_for_key = False
        self.waiting_for_preset_key = None
        self.is_paused = False
        self.next_step = threading.Event() # For step-by-step
        
        # Stealth / Anti-Detection settings
        self.var_stealth_move = ctk.BooleanVar(value=False)
        self.var_stealth_jitter = ctk.BooleanVar(value=False)
        self.var_stealth_jitter_radius = ctk.DoubleVar(value=3.0)
        self.var_stealth_timing = ctk.BooleanVar(value=False)
        self.var_stealth_timing_val = ctk.DoubleVar(value=0.2) # 20%
        self.var_stealth_hide_window = ctk.BooleanVar(value=False) # Hide when running
        self.var_stealth_random_title = ctk.BooleanVar(value=False) # Random window title
        self.var_stealth_sendinput = ctk.BooleanVar(value=False) # Use SendInput API
        self.original_title = "Franky AutoMate - โปรแกรมช่วยทำงานอัตโนมัติ"
        
        # Debug & Performance Settings
        self.var_debug_mode = ctk.BooleanVar(value=False)  # Verbose logging
        self.screenshot_cache = None  # Cached screenshot 
        self.screenshot_cache_time = 0  # Timestamp of cached screenshot
        self.screenshot_cache_ttl = 0.1  # Cache TTL in seconds (100ms)
        self.perf_metrics = {"actions": 0, "total_time": 0, "loop_times": []}
        
        # Presets Configuration
        self.presets = []  # List of preset dicts
        self.current_preset_index = 0
        self.presets_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets.json")
        
        # Recording State
        self.recording_state = None  # None, "main_hotkey", "preset_hotkey", "action_hotkey"
        self.recorded_keys = set()
        self.current_recorded_str = ""
        
        # Multi-color check points
        self.multi_color_points = []  # List of {x, y, rgb, tolerance}
        
        # Initialize with default preset
        self.create_default_preset()
        self.load_presets_on_startup()
        
        self.held_keys = set()
        self.key_listener = keyboard.Listener(on_press=self.on_global_hotkey, on_release=self.on_global_release)
        self.key_listener.start()
        
        # Async Preload Assets (Phase 2)
        threading.Thread(target=self.preload_images, daemon=True).start()
        
        # --- Main Layout ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(1, weight=1)

        # ================== BRAND HEADER ==================
        self.frame_top = ctk.CTkFrame(self, fg_color="transparent", height=80)
        self.frame_top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(15, 0))
        
        # Text centering container
        header_text = ctk.CTkFrame(self.frame_top, fg_color="transparent")
        header_text.pack(expand=True)

        # Merged Header Row
        header_content = ctk.CTkFrame(header_text, fg_color="transparent")
        header_content.pack(pady=10)
        
        lbl_title = ctk.CTkLabel(header_content, text="FRANKY AutoMate", font=("Impact", 32), text_color="#3498db")
        lbl_title.pack(side="left")
        
        lbl_sep = ctk.CTkLabel(header_content, text=" | ", font=("Segoe UI", 24), text_color="#555")
        lbl_sep.pack(side="left", padx=10)
        
        lbl_sub = ctk.CTkLabel(header_content, text="ระบบจัดการคำสั่งอัตโนมัติระดับมืออาชีพ [v1.6.0 Premium]", font=("Segoe UI", 13, "bold"), text_color="#95a5a6")
        lbl_sub.pack(side="left", pady=(5, 0))

        # ================== LEFT PANEL (Sequence List) ==================
        self.frame_left = ctk.CTkFrame(self, corner_radius=15, fg_color="#1e1e1e", border_width=1, border_color="#333333")
        self.frame_left.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
        self.frame_left.grid_rowconfigure(2, weight=1)  # Action list expands
        self.frame_left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.frame_left, text="รายการขั้นตอน (Script)", font=("Segoe UI", 20, "bold")).grid(row=0, column=0, pady=(15, 5), sticky="w", padx=20)
        
        # Target Info Header (Row 1)
        self.frame_target = ctk.CTkFrame(self.frame_left, fg_color="#3a3a3a", corner_radius=10)
        self.frame_target.grid(row=1, column=0, sticky="ew", padx=15, pady=5)
        
        self.lbl_target = ctk.CTkLabel(self.frame_target, text=f"เป้าหมาย: {self.target_title}", text_color="#ffd700", font=("Segoe UI", 14), wraplength=400, anchor="w")
        self.lbl_target.pack(side="left", padx=15, pady=10)
        
        self.btn_reset_target = ctk.CTkButton(self.frame_target, text="ยกเลิก", command=self.reset_target_window, width=80, fg_color="#7f8c8d", hover_color="#95a5a6")
        self.btn_reset_target.pack(side="right", padx=(5, 10), pady=10)
        
        self.btn_set_target = ctk.CTkButton(self.frame_target, text="เลือกหน้าต่างเป้าหมาย", command=self.pick_target_window, width=150, fg_color="#d35400", hover_color="#a04000")
        self.btn_set_target.pack(side="right", padx=(5, 0), pady=10)

        # Scrollable List (Row 2) - EXPANSIBLE
        self.scroll_actions = ctk.CTkScrollableFrame(self.frame_left, fg_color="transparent")
        self.scroll_actions.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        
        # List Controls Toolbar (Row 3)
        self.frame_list_controls = ctk.CTkFrame(self.frame_left, fg_color="transparent")
        self.frame_list_controls.grid(row=3, column=0, sticky="ew", padx=15, pady=15)
        
        ctk.CTkButton(self.frame_list_controls, text="ล้างทั้งหมด", fg_color="#c0392b", hover_color="#922b21", command=self.clear_actions, width=80).pack(side="left")
        ctk.CTkButton(self.frame_list_controls, text="ลบที่เลือก", fg_color="#e74c3c", hover_color="#c0392b", command=self.remove_selected_action, width=80).pack(side="left", padx=5)
        
        # Spacer
        ctk.CTkLabel(self.frame_list_controls, text="").pack(side="left", fill="x", expand=True)
        
        ctk.CTkButton(self.frame_list_controls, text="ขยับขึ้น", fg_color="#2980b9", hover_color="#2471a3", command=self.move_action_up, width=80).pack(side="left", padx=2)
        ctk.CTkButton(self.frame_list_controls, text="ขยับลง", fg_color="#2980b9", hover_color="#2471a3", command=self.move_action_down, width=80).pack(side="left", padx=2)


        # ================== RIGHT PANEL (Tools & Setup) ==================
        self.frame_right = ctk.CTkFrame(self, width=400, corner_radius=15, fg_color="#1e1e1e", border_width=1, border_color="#333333")
        self.frame_right.grid(row=1, column=1, sticky="nsew", padx=(0, 15), pady=15)
        self.frame_right.grid_propagate(False) # Keep fixed width
        self.frame_right.grid_rowconfigure(0, weight=1)
        self.frame_right.grid_columnconfigure(0, weight=1)

        # Use Scrollable Frame inside the right panel to handle vertical overflow
        self.scroll_right = ctk.CTkScrollableFrame(self.frame_right, fg_color="transparent", corner_radius=0)
        self.scroll_right.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.scroll_right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.scroll_right, text="เครื่องมือเพิ่มคำสั่ง", font=("Segoe UI", 18, "bold")).grid(row=0, column=0, pady=(10, 5), sticky="w", padx=20)

        # Tabs (Row 1)
        self.tab_actions = ctk.CTkTabview(self.scroll_right, corner_radius=10, fg_color="#333333", 
                                          segmented_button_fg_color="#1a1a1a", 
                                          segmented_button_selected_color="#2980b9", 
                                          height=450)
        self.tab_actions.grid(row=1, column=0, sticky="ew", padx=15, pady=5)
        
        self.tab_click = self.tab_actions.add("เมาส์")
        self.tab_type = self.tab_actions.add("พิมพ์")
        self.tab_image = self.tab_actions.add("รูป")
        self.tab_color = self.tab_actions.add("สี")
        self.tab_wait = self.tab_actions.add("รอ")
        self.tab_stealth = self.tab_actions.add("หลบ")
        self.tab_log = self.tab_actions.add("Log")

        self.setup_click_tab()
        self.setup_type_tab()
        self.setup_image_tab()
        self.setup_color_tab()
        self.setup_wait_tab()
        self.setup_stealth_tab()
        self.setup_log_tab()

        # PRESET MANAGEMENT PANEL (MOVED HERE - Row 2)
        self.frame_preset = ctk.CTkFrame(self.scroll_right, fg_color="#1f4f4f", corner_radius=12)
        self.frame_preset.grid(row=2, column=0, sticky="ew", padx=15, pady=10)
        
        # Row 1: Header + Save/Load buttons
        preset_header = ctk.CTkFrame(self.frame_preset, fg_color="transparent")
        preset_header.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(preset_header, text="จัดการชุดคำสั่ง (PRESETS)", font=("Segoe UI", 12, "bold"), text_color="#3498db").pack(side="left")
        ctk.CTkButton(preset_header, text="โหลดไฟล์", width=65, height=24, font=("Segoe UI", 10, "bold"), fg_color="#2980b9", command=self.load_presets_from_file).pack(side="right", padx=2)
        ctk.CTkButton(preset_header, text="บันทึกไฟล์", width=65, height=24, font=("Segoe UI", 10, "bold"), fg_color="#27ae60", command=self.save_presets_to_file).pack(side="right", padx=2)
        
        # Row 2: Preset selection + Add/Delete
        preset_select = ctk.CTkFrame(self.frame_preset, fg_color="transparent")
        preset_select.pack(fill="x", padx=10, pady=2)
        self.preset_dropdown = ctk.CTkComboBox(preset_select, values=["ชุดคำสั่งเริ่มต้น"], width=160, height=30, command=self.on_preset_changed, state="readonly", font=("Segoe UI", 12))
        self.preset_dropdown.pack(side="left")
        ctk.CTkButton(preset_select, text="สร้างใหม่", width=65, height=30, fg_color="#16a085", font=("Segoe UI", 10, "bold"), command=self.add_new_preset).pack(side="left", padx=5)
        ctk.CTkButton(preset_select, text="ลบทิ้ง", width=65, height=30, fg_color="#c0392b", font=("Segoe UI", 10, "bold"), command=self.delete_current_preset).pack(side="left", padx=2)

        # Row 3: Name & Hotkey
        preset_config = ctk.CTkFrame(self.frame_preset, fg_color="transparent")
        preset_config.pack(fill="x", padx=10, pady=(2, 8))
        self.entry_preset_name = ctk.CTkEntry(preset_config, height=28, placeholder_text="ตั้งชื่อชุดคำสั่ง...", font=("Segoe UI", 12))
        self.entry_preset_name.pack(side="left", fill="x", expand=True)
        self.entry_preset_name.bind("<FocusOut>", self.on_preset_name_changed)
        
        self.lbl_preset_hotkey = ctk.CTkLabel(preset_config, text="[ - ]", text_color="#f1c40f", font=("Segoe UI", 12, "bold"), width=40)
        self.lbl_preset_hotkey.pack(side="left", padx=5)
        ctk.CTkButton(preset_config, text="ตั้งปุ่มลัด", width=75, height=28, font=("Segoe UI", 10, "bold"), fg_color="#444", command=self.start_change_preset_hotkey).pack(side="left")

        # Run Section (Row 3)
        self.frame_run = ctk.CTkFrame(self.scroll_right, fg_color="#252525", corner_radius=12, border_width=1, border_color="#333")
        self.frame_run.grid(row=3, column=0, sticky="ew", padx=15, pady=(5, 20))
        
        # Hotkey & Loop
        config_line = ctk.CTkFrame(self.frame_run, fg_color="transparent")
        config_line.pack(fill="x", padx=15, pady=(10, 5))
        
        ctk.CTkLabel(config_line, text="ปุ่มลัด เริ่ม/หยุด:", font=("Segoe UI", 12, "bold")).pack(side="left")
        self.lbl_hotkey = ctk.CTkLabel(config_line, text="[ F6 ]", text_color="#f1c40f", font=("Segoe UI", 12, "bold"))
        self.lbl_hotkey.pack(side="left", padx=5)
        ctk.CTkButton(config_line, text="เปลี่ยนปุ่ม", command=self.start_change_hotkey, width=80, height=24, font=("Segoe UI", 10, "bold"), fg_color="#444").pack(side="right")
        
        loop_line = ctk.CTkFrame(self.frame_run, fg_color="transparent")
        loop_line.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkLabel(loop_line, text="จำนวนรอบการทำงาน:", font=("Segoe UI", 12, "bold")).pack(side="left")
        self.entry_loop = ctk.CTkEntry(loop_line, width=55, height=28, justify="center", font=("Segoe UI", 12))
        self.entry_loop.insert(0, "1")
        self.entry_loop.pack(side="left", padx=10)
        ctk.CTkLabel(loop_line, text="(0 = ทำวนไปเรื่อยๆ)", text_color="#7f8c8d", font=("Segoe UI", 11)).pack(side="left")

        # Speed Row
        speed_line = ctk.CTkFrame(self.frame_run, fg_color="transparent")
        speed_line.pack(fill="x", padx=15, pady=(0, 5))
        ctk.CTkLabel(speed_line, text="หน่วงเวลาเพิ่ม:", font=("Segoe UI", 11, "bold")).pack(side="left")
        self.slider_speed = ctk.CTkSlider(speed_line, from_=0.0, to=2.0, number_of_steps=20, width=150, command=self.on_speed_changed)
        self.slider_speed.set(0.0)
        self.slider_speed.pack(side="left", padx=5)
        self.lbl_speed_val = ctk.CTkLabel(speed_line, text="0.0s", font=("Segoe UI", 11, "bold"), text_color="#3498db", width=40)
        self.lbl_speed_val.pack(side="left")

        # Checkbox Row
        debug_row = ctk.CTkFrame(self.frame_run, fg_color="transparent")
        debug_row.pack(fill="x", padx=15, pady=(0, 10))
        self.var_dry_run = ctk.BooleanVar(value=False)
        self.cb_dry_run = ctk.CTkCheckBox(debug_row, text="ทดลองวิ่ง (Dry Run)", font=("Segoe UI", 10), variable=self.var_dry_run)
        self.cb_dry_run.pack(side="left")
        
        self.var_step_mode = ctk.BooleanVar(value=False)
        self.cb_step = ctk.CTkCheckBox(debug_row, text="ทีละขั้นตอน (Step)", font=("Segoe UI", 10), variable=self.var_step_mode)
        self.cb_step.pack(side="left", padx=10)
        
        self.cb_marker = ctk.CTkCheckBox(debug_row, text="แสดงจุดคลิก", font=("Segoe UI", 10), variable=ctk.BooleanVar(value=True), command=self.on_marker_toggle)
        self.cb_marker.pack(side="right")

        f_btns = ctk.CTkFrame(self.frame_run, fg_color="transparent")
        f_btns.pack(fill="x", padx=15, pady=(0, 15))
        
        self.btn_run = ctk.CTkButton(f_btns, text="▶ เริ่มทำงานอัตโนมัติ", command=self.run_automation, fg_color="#27ae60", hover_color="#1e8449", font=("Segoe UI", 15, "bold"), height=50)
        self.btn_run.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.btn_stop = ctk.CTkButton(f_btns, text="🛑 หยุด", command=self.stop_automation, fg_color="#c0392b", hover_color="#922b21", font=("Segoe UI", 15, "bold"), height=50, width=80)
        self.btn_stop.pack(side="left")

        # Footer / Status Bar Section
        self.frame_footer = ctk.CTkFrame(self, fg_color="transparent", height=30)
        self.frame_footer.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 10))
        self.frame_footer.grid_columnconfigure(0, weight=1)
        self.frame_footer.grid_columnconfigure(1, weight=1)
        self.frame_footer.grid_columnconfigure(2, weight=1)
        
        self.lbl_status = ctk.CTkLabel(self.frame_footer, text="สถานะ: พร้อมทำงาน", font=("Segoe UI", 12), text_color="#95a5a6")
        self.lbl_status.grid(row=0, column=0, sticky="w")
        
        self.lbl_brand = ctk.CTkLabel(self.frame_footer, text="Franky AutoMate - Professional", font=("Segoe UI", 12, "bold"), text_color="#3498db")
        self.lbl_brand.grid(row=0, column=1, sticky="n")
        
        f_footer_right = ctk.CTkFrame(self.frame_footer, fg_color="transparent")
        f_footer_right.grid(row=0, column=2, sticky="e")
        
        ctk.CTkButton(f_footer_right, text="📖 คู่มือการใช้งาน", width=100, height=24, font=("Segoe UI", 11, "bold"), fg_color="#34495e", hover_color="#2c3e50", command=self.show_user_manual).pack(side="left", padx=5)
        ctk.CTkButton(f_footer_right, text="🔄 อัปเดท", width=70, height=24, font=("Segoe UI", 10), fg_color="#27ae60", hover_color="#1e8449", command=self.check_for_updates).pack(side="left", padx=5)
        ctk.CTkLabel(f_footer_right, text=f"v{APP_VERSION} Premium", font=("Segoe UI", 11), text_color="#7f8c8d").pack(side="left", padx=5)
        
        # Load UI for first preset
        self.update_preset_ui()
        
        # Auto check for updates (silent)
        self.after(3000, lambda: self.check_for_updates(silent=True))
    
    # --- Preset Management ---
    
    
    
    
    
    
    
    
    
    


    

    
    



    
    def run_preset(self, preset_index):
        """Run a specific preset"""
        if self.is_running:
            return  # Already running
        
        # Save current, switch to preset, run
        self.save_current_to_preset()
        self.current_preset_index = preset_index
        self.load_preset_to_ui(preset_index)
        self.update_preset_ui()
        
        preset = self.get_current_preset()
        if preset:
            self.lbl_status.configure(text=f"เริ่มทำงานชุด: {preset['name']}", text_color="#27ae60")
        
        self.run_automation()
    
    def stop_automation(self):
        """Stop running automation"""
        self.is_running = False
        self.btn_run.configure(text="▶ เริ่มทำงาน (START)", fg_color="#27ae60")
        self.lbl_status.configure(text="หยุดแล้ว", text_color="#e74c3c")
    
    # --- Target Window Logic ---
    def pick_target_window(self):
        self.lbl_status.configure(text="โหมดเลือกหน้าต่าง: หน้าจอจะมืดลง คลิกที่หน้าต่างที่ต้องการ...", text_color="#d35400")
        self.withdraw()
        
        # Overlay for window picking
        self.pick_overlay = ctk.CTkToplevel(self)
        self.pick_overlay.attributes('-fullscreen', True)
        self.pick_overlay.attributes('-alpha', 0.3)
        self.pick_overlay.attributes('-topmost', True)
        self.pick_overlay.configure(fg_color="black", cursor="hand2")
        
        def on_window_click(event):
            # Capture coords
            x, y = event.x_root, event.y_root
            
            # Destroy first so WindowFromPoint sees what's under
            self.pick_overlay.destroy()
            self.deiconify()
            self.update() # Force update
            
            # Find window
            hwnd = win32gui.WindowFromPoint((x, y))
            
            # Find root parent
            root = hwnd
            while True:
                try:
                    parent = win32gui.GetParent(root)
                    if not parent: break
                    root = parent
                except: break
            
            self.target_hwnd = root
            title = win32gui.GetWindowText(root)
            self.target_title = title if title else f"ID: {root}"
            
            self.lbl_target.configure(text=f"เป้าหมาย: {self.target_title}")
            self.lbl_status.configure(text="ล็อคเป้าหมายเรียบร้อย (ไม่ได้คลิกจริง)", text_color="gray")

        def on_cancel_win(event):
            self.pick_overlay.destroy()
            self.deiconify()
            self.lbl_status.configure(text="ยกเลิกการเลือกหน้าต่าง", text_color="gray")

        self.pick_overlay.bind("<Button-1>", on_window_click)
        self.pick_overlay.bind("<Escape>", on_cancel_win)
        self.pick_overlay.focus_force()
    # --- Setup Tabs ---
    def setup_click_tab(self):
        t = self.tab_click
        
        # Row 1: Pick + Label
        f_pick = ctk.CTkFrame(t, fg_color="transparent")
        f_pick.pack(fill="x", padx=15, pady=(10, 5))
        self.btn_pick_coord = ctk.CTkButton(f_pick, text="📍 เลือกจุดบนจอ", command=self.start_pick_location, fg_color="#3498db", hover_color="#2980b9", width=120, height=32)
        self.btn_pick_coord.pack(side="left")
        self.lbl_picked_coord = ctk.CTkLabel(f_pick, text="พิกัด: -", text_color="#3498db", font=("Segoe UI", 12))
        self.lbl_picked_coord.pack(side="left", padx=15)
        
        # Row 2: Mode & Button selection grouped
        ctk.CTkLabel(t, text="ตั้งค่าเพิ่มเติม", font=("Segoe UI", 12, "bold")).pack(pady=(12, 2), anchor="w", padx=20)
        f_conf = ctk.CTkFrame(t, fg_color="#252525", corner_radius=10)
        f_conf.pack(fill="x", padx=15, pady=5)
        
        # Sub-row: Click Mode
        f_mode = ctk.CTkFrame(f_conf, fg_color="transparent")
        f_mode.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(f_mode, text="รูปแบบ:", width=60, anchor="w").pack(side="left")
        self.var_click_mode = ctk.StringVar(value="normal")
        ctk.CTkRadioButton(f_mode, text="ปกติ (Standard)", variable=self.var_click_mode, value="normal", font=("Segoe UI", 11)).pack(side="left", padx=5)
        ctk.CTkRadioButton(f_mode, text="เบื้องหลัง (Background)", variable=self.var_click_mode, value="background", font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        # Sub-row: Mouse Button
        f_btn = ctk.CTkFrame(f_conf, fg_color="transparent")
        f_btn.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(f_btn, text="ปุ่มที่ใช้:", width=60, anchor="w").pack(side="left")
        self.var_click_btn = ctk.StringVar(value="left")
        ctk.CTkRadioButton(f_btn, text="คลิกซ้าย", variable=self.var_click_btn, value="left", font=("Segoe UI", 11)).pack(side="left", padx=5)
        ctk.CTkRadioButton(f_btn, text="คลิกขวา", variable=self.var_click_btn, value="right", font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        # Stop Checkbox
        self.var_click_stop = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(t, text="หยุดทำงานทันทีหลังจากคลิกนี้", variable=self.var_click_stop, font=("Segoe UI", 11)).pack(pady=10, padx=20, anchor="w")
        
        # Add Button
        ctk.CTkButton(t, text="➕ เพิ่มคำสั่งคลิก", command=self.add_click_action, fg_color="#27ae60", hover_color="#1e8449", height=40, font=("Segoe UI", 14, "bold")).pack(pady=10, padx=20, fill="x")

    def setup_type_tab(self):
        t = self.tab_type
        
        ctk.CTkLabel(t, text="ตั้งค่าข้อความ/ปุ่ม", font=("Segoe UI", 12, "bold")).pack(pady=(15, 2), anchor="w", padx=20)
        f_input = ctk.CTkFrame(t, fg_color="#252525", corner_radius=10)
        f_input.pack(fill="x", padx=15, pady=5)
        
        self.entry_text = ctk.CTkEntry(f_input, placeholder_text="กรอกข้อความ หรือใช้ปุ่ม Record...", height=35)
        self.entry_text.pack(pady=10, fill="x", padx=10)
        
        f_row = ctk.CTkFrame(f_input, fg_color="transparent")
        f_row.pack(fill="x", padx=10, pady=(0, 10))
        
        self.btn_record_key = ctk.CTkButton(f_row, text="⌨️ บันทึกปุ่มกด", command=self.start_recording_action_hotkey, fg_color="#34495e", hover_color="#2c3e50", width=120, height=28)
        self.btn_record_key.pack(side="left")
        
        self.var_input_mode = ctk.StringVar(value="text")
        ctk.CTkRadioButton(f_row, text="ข้อความ", variable=self.var_input_mode, value="text", font=("Segoe UI", 11)).pack(side="right", padx=5)
        ctk.CTkRadioButton(f_row, text="ปุ่มลัด", variable=self.var_input_mode, value="hotkey", font=("Segoe UI", 11)).pack(side="right", padx=5)
        
        ctk.CTkButton(t, text="➕ เพิ่มคำสั่งพิมพ์", command=self.add_type_action, fg_color="#27ae60", hover_color="#1e8449", height=40, font=("Segoe UI", 14, "bold")).pack(pady=20, padx=20, fill="x")

    def setup_image_tab(self):
        t = self.tab_image
        
        # Row 1: Image Path Selector
        ctk.CTkLabel(t, text="ตั้งค่ารูปภาพ", font=("Segoe UI", 12, "bold")).pack(pady=(15, 2), anchor="w", padx=20)
        f_img = ctk.CTkFrame(t, fg_color="#252525", corner_radius=10)
        f_img.pack(fill="x", padx=15, pady=(0, 5))
        
        f_img_row = ctk.CTkFrame(f_img, fg_color="transparent")
        f_img_row.pack(fill="x", padx=10, pady=10)
        self.lbl_img_path = ctk.CTkLabel(f_img_row, text="ยังไม่ได้เลือกรูปภาพ", text_color="#7f8c8d", font=("Segoe UI", 11), anchor="w")
        self.lbl_img_path.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(f_img_row, text="📂 เลือกรูป", command=self.browse_image, width=80, height=28).pack(side="right")
        
        # Row 2: Region & Offset
        f_region_offset = ctk.CTkFrame(t, fg_color="transparent")
        f_region_offset.pack(fill="x", padx=15, pady=5)
        
        # Region (Left half)
        f_reg = ctk.CTkFrame(f_region_offset, fg_color="#252525", corner_radius=10)
        f_reg.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(f_reg, text="ขอบเขตการค้นหา", font=("Segoe UI", 11, "bold")).pack(pady=(5, 0))
        self.btn_pick_region = ctk.CTkButton(f_reg, text="🎯 ตีกรอบพื้นที่", command=self.start_pick_region, fg_color="#d35400", hover_color="#a04000", height=28, font=("Segoe UI", 11))
        self.btn_pick_region.pack(pady=5, padx=10, fill="x")
        self.lbl_region_info = ctk.CTkLabel(f_reg, text="พื้นที่: ทั้งหน้าจอ", text_color="#7f8c8d", font=("Segoe UI", 10))
        self.lbl_region_info.pack(pady=(0, 5))
        
        # Spacer
        ctk.CTkLabel(f_region_offset, text="", width=10).pack(side="left")

        # Offset (Right half)
        f_off = ctk.CTkFrame(f_region_offset, fg_color="#252525", corner_radius=10)
        f_off.pack(side="right", fill="both", expand=True)
        ctk.CTkLabel(f_off, text="จุดคลิก (0=กลางรูป)", font=("Segoe UI", 11, "bold")).pack(pady=(5, 0))
        f_off_row = ctk.CTkFrame(f_off, fg_color="transparent")
        f_off_row.pack(pady=5)
        self.entry_off_x = ctk.CTkEntry(f_off_row, width=45, height=24, placeholder_text="X")
        self.entry_off_x.insert(0, "0")
        self.entry_off_x.pack(side="left", padx=2)
        self.entry_off_y = ctk.CTkEntry(f_off_row, width=45, height=24, placeholder_text="Y")
        self.entry_off_y.insert(0, "0")
        self.entry_off_y.pack(side="left", padx=2)
        
        # Row 3: Mode & Action
        f_mode_action = ctk.CTkFrame(t, fg_color="#252525", corner_radius=10)
        f_mode_action.pack(fill="x", padx=15, pady=10)
        
        # Sub-row: Behavior Mode
        f_mode = ctk.CTkFrame(f_mode_action, fg_color="transparent")
        f_mode.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(f_mode, text="พฤติกรรม:", width=70, anchor="w", font=("Segoe UI", 11)).pack(side="left")
        self.var_img_mode = ctk.StringVar(value="wait")
        ctk.CTkRadioButton(f_mode, text="รอจนเจอ", variable=self.var_img_mode, value="wait", font=("Segoe UI", 10)).pack(side="left", padx=2)
        ctk.CTkRadioButton(f_mode, text="เช็คครั้งเดียว", variable=self.var_img_mode, value="once", font=("Segoe UI", 10)).pack(side="left", padx=2)
        ctk.CTkRadioButton(f_mode, text="เจอแล้วหยุด", variable=self.var_img_mode, value="break", font=("Segoe UI", 10)).pack(side="left", padx=2)
        
        # Sub-row: After-match Action
        f_action = ctk.CTkFrame(f_mode_action, fg_color="transparent")
        f_action.pack(fill="x", padx=10, pady=5)
        self.var_img_click = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(f_action, text="คลิกที่รูปเมื่อเจอ", variable=self.var_img_click, font=("Segoe UI", 11)).pack(side="left")
        
        self.var_img_click_mode = ctk.StringVar(value="normal")
        ctk.CTkRadioButton(f_action, text="ปกติ", variable=self.var_img_click_mode, value="normal", font=("Segoe UI", 10)).pack(side="right", padx=5)
        ctk.CTkRadioButton(f_action, text="เบื้องหลัง", variable=self.var_img_click_mode, value="background", font=("Segoe UI", 10)).pack(side="right", padx=5)
        ctk.CTkLabel(f_action, text="โหมดคลิก:", font=("Segoe UI", 10)).pack(side="right")
        
        ctk.CTkButton(t, text="➕ เพิ่มคำสั่งหารูป", command=self.add_image_action, fg_color="#27ae60", hover_color="#1e8449", height=40, font=("Segoe UI", 14, "bold")).pack(pady=10, padx=20, fill="x")

    def setup_color_tab(self):
        t = self.tab_color
        
        # Row 1: Pick + Preview
        ctk.CTkLabel(t, text="ตั้งค่าหาสี", font=("Segoe UI", 12, "bold")).pack(pady=(15, 2), anchor="w", padx=20)
        f_pick = ctk.CTkFrame(t, fg_color="#252525", corner_radius=10)
        f_pick.pack(fill="x", padx=15, pady=(0, 5))
        
        f_pick_row = ctk.CTkFrame(f_pick, fg_color="transparent")
        f_pick_row.pack(fill="x", padx=10, pady=10)
        self.btn_pick_color = ctk.CTkButton(f_pick_row, text="🎨 ดูดสีจากจอ", command=self.start_pick_color, fg_color="#e67e22", hover_color="#d35400", width=110, height=32)
        self.btn_pick_color.pack(side="left")
        
        self.canvas_color = ctk.CTkCanvas(f_pick_row, width=24, height=24, highlightthickness=1, highlightbackground="#555")
        self.canvas_color.pack(side="right", padx=5)
        self.lbl_color_info = ctk.CTkLabel(f_pick_row, text="ค่าสี RGB: -", font=("Segoe UI", 11), text_color="#7f8c8d")
        self.lbl_color_info.pack(side="right", padx=10)

        # Row 2: Region & Tolerance
        f_reg_tol = ctk.CTkFrame(t, fg_color="transparent")
        f_reg_tol.pack(fill="x", padx=15, pady=5)
        
        f_reg = ctk.CTkFrame(f_reg_tol, fg_color="#252525", corner_radius=10)
        f_reg.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(f_reg, text="ขอบเขตการค้นหา", font=("Segoe UI", 11, "bold")).pack(pady=(5, 0))
        self.btn_pick_color_region = ctk.CTkButton(f_reg, text="🎯 ตีกรอบพื้นที่", command=self.start_pick_region, fg_color="#d35400", height=28, font=("Segoe UI", 11))
        self.btn_pick_color_region.pack(pady=5, padx=10, fill="x")
        self.lbl_color_region_info = ctk.CTkLabel(f_reg, text="พื้นที่: จุดเดียว", text_color="#7f8c8d", font=("Segoe UI", 10))
        self.lbl_color_region_info.pack(pady=(0, 5))
        
        ctk.CTkLabel(f_reg_tol, text="", width=10).pack(side="left")
        
        f_tol = ctk.CTkFrame(f_reg_tol, fg_color="#252525", corner_radius=10)
        f_tol.pack(side="right", fill="both", expand=True)
        ctk.CTkLabel(f_tol, text="ความเพี้ยนสี", font=("Segoe UI", 11, "bold")).pack(pady=(5, 0))
        self.entry_tol = ctk.CTkEntry(f_tol, width=60, height=28, justify="center")
        self.entry_tol.insert(0, "10")
        self.entry_tol.pack(pady=10)

        # Row 3: Mode & Action
        f_mode_action = ctk.CTkFrame(t, fg_color="#252525", corner_radius=10)
        f_mode_action.pack(fill="x", padx=15, pady=10)
        
        f_mode = ctk.CTkFrame(f_mode_action, fg_color="transparent")
        f_mode.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(f_mode, text="พฤติกรรม:", width=70, anchor="w", font=("Segoe UI", 11)).pack(side="left")
        self.var_color_mode = ctk.StringVar(value="wait")
        ctk.CTkRadioButton(f_mode, text="รอจนเจอ", variable=self.var_color_mode, value="wait", font=("Segoe UI", 10)).pack(side="left", padx=2)
        ctk.CTkRadioButton(f_mode, text="เช็คครั้งเดียว", variable=self.var_color_mode, value="once", font=("Segoe UI", 10)).pack(side="left", padx=2)
        ctk.CTkRadioButton(f_mode, text="เจอแล้วหยุด", variable=self.var_color_mode, value="break", font=("Segoe UI", 10)).pack(side="left", padx=2)
        
        f_action = ctk.CTkFrame(f_mode_action, fg_color="transparent")
        f_action.pack(fill="x", padx=10, pady=5)
        self.var_color_click = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(f_action, text="คลิกที่สีเมื่อเจอ", variable=self.var_color_click, font=("Segoe UI", 11)).pack(side="left")
        
        self.var_color_click_mode = ctk.StringVar(value="normal")
        ctk.CTkRadioButton(f_action, text="ปกติ", variable=self.var_color_click_mode, value="normal", font=("Segoe UI", 10)).pack(side="right", padx=5)
        ctk.CTkRadioButton(f_action, text="เบื้องหลัง", variable=self.var_color_click_mode, value="background", font=("Segoe UI", 10)).pack(side="right", padx=5)
        
        ctk.CTkButton(t, text="➕ เพิ่มคำสั่งหาสี", command=self.add_color_action, fg_color="#27ae60", hover_color="#1e8449", height=40, font=("Segoe UI", 14, "bold")).pack(pady=10, padx=20, fill="x")
        
        # Multi-Color Check Section
        ctk.CTkLabel(t, text="เช็คหลายสีพร้อมกัน", font=("Segoe UI", 12, "bold")).pack(pady=(10, 2), anchor="w", padx=20)
        f_multi = ctk.CTkFrame(t, fg_color="#252525", corner_radius=10)
        f_multi.pack(fill="x", padx=15, pady=5)
        
        # Point list display
        self.lbl_multi_color_count = ctk.CTkLabel(f_multi, text="จุดที่เก็บ: 0 จุด", font=("Segoe UI", 11), text_color="#7f8c8d")
        self.lbl_multi_color_count.pack(pady=(10, 5))
        
        f_multi_btns = ctk.CTkFrame(f_multi, fg_color="transparent")
        f_multi_btns.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(f_multi_btns, text="➕ เพิ่มจุดปัจจุบัน", command=self.add_multi_color_point, fg_color="#3498db", height=28, width=100).pack(side="left", padx=2)
        ctk.CTkButton(f_multi_btns, text="🗑️ ล้างจุด", command=self.clear_multi_color_points, fg_color="#e74c3c", height=28, width=80).pack(side="left", padx=2)
        
        # Logic selection
        f_logic = ctk.CTkFrame(f_multi, fg_color="transparent")
        f_logic.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(f_logic, text="เงื่อนไข:", font=("Segoe UI", 10)).pack(side="left")
        self.var_multi_color_logic = ctk.StringVar(value="AND")
        ctk.CTkRadioButton(f_logic, text="ทุกจุดต้องตรง (AND)", variable=self.var_multi_color_logic, value="AND", font=("Segoe UI", 10)).pack(side="left", padx=5)
        ctk.CTkRadioButton(f_logic, text="จุดใดจุดหนึ่ง (OR)", variable=self.var_multi_color_logic, value="OR", font=("Segoe UI", 10)).pack(side="left", padx=5)
        
        ctk.CTkButton(t, text="➕ เพิ่มคำสั่งเช็คหลายสี", command=self.add_multi_color_action, fg_color="#9b59b6", hover_color="#8e44ad", height=36, font=("Segoe UI", 13, "bold")).pack(pady=10, padx=20, fill="x")

    def setup_log_tab(self):
        t = self.tab_log
        ctk.CTkLabel(t, text="บันทึกการทำงาน (Log)", font=("Segoe UI", 12, "bold")).pack(pady=(15, 2), anchor="w", padx=20)
        self.txt_log = ctk.CTkTextbox(t, height=350, font=("Consolas", 11), fg_color="#1a1a1a", border_width=1, border_color="#333")
        self.txt_log.pack(fill="both", expand=True, padx=10, pady=5)
        self.txt_log.configure(state="disabled")
        
        f_btn = ctk.CTkFrame(t, fg_color="transparent")
        f_btn.pack(pady=(0, 10))
        ctk.CTkButton(f_btn, text="🗑️ ล้างบันทึก", command=self.clear_logs, height=28, fg_color="#34495e", width=100).pack(side="left", padx=5)
        ctk.CTkButton(f_btn, text="💾 ส่งออก Log", command=self.export_logs, height=28, fg_color="#2980b9", width=100).pack(side="left", padx=5)
        ctk.CTkCheckBox(f_btn, text="🔧 Debug Mode", variable=self.var_debug_mode, font=("Segoe UI", 10), width=100).pack(side="left", padx=10)

    def log_message(self, message, color="white"):
        def _log():
            now = time.strftime("%H:%M:%S")
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", f"[{now}] {message}\n")
            self.txt_log.see("end")
            self.txt_log.configure(state="disabled")
        self.after(0, _log)

    def clear_logs(self):
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.configure(state="disabled")

    def export_logs(self):
        try:
            content = self.txt_log.get("1.0", "end-1c")
            if not content.strip():
                messagebox.showwarning("แจ้งเตือน", "ไม่มีข้อมูลบันทึกให้ส่งออกครับ")
                return
            path = filedialog.asksaveasfilename(defaultextension=".txt", 
                                                filetypes=[("Text Files", "*.txt")],
                                                initialfile=f"log_{time.strftime('%Y%m%d_%H%M%S')}.txt")
            if path:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.lbl_status.configure(text=f"✅ ส่งออก Log สำเร็จ: {os.path.basename(path)}", text_color="#2ecc71")
        except Exception as e:
            messagebox.showerror("Error", f"ไม่สามารถบันทึกไฟล์ได้: {e}")

    def setup_stealth_tab(self):
        t = self.tab_stealth
        ctk.CTkLabel(t, text="โหมดหลบการตรวจจับ (Anti-Bot)", font=("Segoe UI", 12, "bold")).pack(pady=(15, 2), anchor="w", padx=20)
        
        f_stealth = ctk.CTkFrame(t, fg_color="#252525", corner_radius=10)
        f_stealth.pack(fill="x", padx=15, pady=10)
        
        # Mouse Movement
        f_move = ctk.CTkFrame(f_stealth, fg_color="transparent")
        f_move.pack(fill="x", padx=10, pady=10)
        ctk.CTkCheckBox(f_move, text="ขยับเมาส์แบบคน (Human Curves)", variable=self.var_stealth_move, font=("Segoe UI", 11)).pack(side="left")
        
        # Click Jitter
        f_jitter = ctk.CTkFrame(f_stealth, fg_color="transparent")
        f_jitter.pack(fill="x", padx=10, pady=5)
        ctk.CTkCheckBox(f_jitter, text="สุ่มจุดคลิกรอบเป้าหมาย (Click Jitter)", variable=self.var_stealth_jitter, font=("Segoe UI", 11)).pack(side="left")
        
        f_j_val = ctk.CTkFrame(f_stealth, fg_color="transparent")
        f_j_val.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(f_j_val, text="รัศมีการสุ่ม (พิกเซล):", font=("Segoe UI", 10)).pack(side="left", padx=(20, 5))
        self.slider_jitter = ctk.CTkSlider(f_j_val, from_=1, to=20, number_of_steps=19, width=120, variable=self.var_stealth_jitter_radius)
        self.slider_jitter.pack(side="left")
        ctk.CTkLabel(f_j_val, textvariable=self.var_stealth_jitter_radius, font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)

        # Timing Jitter
        f_timing = ctk.CTkFrame(f_stealth, fg_color="transparent")
        f_timing.pack(fill="x", padx=10, pady=5)
        ctk.CTkCheckBox(f_timing, text="สุ่มเวลาหน่วง (Timing Variance)", variable=self.var_stealth_timing, font=("Segoe UI", 11)).pack(side="left")
        
        f_t_val = ctk.CTkFrame(f_stealth, fg_color="transparent")
        f_t_val.pack(fill="x", padx=10, pady=(0, 15))
        ctk.CTkLabel(f_t_val, text="เปอร์เซ็นต์การสุ่ม (0.1-0.5):", font=("Segoe UI", 10)).pack(side="left", padx=(20, 5))
        self.slider_timing = ctk.CTkSlider(f_t_val, from_=0.1, to=0.5, number_of_steps=4, width=120, variable=self.var_stealth_timing_val, command=self.on_stealth_timing_changed)
        self.slider_timing.pack(side="left")
        self.lbl_stealth_timing_val = ctk.CTkLabel(f_t_val, text=f"{int(self.var_stealth_timing_val.get()*100)}%", font=("Segoe UI", 10, "bold"))
        self.lbl_stealth_timing_val.pack(side="left", padx=5)

        warning_label = ctk.CTkLabel(t, text="⚠️ หมายเหตุ: โหมด Stealth อาจทำให้การทำงานช้าลง", text_color="#e67e22", font=("Segoe UI", 10, "italic"))
        warning_label.pack(pady=(5, 0))
        
        # Technical Anti-Detection Section
        ctk.CTkLabel(t, text="การซ่อนตัว (Technical)", font=("Segoe UI", 12, "bold")).pack(pady=(10, 2), anchor="w", padx=20)
        
        f_tech = ctk.CTkFrame(t, fg_color="#252525", corner_radius=10)
        f_tech.pack(fill="x", padx=15, pady=5)
        
        f_hide = ctk.CTkFrame(f_tech, fg_color="transparent")
        f_hide.pack(fill="x", padx=10, pady=8)
        ctk.CTkCheckBox(f_hide, text="ซ่อนหน้าต่างตอนรัน (Minimize on Run)", variable=self.var_stealth_hide_window, font=("Segoe UI", 11)).pack(side="left")
        
        f_title = ctk.CTkFrame(f_tech, fg_color="transparent")
        f_title.pack(fill="x", padx=10, pady=(0, 5))
        ctk.CTkCheckBox(f_title, text="สุ่มชื่อหน้าต่าง (Random Title)", variable=self.var_stealth_random_title, command=self.on_random_title_toggle, font=("Segoe UI", 11)).pack(side="left")
        
        f_sendinput = ctk.CTkFrame(f_tech, fg_color="transparent")
        f_sendinput.pack(fill="x", padx=10, pady=(0, 8))
        ctk.CTkCheckBox(f_sendinput, text="ใช้ SendInput API (หลบง่ายกว่า)", variable=self.var_stealth_sendinput, font=("Segoe UI", 11)).pack(side="left")

    def setup_wait_tab(self):
        t = self.tab_wait
        ctk.CTkLabel(t, text="ตั้งค่าการหน่วงเวลา", font=("Segoe UI", 12, "bold")).pack(pady=(15, 2), anchor="w", padx=20)
        f_wait = ctk.CTkFrame(t, fg_color="#252525", corner_radius=10)
        f_wait.pack(fill="x", padx=15, pady=20)
        
        ctk.CTkLabel(f_wait, text="หน่วงเวลา (วินาที)", font=("Segoe UI", 13, "bold")).pack(pady=(15, 5))
        self.entry_wait = ctk.CTkEntry(f_wait, width=150, height=40, font=("Segoe UI", 18), justify="center", placeholder_text="0.5")
        self.entry_wait.insert(0, "1.0")
        self.entry_wait.pack(pady=15)
        
        ctk.CTkButton(t, text="➕ เพิ่มคำสั่งรอ", command=self.add_wait_action, fg_color="#27ae60", hover_color="#1e8449", height=40, font=("Segoe UI", 14, "bold")).pack(pady=20, padx=20, fill="x")

    # --- Debugging Helpers ---
    def on_speed_changed(self, val):
        self.speed_delay = float(val)
        self.lbl_speed_val.configure(text=f"{self.speed_delay:.1f}s")
    
    def on_marker_toggle(self):
        self.show_marker = self.cb_marker.get()

    def on_stealth_timing_changed(self, val):
        self.lbl_stealth_timing_val.configure(text=f"{int(float(val)*100)}%")

    def on_random_title_toggle(self):
        if self.var_stealth_random_title.get():
            # Generate random title
            fake_apps = ["Microsoft Excel", "Notepad", "Calculator", "Windows Settings", "File Explorer", "Chrome", "Edge", "System32"]
            self.title(random.choice(fake_apps))
        else:
            self.title(self.original_title)

    def stealth_on_run_start(self):
        """Called when automation starts - applies stealth settings"""
        if self.var_stealth_hide_window.get():
            self.iconify()

    def stealth_on_run_stop(self):
        """Called when automation stops - restores window"""
        if self.var_stealth_hide_window.get():
            self.deiconify()
            self.lift()

    def show_click_marker(self, x, y):
        """Show a temporary visual marker at click location"""
        if not self.show_marker: return
        
        marker = ctk.CTkToplevel(self)
        marker.overrideredirect(True)
        marker.attributes("-topmost", True)
        marker.attributes("-transparentcolor", "black")
        marker.configure(fg_color="black")
        
        # Circle Size
        size = 30
        marker.geometry(f"{size}x{size}+{int(x - size/2)}+{int(y - size/2)}")
        
        canvas = ctk.CTkCanvas(marker, width=size, height=size, bg="black", highlightthickness=0)
        canvas.pack()
        canvas.create_oval(2, 2, size-2, size-2, outline="#e74c3c", width=3)
        canvas.create_oval(size/2-2, size/2-2, size/2+2, size/2+2, fill="#e74c3c")
        
        # Fade and Destroy
        def fade(alpha=1.0):
            if alpha <= 0:
                marker.destroy()
                return
            marker.attributes("-alpha", alpha)
            self.after(50, lambda: fade(alpha - 0.2))
        
        fade()

    # --- Actions Management ---
    def update_list_display(self):
        # Clear existing widgets
        for widget in self.scroll_actions.winfo_children():
            widget.destroy()
        
        self.action_widgets = []
            
        if not self.actions:
            lbl_empty = ctk.CTkLabel(self.scroll_actions, text="ยังไม่มีขั้นตอนในระบบ\n(เลือกเครื่องมือทางขวาเพื่อเพิ่มคำสั่งเข้า Script)", font=("Segoe UI", 12), text_color="#7f8c8d")
            lbl_empty.pack(pady=40)
            return

        # Re-draw all actions
        for i, action in enumerate(self.actions):
            self.create_action_widget(i, action)
    
    def highlight_action(self, index):
        """Highlight the currently executing action in the list"""
        def _highlight():
            for i, frame in enumerate(self.action_widgets):
                if i == index:
                    # Highlighting (Yellow-ish border or brighter BG)
                    frame.configure(fg_color="#3e6643", border_color="#2ecc71") 
                else:
                    is_selected = (i == getattr(self, 'selected_index', -1))
                    bg_color = "#3498db" if is_selected else "#3d3d3d"
                    border_color = "#2980b9" if is_selected else "#2b2b2b"
                    frame.configure(fg_color=bg_color, border_color=border_color)
        self.after(0, _highlight)

    def create_action_widget(self, index, action_data):
        is_selected = (index == getattr(self, 'selected_index', -1))
        bg_color = "#2c3e50" if is_selected else "#252525"
        border_color = "#3498db" if is_selected else "#333333"
        hover_color = "#34495e" if not is_selected else "#2c3e50"
        
        f = ctk.CTkFrame(self.scroll_actions, fg_color=bg_color, corner_radius=8, border_width=1, border_color=border_color)
        f.pack(fill="x", pady=2, padx=5)
        self.action_widgets.append(f)
        
        def on_click(event):
            self.selected_index = index
            self.update_list_display()
            
        f.bind("<Button-1>", on_click)
        
        # Icon/Index Column
        lbl_idx = ctk.CTkLabel(f, text=f"{index+1:02d}", width=40, font=("Segoe UI", 11, "bold"), text_color="#7f8c8d")
        lbl_idx.pack(side="left", padx=(10, 5))
        lbl_idx.bind("<Button-1>", on_click)
        
        # Action Icon (Emoji based on type)
        icons = {"click": "🖱️", "text": "⌨️", "hotkey": "🎹", "wait": "⏳", "image_search": "🖼️", "color_search": "🎨", "multi_color_check": "🎯"}
        lbl_icon = ctk.CTkLabel(f, text=icons.get(action_data["type"], "❓"), font=("Segoe UI", 14))
        lbl_icon.pack(side="left", padx=5)
        lbl_icon.bind("<Button-1>", on_click)

        # Description
        t = action_data["type"]
        desc = "?"
        if t == "click":
            mode = "เบื้องหลัง" if action_data.get("mode") == "background" else "ปกติ"
            btn = "ซ้าย" if action_data['button'] == "left" else "ขวา"
            desc = f"คลิก{btn} ที่ {action_data['x']},{action_data['y']} ({mode})"
        elif t == "text": desc = f"พิมพ์ข้อความ: \"{action_data['content']}\""
        elif t == "hotkey": desc = f"กดปุ่ม: {action_data['content'].upper()}"
        elif t == "wait": desc = f"รอ {action_data['seconds']} วินาที"
        elif t == "color_search":
            desc = f"หาสี: {action_data['rgb']}"
            desc += " [ตีกรอบ]" if action_data.get("region") else " [เฉพาะจุด]"
        elif t == "image_search":
            fname = os.path.basename(action_data['path'])
            desc = f"หารูป: {fname}"
            desc += " [ตีกรอบ]" if action_data.get("region") else " [ทั้งจอ]"
        elif t == "multi_color_check":
            points = action_data.get("points", [])
            logic = action_data.get("logic", "AND")
            desc = f"เช็ค {len(points)} สี ({logic})"
        
        if action_data.get("stop_after"): desc += " [🛑]"

        lbl_desc = ctk.CTkLabel(f, text=desc, anchor="w", font=("Segoe UI", 12), text_color="white")
        lbl_desc.pack(side="left", fill="x", expand=True, padx=10, pady=8)
        lbl_desc.bind("<Button-1>", on_click)

    def add_action_item(self, action_data, label_text_unused=None):
        # label_text_unused is kept for compatibility but we generate text dynamically now in update_list_display
        self.actions.append(action_data)
        self.update_list_display()

    def clear_actions(self):
        if self.actions:
            if messagebox.askyesno("ยืนยัน", "ลบคำสั่งทั้งหมด?"):
                self.actions.clear()
                self.selected_index = -1
                self.update_list_display()

    def reset_target_window(self):
        self.target_hwnd = None
        self.target_title = "ทั้งหน้าจอ (Global)"
        self.lbl_target.configure(text=f"เป้าหมาย: {self.target_title}")
        self.lbl_status.configure(text="รีเซ็ตเป้าหมายเป็น 'ทั้งหน้าจอ' เรียบร้อย", text_color="gray")

    def move_action_up(self):
        idx = getattr(self, 'selected_index', -1)
        if idx > 0 and idx < len(self.actions):
            self.actions[idx], self.actions[idx-1] = self.actions[idx-1], self.actions[idx]
            self.selected_index -= 1
            self.update_list_display()
            self.auto_save_presets()
            self.lbl_status.configure(text="เลื่อนขั้นตอนขึ้นแล้ว", text_color="#3498db")
        elif idx == 0:
            self.lbl_status.configure(text="⚠️ อยู่บนสุดแล้วครับ", text_color="#f1c40f")
        else:
            self.lbl_status.configure(text="⚠️ กรุณาคลิกเลือกขั้นตอนที่จะขยับก่อน", text_color="#f1c40f")

    def move_action_down(self):
        idx = getattr(self, 'selected_index', -1)
        if 0 <= idx < len(self.actions) - 1:
            self.actions[idx], self.actions[idx+1] = self.actions[idx+1], self.actions[idx]
            self.selected_index += 1
            self.update_list_display()
            self.auto_save_presets()
            self.lbl_status.configure(text="เลื่อนขั้นตอนลงแล้ว", text_color="#3498db")
        elif idx == len(self.actions) - 1:
            self.lbl_status.configure(text="⚠️ อยู่ล่างสุดแล้วครับ", text_color="#f1c40f")
        elif idx == -1:
            self.lbl_status.configure(text="⚠️ กรุณาคลิกเลือกขั้นตอนที่จะขยับก่อน", text_color="#f1c40f")

    def remove_selected_action(self):
        idx = getattr(self, 'selected_index', -1)
        if 0 <= idx < len(self.actions):
            self.actions.pop(idx)
            self.selected_index = -1
            self.update_list_display()
            self.auto_save_presets()
            self.lbl_status.configure(text="ลบขั้นตอนเรียบร้อย", text_color="#e74c3c")
        else:
            self.lbl_status.configure(text="⚠️ กรุณาคลิกเลือกขั้นตอนที่จะลบก่อน", text_color="#f1c40f")


    # --- Pick Location Logic ---
    def start_pick_location(self):
        self.lbl_status.configure(text="โหมดเลือกพิกัด: หน้าจอจะมืดลงสักครู่ คลิกจุดที่ต้องการ...", text_color="#2980b9")
        self.withdraw()
        
        # Create full-screen transparent overlay
        self.pick_overlay = ctk.CTkToplevel(self)
        self.pick_overlay.attributes('-fullscreen', True)
        self.pick_overlay.attributes('-alpha', 0.3) # Semi-transparent dim
        self.pick_overlay.attributes('-topmost', True)
        self.pick_overlay.configure(fg_color="black", cursor="crosshair")
        
        def on_overlay_click(event):
            self.picked_x_raw = event.x_root
            self.picked_y_raw = event.y_root
            
            # Destroy overlay and restore app
            self.pick_overlay.destroy()
            self.deiconify()
            self.calculate_picked_coords()

        def on_cancel(event):
            self.pick_overlay.destroy()
            self.deiconify()
            self.lbl_status.configure(text="ยกเลิกการเลือกพิกัด", text_color="gray")

        self.pick_overlay.bind("<Button-1>", on_overlay_click)
        self.pick_overlay.bind("<Escape>", on_cancel)
        
        # Force focus to catch keys
        self.pick_overlay.focus_force()

    def calculate_picked_coords(self):
        if self.target_hwnd and win32gui.IsWindow(self.target_hwnd):
             try:
                rect = win32gui.GetWindowRect(self.target_hwnd)
                self.picked_rel_x = self.picked_x_raw - rect[0]
                self.picked_rel_y = self.picked_y_raw - rect[1]
                self.is_relative = True
                txt = f"X:{self.picked_rel_x}, Y:{self.picked_rel_y} (ในหน้าต่าง)"
             except:
                self.picked_rel_x = self.picked_x_raw
                self.picked_rel_y = self.picked_y_raw
                self.is_relative = False
                txt = f"X:{self.picked_rel_x}, Y:{self.picked_rel_y} (Error Window)"
        else:
             self.picked_rel_x, self.picked_rel_y = self.picked_x_raw, self.picked_y_raw
             self.is_relative = False
             txt = f"X:{self.picked_rel_x}, Y:{self.picked_rel_y} (จอ)"
             
        self.lbl_picked_coord.configure(text=txt)
        self.lbl_status.configure(text="บันทึกพิกัดแล้ว (ไม่ได้คลิกจริง)", text_color="gray")

    # --- Color Picker Logic ---
    def start_pick_region(self):
        """Pick a rectangular region on screen"""
        self.lbl_status.configure(text="โหมดตีกรอบ: คลิกค้างแล้วลากเพื่อครอบพื้นที่...", text_color="#d35400")
        self.withdraw()
        self.update() # Ensure window is hidden
        
        self.reg_overlay = ctk.CTkToplevel(self)
        self.reg_overlay.attributes('-fullscreen', True)
        self.reg_overlay.attributes('-alpha', 0.3)
        self.reg_overlay.attributes('-topmost', True)
        self.reg_overlay.configure(fg_color="black")
        self.reg_overlay.focus_force()
        self.reg_overlay.attributes("-topmost", True)
        
        # Cursor setting can sometimes fail on some systems, try-except it
        try: self.reg_overlay.configure(cursor="cross") 
        except: pass
        
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.canvas_reg = ctk.CTkCanvas(self.reg_overlay, bg="black", highlightthickness=0)
        self.canvas_reg.pack(fill="both", expand=True)

        def on_press(event):
            self.start_x = event.x
            self.start_y = event.y
            if self.rect_id: self.canvas_reg.delete(self.rect_id)
            self.rect_id = self.canvas_reg.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red", width=2)

        def on_drag(event):
            self.canvas_reg.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

        def on_release(event):
            try:
                end_x, end_y = event.x, event.y
                self.reg_overlay.destroy()
                self.deiconify()
                
                x1, x2 = min(self.start_x, end_x), max(self.start_x, end_x)
                y1, y2 = min(self.start_y, end_y), max(self.start_y, end_y)
                w, h = x2 - x1, y2 - y1
                
                if w > 5 and h > 5:
                    self.current_region = (x1, y1, w, h)
                    info_text = f"{w}x{h} @ {x1},{y1}"
                    self.lbl_region_info.configure(text=info_text, text_color="#2ecc71")
                    self.lbl_color_region_info.configure(text=info_text, text_color="#2ecc71")
                    self.lbl_status.configure(text="เลือกพื้นที่เรียบร้อย", text_color="#2ecc71")
                else:
                    self.current_region = None
                    self.lbl_region_info.configure(text="พื้นที่: ทั้งจอ", text_color="gray")
                    self.lbl_color_region_info.configure(text="จุดเดียว", text_color="gray")
            except:
                self.deiconify()
                self.lbl_status.configure(text="เกิดข้อผิดพลาดในการเลือกพื้นที่", text_color="red")

        self.canvas_reg.bind("<Button-1>", on_press)
        self.canvas_reg.bind("<B1-Motion>", on_drag)
        self.canvas_reg.bind("<ButtonRelease-1>", on_release)
        self.reg_overlay.bind("<Escape>", lambda e: [self.reg_overlay.destroy(), self.deiconify()])

    def start_pick_color(self):
        self.lbl_status.configure(text="โหมดดูดสี: คลิกจุดที่ต้องการดูดสี...", text_color="#e67e22")
        self.withdraw()
        
        overlay = ctk.CTkToplevel(self)
        overlay.attributes('-fullscreen', True)
        overlay.attributes('-alpha', 0.1)
        overlay.attributes('-topmost', True)
        overlay.configure(fg_color="black", cursor="crosshair")
        
        def on_overlay_click(event):
            abs_x, abs_y = event.x_root, event.y_root
            try:
                rgb = pyautogui.pixel(abs_x, abs_y)
                self.current_color_data = (abs_x, abs_y, rgb)
                self.lbl_color_info.configure(text=f"พิกัด: {abs_x},{abs_y} RGB: {rgb}")
                
                # Update preview canvas
                hex_color = '#%02x%02x%02x' % rgb
                self.canvas_color.delete("all")
                self.canvas_color.create_rectangle(0, 0, 20, 20, fill=hex_color, outline="white")
                self.lbl_status.configure(text=f"ดูดสีสำเร็จ: {rgb}", text_color="gray")
            except Exception as e:
                print(f"Color Pick Error: {e}")
                self.lbl_status.configure(text="ดูดสีผิดพลาด!", text_color="#e74c3c")

            overlay.destroy()
            self.deiconify()

        def on_cancel(event):
            overlay.destroy()
            self.deiconify()
            self.lbl_status.configure(text="ยกเลิกการดูดสี", text_color="gray")

        overlay.bind("<Button-1>", on_overlay_click)
        overlay.bind("<Escape>", on_cancel)
        overlay.focus_force()

    def add_color_action(self):
        if not self.current_color_data:
            self.lbl_color_info.configure(text="กรุณาดูดสีก่อน!", text_color="#e74c3c")
            return
        
        x, y, rgb = self.current_color_data
        try:
            tol = int(self.entry_tol.get())
        except:
            tol = 10
            
        mode = self.var_color_mode.get()
        do_click = self.var_color_click.get()
        click_mode = self.var_color_click_mode.get()
        
        data = {
            "type": "color_search",
            "x": x,
            "y": y,
            "rgb": rgb,
            "region": self.current_region,
            "tolerance": tol,
            "mode": mode,
            "do_click": do_click,
            "click_mode": click_mode
        }
        
        self.add_action_item(data)
        self.lbl_color_info.configure(text_color="white")
        
        # Reset Region & UI
        self.current_region = None
        info_img = "พื้นที่: ทั้งจอ"
        info_color = "พื้นที่: จุดเดียว"
        self.lbl_region_info.configure(text=info_img, text_color="gray")
        self.lbl_color_region_info.configure(text=info_color, text_color="gray")

    def add_click_action(self):
        try:
            x, y = getattr(self, 'picked_rel_x', 0), getattr(self, 'picked_rel_y', 0)
            is_rel = getattr(self, 'is_relative', False)
        except: return
        mode = self.var_click_mode.get()
        btn = self.var_click_btn.get()
        stop_after = self.var_click_stop.get()
        
        # Validation for background mode
        if mode == "background" and not self.target_hwnd:
             messagebox.showwarning("แจ้งเตือน", "โหมดคลิกเบื้องหลัง ต้อง 'ล็อคเป้าหน้าต่าง' ก่อนครับ")
             return

        self.add_action_item({
            "type": "click", 
            "x": x, "y": y, 
            "button": btn, 
            "relative": is_rel,
            "mode": mode,
            "stop_after": stop_after
        }, None)

    def add_type_action(self):
        txt = self.entry_text.get().strip()
        mode = self.var_input_mode.get()
        if not txt:
            messagebox.showwarning("แจ้งเตือน", "กรุณากรอกข้อความหรือบันทึกปุ่มลัดก่อนครับ")
            return
            
        if mode == "text":
            self.add_action_item({"type": "text", "content": txt}, f"พิมพ์ {txt}")
        else:
            self.add_action_item({"type": "hotkey", "content": txt}, f"คีย์ลัด {txt}")
            
        self.entry_text.delete(0, "end")

    def browse_image(self):
        p = filedialog.askopenfilename(filetypes=[("ไฟล์รูปภาพ", "*.png *.jpg *.jpeg *.bmp")])
        if p: 
            self.current_img_path = p
            fname = os.path.basename(p)
            self.lbl_img_path.configure(text=fname, text_color="#3498db")
            # Cache it immediately
            threading.Thread(target=self.cache_image, args=(p,), daemon=True).start()

    def cache_image(self, path):
        if path and path not in self.image_cache:
            try:
                img = cv2.imread(path)
                if img is not None:
                    # Pre-convert to grayscale for performance
                    self.image_cache[path] = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            except: pass

    def preload_images(self):
        """Preload images from all presets into cache"""
        processed = set()
        for p in self.presets:
            for action in p.get("actions", []):
                if action["type"] == "image_search":
                    path = action["path"]
                    if path and path not in processed:
                        self.cache_image(path)
                        processed.add(path)

    def add_image_action(self):
        path = self.current_img_path
        if not path: 
            self.lbl_img_path.configure(text="กรุณาเลือกรูปภาพ!", text_color="#e74c3c")
            return
        
        mode = self.var_img_mode.get() # wait / once
        do_click = self.var_img_click.get()
        
        try:
            off_x = int(self.entry_off_x.get())
            off_y = int(self.entry_off_y.get())
        except:
            off_x, off_y = 0, 0
            
        click_mode = self.var_img_click_mode.get()
        
        data = {
            "type": "image_search",
            "path": path,
            "region": self.current_region,
            "mode": mode,
            "do_click": do_click,
            "click_mode": click_mode,
            "off_x": off_x,
            "off_y": off_y
        }
        
        self.add_action_item(data)
        self.lbl_status.configure(text="เพิ่มคำสั่งค้นหารูปแล้ว", text_color="#27ae60")
        
        # Reset Region & UI
        self.current_region = None
        info_img = "พื้นที่: ทั้งจอ"
        info_color = "พื้นที่: จุดเดียว"
        self.lbl_region_info.configure(text=info_img, text_color="gray")
        self.lbl_color_region_info.configure(text=info_color, text_color="gray")

    def add_wait_action(self):
        try: t = float(self.entry_wait.get())
        except: return
        self.add_action_item({"type": "wait", "seconds": t}, f"รอ {t} วิ")

    def add_multi_color_point(self):
        """Add current color point to multi-color list"""
        if not self.current_color_data:
            self.lbl_status.configure(text="กรุณาดูดสีก่อน!", text_color="#e74c3c")
            return
        
        x, y, rgb = self.current_color_data
        try:
            tol = int(self.entry_tol.get())
        except:
            tol = 10
            
        point = {"x": x, "y": y, "rgb": rgb, "tolerance": tol}
        self.multi_color_points.append(point)
        
        count = len(self.multi_color_points)
        self.lbl_multi_color_count.configure(text=f"จุดที่เก็บ: {count} จุด")
        self.lbl_status.configure(text=f"เพิ่มจุดสี #{count}: {rgb} ที่ ({x},{y})", text_color="#3498db")

    def clear_multi_color_points(self):
        """Clear all multi-color points"""
        self.multi_color_points = []
        self.lbl_multi_color_count.configure(text="จุดที่เก็บ: 0 จุด")
        self.lbl_status.configure(text="ล้างจุดสีทั้งหมดแล้ว", text_color="#7f8c8d")

    def add_multi_color_action(self):
        """Add multi-color check action to script"""
        if not self.multi_color_points:
            self.lbl_status.configure(text="กรุณาเพิ่มจุดสีอย่างน้อย 1 จุด!", text_color="#e74c3c")
            return
        
        logic = self.var_multi_color_logic.get()
        mode = self.var_color_mode.get()
        do_click = self.var_color_click.get()
        click_mode = self.var_color_click_mode.get()
        
        # Use first point as click target if clicking is enabled
        click_x, click_y = 0, 0
        if do_click and self.multi_color_points:
            click_x = self.multi_color_points[0]["x"]
            click_y = self.multi_color_points[0]["y"]
        
        data = {
            "type": "multi_color_check",
            "points": self.multi_color_points.copy(),
            "logic": logic,
            "mode": mode,
            "do_click": do_click,
            "click_mode": click_mode,
            "click_x": click_x,
            "click_y": click_y
        }
        
        desc = f"เช็ค {len(self.multi_color_points)} สี ({logic})"
        self.add_action_item(data, desc)
        self.lbl_status.configure(text=f"เพิ่มคำสั่งเช็คหลายสี: {len(self.multi_color_points)} จุด", text_color="#27ae60")
        
        # Clear points after adding
        self.clear_multi_color_points()

    def show_user_manual(self):
        """Displays a detailed user manual in a new window"""
        manual_win = ctk.CTkToplevel(self)
        manual_win.title("คู่มือการใช้งาน - Franky AutoMate Professional")
        manual_win.geometry("900x800")
        manual_win.attributes("-topmost", True)
        
        # Heading
        ctk.CTkLabel(manual_win, text="📖 คู่มือการใช้งาน Franky AutoMate", font=("Segoe UI", 24, "bold"), text_color="#3498db").pack(pady=20)
        
        # Scrollable Content
        txt_manual = ctk.CTkTextbox(manual_win, font=("Segoe UI", 14), corner_radius=10, border_width=1, border_color="#333")
        txt_manual.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        manual_content = """
[ ส่วนที่ 1: การเตรียมการเบื้องต้น ]
1. การเลือกเป้าหมาย (สำคัญมาก):
   - หากต้องการส่งคำสั่งไปเฉพาะหน้าต่างใดหน้าต่างหนึ่ง ให้กด "เลือกหน้าต่างเป้าหมาย" แล้วคลิกที่หน้าต่างนั้น
   - หากต้องการทำงานแบบเต็มหน้าจอ (Global) ให้กด "ยกเลิก" หรือไม่ต้องทำส่วนนี้

[ ส่วนที่ 2: เครื่องมือเพิ่มคำสั่ง ]
1. เมาส์ (Mouse):
   - กด "เลือกจุดบนจอ" หน้าจอจะมืดลง ให้คลิกจุดที่ต้องการ
   - เลือกโหมด "ปกติ" (ต้องเปิดหน้าต่างค้างไว้) หรือ "เบื้องหลัง" (ทำงานได้แม้หน้าต่างโดนทับ)
   - หากเลือกเบื้องหลัง ต้องล็อคเป้าหมายหน้าต่างก่อนเสมอ

2. พิมพ์/ปุ่ม (Keyboard):
   - "ข้อความ": พิมพ์สิ่งที่ต้องการให้โปรแกรมกรอกลงไป
   - "ปุ่มลัด": กดปุ่ม "บันทึกปุ่มกด" แล้วกดคีย์ลัดที่ต้องการ (เช่น Ctrl+C, Alt+Tab)

3. ค้นหารูป (Image Search):
   - เลือกรูปภาพตัวอย่างที่ต้องการให้โปรแกรมหา (ควรใช้ไฟล์ .png)
   - "ตีกรอบพื้นที่": ลากเมาส์ครอบบริเวณที่ต้องการให้หา (ช่วยให้หาเร็วขึ้นมาก)
   - "รอจนเจอ": โปรแกรมจะวนรอจนภาพปรากฏขึ้นมา
   - "ขยับจุดคลิก (Offset)": หากต้องการให้คลิกเยื้องจากกลางรูปภาพ

4. ค้นหาสี (Color Search):
   - กด "ดูดสีจากจอ" แล้วคลิกจุดที่มีสีที่ต้องการ
   - "ความเพี้ยนสี (Tolerance)": ปรับระดับ 0-100 (หากสีมีการเปลี่ยนแปลงเล็กน้อย เช่น แสงเงา)

[ ส่วนที่ 3: ระบบจัดการขั้นตอน (Script) ]
- คำสั่งที่เพิ่มจะมาเรียงกันที่ด้านซ้าย
- คุณสามารถ "ขยับขึ้น/ลง" เพื่อเปลี่ยนลำดับการทำงาน
- "ลบที่เลือก" หรือ "ล้างทั้งหมด" เพื่อเริ่มใหม่

[ ส่วนที่ 4: การตั้งค่าการรัน (Presets & Execution) ]
1. Presets: ระบบบันทึกชุดคำสั่งได้หลายชุด สามารถเปลี่ยนชื่อและตั้งปุ่มลัดเฉพาะชุดได้
2. จำนวนรอบ: ใส่เลขรอบที่ต้องการ หรือใส่ 0 เพื่อให้วนซ้ำไม่จำกัด
3. หน่วงเวลาเพิ่ม: ปรับความเร็วภาพรวม (ถ้าโปรแกรมรันเร็วเกินไปจนเกม/แอพตามไม่ทัน)
4. ทดลองวิ่ง (Dry Run): โปรแกรมจะรันตามขั้นตอนแต่ "ไม่คลิกจริง" (ใช้ตรวจสอบตำแหน่ง)

[ ส่วนที่ 5: ปุ่มลัดหลัก ]
- เริ่ม/หยุด: ค่าเริ่มต้นคือ [ F6 ] คุณสามารถเปลี่ยนได้ตามถนัด
- การกู้คืน: หากเมาส์ค้างหรือโปรแกรมทำงานผิดปกติ ให้เลื่อนเมาส์ไปที่ "ขอบหน้าจอ" ด้านใดด้านหนึ่ง ระบบจะหยุดทำงานทันที (Fail-safe)

[ ส่วนที่ 6: โหมดหลบการตรวจจับ (Stealth Mode) ]
โหมดนี้ทำให้การทำงานอัตโนมัติดู "เหมือนคนจริง" มากขึ้น เหมาะกับระบบที่มีการตรวจจับบอท

1. ขยับเมาส์แบบคน (Human Curves):
   - เมาส์จะเคลื่อนที่เป็นเส้นโค้ง Bezier แทนการกระโดดไปตรงจุด
   - มีการสุ่มความเร็วและทิศทางเล็กน้อยทุกครั้ง
   - ใช้ได้กับ: คลิกปกติ เท่านั้น (ไม่รองรับคลิกเบื้องหลัง)

2. สุ่มจุดคลิก (Click Jitter):
   - จุดคลิกจะสุ่มคลาดเคลื่อนเล็กน้อย (1-20 พิกเซล)
   - ตัวอย่าง: ถ้าเป้าหมาย (500,300) และ Jitter=3, จุดจริงอาจเป็น (502,298)
   - ใช้ได้กับ: คลิกปกติ, ค้นหารูป, ค้นหาสี

3. สุ่มเวลาหน่วง (Timing Variance):
   - เวลารอจะมีความแปรปรวน ±10-50%
   - ตัวอย่าง: รอ 1 วินาที อาจเป็น 0.8s, 1.0s หรือ 1.2s
   - ใช้ได้กับ: ทุกประเภทคำสั่ง

คำแนะนำ:
- ค่าเริ่มต้นแนะนำ: Jitter 3-5px, Timing 20%
- คลิกเบื้องหลังไม่รองรับ Human Curves (ไม่ได้ขยับเมาส์จริง)
- โหมด Stealth อาจทำให้การทำงานช้าลงเล็กน้อย

--------------------------------------------------
Franky AutoMate v1.6.0 Premium Edition
"เครื่องมือช่วยรันงานอัตโนมัติ สำหรับผู้ที่ต้องการความเป็นเลิศ"
"""
        txt_manual.insert("0.0", manual_content.strip())
        txt_manual.configure(state="disabled") # Read only

        ctk.CTkButton(manual_win, text="ปิดคู่มือ", command=manual_win.destroy, width=120).pack(pady=10)

    def check_for_updates(self, silent=False):
        """Check GitHub for new releases"""
        def _check():
            try:
                req = urllib.request.Request(
                    GITHUB_API_URL,
                    headers={'User-Agent': 'FrankyAutoMate'}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    
                latest_version = data.get('tag_name', '').lstrip('v')
                download_url = data.get('html_url', '')
                release_notes = data.get('body', '')[:200]
                
                # Version comparison (simple string compare)
                current_parts = [int(x) for x in APP_VERSION.split('.')]
                latest_parts = [int(x) for x in latest_version.split('.') if x.isdigit()]
                
                # Pad versions to same length
                while len(current_parts) < 3: current_parts.append(0)
                while len(latest_parts) < 3: latest_parts.append(0)
                
                is_newer = latest_parts > current_parts
                
                if is_newer:
                    self.after(0, lambda: self._show_update_dialog(latest_version, download_url, release_notes))
                elif not silent:
                    self.after(0, lambda: messagebox.showinfo(
                        "ตรวจสอบอัปเดท",
                        f"✅ คุณใช้เวอร์ชันล่าสุดแล้ว!\n\nเวอร์ชันปัจจุบัน: {APP_VERSION}"
                    ))
                    
            except Exception as e:
                if not silent:
                    self.after(0, lambda: messagebox.showerror(
                        "ตรวจสอบอัปเดท",
                        f"❌ ไม่สามารถเชื่อมต่อ GitHub ได้\n\n{str(e)}"
                    ))
                if self.var_debug_mode.get():
                    self.log_message(f"🔧 Update check error: {e}", level=logging.DEBUG)
        
        # Run in background thread
        threading.Thread(target=_check, daemon=True).start()
    
    def _show_update_dialog(self, new_version, download_url, notes):
        """Show update available dialog"""
        result = messagebox.askyesno(
            "🎉 มีอัปเดทใหม่!",
            f"พบเวอร์ชันใหม่: v{new_version}\n"
            f"เวอร์ชันปัจจุบัน: v{APP_VERSION}\n\n"
            f"📝 Notes:\n{notes[:150]}...\n\n"
            "ต้องการเปิดหน้าดาวน์โหลดไหม?"
        )
        if result:
            webbrowser.open(download_url)


if __name__ == "__main__":
    app = AutoMationApp()
    app.mainloop()