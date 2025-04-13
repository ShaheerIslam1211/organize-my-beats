#!/usr/bin/env python
"""
Advanced GUI for organize_my_beats using PyQt5.

This module provides a modern, feature-rich interface for the music organizer
with advanced UI elements and better user interaction.
"""

import os
import sys
import shutil
import threading
from pathlib import Path
from datetime import datetime
from mutagen import File as MutagenFile

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QFileDialog,
    QProgressBar,
    QTextEdit,
    QGroupBox,
    QCheckBox,
    QSpinBox,
    QComboBox,
    QMessageBox,
    QSplitter,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QStyle,
    QTabWidget,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QFont, QColor

# Supported audio file extensions
AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".ogg", ".wav", ".wma", ".aac"}


class WorkerThread(QThread):
    """Worker thread to handle file processing without freezing the UI."""

    update_signal = pyqtSignal(str)  # Signal for log updates
    progress_signal = pyqtSignal(int)  # Signal for progress updates
    finished_signal = pyqtSignal(dict)  # Signal for completion with stats

    def __init__(self, source_dir, dest_dir, options):
        super().__init__()
        self.source_dir = Path(source_dir)
        self.dest_dir = Path(dest_dir)
        self.options = options
        self.running = True
        self.total_files = 0
        self.processed_files = 0
        self.stats = {
            "total": 0,
            "copied": 0,
            "skipped": 0,
            "no_year": 0,
            "errors": 0,
            "years": {},
        }

    def run(self):
        """Main processing function that runs in a separate thread."""
        self.update_signal.emit("🔍 Scanning for audio files...")

        # First count total files for progress tracking
        self.count_files(self.source_dir)
        self.update_signal.emit(f"Found {self.total_files} audio files to process")

        # Then process the files
        self.process_directory(self.source_dir)

        # Emit completion signal with statistics
        self.finished_signal.emit(self.stats)

    def count_files(self, directory):
        """Count total audio files for progress tracking."""
        for item in directory.glob("**/*"):
            if item.is_file() and item.suffix.lower() in AUDIO_EXTENSIONS:
                self.total_files += 1

    def process_directory(self, directory):
        """Process all audio files in a directory and its subdirectories."""
        for item in directory.glob("**/*"):
            if not self.running:  # Check if we should stop
                return

            if item.is_file() and item.suffix.lower() in AUDIO_EXTENSIONS:
                self.process_file(item)
                self.processed_files += 1
                progress = (
                    int((self.processed_files / self.total_files) * 100)
                    if self.total_files > 0
                    else 0
                )
                self.progress_signal.emit(progress)

    def process_file(self, file_path):
        """Process a single audio file."""
        self.stats["total"] += 1

        try:
            year = self.get_song_year(file_path)
            if year:
                # Update year statistics
                if year not in self.stats["years"]:
                    self.stats["years"][year] = 0
                self.stats["years"][year] += 1

                # Create year folder and copy file
                year_folder = self.dest_dir / year
                year_folder.mkdir(parents=True, exist_ok=True)
                dest_file = year_folder / file_path.name

                if not dest_file.exists() or self.options.get("overwrite", False):
                    shutil.copy2(file_path, dest_file)
                    self.stats["copied"] += 1
                    self.update_signal.emit(f"✅ Copied to {year}: {file_path.name}")
                else:
                    self.stats["skipped"] += 1
                    self.update_signal.emit(
                        f"⚠️ Skipped (already exists): {file_path.name}"
                    )
            else:
                self.stats["no_year"] += 1
                self.update_signal.emit(f"❓ No year found: {file_path.name}")

                # Handle files with no year metadata if option is enabled
                if self.options.get("unknown_year_folder", False):
                    unknown_folder = self.dest_dir / "Unknown Year"
                    unknown_folder.mkdir(parents=True, exist_ok=True)
                    dest_file = unknown_folder / file_path.name

                    if not dest_file.exists() or self.options.get("overwrite", False):
                        shutil.copy2(file_path, dest_file)
                        self.update_signal.emit(
                            f"📁 Copied to Unknown Year folder: {file_path.name}"
                        )
        except Exception as e:
            self.stats["errors"] += 1
            self.update_signal.emit(f"❌ Error processing {file_path.name}: {str(e)}")

    def get_song_year(self, filepath):
        """Extract year information from audio file metadata."""
        try:
            audio = MutagenFile(filepath, easy=True)
            if not audio:
                return None

            # Try common fields for year information
            for tag in ("date", "year", "originaldate", "copyright"):
                if tag in audio:
                    year_str = str(audio[tag][0])
                    # Extract year from various formats (YYYY, YYYY-MM-DD, etc.)
                    if len(year_str) >= 4 and year_str[:4].isdigit():
                        year = year_str[:4]
                        # Validate year is reasonable (between 1900 and current year + 1)
                        current_year = datetime.now().year
                        if 1900 <= int(year) <= current_year + 1:
                            return year
        except Exception as e:
            self.update_signal.emit(
                f"⚠️ Error reading metadata: {filepath.name} - {str(e)}"
            )
        return None

    def stop(self):
        """Stop the processing thread."""
        self.running = False


