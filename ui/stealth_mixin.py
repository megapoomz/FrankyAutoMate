import random
import customtkinter as ctk
import ctypes
import win32api
import win32con

class StealthMixin:
    """Handles stealth-related UI logic and window management"""
    
    def on_speed_changed(self, val):
        self.speed_delay = float(val)
        self.lbl_speed_val.configure(text=f"{self.speed_delay:.1f}s")
    
    def on_marker_toggle(self):
        self.show_marker = self.cb_marker.get()

    def on_stealth_timing_changed(self, val):
        self.lbl_stealth_timing_val.configure(text=f"{int(float(val)*100)}%")

    def on_random_title_toggle(self):
        if self.var_stealth_random_title.get():
            fake_apps = ["Microsoft Excel", "Notepad", "Calculator", "Windows Settings", "File Explorer", "Chrome", "Edge", "System32"]
            self.title(random.choice(fake_apps))
        else:
            self.title(self.original_title)
        self.auto_save_presets()

    def stealth_on_run_start(self):
        if self.var_stealth_hide_window.get():
            self.iconify()

    def stealth_on_run_stop(self):
        if self.var_stealth_hide_window.get():
            self.after(0, self.deiconify)
            self.after(50, self.lift)

    # ── Running Overlay ──────────────────────────────────────────────

    def _make_click_through(self, toplevel, alpha=0.92):
        """Make a Toplevel window click-through using Win32 API"""
        toplevel.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(toplevel.winfo_id())
        # 64-bit Safe API calls
        GetWindowLong = ctypes.windll.user32.GetWindowLongPtrW if hasattr(ctypes.windll.user32, "GetWindowLongPtrW") else ctypes.windll.user32.GetWindowLongW
        SetWindowLong = ctypes.windll.user32.SetWindowLongPtrW if hasattr(ctypes.windll.user32, "SetWindowLongPtrW") else ctypes.windll.user32.SetWindowLongW
        
        GWL_EXSTYLE = -20
        ex_style = GetWindowLong(hwnd, GWL_EXSTYLE)
        ex_style |= win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
        SetWindowLong(hwnd, GWL_EXSTYLE, ex_style)
        ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0, int(alpha * 255), 0x02)

    def show_running_overlay(self):
        """Show premium HUD-style overlay with animated scanning line"""
        if not self.var_show_overlay.get():
            return
        
        if hasattr(self, '_overlay_win') and self._overlay_win and self._overlay_win.winfo_exists():
            return  # Already showing

        self._overlay_anim_running = True
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        # ── Layer 1: Subtle dark vignette tint ──
        tint = ctk.CTkToplevel()
        tint.title("")
        tint.overrideredirect(True)
        tint.attributes("-topmost", True)
        tint.configure(fg_color="#000000")
        tint.geometry(f"{sw}x{sh}+0+0")
        tint.attributes("-alpha", 0.35)
        self._make_click_through(tint, alpha=0.35)
        self._overlay_tint = tint

        # ── Layer 2: Premium HUD Banner ──
        banner = ctk.CTkToplevel()
        banner.title("")
        banner.overrideredirect(True)
        banner.attributes("-topmost", True)

        banner_h = 48
        banner.geometry(f"{sw}x{banner_h}+0+0")
        banner.configure(fg_color="#06080f")
        self._make_click_through(banner, alpha=0.92)

        # ── Animated Scanning Line (bottom edge cyan glow) ──
        self._scan_bar = ctk.CTkFrame(banner, height=2, width=150, fg_color="#06b6d4", corner_radius=0)
        self._scan_bar.place(x=0, y=banner_h - 2)
        self._scan_pos = 0
        self._scan_sw = sw

        # ── Content ──
        content = ctk.CTkFrame(banner, fg_color="transparent")
        content.pack(fill="both", expand=True)

        # Left: Recording indicator
        f_left = ctk.CTkFrame(content, fg_color="transparent")
        f_left.pack(side="left", padx=(20, 0))

        self._overlay_dot_label = ctk.CTkLabel(
            f_left, text="⬤", font=("Segoe UI", 12), text_color="#ef4444", width=18
        )
        self._overlay_dot_label.pack(side="left")

        self._overlay_rec_label = ctk.CTkLabel(
            f_left, text="REC", font=("JetBrains Mono", 9, "bold"), text_color="#ef4444"
        )
        self._overlay_rec_label.pack(side="left", padx=(5, 0))

        # Divider line
        ctk.CTkFrame(content, width=1, height=24, fg_color="#1e293b").pack(side="left", padx=15)

        # Center: Brand + status
        ctk.CTkLabel(
            content,
            text="FRANKY AUTOMATE",
            font=("JetBrains Mono", 11, "bold"),
            text_color="#06b6d4"
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            content,
            text="กำลังทำงานอัตโนมัติ — อย่าสัมผัสเมาส์",
            font=("Tahoma", 11),
            text_color="#475569"
        ).pack(side="left")

        # Right: Keyboard badge
        hotkey = getattr(self, 'toggle_key', 'F6').upper()
        f_key = ctk.CTkFrame(content, fg_color="#0f172a", corner_radius=6, 
                              border_width=1, border_color="#1e293b")
        f_key.pack(side="right", padx=20)
        ctk.CTkLabel(
            f_key, text=f"{hotkey}  STOP",
            font=("JetBrains Mono", 10, "bold"),
            text_color="#64748b"
        ).pack(padx=12, pady=4)

        self._overlay_win = banner
        self._overlay_dot_phase = 0
        self._animate_overlay_dot()
        self._animate_scan_line()

    def _animate_scan_line(self):
        """Animate cyan scanning line sweeping across the banner bottom"""
        if not self._overlay_anim_running:
            return
        if not hasattr(self, '_overlay_win') or not self._overlay_win or not self._overlay_win.winfo_exists():
            return

        try:
            self._scan_pos += 6
            if self._scan_pos > self._scan_sw:
                self._scan_pos = -150
            self._scan_bar.place(x=self._scan_pos)
            self._overlay_win.after(16, self._animate_scan_line)
        except Exception:
            pass

    def _animate_overlay_dot(self):
        """Animate recording dot with smooth breathing glow"""
        if not self._overlay_anim_running:
            return
        if not hasattr(self, '_overlay_win') or not self._overlay_win or not self._overlay_win.winfo_exists():
            return
        
        try:
            # Smooth 8-step breathing cycle
            colors = ["#ef4444", "#dc2626", "#b91c1c", "#991b1b", "#b91c1c", "#dc2626", "#ef4444", "#f87171"]
            color = colors[self._overlay_dot_phase % len(colors)]
            self._overlay_dot_label.configure(text_color=color)
            self._overlay_rec_label.configure(text_color=color)
            self._overlay_dot_phase += 1
            
            self._overlay_win.after(300, self._animate_overlay_dot)
        except Exception:
            pass

    def hide_running_overlay(self):
        """Close both the tint and banner"""
        self._overlay_anim_running = False
        # Destroy tint
        if hasattr(self, '_overlay_tint') and self._overlay_tint:
            try:
                if self._overlay_tint.winfo_exists():
                    self._overlay_tint.destroy()
            except Exception:
                pass
            self._overlay_tint = None
        # Destroy banner
        if hasattr(self, '_overlay_win') and self._overlay_win:
            try:
                if self._overlay_win.winfo_exists():
                    self._overlay_win.destroy()
            except Exception:
                pass
            self._overlay_win = None
            self._overlay_dot_phase = 0
