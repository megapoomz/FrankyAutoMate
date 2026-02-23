import os
import time

from tkinter import filedialog, messagebox
import customtkinter as ctk
from core.constants import (
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_INNER,
    COLOR_MUTED,
    COLOR_DANGER,
    COLOR_SUCCESS,
    BORDER_COLOR,
    GRADIENT_START,
    GRADIENT_END,
    COLOR_CARD,
)
from ui.ui_mixin import ToolTip


class TabsMixin:
    """Handles UI tab setups, action list management, and picker logic"""

    def setup_click_tab(self):
        t = self.tab_click
        # Row 1: Pick + Label + Add (All in one compact row)
        f_top = ctk.CTkFrame(t, fg_color="transparent")
        f_top.pack(fill="x", padx=15, pady=(15, 5))

        self.btn_pick_coord = ctk.CTkButton(
            f_top,
            text="เลือกพิกัด (Pick)",
            command=self.start_pick_location,
            fg_color=GRADIENT_END,
            hover_color=GRADIENT_START,
            width=120,
            height=32,
            font=("Inter", 11, "bold"),
        )
        self.btn_pick_coord.pack(side="left", padx=(0, 10))
        ToolTip(self.btn_pick_coord, "คลิกเพื่อไปจิ้มจุดบนหน้าจอ")

        self.lbl_picked_coord = ctk.CTkLabel(f_top, text="พิกัด: -", text_color=COLOR_ACCENT, font=("JetBrains Mono", 12, "bold"))
        self.lbl_picked_coord.pack(side="left", fill="x", expand=True)

        # Row 2: Config Grid
        f_grid = ctk.CTkFrame(t, fg_color=COLOR_INNER, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        f_grid.pack(fill="x", padx=15, pady=5)

        # Row 1: Left = Click Mode, Right = Button
        f_r1 = ctk.CTkFrame(f_grid, fg_color="transparent")
        f_r1.pack(fill="x", padx=15, pady=(15, 5))

        # Mode
        ctk.CTkLabel(f_r1, text="โหมด:", font=("Inter", 12), text_color=COLOR_MUTED).pack(side="left", padx=(0, 5))
        self.var_click_mode = ctk.StringVar(value="normal")
        rb_norm = ctk.CTkRadioButton(f_r1, text="ปกติ", variable=self.var_click_mode, value="normal", font=("Inter", 12), width=60)
        rb_norm.pack(side="left", padx=5)
        rb_bg = ctk.CTkRadioButton(f_r1, text="เบื้องหลัง (BG)", variable=self.var_click_mode, value="background", font=("Inter", 12))
        rb_bg.pack(side="left", padx=5)
        ToolTip(
            rb_bg,
            "⚠️ โหมดเบื้องหลัง: ส่งคำสั่งตรงเข้าโปรแกรม (ไม่ต้องมีหน้าต่างโฟกัส)\n"
            "❌ อาจใช้ไม่ได้กับ: เว็บเบราว์เซอร์, เกมรุ่นใหม่ หรือโปรแกรมที่รันด้วยสิทธิ์ Admin",
        )

        # Button (Right Side)
        ctk.CTkLabel(f_r1, text="ปุ่ม:", font=("Inter", 12), text_color=COLOR_MUTED).pack(side="right", padx=(10, 5))
        self.var_click_btn = ctk.StringVar(value="left")
        menu_btn = ctk.CTkOptionMenu(
            f_r1,
            variable=self.var_click_btn,
            values=["left", "right", "middle", "double"],
            width=90,
            height=28,
            fg_color=COLOR_CARD,
            button_color=COLOR_INNER,
        )
        menu_btn.pack(side="right")

        # Row 3: Options + Add Button
        f_act = ctk.CTkFrame(t, fg_color="transparent")
        f_act.pack(fill="x", padx=15, pady=10)

        self.var_click_stop = ctk.BooleanVar(value=False)
        cb_stop = ctk.CTkCheckBox(
            f_act,
            text="จบงานทันที (Stop After)",
            variable=self.var_click_stop,
            font=("Inter", 11),
            text_color=COLOR_MUTED,
            border_color=BORDER_COLOR,
            checkmark_color="white",
            width=20,
            height=20,
        )
        cb_stop.pack(side="left")

        ctk.CTkButton(
            f_act,
            text="เพิ่ม (Add)",
            command=self.add_click_action,
            fg_color=COLOR_SUCCESS,
            hover_color="#059669",
            height=32,
            width=100,
            font=("Inter", 12, "bold"),
        ).pack(side="right")

    def setup_type_tab(self):
        t = self.tab_type
        ctk.CTkLabel(t, text="พิมพ์ข้อความ / กดปุ่ม (Keyboard Input)", font=("Inter", 12, "bold"), text_color=COLOR_MUTED).pack(
            pady=(20, 5), anchor="center"
        )

        # Row 1: Entry + Record Button
        f_row1 = ctk.CTkFrame(t, fg_color="transparent")
        f_row1.pack(fill="x", padx=15, pady=(15, 5))

        self.entry_text = ctk.CTkEntry(f_row1, placeholder_text="พิมพ์ข้อความ / กดปุ่ม...", height=35, font=("Inter", 12))
        self.entry_text.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_record_key = ctk.CTkButton(
            f_row1,
            text="อัดปุ่ม (Rec)",
            command=self.start_recording_action_hotkey,
            fg_color=COLOR_CARD,
            hover_color=COLOR_INNER,
            width=80,
            height=35,
            font=("Inter", 11),
        )
        self.btn_record_key.pack(side="right")
        ToolTip(self.btn_record_key, "กดเพื่อเริ่มอัดปุ่มคีย์บอร์ด")

        # Mode
        # Row 2: Options + Add Button
        f_opts = ctk.CTkFrame(t, fg_color="transparent")
        f_opts.pack(fill="x", padx=15, pady=5)

        # Left: Mode & Type (Compact)
        f_vars = ctk.CTkFrame(f_opts, fg_color="transparent")
        f_vars.pack(side="left")

        self.var_type_mode = ctk.StringVar(value="normal")
        ctk.CTkRadioButton(f_vars, text="ปกติ", variable=self.var_type_mode, value="normal", font=("Inter", 11), width=50).pack(side="left", padx=2)
        ctk.CTkRadioButton(f_vars, text="BG", variable=self.var_type_mode, value="background", font=("Inter", 11), width=40).pack(side="left", padx=2)

        ctk.CTkFrame(f_vars, width=1, height=20, fg_color=BORDER_COLOR).pack(side="left", padx=5)  # Divider

        self.var_input_mode = ctk.StringVar(value="text")
        ctk.CTkRadioButton(f_vars, text="Text", variable=self.var_input_mode, value="text", font=("Inter", 11), width=50).pack(side="left", padx=2)
        ctk.CTkRadioButton(f_vars, text="Key", variable=self.var_input_mode, value="hotkey", font=("Inter", 11), width=40).pack(side="left", padx=2)

        self.var_type_stop = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            f_opts,
            text="จบงานทันที",
            variable=self.var_type_stop,
            font=("Inter", 11),
            text_color=COLOR_MUTED,
            border_color=BORDER_COLOR,
            width=20,
            height=20,
        ).pack(side="left", padx=(10, 0))

        # Right: Add Button
        ctk.CTkButton(
            f_opts,
            text="เพิ่ม (Add)",
            command=self.add_type_action,
            fg_color=COLOR_SUCCESS,
            hover_color="#059669",
            height=32,
            width=80,
            font=("Inter", 12, "bold"),
        ).pack(side="right")

    def setup_image_tab(self):
        t = self.tab_image
        ctk.CTkLabel(t, text="1. เลือกรูปภาพ (Target Image)", font=("Inter", 12, "bold"), text_color=COLOR_MUTED).pack(pady=(10, 3), anchor="center")

        f_img = ctk.CTkFrame(t, fg_color=COLOR_INNER, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        f_img.pack(fill="x", padx=15, pady=0)
        f_img_row = ctk.CTkFrame(f_img, fg_color="transparent")
        f_img_row.pack(fill="x", padx=15, pady=10)

        self.lbl_img_path = ctk.CTkLabel(f_img_row, text="ยังไม่ได้เลือกรูปภาพ...", text_color=COLOR_MUTED, font=("Inter", 11, "italic"), anchor="w")
        self.lbl_img_path.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            f_img_row, text="เลือกไฟล์", command=self.browse_image, width=100, height=35, fg_color="#3b82f6", font=("Inter", 11, "bold")
        ).pack(side="right")

        ctk.CTkLabel(t, text="2. ตั้งค่าพิกัดการหา (Config)", font=("Inter", 12, "bold"), text_color=COLOR_MUTED).pack(pady=(8, 3), anchor="center")
        f_sub_row = ctk.CTkFrame(t, fg_color="transparent")
        f_sub_row.pack(fill="x", padx=15, pady=0)

        # Region
        f_reg = ctk.CTkFrame(f_sub_row, fg_color=COLOR_INNER, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        f_reg.pack(side="left", fill="both", expand=True, padx=(0, 5))
        ctk.CTkLabel(f_reg, text="ขอบเขตหา (Region)", font=("Inter", 11, "bold"), text_color=COLOR_ACCENT).pack(pady=(10, 5))
        self.btn_pick_region = ctk.CTkButton(
            f_reg,
            text="ตีกรอบหน้าจอ",
            command=self.start_pick_region,
            fg_color=GRADIENT_END,
            hover_color=GRADIENT_START,
            height=32,
            font=("Inter", 11, "bold"),
        )
        self.btn_pick_region.pack(pady=(0, 10), padx=15, fill="x")
        self.lbl_region_info = ctk.CTkLabel(f_reg, text="ทั้งหน้าจอ (Full Screen)", text_color="#94a3b8", font=("Inter", 10))
        self.lbl_region_info.pack(pady=(0, 10))
        ToolTip(self.btn_pick_region, "จำกัดพื้นที่ค้นหาเพื่อให้ทำงานเร็วขึ้น (ถ้าไม่เลือกจะหาทั้งจอ)")

        # Offset
        f_off = ctk.CTkFrame(f_sub_row, fg_color=COLOR_INNER, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        f_off.pack(side="left", fill="both", expand=True, padx=(5, 0))
        ctk.CTkLabel(f_off, text="จุดคลิก X,Y (Offset)", font=("Inter", 11, "bold"), text_color=COLOR_ACCENT).pack(pady=(10, 5))
        f_off_row = ctk.CTkFrame(f_off, fg_color="transparent")
        f_off_row.pack(pady=(0, 10))
        self.entry_off_x = ctk.CTkEntry(
            f_off_row,
            width=50,
            height=32,
            placeholder_text="X",
            font=("JetBrains Mono", 11),
            fg_color=COLOR_BG,
            border_color=BORDER_COLOR,
            justify="center",
        )
        self.entry_off_x.insert(0, "0")
        self.entry_off_x.pack(side="left", padx=5)
        self.entry_off_y = ctk.CTkEntry(
            f_off_row,
            width=50,
            height=32,
            placeholder_text="Y",
            font=("JetBrains Mono", 11),
            fg_color=COLOR_BG,
            border_color=BORDER_COLOR,
            justify="center",
        )
        self.entry_off_y.insert(0, "0")
        self.entry_off_y.pack(side="left", padx=5)
        ToolTip(self.entry_off_x, "เลื่อนจุดคลิกห่างจากกลางภาพไปทางซ้าย/ขวา (พิกเซล)")

        # Confidence
        f_conf = ctk.CTkFrame(f_sub_row, fg_color=COLOR_INNER, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        f_conf.pack(side="left", fill="both", expand=True, padx=(5, 0))
        lbl_conf_head = ctk.CTkLabel(f_conf, text="ความแม่นยำ (75%)", font=("Inter", 11, "bold"), text_color=COLOR_ACCENT)
        lbl_conf_head.pack(pady=(10, 0))

        def update_conf_lbl(v):
            lbl_conf_head.configure(text=f"ความแม่นยำ ({int(float(v)*100)}%)")

        self.slider_conf = ctk.CTkSlider(f_conf, from_=0.5, to=1.0, variable=self.var_img_conf, command=update_conf_lbl, height=16)
        self.slider_conf.pack(pady=(5, 10), padx=15, fill="x")
        ToolTip(self.slider_conf, "ปรับความแม่นยำในการค้นหา (0.5 - 1.0) แนะนำ 0.95+ สำหรับแยกแยะกล่องติ๊กถูก")

        # Row: Checkboxes + Search Mode
        f_last = ctk.CTkFrame(t, fg_color="transparent")
        f_last.pack(fill="x", padx=15, pady=5)

        self.var_img_click = ctk.BooleanVar(value=True)
        self.var_img_stop = ctk.BooleanVar(value=False)
        cb_click = ctk.CTkCheckBox(f_last, text="เจอแล้วคลิก", variable=self.var_img_click, font=("Inter", 11))
        cb_click.pack(side="left", padx=(5, 10))
        cb_stop = ctk.CTkCheckBox(f_last, text="จบหลังเจอ", variable=self.var_img_stop, font=("Inter", 11))
        cb_stop.pack(side="left", padx=5)

        self.var_img_search_mode = ctk.StringVar(value="once")
        menu_search_mode = ctk.CTkOptionMenu(
            f_last, variable=self.var_img_search_mode, values=["wait", "once"], width=80, fg_color=COLOR_CARD, button_color=COLOR_INNER
        )
        menu_search_mode.pack(side="right", padx=5)
        ToolTip(menu_search_mode, "โหมดค้นหา:\nwait = รอจนกว่าจะเจอรูป (วนค้นหาไม่หยุด)\nonce = เช็คครั้งเดียว ไม่เจอก็ไปขั้นต่อไป")

        # Row: Button Type + Click Mode
        f_img_btns = ctk.CTkFrame(t, fg_color="transparent")
        f_img_btns.pack(fill="x", padx=15, pady=(0, 5))

        ctk.CTkLabel(f_img_btns, text="ปุ่ม:", font=("Inter", 11), text_color=COLOR_MUTED).pack(side="left", padx=5)
        self.var_img_click_btn = ctk.StringVar(value="left")
        menu_btn = ctk.CTkOptionMenu(
            f_img_btns, variable=self.var_img_click_btn, values=["left", "right", "double"], width=80, fg_color=COLOR_CARD, button_color=COLOR_INNER
        )
        menu_btn.pack(side="left", padx=2)

        ctk.CTkLabel(f_img_btns, text="โหมดคลิก:", font=("Inter", 11), text_color=COLOR_MUTED).pack(side="left", padx=(15, 5))
        self.var_img_click_mode = ctk.StringVar(value="normal")
        menu_mode = ctk.CTkOptionMenu(
            f_img_btns, variable=self.var_img_click_mode, values=["normal", "background"], width=110, fg_color=COLOR_CARD, button_color=COLOR_INNER
        )
        menu_mode.pack(side="left", padx=2)

        ToolTip(menu_mode, "โหมดการคลิก: หน้าจอปกติ หรือ พื้นหลัง (BG)")

        ctk.CTkButton(
            t,
            text="เพิ่มคำสั่ง (Add)",
            command=self.add_image_action,
            fg_color=COLOR_SUCCESS,
            hover_color="#059669",
            height=40,
            font=("Inter", 13, "bold"),
        ).pack(pady=5, padx=20, fill="x")

    def setup_color_tab(self):
        t = self.tab_color
        ctk.CTkLabel(t, text="ตรวจจับสี & คลิก (Color)", font=("Inter", 12, "bold"), text_color=COLOR_MUTED).pack(pady=(10, 3), anchor="center")
        f_sub = ctk.CTkFrame(t, fg_color="transparent")
        f_sub.pack(fill="x", padx=15, pady=0)

        # Color Info
        f_col = ctk.CTkFrame(f_sub, fg_color=COLOR_INNER, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        f_col.pack(side="left", fill="both", expand=True, padx=(0, 5))
        ctk.CTkLabel(f_col, text="ข้อมูลสี (RGB)", font=("Inter", 11, "bold"), text_color=COLOR_ACCENT).pack(pady=(8, 3))
        self.lbl_color_info = ctk.CTkLabel(f_col, text="ยังไม่ได้ดูดสี", text_color="#94a3b8", font=("Inter", 10))
        self.lbl_color_info.pack(pady=2)

        self.btn_pick_color = ctk.CTkButton(
            f_col,
            text="ดูดสี (Pick)",
            command=self.start_pick_color,
            fg_color=GRADIENT_END,
            hover_color=GRADIENT_START,
            height=32,
            font=("Inter", 11, "bold"),
        )
        self.btn_pick_color.pack(pady=(3, 5), padx=15, fill="x")
        ToolTip(self.btn_pick_color, "คลิกเพื่อไปจิ้มสีบนหน้าจอที่ต้องการ")

        f_res = ctk.CTkFrame(f_col, fg_color="transparent")
        f_res.pack(pady=(0, 5))
        self.canvas_color = ctk.CTkCanvas(f_res, width=20, height=20, highlightthickness=1, highlightbackground="#334155", bg="#000000")
        self.canvas_color.pack(side="left", padx=5)

        # Tolerance
        f_tol = ctk.CTkFrame(f_sub, fg_color=COLOR_INNER, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        f_tol.pack(side="left", fill="both", expand=True, padx=(5, 0))
        ctk.CTkLabel(f_tol, text="ความเพี้ยนสี (Tolerance)", font=("Inter", 11, "bold"), text_color=COLOR_ACCENT).pack(pady=(8, 3))
        self.entry_tol = ctk.CTkEntry(
            f_tol, width=70, height=32, justify="center", font=("JetBrains Mono", 13), fg_color=COLOR_BG, border_color=BORDER_COLOR
        )
        self.entry_tol.insert(0, "10")
        self.entry_tol.pack(pady=(3, 8))
        ToolTip(self.entry_tol, "ใส่ค่าเลข 0-255\nค่าเทานี้จะยอมให้สีเพี้ยนไปจากต้นฉบับได้แค่ไหน\n(ค่าน้อย = ต้องเหมือนเป๊ะ, ค่ามาก = ยืดหยุ่น)")

        # Extra Settings
        f_conf = ctk.CTkFrame(t, fg_color="transparent")
        f_conf.pack(fill="x", padx=15, pady=5)

        self.var_color_click = ctk.BooleanVar(value=True)
        cb_click = ctk.CTkCheckBox(f_conf, text="เจอแล้วคลิก", variable=self.var_color_click, font=("Inter", 11))
        cb_click.pack(side="left", padx=(5, 10))
        ToolTip(cb_click, "คลิกที่จุดที่เจอสีนั้นทันที")

        # New variable for Button Selection
        self.var_color_click_btn = ctk.StringVar(value="left")
        ctk.CTkOptionMenu(f_conf, variable=self.var_color_click_btn, values=["left", "right", "double"], width=70).pack(side="left", padx=5)

        # Mode Selection
        self.var_color_mode = ctk.StringVar(value="once")  # behavior: once/wait
        ctk.CTkOptionMenu(f_conf, variable=self.var_color_mode, values=["once", "wait"], width=70).pack(side="left", padx=5)

        # Click Mode (Normal/Background) - moved to separate row to avoid overflow
        self.var_color_click_mode = ctk.StringVar(value="normal")

        self.var_color_stop = ctk.BooleanVar(value=False)
        f_color_act = ctk.CTkFrame(t, fg_color="transparent")
        f_color_act.pack(fill="x", padx=15, pady=0)
        ctk.CTkCheckBox(
            f_color_act,
            text="จบงานทันที (Stop After)",
            variable=self.var_color_stop,
            font=("Inter", 11),
            text_color=COLOR_MUTED,
            border_color=BORDER_COLOR,
            width=20,
            height=20,
        ).pack(side="left", padx=5)

        ctk.CTkRadioButton(f_color_act, text="ปกติ", variable=self.var_color_click_mode, value="normal", font=("Inter", 11)).pack(
            side="right", padx=5
        )
        rb_bg_color = ctk.CTkRadioButton(
            f_color_act, text="เบื้องหลัง (BG)", variable=self.var_color_click_mode, value="background", font=("Inter", 11)
        )
        rb_bg_color.pack(side="right", padx=5)
        ToolTip(rb_bg_color, "⚠️ ส่งคำสั่งคลิกเบื้องหลัง (ไม่เลื่อนเมาส์)\n⚠️ ปลายทางอาจบล็อกคำสั่งนี้หากเป็นเบราว์เซอร์หรือเกม")

        ctk.CTkButton(
            t,
            text="เพิ่มคำสั่งเช็คสี (Add Action)",
            command=self.add_color_action,
            fg_color=COLOR_SUCCESS,
            hover_color="#059669",
            height=40,
            font=("Inter", 13, "bold"),
        ).pack(pady=(5, 5), padx=20, fill="x")
        ctk.CTkLabel(t, text="ADVANCED LOGIC (ตรวจสอบหลายจุด)", font=("Inter", 10, "bold"), text_color=COLOR_MUTED).pack(pady=(8, 3), anchor="center")
        f_multi = ctk.CTkFrame(t, fg_color=COLOR_INNER, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        f_multi.pack(fill="x", padx=15, pady=0)

        # Center align content
        self.lbl_multi_color_count = ctk.CTkLabel(f_multi, text="จุดที่เก็บไว้: 0 จุด", font=("Inter", 11), text_color=COLOR_ACCENT)
        self.lbl_multi_color_count.pack(pady=(8, 3))

        f_mb = ctk.CTkFrame(f_multi, fg_color="transparent")
        f_mb.pack(fill="x", padx=15, pady=5)

        # Grid layout for equal width buttons
        f_mb.grid_columnconfigure(0, weight=1)
        f_mb.grid_columnconfigure(1, weight=1)

        btn_add_pt = ctk.CTkButton(
            f_mb,
            text="เก็บจุดสี (Add Point)",
            command=self.add_multi_color_point,
            fg_color=COLOR_CARD,
            hover_color=COLOR_INNER,
            font=("Inter", 11, "bold"),
            height=32,
        )
        btn_add_pt.grid(row=0, column=0, padx=5, sticky="ew")
        ToolTip(btn_add_pt, "ไปจิ้มสีเพิ่มอีกจุด เพื่อเอามาเช็คพร้อมกัน")

        btn_clr_pt = ctk.CTkButton(
            f_mb,
            text="ล้างทั้งหมด",
            command=self.clear_multi_color_points,
            fg_color=COLOR_DANGER,
            hover_color=COLOR_DANGER,
            font=("Inter", 11, "bold"),
            height=32,
            text_color="white",
        )
        btn_clr_pt.grid(row=0, column=1, padx=5, sticky="ew")

        f_logic = ctk.CTkFrame(f_multi, fg_color="transparent")
        f_logic.pack(pady=(3, 8))  # Center pack without fill=x

        ctk.CTkLabel(f_logic, text="เงื่อนไข:", font=("Inter", 11), text_color="#94a3b8").pack(side="left")
        self.var_multi_color_logic = ctk.StringVar(value="AND")

        rb_and = ctk.CTkRadioButton(
            f_logic, text="ทุกจุด (AND)", variable=self.var_multi_color_logic, value="AND", font=("Inter", 12), fg_color=COLOR_ACCENT
        )
        rb_and.pack(side="left", padx=10)
        ToolTip(rb_and, "ต้องเจอสีครบทุกจุด ถึงจะทำงาน")

        rb_or = ctk.CTkRadioButton(
            f_logic, text="บางจุด (OR)", variable=self.var_multi_color_logic, value="OR", font=("Inter", 12), fg_color=COLOR_ACCENT
        )
        rb_or.pack(side="left", padx=10)
        ToolTip(rb_or, "ขอแค่เจอสีสักจุดนึง ก็ทำงานได้")

        self.var_multi_color_stop = ctk.BooleanVar(value=False)
        f_mc_act = ctk.CTkFrame(t, fg_color="transparent")
        f_mc_act.pack(fill="x", padx=15, pady=0)
        ctk.CTkCheckBox(
            f_mc_act,
            text="จบงานทันที (Stop After)",
            variable=self.var_multi_color_stop,
            font=("Inter", 11),
            text_color=COLOR_MUTED,
            border_color=BORDER_COLOR,
            width=20,
            height=20,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            t,
            text="เพิ่มการเช็คหลายสี (Multi-Color Action)",
            command=self.add_multi_color_action,
            fg_color="#9333ea",
            hover_color="#7e22ce",
            height=40,
            font=("Inter", 13, "bold"),
        ).pack(pady=(5, 10), padx=20, fill="x")

    def setup_log_tab(self):
        t = self.tab_log
        ctk.CTkLabel(t, text="SYSTEM ACTIVITY", font=("Inter", 10, "bold"), text_color=COLOR_MUTED).pack(pady=(20, 5), anchor="center")
        self.txt_log = ctk.CTkTextbox(
            t, height=350, font=("JetBrains Mono", 11), fg_color=COLOR_BG, border_width=1, border_color=BORDER_COLOR, text_color=COLOR_MUTED
        )
        self.txt_log.pack(fill="both", expand=True, padx=15, pady=5)

        f_btn = ctk.CTkFrame(t, fg_color="transparent")
        f_btn.pack(fill="x", padx=15, pady=15)

        # Use simple pack logic with fixed widths that fit
        ctk.CTkButton(f_btn, text="ล้าง (Clear)", command=self.clear_logs, height=35, fg_color="#334155", font=("Inter", 11, "bold"), width=100).pack(
            side="left", padx=(0, 10)
        )
        ctk.CTkButton(
            f_btn,
            text="Export Log",
            command=self.export_logs,
            height=35,
            fg_color=COLOR_INNER,
            border_width=1,
            border_color=BORDER_COLOR,
            font=("Inter", 11, "bold"),
            width=120,
        ).pack(side="left")

        # Debug Toggles
        f_deb = ctk.CTkFrame(f_btn, fg_color="transparent")
        f_deb.pack(side="right")
        self.var_debug_overlay = ctk.BooleanVar(value=False)

        # Adjusted padding to prevent cutoff
        ctk.CTkCheckBox(
            f_deb, text="Overlay", variable=self.var_debug_overlay, font=("Inter", 11), text_color=COLOR_MUTED, border_color="#334155"
        ).pack(side="right", padx=(5, 0))
        ctk.CTkCheckBox(f_deb, text="Debug", variable=self.var_debug_mode, font=("Inter", 11), text_color=COLOR_MUTED, border_color="#334155").pack(
            side="right", padx=(10, 5)
        )

    def clear_logs(self):
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.configure(state="disabled")

    def export_logs(self):
        try:
            content = self.txt_log.get("1.0", "end-1c")
            if not content.strip():
                messagebox.showwarning("แจ้งเตือน", "ไม่มีข้อมูลบันทึกให้ส่งออกครับ", parent=self)
                return
            path = filedialog.asksaveasfilename(
                defaultextension=".txt", filetypes=[("Text Files", "*.txt")], initialfile=f"log_{time.strftime('%Y%m%d_%H%M%S')}.txt"
            )
            if path:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.lbl_status.configure(text=f"✅ ส่งออก Log สำเร็จ: {os.path.basename(path)}", text_color="#2ecc71")
        except Exception as e:
            messagebox.showerror("Error", f"ไม่สามารถบันทึกไฟล์ได้: {e}", parent=self)

    def setup_stealth_tab(self):
        t = self.tab_stealth
        ctk.CTkLabel(t, text="โหมดเนียน & ป้องกันการจับได้ (Anti-Detection)", font=("Inter", 12, "bold"), text_color=COLOR_MUTED).pack(
            pady=(20, 5), anchor="w", padx=22
        )
        f_stealth = ctk.CTkFrame(t, fg_color=COLOR_INNER, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        f_stealth.pack(fill="x", padx=15, pady=0)

        # Human Curves
        f_move = ctk.CTkFrame(f_stealth, fg_color="transparent")
        f_move.pack(fill="x", padx=15, pady=(15, 10))
        cb_move = ctk.CTkCheckBox(
            f_move,
            text="ขยับเมาส์โค้งมนแบบคน (Human Curves)",
            variable=self.var_stealth_move,
            font=("Inter", 12),
            fg_color=COLOR_ACCENT,
            border_color="#334155",
            command=self.auto_save_presets,
        )
        cb_move.pack(side="left")
        ToolTip(cb_move, "บังคับให้เมาส์สไลด์เป็นเส้นโค้ง ไม่ใช่วาร์ปไปทันที\n(เฉพาะการคลิกแบบปกติ หน้าจอ)")

        # Jitter
        f_jitter = ctk.CTkFrame(f_stealth, fg_color="transparent")
        f_jitter.pack(fill="x", padx=15, pady=5)

        cb_jitter = ctk.CTkCheckBox(
            f_jitter,
            text="สุ่มจุดคลิกรอบเป้าหมาย (Random Jitter)",
            variable=self.var_stealth_jitter,
            font=("Inter", 12),
            fg_color=COLOR_ACCENT,
            border_color="#334155",
            command=self.auto_save_presets,
        )
        cb_jitter.pack(side="left")
        ToolTip(cb_jitter, "ไม่คลิกที่เดิมเป๊ะๆ ทุกครั้ง จะขยับนิดๆ หน่อยๆ ให้เหมือนคน")

        f_j_val = ctk.CTkFrame(f_stealth, fg_color="transparent")
        f_j_val.pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkLabel(f_j_val, text="รัศมีความมั่ว (Radius):", font=("Inter", 11), text_color="#94a3b8").pack(side="left", padx=(30, 10))

        self.slider_jitter = ctk.CTkSlider(
            f_j_val,
            from_=1,
            to=20,
            number_of_steps=19,
            width=150,
            variable=self.var_stealth_jitter_radius,
            progress_color=COLOR_ACCENT,
            button_color=COLOR_ACCENT,
            command=lambda v: self.auto_save_presets(),
        )
        self.slider_jitter.pack(side="left")
        ToolTip(self.slider_jitter, "ยิ่งเยอะ ยิ่งคลิกไกลจากจุดเดิมมาก")

        ctk.CTkLabel(f_j_val, textvariable=self.var_stealth_jitter_radius, font=("JetBrains Mono", 11, "bold"), text_color=COLOR_ACCENT).pack(
            side="left", padx=10
        )
        ctk.CTkLabel(f_j_val, text="px", font=("Inter", 10), text_color="#64748b").pack(side="left")
        ctk.CTkLabel(t, text="ADVANCED SYSTEM STEALTH", font=("Inter", 10, "bold"), text_color=COLOR_MUTED).pack(pady=(15, 5), anchor="w", padx=22)
        f_tech = ctk.CTkFrame(t, fg_color=COLOR_INNER, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        f_tech.pack(fill="x", padx=15, pady=0)
        f_options = ctk.CTkFrame(f_tech, fg_color="transparent")
        f_options.pack(fill="x", padx=20, pady=(15, 10))
        ctk.CTkCheckBox(
            f_options,
            text="ซ่อนหน้าต่าง (Auto Minimize)",
            variable=self.var_stealth_hide_window,
            font=("Inter", 12),
            fg_color=COLOR_ACCENT,
            border_color="#334155",
            command=self.auto_save_presets,
        ).pack(side="left", padx=(0, 20))
        ctk.CTkCheckBox(
            f_options,
            text="สุ่มชื่อหน้าต่าง (Random Title)",
            variable=self.var_stealth_random_title,
            command=self.on_random_title_toggle,
            font=("Inter", 12),
            fg_color=COLOR_ACCENT,
            border_color="#334155",
        ).pack(side="left")
        f_send = ctk.CTkFrame(f_tech, fg_color="transparent")
        f_send.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkCheckBox(
            f_send,
            text="ใช้ SendInput API (Low-level Emulation)",
            variable=self.var_stealth_sendinput,
            font=("Inter", 12),
            fg_color=COLOR_ACCENT,
            border_color="#334155",
            command=self.auto_save_presets,
        ).pack(side="left")

        ctk.CTkLabel(t, text="โหมด Stealth อาจทำให้การทำงานช้าลงเพื่อความเสมือนมนุษย์", text_color="#f59e0b", font=("Inter", 11, "italic")).pack(
            pady=10
        )

    def setup_wait_tab(self):
        t = self.tab_wait
        ctk.CTkLabel(t, text="TIME DELAY CONFIGURATION", font=("Inter", 10, "bold"), text_color=COLOR_MUTED).pack(pady=(20, 5), anchor="w", padx=22)
        f_wait = ctk.CTkFrame(t, fg_color=COLOR_INNER, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        f_wait.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(f_wait, text="หยุดรอเป็นเวลา (วินาที):", font=("Inter", 12), text_color="#94a3b8").pack(pady=(20, 5))
        self.entry_wait = ctk.CTkEntry(
            f_wait,
            width=200,
            height=60,
            font=("JetBrains Mono", 28, "bold"),
            justify="center",
            placeholder_text="0.5",
            fg_color="#020617",
            border_color=COLOR_ACCENT,
        )
        self.entry_wait.insert(0, "1.0")
        self.entry_wait.pack(pady=(10, 25))
        self.var_wait_stop = ctk.BooleanVar(value=False)
        f_wait_act = ctk.CTkFrame(t, fg_color="transparent")
        f_wait_act.pack(fill="x", padx=15, pady=0)
        ctk.CTkCheckBox(
            f_wait_act,
            text="จบงานทันที (Stop After)",
            variable=self.var_wait_stop,
            font=("Inter", 11),
            text_color=COLOR_MUTED,
            border_color=BORDER_COLOR,
            width=20,
            height=20,
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            t,
            text="เพิ่มขั้นตอนการรอ (ADD WAIT ACTION)",
            command=self.add_wait_action,
            fg_color=COLOR_SUCCESS,
            hover_color="#059669",
            height=50,
            font=("Inter", 14, "bold"),
        ).pack(pady=15, padx=20, fill="x")

    def update_list_display(self):
        for widget in self.scroll_actions.winfo_children():
            widget.destroy()
        self.action_widgets = []

        # Thread-safe snapshot of actions for display
        with self.actions_lock:
            display_actions = list(self.actions)

        if not display_actions:
            lbl_empty = ctk.CTkLabel(
                self.scroll_actions,
                text="ยังไม่มีขั้นตอนในระบบ\n(เลือกเครื่องมือทางขวาเพื่อเพิ่มคำสั่งเข้า Script)",
                font=("Segoe UI", 12),
                text_color="#7f8c8d",
            )
            lbl_empty.pack(pady=40)
            return

        # Sync logic labels with UI
        if hasattr(self, "refresh_label_dropdowns"):
            self.refresh_label_dropdowns()

        # Calculate Indentation Levels
        indents = [0] * len(display_actions)
        label_map = {}
        for i, act in enumerate(display_actions):
            if act["type"] == "logic_label":
                label_map[act.get("name")] = i

        # Forward Pass (IF/JUMP Skipped Blocks)
        for i, act in enumerate(display_actions):
            if act["type"] in ["logic_if", "logic_jump", "logic_else"]:
                target = act.get("target_label")
                if target in label_map:
                    t_idx = label_map[target]
                    if t_idx > i:  # Forward Jump
                        for k in range(i + 1, t_idx):
                            # Skip indentation for "Else Label" (Label immediately following ELSE)
                            if act["type"] == "logic_else" and k == i + 1 and display_actions[k]["type"] == "logic_label":
                                continue
                            indents[k] += 1

        # Backward Pass (Loops)
        for i, act in enumerate(display_actions):
            if act["type"] == "logic_jump":
                target = act.get("target_label")
                if target in label_map:
                    t_idx = label_map[target]
                    if t_idx < i:  # Backward Jump - Loop Body
                        for k in range(t_idx + 1, i + 1):
                            indents[k] += 1

        for i, action in enumerate(display_actions):
            self.create_action_widget(i, action, indent=indents[i])

    def create_action_widget(self, index, action_data, indent=0):
        t = action_data["type"]
        is_selected = index == getattr(self, "selected_index", -1)

        # Color Logic
        base_col = COLOR_CARD
        border_col = BORDER_COLOR
        border_width = 1

        if is_selected:
            base_col = COLOR_INNER
            border_col = COLOR_ACCENT
            border_width = 2
        elif t == "logic_label":
            base_col = ("#dbeafe", "#172554")  # Light Blue / Dark Blue for labels
            border_col = ("#3b82f6", "#1d4ed8")

        # Main Card Frame (Indented)
        base_padx = 12
        indent_px = indent * 25
        if indent_px > 200:
            indent_px = 200

        f = ctk.CTkFrame(self.scroll_actions, fg_color=base_col, corner_radius=8, border_width=border_width, border_color=border_col)
        f.pack(fill="x", pady=2, padx=(base_padx + indent_px, base_padx))
        self.action_widgets.append(f)

        # Click Handler
        def on_click(event):
            self.selected_index = index
            self.update_list_display()

        f.bind("<Button-1>", on_click)

        # --- Left: Index Badge ---
        f_left = ctk.CTkFrame(f, fg_color="transparent", width=35)
        f_left.pack(side="left", padx=(5, 2), pady=1)
        f_left.bind("<Button-1>", on_click)

        # Pill/Circle for Index
        idx_bg = COLOR_ACCENT if is_selected else "#334155"
        f_idx = ctk.CTkFrame(f_left, width=20, height=20, corner_radius=10, fg_color=idx_bg)
        f_idx.pack(anchor="center")
        f_idx.pack_propagate(False)  # Force size

        lbl_idx = ctk.CTkLabel(f_idx, text=f"{index+1}", font=("Inter", 9, "bold"), text_color="white")
        lbl_idx.place(relx=0.5, rely=0.5, anchor="center")
        lbl_idx.bind("<Button-1>", on_click)
        f_idx.bind("<Button-1>", on_click)

        # --- Middle: Content ---
        f_content = ctk.CTkFrame(f, fg_color="transparent")
        f_content.pack(side="left", fill="both", expand=True, padx=10, pady=1)
        f_content.bind("<Button-1>", on_click)

        # Title Map
        title_map = {
            "click": "Mouse Click",
            "text": "Type Text",
            "hotkey": "Press Key",
            "wait": "Delay",
            "image_search": "Find Image",
            "color_search": "Find Color",
            "multi_color_check": "Multi-Color",
            "ocr_search": "OCR Read",
            "logic_if": "IF (ถ้า...เป็นจริง)",
            "logic_jump": "GOTO (กระโดดไปที่)",
            "logic_else": "ELSE (ถ้าไม่จริงทำส่วนนี้)",
            "logic_label": "จุดอ้างอิง (Label)",
            "var_set": "Set Variable",
            "var_math": "Calculate",
        }

        # Description Logic
        desc = ""
        detail_col = "#94a3b8"

        if t == "click":
            mode = "BG" if action_data.get("mode") == "background" else "Normal"
            btn = action_data["button"].title()
            desc = f"{btn} Click at ({action_data['x']}, {action_data['y']}) [{mode}]"
        elif t == "text":
            desc = f"\"{action_data['content']}\""
        elif t == "hotkey":
            desc = f"Key: {action_data['content'].upper()}"
        elif t == "wait":
            desc = f"{action_data['seconds']}s"
        elif t == "color_search":
            desc = f"RGB {action_data['rgb']}"
            if action_data.get("region"):
                desc += " [Region]"
        elif t == "image_search":
            import os

            fname = os.path.basename(action_data["path"])
            if len(fname) > 25:
                fname = fname[:22] + "..."
            conf = int(action_data.get("confidence", 0.75) * 100)
            img_mode_txt = "WAIT" if action_data.get("mode", "wait") == "wait" else "ONCE"
            desc = f"File: {fname} ({conf}%) [{img_mode_txt}]"
        elif t == "multi_color_check":
            desc = f"{len(action_data.get('points', []))} Points ({action_data.get('logic', 'AND')})"
        elif t == "logic_label":
            desc = f"ชื่อจุด: {action_data.get('name')}"
        elif t == "logic_jump":
            desc = f"ข้ามไปทำงานที่ -> {action_data.get('target_label')}"
        elif t == "logic_else":
            desc = "(ถ้าเงื่อนไขจริงทำเสร็จแล้ว ให้ข้ามส่วนนี้ไป)"
        elif t == "logic_if":
            cond_map = {
                "image_found": "เจอรูปภาพ",
                "color_match": "สีตรงกัน",
                "not_image_found": "ไม่เจอรูป",
                "not_color_match": "สีไม่ตรง",
                "var_compare": "ตัวแปรตรงเงื่อนไข",
            }
            c_txt = cond_map.get(action_data.get("condition"), action_data.get("condition"))
            desc = f"ตรวจสอบ: {c_txt}"
            if action_data.get("condition") == "image_found" and "confidence" in action_data:
                desc += f" ({int(action_data['confidence']*100)}%)"
        elif t == "ocr_search":
            desc = f"ค้นหาข้อความ \"{action_data.get('text')}\""
        elif t == "var_set":
            desc = f"${action_data.get('name')} = {action_data.get('value')}"
        elif t == "var_math":
            desc = f"${action_data.get('name')} {action_data.get('op')} {action_data.get('value')}"

        # Title Label
        lbl_title = ctk.CTkLabel(f_content, text=title_map.get(t, "Action"), font=("Inter", 12, "bold"), text_color=COLOR_ACCENT, anchor="w")
        lbl_title.pack(side="left")
        lbl_title.bind("<Button-1>", on_click)

        # Detail Label
        lbl_desc = ctk.CTkLabel(f_content, text=desc, font=("Inter", 11), text_color=detail_col, anchor="w")
        lbl_desc.pack(side="left", padx=10)
        lbl_desc.bind("<Button-1>", on_click)

        # --- Right: Badges ---
        badges = []
        if action_data.get("stop_after"):
            badges.append(("STOP", COLOR_DANGER))
        if t == "logic_label":
            badges.append(("⚓", None))

        if badges:
            f_right = ctk.CTkFrame(f, fg_color="transparent")
            f_right.pack(side="right", padx=10)
            f_right.bind("<Button-1>", on_click)

            for txt, col in badges:
                if col:
                    ctk.CTkLabel(f_right, text=txt, font=("Inter", 9, "bold"), text_color=col).pack(side="right")
                else:
                    ctk.CTkLabel(f_right, text=txt, font=("Segoe UI Emoji", 14)).pack(side="right")
