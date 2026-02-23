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

# Enable DPI awareness for proper coordinate mapping on HiDPI displays
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()  # Fallback for older Windows
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
