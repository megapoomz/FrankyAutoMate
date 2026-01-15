"""
EngineMixin - Handles automation execution, background runner, and action logic
"""
import time
import threading
import random
import math
import logging
import os
from typing import Dict, Any

import pyautogui
import cv2
import numpy as np
import win32gui

from ..utils.sendinput import send_input_click, send_input_move


class EngineMixin:
    """Handles automation execution, background runner, and single action logic"""
    
    def run_automation(self):
        """Start or pause/resume automation"""
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
        try:
            loops = int(self.entry_loop.get())
        except:
            loops = 1
        self.is_running = True
        self.btn_run.configure(text="หยุด (STOP)", fg_color="#c0392b")
        self.stealth_on_run_start()
        self.execution_thread = threading.Thread(target=self.bg_runner, args=(loops,))
        self.execution_thread.daemon = True
        self.execution_thread.start()

    def stop_automation(self):
        """Stop automation"""
        self.is_running = False
        self.is_paused = False
        self.next_step.set()
        self.stealth_on_run_stop()
        self.lbl_status.configure(text="🛑 กำลังสั่งหยุดทำงาน...", text_color="#e67e22")

    def bg_runner(self, loops):
        """Background runner thread"""
        count = 0
        self.log_message("=== เริ่มทำงานอัตโนมัติ ===")
        while self.is_running:
            if loops > 0 and count >= loops:
                break
            count += 1
            loop_msg = f"รอบที่ {count}" + (f" /{loops}" if loops > 0 else "")
            self.log_message(f"--- {loop_msg} ---")
            
            if self.target_hwnd and win32gui.IsWindow(self.target_hwnd):
                try:
                    win32gui.SetForegroundWindow(self.target_hwnd)
                    win32gui.BringWindowToTop(self.target_hwnd)
                    time.sleep(0.3)
                except:
                    pass
            
            for i, action in enumerate(self.actions):
                if not self.is_running:
                    break
                
                # Handling Paused State
                if self.is_paused or self.var_step_mode.get():
                    if self.var_step_mode.get():
                        self.btn_run.configure(text="⏭️ ต่อไป (NEXT STEP)", fg_color="#3498db")
                        self.lbl_status.configure(text=f"⏸️ ขั้นตอน {i+1}: รอคำสั่ง...", text_color="#f1c40f")
                    
                    self.is_paused = True
                    self.next_step.clear()
                    while self.is_paused and self.is_running:
                        if self.next_step.wait(0.1):
                            break
                    
                    self.btn_run.configure(text="🛑 หยุด (STOP)", fg_color="#c0392b")

                if not self.is_running:
                    break
                self.highlight_action(i)
                try:
                    self.execute_one(action)
                except pyautogui.FailSafeException:
                    self.is_running = False
                    self.log_message("⚠️ หยุดระบบฉุกเฉิน: เมาส์ชนขอบจอ (Fail-safe)", "red")
                    self.lbl_status.configure(text="⚠️ หยุดฉุกเฉิน: เมาส์ชนขอบจอ", text_color="#e74c3c")
                    break
                except Exception as e:
                    self.log_message(f"❌ เกิดข้อผิดพลาด: {e}", "red")
                    self.is_running = False
                    self.lbl_status.configure(text=f"❌ ข้อผิดพลาด: {e}", text_color="red")
                    break
                
                if not self.var_step_mode.get():
                    time.sleep(0.1 + self.speed_delay)
        
        self.is_running = False
        self.highlight_action(-1)
        self.btn_run.configure(text="เริ่มทำงาน (START)", fg_color="#27ae60")
        self.lbl_status.configure(text="จบการทำงาน", text_color="#2ecc71")
        self.log_message("=== จบการทำงาน ===")

    def execute_one(self, action: Dict[str, Any]) -> None:
        """Execute a single action"""
        start_time = time.perf_counter()
        t = action["type"]
        
        try:
            if t == "click":
                self._execute_click(action)
            elif t == "text":
                self._execute_text(action)
            elif t == "hotkey":
                self._execute_hotkey(action)
            elif t == "wait":
                self._execute_wait(action)
            elif t == "image_search":
                self._execute_image_search(action)
            elif t == "color_search":
                self._execute_color_search(action)
            
            elapsed = (time.perf_counter() - start_time) * 1000
            self.log_message(f"  ⏱️ ใช้เวลา: {elapsed:.0f}ms", "#7f8c8d")
            self.lbl_status.configure(text=f"รันคำสั่ง {t}: {elapsed:.0f}ms", text_color="#3498db")
                
        except Exception as e:
            self.log_message(f"❌ คำสั่ง {t} ล้มเหลว: {e}", "red")
            raise e

    def _human_move(self, tx, ty):
        """Move mouse in a human-like curve using Bezier points"""
        start_x, start_y = pyautogui.position()
        dist = math.hypot(tx - start_x, ty - start_y)
        
        if dist < 20:
            pyautogui.moveTo(tx, ty, duration=random.uniform(0.05, 0.15))
            return

        # Bezier control points
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
                time.sleep(random.uniform(0.001, 0.003))

    # Note: _execute_click, _execute_text, _execute_hotkey, _execute_wait,
    # _execute_image_search, _execute_color_search methods are kept in main app
    # due to tight coupling with UI and state variables
