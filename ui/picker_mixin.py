import customtkinter as ctk
import pyautogui
import win32gui
from core.constants import COLOR_ACCENT, COLOR_BG, COLOR_WARNING, COLOR_MUTED, COLOR_SUCCESS, COLOR_DANGER, GRADIENT_END, GRADIENT_START

class PickerMixin:
    """Handles screen picking logic for coordinates, regions, and colors"""
    
    def start_pick_location(self):
        self.lbl_status.configure(text="โหมดเลือกพิกัด: หน้าจอจะมืดลงสักครู่ คลิกจุดที่ต้องการ...", text_color=COLOR_ACCENT)
        self.withdraw()
        self.pick_overlay = ctk.CTkToplevel(self)
        self.pick_overlay.attributes('-fullscreen', True, '-alpha', 0.3, '-topmost', True)
        self.pick_overlay.configure(fg_color="black", cursor="crosshair")
        
        def on_overlay_click(event):
            self.picked_x_raw = event.x_root
            self.picked_y_raw = event.y_root
            self.pick_overlay.destroy()
            self.deiconify()
            self.calculate_picked_coords()

        def on_cancel(event):
            self.pick_overlay.destroy()
            self.deiconify()
            self.lbl_status.configure(text="ยกเลิกการเลือกพิกัด", text_color=COLOR_MUTED)

        self.pick_overlay.bind("<Button-1>", on_overlay_click)
        self.pick_overlay.bind("<Escape>", on_cancel)
        # INST-5: Auto-destroy overlay if it loses focus or after 30s timeout
        self.pick_overlay.bind("<FocusOut>", on_cancel)
        self._pick_overlay_timeout = self.after(30000, on_cancel, None)
        
        def _focus_loc():
            self.pick_overlay.lift()
            self.pick_overlay.focus_force()
            self.pick_overlay.grab_set()
        self.after(100, _focus_loc)

    def calculate_picked_coords(self):
        if self.target_hwnd and win32gui.IsWindow(self.target_hwnd):
             try:
                rect = win32gui.GetWindowRect(self.target_hwnd)
                self.picked_rel_x = self.picked_x_raw - rect[0]
                self.picked_rel_y = self.picked_y_raw - rect[1]
                self.is_relative = True
                txt = f"X:{self.picked_rel_x}, Y:{self.picked_rel_y} (ในหน้าต่าง)"
             except Exception:
                self.picked_rel_x, self.picked_rel_y = self.picked_x_raw, self.picked_y_raw
                self.is_relative = False
                txt = f"X:{self.picked_rel_x}, Y:{self.picked_rel_y} (Error Window)"
        else:
             self.picked_rel_x, self.picked_rel_y = self.picked_x_raw, self.picked_y_raw
             self.is_relative = False
             txt = f"X:{self.picked_rel_x}, Y:{self.picked_rel_y} (จอ)"
        self.lbl_picked_coord.configure(text=txt)
        self.lbl_status.configure(text="บันทึกพิกัดแล้ว (ไม่ได้คลิกจริง)", text_color=COLOR_MUTED)

    def start_pick_region(self):
        self.lbl_status.configure(text="โหมดตีกรอบ: คลิกค้างแล้วลากเพื่อครอบพื้นที่...", text_color=COLOR_WARNING)
        self.withdraw()
        self.reg_overlay = ctk.CTkToplevel(self)
        self.reg_overlay.attributes('-fullscreen', True, '-alpha', 0.3, '-topmost', True)
        self.reg_overlay.configure(fg_color="black")
        
        def _focus_reg():
            self.reg_overlay.lift()
            self.reg_overlay.focus_force()
            self.reg_overlay.grab_set()
        self.after(100, _focus_reg)
        
        try: self.reg_overlay.configure(cursor="cross") 
        except Exception: pass
        self.start_x = self.start_y = None
        self.rect_id = None
        self.canvas_reg = ctk.CTkCanvas(self.reg_overlay, bg="black", highlightthickness=0)
        self.canvas_reg.pack(fill="both", expand=True)

        def on_press(event):
            self.start_x, self.start_y = event.x, event.y
            if self.rect_id: self.canvas_reg.delete(self.rect_id)
            self.rect_id = self.canvas_reg.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red", width=2)

        def on_drag(event):
            self.canvas_reg.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

        def on_release(event):
            try:
                ex, ey = event.x, event.y
                self.reg_overlay.destroy()
                self.deiconify()
                x1, x2 = min(self.start_x, ex), max(self.start_x, ex)
                y1, y2 = min(self.start_y, ey), max(self.start_y, ey)
                w, h = x2 - x1, y2 - y1
                if w > 5 and h > 5:
                    self.current_region = (x1, y1, w, h)
                    info = f"{w}x{h} @ {x1},{y1}"
                    self.lbl_region_info.configure(text=info, text_color=COLOR_SUCCESS)
                    self.lbl_status.configure(text="เลือกพื้นที่เรียบร้อย", text_color=COLOR_SUCCESS)
                else:
                    self.current_region = None
                    self.lbl_region_info.configure(text="พื้นที่: ทั้งจอ", text_color=COLOR_MUTED)
            except Exception:
                self.deiconify()
                self.lbl_status.configure(text="เกิดข้อผิดพลาดในการเลือกพื้นที่", text_color=COLOR_DANGER)

        self.canvas_reg.bind("<Button-1>", on_press)
        self.canvas_reg.bind("<B1-Motion>", on_drag)
        self.canvas_reg.bind("<ButtonRelease-1>", on_release)
        self.reg_overlay.bind("<Escape>", lambda e: [self.reg_overlay.destroy(), self.deiconify()])
        # INST-5: Auto-destroy region overlay after 30s timeout
        self.after(30000, lambda: [self.reg_overlay.destroy(), self.deiconify()] if hasattr(self, 'reg_overlay') and self.reg_overlay.winfo_exists() else None)

    def start_pick_color(self):
        self.lbl_status.configure(text="โหมดดูดสี: คลิกจุดที่ต้องการดูดสี...", text_color=COLOR_WARNING)
        self.withdraw()
        overlay = ctk.CTkToplevel(self)
        overlay.attributes('-fullscreen', True, '-alpha', 0.1, '-topmost', True)
        overlay.configure(fg_color="black", cursor="crosshair")
        
        def on_overlay_click(event):
            ax, ay = event.x_root, event.y_root
            try:
                rgb = pyautogui.pixel(ax, ay)
                self.current_color_data = (ax, ay, rgb)
                self.lbl_color_info.configure(text=f"พิกัด: {ax},{ay} RGB: {rgb}")
                
                # Update preview canvas
                hex_color = '#%02x%02x%02x' % rgb
                if hasattr(self, 'canvas_color'):
                    self.canvas_color.delete("all")
                    self.canvas_color.create_rectangle(0, 0, 20, 20, fill=hex_color, outline="white")
                
                self.lbl_status.configure(text=f"ดูดสีสำเร็จ: {rgb}", text_color=COLOR_MUTED)
            except Exception:
                self.lbl_status.configure(text="ดูดสีผิดพลาด!", text_color=COLOR_DANGER)
            overlay.destroy()
            self.deiconify()

        overlay.bind("<Button-1>", on_overlay_click)
        overlay.bind("<Escape>", lambda e: [overlay.destroy(), self.deiconify()])
        # INST-5: Auto-destroy color picker overlay after 30s timeout
        self.after(30000, lambda: [overlay.destroy(), self.deiconify()] if overlay.winfo_exists() else None)
        
        # improved focus handling
        def _focus():
             overlay.lift()
             overlay.focus_force()
             overlay.grab_set()
        self.after(100, _focus)
