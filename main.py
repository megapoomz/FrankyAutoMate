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

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the main application
from autoclick import AutoMationApp

def main():
    """Start the Franky AutoMate application"""
    app = AutoMationApp()
    app.mainloop()

if __name__ == "__main__":
    main()
