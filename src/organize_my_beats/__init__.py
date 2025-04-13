"""Organize My Beats - Music Management Application"""

import sys
import tkinter as tk
from tkinter import messagebox
from PyQt6.QtWidgets import QApplication
from .gui import ModernMusicOrganizerApp
from .advanced_gui import MusicOrganizerAdvanced

def run_basic_gui():
    """Run the basic GUI with customtkinter"""
    try:
        import customtkinter as ctk

        # Make sure we're using the right setup
        ctk.set_appearance_mode("dark")

        # Initialize app without TkinterDnD requirement
        app = ModernMusicOrganizerApp()
        app.mainloop()
    except Exception as e:
        print(f"Error running basic GUI: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")

def run_advanced_gui():
    """Run the advanced GUI with PyQt6"""
    try:
        app = QApplication(sys.argv)
        window = MusicOrganizerAdvanced()
        window.apply_dark_theme()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error running advanced GUI: {e}")

def run(args=None):
    """Run the application with specified arguments"""
    if args and "--advanced" in args:
        run_advanced_gui()
    else:
        run_basic_gui()

if __name__ == "__main__":
    run(sys.argv[1:])
