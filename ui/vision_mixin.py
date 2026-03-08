import customtkinter as ctk
import os
from tkinter import messagebox
from core.constants import COLOR_INNER, BORDER_COLOR, COLOR_SUCCESS, COLOR_MUTED, WAIT_MODE_TIMEOUT

class VisionMixin:
    """Handles AI Vision & OCR UI and actions"""

    def setup_vision_tab(self):
        t = self.tab_vision

        # Check if pytesseract is available and warn if not
        try:
            import pytesseract  # noqa: F401 — availability check only
            _has_pytesseract = True
        except ImportError:
            _has_pytesseract = False

        if not _has_pytesseract:
            ctk.CTkLabel(
                t,
                text="\u26a0\ufe0f pytesseract \u0e44\u0e21\u0e48\u0e1e\u0e23\u0e49\u0e2d\u0e21\u0e43\u0e0a\u0e49\u0e07\u0e32\u0e19 \u0e01\u0e23\u0e38\u0e13\u0e32\u0e15\u0e34\u0e14\u0e15\u0e31\u0e49\u0e07: pip install pytesseract",
                font=("Inter", 12, "bold"),
                text_color="#f59e0b",
                wraplength=400,
            ).pack(pady=(10, 5))

        # --- Section 1: OCR (Text Recognition) ---
        ctk.CTkLabel(t, text="\u0e04\u0e49\u0e19\u0e2b\u0e32\u0e14\u0e49\u0e27\u0e22\u0e02\u0e49\u0e2d\u0e04\u0e27\u0e32\u0e21 (OCR SEARCH)", font=("Inter", 10, "bold"), text_color="#64748b").pack(
            pady=(10, 3), anchor="w", padx=22
        )
        f_ocr = ctk.CTkFrame(t, fg_color=COLOR_INNER, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        f_ocr.pack(fill="x", padx=15, pady=0)

        f_row1 = ctk.CTkFrame(f_ocr, fg_color="transparent")
        f_row1.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(f_row1, text="\u0e02\u0e49\u0e2d\u0e04\u0e27\u0e32\u0e21\u0e17\u0e35\u0e48\u0e15\u0e49\u0e2d\u0e07\u0e01\u0e32\u0e23:", font=("Inter", 12)).pack(side="left", padx=(0, 10))
        self.entry_ocr_text = ctk.CTkEntry(f_row1, placeholder_text="\u0e40\u0e0a\u0e48\u0e19 '\u0e22\u0e37\u0e19\u0e22\u0e31\u0e19', 'Next'...", height=35, font=("Inter", 12))
        self.entry_ocr_text.pack(side="left", fill="x", expand=True)

        f_row2 = ctk.CTkFrame(f_ocr, fg_color="transparent")
        f_row2.pack(fill="x", padx=15, pady=(0, 5))
        ctk.CTkLabel(f_row2, text="\u0e42\u0e2b\u0e21\u0e14:", font=("Inter", 12)).pack(side="left", padx=(0, 10))
        self.var_ocr_mode = ctk.StringVar(value="once")
        ctk.CTkOptionMenu(f_row2, values=["wait", "once"], variable=self.var_ocr_mode, width=120, fg_color="#1e293b").pack(side="left")

        self.var_ocr_click_val = ctk.BooleanVar(value=True)
        self.cb_ocr_click = ctk.CTkCheckBox(f_row2, text="\u0e04\u0e25\u0e34\u0e01\u0e40\u0e21\u0e37\u0e48\u0e2d\u0e1e\u0e1a", variable=self.var_ocr_click_val, font=("Inter", 11))
        self.cb_ocr_click.pack(side="left", padx=15)

        # Add stop_after checkbox (was missing, making stop_after always False)
        self.var_ocr_stop = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(f_row2, text="\u0e08\u0e1a\u0e2b\u0e25\u0e31\u0e07\u0e40\u0e08\u0e2d", variable=self.var_ocr_stop, font=("Inter", 11)).pack(side="left", padx=5)

        # Row 3: Button + Click Mode (separated to avoid overflow)
        f_row3 = ctk.CTkFrame(f_ocr, fg_color="transparent")
        f_row3.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(f_row3, text="\u0e1b\u0e38\u0e48\u0e21:", font=("Inter", 11), text_color=COLOR_MUTED).pack(side="left", padx=(0, 5))
        self.var_ocr_click_btn = ctk.StringVar(value="left")
        menu_btn = ctk.CTkOptionMenu(f_row3, values=["left", "right", "double"], variable=self.var_ocr_click_btn, width=80, fg_color="#334155")
        menu_btn.pack(side="left")

        ctk.CTkLabel(f_row3, text="\u0e42\u0e2b\u0e21\u0e14\u0e04\u0e25\u0e34\u0e01:", font=("Inter", 11), text_color=COLOR_MUTED).pack(side="left", padx=(15, 5))
        self.var_ocr_click_mode = ctk.StringVar(value="normal")
        menu_mode = ctk.CTkOptionMenu(f_row3, values=["normal", "background"], variable=self.var_ocr_click_mode, width=110, fg_color="#334155")
        menu_mode.pack(side="left")

        # Region selector for OCR (Very important for performance)
        f_reg = ctk.CTkFrame(t, fg_color="transparent")
        f_reg.pack(fill="x", padx=15, pady=5)
        self.btn_ocr_region = ctk.CTkButton(
            f_reg, text="\u0e15\u0e35\u0e01\u0e23\u0e2d\u0e1a\u0e1e\u0e37\u0e49\u0e19\u0e17\u0e35\u0e48 (\u0e41\u0e19\u0e30\u0e19\u0e33)", command=self.start_pick_region, fg_color="#334155", height=32, font=("Inter", 11)
        )
        self.btn_ocr_region.pack(side="left", fill="x", expand=True, padx=(0, 5))

        ctk.CTkButton(
            t,
            text="\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e02\u0e31\u0e49\u0e19\u0e15\u0e2d\u0e19 OCR (ADD VISION ACTION)",
            command=self.add_ocr_action,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            height=40,
            font=("Inter", 13, "bold"),
        ).pack(pady=5, padx=20, fill="x")

        # --- Portable Info ---
        f_info = ctk.CTkFrame(t, fg_color="#0f172a", corner_radius=10)
        f_info.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(
            f_info, text="\u0e42\u0e2b\u0e21\u0e14\u0e1e\u0e01\u0e1e\u0e32 (PORTABLE AI)\n\u0e23\u0e27\u0e21\u0e44\u0e1f\u0e25\u0e4c AI \u0e44\u0e27\u0e49\u0e43\u0e19\u0e42\u0e04\u0e23\u0e07\u0e01\u0e32\u0e23\u0e41\u0e25\u0e49\u0e27 \u0e44\u0e21\u0e48\u0e15\u0e49\u0e2d\u0e07\u0e42\u0e2b\u0e25\u0e14\u0e43\u0e2b\u0e21\u0e48", font=("Inter", 11, "bold"), text_color=COLOR_SUCCESS
        ).pack(pady=(10, 5))

        ctk.CTkLabel(
            f_info,
            text="\u0e2a\u0e33\u0e2b\u0e23\u0e31\u0e1a\u0e1c\u0e39\u0e49\u0e1e\u0e31\u0e12\u0e19\u0e32: \u0e19\u0e33\u0e42\u0e1f\u0e25\u0e40\u0e14\u0e2d\u0e23\u0e4c Tesseract-OCR\n\u0e44\u0e1b\u0e27\u0e32\u0e07\u0e17\u0e35\u0e48: bin/tesseract/ \u0e40\u0e1e\u0e37\u0e48\u0e2d\u0e1a\u0e34\u0e49\u0e27\u0e1e\u0e23\u0e49\u0e2d\u0e21\u0e41\u0e2d\u0e1b",
            font=("Inter", 10),
            text_color="#94a3b8",
        ).pack(pady=(0, 5))

        self.btn_manual_tess = ctk.CTkButton(
            f_info,
            text="\u0e40\u0e25\u0e37\u0e2d\u0e01\u0e44\u0e1f\u0e25\u0e4c tesseract.exe \u0e40\u0e2d\u0e07",
            command=self.browse_tesseract_path,
            fg_color="#334155",
            hover_color="#475569",
            height=32,
            font=("Inter", 11, "bold"),
        )
        self.btn_manual_tess.pack(pady=(0, 10), padx=20, fill="x")

    def browse_tesseract_path(self):
        from tkinter import filedialog
        import subprocess

        p = filedialog.askopenfilename(title="Select tesseract.exe", filetypes=[("Executable", "*.exe")])
        if p and "tesseract" in os.path.basename(p).lower():
            # INC-04 FIX: Validate binary actually works before accepting
            try:
                flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                result = subprocess.run([p, "--version"], capture_output=True, text=True, timeout=5, creationflags=flags)
                if result.returncode != 0:
                    raise RuntimeError(f"Exit code {result.returncode}")
            except Exception as e:
                messagebox.showerror("Error", f"Selected file is not a valid Tesseract binary:\n{e}", parent=self)
                return

            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = p
            self.lbl_status.configure(text=f"Tesseract OK: {os.path.basename(p)}", text_color=COLOR_SUCCESS)
            messagebox.showinfo("OK", f"Tesseract path set to:\n{p}", parent=self)

    def add_ocr_action(self):
        txt = self.entry_ocr_text.get().strip()
        if not txt:
            messagebox.showwarning("\u0e41\u0e08\u0e49\u0e07\u0e40\u0e15\u0e37\u0e2d\u0e19", "\u0e01\u0e23\u0e38\u0e13\u0e32\u0e23\u0e30\u0e1a\u0e38\u0e02\u0e49\u0e2d\u0e04\u0e27\u0e32\u0e21\u0e17\u0e35\u0e48\u0e15\u0e49\u0e2d\u0e07\u0e01\u0e32\u0e23\u0e04\u0e49\u0e19\u0e2b\u0e32", parent=self)
            return

        # Warn when using wait mode without region (full-screen OCR is very slow)
        ocr_mode = self.var_ocr_mode.get()
        if ocr_mode == "wait" and not self.current_region:
            proceed = messagebox.askyesno(
                "\u26a0\ufe0f \u0e41\u0e08\u0e49\u0e07\u0e40\u0e15\u0e37\u0e2d\u0e19\u0e1b\u0e23\u0e30\u0e2a\u0e34\u0e17\u0e18\u0e34\u0e20\u0e32\u0e1e",
                "\u0e04\u0e38\u0e13\u0e40\u0e25\u0e37\u0e2d\u0e01\u0e42\u0e2b\u0e21\u0e14 'wait' \u0e42\u0e14\u0e22\u0e44\u0e21\u0e48\u0e44\u0e14\u0e49\u0e15\u0e35\u0e01\u0e23\u0e2d\u0e1a\u0e1e\u0e37\u0e49\u0e19\u0e17\u0e35\u0e48\n\n"
                "OCR \u0e17\u0e31\u0e49\u0e07\u0e08\u0e2d\u0e08\u0e30\u0e0a\u0e49\u0e32\u0e21\u0e32\u0e01 (2-15 \u0e27\u0e34\u0e19\u0e32\u0e17\u0e35\u0e15\u0e48\u0e2d\u0e23\u0e2d\u0e1a)\n"
                "\u0e41\u0e19\u0e30\u0e19\u0e33\u0e43\u0e2b\u0e49\u0e15\u0e35\u0e01\u0e23\u0e2d\u0e1a\u0e1e\u0e37\u0e49\u0e19\u0e17\u0e35\u0e48\u0e01\u0e48\u0e2d\u0e19\n\n"
                "\u0e15\u0e49\u0e2d\u0e07\u0e01\u0e32\u0e23\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e04\u0e33\u0e2a\u0e31\u0e48\u0e07\u0e15\u0e48\u0e2d\u0e44\u0e1b\u0e2b\u0e23\u0e37\u0e2d\u0e44\u0e21\u0e48?",
                parent=self,
            )
            if not proceed:
                return

        action = {
            "type": "ocr_search",
            "text": txt,
            "mode": ocr_mode,
            "do_click": self.var_ocr_click_val.get(),
            "region": self.current_region,
            "click_mode": self.var_ocr_click_mode.get(),
            "button": self.var_ocr_click_btn.get(),
            "stop_after": self.var_ocr_stop.get(),  # Now properly wired to UI checkbox
            "max_wait_time": WAIT_MODE_TIMEOUT,  # Include timeout
        }

        self.add_action_item(action)
        self.lbl_status.configure(text=f'\u0e40\u0e1e\u0e34\u0e48\u0e21 OCR: "{txt}"', text_color=COLOR_SUCCESS)
