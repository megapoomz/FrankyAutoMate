import json
import os
import copy
import logging
import threading
import win32gui
from tkinter import filedialog, messagebox
from core.constants import COLOR_SUCCESS, AUTO_SAVE_DEBOUNCE_MS

class PresetMixin:
    """Handles preset loading, saving, and switching"""

    def create_default_preset(self):
        self.presets = [
            {"name": "ชุดที่ 1", "hotkey": None, "actions": [], "loop_count": 1, "target_hwnd": None, "target_title": "ทั้งหน้าจอ (Global)"}
        ]

    def get_current_preset(self):
        if 0 <= self.current_preset_index < len(self.presets):
            return self.presets[self.current_preset_index]
        return None

    def save_current_to_preset(self):
        preset = self.get_current_preset()
        if preset:
            with self.actions_lock:
                preset["actions"] = copy.deepcopy(self.actions)
            preset["target_hwnd"] = self.target_hwnd
            preset["target_title"] = self.target_title
            try:
                preset["loop_count"] = int(self.entry_loop.get())
            except (ValueError, TypeError):
                preset["loop_count"] = 1

            # Stealth Settings
            preset["stealth_move"] = self.var_stealth_move.get()
            preset["stealth_jitter"] = self.var_stealth_jitter.get()
            preset["stealth_jitter_radius"] = self.var_stealth_jitter_radius.get()
            preset["stealth_timing"] = self.var_stealth_timing.get()
            preset["stealth_timing_val"] = self.var_stealth_timing_val.get()
            # Also save hide_window and random_title stealth settings
            preset["stealth_hide_window"] = self.var_stealth_hide_window.get()
            preset["stealth_random_title"] = self.var_stealth_random_title.get()
            # Save additional settings that were missing
            preset["stealth_sendinput"] = self.var_stealth_sendinput.get()
            if hasattr(self, "var_follow_window"):
                preset["follow_window"] = self.var_follow_window.get()
            if hasattr(self, "var_debug_mode"):
                preset["debug_mode"] = self.var_debug_mode.get()
            if hasattr(self, "var_dry_run"):
                preset["dry_run"] = self.var_dry_run.get()

    def load_preset_to_ui(self, index):
        if 0 <= index < len(self.presets):
            # Clear old cache to save memory
            self.image_cache.clear()

            preset = self.presets[index]
            with self.actions_lock:
                # Use deepcopy to prevent shared mutation between preset and live actions
                self.actions = copy.deepcopy(preset.get("actions", []))
            self.target_hwnd = preset.get("target_hwnd")
            self.target_title = preset.get("target_title", "ทั้งหน้าจอ (Global)")

            # --- Restoration Logic: Try to find HWND by Title if missing ---
            if not self.target_hwnd and self.target_title != "ทั้งหน้าจอ (Global)":

                def find_it(hwnd, ctx):
                    if win32gui.IsWindowVisible(hwnd) and self.target_title in win32gui.GetWindowText(hwnd):
                        self.target_hwnd = hwnd
                        return False  # Stop enumeration
                    return True

                try:
                    win32gui.EnumWindows(find_it, None)
                except Exception:
                    pass

            self.lbl_target.configure(text=f"เป้าหมาย: {self.target_title}")
            self.entry_loop.delete(0, "end")
            self.entry_loop.insert(0, str(preset.get("loop_count", 1)))

            # Restore Stealth Settings
            self.var_stealth_move.set(preset.get("stealth_move", False))
            self.var_stealth_jitter.set(preset.get("stealth_jitter", False))
            self.var_stealth_jitter_radius.set(preset.get("stealth_jitter_radius", 3.0))
            self.var_stealth_timing.set(preset.get("stealth_timing", False))
            self.var_stealth_timing_val.set(preset.get("stealth_timing_val", 0.2))
            # Restore hide_window and random_title stealth settings
            self.var_stealth_hide_window.set(preset.get("stealth_hide_window", False))
            self.var_stealth_random_title.set(preset.get("stealth_random_title", False))
            # Restore additional settings
            self.var_stealth_sendinput.set(preset.get("stealth_sendinput", False))
            if hasattr(self, "var_follow_window"):
                self.var_follow_window.set(preset.get("follow_window", False))
            if hasattr(self, "var_debug_mode"):
                self.var_debug_mode.set(preset.get("debug_mode", False))
            if hasattr(self, "var_dry_run"):
                self.var_dry_run.set(preset.get("dry_run", False))

            self.update_list_display()

    def update_preset_ui(self):
        if not self.presets:
            return
        names = [p["name"] for p in self.presets]
        self.preset_dropdown.configure(values=names)
        preset = self.get_current_preset()
        if preset:
            self.preset_dropdown.set(preset["name"])
            # Only update entry if not focused to avoid cursor jumping
            if self.focus_get() != self.entry_preset_name:
                self.entry_preset_name.delete(0, "end")
                self.entry_preset_name.insert(0, preset["name"])
            hotkey = preset.get("hotkey")
            self.lbl_preset_hotkey.configure(text=f"[ {hotkey} ]" if hotkey else "[ - ]")

    def save_presets_logic(self, filepath):
        save_data = []
        for preset in self.presets:
            # R4-01: Use deepcopy to prevent shared mutation with live preset data
            p = copy.deepcopy(preset)
            p["target_hwnd"] = None
            save_data.append(p)

        # Use DPAPI encryption if available, with plaintext fallback
        try:
            from utils.security import save_config_secure
            save_config_secure({"presets": save_data}, filepath)
        except ImportError:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

    def load_presets_logic(self, filepath, is_startup=False):
        try:
            # Try DPAPI-encrypted format first, fallback to legacy plaintext
            loaded = None
            try:
                from utils.security import load_config_secure
                raw = load_config_secure(filepath)
                if isinstance(raw, dict) and "presets" in raw:
                    loaded = raw["presets"]
                elif isinstance(raw, list):
                    loaded = raw  # Legacy plaintext format loaded via secure loader
            except ImportError:
                pass

            # Fallback: direct JSON load (legacy plaintext)
            if loaded is None:
                with open(filepath, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict) and "presets" in raw:
                    loaded = raw["presets"]
                elif isinstance(raw, list):
                    loaded = raw

            if loaded and isinstance(loaded, list):
                self.presets = loaded
                self.current_preset_index = 0
                self.load_preset_to_ui(0)
                self.update_preset_ui()
                # Only call preload_images if the method exists
                if hasattr(self, "preload_images"):
                    threading.Thread(target=self.preload_images, daemon=True).start()
                msg = f"โหลดแล้ว: {len(self.presets)} ชุด"
                self.lbl_status.configure(text=msg, text_color="#27ae60")
        except Exception as e:
            # Report load errors to user instead of silently swallowing
            if not is_startup:
                logging.warning(f"Load Error: {e}")
                try:
                    self.lbl_status.configure(text=f"โหลดไฟล์ล้มเหลว: {e}", text_color="#e74c3c")
                except Exception:
                    pass

    def add_new_preset(self):
        self.save_current_to_preset()
        new_idx = len(self.presets) + 1
        new_p = {
            "name": f"ชุดที่ {new_idx}",
            "hotkey": None,
            "actions": [],
            "loop_count": 1,
            "target_hwnd": None,
            "target_title": "ทั้งหน้าจอ (Global)",
        }
        self.presets.append(new_p)
        self.current_preset_index = len(self.presets) - 1
        self.load_preset_to_ui(self.current_preset_index)
        self.update_preset_ui()
        self.auto_save_presets()
        self.lbl_status.configure(text=f"สร้างชุดใหม่: {new_p['name']}", text_color=COLOR_SUCCESS)

    def duplicate_current_preset(self):
        """Duplicate existing preset with all its actions and settings"""
        self.save_current_to_preset()
        curr_p = self.get_current_preset()
        if not curr_p:
            return

        # Use deepcopy instead of json.dumps/loads to preserve Python types
        # (json converts tuples to lists, breaking RGB tuple comparisons)
        new_p = copy.deepcopy(curr_p)
        new_p["name"] = f"{curr_p['name']} (ก๊อปปี้)"
        new_p["hotkey"] = None  # Reset hotkey for the copy
        new_p["target_hwnd"] = None  # Reset transient handle

        self.presets.append(new_p)
        self.current_preset_index = len(self.presets) - 1
        self.load_preset_to_ui(self.current_preset_index)
        self.update_preset_ui()
        self.auto_save_presets()
        self.lbl_status.configure(text=f"ก็อบปี้ชุดคำสั่ง: {new_p['name']}", text_color=COLOR_SUCCESS)

    def delete_current_preset(self):
        if len(self.presets) <= 1:
            messagebox.showwarning("แจ้งเตือน", "ต้องมีอย่างน้อย 1 ชุดคำสั่ง", parent=self)
            return
        p = self.get_current_preset()
        if messagebox.askyesno("ยืนยันลบ", f"ลบชุด '{p['name']}' ?", parent=self):
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
                # Clear stale child handle from previous preset's target
                self.last_child_hwnd = None
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
        except Exception:
            pass

    def auto_save_presets(self):
        # Debounce: only save once per 1000ms even if called rapidly (PERF-2: increased from 500ms)
        if hasattr(self, "_auto_save_timer"):
            try:
                self.after_cancel(self._auto_save_timer)
            except Exception:
                pass
        self._auto_save_timer = self.after(AUTO_SAVE_DEBOUNCE_MS, self._do_auto_save)

    def _do_auto_save(self):
        try:
            self.save_current_to_preset()
            self.save_presets_logic(self.presets_file)
        except Exception as e:
            logging.warning(f"Auto-save failed: {e}")

    def load_presets_from_file(self):
        try:
            path = filedialog.askopenfilename(filetypes=[("ไฟล์ JSON", "*.json")])
            if path:
                self.load_presets_logic(path)
        except Exception:
            pass

    def run_preset(self, index):
        if self.is_running:
            return
        self.save_current_to_preset()
        self.current_preset_index = index
        self.load_preset_to_ui(index)
        self.update_preset_ui()
        p = self.get_current_preset()
        if p:
            self.log_message(f"เริ่มทำงานชุด: {p['name']}")
        self.run_automation()

    def load_presets_on_startup(self):
        if os.path.exists(self.presets_file):
            self.load_presets_logic(self.presets_file, is_startup=True)
