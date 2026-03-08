import time
import logging
import customtkinter as ctk
from core.constants import COLOR_SUCCESS, COLOR_ACCENT, COLOR_INNER, COLOR_CARD, BORDER_COLOR, COLOR_MUTED
from core.logger import logger as _logger

class UIMixin:
    """Handles UI tab setups, list displays, and visual feedback"""

    # ── Batched Logging ──────────────────────────────────────────────

    def log_message(self, message: str, color: str = "white", level: int = logging.INFO):
        """Batched logging: queues messages and flushes to UI every 100ms"""
        # Use module-level logger singleton (no duplicate handlers)
        logger = _logger

        # Log to file immediately using central logger
        if level == logging.ERROR:
            logger.error(message)
        elif level == logging.WARNING:
            logger.warning(message)
        else:
            logger.info(message)

        if not hasattr(self, "txt_log") or self.txt_log is None:
            return

        now = time.strftime("%H:%M:%S")

        # Queue for batch UI update
        if not hasattr(self, "_log_buffer"):
            self._log_buffer = []
            self._log_flush_scheduled = False

        # WARN-06 FIX: Cap buffer at 200 entries to prevent memory bloat
        if len(self._log_buffer) < 200:
            self._log_buffer.append((now, message, color))

        if not self._log_flush_scheduled:
            self._log_flush_scheduled = True
            self.after(100, self._flush_log_buffer)

    def _flush_log_buffer(self):
        """Flush all queued log messages to UI in one batch"""
        self._log_flush_scheduled = False
        if not self._log_buffer:
            return

        buf = self._log_buffer
        self._log_buffer = []

        try:
            self.txt_log.configure(state="normal")
            for now, message, color in buf:
                if color and color != "white":
                    try:
                        self.txt_log.tag_config(color, foreground=color)
                    except Exception:
                        pass
                self.txt_log.insert("end", f"[{now}] {message}\n", color if color and color != "white" else ())
            # WARN-07 FIX: Trim log to last 5000 lines to prevent UI slowdown
            try:
                line_count = int(self.txt_log.index('end-1c').split('.')[0])
                if line_count > 5000:
                    self.txt_log.delete('1.0', f'{line_count - 5000}.0')
            except Exception:
                pass
            self.txt_log.see("end")
            self.txt_log.configure(state="disabled")
        except Exception:
            pass

    # ── Optimized Highlight (only 2 widgets touched) ─────────────────

    def highlight_action(self, index):
        def _highlight():
            widgets = self.action_widgets
            prev = getattr(self, "_highlighted_index", -1)

            # Restore previous widget
            if 0 <= prev < len(widgets):
                is_sel = prev == getattr(self, "selected_index", -1)
                widgets[prev].configure(fg_color=COLOR_INNER if is_sel else COLOR_CARD, border_color=COLOR_ACCENT if is_sel else BORDER_COLOR)

            # Highlight new widget
            if 0 <= index < len(widgets):
                widgets[index].configure(fg_color=COLOR_SUCCESS, border_color=COLOR_ACCENT)

            self._highlighted_index = index

        self.after(0, _highlight)

    # ── Reusable Markers (no create/destroy per call) ────────────────

    def show_click_marker(self, x, y):
        if not getattr(self, "show_marker", True):
            return

        def _show():
            try:
                m = getattr(self, "_click_marker", None)
                if m is None or not m.winfo_exists():
                    m = ctk.CTkToplevel(self)
                    m.overrideredirect(True)
                    m.attributes("-topmost", True, "-transparentcolor", "white", "-alpha", 0.7)
                    c = ctk.CTkCanvas(m, width=30, height=30, bg="white", highlightthickness=0)
                    c.pack()
                    c.create_oval(2, 2, 28, 28, outline="red", width=3)
                    c.create_oval(12, 12, 18, 18, fill="red")
                    self._click_marker = m

                m.geometry(f"30x30+{int(x-15)}+{int(y-15)}")
                m.deiconify()
                m.lift()

                # Track marker timer to prevent TclError on app close
                if hasattr(self, "_click_marker_timer"):
                    try:
                        self.after_cancel(self._click_marker_timer)
                    except Exception:
                        pass
                self._click_marker_timer = self._track_after(400, lambda: m.withdraw() if m.winfo_exists() else None)
            except Exception:
                pass

        self.after(0, _show)

    def show_found_marker(self, x, y, w=40, h=40):
        """Green rectangle for found items"""
        if not getattr(self, "show_marker", True):
            return

        def _show():
            try:
                m = getattr(self, "_found_marker", None)
                if m is None or not m.winfo_exists():
                    m = ctk.CTkToplevel(self)
                    m.overrideredirect(True)
                    m.attributes("-topmost", True, "-transparentcolor", "white", "-alpha", 0.6)
                    c = ctk.CTkCanvas(m, width=w, height=h, bg="white", highlightthickness=0)
                    c.pack(fill="both", expand=True)
                    c.create_rectangle(2, 2, w - 2, h - 2, outline="#2ecc71", width=3)
                    self._found_marker = m
                    self._found_marker_canvas = c
                else:
                    # BUG-06 FIX: Resize canvas when marker is reused with different dimensions
                    c = self._found_marker_canvas
                    c.configure(width=w, height=h)
                    c.delete("all")
                    c.create_rectangle(2, 2, w - 2, h - 2, outline="#2ecc71", width=3)

                m.geometry(f"{w}x{h}+{int(x-w/2)}+{int(y-h/2)}")
                m.deiconify()
                m.lift()

                if hasattr(self, "_found_marker_timer"):
                    try:
                        self.after_cancel(self._found_marker_timer)
                    except Exception:
                        pass
                self._found_marker_timer = self._track_after(400, lambda: m.withdraw() if m.winfo_exists() else None)
            except Exception:
                pass

        self.after(0, _show)

    def show_search_region(self, x, y, w, h):
        """Draws a blue rectangle to show search area (Debug Overlay, reuses window)"""
        var = getattr(self, "var_debug_overlay", None)
        if not var or not var.get():
            return
        if w < 1 or h < 1:
            return

        def _show():
            try:
                m = getattr(self, "_search_region_marker", None)
                if m is None or not m.winfo_exists():
                    m = ctk.CTkToplevel(self)
                    m.overrideredirect(True)
                    m.attributes("-topmost", True, "-transparentcolor", "black", "-alpha", 0.5)
                    self._search_region_marker = m
                    self._search_region_canvas = ctk.CTkCanvas(m, bg="black", highlightthickness=0)
                    self._search_region_canvas.pack(fill="both", expand=True)

                m.geometry(f"{int(w)}x{int(h)}+{int(x)}+{int(y)}")
                c = self._search_region_canvas
                c.configure(width=w, height=h)
                c.delete("all")
                c.create_rectangle(0, 0, w, h, outline="#3498db", width=2, dash=(5, 2))
                m.deiconify()
                m.lift()

                # Track marker timer to prevent TclError on app close
                if hasattr(self, "_search_region_timer"):
                    try:
                        self.after_cancel(self._search_region_timer)
                    except Exception:
                        pass
                self._search_region_timer = self._track_after(150, lambda: m.withdraw() if m.winfo_exists() else None)
            except Exception:
                pass

        self.after(0, _show)

