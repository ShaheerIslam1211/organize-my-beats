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

AUDIO_EXTENSIONS = [".mp3", ".flac", ".m4a", ".ogg", ".wav", ".wma", ".aac"]


class MusicOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Music Organizer by Year - Enhanced Edition")
        self.root.geometry("1200x800")

        # Initialize theme colors
        self.colors = {
            "primary": "#2196F3",
            "secondary": "#4CAF50",
            "background": "#f5f5f5",
            "surface": "#ffffff",
            "error": "#f44336",
            "warning": "#ff9800",
            "success": "#4caf50",
            "text": "#212121",
            "text_secondary": "#757575"
        }

        # Setup theme and styles
        self.setup_theme()

        # Variables
        self.source_path = tk.StringVar()
        self.dest_path = tk.StringVar()
        self.processing = False
        self.current_file = tk.StringVar()
        self.progress_value = tk.DoubleVar()
        self.status_text = tk.StringVar(value="Ready to organize music files...")

        self.stats = {
            "total": 0,
            "copied": 0,
            "skipped": 0,
            "no_year": 0,
            "errors": 0,
            "years": {},
        }

        # Advanced options
        self.settings = {
            "overwrite_files": tk.BooleanVar(value=False),
            "create_unknown_year_folder": tk.BooleanVar(value=True),
            "preserve_folder_structure": tk.BooleanVar(value=False),
            "copy_album_artwork": tk.BooleanVar(value=True),
            "generate_playlist": tk.BooleanVar(value=True),
            "metadata_fields": tk.StringVar(value="date,year,originaldate,copyright"),
            "min_year": tk.StringVar(value="1900"),
            "max_year": tk.StringVar(value=str(datetime.now().year + 1))
        }

        self.worker_thread = None
        self.create_widgets()

        # Configure window minimum size
        self.root.minsize(900, 600)

        # Bind window resize event
        self.root.bind("<Configure>", self.on_window_configure)

        # Load saved settings if they exist
        self.load_settings()

    def setup_theme(self):
        """Setup modern theme and styles for the application"""
        try:
            self.style = Style()

            # Platform-specific theme setup
            self.is_macos = platform.system() == "Darwin"
            self.is_windows = platform.system() == "Windows"

            if self.is_macos:
                self.style.theme_use("aqua")
            elif "clam" in self.style.theme_names():
                self.style.theme_use("clam")

            # Configure fonts
            default_font_family = "Helvetica" if self.is_macos else "Segoe UI"
            self.fonts = {
                "default": tkFont.Font(family=default_font_family, size=10),
                "heading": tkFont.Font(family=default_font_family, size=12, weight="bold"),
                "large": tkFont.Font(family=default_font_family, size=14, weight="bold"),
                "small": tkFont.Font(family=default_font_family, size=9)
            }

            # Configure ttk styles
            self.style.configure("Main.TFrame", background=self.colors["background"])
            self.style.configure("Card.TFrame", background=self.colors["surface"])

            # Button styles
            button_config = {
                "font": self.fonts["default"],
                "padding": (10, 5),
                "relief": "flat",
                "borderwidth": 0
            }

            self.style.configure("Primary.TButton",
                background=self.colors["primary"],
                foreground="white",
                **button_config
            )

            self.style.configure("Secondary.TButton",
                background=self.colors["secondary"],
                foreground="white",
                **button_config
            )

            # Progress bar style
            self.style.configure("Horizontal.TProgressbar",
                background=self.colors["primary"],
                troughcolor=self.colors["background"],
                borderwidth=0,
                thickness=10
            )

            # Entry style
            self.style.configure("TEntry",
                padding=5,
                relief="flat",
                borderwidth=1
            )

            # Label style
            self.style.configure("TLabel",
                background=self.colors["background"],
                font=self.fonts["default"]
            )

            # Heading style
            self.style.configure("Heading.TLabel",
                background=self.colors["background"],
                font=self.fonts["heading"],
                foreground=self.colors["text"]
            )

            # Configure root window
            if not self.is_macos:
                self.root.configure(bg=self.colors["background"])

        except Exception as e:
            print(f"Error setting up theme: {str(e)}")
            # Fall back to system defaults if theme setup fails
            pass

    def create_widgets(self):
        """Create and setup all GUI widgets"""
        try:
            # Main container
            self.main_container = ttk.Frame(self.root, style="Main.TFrame")
            self.main_container.pack(fill="both", expand=True, padx=20, pady=20)

            # Create header
            self.create_header()

            # Create notebook for tabs
            self.notebook = ttk.Notebook(self.main_container)
            self.notebook.pack(fill="both", expand=True, pady=(20, 0))

            # Create all tabs
            self.main_tab = self.create_main_tab()
            self.stats_tab = self.create_stats_tab()
            self.metadata_tab = self.create_metadata_tab()
            self.settings_tab = self.create_settings_tab()
            self.batch_tab = self.create_batch_tab()

            # Add tabs to notebook
            self.notebook.add(self.main_tab, text="🎵 Organizer")
            self.notebook.add(self.stats_tab, text="📊 Statistics")
            self.notebook.add(self.metadata_tab, text="🏷 Metadata")
            self.notebook.add(self.settings_tab, text="⚙️ Settings")
            self.notebook.add(self.batch_tab, text="📦 Batch Process")

            # Create status bar
            self.create_status_bar()

        except Exception as e:
            print(f"Error creating widgets: {str(e)}")
            messagebox.showerror("Error", f"Failed to create application interface: {str(e)}")

    def create_header(self):
        """Create application header with title and description"""
        header_frame = ttk.Frame(self.main_container, style="Main.TFrame")
        header_frame.pack(fill="x", pady=(0, 20))

        title = ttk.Label(
            header_frame,
            text="Music Organizer by Year",
            font=self.fonts["large"],
            foreground=self.colors["primary"],
            style="Heading.TLabel"
        )
        title.pack(anchor="w")

        description = ttk.Label(
            header_frame,
            text="Organize your music collection by release year with advanced metadata handling",
            font=self.fonts["default"],
            foreground=self.colors["text_secondary"],
            wraplength=800
        )
        description.pack(anchor="w")

    def create_main_tab(self):
        """Create the main organizer tab"""
        tab = ttk.Frame(self.notebook, style="Main.TFrame")

        # Source selection card
        source_card = self.create_card(tab, "Source Location")
        source_frame = ttk.Frame(source_card, style="Card.TFrame")
        source_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(source_frame, text="Music Files Location:", style="TLabel").pack(side="left", padx=5)
        source_entry = ttk.Entry(source_frame, textvariable=self.source_path, width=50)
        source_entry.pack(side="left", padx=5, fill="x", expand=True)

        browse_btn = ttk.Button(
            source_frame,
            text="Browse",
            style="Primary.TButton",
            command=self.browse_source
        )
        browse_btn.pack(side="left", padx=5)

        # Destination selection card
        dest_card = self.create_card(tab, "Destination Location")
        dest_frame = ttk.Frame(dest_card, style="Card.TFrame")
        dest_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(dest_frame, text="Output Location:", style="TLabel").pack(side="left", padx=5)
        dest_entry = ttk.Entry(dest_frame, textvariable=self.dest_path, width=50)
        dest_entry.pack(side="left", padx=5, fill="x", expand=True)

        browse_dest_btn = ttk.Button(
            dest_frame,
            text="Browse",
            style="Primary.TButton",
            command=self.browse_dest
        )
        browse_dest_btn.pack(side="left", padx=5)

        # Options card
        options_card = self.create_card(tab, "Organization Options")
        options_frame = ttk.Frame(options_card, style="Card.TFrame")
        options_frame.pack(fill="x", padx=10, pady=5)

        # Create two columns for options
        left_options = ttk.Frame(options_frame)
        left_options.pack(side="left", fill="x", expand=True)

        right_options = ttk.Frame(options_frame)
        right_options.pack(side="left", fill="x", expand=True)

        # Left column options
        ttk.Checkbutton(
            left_options,
            text="Overwrite existing files",
            variable=self.settings["overwrite_files"]
        ).pack(anchor="w", padx=5, pady=2)

        ttk.Checkbutton(
            left_options,
            text="Create 'Unknown Year' folder",
            variable=self.settings["create_unknown_year_folder"]
        ).pack(anchor="w", padx=5, pady=2)

        ttk.Checkbutton(
            left_options,
            text="Preserve folder structure",
            variable=self.settings["preserve_folder_structure"]
        ).pack(anchor="w", padx=5, pady=2)

        # Right column options
        ttk.Checkbutton(
            right_options,
            text="Copy album artwork",
            variable=self.settings["copy_album_artwork"]
        ).pack(anchor="w", padx=5, pady=2)

        ttk.Checkbutton(
            right_options,
            text="Generate playlists",
            variable=self.settings["generate_playlist"]
        ).pack(anchor="w", padx=5, pady=2)

        # Progress card
        progress_card = self.create_card(tab, "Progress")
        progress_frame = ttk.Frame(progress_card, style="Card.TFrame")
        progress_frame.pack(fill="x", padx=10, pady=5)

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode="determinate",
            variable=self.progress_value,
            style="Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill="x", padx=5, pady=5)

        self.current_file_label = ttk.Label(
            progress_frame,
            textvariable=self.current_file,
            style="TLabel",
            wraplength=600
        )
        self.current_file_label.pack(fill="x", padx=5)

        # Buttons frame
        button_frame = ttk.Frame(tab, style="Main.TFrame")
        button_frame.pack(fill="x", pady=20)

        self.start_button = ttk.Button(
            button_frame,
            text="Start Organization",
            style="Primary.TButton",
            command=self.start_organization
        )
        self.start_button.pack(side="left", padx=5)

        self.stop_button = ttk.Button(
            button_frame,
            text="Stop",
            style="Secondary.TButton",
            command=self.stop_organization,
            state="disabled"
        )
        self.stop_button.pack(side="left", padx=5)

        # Log card
        log_card = self.create_card(tab, "Activity Log")

        self.log_output = scrolledtext.ScrolledText(
            log_card,
            height=8,
            font=self.fonts["small"]
        )
        self.log_output.pack(fill="both", expand=True, padx=10, pady=5)

        return tab

    def create_card(self, parent, title):
        """Create a card-style container"""
        card = ttk.LabelFrame(
            parent,
            text=title,
            style="Card.TFrame"
        )
        card.pack(fill="x", padx=10, pady=5)
        return card

    def create_status_bar(self):
        """Create status bar at the bottom of the window"""
        status_frame = ttk.Frame(self.root, style="Main.TFrame")
        status_frame.pack(fill="x", side="bottom", padx=10, pady=5)

        status_label = ttk.Label(
            status_frame,
            textvariable=self.status_text,
            font=self.fonts["small"],
            foreground=self.colors["text_secondary"]
        )
        status_label.pack(side="left")

    def create_stats_tab(self, parent):
        # Stats header
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill="x", padx=10, pady=10)

        header_label = ttk.Label(
            header_frame,
            text="Organization Statistics",
            font=self.fonts["heading"],
        )
        header_label.pack()

        # Summary stats frame
        summary_frame = ttk.LabelFrame(parent, text="Summary")
        summary_frame.pack(fill="x", padx=10, pady=5)

        # Create summary labels
        stats_grid = ttk.Frame(summary_frame)
        stats_grid.pack(fill="x", padx=5, pady=5)

        # Row 1
        ttk.Label(stats_grid, text="Total Files:").grid(
            row=0, column=0, sticky="w", padx=5, pady=2
        )
        self.total_files_label = ttk.Label(stats_grid, text="0")
        self.total_files_label.grid(row=0, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(stats_grid, text="Files Copied:").grid(
            row=0, column=2, sticky="w", padx=5, pady=2
        )
        self.copied_files_label = ttk.Label(stats_grid, text="0")
        self.copied_files_label.grid(row=0, column=3, sticky="w", padx=5, pady=2)

        # Row 2
        ttk.Label(stats_grid, text="Files Skipped:").grid(
            row=1, column=0, sticky="w", padx=5, pady=2
        )
        self.skipped_files_label = ttk.Label(stats_grid, text="0")
        self.skipped_files_label.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(stats_grid, text="No Year Found:").grid(
            row=1, column=2, sticky="w", padx=5, pady=2
        )
        self.no_year_files_label = ttk.Label(stats_grid, text="0")
        self.no_year_files_label.grid(row=1, column=3, sticky="w", padx=5, pady=2)

        # Row 3
        ttk.Label(stats_grid, text="Errors:").grid(
            row=2, column=0, sticky="w", padx=5, pady=2
        )
        self.error_files_label = ttk.Label(stats_grid, text="0")
        self.error_files_label.grid(row=2, column=1, sticky="w", padx=5, pady=2)

        # Year distribution frame
        year_frame = ttk.LabelFrame(parent, text="Year Distribution")
        year_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Create treeview for year stats
        columns = ("year", "count")
        self.year_tree = ttk.Treeview(year_frame, columns=columns, show="headings")
        self.year_tree.heading("year", text="Year")
        self.year_tree.heading("count", text="Number of Songs")
        self.year_tree.column("year", width=100, anchor="center")
        self.year_tree.column("count", width=150, anchor="center")

        # Add scrollbar to treeview
        year_scroll = ttk.Scrollbar(
            year_frame, orient="vertical", command=self.year_tree.yview
        )
        self.year_tree.configure(yscrollcommand=year_scroll.set)

        # Pack treeview and scrollbar
        self.year_tree.pack(side="left", fill="both", expand=True)
        year_scroll.pack(side="right", fill="y")

    def create_metadata_tab(self):
        """Create the metadata viewer tab"""
        tab = ttk.Frame(self.notebook, style="Main.TFrame")

        # File selection card
        file_card = self.create_card(tab, "Audio File Selection")
        file_frame = ttk.Frame(file_card, style="Card.TFrame")
        file_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(file_frame, text="Select Audio File:", style="TLabel").pack(side="left", padx=5)
        self.metadata_file_path = tk.StringVar()
        file_entry = ttk.Entry(file_frame, textvariable=self.metadata_file_path, width=50)
        file_entry.pack(side="left", padx=5, fill="x", expand=True)

        browse_btn = ttk.Button(
            file_frame,
            text="Browse",
            style="Primary.TButton",
            command=self.browse_metadata_file
        )
        browse_btn.pack(side="left", padx=5)

        # Metadata display card
        metadata_card = self.create_card(tab, "File Metadata")
        metadata_frame = ttk.Frame(metadata_card, style="Card.TFrame")
        metadata_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Create two columns
        left_frame = ttk.Frame(metadata_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=5)

        right_frame = ttk.Frame(metadata_frame)
        right_frame.pack(side="left", fill="both", expand=True, padx=5)

        # Metadata tree view
        self.metadata_tree = ttk.Treeview(
            left_frame,
            columns=("Tag", "Value"),
            show="headings",
            height=15
        )
        self.metadata_tree.heading("Tag", text="Tag")
        self.metadata_tree.heading("Value", text="Value")
        self.metadata_tree.column("Tag", width=150)
        self.metadata_tree.column("Value", width=300)
        self.metadata_tree.pack(side="left", fill="both", expand=True)

        # Scrollbar for tree
        tree_scroll = ttk.Scrollbar(left_frame, orient="vertical", command=self.metadata_tree.yview)
        tree_scroll.pack(side="right", fill="y")
        self.metadata_tree.configure(yscrollcommand=tree_scroll.set)

        # Metadata editor
        editor_frame = ttk.LabelFrame(right_frame, text="Edit Metadata")
        editor_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Selected tag
        tag_frame = ttk.Frame(editor_frame)
        tag_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(tag_frame, text="Selected Tag:", style="TLabel").pack(side="left", padx=5)
        self.selected_tag = tk.StringVar()
        self.tag_label = ttk.Label(tag_frame, textvariable=self.selected_tag, style="TLabel")
        self.tag_label.pack(side="left", padx=5)

        # Value editor
        value_frame = ttk.Frame(editor_frame)
        value_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(value_frame, text="Value:", style="TLabel").pack(side="left", padx=5)
        self.tag_value = tk.StringVar()
        value_entry = ttk.Entry(value_frame, textvariable=self.tag_value, width=40)
        value_entry.pack(side="left", padx=5, fill="x", expand=True)

        # Update button
        update_btn = ttk.Button(
            editor_frame,
            text="Update Tag",
            style="Primary.TButton",
            command=self.update_metadata_tag
        )
        update_btn.pack(pady=10)

        # File info card
        info_card = self.create_card(tab, "File Information")
        info_frame = ttk.Frame(info_card, style="Card.TFrame")
        info_frame.pack(fill="x", padx=10, pady=5)

        # Create info labels with a grid layout
        self.file_info = {
            "Format": tk.StringVar(),
            "Bitrate": tk.StringVar(),
            "Sample Rate": tk.StringVar(),
            "Channels": tk.StringVar(),
            "Duration": tk.StringVar(),
            "File Size": tk.StringVar()
        }

        row = 0
        for label, var in self.file_info.items():
            ttk.Label(info_frame, text=f"{label}:", style="TLabel").grid(row=row, column=0, sticky="w", padx=5, pady=2)
            ttk.Label(info_frame, textvariable=var, style="TLabel").grid(row=row, column=1, sticky="w", padx=5, pady=2)
            row += 1

        # Bind tree selection event
        self.metadata_tree.bind("<<TreeviewSelect>>", self.on_metadata_select)

        return tab

    def browse_metadata_file(self):
        """Browse for an audio file to view metadata"""
        filetypes = [("Audio Files", " ".join(f"*{ext}" for ext in AUDIO_EXTENSIONS))]
        filename = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=filetypes
        )
        if filename:
            self.metadata_file_path.set(filename)
            self.load_metadata()

    def load_metadata(self):
        """Load and display metadata for the selected file"""
        try:
            filepath = self.metadata_file_path.get()
            if not filepath:
                return

            # Clear existing metadata
            for item in self.metadata_tree.get_children():
                self.metadata_tree.delete(item)

            # Load audio file
            audio = MutagenFile(filepath, easy=True)
            if not audio:
                messagebox.showerror("Error", "Could not read audio file metadata")
                return

            # Insert metadata into tree
            for tag in sorted(audio.tags.keys()):
                values = audio.tags[tag]
                if isinstance(values, list):
                    value = ", ".join(str(v) for v in values)
                else:
                    value = str(values)
                self.metadata_tree.insert("", "end", values=(tag, value))

            # Update file information
            file_path = Path(filepath)
            file_size = file_path.stat().st_size
            file_size_str = f"{file_size / 1024 / 1024:.2f} MB"

            self.file_info["Format"].set(file_path.suffix[1:].upper())
            self.file_info["File Size"].set(file_size_str)

            # Try to get audio-specific information
            try:
                if hasattr(audio.info, "bitrate"):
                    self.file_info["Bitrate"].set(f"{audio.info.bitrate // 1000} kbps")
                if hasattr(audio.info, "sample_rate"):
                    self.file_info["Sample Rate"].set(f"{audio.info.sample_rate} Hz")
                if hasattr(audio.info, "channels"):
                    self.file_info["Channels"].set(str(audio.info.channels))
                if hasattr(audio.info, "length"):
                    minutes = int(audio.info.length // 60)
                    seconds = int(audio.info.length % 60)
                    self.file_info["Duration"].set(f"{minutes}:{seconds:02d}")
            except Exception as e:
                print(f"Error getting audio info: {e}")

            self.log(f"✅ Loaded metadata for: {file_path.name}")

        except Exception as e:
            self.log(f"❌ Error loading metadata: {str(e)}")
            messagebox.showerror("Error", f"Failed to load metadata: {str(e)}")

    def on_metadata_select(self, event):
        """Handle metadata tree item selection"""
        selection = self.metadata_tree.selection()
        if selection:
            item = selection[0]
            tag, value = self.metadata_tree.item(item)["values"]
            self.selected_tag.set(tag)
            self.tag_value.set(value)

    def update_metadata_tag(self):
        """Update the selected metadata tag"""
        try:
            filepath = self.metadata_file_path.get()
            if not filepath:
                return

            tag = self.selected_tag.get()
            if not tag:
                messagebox.showwarning("Warning", "Please select a tag to update")
                return

            new_value = self.tag_value.get()
            audio = MutagenFile(filepath, easy=True)
            if not audio:
                messagebox.showerror("Error", "Could not read audio file")
                return

            # Update the tag
            audio[tag] = new_value
            audio.save()

            # Reload metadata to show changes
            self.load_metadata()
            self.log(f"✅ Updated tag '{tag}' to: {new_value}")

        except Exception as e:
            self.log(f"❌ Error updating metadata: {str(e)}")
            messagebox.showerror("Error", f"Failed to update metadata: {str(e)}")

    def create_batch_tab(self):
        """Create the batch processing tab"""
        tab = ttk.Frame(self.notebook, style="Main.TFrame")

        # Source folders card
        sources_card = self.create_card(tab, "Source Folders")
        sources_frame = ttk.Frame(sources_card, style="Card.TFrame")
        sources_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Source list with scrollbar
        list_frame = ttk.Frame(sources_frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.sources_list = tk.Listbox(
            list_frame,
            selectmode="extended",
            height=6,
            font=self.fonts["default"]
        )
        self.sources_list.pack(side="left", fill="both", expand=True)

        sources_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.sources_list.yview)
        sources_scroll.pack(side="right", fill="y")
        self.sources_list.configure(yscrollcommand=sources_scroll.set)

        # Buttons for source management
        button_frame = ttk.Frame(sources_frame)
        button_frame.pack(fill="x", padx=5, pady=5)

        ttk.Button(
            button_frame,
            text="Add Folder",
            style="Primary.TButton",
            command=self.add_batch_source
        ).pack(side="left", padx=2)

        ttk.Button(
            button_frame,
            text="Remove Selected",
            style="Secondary.TButton",
            command=self.remove_batch_source
        ).pack(side="left", padx=2)

        ttk.Button(
            button_frame,
            text="Clear All",
            style="Secondary.TButton",
            command=self.clear_batch_sources
        ).pack(side="left", padx=2)

        # Destination folder card
        dest_card = self.create_card(tab, "Destination Folder")
        dest_frame = ttk.Frame(dest_card, style="Card.TFrame")
        dest_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(dest_frame, text="Output Location:", style="TLabel").pack(side="left", padx=5)
        self.batch_dest_path = tk.StringVar()
        dest_entry = ttk.Entry(dest_frame, textvariable=self.batch_dest_path, width=50)
        dest_entry.pack(side="left", padx=5, fill="x", expand=True)

        browse_btn = ttk.Button(
            dest_frame,
            text="Browse",
            style="Primary.TButton",
            command=self.browse_batch_dest
        )
        browse_btn.pack(side="left", padx=5)

        # Batch options card
        options_card = self.create_card(tab, "Batch Processing Options")
        options_frame = ttk.Frame(options_card, style="Card.TFrame")
        options_frame.pack(fill="x", padx=10, pady=5)

        # Create two columns for options
        left_options = ttk.Frame(options_frame)
        left_options.pack(side="left", fill="x", expand=True)

        right_options = ttk.Frame(options_frame)
        right_options.pack(side="left", fill="x", expand=True)

        # Left column options
        ttk.Checkbutton(
            left_options,
            text="Process subfolders",
            variable=self.settings.get("process_subfolders", tk.BooleanVar(value=True)),
            style="TCheckbutton"
        ).pack(anchor="w", padx=5, pady=2)

        ttk.Checkbutton(
            left_options,
            text="Skip existing files",
            variable=self.settings.get("skip_existing", tk.BooleanVar(value=True)),
            style="TCheckbutton"
        ).pack(anchor="w", padx=5, pady=2)

        # Right column options
        ttk.Checkbutton(
            right_options,
            text="Generate report",
            variable=self.settings.get("generate_report", tk.BooleanVar(value=True)),
            style="TCheckbutton"
        ).pack(anchor="w", padx=5, pady=2)

        ttk.Checkbutton(
            right_options,
            text="Create log file",
            variable=self.settings.get("create_log", tk.BooleanVar(value=True)),
            style="TCheckbutton"
        ).pack(anchor="w", padx=5, pady=2)

        # Progress card
        progress_card = self.create_card(tab, "Batch Progress")
        progress_frame = ttk.Frame(progress_card, style="Card.TFrame")
        progress_frame.pack(fill="x", padx=10, pady=5)

        # Overall progress
        overall_frame = ttk.Frame(progress_frame)
        overall_frame.pack(fill="x", padx=5, pady=2)

        ttk.Label(overall_frame, text="Overall Progress:", style="TLabel").pack(side="left", padx=5)
        self.batch_progress = ttk.Progressbar(
            overall_frame,
            mode="determinate",
            style="Horizontal.TProgressbar"
        )
        self.batch_progress.pack(fill="x", padx=5, expand=True)

        # Current folder progress
        folder_frame = ttk.Frame(progress_frame)
        folder_frame.pack(fill="x", padx=5, pady=2)

        ttk.Label(folder_frame, text="Current Folder:", style="TLabel").pack(side="left", padx=5)
        self.folder_progress = ttk.Progressbar(
            folder_frame,
            mode="determinate",
            style="Horizontal.TProgressbar"
        )
        self.folder_progress.pack(fill="x", padx=5, expand=True)

        # Status labels
        status_frame = ttk.Frame(progress_frame)
        status_frame.pack(fill="x", padx=5, pady=2)

        self.batch_status = tk.StringVar(value="Ready to start batch processing")
        status_label = ttk.Label(
            status_frame,
            textvariable=self.batch_status,
            style="TLabel"
        )
        status_label.pack(fill="x", padx=5)

        # Control buttons
        control_frame = ttk.Frame(tab, style="Main.TFrame")
        control_frame.pack(fill="x", pady=20)

        self.batch_start_button = ttk.Button(
            control_frame,
            text="Start Batch Processing",
            style="Primary.TButton",
            command=self.start_batch_processing
        )
        self.batch_start_button.pack(side="left", padx=5)

        self.batch_stop_button = ttk.Button(
            control_frame,
            text="Stop",
            style="Secondary.TButton",
            command=self.stop_batch_processing,
            state="disabled"
        )
        self.batch_stop_button.pack(side="left", padx=5)

        return tab

    def add_batch_source(self):
        """Add a source folder to the batch processing list"""
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            self.sources_list.insert(tk.END, folder)
            self.log(f"Added source folder: {folder}")

    def remove_batch_source(self):
        """Remove selected source folders from the list"""
        selection = self.sources_list.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select folders to remove")
            return

        # Remove selected items in reverse order to maintain correct indices
        for index in sorted(selection, reverse=True):
            folder = self.sources_list.get(index)
            self.sources_list.delete(index)
            self.log(f"Removed source folder: {folder}")

    def clear_batch_sources(self):
        """Clear all source folders from the list"""
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear all source folders?"):
            self.sources_list.delete(0, tk.END)
            self.log("Cleared all source folders")

    def browse_batch_dest(self):
        """Browse for batch processing destination folder"""
        folder = filedialog.askdirectory(title="Select Destination Folder")
        if folder:
            self.batch_dest_path.set(folder)

    def start_batch_processing(self):
        """Start batch processing of multiple folders"""
        # Get source folders
        sources = list(self.sources_list.get(0, tk.END))
        if not sources:
            messagebox.showerror("Error", "Please add at least one source folder")
            return

        # Get destination folder
        dest = self.batch_dest_path.get()
        if not dest:
            messagebox.showerror("Error", "Please select a destination folder")
            return

        # Create destination if it doesn't exist
        dest_path = Path(dest)
        if not dest_path.exists():
            if messagebox.askyesno("Create Destination", f"Create destination folder '{dest}'?"):
                try:
                    dest_path.mkdir(parents=True)
                except Exception as e:
                    messagebox.showerror("Error", f"Could not create destination folder: {e}")
                    return
            else:
                return

        # Update UI state
        self.batch_start_button.config(state="disabled")
        self.batch_stop_button.config(state="normal")
        self.batch_status.set("Starting batch processing...")
        self.batch_progress["value"] = 0
        self.folder_progress["value"] = 0

        # Start processing in a separate thread
        self.processing = True
        self.worker_thread = threading.Thread(
            target=self.process_batch,
            args=(sources, dest)
        )
        self.worker_thread.daemon = True
        self.worker_thread.start()

    def process_batch(self, sources, dest):
        """Process multiple source folders"""
        try:
            total_folders = len(sources)
            processed_folders = 0

            for source in sources:
                if not self.processing:
                    break

                self.batch_status.set(f"Processing folder: {source}")
                source_path = Path(source)

                # Process the current folder
                try:
                    self.process_folder(source_path, Path(dest))
                except Exception as e:
                    self.log(f"Error processing folder {source}: {e}")

                processed_folders += 1
                self.batch_progress["value"] = (processed_folders / total_folders) * 100
                self.root.update_idletasks()

            if self.processing:
                self.batch_processing_complete()
            else:
                self.log("Batch processing stopped by user")
                self.batch_status.set("Processing stopped")

        except Exception as e:
            self.log(f"Error during batch processing: {e}")
            self.batch_processing_complete()

    def stop_batch_processing(self):
        """Stop batch processing"""
        if messagebox.askyesno("Confirm Stop", "Stop batch processing?"):
            self.processing = False
            self.batch_status.set("Stopping...")
            self.log("Stopping batch processing...")

    def batch_processing_complete(self):
        """Update UI when batch processing is complete"""
        self.processing = False
        self.batch_start_button.config(state="normal")
        self.batch_stop_button.config(state="disabled")
        self.batch_status.set("Batch processing complete")

        # Generate report if enabled
        if self.settings.get("generate_report").get():
            self.generate_batch_report()

    def change_theme(self, event=None):
        """Handle theme selection change"""
        # This just updates the variable, apply_theme does the actual work
        pass

    def apply_theme(self):
        """Apply the selected theme"""
        theme_name = self.theme_var.get()

        # Define theme colors
        themes = {
            "Default": {
                "bg": "#f5f5f5",
                "accent": "#4CAF50",
                "secondary": "#2196F3",
                "warning": "#FFC107",
                "error": "#F44336",
            },
            "Dark": {
                "bg": "#333333",
                "accent": "#66BB6A",
                "secondary": "#42A5F5",
                "warning": "#FFCA28",
                "error": "#EF5350",
            },
            "Light": {
                "bg": "#FFFFFF",
                "accent": "#43A047",
                "secondary": "#1E88E5",
                "warning": "#FFB300",
                "error": "#E53935",
            },
            "Blue": {
                "bg": "#E3F2FD",
                "accent": "#1976D2",
                "secondary": "#0097A7",
                "warning": "#FFA000",
                "error": "#D32F2F",
            },
            "Elegant": {
                "bg": "#ECEFF1",
                "accent": "#546E7A",
                "secondary": "#78909C",
                "warning": "#F57F17",
                "error": "#BF360C",
            },
        }

        # Apply the selected theme
        if theme_name in themes:
            colors = themes[theme_name]

            # Update theme colors
            self.colors = colors

            # Update ttk styles
            self.style.configure("TButton", background=colors["accent"])
            self.style.map(
                "TButton",
                background=[("active", self.adjust_color(colors["accent"], -20))],
            )

            self.style.configure("Secondary.TButton", background=colors["secondary"])
            self.style.map(
                "Secondary.TButton",
                background=[("active", self.adjust_color(colors["secondary"], -20))],
            )

            self.style.configure("Danger.TButton", background=colors["error"])
            self.style.map(
                "Danger.TButton",
                background=[("active", self.adjust_color(colors["error"], -20))],
            )

            self.style.configure("Horizontal.TProgressbar", background=colors["accent"])

            # Update root window
            self.root.configure(bg=colors["bg"])

            # Show confirmation
            self.log(f"Applied {theme_name} theme")

    def adjust_color(self, hex_color, amount):
        """Adjust a hex color by the given amount (positive=lighter, negative=darker)"""
        # Convert hex to RGB
        hex_color = hex_color.lstrip("#")
        r, g, b = (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )

        # Adjust color
        r = max(0, min(255, r + amount))
        g = max(0, min(255, g + amount))
        b = max(0, min(255, b + amount))

        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"

    def on_window_configure(self, event):
        """Handle window resize event"""
        # Implement any necessary resizing logic here
        pass

    def load_settings(self):
        """Load saved settings from file"""
        # Implement loading settings from a file
        pass

    def create_settings_tab(self):
        """Create the settings tab with advanced configuration options"""
        tab = ttk.Frame(self.notebook, style="Main.TFrame")

        # Appearance settings card
        appearance_card = self.create_card(tab, "Appearance Settings")
        appearance_frame = ttk.Frame(appearance_card, style="Card.TFrame")
        appearance_frame.pack(fill="x", padx=10, pady=5)

        # Theme selector
        theme_frame = ttk.Frame(appearance_frame)
        theme_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(theme_frame, text="Color Theme:", style="TLabel").pack(side="left", padx=5)
        self.theme_var = tk.StringVar(value="Default")
        theme_combo = ttk.Combobox(
            theme_frame,
            textvariable=self.theme_var,
            values=["Default", "Dark", "Light", "Blue", "Green", "Purple"],
            width=20
        )
        theme_combo.pack(side="left", padx=5)
        theme_combo.bind("<<ComboboxSelected>>", self.change_theme)

        # Font settings
        font_frame = ttk.Frame(appearance_frame)
        font_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(font_frame, text="UI Font Size:", style="TLabel").pack(side="left", padx=5)
        self.font_size_var = tk.StringVar(value="Default")
        font_combo = ttk.Combobox(
            font_frame,
            textvariable=self.font_size_var,
            values=["Small", "Default", "Large"],
            width=20
        )
        font_combo.pack(side="left", padx=5)

        # Organization settings card
        org_card = self.create_card(tab, "Organization Settings")
        org_frame = ttk.Frame(org_card, style="Card.TFrame")
        org_frame.pack(fill="x", padx=10, pady=5)

        # Year range settings
        year_frame = ttk.Frame(org_frame)
        year_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(year_frame, text="Valid Year Range:", style="TLabel").pack(side="left", padx=5)
        ttk.Entry(
            year_frame,
            textvariable=self.settings["min_year"],
            width=6
        ).pack(side="left", padx=2)
        ttk.Label(year_frame, text="to", style="TLabel").pack(side="left", padx=2)
        ttk.Entry(
            year_frame,
            textvariable=self.settings["max_year"],
            width=6
        ).pack(side="left", padx=2)

        # Metadata settings card
        metadata_card = self.create_card(tab, "Metadata Settings")
        metadata_frame = ttk.Frame(metadata_card, style="Card.TFrame")
        metadata_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(
            metadata_frame,
            text="Metadata fields to check for year (comma-separated):",
            style="TLabel"
        ).pack(anchor="w", padx=5, pady=2)

        metadata_entry = ttk.Entry(
            metadata_frame,
            textvariable=self.settings["metadata_fields"],
            width=50
        )
        metadata_entry.pack(fill="x", padx=5, pady=2)

        # File types card
        filetypes_card = self.create_card(tab, "Supported File Types")
        filetypes_frame = ttk.Frame(filetypes_card, style="Card.TFrame")
        filetypes_frame.pack(fill="x", padx=10, pady=5)

        # Create checkboxes for file extensions in a grid layout
        self.extension_vars = {}
        for i, ext in enumerate(AUDIO_EXTENSIONS):
            var = tk.BooleanVar(value=True)
            self.extension_vars[ext] = var
            ttk.Checkbutton(
                filetypes_frame,
                text=ext,
                variable=var,
                style="TCheckbutton"
            ).grid(row=i//3, column=i%3, sticky="w", padx=10, pady=2)

        # Advanced settings card
        advanced_card = self.create_card(tab, "Advanced Settings")
        advanced_frame = ttk.Frame(advanced_card, style="Card.TFrame")
        advanced_frame.pack(fill="x", padx=10, pady=5)

        # Organization structure options
        ttk.Checkbutton(
            advanced_frame,
            text="Create decade folders (e.g., '1990s/1995')",
            variable=self.settings.get("create_decade_folders", tk.BooleanVar(value=False)),
            style="TCheckbutton"
        ).pack(anchor="w", padx=5, pady=2)

        ttk.Checkbutton(
            advanced_frame,
            text="Organize by artist within year folders",
            variable=self.settings.get("organize_by_artist", tk.BooleanVar(value=False)),
            style="TCheckbutton"
        ).pack(anchor="w", padx=5, pady=2)

        # Performance settings
        perf_frame = ttk.Frame(advanced_frame)
        perf_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(perf_frame, text="Processing Batch Size:", style="TLabel").pack(side="left", padx=5)
        self.batch_size_var = tk.StringVar(value="100")
        ttk.Spinbox(
            perf_frame,
            from_=10,
            to=1000,
            increment=10,
            textvariable=self.batch_size_var,
            width=6
        ).pack(side="left", padx=5)

        # Save settings button
        button_frame = ttk.Frame(tab, style="Main.TFrame")
        button_frame.pack(fill="x", pady=20)

        ttk.Button(
            button_frame,
            text="Save Settings",
            style="Primary.TButton",
            command=self.save_settings
        ).pack(side="left", padx=5)

        ttk.Button(
            button_frame,
            text="Reset to Defaults",
            style="Secondary.TButton",
            command=self.reset_settings
        ).pack(side="left", padx=5)

        return tab

    def save_settings(self):
        """Save current settings to a configuration file"""
        try:
            settings = {
                "theme": self.theme_var.get(),
                "font_size": self.font_size_var.get(),
                "min_year": self.settings["min_year"].get(),
                "max_year": self.settings["max_year"].get(),
                "metadata_fields": self.settings["metadata_fields"].get(),
                "batch_size": self.batch_size_var.get(),
                "extensions": {ext: var.get() for ext, var in self.extension_vars.items()},
                "create_decade_folders": self.settings.get("create_decade_folders").get(),
                "organize_by_artist": self.settings.get("organize_by_artist").get()
            }

            config_path = Path.home() / ".music_organizer_config.json"
            with open(config_path, "w") as f:
                json.dump(settings, f, indent=4)

            self.log("✅ Settings saved successfully")
            messagebox.showinfo("Success", "Settings have been saved")

        except Exception as e:
            self.log(f"❌ Error saving settings: {str(e)}")
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

    def reset_settings(self):
        """Reset all settings to their default values"""
        if messagebox.askyesno("Confirm Reset", "Are you sure you want to reset all settings to their defaults?"):
            try:
                # Reset theme
                self.theme_var.set("Default")
                self.change_theme()

                # Reset font size
                self.font_size_var.set("Default")

                # Reset year range
                self.settings["min_year"].set("1900")
                self.settings["max_year"].set(str(datetime.now().year + 1))

                # Reset metadata fields
                self.settings["metadata_fields"].set("date,year,originaldate,copyright")

                # Reset file extensions
                for var in self.extension_vars.values():
                    var.set(True)

                # Reset advanced settings
                self.settings.get("create_decade_folders").set(False)
                self.settings.get("organize_by_artist").set(False)
                self.batch_size_var.set("100")

                self.log("✅ Settings reset to defaults")
                messagebox.showinfo("Success", "Settings have been reset to defaults")

            except Exception as e:
                self.log(f"❌ Error resetting settings: {str(e)}")
                messagebox.showerror("Error", f"Failed to reset settings: {str(e)}")

    def start_organization(self):
        """Start the organization process"""
        if not self.source_path.get() or not self.dest_path.get():
            messagebox.showerror("Error", "Please select both source and destination folders")
            return

        if self.processing:
            messagebox.showwarning("Warning", "Organization is already in progress")
            return

        self.processing = True
        self.stats = {
            "total": 0,
            "copied": 0,
            "skipped": 0,
            "no_year": 0,
            "errors": 0,
            "years": {}
        }
        self.update_stats_display()

        # Disable controls during processing
        self.toggle_controls(False)

        # Start organization in a separate thread
        self.worker_thread = threading.Thread(target=self.process_files)
        self.worker_thread.start()

    def process_files(self):
        """Process files in a separate thread"""
        try:
            from .organize_my_beats import MusicOrganizer

            def progress_callback(processed, total, stats):
                self.progress_value.set((processed / total) * 100 if total > 0 else 0)
                self.current_file.set(f"Processing: {processed}/{total} files")
                self.stats = stats
                self.update_stats_display()
                self.root.update_idletasks()

            organizer = MusicOrganizer(
                Path(self.source_path.get()),
                Path(self.dest_path.get()),
                progress_callback
            )

            # Start the organization process
            stats = organizer.organize()

            self.processing = False
            self.toggle_controls(True)
            self.status_text.set("Organization complete!")
            self.update_stats_display()

            # Show completion message
            messagebox.showinfo(
                "Complete",
                f"Organization complete!\n\n"
                f"Total files: {stats['total']}\n"
                f"Copied: {stats['copied']}\n"
                f"Skipped: {stats['skipped']}\n"
                f"No year found: {stats['no_year']}\n"
                f"Errors: {stats['errors']}"
            )

        except Exception as e:
            self.processing = False
            self.toggle_controls(True)
            self.status_text.set("Error during organization")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def stop_organization(self):
        """Stop the organization process"""
        if not self.processing:
            return

        if messagebox.askyesno("Confirm", "Are you sure you want to stop the organization process?"):
            self.processing = False
            self.status_text.set("Organization stopped")
            self.toggle_controls(True)

    def toggle_controls(self, enabled):
        """Enable or disable all controls"""
        self.start_button.config(state=enabled)
        self.stop_button.config(state=enabled)
        self.sources_list.config(state=enabled)
        self.batch_start_button.config(state=enabled)
        self.batch_stop_button.config(state=enabled)

    def update_stats_display(self):
        """Update the statistics display in the GUI"""
        self.total_files_label.config(text=str(self.stats["total"]))
        self.copied_files_label.config(text=str(self.stats["copied"]))
        self.skipped_files_label.config(text=str(self.stats["skipped"]))
        self.no_year_files_label.config(text=str(self.stats["no_year"]))
        self.error_files_label.config(text=str(self.stats["errors"]))

        # Update year distribution tree
        self.year_tree.delete(*self.year_tree.get_children())
        for year, count in self.stats["years"].items():
            self.year_tree.insert("", "end", values=(year, count))


if __name__ == "__main__":
    try:
        # Try to initialize TkinterDnD for drag and drop support
        try:
            import TkinterDnD2

            root = TkinterDnD2.TkinterDnD.Tk()
        except ImportError:
            root = tk.Tk()

        # Set DPI awareness on Windows to improve rendering
        try:
            from ctypes import windll

            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass  # Not on Windows or other issue

        # Configure root window before creating app
        root.title("Music Organizer by Year - Enhanced Edition")
        root.geometry("900x700")

        # Create and run the application
        app = MusicOrganizerApp(root)
        root.mainloop()

    except Exception as e:
        # If there's a critical error, show it in a messagebox if possible
        import traceback

        error_msg = f"Critical error: {str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)  # Print to console

        try:
            # Try to show error in messagebox
            import tkinter.messagebox as msgbox

            msgbox.showerror(
                "Critical Error",
                f"The application encountered a critical error:\n\n{str(e)}",
            )
        except:
            # If messagebox fails, at least we printed to console
            pass
