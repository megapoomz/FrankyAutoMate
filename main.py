"""
Franky AutoMate - Main Entry Point
Run this file to start the application

Usage:
    python main.py

Or run the package:
    python -m franky
"""

import sys
import os
import ctypes

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# COMPAT-02 FIX: Try DPI Awareness V2 first (best for multi-monitor DPI changes)
try:
    # V2: DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 (Windows 10 1703+)
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except (AttributeError, OSError):
    try:
        # V1: PROCESS_PER_MONITOR_DPI_AWARE (Windows 8.1+)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # Legacy: PROCESS_DPI_AWARE (Windows Vista+)
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# Import and run the main application
from autoclick import AutoMationApp  # noqa: E402

def main():
    """Start the Franky AutoMate application"""
    app = AutoMationApp()
    app.mainloop()

if __name__ == "__main__":
    main()