class ToolTip(object):
    """
    create a tooltip for a given widget
    """

    def __init__(self, widget, text="widget info"):
        self.waittime = 500  # miliseconds
        self.wraplength = 180  # pixels
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        try:
            x, y, _cx, _cy = self.widget.bbox("insert")
        except (TypeError, Exception):
            pass
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20

        # WARN-05 FIX: Reuse existing toplevel window instead of creating new one
        if self.tw is None or not self.tw.winfo_exists():
            self.tw = ctk.CTkToplevel(self.widget)
            self.tw.wm_overrideredirect(True)
            self.tw.wm_attributes("-topmost", True)
            self._tw_label = ctk.CTkLabel(
                self.tw,
                text=self.text,
                justify="left",
                bg_color=COLOR_INNER,
                fg_color=COLOR_INNER,
                text_color=COLOR_MUTED,
                corner_radius=6,
                width=200,
                wraplength=self.wraplength,
                font=("Inter", 12),
            )
            self._tw_label.pack(ipadx=5, ipady=5)
        else:
            # Update text in case it changed
            self._tw_label.configure(text=self.text)

        self.tw.geometry("+%d+%d" % (x, y))
        self.tw.deiconify()

    def hidetip(self):
        tw = self.tw
        if tw:
            try:
                tw.withdraw()  # Hide instead of destroy for reuse
            except Exception:
                pass

    def destroy(self):
        """Explicit cleanup — call this when the host widget is destroyed.
        More reliable than __del__ which is not guaranteed to run."""
        try:
            self.unschedule()
            self.hidetip()
            self.widget.unbind("<Enter>")
            self.widget.unbind("<Leave>")
        except Exception:
            pass

    def __del__(self):
        """Cleanup pending callbacks on garbage collection (fallback)"""
        try:
            self.unschedule()
            self.hidetip()
        except Exception:
            pass
