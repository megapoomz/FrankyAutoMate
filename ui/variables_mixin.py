import customtkinter as ctk
from tkinter import messagebox
from core.constants import COLOR_INNER, COLOR_ACCENT, COLOR_MUTED, BORDER_COLOR


class VariablesMixin:
    """Handles UI and action logic for Variables and Advanced Loops (Phase 3)"""

    def setup_vars_tab(self):
        t = self.tab_vars
        from ui.ui_mixin import ToolTip

        # --- Header ---
        ctk.CTkLabel(t, text="ตัวแปรและการนับ (Variables)", font=("Inter", 12, "bold"), text_color=COLOR_MUTED).pack(
            pady=(10, 5), anchor="w", padx=22
        )

        # --- Section 1: Set Variable ---
        ctk.CTkLabel(t, text="สร้าง/กำหนดค่าตัวแปร (Set)", font=("Inter", 12, "bold"), text_color=COLOR_MUTED).pack(pady=(8, 3), anchor="w", padx=22)
        f_set = ctk.CTkFrame(t, fg_color=COLOR_INNER, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        f_set.pack(fill="x", padx=15, pady=0)

        f_in1 = ctk.CTkFrame(f_set, fg_color="transparent")
        f_in1.pack(pady=5)  # Center by not filling x

        self.entry_var_name = ctk.CTkEntry(f_in1, placeholder_text="ชื่อ (เช่น count)", width=130)
        self.entry_var_name.pack(side="left", padx=(0, 10))
        ToolTip(self.entry_var_name, "ตั้งชื่อกล่องเก็บข้อมูล เช่น count, score")

        ctk.CTkLabel(f_in1, text="=", font=("Inter", 14, "bold"), text_color=COLOR_ACCENT).pack(side="left")

        self.entry_var_val = ctk.CTkEntry(f_in1, placeholder_text="ค่าเริ่ม (เช่น 0)", width=90)
        self.entry_var_val.pack(side="left", padx=(10, 0))
        ToolTip(self.entry_var_val, "ใส่ตัวเลขเริ่มต้น")

        ctk.CTkButton(f_set, text="เพิ่มคำสั่ง Set", command=self.add_var_set_action, fg_color="#334155", hover_color="#475569", height=30).pack(
            pady=10, padx=20, fill="x"
        )

        # --- Section 2: Math Operation ---
        ctk.CTkLabel(t, text="การคำนวณ (Math)", font=("Inter", 12, "bold"), text_color=COLOR_MUTED).pack(pady=(8, 3), anchor="w", padx=22)
        f_math = ctk.CTkFrame(t, fg_color=COLOR_INNER, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        f_math.pack(fill="x", padx=15, pady=0)

        f_in2 = ctk.CTkFrame(f_math, fg_color="transparent")
        f_in2.pack(pady=8)  # Center packing

        self.entry_math_name = ctk.CTkEntry(f_in2, placeholder_text="ชื่อตัวแปร", width=100)
        self.entry_math_name.pack(side="left", padx=5)

        self.combo_math_op = ctk.CTkComboBox(f_in2, values=["บวกเพิ่ม (+)", "ลบออก (-)", "คูณ (*)", "หาร (/)"], width=110)
        self.combo_math_op.set("บวกเพิ่ม (+)")
        self.combo_math_op.pack(side="left", padx=5)

        self.entry_math_val = ctk.CTkEntry(f_in2, placeholder_text="จำนวน", width=60)
        self.entry_math_val.insert(0, "1")
        self.entry_math_val.pack(side="left", padx=5)
        ToolTip(self.entry_math_val, "ใส่จำนวนที่ต้องการบวก/ลบ")

        ctk.CTkButton(f_math, text="เพิ่มคำสั่งคำนวณ", command=self.add_var_math_action, fg_color="#334155", hover_color="#475569", height=30).pack(
            pady=(0, 10), padx=20, fill="x"
        )

        # --- Section 3: Variable IF ---
        ctk.CTkLabel(t, text="เช็คเงื่อนไขตัวแปร (Check Variable)", font=("Inter", 12, "bold"), text_color=COLOR_MUTED).pack(
            pady=(8, 3), anchor="w", padx=22
        )
        f_vif = ctk.CTkFrame(t, fg_color=COLOR_INNER, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        f_vif.pack(fill="x", padx=15, pady=0)

        f_in3 = ctk.CTkFrame(f_vif, fg_color="transparent")
        f_in3.pack(pady=8)  # Center packing

        ctk.CTkLabel(f_in3, text="ถ้า", font=("Inter", 12)).pack(side="left")
        self.entry_vif_left = ctk.CTkEntry(f_in3, placeholder_text="ชื่อตัวแปร", width=90)
        self.entry_vif_left.pack(side="left", padx=5)

        self.combo_vif_op = ctk.CTkComboBox(f_in3, values=["==", "!=", ">", "<", ">=", "<="], width=60)
        self.combo_vif_op.set("==")
        self.combo_vif_op.pack(side="left", padx=2)

        self.entry_vif_right = ctk.CTkEntry(f_in3, placeholder_text="ค่าเปรียบเทียบ", width=90)
        self.entry_vif_right.pack(side="left", padx=5)

        ctk.CTkLabel(f_vif, text="เป็นจริง ให้กระโดดไปที่:").pack(pady=(0, 5))
        self.combo_vif_label = ctk.CTkComboBox(f_vif, values=["(Refresh)"], width=200)
        self.combo_vif_label.pack(pady=5)
        ToolTip(self.combo_vif_label, "ถ้าเงื่อนไขเป็นจริง จะให้ข้ามไปทำงานที่จุดไหน")

        ctk.CTkButton(f_vif, text="เพิ่มเงื่อนไข", command=self.add_var_if_action, fg_color="#2563eb", hover_color="#1d4ed8", height=32).pack(
            pady=8, padx=20, fill="x"
        )

    def add_var_set_action(self):
        name = self.entry_var_name.get().strip()
        val = self.entry_var_val.get().strip()
        if not name:
            return messagebox.showwarning("เตือน", "กรุณาใส่ชื่อตัวแปร", parent=self)

        # Try to cast to number if it looks like one
        try:
            if "." in val:
                val = float(val)
            else:
                val = int(val)
        except (ValueError, TypeError):
            pass

        self.add_action_item({"type": "var_set", "name": name, "value": val})

    def add_var_math_action(self):
        name = self.entry_math_name.get().strip()
        op_text = self.combo_math_op.get()
        val = self.entry_math_val.get().strip()

        if not name:
            return messagebox.showwarning("เตือน", "กรุณาใส่ชื่อตัวแปร", parent=self)

        op_map = {"บวกเพิ่ม (+)": "add", "ลบออก (-)": "sub", "คูณ (*)": "mul", "หาร (/)": "div"}
        op = op_map.get(op_text, "add")

        # Convert val to number if possible (prevent float() errors during execution)
        if not val.startswith("$"):
            try:
                if "." in val:
                    val = float(val)
                else:
                    val = int(val)
            except (ValueError, TypeError):
                pass

        self.add_action_item({"type": "var_math", "name": name, "op": op, "value": val})

    def add_var_if_action(self):
        left = self.entry_vif_left.get().strip()
        op = self.combo_vif_op.get()
        right = self.entry_vif_right.get().strip()
        target = self.combo_vif_label.get()

        if not left or not target or target == "(Refresh)":
            return messagebox.showwarning("เตือน", "กรุณาระบุเงื่อนไขและ Label เป้าหมาย", parent=self)

        # Auto-prepend $ so _resolve_value treats left as variable name
        if not left.startswith("$"):
            left = f"${left}"

        self.add_action_item(
            {"type": "logic_if", "condition": "var_compare", "left": left, "op": op, "right": right, "target_label": target, "jump_on": "true"}
        )
