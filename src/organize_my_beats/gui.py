"""Modern Music Organizer with Advanced Features"""

import os
import shutil
import threading
from pathlib import Path
from datetime import datetime
from mutagen import File as MutagenFile
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from tkinter.ttk import Style, Progressbar
import tkinter.font as tkFont
import platform
import json
from PIL import Image, ImageTk
import sys
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import customtkinter as ctk
from typing import Dict, List, Optional, Tuple
import webbrowser
from matplotlib.figure import Figure
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QPushButton, QLabel, QLineEdit)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor
from tkinterdnd2 import DND_FILES, TkinterDnD
import psutil
from .player_view import AdvancedMusicPlayer

AUDIO_EXTENSIONS = [".mp3", ".flac", ".m4a", ".ogg", ".wav", ".wma", ".aac"]

class ModernMusicOrganizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure the window
        self.title("Organize My Beats")
        self.geometry("1400x900")

        # Set the theme and color scheme
        self.accent_colors = {
            "light": {
                "primary": "#007AFF",
                "secondary": "#5856D6",
                "success": "#34C759",
                "warning": "#FF9500",
                "danger": "#FF3B30"
            },
            "dark": {
                "primary": "#0A84FF",
                "secondary": "#5E5CE6",
                "success": "#32D74B",
                "warning": "#FF9F0A",
                "danger": "#FF453A"
            }
        }

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Initialize drag and drop (this will be enabled if TkinterDnD is properly installed)
        self.dnd_enabled = False
        self.enable_drag_and_drop()

        # Load configuration
        self.config = self.load_config()

        # Initialize processing state
        self.is_processing = False
        self.total_files = 0
        self.processed_files = 0

        # Create the main layout
        self.create_sidebar()
        self.create_header()
        self.create_main_content()

        # Initialize views
        self.views = {}
        self.current_view = None

        # Create player view
        self.player_view = None

        # Start system monitoring
        self.start_system_monitoring()

        # Show initial view
        self.show_dashboard()

    def start_system_monitoring(self):
        """Start monitoring system resources"""
        def update_stats():
            if hasattr(self, 'cpu_label'):
                cpu_usage = psutil.cpu_percent()
                self.cpu_label.configure(text=f"CPU: {cpu_usage}%")
            if hasattr(self, 'cpu_progress'):
                self.cpu_progress.set(cpu_usage / 100)
            if hasattr(self, 'memory_label'):
                mem = psutil.virtual_memory()
                self.memory_label.configure(text=f"Memory: {mem.percent}%")
            if hasattr(self, 'memory_progress'):
                self.memory_progress.set(mem.percent / 100)
            self.after(1000, update_stats)
        update_stats()

    def load_config(self):
        config_path = os.path.join(os.path.expanduser("~"), ".organize_my_beats_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                return json.load(f)
        return {"music_dirs": [], "theme": "dark", "auto_organize": True}

    def save_config(self):
        config_path = os.path.join(os.path.expanduser("~"), ".organize_my_beats_config.json")
        with open(config_path, "w") as f:
            json.dump(self.config, f)

    def create_sidebar(self):
        # Create sidebar frame with gradient effect
        self.sidebar = ctk.CTkFrame(
            self,
            width=280,
            corner_radius=0,
            fg_color=("gray90", "gray17")
        )
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)
        self.sidebar.pack_propagate(False)

        # App logo/title with custom styling
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", pady=20)

        self.logo_label = ctk.CTkLabel(
            logo_frame,
            text="Organize\nMy Beats",
            font=ctk.CTkFont(family="Helvetica", size=28, weight="bold"),
            text_color=self.accent_colors["dark"]["primary"]
        )
        self.logo_label.pack()

        # Version info
        version_label = ctk.CTkLabel(
            logo_frame,
            text="v1.0",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray70")
        )
        version_label.pack(pady=(0, 10))

        # System stats section
        stats_frame = ctk.CTkFrame(
            self.sidebar,
            fg_color=("gray85", "gray20"),
            corner_radius=10
        )
        stats_frame.pack(fill="x", padx=15, pady=10)

        # CPU Usage with progress bar
        cpu_frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
        cpu_frame.pack(fill="x", padx=10, pady=5)

        self.cpu_label = ctk.CTkLabel(
            cpu_frame,
            text="CPU: 0%",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.cpu_label.pack(side="left", padx=5)

        self.cpu_progress = ctk.CTkProgressBar(
            cpu_frame,
            width=120,
            height=6,
            corner_radius=3
        )
        self.cpu_progress.pack(side="right", padx=5)
        self.cpu_progress.set(0)

        # Memory Usage with progress bar
        mem_frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
        mem_frame.pack(fill="x", padx=10, pady=5)

        self.memory_label = ctk.CTkLabel(
            mem_frame,
            text="Memory: 0%",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.memory_label.pack(side="left", padx=5)

        self.memory_progress = ctk.CTkProgressBar(
            mem_frame,
            width=120,
            height=6,
            corner_radius=3
        )
        self.memory_progress.pack(side="right", padx=5)
        self.memory_progress.set(0)

        # Navigation section
        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", pady=20)

        nav_label = ctk.CTkLabel(
            nav_frame,
            text="NAVIGATION",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray60")
        )
        nav_label.pack(anchor="w", padx=20, pady=(0, 10))

        # Navigation buttons with icons and hover effects
        nav_buttons = [
            ("🏠 Dashboard", self.show_dashboard, "View overview and quick actions"),
            ("🎵 Player", self.show_player, "Play and manage your music"),
            ("📁 Files", self.show_files, "Browse and manage your music files"),
            ("📊 Statistics", self.show_statistics, "View detailed analytics"),
            ("🔍 Search", self.show_search, "Search your music library"),
            ("📱 Mobile Sync", self.show_mobile_sync, "Sync with mobile devices"),
            ("⚙️ Settings", self.show_settings, "Configure application settings")
        ]

        for text, command, tooltip in nav_buttons:
            button_frame = ctk.CTkFrame(nav_frame, fg_color="transparent")
            button_frame.pack(fill="x", pady=2)

            btn = ctk.CTkButton(
                button_frame,
                text=text,
                command=command,
                width=240,
                height=45,
                corner_radius=8,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray75", "gray28"),
                anchor="w",
                font=ctk.CTkFont(size=14)
            )
            btn.pack(side="left", padx=15)

            # Create tooltip
            self.create_tooltip(btn, tooltip)

        # Bottom section with user info
        bottom_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", pady=20)

        # Help button
        help_btn = ctk.CTkButton(
            bottom_frame,
            text="❓ Help & Support",
            command=self.show_help,
            width=240,
            height=40,
            corner_radius=8,
            fg_color=self.accent_colors["dark"]["secondary"],
            hover_color=("gray70", "gray30"),
            font=ctk.CTkFont(size=13)
        )
        help_btn.pack(padx=15, pady=5)

    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")

            label = tk.Label(
                tooltip,
                text=text,
                justify='left',
                background="#2B2B2B",
                foreground="white",
                relief='solid',
                borderwidth=1,
                font=("Helvetica", 11)
            )
            label.pack()

            def hide_tooltip():
                tooltip.destroy()

            widget.tooltip = tooltip
            widget.bind('<Leave>', lambda e: hide_tooltip())

        widget.bind('<Enter>', show_tooltip)

    def show_help(self):
        """Show help and support dialog"""
        help_window = ctk.CTkToplevel(self)
        help_window.title("Help & Support")
        help_window.geometry("600x400")

        # Add help content here
        help_frame = ctk.CTkFrame(help_window)
        help_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            help_frame,
            text="Help & Support",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=10)

        # Add help sections
        sections = [
            ("Getting Started", "Learn how to use the basic features of Organize My Beats"),
            ("Advanced Features", "Discover powerful organization and analysis tools"),
            ("Troubleshooting", "Find solutions to common issues"),
            ("Contact Support", "Get help from our support team")
        ]

        for title, desc in sections:
            section_frame = ctk.CTkFrame(help_frame, fg_color="transparent")
            section_frame.pack(fill="x", pady=5)

            ctk.CTkLabel(
                section_frame,
                text=title,
                font=ctk.CTkFont(size=14, weight="bold")
            ).pack(anchor="w")

            ctk.CTkLabel(
                section_frame,
                text=desc,
                font=ctk.CTkFont(size=12)
            ).pack(anchor="w")

    def create_header(self):
        # Create header frame with glass effect
        self.header = ctk.CTkFrame(
            self,
            height=80,
            corner_radius=0,
            fg_color=("gray95", "gray15")
        )
        self.header.pack(side="top", fill="x", padx=0, pady=0)

        # Left section - Search
        search_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        search_frame.pack(side="left", padx=20, pady=10)

        # Search bar with icon
        search_container = ctk.CTkFrame(
            search_frame,
            fg_color=("gray85", "gray25"),
            corner_radius=10,
            height=45
        )
        search_container.pack(side="left")
        search_container.pack_propagate(False)

        search_icon = ctk.CTkLabel(
            search_container,
            text="🔍",
            width=20,
            font=ctk.CTkFont(size=14)
        )
        search_icon.pack(side="left", padx=(15, 5))

        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            search_container,
            placeholder_text="Search music files...",
            width=300,
            height=35,
            border_width=0,
            fg_color="transparent",
            font=ctk.CTkFont(size=13)
        )
        self.search_entry.pack(side="left", padx=(0, 15), pady=5)

        # Search filters
        filter_frame = ctk.CTkFrame(search_frame, fg_color="transparent")
        filter_frame.pack(side="left", padx=10)

        self.search_filters = {
            "title": tk.BooleanVar(value=True),
            "artist": tk.BooleanVar(value=True),
            "album": tk.BooleanVar(value=True),
            "genre": tk.BooleanVar(value=False)
        }

        for filter_name, var in self.search_filters.items():
            filter_btn = ctk.CTkButton(
                filter_frame,
                text=filter_name.title(),
                width=70,
                height=30,
                corner_radius=15,
                fg_color=("gray75", "gray30"),
                text_color=("gray20", "gray90"),
                hover_color=("gray65", "gray40"),
                command=lambda n=filter_name: self.toggle_filter(n)
            )
            filter_btn.pack(side="left", padx=2)

        # Right section - Quick Actions
        actions_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        actions_frame.pack(side="right", padx=20)

        # Scan Library button with progress indicator
        self.scan_button = ctk.CTkButton(
            actions_frame,
            text="🔄 Scan Library",
            width=130,
            height=40,
            corner_radius=8,
            fg_color=self.accent_colors["dark"]["primary"],
            hover_color=("gray70", "gray30"),
            font=ctk.CTkFont(size=13),
            command=self.scan_library
        )
        self.scan_button.pack(side="left", padx=5)

        # Quick Organize button
        self.organize_button = ctk.CTkButton(
            actions_frame,
            text="✨ Quick Organize",
            width=130,
            height=40,
            corner_radius=8,
            fg_color=self.accent_colors["dark"]["success"],
            hover_color=("gray70", "gray30"),
            font=ctk.CTkFont(size=13),
            command=self.quick_organize
        )
        self.organize_button.pack(side="left", padx=5)

        # Settings button
        self.settings_button = ctk.CTkButton(
            actions_frame,
            text="⚙️",
            width=40,
            height=40,
            corner_radius=8,
            fg_color="transparent",
            hover_color=("gray75", "gray30"),
            font=ctk.CTkFont(size=16),
            command=self.show_settings
        )
        self.settings_button.pack(side="left", padx=5)

    def toggle_filter(self, filter_name):
        """Toggle search filter and update UI"""
        current_value = self.search_filters[filter_name].get()
        self.search_filters[filter_name].set(not current_value)
        self.update_search()

    def update_search(self):
        """Update search results based on current filters"""
        query = self.search_entry.get()
        active_filters = [
            name for name, var in self.search_filters.items()
            if var.get()
        ]
        # Implement search logic here
        pass

    def create_main_content(self):
        # Create main content area
        self.main_content = ctk.CTkFrame(self)
        self.main_content.pack(side="right", fill="both", expand=True, padx=20, pady=20)

    def show_dashboard(self):
        self.clear_main_content()

        # Create scrollable dashboard
        dashboard_scroll = ctk.CTkScrollableFrame(
            self.main_content,
            fg_color="transparent"
        )
        dashboard_scroll.pack(fill="both", expand=True)

        # Welcome section
        welcome_frame = ctk.CTkFrame(
            dashboard_scroll,
            fg_color=("gray90", "gray17"),
            corner_radius=15
        )
        welcome_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            welcome_frame,
            text="Welcome back!",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.accent_colors["dark"]["primary"]
        ).pack(padx=20, pady=(20, 5))

        ctk.CTkLabel(
            welcome_frame,
            text="Here's an overview of your music library",
            font=ctk.CTkFont(size=14),
            text_color=("gray40", "gray60")
        ).pack(padx=20, pady=(0, 20))

        # Statistics cards in a grid
        stats_frame = ctk.CTkFrame(dashboard_scroll, fg_color="transparent")
        stats_frame.pack(fill="x", padx=20, pady=10)
        stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        stats = [
            ("Total Tracks", "1,234", "🎵", self.accent_colors["dark"]["primary"]),
            ("Total Size", "45.6 GB", "💾", self.accent_colors["dark"]["secondary"]),
            ("Genres", "15", "🎼", self.accent_colors["dark"]["success"]),
            ("Artists", "89", "👤", self.accent_colors["dark"]["warning"])
        ]

        for i, (title, value, icon, color) in enumerate(stats):
            self.create_stat_card(stats_frame, title, value, icon, color, i)

        # Recent Activity section
        activity_frame = ctk.CTkFrame(
            dashboard_scroll,
            fg_color=("gray90", "gray17"),
            corner_radius=15
        )
        activity_frame.pack(fill="x", padx=20, pady=10)

        # Activity header with view all button
        activity_header = ctk.CTkFrame(activity_frame, fg_color="transparent")
        activity_header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            activity_header,
            text="Recent Activity",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(side="left")

        ctk.CTkButton(
            activity_header,
            text="View All →",
            font=ctk.CTkFont(size=12),
            width=80,
            height=30,
            fg_color="transparent",
            hover_color=("gray75", "gray30")
        ).pack(side="right")

        # Activity list
        self.create_recent_activity(activity_frame)

        # Quick Actions section
        actions_frame = ctk.CTkFrame(
            dashboard_scroll,
            fg_color=("gray90", "gray17"),
            corner_radius=15
        )
        actions_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            actions_frame,
            text="Quick Actions",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(padx=20, pady=(20, 10))

        self.create_quick_actions(actions_frame)

    def create_stat_card(self, parent, title, value, icon, color, column):
        card = ctk.CTkFrame(
            parent,
            fg_color=("gray85", "gray20"),
            corner_radius=10
        )
        card.grid(row=0, column=column, padx=5, pady=5, sticky="nsew")

        # Icon
        ctk.CTkLabel(
            card,
            text=icon,
            font=ctk.CTkFont(size=24),
            text_color=color
        ).pack(pady=(15, 5))

        # Value
        ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=color
        ).pack(pady=5)

        # Title
        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=14),
            text_color=("gray40", "gray60")
        ).pack(pady=(5, 15))

    def create_recent_activity(self, parent):
        # Example activities
        activities = [
            ("Added new tracks", "2 minutes ago", "➕"),
            ("Organized library", "1 hour ago", "📁"),
            ("Updated metadata", "3 hours ago", "✏️"),
            ("Backup completed", "Yesterday", "💾"),
            ("Synced with mobile", "2 days ago", "📱")
        ]

        for activity, time, icon in activities:
            activity_item = ctk.CTkFrame(parent, fg_color="transparent")
            activity_item.pack(fill="x", padx=20, pady=5)

            # Icon
            ctk.CTkLabel(
                activity_item,
                text=icon,
                font=ctk.CTkFont(size=16),
                width=30
            ).pack(side="left", padx=5)

            # Activity text
            text_frame = ctk.CTkFrame(activity_item, fg_color="transparent")
            text_frame.pack(side="left", fill="x", expand=True, padx=5)

            ctk.CTkLabel(
                text_frame,
                text=activity,
                font=ctk.CTkFont(size=13),
                anchor="w"
            ).pack(fill="x")

            ctk.CTkLabel(
                text_frame,
                text=time,
                font=ctk.CTkFont(size=11),
                text_color=("gray40", "gray60"),
                anchor="w"
            ).pack(fill="x")

    def create_quick_actions(self, parent):
        actions_grid = ctk.CTkFrame(parent, fg_color="transparent")
        actions_grid.pack(fill="x", padx=20, pady=(0, 20))
        actions_grid.grid_columnconfigure((0, 1, 2), weight=1)

        actions = [
            ("Add Music", self.add_music, "📥", self.accent_colors["dark"]["primary"]),
            ("Organize Now", self.organize_music, "✨", self.accent_colors["dark"]["success"]),
            ("Export Report", self.export_report, "📊", self.accent_colors["dark"]["warning"]),
            ("Scan Library", self.scan_library, "🔄", self.accent_colors["dark"]["secondary"]),
            ("Backup", self.backup_library, "💾", self.accent_colors["dark"]["primary"]),
            ("Settings", self.show_settings, "⚙️", self.accent_colors["dark"]["secondary"])
        ]

        for i, (text, command, icon, color) in enumerate(actions):
            row = i // 3
            col = i % 3

            action_btn = ctk.CTkButton(
                actions_grid,
                text=f"{icon} {text}",
                command=command,
                width=150,
                height=40,
                corner_radius=8,
                fg_color=color,
                hover_color=("gray70", "gray30"),
                font=ctk.CTkFont(size=13)
            )
            action_btn.grid(row=row, column=col, padx=5, pady=5)

    def backup_library(self):
        """Backup the music library"""
        # Implement backup functionality
        pass

    def show_files(self):
        self.clear_main_content()

        # Create files view with toolbar
        files_container = ctk.CTkFrame(self.main_content, fg_color="transparent")
        files_container.pack(fill="both", expand=True)

        # Toolbar
        toolbar = ctk.CTkFrame(files_container, height=50, fg_color=("gray90", "gray17"))
        toolbar.pack(fill="x", padx=20, pady=(0, 10))
        toolbar.pack_propagate(False)

        # Left side - View options
        view_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        view_frame.pack(side="left", padx=10)

        self.view_var = tk.StringVar(value="grid")

        grid_btn = ctk.CTkButton(
            view_frame,
            text="Grid View",
            width=90,
            height=30,
            command=lambda: self.switch_view("grid"),
            fg_color=self.accent_colors["dark"]["primary"] if self.view_var.get() == "grid" else "transparent"
        )
        grid_btn.pack(side="left", padx=5)

        list_btn = ctk.CTkButton(
            view_frame,
            text="List View",
            width=90,
            height=30,
            command=lambda: self.switch_view("list"),
            fg_color=self.accent_colors["dark"]["primary"] if self.view_var.get() == "list" else "transparent"
        )
        list_btn.pack(side="left", padx=5)

        # Right side - Sort and filter options
        options_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        options_frame.pack(side="right", padx=10)

        # Sort dropdown
        sort_options = ["Name", "Date Modified", "Size", "Type"]
        sort_menu = ctk.CTkOptionMenu(
            options_frame,
            values=sort_options,
            width=120,
            height=30,
            command=self.sort_files
        )
        sort_menu.pack(side="right", padx=5)

        # Filter button
        filter_btn = ctk.CTkButton(
            options_frame,
            text="🔍 Filter",
            width=90,
            height=30,
            command=self.show_filter_dialog
        )
        filter_btn.pack(side="right", padx=5)

        # Create scrollable frame for files
        self.files_frame = ctk.CTkScrollableFrame(
            files_container,
            fg_color=("gray95", "gray17")
        )
        self.files_frame.pack(fill="both", expand=True, padx=20)

        # Show files in current view mode
        self.refresh_files()

    def switch_view(self, view_type):
        """Switch between grid and list view"""
        self.view_var.set(view_type)
        self.refresh_files()

    def refresh_files(self):
        """Refresh the files view"""
        # Clear current view
        for widget in self.files_frame.winfo_children():
            widget.destroy()

        if self.view_var.get() == "grid":
            self.create_grid_view()
        else:
            self.create_list_view()

    def create_grid_view(self):
        """Create grid view of files"""
        # Example files data
        files = [
            ("Track 1.mp3", "3:45", "4.2 MB", "🎵"),
            ("Album Art.jpg", "", "1.8 MB", "🖼️"),
            ("Playlist.m3u", "", "2 KB", "📄"),
            ("Track 2.flac", "5:12", "28.4 MB", "🎵"),
            ("Track 3.wav", "4:18", "42.1 MB", "🎵"),
            ("Lyrics.txt", "", "1 KB", "📝")
        ]

        # Configure grid
        self.files_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        for i, (name, duration, size, icon) in enumerate(files):
            row = i // 4
            col = i % 4

            # File card
            card = ctk.CTkFrame(
                self.files_frame,
                fg_color=("gray85", "gray20"),
                corner_radius=10
            )
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            # Icon
            ctk.CTkLabel(
                card,
                text=icon,
                font=ctk.CTkFont(size=32)
            ).pack(pady=(15, 5))

            # File name
            ctk.CTkLabel(
                card,
                text=name,
                font=ctk.CTkFont(size=13, weight="bold"),
                wraplength=150
            ).pack(pady=5)

            # File info
            if duration:
                ctk.CTkLabel(
                    card,
                    text=duration,
                    font=ctk.CTkFont(size=12),
                    text_color=("gray40", "gray60")
                ).pack(pady=2)

            ctk.CTkLabel(
                card,
                text=size,
                font=ctk.CTkFont(size=12),
                text_color=("gray40", "gray60")
            ).pack(pady=(2, 15))

    def create_list_view(self):
        """Create list view of files"""
        # Headers
        headers_frame = ctk.CTkFrame(self.files_frame, fg_color="transparent")
        headers_frame.pack(fill="x", padx=10, pady=5)

        headers = ["Name", "Duration", "Size", "Type", "Date Modified"]
        for header in headers:
            ctk.CTkLabel(
                headers_frame,
                text=header,
                font=ctk.CTkFont(size=12, weight="bold"),
                width=150
            ).pack(side="left", padx=5)

        # Example files data
        files = [
            ("Track 1.mp3", "3:45", "4.2 MB", "Audio", "2024-03-20"),
            ("Album Art.jpg", "", "1.8 MB", "Image", "2024-03-19"),
            ("Playlist.m3u", "", "2 KB", "Playlist", "2024-03-18"),
            ("Track 2.flac", "5:12", "28.4 MB", "Audio", "2024-03-17"),
            ("Track 3.wav", "4:18", "42.1 MB", "Audio", "2024-03-16"),
            ("Lyrics.txt", "", "1 KB", "Text", "2024-03-15")
        ]

        for file_data in files:
            item_frame = ctk.CTkFrame(
                self.files_frame,
                fg_color=("gray85", "gray20"),
                corner_radius=5,
                height=40
            )
            item_frame.pack(fill="x", padx=10, pady=2)
            item_frame.pack_propagate(False)

            for text in file_data:
                ctk.CTkLabel(
                    item_frame,
                    text=text,
                    font=ctk.CTkFont(size=12),
                    width=150,
                    anchor="w"
                ).pack(side="left", padx=5, pady=10)

    def sort_files(self, option):
        """Sort files based on selected option"""
        # Implement sorting logic
        self.refresh_files()

    def show_filter_dialog(self):
        """Show filter options dialog"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Filter Files")
        dialog.geometry("400x500")

        # Add filter options
        filter_frame = ctk.CTkFrame(dialog)
        filter_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # File type filters
        ctk.CTkLabel(
            filter_frame,
            text="File Types",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))

        types = ["Audio Files", "Images", "Playlists", "Lyrics", "All Files"]
        for file_type in types:
            ctk.CTkCheckBox(
                filter_frame,
                text=file_type
            ).pack(anchor="w", pady=2)

        # Date range
        ctk.CTkLabel(
            filter_frame,
            text="Date Range",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(20, 10))

        date_frame = ctk.CTkFrame(filter_frame, fg_color="transparent")
        date_frame.pack(fill="x")

        ctk.CTkEntry(
            date_frame,
            placeholder_text="Start Date"
        ).pack(side="left", padx=5)

        ctk.CTkEntry(
            date_frame,
            placeholder_text="End Date"
        ).pack(side="left", padx=5)

        # Size range
        ctk.CTkLabel(
            filter_frame,
            text="Size Range",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(20, 10))

        size_frame = ctk.CTkFrame(filter_frame, fg_color="transparent")
        size_frame.pack(fill="x")

        ctk.CTkEntry(
            size_frame,
            placeholder_text="Min Size"
        ).pack(side="left", padx=5)

        ctk.CTkEntry(
            size_frame,
            placeholder_text="Max Size"
        ).pack(side="left", padx=5)

        # Apply button
        ctk.CTkButton(
            filter_frame,
            text="Apply Filters",
            command=dialog.destroy
        ).pack(pady=20)

    def show_statistics(self):
        self.clear_main_content()

        # Create statistics view with charts
        stats_frame = ctk.CTkFrame(self.main_content)
        stats_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Add charts and graphs here
        self.create_statistics_charts(stats_frame)

    def create_statistics_charts(self, parent):
        # Genre distribution chart
        fig = Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)

        # Example data
        genres = ["Rock", "Pop", "Jazz", "Electronic", "Classical"]
        counts = [30, 25, 15, 20, 10]

        ax.pie(counts, labels=genres, autopct='%1.1f%%')
        ax.set_title("Genre Distribution")

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(side="left", fill="both", expand=True, padx=10, pady=10)

    def show_settings(self):
        self.clear_main_content()

        # Create settings view
        settings_frame = ctk.CTkFrame(self.main_content)
        settings_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Add settings options
        self.create_settings_options(settings_frame)

    def create_settings_options(self, parent):
        # Theme selection
        theme_frame = ctk.CTkFrame(parent)
        theme_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            theme_frame,
            text="Theme:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left", padx=10)

        theme_var = tk.StringVar(value=self.config["theme"])
        theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=["dark", "light"],
            variable=theme_var,
            command=self.change_theme
        )
        theme_menu.pack(side="left", padx=10)

        # Auto-organize toggle
        organize_frame = ctk.CTkFrame(parent)
        organize_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            organize_frame,
            text="Auto-organize:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left", padx=10)

        auto_organize_var = tk.BooleanVar(value=self.config["auto_organize"])
        auto_organize_switch = ctk.CTkSwitch(
            organize_frame,
            text="",
            variable=auto_organize_var,
            command=self.toggle_auto_organize
        )
        auto_organize_switch.pack(side="left", padx=10)

    def clear_main_content(self):
        """Clear the main content area and hide any persistent views"""
        for widget in self.main_content.winfo_children():
            widget.pack_forget()  # Hide instead of destroy for persistent views

        # For widgets that aren't persistent or need to be destroyed
        for widget in self.main_content.winfo_children():
            if widget not in [self.player_view]:  # List of persistent widgets to keep
                widget.destroy()

    # Action methods
    def scan_library(self):
        """Scan the music library for files"""
        if self.is_processing:
            return

        # Ask user to select directory if none configured
        if not self.config.get("music_dirs"):
            dir_path = filedialog.askdirectory(title="Select Music Directory")
            if not dir_path:
                return  # User cancelled

            self.config["music_dirs"] = [dir_path]
            self.save_config()

        self.is_processing = True

        # Update button to show scanning state
        original_text = self.scan_button.cget("text")
        self.scan_button.configure(text="🔄 Scanning...")

        # In a real app, we would do the actual scanning here
        def scan_process():
            import time
            import random
            import os

            # Simulate scanning of files
            file_count = random.randint(200, 500)
            for i in range(file_count):
                # Simulate finding files
                time.sleep(0.01)

            # Restore button state
            self.after(0, lambda: self.scan_button.configure(text=original_text))
            self.is_processing = False

            # Show results
            self.after(0, lambda: messagebox.showinfo(
                "Scan Complete",
                f"Scanned {file_count} files in your music library.\n\n"
                f"Found:\n"
                f"• {random.randint(10, 30)} Artists\n"
                f"• {random.randint(20, 50)} Albums\n"
                f"• {random.randint(5, 15)} Genres"
            ))

            # Refresh dashboard stats
            self.after(0, self.show_dashboard)

        # Run in a separate thread to keep UI responsive
        import threading
        thread = threading.Thread(target=scan_process)
        thread.daemon = True
        thread.start()

    def add_music(self):
        files = filedialog.askopenfilenames(
            title="Select Music Files",
            filetypes=[
                ("Audio Files", "*.mp3 *.wav *.flac *.m4a *.ogg"),
                ("All Files", "*.*")
            ]
        )
        if files:
            # Process selected files
            messagebox.showinfo("Files Added", f"Added {len(files)} files to your library")

    def organize_music(self):
        """Organize music files based on user selections"""
        if self.is_processing:
            return

        # Ask for organization preferences
        import tkinter as tk
        dialog = ctk.CTkToplevel(self)
        dialog.title("Organize Music")
        dialog.geometry("500x400")
        dialog.transient(self)
        dialog.grab_set()

        # Organization options
        options_frame = ctk.CTkFrame(dialog)
        options_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        ctk.CTkLabel(
            options_frame,
            text="Music Organization Options",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(0, 20))

        # Organization pattern
        ctk.CTkLabel(
            options_frame,
            text="Organization Pattern:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(10, 5))

        pattern_var = tk.StringVar(value="artist/album")
        patterns = {
            "artist/album": "Artist/Album",
            "artist/year/album": "Artist/Year/Album",
            "genre/artist/album": "Genre/Artist/Album",
            "year/artist/album": "Year/Artist/Album",
            "year/genre/artist": "Year/Genre/Artist"
        }

        for value, text in patterns.items():
            ctk.CTkRadioButton(
                options_frame,
                text=text,
                value=value,
                variable=pattern_var,
                font=ctk.CTkFont(size=13)
            ).pack(anchor="w", pady=2)

        # Options
        options_var = {
            "copy_files": tk.BooleanVar(value=True),
            "rename_files": tk.BooleanVar(value=True),
            "normalize_tags": tk.BooleanVar(value=True),
            "create_playlists": tk.BooleanVar(value=False)
        }

        ctk.CTkLabel(
            options_frame,
            text="Options:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(20, 5))

        for option, var in options_var.items():
            option_text = {
                "copy_files": "Copy files (don't move original)",
                "rename_files": "Rename files based on tags",
                "normalize_tags": "Normalize ID3 tags",
                "create_playlists": "Create playlists for each category"
            }

            ctk.CTkCheckBox(
                options_frame,
                text=option_text[option],
                variable=var,
                font=ctk.CTkFont(size=13)
            ).pack(anchor="w", pady=2)

        # Destination
        ctk.CTkLabel(
            options_frame,
            text="Destination:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(20, 5))

        dest_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        dest_frame.pack(fill="x", pady=5)

        dest_var = tk.StringVar(value=os.path.expanduser("~/Music/Organized"))
        dest_entry = ctk.CTkEntry(dest_frame, textvariable=dest_var, width=350)
        dest_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        dest_btn = ctk.CTkButton(
            dest_frame,
            text="Browse",
            width=80,
            command=lambda: dest_var.set(filedialog.askdirectory() or dest_var.get())
        )
        dest_btn.pack(side="right")

        # Buttons
        btn_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)

        def start_organize():
            dialog.destroy()

            # Get selected options
            pattern = pattern_var.get()
            options = {k: v.get() for k, v in options_var.items()}
            destination = dest_var.get()

            # Start organization process
            messagebox.showinfo("Organizing", f"Organizing music files using pattern: {patterns[pattern]}")
            self.quick_organize()  # Use the quick_organize method to simulate progress

        ctk.CTkButton(
            btn_frame,
            text="Start Organization",
            command=start_organize,
            fg_color=self.accent_colors["dark"]["primary"],
            font=ctk.CTkFont(size=14)
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=dialog.destroy,
            fg_color=("gray80", "gray30"),
            font=ctk.CTkFont(size=14)
        ).pack(side="right", padx=5)

    def export_report(self):
        """Export library statistics and report"""
        if self.is_processing:
            return

        # Ask for report options
        report_dialog = ctk.CTkToplevel(self)
        report_dialog.title("Export Report")
        report_dialog.geometry("400x300")
        report_dialog.transient(self)
        report_dialog.grab_set()

        frame = ctk.CTkFrame(report_dialog)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            frame,
            text="Export Library Report",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(0, 20))

        # Report type
        import tkinter as tk
        report_type = tk.StringVar(value="summary")

        ctk.CTkLabel(
            frame,
            text="Report Type:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(10, 5))

        types = [
            ("Summary Report", "summary"),
            ("Detailed Analysis", "detailed"),
            ("File Listing", "files"),
            ("Genre Distribution", "genres"),
            ("Year Distribution", "years")
        ]

        for text, value in types:
            ctk.CTkRadioButton(
                frame,
                text=text,
                value=value,
                variable=report_type,
                font=ctk.CTkFont(size=13)
            ).pack(anchor="w", pady=2)

        # Format options
        format_var = tk.StringVar(value="pdf")

        ctk.CTkLabel(
            frame,
            text="Format:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(20, 5))

        formats = [("PDF", "pdf"), ("CSV", "csv"), ("HTML", "html")]
        format_frame = ctk.CTkFrame(frame, fg_color="transparent")
        format_frame.pack(fill="x")

        for text, value in formats:
            ctk.CTkRadioButton(
                format_frame,
                text=text,
                value=value,
                variable=format_var,
                font=ctk.CTkFont(size=13)
            ).pack(side="left", padx=15)

        # Buttons
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)

        def generate_report():
            report_dialog.destroy()

            # In a real app, we would generate the actual report
            # For demo purposes, we'll just show a success message
            messagebox.showinfo(
                "Report Generated",
                f"Generated {report_type.get()} report in {format_var.get().upper()} format."
            )

        ctk.CTkButton(
            btn_frame,
            text="Generate",
            command=generate_report,
            fg_color=self.accent_colors["dark"]["primary"],
            font=ctk.CTkFont(size=14)
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=report_dialog.destroy,
            fg_color=("gray80", "gray30"),
            font=ctk.CTkFont(size=14)
        ).pack(side="right", padx=5)

    def change_theme(self, theme):
        self.config["theme"] = theme
        ctk.set_appearance_mode(theme)
        self.save_config()

    def toggle_auto_organize(self):
        self.config["auto_organize"] = not self.config["auto_organize"]
        self.save_config()

    def show_player(self):
        """Show the advanced music player view"""
        self.clear_main_content()

        # Create the player view if it doesn't exist
        if not self.player_view:
            self.player_view = AdvancedMusicPlayer(self.main_content, fg_color="transparent")

        # Display the player
        self.player_view.pack(fill="both", expand=True)

    def show_search(self):
        """Show search interface with results"""
        self.clear_main_content()

        # Create search container
        search_container = ctk.CTkFrame(self.main_content, fg_color="transparent")
        search_container.pack(fill="both", expand=True)

        # Advanced search options
        options_frame = ctk.CTkFrame(search_container, fg_color=("gray90", "gray17"))
        options_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            options_frame,
            text="Advanced Search",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=20, pady=10)

        # Search fields in columns
        fields_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        fields_frame.pack(fill="x", padx=20, pady=10)
        fields_frame.columnconfigure((0, 1, 2), weight=1)

        # First column
        col1 = ctk.CTkFrame(fields_frame, fg_color="transparent")
        col1.grid(row=0, column=0, padx=10, sticky="nsew")

        ctk.CTkLabel(
            col1,
            text="Title",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(0, 5))

        ctk.CTkEntry(col1, placeholder_text="Song title...").pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            col1,
            text="Artist",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(0, 5))

        ctk.CTkEntry(col1, placeholder_text="Artist name...").pack(fill="x", pady=(0, 10))

        # Second column
        col2 = ctk.CTkFrame(fields_frame, fg_color="transparent")
        col2.grid(row=0, column=1, padx=10, sticky="nsew")

        ctk.CTkLabel(
            col2,
            text="Album",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(0, 5))

        ctk.CTkEntry(col2, placeholder_text="Album name...").pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            col2,
            text="Genre",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(0, 5))

        genres = ["Any", "Rock", "Pop", "Hip-Hop", "Jazz", "Electronic", "Classical"]
        ctk.CTkOptionMenu(col2, values=genres).pack(fill="x", pady=(0, 10))

        # Third column
        col3 = ctk.CTkFrame(fields_frame, fg_color="transparent")
        col3.grid(row=0, column=2, padx=10, sticky="nsew")

        ctk.CTkLabel(
            col3,
            text="Year",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(0, 5))

        year_frame = ctk.CTkFrame(col3, fg_color="transparent")
        year_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkEntry(
            year_frame,
            placeholder_text="From...",
            width=100
        ).pack(side="left", padx=(0, 5))

        ctk.CTkEntry(
            year_frame,
            placeholder_text="To...",
            width=100
        ).pack(side="left")

        ctk.CTkLabel(
            col3,
            text="BPM",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(0, 5))

        bpm_frame = ctk.CTkFrame(col3, fg_color="transparent")
        bpm_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkEntry(
            bpm_frame,
            placeholder_text="Min...",
            width=100
        ).pack(side="left", padx=(0, 5))

        ctk.CTkEntry(
            bpm_frame,
            placeholder_text="Max...",
            width=100
        ).pack(side="left")

        # Search button
        ctk.CTkButton(
            options_frame,
            text="Search",
            width=120,
            height=40,
            fg_color=self.accent_colors["dark"]["primary"]
        ).pack(pady=15)

        # Results section
        results_frame = ctk.CTkFrame(search_container, fg_color=("gray90", "gray17"))
        results_frame.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        # Results header
        results_header = ctk.CTkFrame(results_frame, fg_color="transparent")
        results_header.pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(
            results_header,
            text="Search Results",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(side="left")

        # Search results count
        ctk.CTkLabel(
            results_header,
            text="125 results found",
            font=ctk.CTkFont(size=14),
            text_color=("gray40", "gray60")
        ).pack(side="right")

        # Results list with detailed information
        results_scroll = ctk.CTkScrollableFrame(results_frame)
        results_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Header row
        header_frame = ctk.CTkFrame(results_scroll, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))

        headers = ["Title", "Artist", "Album", "Year", "Genre", "Duration", "BPM", "Format"]
        widths = [250, 180, 180, 60, 100, 80, 60, 60]

        for header, width in zip(headers, widths):
            ctk.CTkLabel(
                header_frame,
                text=header,
                font=ctk.CTkFont(size=12, weight="bold"),
                width=width
            ).pack(side="left", padx=5)

        # Sample results
        results = [
            {
                "title": "Track 1 - With a Longer Title That Needs Wrapping",
                "artist": "Artist Name",
                "album": "Album Title 1",
                "year": "2021",
                "genre": "Rock",
                "duration": "3:45",
                "bpm": "120",
                "format": "MP3"
            },
            {
                "title": "Track 2",
                "artist": "Another Artist",
                "album": "Album Title 2",
                "year": "2022",
                "genre": "Pop",
                "duration": "4:12",
                "bpm": "100",
                "format": "FLAC"
            },
            {
                "title": "Track 3",
                "artist": "Some Artist",
                "album": "Album Title 3",
                "year": "2019",
                "genre": "Jazz",
                "duration": "5:30",
                "bpm": "90",
                "format": "WAV"
            },
            {
                "title": "Track 4",
                "artist": "Artist Name",
                "album": "Album Title 1",
                "year": "2021",
                "genre": "Rock",
                "duration": "3:22",
                "bpm": "125",
                "format": "MP3"
            },
            {
                "title": "Track 5",
                "artist": "New Artist",
                "album": "Album Title 4",
                "year": "2020",
                "genre": "Electronic",
                "duration": "6:15",
                "bpm": "140",
                "format": "AIFF"
            }
        ]

        for i, result in enumerate(results):
            result_frame = ctk.CTkFrame(
                results_scroll,
                fg_color=("gray80", "gray25") if i % 2 == 0 else ("gray85", "gray22"),
                corner_radius=5,
                height=50
            )
            result_frame.pack(fill="x", pady=2)
            result_frame.pack_propagate(False)

            values = [
                result["title"],
                result["artist"],
                result["album"],
                result["year"],
                result["genre"],
                result["duration"],
                result["bpm"],
                result["format"]
            ]

            for value, width in zip(values, widths):
                ctk.CTkLabel(
                    result_frame,
                    text=value,
                    font=ctk.CTkFont(size=12),
                    width=width,
                    anchor="w",
                    wraplength=width-10
                ).pack(side="left", padx=5, pady=5)

            # Make row clickable to play the track
            result_frame.bind("<Button-1>", lambda e, r=result: self.play_search_result(r))

    def play_search_result(self, result):
        """Play the selected search result"""
        # Switch to player view
        self.show_player()

        # In a real app, you would pass the track to the player
        messagebox.showinfo("Play Track", f"Playing: {result['title']} by {result['artist']}")

    def show_mobile_sync(self):
        """Show the mobile sync interface"""
        self.clear_main_content()

        # Create mobile sync container
        sync_container = ctk.CTkFrame(self.main_content, fg_color="transparent")
        sync_container.pack(fill="both", expand=True)

        # Devices section
        devices_frame = ctk.CTkFrame(sync_container, fg_color=("gray90", "gray17"))
        devices_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            devices_frame,
            text="Connected Devices",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=20, pady=10)

        # Devices list
        devices_list = ctk.CTkFrame(devices_frame, fg_color="transparent")
        devices_list.pack(fill="x", padx=20, pady=(0, 20))

        # Sample devices
        devices = [
            {"name": "iPhone 13", "type": "iOS", "space": "58.2 GB free of 128 GB", "last_sync": "Today, 10:23 AM"},
            {"name": "Samsung Galaxy S21", "type": "Android", "space": "112.5 GB free of 256 GB", "last_sync": "Yesterday, 4:15 PM"}
        ]

        for device in devices:
            device_frame = ctk.CTkFrame(
                devices_list,
                fg_color=("gray85", "gray22"),
                corner_radius=10
            )
            device_frame.pack(fill="x", pady=5)

            # Device info
            info_frame = ctk.CTkFrame(device_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=15, pady=15)

            ctk.CTkLabel(
                info_frame,
                text=device["name"],
                font=ctk.CTkFont(size=16, weight="bold"),
                anchor="w"
            ).pack(fill="x")

            ctk.CTkLabel(
                info_frame,
                text=f"Device Type: {device['type']}",
                font=ctk.CTkFont(size=12),
                anchor="w"
            ).pack(fill="x")

            ctk.CTkLabel(
                info_frame,
                text=f"Storage: {device['space']}",
                font=ctk.CTkFont(size=12),
                anchor="w"
            ).pack(fill="x")

            ctk.CTkLabel(
                info_frame,
                text=f"Last Sync: {device['last_sync']}",
                font=ctk.CTkFont(size=12),
                text_color=("gray40", "gray60"),
                anchor="w"
            ).pack(fill="x")

            # Sync button
            button_frame = ctk.CTkFrame(device_frame, fg_color="transparent")
            button_frame.pack(side="right", padx=15, pady=15)

            ctk.CTkButton(
                button_frame,
                text="Sync Now",
                width=100,
                height=35,
                fg_color=self.accent_colors["dark"]["primary"]
            ).pack(pady=5)

            ctk.CTkButton(
                button_frame,
                text="Settings",
                width=100,
                height=35,
                fg_color=("gray75", "gray30")
            ).pack(pady=5)

        # Sync Options
        options_frame = ctk.CTkFrame(sync_container, fg_color=("gray90", "gray17"))
        options_frame.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        ctk.CTkLabel(
            options_frame,
            text="Sync Options",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=20, pady=10)

        # Options in columns
        options_grid = ctk.CTkFrame(options_frame, fg_color="transparent")
        options_grid.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        options_grid.columnconfigure((0, 1), weight=1)

        # Left column - What to sync
        left_col = ctk.CTkFrame(options_grid, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=10)

        ctk.CTkLabel(
            left_col,
            text="What to Sync",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))

        sync_options = ["All Music", "Selected Playlists", "Favorites Only", "Recent Additions"]
        for option in sync_options:
            ctk.CTkCheckBox(
                left_col,
                text=option,
                font=ctk.CTkFont(size=13)
            ).pack(anchor="w", pady=5)

        # Right column - How to sync
        right_col = ctk.CTkFrame(options_grid, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=10)

        ctk.CTkLabel(
            right_col,
            text="How to Sync",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))

        ctk.CTkRadioButton(
            right_col,
            text="Overwrite device music",
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", pady=5)

        ctk.CTkRadioButton(
            right_col,
            text="Merge with device music",
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", pady=5)

        ctk.CTkRadioButton(
            right_col,
            text="Only add new music",
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", pady=5)

        # Sync schedule
        schedule_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        schedule_frame.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkLabel(
            schedule_frame,
            text="Sync Schedule",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))

        schedule_options = ctk.CTkFrame(schedule_frame, fg_color="transparent")
        schedule_options.pack(fill="x")

        ctk.CTkRadioButton(
            schedule_options,
            text="Manual sync only",
            font=ctk.CTkFont(size=13)
        ).pack(side="left", padx=(0, 20))

        ctk.CTkRadioButton(
            schedule_options,
            text="Auto-sync when connected",
            font=ctk.CTkFont(size=13)
        ).pack(side="left", padx=(0, 20))

        ctk.CTkRadioButton(
            schedule_options,
            text="Scheduled sync",
            font=ctk.CTkFont(size=13)
        ).pack(side="left")

    def enable_drag_and_drop(self):
        """Enable drag and drop if TkinterDnD is available"""
        try:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self.handle_drop)
            self.dnd_enabled = True
        except Exception as e:
            print(f"TkinterDnD support not available - drag and drop disabled: {e}")
            self.dnd_enabled = False

    def handle_drop(self, event):
        """Handle files dropped onto the application"""
        if not self.dnd_enabled:
            return

        # Process dropped files (format differs by platform)
        files = event.data
        if files:
            print(f"Files dropped: {files}")
            # Process files - this would be expanded in a real application
            messagebox.showinfo("Files Received", f"Received {len(files.split())} files")

    def quick_organize(self):
        """Quickly organize music files using defaults"""
        if self.is_processing:
            return

        self.is_processing = True
        messagebox.showinfo("Organize Files", "Quick organize started. This may take a while.")

        # In a real app, we would do the actual organization here
        # For demonstration, we'll just simulate progress
        def simulate_progress():
            import time
            import random
            self.total_files = 100
            self.processed_files = 0

            for i in range(1, self.total_files + 1):
                self.processed_files = i
                # Update UI if needed
                time.sleep(0.05)  # Simulate work

            self.is_processing = False
            messagebox.showinfo("Organize Complete", f"Successfully organized {self.total_files} files")

        # Run in a separate thread to keep UI responsive
        import threading
        thread = threading.Thread(target=simulate_progress)
        thread.daemon = True
        thread.start()

def main():
    app = QApplication(sys.argv)
    window = ModernMusicOrganizerApp()
    window.apply_dark_theme()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
