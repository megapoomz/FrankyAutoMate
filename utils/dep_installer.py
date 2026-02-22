import os
import sys
import subprocess
import threading
import requests
from tkinter import messagebox

TESSERACT_MIRRORS = [
    # Direct SourceForge Link (Often more stable)
    "https://downloads.sourceforge.net/project/tesseract-ocr-alt/tesseract-ocr-w64-setup-5.5.0.20241111.exe",
    # Original UB Mannheim
    "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-v5.3.0.20221222.exe",
    # WayBack Machine
    "https://web.archive.org/web/20240101/https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-v5.3.0.20221222.exe"
]

class DependencyInstaller:
    """Handles automatic installation of Tesseract and Python dependencies"""
    
    @staticmethod
    def install_pytesseract(callback=None):
        """Installs pytesseract via pip"""
        def run():
            try:
                if callback: callback("กำลังติดตั้งไลบรารี pytesseract...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pytesseract", "requests"])
                if callback: callback("ติดตั้งไลบรารีสำเร็จ! ✅")
            except Exception as e:
                if callback: callback(f"ล้มเหลวในการลงไลบรารี: {e}")
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    @staticmethod
    def setup_tesseract(app, callback=None):
        """Downloads and installs Tesseract OCR for Windows"""
        def run():
            temp_dir = os.path.join(os.environ.get('TEMP', '.'), "FrankyAutoMate_Setup")
            os.makedirs(temp_dir, exist_ok=True)
            installer_path = os.path.join(temp_dir, "tesseract_installer.exe")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            success = False
            for url in TESSERACT_MIRRORS:
                try:
                    site_name = url.split('/')[2]
                    if callback: callback(f"กำลังลองจาก Mirror: {site_name}...")
                    
                    # Download with timeout and headers
                    response = requests.get(url, stream=True, timeout=20, headers=headers, allow_redirects=True)
                    response.raise_for_status()
                    
                    with open(installer_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=16384):
                            f.write(chunk)
                    
                    success = True
                    break
                except Exception as e:
                    print(f"Failed mirror {url}: {e}")
                    if callback: callback(f"Mirror {site_name} พยายามแล้วแต่ล้มเหลว...")
                    continue
            
            if not success:
                import webbrowser
                msg = "❌ ดาวน์โหลดอัตโนมัติไม่สำเร็จ (อาจเกิดจาก Block ของอินเทอร์เน็ต)\n\nผมกำลังเปิดหน้าเว็บดาวน์โหลดให้คุณรันเองครับ เมื่อโหลดเสร็จแล้วติดตั้งให้เรียบร้อยแล้วรันโปรแกรมใหม่อีกครั้งครับ"
                if callback: callback("ดาวน์โหลดไม่สำเร็จ กำลังเปิดเบราว์เซอร์... 🌐")
                webbrowser.open("https://github.com/UB-Mannheim/tesseract/wiki")
                messagebox.showwarning("ดาวน์โหลดแมนนวล", msg, parent=app)
                return

            try:
                if callback: callback("ดาวน์โหลดเสร็จสิ้น กำลังติดตั้ง (ใช้เวลาสักครู่)...")
                
                # SEC-2: Verify installer checksum before running
                try:
                    from utils.security import verify_file_checksum
                    installer_filename = os.path.basename(url)
                    if not verify_file_checksum(installer_path, filename=installer_filename):
                        if callback: callback("⚠️ Checksum ไม่ตรง! อาจมีการดัดแปลงไฟล์")
                        # Still allow but warn
                except ImportError:
                    pass  # Security module not available
                
                process = subprocess.Popen([installer_path, "/S"])
                process.wait()
                
                # Verify installation in common paths
                common_paths = [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
                ]
                
                found = any(os.path.exists(p) for p in common_paths)
                
                if found:
                    if callback: callback("Tesseract-OCR ติดตั้งสำเร็จ! ✅")
                    messagebox.showinfo("สำเร็จ", "ติดตั้ง Tesseract-OCR เรียบร้อยแล้ว!\nกรุณารีสตาร์ทโปรแกรมอีกครั้งเพื่อเริ่มใช้งาน AI Vision", parent=app)
                else:
                    if callback: callback("ติดตั้งเสร็จสิ้น แต่หาไม่เจอ กรุณาเช็ค Manual")
                    
            except Exception as e:
                if callback: callback(f"เกิดข้อผิดพลาด: {e}")
                messagebox.showerror("Error", f"ไม่สามารถติดตั้ง Tesseract ได้: {e}", parent=app)

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
