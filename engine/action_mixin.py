import os
from typing import Dict, Any
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pyautogui


class ActionMixin:
    """Handles adding and managing actions in the script"""

    def add_action_item(self, action_data: Dict[str, Any]) -> None:
        with self.actions_lock:
            self.actions.append(action_data)
        self.update_list_display()
        self.auto_save_presets()

    def clear_actions(self) -> None:
        if self.actions:
            if messagebox.askyesno("ยืนยัน", "ลบคำสั่งทั้งหมด?", parent=self):
                with self.actions_lock:
                    self.actions.clear()
                self.selected_index = -1
                self.update_list_display()
                self.auto_save_presets()

    def move_action_up(self) -> None:
        idx = getattr(self, "selected_index", -1)
        if idx > 0 and idx < len(self.actions):
            with self.actions_lock:
                self.actions[idx], self.actions[idx - 1] = self.actions[idx - 1], self.actions[idx]
            self.selected_index -= 1
            self.update_list_display()
            self.auto_save_presets()
            self.lbl_status.configure(text="เลื่อนขั้นตอนขึ้นแล้ว", text_color="#3498db")
        elif idx == 0:
            self.lbl_status.configure(text="⚠️ อยู่บนสุดแล้วครับ", text_color="#f1c40f")
        else:
            self.lbl_status.configure(text="⚠️ กรุณาคลิกเลือกขั้นตอนที่จะขยับก่อน", text_color="#f1c40f")

    def move_action_down(self) -> None:
        idx = getattr(self, "selected_index", -1)
        if 0 <= idx < len(self.actions) - 1:
            with self.actions_lock:
                self.actions[idx], self.actions[idx + 1] = self.actions[idx + 1], self.actions[idx]
            self.selected_index += 1
            self.update_list_display()
            self.auto_save_presets()
            self.lbl_status.configure(text="เลื่อนขั้นตอนลงแล้ว", text_color="#3498db")
        elif idx == len(self.actions) - 1:
            self.lbl_status.configure(text="⚠️ อยู่ล่างสุดแล้วครับ", text_color="#f1c40f")
        elif idx == -1:
            self.lbl_status.configure(text="⚠️ กรุณาคลิกเลือกขั้นตอนที่จะขยับก่อน", text_color="#f1c40f")

    def remove_selected_action(self) -> None:
        idx = getattr(self, "selected_index", -1)
        if 0 <= idx < len(self.actions):
            with self.actions_lock:
                self.actions.pop(idx)
            self.selected_index = -1
            self.update_list_display()
            self.auto_save_presets()
            self.lbl_status.configure(text="ลบขั้นตอนเรียบร้อย", text_color="#e74c3c")
        else:
            self.lbl_status.configure(text="⚠️ กรุณาคลิกเลือกขั้นตอนที่จะลบก่อน", text_color="#f1c40f")

    def add_click_action(self):
        try:
            x, y = getattr(self, "picked_rel_x", 0), getattr(self, "picked_rel_y", 0)
            is_rel = getattr(self, "is_relative", False)
        except (ValueError, TypeError):
            return
        mode = self.var_click_mode.get()
        btn = self.var_click_btn.get()
        stop_after = self.var_click_stop.get()
        if mode == "background" and not self.target_hwnd:
            messagebox.showwarning("แจ้งเตือน", "โหมดคลิกเบื้องหลัง ต้อง 'ล็อคเป้าหน้าต่าง' ก่อนครับ", parent=self)
            return
        self.add_action_item({"type": "click", "x": x, "y": y, "button": btn, "relative": is_rel, "mode": mode, "stop_after": stop_after})

    def add_type_action(self):
        txt = self.entry_text.get().strip()
        mode = self.var_input_mode.get()
        if not txt:
            messagebox.showwarning("แจ้งเตือน", "กรุณากรอกข้อความหรือบันทึกปุ่มลัดก่อนครับ", parent=self)
            return
        if mode == "text":
            self.add_action_item({"type": "text", "content": txt, "mode": self.var_type_mode.get(), "stop_after": self.var_type_stop.get()})
        else:
            self.add_action_item({"type": "hotkey", "content": txt, "mode": self.var_type_mode.get(), "stop_after": self.var_type_stop.get()})
        self.entry_text.delete(0, "end")

    def browse_image(self):
        p = filedialog.askopenfilename(filetypes=[("ไฟล์รูปภาพ", "*.png *.jpg *.jpeg *.bmp")])
        if p:
            self.current_img_path = p
            self.lbl_img_path.configure(text=os.path.basename(p), text_color="#2ecc71")

    def add_image_action(self):
        if not self.current_img_path:
            messagebox.showwarning("แจ้งเตือน", "กรุณาเลือกไฟล์รูปก่อนครับ", parent=self)
            return
        try:
            ox = int(self.entry_off_x.get())
            oy = int(self.entry_off_y.get())
        except (ValueError, TypeError):
            ox, oy = 0, 0
        self.add_action_item(
            {
                "type": "image_search",
                "path": self.current_img_path,
                "region": self.current_region,
                "off_x": ox,
                "off_y": oy,
                "mode": self.var_img_search_mode.get(),
                "do_click": self.var_img_click.get(),
                "click_mode": self.var_img_click_mode.get(),
                "button": self.var_img_click_btn.get(),
                "stop_after": self.var_img_stop.get(),
                "confidence": self.var_img_conf.get(),
            }
        )
        self.current_region = None
        self.lbl_region_info.configure(text="พื้นที่: ทั้งจอ", text_color="gray")

    def add_wait_action(self):
        try:
            s = float(self.entry_wait.get())
            if s <= 0:
                raise ValueError
        except (ValueError, TypeError):
            s = 1.0
        self.add_action_item({"type": "wait", "seconds": s, "stop_after": self.var_wait_stop.get()})

    def add_color_action(self):
        if not self.current_color_data:
            messagebox.showwarning("แจ้งเตือน", "กรุณาดูดสีก่อนครับ", parent=self)
            return

        abs_x, abs_y, rgb = self.current_color_data
        try:
            tol = int(self.entry_tol.get())
        except (ValueError, TypeError):
            tol = 10

        self.add_action_item(
            {
                "type": "color_search",
                "x": abs_x,
                "y": abs_y,
                "rgb": rgb,
                "region": self.current_region,
                "tolerance": tol,
                "mode": self.var_color_mode.get(),
                "do_click": self.var_color_click.get(),
                "click_mode": self.var_color_click_mode.get(),
                "button": self.var_color_click_btn.get(),
                "stop_after": self.var_color_stop.get(),
            }
        )
        self.current_region = None
        self.lbl_region_info.configure(text="พื้นที่: ทั้งจอ", text_color="gray")

    def add_multi_color_point(self):
        self.withdraw()
        overlay = ctk.CTkToplevel(self)
        overlay.attributes("-fullscreen", True, "-alpha", 0.1, "-topmost", True)
        overlay.configure(fg_color="black", cursor="crosshair")

        def on_click(event):
            try:
                rgb = pyautogui.pixel(event.x_root, event.y_root)
                if not hasattr(self, "temp_multi_points"):
                    self.temp_multi_points = []
                self.temp_multi_points.append({"x": event.x_root, "y": event.y_root, "rgb": rgb, "tolerance": 10})
                self.lbl_multi_color_count.configure(text=f"จุดที่เก็บไว้: {len(self.temp_multi_points)} จุด")
            except Exception:
                pass
            overlay.destroy()
            self.deiconify()

        overlay.bind("<Button-1>", on_click)
        overlay.bind("<Escape>", lambda e: [overlay.destroy(), self.deiconify()])

        def _focus_mc():
            overlay.lift()
            overlay.focus_force()
            overlay.grab_set()

        self.after(100, _focus_mc)

    def clear_multi_color_points(self):
        self.temp_multi_points = []
        self.lbl_multi_color_count.configure(text="จุดที่เก็บไว้: 0 จุด")

    def add_multi_color_action(self):
        points = getattr(self, "temp_multi_points", [])
        if not points:
            messagebox.showwarning("แจ้งเตือน", "กรุณาเก็บจุดสีก่อนครับ", parent=self)
            return
        self.add_action_item(
            {
                "type": "multi_color_check",
                "points": points.copy(),
                "logic": self.var_multi_color_logic.get(),
                "mode": "once",
                "stop_after": self.var_multi_color_stop.get(),
            }
        )
        self.clear_multi_color_points()
