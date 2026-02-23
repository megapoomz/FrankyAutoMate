import random


class StealthMixin:
    """Handles stealth-related UI logic and window management"""

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

    # ── Running Overlay (Removed — interferes with image search) ─────
    def show_running_overlay(self):
        pass

    def hide_running_overlay(self):
        pass
