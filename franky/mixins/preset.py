"""
PresetMixin - Handles preset loading, saving, and switching
"""
import json
import os
from tkinter import filedialog, messagebox


class PresetMixin:
    """Handles preset loading, saving, and switching"""
    
    def create_default_preset(self):
        """Create initial default preset"""
        self.presets = [{
            "name": "ชุดที่ 1",
            "hotkey": None,
            "actions": [],
            "loop_count": 1,
            "target_hwnd": None,
            "target_title": "ทั้งหน้าจอ (Global)"
        }]
        self.current_preset_index = 0

    def get_current_preset(self):
        """Get the currently selected preset"""
        if 0 <= self.current_preset_index < len(self.presets):
            return self.presets[self.current_preset_index]
        return None

    def save_current_to_preset(self):
        """Save current UI state to preset"""
        preset = self.get_current_preset()
        if preset:
            preset["actions"] = self.actions.copy()
            preset["target_hwnd"] = self.target_hwnd
            preset["target_title"] = self.target_title
            try:
                preset["loop_count"] = int(self.entry_loop.get())
            except:
                preset["loop_count"] = 1
            
            # Stealth Settings
            preset["stealth_move"] = self.var_stealth_move.get()
            preset["stealth_jitter"] = self.var_stealth_jitter.get()
            preset["stealth_jitter_radius"] = self.var_stealth_jitter_radius.get()
            preset["stealth_timing"] = self.var_stealth_timing.get()
            preset["stealth_timing_val"] = self.var_stealth_timing_val.get()

    def load_preset_to_ui(self, index):
        """Load preset data to UI"""
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
        """Update preset dropdown and name entry"""
        if not self.presets:
            return
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
        """Save all presets to file"""
        save_data = []
        for preset in self.presets:
            p = preset.copy()
            p["target_hwnd"] = None  # Don't save window handles
            save_data.append(p)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

    def load_presets_logic(self, filepath, is_startup=False):
        """Load presets from file"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if loaded and isinstance(loaded, list):
                self.presets = loaded
                self.current_preset_index = 0
                self.load_preset_to_ui(0)
                self.update_preset_ui()
                self.preload_images()
                msg = f"โหลดแล้ว: {len(self.presets)} ชุด"
                self.lbl_status.configure(text=msg, text_color="#27ae60")
        except:
            pass

    def add_new_preset(self):
        """Create a new preset"""
        self.save_current_to_preset()
        new_idx = len(self.presets) + 1
        new_p = {
            "name": f"ชุดที่ {new_idx}",
            "hotkey": None,
            "actions": [],
            "loop_count": 1,
            "target_hwnd": None,
            "target_title": "ทั้งหน้าจอ (Global)"
        }
        self.presets.append(new_p)
        self.current_preset_index = len(self.presets) - 1
        self.load_preset_to_ui(self.current_preset_index)
        self.update_preset_ui()
        self.auto_save_presets()
        self.lbl_status.configure(text=f"สร้างชุดใหม่: {new_p['name']}", text_color="#27ae60")

    def delete_current_preset(self):
        """Delete current preset"""
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
        """Handle preset dropdown change"""
        self.save_current_to_preset()
        for i, p in enumerate(self.presets):
            if p["name"] == selected_name:
                self.current_preset_index = i
                self.load_preset_to_ui(i)
                self.update_preset_ui()
                break

    def on_preset_name_changed(self, event=None):
        """Handle preset name change"""
        p = self.get_current_preset()
        if p:
            new_name = self.entry_preset_name.get().strip()
            if new_name:
                p["name"] = new_name
                self.update_preset_ui()
                self.auto_save_presets()

    def start_change_preset_hotkey(self):
        """Start recording preset hotkey"""
        self.recording_state = "preset_hotkey"
        self.waiting_for_preset_key = self.current_preset_index
        self.recorded_keys = set()
        self.lbl_preset_hotkey.configure(text="[ กดปุ่ม... ]", text_color="#e74c3c")
        self.lbl_status.configure(text="กรุณากดปุ่มที่ต้องการตั้งเป็นปุ่มลัดสำหรับชุดนี้...", text_color="#e67e22")
        self.focus()

    def save_presets_to_file(self):
        """Save presets to user-selected file"""
        self.save_current_to_preset()
        try:
            path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("ไฟล์ JSON", "*.json")],
                initialfile="presets.json"
            )
            if path:
                self.save_presets_logic(path)
                self.lbl_status.configure(text=f"บันทึกแล้ว: {os.path.basename(path)}", text_color="#27ae60")
        except:
            pass

    def auto_save_presets(self):
        """Auto-save presets to default file"""
        self.save_current_to_preset()
        self.save_presets_logic(self.presets_file)

    def load_presets_from_file(self):
        """Load presets from user-selected file"""
        try:
            path = filedialog.askopenfilename(filetypes=[("ไฟล์ JSON", "*.json")])
            if path:
                self.load_presets_logic(path)
        except:
            pass

    def run_preset(self, index):
        """Run a specific preset"""
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
        """Load presets when app starts"""
        if os.path.exists(self.presets_file):
            self.load_presets_logic(self.presets_file, is_startup=True)
