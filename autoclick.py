import sys
import os
import time
import threading
import logging
import random
import json
import webbrowser
import ctypes
from typing import Dict, Any, List, Optional

import customtkinter as ctk
import pyautogui
import win32gui
import win32con
import win32api
import requests
import mss
import numpy as np

# Core & Utils
from core.constants import *
from utils.win32_input import send_input_click, send_input_move, send_input_text, is_admin

# Engine Mixins
from engine.hotkey_engine import HotkeyMixin
from engine.preset_manager import PresetMixin
from engine.automation_engine import EngineMixin
from engine.action_mixin import ActionMixin
from engine.logic_mixin import LogicMixin

# UI Mixins
from ui.picker_mixin import PickerMixin
from ui.vision_mixin import VisionMixin
from ui.variables_mixin import VariablesMixin
from ui.stealth_mixin import StealthMixin
from ui.tabs_mixin import TabsMixin
from ui.ui_mixin import UIMixin
from ui.update_window import UpdateProgressWindow

# Ensure logs directory exists
LOG_DIR = os.path.join(os.getenv('APPDATA', os.getcwd()), "FrankyAutoMate", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f"automate_{time.strftime('%Y%m%d')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

class AutoMationApp(ctk.CTk, HotkeyMixin, PresetMixin, EngineMixin, ActionMixin, LogicMixin, VisionMixin, VariablesMixin, PickerMixin, StealthMixin, TabsMixin, UIMixin):
    def __init__(self):
        super().__init__()
        
        # State Initialization
        self.actions = []
        self.is_running = False
        self.is_paused = False
        self.execution_thread = None
        self.next_step = threading.Event()
        self.target_hwnd = None
        self.target_title = "ทั้งหน้าจอ (Global)"
        self.image_cache = {}
        self.action_widgets = []
        self.temp_multi_points = []
        self.speed_delay = 0.0
        self.selected_index = -1
        self.show_marker = True
        self.current_img_path = ""
        self.current_region = None
        self.current_color_data = None
        
        # Hotkey & Engine Configuration
        self.toggle_key = "f6"
        self.held_keys = set()
        self.recorded_keys = set()
        self.recording_state = None
        self.current_recorded_str = ""
        self.waiting_for_preset_key = None
        self.current_preset_index = 0
        
        # Perf Metrics
        self.perf_metrics = {"start_time": 0, "actions_exec": []}
        self.screenshot_cache = None
        self.screenshot_cache_time = 0
        self.screenshot_cache_ttl = 0.15  # 150ms TTL for screen cache
        
        # Stealth Vars
        self.var_stealth_move = ctk.BooleanVar(value=False)
        self.var_stealth_jitter = ctk.BooleanVar(value=False)
        self.var_stealth_jitter_radius = ctk.DoubleVar(value=3.0)
        self.var_stealth_timing = ctk.BooleanVar(value=False)
        self.var_stealth_timing_val = ctk.DoubleVar(value=0.2)
        self.var_stealth_hide_window = ctk.BooleanVar(value=False)
        self.var_stealth_random_title = ctk.BooleanVar(value=False)
        self.var_stealth_sendinput = ctk.BooleanVar(value=False)
        self.var_show_overlay = ctk.BooleanVar(value=True)
        self.var_img_conf = ctk.DoubleVar(value=0.75)
        self.original_title = f"Franky AutoMate v{APP_VERSION}"
        
        # UI Control Vars
        self.var_dry_run = ctk.BooleanVar(value=False)
        self.var_step_mode = ctk.BooleanVar(value=False)
        self.var_debug_mode = ctk.BooleanVar(value=False)
        self.var_follow_window = ctk.BooleanVar(value=False)
        
        # Variable System (Phase 3)
        self.variables = {}
        self.variable_lock = threading.Lock()
        
        # Path for presets
        self.presets_file = os.path.join(os.path.dirname(LOG_DIR), "presets.json")
        self.create_default_preset()
        
        # Deferred startup
        self.after(100, self.launch_app)

    def launch_app(self):
        self.setup_ui()
        self.load_presets_on_startup()
        self.setup_hotkeys()
        self.protocol("WM_DELETE_WINDOW", self.on_app_close)
        self.deiconify()
        
        if not is_admin():
            import tkinter.messagebox as messagebox
            ans = messagebox.askyesno("ต้องใช้สิทธิ์ Administrator",
                "โปรแกรมจำเป็นต้องทำงานด้วยสิทธิ์ Administrator เพื่อส่งคลิก/คีย์บอร์ดไปยังทุกหน้าต่างอย่างเสถียร 100%\n\n"
                "ต้องการให้โปรแกรมเปิดใหม่ด้วยสิทธิ์ Administrator ตอนนี้เลยใช่หรือไม่?", parent=self)
            if ans:
                try:
                    script = os.path.abspath(sys.argv[0])
                    params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
                    if getattr(sys, 'frozen', False):
                        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
                    else:
                        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
                    sys.exit(0)
                except Exception as e:
                    messagebox.showerror("Error", f"ไม่สามารถยกระดับสิทธิ์ได้: {e}", parent=self)
                
        self.lbl_status.configure(text="ระบบพร้อมทำงาน", text_color=COLOR_SUCCESS)
        # Auto-check for updates after 3 seconds
        self.after(3000, lambda: threading.Thread(target=self.check_for_updates, args=(True,), daemon=True).start())

    def on_app_close(self):
        """Cleanup resources before closing"""
        if hasattr(self, 'sct'):
            try: self.sct.close()
            except Exception: pass
        if hasattr(self, 'listener'):
            try: self.listener.stop()
            except Exception: pass
        self.destroy()

    def check_for_updates(self, silent=False):
        """Check GitHub Releases for new version. Runs in background thread."""
        try:
            self.after(0, lambda: self.btn_check_update.configure(text="⏳ กำลังเช็ค...", state="disabled"))
            
            headers = {'User-Agent': 'FrankyAutoMate-Updater'}
            resp = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            latest_tag = data.get("tag_name", "").lstrip("vV")
            changelog = data.get("body", "ไม่มีรายละเอียด")
            
            # Find .zip asset download URL
            download_url = None
            for asset in data.get("assets", []):
                if asset["name"].endswith(".zip"):
                    download_url = asset["browser_download_url"]
                    break
            
            # Semver comparison
            def parse_ver(v):
                parts = v.split(".")
                return tuple(int(x) for x in parts if x.isdigit())
            
            current = parse_ver(APP_VERSION)
            latest = parse_ver(latest_tag)
            
            if latest > current and download_url:
                def _show_update():
                    from tkinter import messagebox
                    answer = messagebox.askyesno(
                        "🔔 พบเวอร์ชันใหม่!",
                        f"เวอร์ชันปัจจุบัน: v{APP_VERSION}\n"
                        f"เวอร์ชันใหม่: v{latest_tag}\n\n"
                        f"📋 รายละเอียด:\n{changelog[:300]}{'...' if len(changelog) > 300 else ''}\n\n"
                        f"ต้องการอัปเดตตอนนี้เลยไหม?",
                        parent=self
                    )
                    if answer:
                        UpdateProgressWindow(self, latest_tag, download_url)
                self.after(0, _show_update)
            elif not silent:
                self.after(0, lambda: self.lbl_status.configure(
                    text=f"✅ ใช้เวอร์ชันล่าสุดแล้ว (v{APP_VERSION})", text_color=COLOR_SUCCESS))
                
        except Exception as e:
            if not silent:
                self.after(0, lambda: self.lbl_status.configure(
                    text=f"❌ เช็คอัปเดตไม่ได้: {e}", text_color=COLOR_DANGER))
        finally:
            self.after(0, lambda: self.btn_check_update.configure(text="🔄 เช็คอัปเดต", state="normal"))

    def preload_images(self):
        """Preload image templates from all preset actions into cache"""
        try:
            import cv2
            for preset in self.presets:
                for action in preset.get("actions", []):
                    path = action.get("path")
                    if path and path not in self.image_cache:
                        try:
                            img = cv2.imread(path)
                            if img is not None:
                                self.image_cache[path] = img
                        except Exception:
                            pass
        except Exception:
            pass

    def setup_ui(self):
        self.title(self.original_title)
        self.geometry("1180x880")
        self.minsize(1100, 800)
        self.configure(fg_color=COLOR_BG)

        # Set AppUserModelID so Windows taskbar displays correct icon when running from source
        try:
            import ctypes
            myappid = f"megapoomz.frankyautomate.app.{APP_VERSION}"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        # Resolve asset path for Window Icon (both frozen/unfrozen)
        if getattr(sys, 'frozen', False):
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.icon_path_ico = os.path.join(base_dir, "icon.ico")
        self.icon_path_png = os.path.join(base_dir, "icon.png")

        # Set the icon immediately and also defer it with after() to guarantee persistence
        self.set_app_icon()
        self.after(200, self.set_app_icon)
        self.after(1000, self.set_app_icon) # Extra insurance for delayed window rendering

    def set_app_icon(self):
        """Set taskbar and titlebar icon with multiple fallbacks and timing workarounds"""
        try:
            import ctypes
            myappid = f"megapoomz.frankyautomate.app.{APP_VERSION}"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        # Try setting the icon using iconbitmap (.ico)
        if hasattr(self, 'icon_path_ico') and os.path.exists(self.icon_path_ico):
            try:
                self.iconbitmap(self.icon_path_ico)
            except Exception as e:
                try:
                    self.wm_iconbitmap(self.icon_path_ico)
                except Exception:
                    pass

        # Also set iconphoto (.png) sequentially to ensure taskbar and window titlebar display correctly on all Windows environments
        if hasattr(self, 'icon_path_png') and os.path.exists(self.icon_path_png):
            try:
                from PIL import Image, ImageTk
                img = Image.open(self.icon_path_png)
                photo = ImageTk.PhotoImage(img)
                self.iconphoto(True, photo)
                self._icon_photo_ref = photo  # Prevent garbage collection
            except Exception as ex:
                pass
        
        # Main Layout
        self.grid_columnconfigure(0, weight=1) # List area
        self.grid_columnconfigure(1, weight=1) # Tool area
        self.grid_rowconfigure(0, weight=1)

        # --- Left Panel: Action List ---
        f_left = ctk.CTkFrame(self, fg_color="transparent")
        f_left.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        # Header for Actions
        f_list_head = ctk.CTkFrame(f_left, fg_color="transparent")
        f_list_head.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(f_list_head, text="ลำดับขั้นตอน (AUTOMATION SCRIPT)", font=("Tahoma", 16, "bold"), text_color="white").pack(side="left")
        
        # Action Toolbar (Up/Down/Delete)
        f_tool_mini = ctk.CTkFrame(f_list_head, fg_color=COLOR_INNER, corner_radius=10, height=35)
        f_tool_mini.pack(side="right")
        ctk.CTkButton(f_tool_mini, text="ขึ้น", width=35, height=30, command=self.move_action_up, fg_color="transparent", hover_color=COLOR_INNER).pack(side="left", padx=2)
        ctk.CTkButton(f_tool_mini, text="ลง", width=35, height=30, command=self.move_action_down, fg_color="transparent", hover_color=COLOR_INNER).pack(side="left", padx=2)
        ctk.CTkButton(f_tool_mini, text="ลบ", width=35, height=30, command=self.remove_selected_action, fg_color="transparent", hover_color=COLOR_DANGER).pack(side="left", padx=2)

        # List Scrollable
        self.scroll_actions = ctk.CTkScrollableFrame(f_left, fg_color="#020617", border_width=1, border_color=BORDER_COLOR, corner_radius=15)
        self.scroll_actions.pack(fill="both", expand=True)
        
        # Execution Panel (Below Action List on Left Side)
        self.setup_execution_panel(f_left)

        # --- Right Panel: Tools & Config ---
        f_right = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=20, border_width=1, border_color=BORDER_COLOR)
        f_right.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=20)
        
        # Make the internal content scrollable
        self.scroll_right = ctk.CTkScrollableFrame(f_right, fg_color="transparent", corner_radius=0)
        self.scroll_right.pack(fill="both", expand=True, padx=5, pady=5)

        # Main Tabview with 4 premium categories (Inside scrollable)
        self.main_tabs = ctk.CTkTabview(self.scroll_right, fg_color="transparent", 
                                        segmented_button_selected_color=COLOR_ACCENT, 
                                        segmented_button_unselected_color="#1e293b", 
                                        segmented_button_fg_color="#0f172a")
        self.main_tabs._segmented_button.configure(font=("Tahoma", 11, "bold"))
        self.main_tabs.pack(fill="x", padx=5, pady=5)

        tab_actions_group = self.main_tabs.add("🛠️ การทำงาน (Actions)")
        tab_detection_group = self.main_tabs.add("🔍 การตรวจจับ (Detection)")
        tab_logic_group = self.main_tabs.add("🧠 ตรรกะ & ตัวแปร (Logic)")
        tab_settings_group = self.main_tabs.add("⚙️ ระบบ & ตั้งค่า (System)")

        # Group 1: Actions Sub-tabview
        tabs_actions = ctk.CTkTabview(tab_actions_group, fg_color="transparent",
                                      segmented_button_selected_color=COLOR_ACCENT,
                                      segmented_button_unselected_color="#0f172a",
                                      segmented_button_fg_color="#1e293b")
        tabs_actions._segmented_button.configure(font=("Tahoma", 10, "bold"))
        tabs_actions.pack(fill="x", padx=0, pady=0)
        
        self.tab_click = tabs_actions.add("🖱️ Mouse")
        self.tab_type = tabs_actions.add("⌨️ Type")
        self.tab_wait = tabs_actions.add("⏱️ Wait")

        # Group 2: Detection Sub-tabview
        tabs_detection = ctk.CTkTabview(tab_detection_group, fg_color="transparent",
                                        segmented_button_selected_color=COLOR_ACCENT,
                                        segmented_button_unselected_color="#0f172a",
                                        segmented_button_fg_color="#1e293b")
        tabs_detection._segmented_button.configure(font=("Tahoma", 10, "bold"))
        tabs_detection.pack(fill="x", padx=0, pady=0)
        
        self.tab_image = tabs_detection.add("🖼️ Image")
        self.tab_color = tabs_detection.add("🎨 Color")
        self.tab_vision = tabs_detection.add("👁️ Vision")

        # Group 3: Logic & Variables Sub-tabview
        tabs_logic = ctk.CTkTabview(tab_logic_group, fg_color="transparent",
                                    segmented_button_selected_color=COLOR_ACCENT,
                                    segmented_button_unselected_color="#0f172a",
                                    segmented_button_fg_color="#1e293b")
        tabs_logic._segmented_button.configure(font=("Tahoma", 10, "bold"))
        tabs_logic.pack(fill="x", padx=0, pady=0)
        
        self.tab_vars = tabs_logic.add("💾 Vars")
        self.tab_logic = tabs_logic.add("❓ Logic")

        # Group 4: Stealth & Logs Sub-tabview
        tabs_settings = ctk.CTkTabview(tab_settings_group, fg_color="transparent",
                                       segmented_button_selected_color=COLOR_ACCENT,
                                       segmented_button_unselected_color="#0f172a",
                                       segmented_button_fg_color="#1e293b")
        tabs_settings._segmented_button.configure(font=("Tahoma", 10, "bold"))
        tabs_settings.pack(fill="x", padx=0, pady=0)
        
        self.tab_stealth = tabs_settings.add("🛡️ Stealth")
        self.tab_log = tabs_settings.add("📋 Log")
        
        self.setup_click_tab()
        self.setup_type_tab()
        self.setup_image_tab()
        self.setup_color_tab()
        self.setup_wait_tab()
        self.setup_vars_tab()
        self.setup_vision_tab()
        self.setup_logic_tab()
        self.setup_stealth_tab()
        self.setup_log_tab()

        # Preset & Control Section (Bottom Right)
        self.setup_bottom_panels(self.scroll_right)
        
        # Footer
        self.setup_footer()
        self.update_list_display()

    def setup_bottom_panels(self, parent):
        f_bot = ctk.CTkFrame(parent, fg_color="transparent")
        f_bot.pack(fill="x", padx=15, pady=15)
        
        # Target Window Frame
        f_target = ctk.CTkFrame(f_bot, fg_color=COLOR_INNER, corner_radius=15, border_width=1, border_color=BORDER_COLOR)
        f_target.pack(fill="x", pady=(0, 10))
        
        f_t_head = ctk.CTkFrame(f_target, fg_color="transparent")
        f_t_head.pack(fill="x", padx=15, pady=(12, 5))
        ctk.CTkLabel(f_t_head, text="เป้าหมาย (TARGET WINDOW)", font=("Tahoma", 11, "bold"), text_color=COLOR_ACCENT).pack(side="left")
        
        self.lbl_target = ctk.CTkLabel(f_target, text=f"เป้าหมาย: {self.target_title}", font=("Tahoma", 12))
        self.lbl_target.pack(pady=5)
        
        f_t_btn = ctk.CTkFrame(f_target, fg_color="transparent")
        f_t_btn.pack(pady=(0, 5))
        ctk.CTkButton(f_t_btn, text="ล็อคหน้าต่าง", command=self.pick_target_window, width=120, height=32, font=("Tahoma", 11, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(f_t_btn, text="รีเซ็ต", command=self.reset_target_window, width=100, height=32, fg_color="#334155", font=("Tahoma", 11)).pack(side="left", padx=5)

        self.cb_follow = ctk.CTkCheckBox(f_target, text="ติดตามหน้าต่างอัตโนมัติ (Follow Window)", variable=self.var_follow_window, font=("Tahoma", 11))
        self.cb_follow.pack(pady=(0, 10))

        # Preset Frame
        f_preset = ctk.CTkFrame(f_bot, fg_color=COLOR_INNER, corner_radius=15, border_width=1, border_color=BORDER_COLOR)
        f_preset.pack(fill="x", pady=(0, 10))
        
        f_pre_head = ctk.CTkFrame(f_preset, fg_color="transparent")
        f_pre_head.pack(fill="x", padx=15, pady=(12, 5))
        ctk.CTkLabel(f_pre_head, text="คลังชุดคำสั่ง (PRESETS)", font=("Tahoma", 11, "bold"), text_color=COLOR_ACCENT).pack(side="left")
        ctk.CTkButton(f_pre_head, text="บันทึกไฟล์", width=80, height=24, font=("Tahoma", 10), command=self.save_presets_to_file).pack(side="right", padx=5)
        ctk.CTkButton(f_pre_head, text="โหลดไฟล์", width=80, height=24, font=("Tahoma", 10), command=self.load_presets_from_file).pack(side="right")

        f_pre_name = ctk.CTkFrame(f_preset, fg_color="transparent")
        f_pre_name.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(f_pre_name, text="ชื่อชุด:", font=("Tahoma", 11)).pack(side="left", padx=(0, 5))
        self.entry_preset_name = ctk.CTkEntry(f_pre_name, height=28, font=("Tahoma", 11))
        self.entry_preset_name.pack(side="left", fill="x", expand=True)
        self.entry_preset_name.bind("<KeyRelease>", self.on_preset_name_changed)

        f_pre_row = ctk.CTkFrame(f_preset, fg_color="transparent")
        f_pre_row.pack(fill="x", padx=15, pady=(0, 12))
        self.preset_dropdown = ctk.CTkOptionMenu(f_pre_row, values=["ชุดที่ 1"], command=self.on_preset_changed, fg_color=COLOR_CARD, button_color=COLOR_INNER)
        self.preset_dropdown.pack(side="left", fill="x", expand=True)
        self.lbl_preset_hotkey = ctk.CTkLabel(f_pre_row, text="[ - ]", font=("JetBrains Mono", 11, "bold"), text_color=COLOR_ACCENT)
        self.lbl_preset_hotkey.pack(side="left", padx=5)
        ctk.CTkButton(f_pre_row, text="ตั้งปุ่ม", width=55, command=self.start_change_preset_hotkey).pack(side="left", padx=2)
        ctk.CTkButton(f_pre_row, text="เพิ่ม", width=45, command=self.add_new_preset).pack(side="left", padx=2)
        ctk.CTkButton(f_pre_row, text="ก็อบ", width=45, command=self.duplicate_current_preset, fg_color=COLOR_ACCENT, hover_color=GRADIENT_START).pack(side="left", padx=2)
        ctk.CTkButton(f_pre_row, text="ลบ", width=40, command=self.delete_current_preset, fg_color=COLOR_DANGER).pack(side="left", padx=2)

        # Main Control Frame (Execution) - Moved to Left Side via setup_execution_panel
        # This function now only handles Target + Presets for the right side
        
    def setup_execution_panel(self, parent):
        """Execution controls - placed on the left side below the action list"""
        f_run = ctk.CTkFrame(parent, fg_color=COLOR_INNER, corner_radius=15, border_width=1, border_color=BORDER_COLOR)
        f_run.pack(fill="x", pady=(15, 0))
        
        f_run_head = ctk.CTkFrame(f_run, fg_color="transparent")
        f_run_head.pack(fill="x", padx=15, pady=(12, 8))
        ctk.CTkLabel(f_run_head, text="เริ่มทำงาน (EXECUTION)", font=("Tahoma", 11, "bold"), text_color=COLOR_SUCCESS).pack(side="left")
        self.lbl_hotkey = ctk.CTkLabel(f_run_head, text="[ F6 ]", font=("JetBrains Mono", 11, "bold"), text_color=COLOR_ACCENT)
        self.lbl_hotkey.pack(side="right")
        self.lbl_hotkey.bind("<Button-1>", lambda e: self.start_change_hotkey())
        
        f_loop = ctk.CTkFrame(f_run, fg_color="transparent")
        f_loop.pack(fill="x", padx=15)
        ctk.CTkLabel(f_loop, text="ทำกี่รอบ (0=ตลอดไป):", font=("Tahoma", 12)).pack(side="left")
        self.entry_loop = ctk.CTkEntry(f_loop, width=70, height=30, justify="center", font=("JetBrains Mono", 12))
        self.entry_loop.insert(0, "1")
        self.entry_loop.pack(side="left", padx=10)
        self.entry_loop.bind("<KeyRelease>", lambda e: self.auto_save_presets())
        
        f_opt = ctk.CTkFrame(f_run, fg_color="transparent")
        f_opt.pack(fill="x", padx=15, pady=5)
        ctk.CTkCheckBox(f_opt, text="จำลอง (Dry Run)", variable=self.var_dry_run, font=("Tahoma", 11)).pack(side="left", padx=5)
        ctk.CTkCheckBox(f_opt, text="ทำทีละขั้น (Step Mode)", variable=self.var_step_mode, font=("Tahoma", 11)).pack(side="left", padx=5)

        self.btn_run = ctk.CTkButton(f_run, text="เริ่มทำงาน (Global Start)", command=self.run_automation, fg_color=COLOR_SUCCESS, hover_color="#059669", height=45, font=("Tahoma", 14, "bold"))
        self.btn_run.pack(fill="x", padx=15, pady=(5, 15))

    def setup_footer(self):
        f_foot = ctk.CTkFrame(self, fg_color=COLOR_INNER, height=40, corner_radius=0)
        f_foot.grid(row=1, column=0, columnspan=2, sticky="ew")
        
        ctk.CTkLabel(f_foot, text=f"FrankyAutoMate v{APP_VERSION} Premium", font=("Tahoma", 10, "bold"), text_color="#475569").pack(side="left", padx=20)
        
        # Admin Status Indicator
        if is_admin():
            admin_text = "🛡️ ADMIN MODE (High Support)"
            admin_color = COLOR_SUCCESS
        else:
            admin_text = "⚠️ STANDARD MODE (Limited Support - Recommend Run as Admin)"
            admin_color = COLOR_WARNING
            
        ctk.CTkLabel(f_foot, text=admin_text, font=("Tahoma", 10, "bold"), text_color=admin_color).pack(side="left", padx=10)

        self.lbl_status = ctk.CTkLabel(f_foot, text="พร้อมทำงาน", font=("Tahoma", 10))
        self.lbl_status.pack(side="right", padx=20)
        
        self.btn_check_update = ctk.CTkButton(f_foot, text="🔄 เช็คอัปเดต", font=("Tahoma", 10, "bold"), 
            fg_color="transparent", hover_color=COLOR_CARD, text_color=COLOR_ACCENT, width=100, height=28,
            command=lambda: threading.Thread(target=self.check_for_updates, args=(False,), daemon=True).start())
        self.btn_check_update.pack(side="right", padx=5)

    def reset_target_window(self):
        self.target_hwnd = None
        self.target_title = "ทั้งหน้าจอ (Global)"
        self.lbl_target.configure(text=f"เป้าหมาย: {self.target_title}")
        self.auto_save_presets()
        self.lbl_status.configure(text="รีเซ็ตเป้าหมายเป็น 'ทั้งหน้าจอ' เรียบร้อย", text_color=COLOR_MUTED)

    # --- Methods moved from Mixins for better coupling ---
    def pick_target_window(self):
        self.lbl_status.configure(text="โหมดเลือกหน้าต่าง: หน้าจอจะมืดลง คลิกที่หน้าต่างที่ต้องการ...", text_color="#d35400")
        self.withdraw()
        overlay = ctk.CTkToplevel(self)
        overlay.attributes('-fullscreen', True, '-alpha', 0.3, '-topmost', True)
        overlay.configure(fg_color="black", cursor="hand2")
        
        def on_click(event):
            x, y = win32api.GetCursorPos()
            overlay.destroy()
            self.deiconify()
            hwnd = win32gui.WindowFromPoint((x, y))
            root = hwnd
            while True:
                try:
                    p = win32gui.GetParent(root)
                    if not p: break
                    root = p
                except: break
            self.target_hwnd = root
            t = win32gui.GetWindowText(root)
            self.target_title = t if t else f"ID: {root}"
            self.lbl_target.configure(text=f"เป้าหมาย: {self.target_title}")
            self.auto_save_presets()
            self.lbl_status.configure(text=f"ล็อคเป้าหมาย: {self.target_title}", text_color=COLOR_MUTED)

        overlay.bind("<Button-1>", on_click)
        overlay.bind("<Escape>", lambda e: [overlay.destroy(), self.deiconify()])
        overlay.focus_force()

if __name__ == "__main__":
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1) # PROCESS_SYSTEM_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    app = AutoMationApp()
    app.mainloop()
