import random
import customtkinter as ctk
import tkinter as tk
from core.constants import COLOR_INNER, BORDER_COLOR, COLOR_ACCENT, COLOR_SUCCESS, GRADIENT_END, GRADIENT_START, COLOR_MUTED

class LogicMixin:
    """Handles logic-based UI and action creation (If/Then, Jumps, Labels)"""
    
    def setup_logic_tab(self):
        t = self.tab_logic
        from ui.ui_mixin import ToolTip
        self.logic_label_list = ["(เลือก Label)"]
        
        # --- Section 1: Labels (Anchors) ---
        ctk.CTkLabel(t, text="สร้างจุดอ้างอิง (Label)", font=("Inter", 12, "bold"), text_color=COLOR_MUTED).pack(pady=(10, 3), anchor="w", padx=22)
        f_label = ctk.CTkFrame(t, fg_color=COLOR_INNER, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        f_label.pack(fill="x", padx=15, pady=0)
        
        f_l_row = ctk.CTkFrame(f_label, fg_color="transparent")
        f_l_row.pack(fill="x", padx=15, pady=10)
        self.entry_label_name = ctk.CTkEntry(f_l_row, placeholder_text="ตั้งชื่อจุด (เช่น: start_loop)", height=35, font=("Inter", 12))
        self.entry_label_name.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ToolTip(self.entry_label_name, "ตั้งชื่อจุดนี้ไว้ เพื่อให้คำสั่งอื่นกระโดดกลับมาได้")
        
        btn_label = ctk.CTkButton(f_l_row, text="วางจุดนี้", command=self.add_label_action, width=100, height=35, fg_color="#334155", font=("Inter", 11, "bold"))
        btn_label.pack(side="right")
        ToolTip(btn_label, "สร้างจุดอ้างอิง ณ ตำแหน่งนี้ของสคริปต์")

        # --- Section 2: If/Else Condition ---
        ctk.CTkLabel(t, text="ถ้า...ให้ไป... (Condition)", font=("Inter", 12, "bold"), text_color=COLOR_MUTED).pack(pady=(10, 3), anchor="w", padx=22)
        f_if = ctk.CTkFrame(t, fg_color=COLOR_INNER, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        f_if.pack(fill="x", padx=15, pady=0)
        
        
        f_if_row1 = ctk.CTkFrame(f_if, fg_color="transparent")
        f_if_row1.pack(fill="x", padx=15, pady=(10, 3))
        
        ctk.CTkLabel(f_if_row1, text="1. ถ้า (If):", font=("Inter", 12)).pack(side="left", padx=(0, 10))
        self.var_logic_condition = ctk.StringVar(value="image_found")
        menu_cond = ctk.CTkOptionMenu(f_if_row1, values=["image_found", "color_match"], variable=self.var_logic_condition, width=140, fg_color="#1e293b", dropdown_fg_color="#0f172a", command=self.update_logic_source_ui)
        menu_cond.pack(side="left")
        
        ctk.CTkLabel(f_if_row1, text="เป็นจริง", font=("Inter", 12, "bold"), text_color=COLOR_SUCCESS).pack(side="left", padx=10)
        
        # Source Selection UI (Dynamic)
        self.f_logic_source = ctk.CTkFrame(f_if, fg_color="#1e293b", corner_radius=6)
        self.f_logic_source.pack(fill="x", padx=15, pady=5)
        
        # Will be populated by update_logic_source_ui
        self.lbl_logic_source_status = ctk.CTkLabel(self.f_logic_source, text="-", text_color="#94a3b8", font=("Inter", 11))
        self.lbl_logic_source_status.pack(side="left", padx=10, pady=5)
        self.btn_logic_source_action = ctk.CTkButton(self.f_logic_source, text="...", width=80, height=25)
        self.btn_logic_source_action.pack(side="right", padx=10, pady=5)
        
        # Confidence Slider Row (only visible for image_found)
        self.f_logic_conf = ctk.CTkFrame(f_if, fg_color="#1e293b", corner_radius=6)
        self.f_logic_conf.pack(fill="x", padx=15, pady=(0, 5))
        
        self.lbl_logic_conf_head = ctk.CTkLabel(self.f_logic_conf, text="ความแม่นยำ (75%)", font=("Inter", 11, "bold"), text_color=COLOR_ACCENT)
        self.lbl_logic_conf_head.pack(side="left", padx=(10, 5), pady=5)
        
        def update_logic_conf_lbl(v):
            self.lbl_logic_conf_head.configure(text=f"ความแม่นยำ ({int(float(v)*100)}%)")
            
        self.slider_logic_conf = ctk.CTkSlider(self.f_logic_conf, from_=0.5, to=1.0, variable=self.var_logic_conf, command=update_logic_conf_lbl, height=16, width=150)
        self.slider_logic_conf.pack(side="left", padx=(5, 10), pady=5, fill="x", expand=True)
        ToolTip(self.slider_logic_conf, "ปรับความแม่นยำในการค้นหารูปภาพ (0.5 - 1.0)\nค่ายิ่งสูง ยิ่งต้องเหมือนมาก")
        
        f_if_row2 = ctk.CTkFrame(f_if, fg_color="transparent")
        f_if_row2.pack(fill="x", padx=15, pady=(3, 10))
        
        # Structure Mode Selection
        ctk.CTkLabel(f_if_row2, text="รูปแบบ (Structure):", font=("Inter", 12)).pack(side="left", padx=(0, 10))
        self.var_logic_struct = ctk.StringVar(value="Block (IF)")
        self.opt_logic_struct = ctk.CTkOptionMenu(f_if_row2, variable=self.var_logic_struct, 
                                                  values=["Jump Only", "Block (IF)", "Block (IF/ELSE)"],
                                                  command=self.update_logic_struct_ui, width=140)
        self.opt_logic_struct.pack(side="left")
        ToolTip(self.opt_logic_struct, "เลือกรูปแบบโครงสร้างเงื่อนไข")
        
        # Target Label (Only for Jump Mode)
        self.f_target_label = ctk.CTkFrame(f_if_row2, fg_color="transparent")
        # Initially hidden — shown only when "Jump Only" selected via update_logic_struct_ui()
        ctk.CTkLabel(self.f_target_label, text="ข้ามไปที่:", font=("Inter", 12)).pack(side="left", padx=(5, 5))
        self.opt_logic_target = ctk.CTkOptionMenu(self.f_target_label, values=self.logic_label_list, height=32, fg_color="#0f172a", width=130)
        self.opt_logic_target.pack(side="left")
        
        self.after(500, lambda: [self.update_logic_source_ui(), self.update_logic_struct_ui()]) # Init UI
        
        ctk.CTkButton(t, text="เพิ่มเงื่อนไข (Add Condition)", command=self.add_if_action, 
                       fg_color="#9333ea", hover_color="#7e22ce", height=40, font=("Inter", 13, "bold")).pack(pady=5, padx=20, fill="x")

        # --- Section 3: Force Jump ---
        ctk.CTkLabel(t, text="สั่งกระโดด/วนลูป (Jump/Loop)", font=("Inter", 12, "bold"), text_color=COLOR_MUTED).pack(pady=(8, 3), anchor="w", padx=22)
        f_jump = ctk.CTkFrame(t, fg_color=COLOR_INNER, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        f_jump.pack(fill="x", padx=15, pady=0)
        
        f_j_row = ctk.CTkFrame(f_jump, fg_color="transparent")
        f_j_row.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(f_j_row, text="กระโดดไปที่:", font=("Inter", 12)).pack(side="left", padx=(0, 10))
        self.opt_jump_target = ctk.CTkOptionMenu(f_j_row, values=self.logic_label_list, height=35, fg_color="#0f172a", width=150)
        self.opt_jump_target.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ToolTip(self.opt_jump_target, "เลือกจุดที่ต้องการให้วนกลับไป หรือข้ามไป")
        
        ctk.CTkButton(f_j_row, text="เพิ่มคำสั่ง", command=self.add_jump_action, width=100, height=35, fg_color="#334155", font=("Inter", 11, "bold")).pack(side="right")

        # --- Section 4: Quick Shortcuts ---
         # (Removed for cleaner UI as per user request to simplify)

    def refresh_label_dropdowns(self):
        if not hasattr(self, 'opt_logic_target'): return # Tab not setup yet
        labels = [a["name"] for a in self.actions if a["type"] == "logic_label"]
        self.logic_label_list = labels if labels else ["(ไม่มี Label)"]
        try:
            self.opt_logic_target.configure(values=self.logic_label_list)
            self.opt_jump_target.configure(values=self.logic_label_list)
            if hasattr(self, 'combo_vif_label'):
                self.combo_vif_label.configure(values=self.logic_label_list)
                
            # Only set if currently selected value is not in the new list
            if self.opt_logic_target.get() not in self.logic_label_list:
                self.opt_logic_target.set(self.logic_label_list[0])
            if self.opt_jump_target.get() not in self.logic_label_list:
                self.opt_jump_target.set(self.logic_label_list[0])
            if hasattr(self, 'combo_vif_label') and self.combo_vif_label.get() not in self.logic_label_list:
                self.combo_vif_label.set(self.logic_label_list[0])
        except Exception: pass

    def quick_loop_shortcut(self):
        """Adds a 'Start' label and a 'Jump to Start' pair automatically"""
        loop_name = f"Loop_{random.randint(100, 999)}"
        with self.actions_lock:
            self.actions.append({"type": "logic_label", "name": f"{loop_name}_Start"})
            self.actions.append({"type": "wait", "seconds": 1.0})
            self.actions.append({"type": "logic_jump", "target_label": f"{loop_name}_Start"})
        self.update_list_display()
        self.auto_save_presets()
        self.lbl_status.configure(text=f"สร้าง Loop อัตโนมัติ: {loop_name}", text_color=COLOR_SUCCESS)

    def add_label_action(self):
        name = self.entry_label_name.get().strip()
        if not name: return
        action = {"type": "logic_label", "name": name}
        self.add_action_item(action)
        self.refresh_label_dropdowns()
        self.lbl_status.configure(text=f"เพิ่มจุดอ้างอิง: {name}", text_color=COLOR_SUCCESS)
        self.entry_label_name.delete(0, "end")

    def add_if_action(self):
        cond = self.var_logic_condition.get()
        mode = self.var_logic_struct.get()
        target = self.opt_logic_target.get()
        
        # --- 1. Jump Only Mode ---
        if mode == "Jump Only":
            if target == "(ไม่มี Label)": return
            action = {
                "type": "logic_if", "condition": cond, "target_label": target, "jump_on": "true"
            }
            self._fill_action_params(action)
            self.add_action_item(action)
            self.lbl_status.configure(text=f"เพิ่ม IF (Jump) -> {target}", text_color=COLOR_SUCCESS)

        # --- 2. Block (IF) Mode ---
        elif mode == "Block (IF)":

            end_label = f"End_IF_{random.randint(1000, 9999)}"
            
            action = {
                "type": "logic_if", "condition": cond, "target_label": end_label, "jump_on": "false"
            }
            self._fill_action_params(action)
            with self.actions_lock:
                self.actions.append(action)
                self.actions.append({"type": "logic_label", "name": end_label})
            self.refresh_label_dropdowns()
            self.update_list_display()
            self.auto_save_presets()
            self.lbl_status.configure(text=f"เพิ่ม IF Block -> {end_label}", text_color=COLOR_SUCCESS)

        # --- 3. Block (IF/ELSE) Mode ---
        elif mode == "Block (IF/ELSE)":

            rid = random.randint(1000, 9999)
            else_label = f"Else_{rid}"
            end_label = f"End_IF_{rid}"
            
            action = {
                "type": "logic_if", "condition": cond, "target_label": else_label, "jump_on": "false"
            }
            self._fill_action_params(action)
            with self.actions_lock:
                self.actions.append(action)
                self.actions.append({"type": "logic_else", "target_label": end_label})
                self.actions.append({"type": "logic_label", "name": else_label})
                self.actions.append({"type": "logic_label", "name": end_label})
            self.refresh_label_dropdowns()
            self.update_list_display()
            self.auto_save_presets()
            self.lbl_status.configure(text=f"เพิ่ม IF/ELSE Block", text_color=COLOR_SUCCESS)
            
        self.update_list_display()
        self.auto_save_presets()

    def _fill_action_params(self, action):
        cond = action["condition"]
        if cond == "image_found":
            action["path"] = self.current_img_path
            action["region"] = self.current_region
            action["confidence"] = self.var_logic_conf.get()
        elif cond == "color_match" and self.current_color_data:
            _, _, rgb = self.current_color_data
            action["rgb"] = rgb
            action["x"] = self.current_color_data[0]
            action["y"] = self.current_color_data[1]
            try: action["tolerance"] = int(self.entry_tol.get())
            except (ValueError, TypeError): action["tolerance"] = 10

    def add_jump_action(self):
        target = self.opt_jump_target.get()
        if target == "(ไม่มี Label)": return
        action = {"type": "logic_jump", "target_label": target}
        self.add_action_item(action)
        self.lbl_status.configure(text=f"เพิ่มการกระโดดรั้งไปที่: {target}", text_color=COLOR_SUCCESS)

    def update_logic_source_ui(self, event=None):
        import os
        if not hasattr(self, 'f_logic_source'): return
        cond = self.var_logic_condition.get()
        
        if cond == "image_found":
            path = getattr(self, 'current_img_path', None)
            display = os.path.basename(path) if path else "(ยังไม่เลือกรูปภาพ)"
            if len(display) > 25: display = display[:22] + "..."
            color = "#2ecc71" if path else "#e74c3c"
            
            self.lbl_logic_source_status.configure(text=f"รูปภาพ: {display}", text_color=color)
            self.btn_logic_source_action.configure(text="เลือกรูป", command=self.browse_logic_image, fg_color="#3b82f6", hover_color="#2563eb")
            # Show confidence slider
            if hasattr(self, 'f_logic_conf'):
                self.f_logic_conf.pack(fill="x", padx=15, pady=(0, 5))
        
        elif cond == "color_match":
            data = getattr(self, 'current_color_data', None)
            if data:
                r, g, b = data[2]
                display = f"RGB({r},{g},{b}) @ {data[0]},{data[1]}"
                color = "#2ecc71"
            else:
                display = "(ยังไม่ดูดสี)"
                color = "#e74c3c"
                
            self.lbl_logic_source_status.configure(text=f"สีเป้าหมาย: {display}", text_color=color)
            self.btn_logic_source_action.configure(text="ดูดสีใหม่", command=self.pick_logic_color, fg_color="#f59e0b", hover_color="#d97706")
            # Hide confidence slider
            if hasattr(self, 'f_logic_conf'):
                self.f_logic_conf.pack_forget()

    def update_logic_struct_ui(self, event=None):
        if not hasattr(self, 'f_target_label'): return
        mode = self.var_logic_struct.get()
        if mode == "Jump Only":
            self.f_target_label.pack(side="left", padx=10)
        else:
            self.f_target_label.pack_forget()

    def browse_logic_image(self):
        # Reuse existing browse logic but refresh UI here
        self.browse_image()
        self.update_logic_source_ui()

    def pick_logic_color(self):
        # Call existing picker
        self.start_pick_color()
        self.check_picker_status(0)

    def check_picker_status(self, count=0):
        # Poll for color data update (Stop after 60 seconds)
        self.update_logic_source_ui()
        if self.state() == "normal" and count < 60: 
             self.after(1000, lambda: self.check_picker_status(count+1))
