"""
CloudPrep Organizer - Main Entry Point
Run this file to launch the application.
Requirements: pip install customtkinter pillow mutagen pymediainfo
"""

import sys
import os

# Ensure the app directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.gui import CloudPrepApp

if __name__ == "__main__":
    app = CloudPrepApp()
    app.run()
