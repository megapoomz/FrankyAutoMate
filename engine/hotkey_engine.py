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

    def setup_hotkeys(self):
        """Build and Start Global Hotkey Engine"""
        from pynput import keyboard as pynput_keyboard
        self.listener = pynput_keyboard.Listener(on_press=self.on_global_hotkey, on_release=self.on_global_release)
        self.listener.daemon = True
        self.listener.start()
