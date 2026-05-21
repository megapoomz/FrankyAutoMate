import customtkinter as ctk
import os
from tkinter import messagebox
from core.constants import COLOR_INNER, BORDER_COLOR, COLOR_ACCENT, COLOR_SUCCESS, GRADIENT_END, GRADIENT_START, COLOR_MUTED

class VisionMixin:
    """Handles AI Vision & OCR UI and actions"""
    
    def setup_vision_tab(self):
        t = self.tab_vision
        
        # --- Section 1: OCR (Text Recognition) ---
        ctk.CTkLabel(t, text="ค้นหาด้วยข้อความ (OCR SEARCH)", font=("Tahoma", 10, "bold"), text_color="#64748b").pack(pady=(20, 5), anchor="w", padx=22)
        f_ocr = ctk.CTkFrame(t, fg_color=COLOR_INNER, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        f_ocr.pack(fill="x", padx=15, pady=0)
        
        f_row1 = ctk.CTkFrame(f_ocr, fg_color="transparent")
        f_row1.pack(fill="x", padx=15, pady=15)
        ctk.CTkLabel(f_row1, text="ข้อความที่ต้องการ:", font=("Tahoma", 12)).pack(side="left", padx=(0, 10))
        self.entry_ocr_text = ctk.CTkEntry(f_row1, placeholder_text="เช่น 'ยืนยัน', 'Next'...", height=35, font=("Tahoma", 12))
        self.entry_ocr_text.pack(side="left", fill="x", expand=True)
        
        f_row2 = ctk.CTkFrame(f_ocr, fg_color="transparent")
        f_row2.pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkLabel(f_row2, text="โหมด:", font=("Tahoma", 12)).pack(side="left", padx=(0, 10))
        self.var_ocr_mode = ctk.StringVar(value="wait")
        ctk.CTkOptionMenu(f_row2, values=["wait", "once"], variable=self.var_ocr_mode, width=120, fg_color="#1e293b").pack(side="left")
        
        self.var_ocr_click_val = ctk.BooleanVar(value=True)
        self.cb_ocr_click = ctk.CTkCheckBox(f_row2, text="คลิกเมื่อพบ", variable=self.var_ocr_click_val, font=("Tahoma", 11))
        self.cb_ocr_click.pack(side="left", padx=15)
        
        ctk.CTkLabel(f_row2, text="ปุ่ม:", font=("Tahoma", 11), text_color=COLOR_MUTED).pack(side="left", padx=5)
        self.var_ocr_click_btn = ctk.StringVar(value="left")
        menu_btn = ctk.CTkOptionMenu(f_row2, values=["left", "right", "double"], variable=self.var_ocr_click_btn, width=80, fg_color="#334155")
        menu_btn.pack(side="left")

        ctk.CTkLabel(f_row2, text="โหมด:", font=("Tahoma", 11), text_color=COLOR_MUTED).pack(side="left", padx=(10, 5))
        self.var_ocr_click_mode = ctk.StringVar(value="normal")
        menu_mode = ctk.CTkOptionMenu(f_row2, values=["normal", "background"], variable=self.var_ocr_click_mode, width=100, fg_color="#334155")
        menu_mode.pack(side="left")

        # Region selector for OCR (Very important for performance)
        f_reg = ctk.CTkFrame(t, fg_color="transparent")
        f_reg.pack(fill="x", padx=15, pady=10)
        self.btn_ocr_region = ctk.CTkButton(f_reg, text="ตีกรอบพื้นที่ (แนะนำ)", command=self.start_pick_region, 
                                            fg_color="#334155", height=32, font=("Tahoma", 11))
        self.btn_ocr_region.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ctk.CTkButton(t, text="เพิ่มขั้นตอน OCR (ADD VISION ACTION)", command=self.add_ocr_action, 
                       fg_color="#2563eb", hover_color="#1d4ed8", height=45, font=("Tahoma", 13, "bold")).pack(pady=10, padx=20, fill="x")

        # --- Portable Info ---
        f_info = ctk.CTkFrame(t, fg_color="#0f172a", corner_radius=10)
        f_info.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(f_info, text="โหมดพกพา (PORTABLE AI)\nรวมไฟล์ AI ไว้ในโครงการแล้ว ไม่ต้องโหลดใหม่", 
                      font=("Tahoma", 11, "bold"), text_color=COLOR_SUCCESS).pack(pady=(15, 10))
        
        ctk.CTkLabel(f_info, text="สำหรับผู้พัฒนา: นำโฟลเดอร์ Tesseract-OCR\nไปวางที่: bin/tesseract/ เพื่อบิ้วพร้อมแอป", 
                      font=("Tahoma", 10), text_color="#94a3b8").pack(pady=(0, 10))
        
        self.btn_manual_tess = ctk.CTkButton(f_info, text="เลือกไฟล์ tesseract.exe เอง", 
                                              command=self.browse_tesseract_path,
                                              fg_color="#334155", hover_color="#475569", height=32, font=("Tahoma", 11, "bold"))
        self.btn_manual_tess.pack(pady=(0, 10), padx=20, fill="x")

        self.btn_install_dep = ctk.CTkButton(f_info, text="ติดตั้ง AI Dependencies อัตโนมัติ", 
                                              command=self.install_ai_dependencies,
                                              fg_color="#10b981", hover_color="#059669", height=32, font=("Tahoma", 11, "bold"))
        self.btn_install_dep.pack(pady=(0, 15), padx=20, fill="x")

    def browse_tesseract_path(self):
        from tkinter import filedialog
        p = filedialog.askopenfilename(title="เลือกไฟล์ tesseract.exe", filetypes=[("Executable", "*.exe")])
        if p and "tesseract.exe" in p.lower():
             import pytesseract
             pytesseract.pytesseract.tesseract_cmd = p
             self.lbl_status.configure(text=f"เชื่อมต่อ Tesseract สำเร็จ: {os.path.basename(p)}", text_color=COLOR_SUCCESS)
             messagebox.showinfo("สำเร็จ", f"ตั้งค่าตำแหน่ง Tesseract ใหม่แล้วที่:\n{p}", parent=self)

    def install_ai_dependencies(self):
        from utils.dep_installer import DependencyInstaller
        self.btn_install_dep.configure(state="disabled", text="กำลังดำเนินการ...")
        self.lbl_status.configure(text="เริ่มกระบวนการติดตั้ง Dependencies...", text_color=COLOR_ACCENT)
        
        def update_status(msg):
            self.lbl_status.configure(text=msg)
            if "สำเร็จ" in msg or "ผิดพลาด" in msg:
                self.btn_install_dep.configure(state="normal", text="ติดตั้ง AI Dependencies อัตโนมัติ")

        DependencyInstaller.install_pytesseract(update_status)
        DependencyInstaller.setup_tesseract(self, update_status)

    def add_ocr_action(self):
        txt = self.entry_ocr_text.get().strip()
        if not txt:
            messagebox.showwarning("แจ้งเตือน", "กรุณาระบุข้อความที่ต้องการค้นหา", parent=self)
            return
            
        action = {
            "type": "ocr_search",
            "text": txt,
            "mode": self.var_ocr_mode.get(),
            "do_click": self.var_ocr_click_val.get(),
            "region": self.current_region,
            "click_mode": self.var_ocr_click_mode.get(),
            "button": self.var_ocr_click_btn.get()
        }
        
        self.actions.append(action)
        self.update_list_display()
        self.lbl_status.configure(text=f"เพิ่ม OCR: \"{txt}\"", text_color=COLOR_SUCCESS)
        self.current_region = None # Reset
        if hasattr(self, 'lbl_region_info'):
            self.lbl_region_info.configure(text="พื้นที่: ทั้งจอ", text_color="gray")
