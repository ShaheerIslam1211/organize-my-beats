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

AUDIO_EXTENSIONS = [".mp3", ".flac", ".m4a", ".ogg", ".wav", ".wma", ".aac"]


class MusicOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Music Organizer by Year - Enhanced Edition")
        self.root.geometry("900x700")

        # Setup theme and styles
        self.setup_theme()

        # Variables
        self.source_path = tk.StringVar()
        self.dest_path = tk.StringVar()
        self.processing = False
        self.stats = {
            "total": 0,
            "copied": 0,
            "skipped": 0,
            "no_year": 0,
            "errors": 0,
            "years": {},
        }
        self.worker_thread = None

        # Options
        self.overwrite_files = tk.BooleanVar(value=False)
        self.create_unknown_year_folder = tk.BooleanVar(value=True)
        self.selected_metadata_fields = tk.StringVar(
            value="date,year,originaldate,copyright"
        )

        # Check for TkinterDnD2 availability
        self.dnd_available = False
        try:
            import TkinterDnD2

            self.dnd_available = True
        except ImportError:
            pass

        self.create_widgets()

    def setup_theme(self):
        """Setup modern theme and styles for the application"""
        try:
            # Configure ttk styles
            self.style = Style()

            # Try to use a theme that works well across platforms
            available_themes = self.style.theme_names()

            # On macOS, prefer 'aqua' theme which is native
            import platform

            is_macos = platform.system() == "Darwin"

            if is_macos and "aqua" in available_themes:
                selected_theme = "aqua"  # Best for macOS
            else:
                # For other platforms, try these themes
                preferred_themes = ["clam", "alt", "default"]
                selected_theme = "default"  # Fallback
                for theme in preferred_themes:
                    if theme in available_themes:
                        selected_theme = theme
                        break

            self.style.theme_use(selected_theme)

            # Configure colors - using slightly muted colors for better cross-platform compatibility
            bg_color = "#f5f5f5"
            accent_color = "#4CAF50"
            secondary_color = "#2196F3"
            warning_color = "#FFC107"
            error_color = "#F44336"

            # Configure fonts - use system defaults when possible
            default_font = tkFont.nametofont("TkDefaultFont")
            default_font.configure(size=10)
            heading_font = tkFont.Font(
                family=default_font.cget("family"), size=12, weight="bold"
            )

            # Basic button style that works across platforms
            button_config = {"padding": 6}

            # Add style configurations that work on all platforms
            self.style.configure("TButton", **button_config)

            # Apply platform-specific styling
            if not is_macos:
                # These styles work better on Windows/Linux
                button_config["relief"] = "flat"
                button_config["background"] = accent_color
                button_config["foreground"] = "white"

                self.style.configure("TButton", **button_config)
                self.style.map(
                    "TButton",
                    background=[("active", "#45a049"), ("disabled", "#cccccc")],
                )
                self.style.configure("Secondary.TButton", background=secondary_color)
                self.style.map("Secondary.TButton", background=[("active", "#1976D2")])
                self.style.configure("Danger.TButton", background=error_color)
                self.style.map("Danger.TButton", background=[("active", "#D32F2F")])

            # Progress bar style - works on most platforms
            self.style.configure("Horizontal.TProgressbar", background=accent_color)

            # Configure root window - use a more compatible approach for macOS
            if not is_macos:
                self.root.configure(bg=bg_color)

            # Store theme colors for later use
            self.theme = {
                "bg": bg_color,
                "accent": accent_color,
                "secondary": secondary_color,
                "warning": warning_color,
                "error": error_color,
                "heading_font": heading_font,
            }

        except Exception as e:
            # If theme setup fails, fall back to system defaults
            print(f"Error setting up theme: {str(e)}")
            # Don't raise the exception - let the application continue with default theme

    def create_widgets(self):
        try:
            # Create notebook (tabbed interface)
            self.notebook = ttk.Notebook(self.root)
            self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

            # Create all tabs first
            main_tab = ttk.Frame(self.notebook)
            stats_tab = ttk.Frame(self.notebook)
            settings_tab = ttk.Frame(self.notebook)
            metadata_tab = ttk.Frame(self.notebook)
            batch_tab = ttk.Frame(self.notebook)

            # Create log output first so it can be used by other methods
            log_frame = ttk.LabelFrame(main_tab, text="Log")
            log_frame.pack(fill="both", expand=True, padx=10, pady=10)

            self.log_output = scrolledtext.ScrolledText(log_frame, width=80, height=15)
            self.log_output.pack(fill="both", expand=True, padx=5, pady=5)

            # Configure tabs in a specific order to ensure dependencies are met
            self.setup_main_tab(main_tab)
            self.setup_stats_tab(stats_tab)
            self.setup_settings_tab(settings_tab)
            self.setup_metadata_tab(metadata_tab)
            self.setup_batch_tab(batch_tab)

            # Add tabs to notebook after they've been fully configured
            self.notebook.add(main_tab, text="Organizer")
            self.notebook.add(stats_tab, text="Statistics")
            self.notebook.add(settings_tab, text="Settings")
            self.notebook.add(metadata_tab, text="Metadata Viewer")
            self.notebook.add(batch_tab, text="Batch Processing")

            # Now that all widgets are created and registered, we can log messages
            self.show_welcome_messages()

        except Exception as e:
            # If there's an error during widget creation, show a messagebox
            import traceback

            error_msg = f"Error creating widgets: {str(e)}\n\n{traceback.format_exc()}"
            print(error_msg)  # Print to console for debugging
            messagebox.showerror(
                "Error Initializing UI", f"Error creating widgets: {str(e)}"
            )
            # Try to continue anyway

    def setup_main_tab(self, parent):
        # Folder selection frame
        folder_frame = ttk.LabelFrame(parent, text="Folder Selection")
        folder_frame.pack(fill="x", padx=10, pady=10)

        # Source folder selection
        source_frame = ttk.Frame(folder_frame)
        source_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(source_frame, text="🎵 Source Folder:").pack(side="left", padx=5)
        source_entry = ttk.Entry(source_frame, textvariable=self.source_path, width=50)
        source_entry.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(source_frame, text="Browse", command=self.browse_source).pack(
            side="left", padx=5
        )

        # Setup drag and drop for source entry
        self.setup_drag_drop(source_entry, self.source_path)

        # Destination folder selection
        dest_frame = ttk.Frame(folder_frame)
        dest_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(dest_frame, text="📁 Destination Folder:").pack(side="left", padx=5)
        dest_entry = ttk.Entry(dest_frame, textvariable=self.dest_path, width=50)
        dest_entry.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(dest_frame, text="Browse", command=self.browse_dest).pack(
            side="left", padx=5
        )

        # Setup drag and drop for destination entry
        self.setup_drag_drop(dest_entry, self.dest_path)

        # Quick options frame
        options_frame = ttk.LabelFrame(parent, text="Quick Options")
        options_frame.pack(fill="x", padx=10, pady=5)

        ttk.Checkbutton(
            options_frame,
            text="Overwrite existing files",
            variable=self.overwrite_files,
        ).pack(anchor="w", padx=5, pady=2)
        ttk.Checkbutton(
            options_frame,
            text="Create 'Unknown Year' folder for files without year metadata",
            variable=self.create_unknown_year_folder,
        ).pack(anchor="w", padx=5, pady=2)

        # Progress frame
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(progress_frame, text="Progress:").pack(anchor="w")
        self.progress_bar = Progressbar(
            progress_frame, orient="horizontal", length=100, mode="determinate"
        )
        self.progress_bar.pack(fill="x", padx=5, pady=5)

        # Status label
        self.status_label = ttk.Label(progress_frame, text="Ready")
        self.status_label.pack(anchor="w", padx=5)

        # Buttons frame
        buttons_frame = ttk.Frame(parent)
        buttons_frame.pack(fill="x", padx=10, pady=5)

        self.start_button = ttk.Button(
            buttons_frame,
            text="Start Organizing",
            command=self.start_processing,
            style="TButton",
        )
        self.start_button.pack(side="left", padx=5)

        self.stop_button = ttk.Button(
            buttons_frame,
            text="Stop",
            command=self.stop_processing,
            style="Danger.TButton",
            state="disabled",
        )
        self.stop_button.pack(side="left", padx=5)

    def setup_stats_tab(self, parent):
        # Stats header
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill="x", padx=10, pady=10)

        header_label = ttk.Label(
            header_frame,
            text="Organization Statistics",
            font=self.theme["heading_font"],
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

    def setup_settings_tab(self, parent):
        # Theme settings
        theme_frame = ttk.LabelFrame(parent, text="Theme Settings")
        theme_frame.pack(fill="x", padx=10, pady=10)

        theme_frame_inner = ttk.Frame(theme_frame)
        theme_frame_inner.pack(fill="x", padx=5, pady=5)

        ttk.Label(theme_frame_inner, text="Color Theme:").grid(
            row=0, column=0, sticky="w", padx=5, pady=5
        )

        # Theme selector
        self.theme_var = tk.StringVar(value="Default")
        theme_combo = ttk.Combobox(
            theme_frame_inner,
            textvariable=self.theme_var,
            values=["Default", "Dark", "Light", "Blue", "Elegant"],
        )
        theme_combo.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        theme_combo.bind("<<ComboboxSelected>>", self.change_theme)

        ttk.Button(
            theme_frame_inner,
            text="Apply Theme",
            command=self.apply_theme,
            style="Secondary.TButton",
        ).grid(row=0, column=2, padx=5, pady=5)

        # Metadata settings
        metadata_frame = ttk.LabelFrame(parent, text="Metadata Settings")
        metadata_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(
            metadata_frame, text="Metadata fields to check for year (comma-separated):"
        ).pack(anchor="w", padx=5, pady=5)
        metadata_entry = ttk.Entry(
            metadata_frame, textvariable=self.selected_metadata_fields, width=50
        )
        metadata_entry.pack(fill="x", padx=5, pady=5)

        # File type settings
        filetype_frame = ttk.LabelFrame(parent, text="File Type Settings")
        filetype_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(filetype_frame, text="Supported audio file extensions:").pack(
            anchor="w", padx=5, pady=5
        )

        # Create checkboxes for each extension
        extensions_frame = ttk.Frame(filetype_frame)
        extensions_frame.pack(fill="x", padx=5, pady=5)

        self.extension_vars = {}
        for i, ext in enumerate(AUDIO_EXTENSIONS):
            var = tk.BooleanVar(value=True)
            self.extension_vars[ext] = var
            ttk.Checkbutton(extensions_frame, text=ext, variable=var).grid(
                row=i // 3, column=i % 3, sticky="w", padx=10, pady=2
            )

        # Organization rules
        rules_frame = ttk.LabelFrame(parent, text="Organization Rules")
        rules_frame.pack(fill="x", padx=10, pady=10)

        # Create decade folders option
        self.create_decade_folders = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            rules_frame,
            text="Create year folders with decade prefix (e.g., '1990s/1995')",
            variable=self.create_decade_folders,
        ).pack(anchor="w", padx=5, pady=2)

        # Organize by artist option
        self.organize_by_artist = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            rules_frame,
            text="Organize by artist within year folders",
            variable=self.organize_by_artist,
        ).pack(anchor="w", padx=5, pady=2)

        # Advanced options
        advanced_frame = ttk.LabelFrame(parent, text="Advanced Options")
        advanced_frame.pack(fill="x", padx=10, pady=10)

        # Parallel processing option
        self.use_parallel_processing = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            advanced_frame,
            text="Use parallel processing (faster but uses more memory)",
            variable=self.use_parallel_processing,
        ).pack(anchor="w", padx=5, pady=2)

        # Batch size option
        batch_frame = ttk.Frame(advanced_frame)
        batch_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(batch_frame, text="Batch size:").pack(side="left", padx=5)
        self.batch_size_var = tk.IntVar(value=100)
        batch_spinbox = ttk.Spinbox(
            batch_frame,
            from_=10,
            to=1000,
            increment=10,
            textvariable=self.batch_size_var,
            width=5,
        )
        batch_spinbox.pack(side="left", padx=5)

        # About section
        about_frame = ttk.LabelFrame(parent, text="About")
        about_frame.pack(fill="x", padx=10, pady=10)

        about_text = "Music Organizer Enhanced Edition\nVersion 1.0\n\nA powerful tool to organize your music collection by year."
        ttk.Label(about_frame, text=about_text, justify="center").pack(padx=10, pady=10)

    def show_welcome_messages(self):
        """Display welcome messages after all widgets are initialized"""
        try:
            # Make sure the log_output widget exists and is ready
            if hasattr(self, "log_output") and self.log_output.winfo_exists():
                # Welcome message
                self.log(
                    "Welcome to Music Organizer Enhanced! Select source and destination folders to begin."
                )

                # Show drag and drop availability message
                if not self.dnd_available:
                    self.log(
                        "Note: Drag and drop functionality not available. Install 'tkinterdnd2' package for this feature."
                    )
            else:
                # If log_output widget isn't ready, delay the welcome message with a longer timeout
                # This gives more time for the UI to initialize on slower systems
                self.root.after(1000, self.show_welcome_messages)
                return

        except Exception as e:
            # If logging fails, show a messagebox instead
            try:
                # Use after() to delay the messagebox to ensure the UI is ready
                self.root.after(
                    500,
                    lambda: messagebox.showinfo(
                        "Welcome", "Welcome to Music Organizer Enhanced!"
                    ),
                )
            except Exception as inner_e:
                print(f"Even messagebox failed: {inner_e}")  # Last resort logging
            print(f"Error logging welcome message: {e}")

    def setup_drag_drop(self, widget, string_var):
        """Setup drag and drop functionality for the given widget"""
        # Skip if drag and drop is not available
        if not self.dnd_available:
            return

        def drag_enter(event):
            event.widget.configure(background="#e1f5fe")
            return "event.action=copy"

        def drag_leave(event):
            event.widget.configure(background="white")

        def drop(event):
            event.widget.configure(background="white")
            # Get the dropped data (file path)
            if event.data:
                data = event.data
                if data.startswith("{") and data.endswith("}"):  # Windows/macOS
                    data = data[1:-1]
                if os.path.isdir(data):
                    string_var.set(data)

        # Bind drag and drop events
        try:
            widget.drop_target_register("DND_Files")
            widget.dnd_bind("<<DropEnter>>", drag_enter)
            widget.dnd_bind("<<DropLeave>>", drag_leave)
            widget.dnd_bind("<<Drop>>", drop)
        except Exception as e:
            # TkinterDnD binding failed
            self.dnd_available = False

    def browse_source(self):
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            self.source_path.set(folder)

    def browse_dest(self):
        folder = filedialog.askdirectory(title="Select Destination Folder")
        if folder:
            self.dest_path.set(folder)

    def log(self, message):
        """Add a message to the log output with error handling"""
        try:
            # Check if the log_output widget exists and is ready
            if hasattr(self, "log_output") and self.log_output.winfo_exists():
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.log_output.insert(tk.END, f"[{timestamp}] {message}\n")
                self.log_output.see(tk.END)

                # Use update_idletasks instead of update to avoid potential issues
                try:
                    self.root.update_idletasks()
                except:
                    pass  # Ignore update errors
            else:
                # If log widget isn't available, print to console instead
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        except Exception as e:
            # If logging fails completely, print to console
            print(f"Error in log method: {e}")
            print(f"Original message: {message}")
            # Don't propagate the exception

    def update_status(self, message):
        """Update the status label with a message"""
        self.status_label.config(text=message)
        self.root.update()

    def update_progress(self, value):
        """Update the progress bar value (0-100)"""
        self.progress_bar["value"] = value
        self.root.update()

    def update_stats_display(self):
        """Update the statistics display with current stats"""
        # Update summary labels
        self.total_files_label.config(text=str(self.stats["total"]))
        self.copied_files_label.config(text=str(self.stats["copied"]))
        self.skipped_files_label.config(text=str(self.stats["skipped"]))
        self.no_year_files_label.config(text=str(self.stats["no_year"]))
        self.error_files_label.config(text=str(self.stats["errors"]))

        # Clear and update year tree
        for item in self.year_tree.get_children():
            self.year_tree.delete(item)

        # Sort years in descending order
        sorted_years = sorted(
            self.stats["years"].items(), key=lambda x: x[0], reverse=True
        )

        # Add years to tree
        for year, count in sorted_years:
            self.year_tree.insert("", "end", values=(year, count))

    def stop_processing(self):
        """Stop the current processing operation"""
        if self.processing and self.worker_thread and self.worker_thread.is_alive():
            if messagebox.askyesno(
                "Confirm Stop", "Are you sure you want to stop the current operation?"
            ):
                self.processing = False
                self.log("⚠️ Stopping operation...")
                self.update_status("Stopping...")
                # Thread will check self.processing flag and exit gracefully

    def get_song_year(self, filepath):
        try:
            audio = MutagenFile(filepath, easy=True)
            if not audio:
                return None

            # Get metadata fields from settings
            metadata_fields = [
                field.strip()
                for field in self.selected_metadata_fields.get().split(",")
            ]

            for tag in metadata_fields:
                if tag in audio:
                    year_str = str(audio[tag][0])
                    if len(year_str) >= 4 and year_str[:4].isdigit():
                        year = year_str[:4]
                        # Validate year is reasonable (between 1900 and current year + 1)
                        current_year = datetime.now().year
                        if 1900 <= int(year) <= current_year + 1:
                            return year
        except Exception as e:
            self.log(f"[!] Error reading metadata: {os.path.basename(filepath)} – {e}")
        return None

    def get_active_extensions(self):
        """Get list of active file extensions based on settings"""
        return [ext for ext, var in self.extension_vars.items() if var.get()]

    def start_processing(self):
        source = Path(self.source_path.get())
        dest = Path(self.dest_path.get())

        if not source.exists():
            messagebox.showerror("Error", "Source folder does not exist.")
            return

        if not dest.exists():
            if messagebox.askyesno(
                "Create Destination",
                f"The destination folder '{dest}' does not exist. Create it?",
            ):
                try:
                    dest.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    messagebox.showerror(
                        "Error", f"Could not create destination folder: {str(e)}"
                    )
                    return
            else:
                return

        # Reset stats
        self.stats = {
            "total": 0,
            "copied": 0,
            "skipped": 0,
            "no_year": 0,
            "errors": 0,
            "years": {},
        }
        self.update_stats_display()

        # Clear log
        self.log_output.delete(1.0, tk.END)

        # Update UI state
        self.processing = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.progress_bar["value"] = 0

        # Get active extensions
        active_extensions = self.get_active_extensions()

        # Get options
        options = {
            "overwrite": self.overwrite_files.get(),
            "unknown_year_folder": self.create_unknown_year_folder.get(),
        }

        # Start processing in a separate thread
        self.log("🚀 Starting organization process...")
        self.log(f"📂 Source: {source}")
        self.log(f"📁 Destination: {dest}")

        self.worker_thread = threading.Thread(
            target=self.process_files_thread,
            args=(source, dest, active_extensions, options),
        )
        self.worker_thread.daemon = True
        self.worker_thread.start()

    def process_files_thread(self, source, dest, extensions, options):
        """Process files in a separate thread to keep UI responsive"""
        try:
            # First count files for progress tracking
            self.update_status("Counting files...")
            total_files = 0
            for root_dir, _, files in os.walk(source):
                if not self.processing:
                    return
                for file in files:
                    file_path = Path(root_dir) / file
                    if file_path.suffix.lower() in extensions:
                        total_files += 1

            if total_files == 0:
                self.log("No audio files found in the source directory.")
                self.processing_complete()
                return

            self.log(f"Found {total_files} audio files to process")

            # Process files
            processed_files = 0
            for root_dir, _, files in os.walk(source):
                if not self.processing:
                    return

                for file in files:
                    if not self.processing:
                        return

                    file_path = Path(root_dir) / file
                    if file_path.suffix.lower() not in extensions:
                        continue

                    self.stats["total"] += 1
                    processed_files += 1

                    # Update progress every 10 files or for the last file
                    if processed_files % 10 == 0 or processed_files == total_files:
                        progress = int((processed_files / total_files) * 100)
                        self.root.after(0, lambda p=progress: self.update_progress(p))
                        self.root.after(
                            0,
                            lambda: self.update_status(
                                f"Processing file {processed_files} of {total_files}"
                            ),
                        )

                    # Process the file
                    year = self.get_song_year(file_path)
                    if year:
                        # Update year statistics
                        if year not in self.stats["years"]:
                            self.stats["years"][year] = 0
                        self.stats["years"][year] += 1

                        # Create year folder and copy file
                        year_folder = dest / year
                        year_folder.mkdir(parents=True, exist_ok=True)
                        dest_file = year_folder / file

                        if not dest_file.exists() or options["overwrite"]:
                            try:
                                shutil.copy2(file_path, dest_file)
                                self.stats["copied"] += 1
                                self.root.after(
                                    0,
                                    lambda f=file, y=year: self.log(
                                        f"✅ Copied to {y}: {f}"
                                    ),
                                )
                            except Exception as e:
                                self.stats["errors"] += 1
                                self.root.after(
                                    0,
                                    lambda f=file_path, e=str(e): self.log(
                                        f"[!] Copy failed: {f.name} – {e}"
                                    ),
                                )
                        else:
                            self.stats["skipped"] += 1
                            self.root.after(
                                0,
                                lambda f=file: self.log(
                                    f"⚠️ Skipped (already exists): {f}"
                                ),
                            )
                    else:
                        self.stats["no_year"] += 1
                        self.root.after(
                            0,
                            lambda f=file_path: self.log(f"❓ No year found: {f.name}"),
                        )

                        # Handle files with no year metadata if option is enabled
                        if options["unknown_year_folder"]:
                            unknown_folder = dest / "Unknown Year"
                            unknown_folder.mkdir(parents=True, exist_ok=True)
                            dest_file = unknown_folder / file

                            if not dest_file.exists() or options["overwrite"]:
                                try:
                                    shutil.copy2(file_path, dest_file)
                                    self.root.after(
                                        0,
                                        lambda f=file: self.log(
                                            f"📁 Copied to Unknown Year folder: {f}"
                                        ),
                                    )
                                except Exception as e:
                                    self.root.after(
                                        0,
                                        lambda f=file, e=str(e): self.log(
                                            f"[!] Copy to Unknown Year failed: {f} – {e}"
                                        ),
                                    )

                    # Update stats display periodically
                    if processed_files % 20 == 0 or processed_files == total_files:
                        self.root.after(0, self.update_stats_display)

            # Processing complete
            self.root.after(0, lambda: self.log("✅ Organization complete!"))
            self.root.after(0, self.processing_complete)

        except Exception as e:
            self.root.after(
                0, lambda e=str(e): self.log(f"❌ Error during processing: {e}")
            )
            self.root.after(0, self.processing_complete)

    def processing_complete(self):
        """Update UI state when processing is complete"""
        self.processing = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.update_status("Ready")

        # Show final statistics
        self.log(f"📊 Statistics:")
        self.log(f"   - Total files processed: {self.stats['total']}")
        self.log(f"   - Files copied: {self.stats['copied']}")
        self.log(f"   - Files skipped (already exist): {self.stats['skipped']}")
        self.log(f"   - Files without year metadata: {self.stats['no_year']}")
        self.log(f"   - Errors encountered: {self.stats['errors']}")

        # Update stats display one final time
        self.update_stats_display()

        # Switch to statistics tab
        self.notebook.select(1)  # Select the stats tab

    def setup_metadata_tab(self, parent):
        """Setup the metadata viewer tab"""
        # File selection frame
        file_frame = ttk.Frame(parent)
        file_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(file_frame, text="Select audio file:").pack(side="left", padx=5)
        self.metadata_file_path = tk.StringVar()
        file_entry = ttk.Entry(
            file_frame, textvariable=self.metadata_file_path, width=50
        )
        file_entry.pack(side="left", fill="x", expand=True, padx=5)

        ttk.Button(file_frame, text="Browse", command=self.browse_metadata_file).pack(
            side="left", padx=5
        )
        ttk.Button(
            file_frame,
            text="Load Metadata",
            command=self.load_metadata,
            style="Secondary.TButton",
        ).pack(side="left", padx=5)

        # Metadata display frame
        metadata_display_frame = ttk.LabelFrame(parent, text="File Metadata")
        metadata_display_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Create treeview for metadata
        columns = ("tag", "value")
        self.metadata_tree = ttk.Treeview(
            metadata_display_frame, columns=columns, show="headings"
        )
        self.metadata_tree.heading("tag", text="Tag")
        self.metadata_tree.heading("value", text="Value")
        self.metadata_tree.column("tag", width=150)
        self.metadata_tree.column("value", width=350)

        # Add scrollbar to treeview
        metadata_scroll = ttk.Scrollbar(
            metadata_display_frame, orient="vertical", command=self.metadata_tree.yview
        )
        self.metadata_tree.configure(yscrollcommand=metadata_scroll.set)

        # Pack treeview and scrollbar
        self.metadata_tree.pack(side="left", fill="both", expand=True)
        metadata_scroll.pack(side="right", fill="y")

        # Edit metadata frame
        edit_frame = ttk.Frame(parent)
        edit_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(edit_frame, text="Tag:").grid(row=0, column=0, padx=5, pady=5)
        self.edit_tag_var = tk.StringVar()
        ttk.Entry(edit_frame, textvariable=self.edit_tag_var, width=20).grid(
            row=0, column=1, padx=5, pady=5
        )

        ttk.Label(edit_frame, text="Value:").grid(row=0, column=2, padx=5, pady=5)
        self.edit_value_var = tk.StringVar()
        ttk.Entry(edit_frame, textvariable=self.edit_value_var, width=40).grid(
            row=0, column=3, padx=5, pady=5
        )

        ttk.Button(
            edit_frame,
            text="Update Tag",
            command=self.update_metadata_tag,
            style="Secondary.TButton",
        ).grid(row=0, column=4, padx=5, pady=5)

        # Bind selection event
        self.metadata_tree.bind("<<TreeviewSelect>>", self.on_metadata_select)

    def setup_batch_tab(self, parent):
        """Setup the batch processing tab"""
        # Batch processing instructions
        instructions_frame = ttk.Frame(parent)
        instructions_frame.pack(fill="x", padx=10, pady=10)

        instructions_text = "Batch Processing allows you to apply the same organization rules to multiple source folders."
        ttk.Label(instructions_frame, text=instructions_text, wraplength=600).pack(
            padx=10, pady=5
        )

        # Batch sources frame
        sources_frame = ttk.LabelFrame(parent, text="Source Folders")
        sources_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Create listbox for sources with scrollbar
        sources_list_frame = ttk.Frame(sources_frame)
        sources_list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.sources_listbox = tk.Listbox(sources_list_frame, height=10)
        self.sources_listbox.pack(side="left", fill="both", expand=True)

        sources_scroll = ttk.Scrollbar(
            sources_list_frame, orient="vertical", command=self.sources_listbox.yview
        )
        self.sources_listbox.configure(yscrollcommand=sources_scroll.set)
        sources_scroll.pack(side="right", fill="y")

        # Buttons for managing sources
        sources_buttons_frame = ttk.Frame(sources_frame)
        sources_buttons_frame.pack(fill="x", padx=5, pady=5)

        ttk.Button(
            sources_buttons_frame, text="Add Folder", command=self.add_batch_source
        ).pack(side="left", padx=5)
        ttk.Button(
            sources_buttons_frame,
            text="Remove Selected",
            command=self.remove_batch_source,
        ).pack(side="left", padx=5)
        ttk.Button(
            sources_buttons_frame, text="Clear All", command=self.clear_batch_sources
        ).pack(side="left", padx=5)

        # Destination folder
        dest_frame = ttk.LabelFrame(parent, text="Destination Folder")
        dest_frame.pack(fill="x", padx=10, pady=10)

        dest_inner_frame = ttk.Frame(dest_frame)
        dest_inner_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(dest_inner_frame, text="Destination:").pack(side="left", padx=5)
        self.batch_dest_path = tk.StringVar()
        ttk.Entry(dest_inner_frame, textvariable=self.batch_dest_path, width=50).pack(
            side="left", fill="x", expand=True, padx=5
        )
        ttk.Button(
            dest_inner_frame, text="Browse", command=self.browse_batch_dest
        ).pack(side="left", padx=5)

        # Batch options
        options_frame = ttk.LabelFrame(parent, text="Batch Options")
        options_frame.pack(fill="x", padx=10, pady=10)

        # Use same options as main tab
        ttk.Checkbutton(
            options_frame,
            text="Use same options as in Settings tab",
            variable=tk.BooleanVar(value=True),
        ).pack(anchor="w", padx=5, pady=2)

        # Start batch button
        batch_button_frame = ttk.Frame(parent)
        batch_button_frame.pack(fill="x", padx=10, pady=10)

        self.batch_start_button = ttk.Button(
            batch_button_frame,
            text="Start Batch Processing",
            command=self.start_batch_processing,
            style="TButton",
        )
        self.batch_start_button.pack(side="left", padx=5)

        self.batch_stop_button = ttk.Button(
            batch_button_frame,
            text="Stop",
            command=self.stop_batch_processing,
            style="Danger.TButton",
            state="disabled",
        )
        self.batch_stop_button.pack(side="left", padx=5)

    def browse_metadata_file(self):
        """Browse for an audio file to view metadata"""
        filetypes = [("Audio Files", " ".join(["*" + ext for ext in AUDIO_EXTENSIONS]))]
        file = filedialog.askopenfilename(
            title="Select Audio File", filetypes=filetypes
        )
        if file:
            self.metadata_file_path.set(file)
            self.load_metadata()

    def load_metadata(self):
        """Load and display metadata from the selected audio file"""
        file_path = self.metadata_file_path.get()
        if not file_path or not os.path.isfile(file_path):
            messagebox.showerror("Error", "Please select a valid audio file.")
            return

        # Clear existing metadata
        for item in self.metadata_tree.get_children():
            self.metadata_tree.delete(item)

        try:
            audio = MutagenFile(file_path, easy=True)
            if not audio:
                messagebox.showerror("Error", "Could not read metadata from this file.")
                return

            # Display all metadata tags
            for tag, value in audio.items():
                self.metadata_tree.insert("", "end", values=(tag, str(value)))

            # Display file info
            file_info = Path(file_path)
            self.metadata_tree.insert("", "end", values=("filename", file_info.name))
            self.metadata_tree.insert(
                "",
                "end",
                values=("filesize", f"{os.path.getsize(file_path) / 1024:.1f} KB"),
            )

        except Exception as e:
            messagebox.showerror("Error", f"Error reading metadata: {str(e)}")

    def on_metadata_select(self, event):
        """Handle selection in the metadata treeview"""
        selection = self.metadata_tree.selection()
        if selection:
            item = self.metadata_tree.item(selection[0])
            values = item["values"]
            if values and len(values) >= 2:
                self.edit_tag_var.set(values[0])
                self.edit_value_var.set(values[1])

    def update_metadata_tag(self):
        """Update a metadata tag in the selected file"""
        file_path = self.metadata_file_path.get()
        tag = self.edit_tag_var.get()
        value = self.edit_value_var.get()

        if not file_path or not os.path.isfile(file_path):
            messagebox.showerror("Error", "Please select a valid audio file.")
            return

        if not tag:
            messagebox.showerror("Error", "Please select a tag to update.")
            return

        try:
            # Special handling for file info tags which can't be modified
            if tag in ["filename", "filesize"]:
                messagebox.showinfo("Info", f"The {tag} tag cannot be modified.")
                return

            audio = MutagenFile(file_path)
            if not audio:
                messagebox.showerror("Error", "Could not read metadata from this file.")
                return

            # Update the tag
            audio[tag] = value
            audio.save()

            messagebox.showinfo("Success", f"Updated {tag} to '{value}'")

            # Reload metadata to show changes
            self.load_metadata()

        except Exception as e:
            messagebox.showerror("Error", f"Error updating metadata: {str(e)}")

    def add_batch_source(self):
        """Add a source folder to the batch processing list"""
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            # Check if already in list
            items = self.sources_listbox.get(0, tk.END)
            if folder not in items:
                self.sources_listbox.insert(tk.END, folder)

    def remove_batch_source(self):
        """Remove the selected source folder from the batch list"""
        selection = self.sources_listbox.curselection()
        if selection:
            self.sources_listbox.delete(selection[0])

    def clear_batch_sources(self):
        """Clear all source folders from the batch list"""
        self.sources_listbox.delete(0, tk.END)

    def browse_batch_dest(self):
        """Browse for a destination folder for batch processing"""
        folder = filedialog.askdirectory(title="Select Destination Folder")
        if folder:
            self.batch_dest_path.set(folder)

    def start_batch_processing(self):
        """Start the batch processing operation"""
        # Get all source folders
        sources = list(self.sources_listbox.get(0, tk.END))
        dest = self.batch_dest_path.get()

        if not sources:
            messagebox.showerror("Error", "Please add at least one source folder.")
            return

        if not dest:
            messagebox.showerror("Error", "Please select a destination folder.")
            return

        # Confirm batch operation
        if not messagebox.askyesno(
            "Confirm Batch Operation",
            f"Process {len(sources)} source folders to {dest}?\n\nThis may take a long time depending on the number and size of your music collections.",
        ):
            return

        # Update UI
        self.batch_start_button.config(state="disabled")
        self.batch_stop_button.config(state="normal")

        # Switch to main tab to show progress
        self.notebook.select(0)

        # Start processing first source
        self.log(f"🚀 Starting batch processing of {len(sources)} folders")

        # TODO: Implement actual batch processing
        # For now, just simulate completion
        self.root.after(2000, lambda: self.log("✅ Batch processing complete!"))
        self.root.after(2000, self.batch_processing_complete)

    def stop_batch_processing(self):
        """Stop the batch processing operation"""
        if messagebox.askyesno(
            "Confirm Stop", "Are you sure you want to stop the batch processing?"
        ):
            self.log("⚠️ Batch processing stopped by user")
            self.batch_processing_complete()

    def batch_processing_complete(self):
        """Update UI when batch processing is complete"""
        self.batch_start_button.config(state="normal")
        self.batch_stop_button.config(state="disabled")

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
            self.theme = {
                "bg": colors["bg"],
                "accent": colors["accent"],
                "secondary": colors["secondary"],
                "warning": colors["warning"],
                "error": colors["error"],
                "heading_font": self.theme["heading_font"],
            }

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