class MusicOrganizerAdvanced(QMainWindow):
    """Advanced PyQt5 GUI for the music organizer application."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Organize My Beats - Advanced Music Organizer")
        self.setMinimumSize(900, 700)

        # Initialize UI components
        self.init_ui()

        # Worker thread
        self.worker = None

    def init_ui(self):
        """Initialize the user interface."""
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # Create tab widget for different views
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Main tab
        main_tab = QWidget()
        main_tab_layout = QVBoxLayout(main_tab)

        # Source and destination selection
        folder_group = QGroupBox("Folder Selection")
        folder_layout = QVBoxLayout(folder_group)

        # Source folder selection
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Source Folder:"))
        self.source_path = QLineEdit()
        source_layout.addWidget(self.source_path)
        source_btn = QPushButton("Browse")
        source_btn.clicked.connect(self.browse_source)
        source_layout.addWidget(source_btn)
        folder_layout.addLayout(source_layout)

        # Destination folder selection
        dest_layout = QHBoxLayout()
        dest_layout.addWidget(QLabel("Destination Folder:"))
        self.dest_path = QLineEdit()
        dest_layout.addWidget(self.dest_path)
        dest_btn = QPushButton("Browse")
        dest_btn.clicked.connect(self.browse_dest)
        dest_layout.addWidget(dest_btn)
        folder_layout.addLayout(dest_layout)

        main_tab_layout.addWidget(folder_group)

        # Options group
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)

        # Overwrite existing files option
        self.overwrite_checkbox = QCheckBox("Overwrite existing files")
        options_layout.addWidget(self.overwrite_checkbox)

        # Create folder for files with unknown year
        self.unknown_year_checkbox = QCheckBox(
            "Create 'Unknown Year' folder for files without year metadata"
        )
        self.unknown_year_checkbox.setChecked(True)
        options_layout.addWidget(self.unknown_year_checkbox)

        main_tab_layout.addWidget(options_group)

        # Progress bar
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("Progress:"))
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        main_tab_layout.addLayout(progress_layout)

        # Action buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Organizing")
        self.start_button.clicked.connect(self.start_processing)
        self.start_button.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 8px;"
        )
        button_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_processing)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet(
            "background-color: #f44336; color: white; padding: 8px;"
        )
        button_layout.addWidget(self.stop_button)

        main_tab_layout.addLayout(button_layout)

        # Log output
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output)
        main_tab_layout.addWidget(log_group)

        # Add main tab to tab widget
        self.tabs.addTab(main_tab, "Organizer")

        # Statistics tab
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)

        self.stats_table = QTableWidget(0, 2)
        self.stats_table.setHorizontalHeaderLabels(["Year", "Number of Songs"])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        stats_layout.addWidget(self.stats_table)

        self.tabs.addTab(stats_tab, "Statistics")

        # Set the central widget
        self.setCentralWidget(main_widget)

        # Initialize with a welcome message
        self.log(
            "Welcome to Organize My Beats! Select source and destination folders to begin."
        )

    def browse_source(self):
        """Open file dialog to select source folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder")
        if folder:
            self.source_path.setText(folder)

    def browse_dest(self):
        """Open file dialog to select destination folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if folder:
            self.dest_path.setText(folder)

    def log(self, message):
        """Add a message to the log output."""
        self.log_output.append(message)
        # Auto-scroll to the bottom
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum()
        )

    def start_processing(self):
        """Start the music organizing process."""
        source = self.source_path.text()
        dest = self.dest_path.text()

        if not source or not dest:
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please select both source and destination folders.",
            )
            return

        source_path = Path(source)
        dest_path = Path(dest)

        if not source_path.exists():
            QMessageBox.warning(
                self, "Invalid Source", "The source folder does not exist."
            )
            return

        if not dest_path.exists():
            # Ask if we should create the destination folder
            reply = QMessageBox.question(
                self,
                "Create Destination",
                f"The destination folder '{dest}' does not exist. Create it?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                try:
                    dest_path.mkdir(parents=True)
                except Exception as e:
                    QMessageBox.critical(
                        self, "Error", f"Could not create destination folder: {str(e)}"
                    )
                    return
            else:
                return

        # Clear previous results
        self.log_output.clear()
        self.progress_bar.setValue(0)
        self.stats_table.setRowCount(0)

        # Get options
        options = {
            "overwrite": self.overwrite_checkbox.isChecked(),
            "unknown_year_folder": self.unknown_year_checkbox.isChecked(),
        }

        # Create and start worker thread
        self.worker = WorkerThread(source, dest, options)
        self.worker.update_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.process_complete)

        # Update UI state
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        # Start processing
        self.log(f"🚀 Starting organization process...")
        self.log(f"📂 Source: {source}")
        self.log(f"📁 Destination: {dest}")
        self.worker.start()

    def stop_processing(self):
        """Stop the current processing operation."""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm Stop",
                "Are you sure you want to stop the current operation?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.log("⚠️ Stopping operation...")
                self.worker.stop()
                self.worker.wait()  # Wait for the thread to finish
                self.log("⚠️ Operation stopped by user")
                self.update_ui_state_stopped()

    def update_progress(self, value):
        """Update the progress bar."""
        self.progress_bar.setValue(value)

    def process_complete(self, stats):
        """Handle completion of the processing operation."""
        self.log("✅ Organization complete!")
        self.log(f"📊 Statistics:")
        self.log(f"   - Total files processed: {stats['total']}")
        self.log(f"   - Files copied: {stats['copied']}")
        self.log(f"   - Files skipped (already exist): {stats['skipped']}")
        self.log(f"   - Files without year metadata: {stats['no_year']}")
        self.log(f"   - Errors encountered: {stats['errors']}")

        # Update statistics table
        self.update_statistics(stats["years"])

        # Switch to statistics tab
        self.tabs.setCurrentIndex(1)

        # Update UI state
        self.update_ui_state_stopped()

    def update_ui_state_stopped(self):
        """Update UI state when processing is stopped or completed."""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def update_statistics(self, years_data):
        """Update the statistics table with year data."""
        # Sort years in descending order
        sorted_years = sorted(years_data.items(), key=lambda x: x[0], reverse=True)

        # Clear and resize the table
        self.stats_table.setRowCount(len(sorted_years))

        # Fill the table with data
        for row, (year, count) in enumerate(sorted_years):
            year_item = QTableWidgetItem(year)
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignCenter)

            self.stats_table.setItem(row, 0, year_item)
            self.stats_table.setItem(row, 1, count_item)


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    window = MusicOrganizerAdvanced()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
