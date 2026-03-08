import customtkinter as ctk
import pyautogui
import win32gui
import win32api
from core.constants import COLOR_ACCENT, COLOR_WARNING, COLOR_MUTED, COLOR_SUCCESS, COLOR_DANGER

class PickerMixin:
    """Handles screen picking logic for coordinates, regions, and colors"""

    def start_pick_location(self):
        self.lbl_status.configure(text="โหมดเลือกพิกัด: หน้าจอจะมืดลงสักครู่ คลิกจุดที่ต้องการ...", text_color=COLOR_ACCENT)
        self.withdraw()
        self.pick_overlay = ctk.CTkToplevel(self)
        self.pick_overlay.attributes("-fullscreen", True, "-alpha", 0.3, "-topmost", True)
        self.pick_overlay.configure(fg_color="black", cursor="crosshair")

        def on_overlay_click(event):
            # Use GetCursorPos for DPI-accurate coordinates (not Tkinter event)
            try:
                cursor_pos = win32api.GetCursorPos()
                self.picked_x_raw = cursor_pos[0]
                self.picked_y_raw = cursor_pos[1]
            except Exception:
                self.picked_x_raw = event.x_root
                self.picked_y_raw = event.y_root
            # BUG-A5: Cancel timeout to prevent spurious destroy
            if hasattr(self, '_pick_overlay_timeout') and self._pick_overlay_timeout:
                self.after_cancel(self._pick_overlay_timeout)
                self._pick_overlay_timeout = None
            self.pick_overlay.destroy()
            self.deiconify()
            self.calculate_picked_coords()

        def on_cancel(event):
            self.pick_overlay.destroy()
            self.deiconify()
            self.lbl_status.configure(text="ยกเลิกการเลือกพิกัด", text_color=COLOR_MUTED)

        self.pick_overlay.bind("<Button-1>", on_overlay_click)
        self.pick_overlay.bind("<Escape>", on_cancel)
        # Removed <FocusOut> binding — causes premature dismiss on multi-monitor setups
        self._pick_overlay_timeout = self._track_after(30000, on_cancel, None)

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
        self.reg_overlay.attributes("-fullscreen", True, "-alpha", 0.3, "-topmost", True)
        self.reg_overlay.configure(fg_color="black")

        def _focus_reg():
            self.reg_overlay.lift()
            self.reg_overlay.focus_force()
            self.reg_overlay.grab_set()

        self.after(100, _focus_reg)

        try:
            self.reg_overlay.configure(cursor="cross")
        except Exception:
            pass
        self.start_x = self.start_y = None
        self.rect_id = None
        self.canvas_reg = ctk.CTkCanvas(self.reg_overlay, bg="black", highlightthickness=0)
        self.canvas_reg.pack(fill="both", expand=True)

        def on_press(event):
            # Use GetCursorPos for DPI-accurate region coordinates
            try:
                cursor_pos = win32api.GetCursorPos()
                self.start_x, self.start_y = cursor_pos[0], cursor_pos[1]
            except Exception:
                self.start_x, self.start_y = event.x_root, event.y_root
            if self.rect_id:
                self.canvas_reg.delete(self.rect_id)
            self.rect_id = self.canvas_reg.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red", width=2)

        def on_drag(event):
            # FIX: Use GetCursorPos for DPI-accurate drag coordinates (matching on_press)
            try:
                cursor_pos = win32api.GetCursorPos()
                cx, cy = cursor_pos[0], cursor_pos[1]
            except Exception:
                cx, cy = event.x_root, event.y_root
            self.canvas_reg.coords(self.rect_id, self.start_x, self.start_y, cx, cy)

        def on_release(event):
            try:
                # Use GetCursorPos for DPI-accurate region end point
                try:
                    cursor_pos = win32api.GetCursorPos()
                    ex, ey = cursor_pos[0], cursor_pos[1]
                except Exception:
                    ex, ey = event.x_root, event.y_root
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
        # Auto-destroy with try-except to prevent TclError
        def _auto_close_reg():
            try:
                if hasattr(self, "reg_overlay") and self.reg_overlay.winfo_exists():
                    self.reg_overlay.destroy()
                    self.deiconify()
            except Exception:
                pass
        self._track_after(30000, _auto_close_reg)

    def start_pick_color(self):
        self.lbl_status.configure(text="โหมดดูดสี: คลิกจุดที่ต้องการดูดสี...", text_color=COLOR_WARNING)
        self.withdraw()
        overlay = ctk.CTkToplevel(self)
        overlay.attributes("-fullscreen", True, "-alpha", 0.1, "-topmost", True)
        overlay.configure(fg_color="black", cursor="crosshair")

        def on_overlay_click(event):
            # Use GetCursorPos for DPI-accurate color pick coordinates
            try:
                cursor_pos = win32api.GetCursorPos()
                ax, ay = cursor_pos[0], cursor_pos[1]
            except Exception:
                ax, ay = event.x_root, event.y_root
            try:
                # COMPAT-03: Use fast Win32 GetPixel instead of slow pyautogui.pixel
                from utils.win32_input import fast_get_pixel
                rgb = fast_get_pixel(ax, ay)
                self.current_color_data = (ax, ay, rgb)
                self.lbl_color_info.configure(text=f"พิกัด: {ax},{ay} RGB: {rgb}")

                # Update preview canvas
                hex_color = "#%02x%02x%02x" % rgb
                if hasattr(self, "canvas_color"):
                    self.canvas_color.delete("all")
                    self.canvas_color.create_rectangle(0, 0, 20, 20, fill=hex_color, outline="white")

                self.lbl_status.configure(text=f"ดูดสีสำเร็จ: {rgb}", text_color=COLOR_MUTED)
            except Exception:
                self.lbl_status.configure(text="ดูดสีผิดพลาด!", text_color=COLOR_DANGER)
            overlay.destroy()
            self.deiconify()

        overlay.bind("<Button-1>", on_overlay_click)
        overlay.bind("<Escape>", lambda e: [overlay.destroy(), self.deiconify()])
        # Auto-destroy with try-except to prevent TclError
        def _auto_close_color():
            try:
                if overlay.winfo_exists():
                    overlay.destroy()
                    self.deiconify()
            except Exception:
                pass
        self._track_after(30000, _auto_close_color)

        # improved focus handling
        def _focus():
            overlay.lift()
            overlay.focus_force()
            overlay.grab_set()

        self.after(100, _focus)
