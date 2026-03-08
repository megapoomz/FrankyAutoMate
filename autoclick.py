import sys
import os
import threading
from pathlib import Path
import logging
import ctypes

# DPI awareness moved exclusively to main.py to avoid duplicate calls.
# When running autoclick.py directly (dev mode), main.py should be the entry point.

import customtkinter as ctk
import win32gui

# Core & Utils
from core.constants import (
    APP_VERSION,
    GITHUB_API_URL,
    SCREENSHOT_CACHE_TTL,
    COLOR_BG,
    COLOR_CARD,
    COLOR_INNER,
    COLOR_ACCENT,
    COLOR_SUCCESS,
    COLOR_DANGER,
    COLOR_WARNING,
    COLOR_MUTED,
    GRADIENT_START,
    BORDER_COLOR,
)
from utils.win32_input import is_admin

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

class AutoMationApp(
    ctk.CTk,
    HotkeyMixin,
    PresetMixin,
    EngineMixin,
    ActionMixin,
    LogicMixin,
    VisionMixin,
    VariablesMixin,
    PickerMixin,
    StealthMixin,
    TabsMixin,
    UIMixin,
):
    """
    Mixin Dependency Graph
    ─────────────────────────────────
    Each mixin uses self.xxx to access attributes defined in other mixins.
    The dependency flow (→ means "depends on") is:

    EngineMixin    → UIMixin (log_message, safe_update_ui, highlight_action)
                   → StealthMixin (stealth_on_run_start/stop)
                   → PickerMixin (implicit: picked coords)
    ActionMixin    → UIMixin (update_list_display, auto_save_presets)
    LogicMixin     → UIMixin + ActionMixin (add_action_item, refresh_label_dropdowns)
    TabsMixin      → ActionMixin + PickerMixin (add_action_item, picks)
    VisionMixin    → ActionMixin + TabsMixin (add_action_item, tab references)
    VariablesMixin → ActionMixin (add_action_item)
    PickerMixin    → UIMixin (lbl_status)
    PresetMixin    → UIMixin + ActionMixin (UI updates, actions management)
    HotkeyMixin    → EngineMixin + PresetMixin (run/stop, preset switching)
    StealthMixin   → ctk.CTk (title, iconify, deiconify)

    Type safety: see core/protocols.py for AppProtocol
    """
    def __init__(self):
        super().__init__()

        self.actions: list[dict] = []
        self.actions_lock = threading.Lock()  # Protects self.actions between UI and bg threads
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
        self.picked_x_raw = 0
        self.picked_y_raw = 0
        self.picked_rel_x = 0
        self.picked_rel_y = 0
        self.is_relative = False
        self._last_status_update = 0.0
        self.current_region = None
        self.current_color_data = None
        self.last_child_hwnd = None  # Track last child HWND for background actions

        self._held_keys_lock = threading.Lock()

        self._pending_after_ids = []

        self.toggle_key = "f6"
        self.held_keys = set()
        self.recorded_keys = set()
        self.recording_state = None
        self.current_recorded_str = ""
        self.waiting_for_preset_key = None
        self.current_preset_index = 0

        self.perf_metrics = {"start_time": 0, "actions_exec": []}
        self.screenshot_cache = None
        self.screenshot_cache_time = 0
        self.screenshot_cache_ttl = SCREENSHOT_CACHE_TTL  # Use centralized constant
        self._screenshot_gray_cache = None
        self._screenshot_lock = threading.Lock()  # Protects screenshot cache across threads
        self.sct = None  # Initialized in bg_runner thread

        self.var_stealth_move = ctk.BooleanVar(value=False)
        self.var_stealth_jitter = ctk.BooleanVar(value=False)
        self.var_stealth_jitter_radius = ctk.DoubleVar(value=3.0)
        self.var_stealth_timing = ctk.BooleanVar(value=False)
        self.var_stealth_timing_val = ctk.DoubleVar(value=0.2)
        self.var_stealth_hide_window = ctk.BooleanVar(value=False)
        self.var_stealth_random_title = ctk.BooleanVar(value=False)
        self.var_stealth_sendinput = ctk.BooleanVar(value=False)
        self.var_img_conf = ctk.DoubleVar(value=0.75)
        self.var_logic_conf = ctk.DoubleVar(value=0.75)
        self.original_title = f"Franky AutoMate v{APP_VERSION}"

        self.var_dry_run = ctk.BooleanVar(value=False)
        self.var_step_mode = ctk.BooleanVar(value=False)
        self.var_debug_mode = ctk.BooleanVar(value=False)
        self.var_follow_window = ctk.BooleanVar(value=False)

        self.variables = {}
        # Must be RLock (reentrant) because _execute_var_set/math
        # hold this lock while calling _resolve_value which also acquires it
        self.variable_lock = threading.RLock()

        # Path for presets — Path.home() fallback instead of os.getcwd()
        _appdata = os.getenv("APPDATA") or str(Path.home())
        appdata_dir = os.path.join(_appdata, "FrankyAutoMate")
        os.makedirs(appdata_dir, exist_ok=True)
        self.presets_file = os.path.join(appdata_dir, "presets.json")
        self.create_default_preset()

        self.after(100, self.launch_app)

    def launch_app(self):
        self.setup_ui()
        self.load_presets_on_startup()
        self.setup_hotkeys()
        self.protocol("WM_DELETE_WINDOW", self.on_app_close)
        self.deiconify()
        self.lbl_status.configure(text="ระบบพร้อมทำงาน", text_color=COLOR_SUCCESS)

        if not is_admin():
            from tkinter import messagebox

            self.after(
                500,
                lambda: messagebox.showwarning(
                    "คำเตือนสิทธิ์การใช้งาน (Admin Mode)",
                    "คุณไม่ได้เปิดโปรแกรมนี้ด้วยสิทธิ์แอดมิน (Run as administrator)\n\n"
                    "หากเป้าหมายของคุณคือหน้าจอเกมหรือโปรแกรมที่ใช้ระดับสิทธิ์สูง คำสั่งคลิกและพิมพ์อาจไม่ตอบสนอง\n"
                    "แนะนำให้ปิดแล้วเปิดใหม่โดยคลิกขวาเลือก Run as administrator",
                    parent=self,
                ),
            )
        # Auto-check for updates after 3 seconds
        self._pending_after_ids.append(self.after(3000, lambda: threading.Thread(target=self.check_for_updates, args=(True,), daemon=True).start()))
        
        self._start_listener_health_check()

    def on_app_close(self):
        """Cleanup resources before closing"""
        if self.is_running:
            self.stop_automation()
            t = getattr(self, "execution_thread", None)
            if t and t.is_alive():
                t.join(timeout=2)
        # Cancel all tracked timers; iterate a copy since cancel may modify list
        ids_to_cancel = list(getattr(self, "_pending_after_ids", []))
        for after_id in ids_to_cancel:
            try:
                self.after_cancel(after_id)
            except Exception:
                pass
        self._pending_after_ids.clear()
        if hasattr(self, "_auto_save_timer"):
            try:
                self.after_cancel(self._auto_save_timer)
            except Exception:
                pass
        self.last_child_hwnd = None
        # HIGH-04: Don't close sct here — bg_runner owns it and handles cleanup.
        # Just signal stop and let bg_runner's finally block close sct safely.
        if self.is_running:
            self.is_running = False
            # Give bg_runner a moment to stop and clean up sct
            if hasattr(self, 'execution_thread') and self.execution_thread and self.execution_thread.is_alive():
                self.execution_thread.join(timeout=1.0)
        if hasattr(self, "listener"):
            try:
                self.listener.stop()
            except Exception:
                pass
        self.destroy()

    def _start_listener_health_check(self):
        """Periodically check if pynput listener is still alive, restart if crashed."""

        def _check():
            listener = getattr(self, "listener", None)
            if listener and not listener.is_alive():
                logging.warning("Hotkey listener died, restarting...")
                try:
                    listener.stop()
                except Exception:
                    pass
                self.setup_hotkeys()
            self._cleanup_pending_afters()
            timer_id = self.after(30000, _check)  # Re-check every 30 seconds
            self._pending_after_ids.append(timer_id)

        timer_id = self.after(30000, _check)
        self._pending_after_ids.append(timer_id)

    def _track_after(self, delay_ms, callback, *args):
        """Wrapper for self.after() that tracks timer IDs for cleanup on close."""
        timer_id = self.after(delay_ms, callback, *args)
        self._pending_after_ids.append(timer_id)
        self._cleanup_pending_afters()
        return timer_id

    def _cleanup_pending_afters(self):
        """MED-01: Consolidated cleanup — evict old tracked timer IDs when list grows too large."""
        if len(self._pending_after_ids) > 100:
            old_ids = self._pending_after_ids[:-50]
            for old_id in old_ids:
                try:
                    self.after_cancel(old_id)
                except Exception:
                    pass
            self._pending_after_ids = self._pending_after_ids[-50:]

    def _cancel_timer(self, timer_id):
        """Cancel a specific after timer safely."""
        if timer_id is not None:
            try:
                self.after_cancel(timer_id)
            except Exception:
                pass

    def _validate_target_hwnd(self):
        """Verify target_hwnd still exists and title matches."""
        if self.target_hwnd:
            try:
                if not win32gui.IsWindow(self.target_hwnd):
                    self.target_hwnd = None
                    return False
                current_title = win32gui.GetWindowText(self.target_hwnd)
                if self.target_title and self.target_title != "ทั้งหน้าจอ (Global)":
                    if current_title and self.target_title not in current_title and current_title not in self.target_title:
                        logging.warning(f"Target HWND {self.target_hwnd} title changed: '{current_title}' != '{self.target_title}'")
                        self.target_hwnd = None
                        return False
            except Exception:
                self.target_hwnd = None
                return False
        return True

    def _add_section_divider(self, parent):
        """Visual separator between sections in combined tabs"""
        ctk.CTkFrame(parent, height=2, fg_color=BORDER_COLOR).pack(fill="x", padx=10, pady=15)

    def check_for_updates(self, silent=False):
        """Check GitHub Releases for new version. Runs in background thread."""
        try:
            def _set_btn(text, state):
                try:
                    if hasattr(self, 'btn_check_update') and self.btn_check_update.winfo_exists():
                        self.btn_check_update.configure(text=text, state=state)
                except Exception:
                    pass
            self.after(0, lambda: _set_btn("⏳ กำลังเช็ค...", "disabled"))

            import requests
            headers = {"User-Agent": "FrankyAutoMate-Updater"}
            resp = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            latest_tag = data.get("tag_name", "").lstrip("vV")
            changelog = data.get("body", "ไม่มีรายละเอียด")

            download_url = None
            for asset in data.get("assets", []):
                if asset["name"].endswith(".zip"):
                    url = asset["browser_download_url"]
                    
                    if url.startswith("https://"):
                        download_url = url
                    else:
                        self.log_message(f"[SEC] Rejected non-HTTPS download URL: {url}", "#f59e0b")
                    break

            def parse_ver(v):
                import re
                parts = v.split(".")
                result = []
                for x in parts:
                    digits = re.sub(r'[^0-9]', '', x)
                    if digits:
                        result.append(int(digits))
                return tuple(result) if result else (0,)

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
                        parent=self,
                    )
                    if answer:
                        UpdateProgressWindow(self, latest_tag, download_url)

                self.after(0, _show_update)
            elif not silent:
                self.after(0, lambda: self.lbl_status.configure(text=f"✅ ใช้เวอร์ชันล่าสุดแล้ว (v{APP_VERSION})", text_color=COLOR_SUCCESS))

        except Exception as e:
            if not silent:
                err_msg = str(e)
                self.after(0, lambda err=err_msg: self.lbl_status.configure(text=f"❌ เช็คอัปเดตไม่ได้: {err}", text_color=COLOR_DANGER))
        finally:
            self.after(0, lambda: _set_btn("🔄 เช็คอัปเดต", "normal"))

    def preload_images(self):
        """Preload image templates from all preset actions into cache (with size limit)"""
        # Concurrency guard — prevent overlapping preload threads
        if getattr(self, '_preload_running', False):
            return
        self._preload_running = True
        try:
            import cv2
            from core.constants import IMAGE_CACHE_MAX_SIZE

            with self.actions_lock:
                presets_snapshot = [p.get("actions", []) for p in self.presets]

            loaded = 0
            for actions in presets_snapshot:
                for action in actions:
                    
                    if len(self.image_cache) >= IMAGE_CACHE_MAX_SIZE:
                        return
                    path = action.get("path")
                    if path and path not in self.image_cache:
                        try:
                            img = cv2.imread(path)
                            if img is not None:
                                # HIGH-03: Use thread-safe pattern — dict assignment is atomic in CPython
                                # but check-then-set is not. Using simple assignment is safe enough
                                # since worst case is a redundant cv2.imread, not data corruption.
                                self.image_cache[path] = img
                                loaded += 1
                        except Exception:
                            pass
        except Exception as e:
            logging.warning(f"preload_images error: {e}")
        finally:
            self._preload_running = False

    def setup_ui(self):
        self.title(self.original_title)
        # Set window icon (title bar + taskbar)
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        self.geometry("1180x880")
        self.minsize(1100, 800)
        self.configure(fg_color=COLOR_BG)

        # Main Layout
        self.grid_columnconfigure(0, weight=1)  # List area
        self.grid_columnconfigure(1, weight=1)  # Tool area
        self.grid_rowconfigure(0, weight=1)

        # --- Left Panel: Action List ---
        f_left = ctk.CTkFrame(self, fg_color="transparent")
        f_left.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        # Header for Actions
        f_list_head = ctk.CTkFrame(f_left, fg_color="transparent")
        f_list_head.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(f_list_head, text="ลำดับขั้นตอน (AUTOMATION SCRIPT)", font=("Inter", 16, "bold"), text_color="white").pack(side="left")

        # Action Toolbar (Up/Down/Delete)
        f_tool_mini = ctk.CTkFrame(f_list_head, fg_color=COLOR_INNER, corner_radius=10, height=35)
        f_tool_mini.pack(side="right")
        ctk.CTkButton(
            f_tool_mini, text="ขึ้น", width=35, height=30, command=self.move_action_up, fg_color="transparent", hover_color=COLOR_INNER
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            f_tool_mini, text="ลง", width=35, height=30, command=self.move_action_down, fg_color="transparent", hover_color=COLOR_INNER
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            f_tool_mini, text="ลบ", width=35, height=30, command=self.remove_selected_action, fg_color="transparent", hover_color=COLOR_DANGER
        ).pack(side="left", padx=2)

        # List Scrollable
        self.scroll_actions = ctk.CTkScrollableFrame(f_left, fg_color="#020617", border_width=1, border_color=BORDER_COLOR, corner_radius=15)
        self.scroll_actions.pack(fill="both", expand=True)

        # Execution Panel (Below Action List on Left Side)
        self.setup_execution_panel(f_left)

        # --- Right Panel: Tools & Config ---
        f_right = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=20, border_width=1, border_color=BORDER_COLOR)
        f_right.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=20)

        # TARGET + PRESETS: Pinned at bottom of right panel (always visible)
        self.setup_bottom_panels(f_right)

        # SCROLLABLE TABS: Fill remaining space above the pinned panels
        self.scroll_right = ctk.CTkScrollableFrame(f_right, fg_color="transparent", corner_radius=0)
        self.scroll_right.pack(fill="both", expand=True, padx=5, pady=(5, 0))

        # Tabs for actions (Inside scrollable)
        self.tabs = ctk.CTkTabview(
            self.scroll_right,
            fg_color="transparent",
            segmented_button_selected_color=COLOR_ACCENT,
            segmented_button_unselected_color="#1e293b",
            segmented_button_fg_color="#0f172a",
        )
        # Custom font for tab buttons
        self.tabs._segmented_button.configure(font=("Inter", 11, "bold"))
        self.tabs.pack(fill="x", padx=5, pady=5)

        # === 5 Combined Tabs (simplified from 10) ===
        tab_action = self.tabs.add("คลิก/ค้นหา")
        tab_input = self.tabs.add("พิมพ์/รอ")
        tab_logic_main = self.tabs.add("เงื่อนไข")
        self.tab_stealth = self.tabs.add("ซ่อนตัว")
        self.tab_log = self.tabs.add("บันทึก")

        self.tab_click = tab_action
        self.tab_image = tab_action
        self.tab_color = tab_action
        self.tab_vision = tab_action
        self.tab_type = tab_input
        self.tab_wait = tab_input
        self.tab_vars = tab_logic_main
        self.tab_logic = tab_logic_main

        # --- 🎯 Action Tab: Mouse + Image + Color + OCR ---
        self.setup_click_tab()
        self._add_section_divider(tab_action)
        self.setup_image_tab()
        self._add_section_divider(tab_action)
        self.setup_color_tab()
        self._add_section_divider(tab_action)
        self.setup_vision_tab()

        # --- ⌨️ Input Tab: Type/Hotkey + Wait ---
        self.setup_type_tab()
        self._add_section_divider(tab_input)
        self.setup_wait_tab()

        # --- 🔀 Logic Tab: Labels/If/Jump + Variables ---
        self.setup_logic_tab()
        self._add_section_divider(tab_logic_main)
        self.setup_vars_tab()

        # --- Standalone Tabs ---
        self.setup_stealth_tab()
        self.setup_log_tab()

        # Footer
        self.setup_footer()
        self.update_list_display()

    def setup_bottom_panels(self, parent):
        f_bot = ctk.CTkFrame(parent, fg_color="transparent")
        f_bot.pack(fill="x", side="bottom", padx=10, pady=(5, 10))

        # Target Window Frame
        f_target = ctk.CTkFrame(f_bot, fg_color=COLOR_INNER, corner_radius=15, border_width=1, border_color=BORDER_COLOR)
        f_target.pack(fill="x", pady=(0, 10))

        f_t_head = ctk.CTkFrame(f_target, fg_color="transparent")
        f_t_head.pack(fill="x", padx=15, pady=(12, 5))
        ctk.CTkLabel(f_t_head, text="เป้าหมาย (TARGET WINDOW)", font=("Inter", 11, "bold"), text_color=COLOR_ACCENT).pack(side="left")

        self.lbl_target = ctk.CTkLabel(f_target, text=f"เป้าหมาย: {self.target_title}", font=("Inter", 12))
        self.lbl_target.pack(pady=5)

        f_t_btn = ctk.CTkFrame(f_target, fg_color="transparent")
        f_t_btn.pack(pady=(0, 5))
        ctk.CTkButton(f_t_btn, text="ล็อคหน้าต่าง", command=self.pick_target_window, width=120, height=32, font=("Inter", 11, "bold")).pack(
            side="left", padx=5
        )
        ctk.CTkButton(f_t_btn, text="รีเซ็ต", command=self.reset_target_window, width=100, height=32, fg_color="#334155", font=("Inter", 11)).pack(
            side="left", padx=5
        )

        self.cb_follow = ctk.CTkCheckBox(
            f_target, text="ติดตามหน้าต่างอัตโนมัติ (Follow Window)", variable=self.var_follow_window, font=("Inter", 11)
        )
        self.cb_follow.pack(pady=(0, 10))

        # Preset Frame
        f_preset = ctk.CTkFrame(f_bot, fg_color=COLOR_INNER, corner_radius=15, border_width=1, border_color=BORDER_COLOR)
        f_preset.pack(fill="x", pady=(0, 10))

        f_pre_head = ctk.CTkFrame(f_preset, fg_color="transparent")
        f_pre_head.pack(fill="x", padx=15, pady=(12, 5))
        ctk.CTkLabel(f_pre_head, text="คลังชุดคำสั่ง (PRESETS)", font=("Inter", 11, "bold"), text_color=COLOR_ACCENT).pack(side="left")
        ctk.CTkButton(f_pre_head, text="บันทึกไฟล์", width=80, height=24, font=("Inter", 10), command=self.save_presets_to_file).pack(
            side="right", padx=5
        )
        ctk.CTkButton(f_pre_head, text="โหลดไฟล์", width=80, height=24, font=("Inter", 10), command=self.load_presets_from_file).pack(side="right")

        f_pre_name = ctk.CTkFrame(f_preset, fg_color="transparent")
        f_pre_name.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(f_pre_name, text="ชื่อชุด:", font=("Inter", 11)).pack(side="left", padx=(0, 5))
        self.entry_preset_name = ctk.CTkEntry(f_pre_name, height=28, font=("Inter", 11))
        self.entry_preset_name.pack(side="left", fill="x", expand=True)
        self.entry_preset_name.bind("<KeyRelease>", self.on_preset_name_changed)

        f_pre_row = ctk.CTkFrame(f_preset, fg_color="transparent")
        f_pre_row.pack(fill="x", padx=15, pady=(0, 12))
        self.preset_dropdown = ctk.CTkOptionMenu(
            f_pre_row, values=["ชุดที่ 1"], command=self.on_preset_changed, fg_color=COLOR_CARD, button_color=COLOR_INNER
        )
        self.preset_dropdown.pack(side="left", fill="x", expand=True)
        self.lbl_preset_hotkey = ctk.CTkLabel(f_pre_row, text="[ - ]", font=("JetBrains Mono", 11, "bold"), text_color=COLOR_ACCENT)
        self.lbl_preset_hotkey.pack(side="left", padx=5)
        ctk.CTkButton(f_pre_row, text="ตั้งปุ่ม", width=55, command=self.start_change_preset_hotkey).pack(side="left", padx=2)
        ctk.CTkButton(f_pre_row, text="เพิ่ม", width=45, command=self.add_new_preset).pack(side="left", padx=2)
        ctk.CTkButton(
            f_pre_row, text="ก็อบ", width=45, command=self.duplicate_current_preset, fg_color=COLOR_ACCENT, hover_color=GRADIENT_START
        ).pack(side="left", padx=2)
        ctk.CTkButton(f_pre_row, text="ลบ", width=40, command=self.delete_current_preset, fg_color=COLOR_DANGER).pack(side="left", padx=2)

    def setup_execution_panel(self, parent):
        """Execution controls - placed on the left side below the action list"""
        f_run = ctk.CTkFrame(parent, fg_color=COLOR_INNER, corner_radius=15, border_width=1, border_color=BORDER_COLOR)
        f_run.pack(fill="x", pady=(15, 0))

        f_run_head = ctk.CTkFrame(f_run, fg_color="transparent")
        f_run_head.pack(fill="x", padx=15, pady=(12, 8))
        ctk.CTkLabel(f_run_head, text="เริ่มทำงาน (EXECUTION)", font=("Inter", 11, "bold"), text_color=COLOR_SUCCESS).pack(side="left")
        self.lbl_hotkey = ctk.CTkLabel(f_run_head, text="[ F6 ]", font=("JetBrains Mono", 11, "bold"), text_color=COLOR_ACCENT)
        self.lbl_hotkey.pack(side="right")
        self.lbl_hotkey.bind("<Button-1>", lambda e: self.start_change_hotkey())

        f_loop = ctk.CTkFrame(f_run, fg_color="transparent")
        f_loop.pack(fill="x", padx=15)
        ctk.CTkLabel(f_loop, text="ทำกี่รอบ (0=ตลอดไป):", font=("Inter", 12)).pack(side="left")
        self.entry_loop = ctk.CTkEntry(f_loop, width=70, height=30, justify="center", font=("JetBrains Mono", 12))
        self.entry_loop.insert(0, "1")
        self.entry_loop.pack(side="left", padx=10)
        self.entry_loop.bind("<KeyRelease>", lambda e: self.auto_save_presets())

        f_opt = ctk.CTkFrame(f_run, fg_color="transparent")
        f_opt.pack(fill="x", padx=15, pady=5)
        ctk.CTkCheckBox(f_opt, text="จำลอง (Dry Run)", variable=self.var_dry_run, font=("Inter", 11)).pack(side="left", padx=5)
        ctk.CTkCheckBox(f_opt, text="ทำทีละขั้น (Step Mode)", variable=self.var_step_mode, font=("Inter", 11)).pack(side="left", padx=5)

        self.btn_run = ctk.CTkButton(
            f_run,
            text="เริ่มทำงาน (Global Start)",
            command=self.run_automation,
            fg_color=COLOR_SUCCESS,
            hover_color="#059669",
            height=45,
            font=("Inter", 14, "bold"),
        )
        self.btn_run.pack(fill="x", padx=15, pady=(5, 15))

    def setup_footer(self):
        f_foot = ctk.CTkFrame(self, fg_color=COLOR_INNER, height=40, corner_radius=0)
        f_foot.grid(row=1, column=0, columnspan=2, sticky="ew")

        ctk.CTkLabel(f_foot, text=f"FrankyAutoMate v{APP_VERSION} Premium", font=("Inter", 10, "bold"), text_color="#475569").pack(
            side="left", padx=20
        )

        # Admin Status Indicator
        if is_admin():
            admin_text = "🛡️ ADMIN MODE (High Support)"
            admin_color = COLOR_SUCCESS
        else:
            admin_text = "⚠️ STANDARD MODE (Limited Support - Recommend Run as Admin)"
            admin_color = COLOR_WARNING

        ctk.CTkLabel(f_foot, text=admin_text, font=("Inter", 10, "bold"), text_color=admin_color).pack(side="left", padx=10)

        self.lbl_status = ctk.CTkLabel(f_foot, text="พร้อมทำงาน", font=("Inter", 10))
        self.lbl_status.pack(side="right", padx=20)

        self.btn_check_update = ctk.CTkButton(
            f_foot,
            text="🔄 เช็คอัปเดต",
            font=("Inter", 10, "bold"),
            fg_color="transparent",
            hover_color=COLOR_CARD,
            text_color=COLOR_ACCENT,
            width=100,
            height=28,
            command=lambda: threading.Thread(target=self.check_for_updates, args=(False,), daemon=True).start(),
        )
        self.btn_check_update.pack(side="right", padx=5)

    def reset_target_window(self):
        self.target_hwnd = None
        self.target_title = "ทั้งหน้าจอ (Global)"
        self.last_child_hwnd = None
        self.lbl_target.configure(text=f"เป้าหมาย: {self.target_title}")
        self.auto_save_presets()
        self.lbl_status.configure(text="รีเซ็ตเป้าหมายเป็น 'ทั้งหน้าจอ' เรียบร้อย", text_color=COLOR_MUTED)

    # --- Methods moved from Mixins for better coupling ---
    def pick_target_window(self):
        self.lbl_status.configure(text="โหมดเลือกหน้าต่าง: หน้าจอจะมืดลง คลิกที่หน้าต่างที่ต้องการ...", text_color="#d35400")
        self.withdraw()
        overlay = ctk.CTkToplevel(self)
        overlay.attributes("-fullscreen", True, "-alpha", 0.3, "-topmost", True)
        overlay.configure(fg_color="black", cursor="hand2")

        _overlay_timer_holder = [None]

        def on_click(event):
            x, y = event.x_root, event.y_root
            if _overlay_timer_holder[0] is not None:
                try:
                    self.after_cancel(_overlay_timer_holder[0])
                except Exception:
                    pass
            overlay.destroy()
            self.deiconify()
            hwnd = win32gui.WindowFromPoint((x, y))
            root = hwnd
            while True:
                try:
                    p = win32gui.GetParent(root)
                    if not p:
                        break
                    root = p
                except Exception:
                    break
            self.target_hwnd = root
            self.last_child_hwnd = None
            t = win32gui.GetWindowText(root)
            self.target_title = t if t else f"ID: {root}"
            self.lbl_target.configure(text=f"เป้าหมาย: {self.target_title}")
            self.auto_save_presets()
            self.lbl_status.configure(text=f"ล็อคเป้าหมาย: {self.target_title}", text_color=COLOR_MUTED)

        overlay.bind("<Button-1>", on_click)
        # MED-07: Cancel overlay timer on Escape to prevent stale timer callbacks
        overlay.bind("<Escape>", lambda e: [self._cancel_timer(_overlay_timer_holder[0]), overlay.destroy(), self.deiconify()])

        def _auto_close_overlay():
            try:
                if overlay.winfo_exists():
                    overlay.destroy()
                    self.deiconify()
            except Exception:
                pass

        _overlay_timer = self.after(30000, _auto_close_overlay)
        _overlay_timer_holder[0] = _overlay_timer
        self._pending_after_ids.append(_overlay_timer)

        def _focus_target():
            overlay.lift()
            overlay.focus_force()
            overlay.grab_set()

        self.after(100, _focus_target)

if __name__ == "__main__":
    # Enable DPI awareness when running autoclick.py directly (dev mode)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    app = AutoMationApp()
    app.mainloop()
