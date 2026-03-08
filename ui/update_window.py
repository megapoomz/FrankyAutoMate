import os
import sys
import threading
import zipfile
import shutil
import tempfile
import subprocess
from pathlib import Path
from tkinter import messagebox
import customtkinter as ctk
from core.constants import COLOR_BG, COLOR_ACCENT

class UpdateProgressWindow(ctk.CTkToplevel):
    def __init__(self, parent, new_version, download_url):
        super().__init__(parent)
        self.title("ระบบอัปเดตอัตโนมัติ")
        self.geometry("450x280")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(fg_color=COLOR_BG)
        self.grab_set()

        self.download_url = download_url
        self.new_version = new_version
        self.cancelled = False

        # Center
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (450 // 2)
        y = (self.winfo_screenheight() // 2) - (280 // 2)
        self.geometry(f"450x280+{x}+{y}")

        self.lbl_title = ctk.CTkLabel(self, text=f"📥 กำลังโหลดเวอร์ชัน v{new_version}", font=("Inter", 18, "bold"), text_color="white")
        self.lbl_title.pack(pady=(30, 5))

        ctk.CTkLabel(self, text="กรุณารอสักครู่ ระบบกำลังเตรียมการติดตั้ง...", font=("Inter", 12), text_color="#94a3b8").pack(pady=(0, 20))

        self.progress_bar = ctk.CTkProgressBar(self, width=350, height=12, progress_color=COLOR_ACCENT, fg_color="#1e293b")
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

        self.lbl_status = ctk.CTkLabel(self, text="0% (0.00 MB / 0.00 MB)", font=("JetBrains Mono", 12), text_color=COLOR_ACCENT)
        self.lbl_status.pack(pady=5)

        self.btn_cancel = ctk.CTkButton(self, text="ยกเลิกการโหลด", fg_color="#334155", font=("Inter", 11, "bold"), height=35, command=self.on_cancel)
        self.btn_cancel.pack(pady=20)

        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

        self.start_download()

    def on_cancel(self):
        self.cancelled = True
        self.destroy()

    def start_download(self):
        threading.Thread(target=self.do_download, daemon=True).start()

    def do_download(self):
        try:
            import requests

            temp_dir = Path(tempfile.gettempdir()) / "FrankyAutoMate_Update"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)

            zip_path = temp_dir / "update.zip"

            headers = {"User-Agent": "FrankyAutoMate-Updater"}
            response = requests.get(self.download_url, stream=True, headers=headers, timeout=120)
            total_size = int(response.headers.get("content-length", 0))

            downloaded = 0
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.cancelled:
                        return
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = downloaded / total_size
                            self.after(0, lambda p=pct, d=downloaded, t=total_size: self.update_ui(p, d, t))

            if self.cancelled:
                return

            self.after(0, lambda: self.lbl_status.configure(text="กำลังตรวจสอบไฟล์..."))

            # SEC-1: Verify checksum of downloaded file before extracting
            from utils.security import verify_file_checksum
            if not verify_file_checksum(str(zip_path), filename=f"FrankyAutoMate_v{self.new_version}.zip"):
                self.after(0, lambda: messagebox.showerror(
                    "ผิดพลาด",
                    "Checksum ไม่ตรง! ไฟล์อัปเดตอาจถูกเปลี่ยนแปลง กรุณาดาวน์โหลดใหม่",
                    parent=self
                ))
                self.after(0, self.destroy)
                return

            self.after(0, lambda: self.lbl_status.configure(text="กำลังติดตั้งอัปเดต..."))

            extract_dir = temp_dir / "extracted"
            extract_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                # Validate paths to prevent Zip Slip (path traversal)
                for member in zip_ref.namelist():
                    member_path = (extract_dir / member).resolve()
                    if not str(member_path).startswith(str(extract_dir.resolve())):
                        raise ValueError(f"Zip Slip detected: {member}")
                zip_ref.extractall(extract_dir)

            # Find exe in extracted
            exe_name = "FrankyAutoMate.exe"
            found_exe = None
            for p in extract_dir.rglob(exe_name):
                found_exe = p
                break

            if not found_exe:
                # Fallback to any exe if named differently
                for p in extract_dir.rglob("*.exe"):
                    found_exe = p
                    break

            if not found_exe:
                self.after(0, lambda: messagebox.showerror("ผิดพลาด", "ไม่พบไฟล์ .exe ในแพ็คเกจอัปเดต", parent=self))
                self.after(0, self.destroy)
                return

            self.after(1000, lambda: self.apply_update(found_exe))

        except Exception as e:
            self.after(0, lambda msg=str(e): messagebox.showerror("ผิดพลาด", f"ไม่สามารถอัปเดตได้: {msg}", parent=self))
            self.after(0, self.destroy)

    def update_ui(self, pct, downloaded, total):
        self.progress_bar.set(pct)
        d_mb = downloaded / (1024 * 1024)
        t_mb = total / (1024 * 1024)
        self.lbl_status.configure(text=f"{int(pct*100)}% ({d_mb:.1f} MB / {t_mb:.1f} MB)")

    def apply_update(self, new_exe):
        try:
            current_exe = sys.executable
            if not getattr(sys, "frozen", False):
                messagebox.showinfo("Dev Mode", "โหมดนักพัฒนา: ดาวน์โหลดเสร็จแล้วแต่จะไม่ทำการเปลี่ยนไฟล์จริง")
                self.destroy()
                return

            # Sanitize paths to prevent command injection
            def safe_path(p):
                """Remove potentially dangerous characters from paths for batch script"""
                import unicodedata
                # SEC-04 FIX: Normalize Unicode first (NFKC converts fullwidth chars like ＆ to &)
                result = unicodedata.normalize("NFKC", str(Path(p).resolve()))
                # Aggressive sanitization — strip ALL batch-special chars
                for ch in ('"', "'", "&", "|", ">", "<", "^", "%", "!", ";", "@",
                           "\n", "\r", "(", ")", "`", "{", "}", "$", "~", ".."):
                    result = result.replace(ch, "")
                return result

            safe_new_exe = safe_path(new_exe)
            safe_current_exe = safe_path(current_exe)
            safe_exe_basename = safe_path(os.path.basename(current_exe))

            # Validate parent_dir is inside temp before allowing rmdir
            resolved_parent = Path(new_exe).resolve().parent.parent
            temp_root = Path(tempfile.gettempdir()).resolve()
            if not str(resolved_parent).startswith(str(temp_root)):
                raise ValueError(f"Cleanup dir '{resolved_parent}' is outside temp directory — aborting for safety")
            safe_parent_dir = safe_path(resolved_parent)

            script_path = Path(tempfile.gettempdir()) / "franky_automate_updater.bat"

            batch_content = f"""@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title Franky AutoMate Updater
echo ========================================
echo   Franky AutoMate Auto-Updater
echo ========================================
echo.

echo [1/3] Waiting for application to exit...
taskkill /F /PID {os.getpid()} >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/3] Replacing executable...
set RETRIES=0
:RETRY_COPY
copy /Y "{safe_new_exe}" "{safe_current_exe}" >nul 2>&1
if errorlevel 1 (
    set /a RETRIES+=1
    if !RETRIES! lss 5 (
        echo    Retry !RETRIES!/5 - File still locked, waiting...
        taskkill /F /PID {os.getpid()} >nul 2>&1
        timeout /t 2 /nobreak >nul
        goto RETRY_COPY
    ) else (
        echo [ERROR] Could not replace file after 5 attempts!
        echo Please manually copy from: "{safe_new_exe}"
        echo To: "{safe_current_exe}"
        pause
        exit /b 1
    )
)

echo [3/3] Cleaning up...
rmdir /S /Q "{safe_parent_dir}" >nul 2>&1

echo.
echo Update Complete! Starting application...
start "" "{safe_current_exe}"
del "%~f0" & exit
"""
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(batch_content)

            subprocess.Popen(["cmd", "/c", str(script_path)], creationflags=subprocess.CREATE_NEW_CONSOLE)
            os._exit(0)

        except Exception as e:
            messagebox.showerror("ผิดพลาด", f"ไม่สามารถติดตั้งอัปเดตได้: {e}", parent=self)
            self.destroy()
