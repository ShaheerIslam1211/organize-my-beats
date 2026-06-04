#!/usr/bin/env python
"""Advanced GUI for organize_my_beats using PyQt5."""

from __future__ import annotations

import csv
import sys
import webbrowser
from pathlib import Path

from PyQt5.QtCore import Qt, QSettings, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from organize_my_beats.engine import (
    DuplicateMode,
    NamingTemplate,
    OperationMode,
    OrganizeMode,
    OrganizeOptions,
    OrganizeStats,
    TrackMetadata,
    format_duration,
    organize_library,
    scan_library,
)
from organize_my_beats.report import BatchReport

APP_STYLE = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #e0e0e0;
}
QGroupBox {
    border: 1px solid #3a3a5c;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 14px;
    font-weight: bold;
    color: #a0a0ff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QLineEdit, QComboBox, QTextEdit, QTableWidget {
    background-color: #2a2a3e;
    border: 1px solid #4a4a6a;
    border-radius: 6px;
    padding: 6px;
    color: #f0f0f0;
}
QPushButton {
    background-color: #4a4a8a;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover { background-color: #5a5aaa; }
QPushButton:disabled { background-color: #3a3a4a; color: #888; }
QPushButton#startBtn { background-color: #2e7d32; }
QPushButton#startBtn:hover { background-color: #388e3c; }
QPushButton#stopBtn { background-color: #c62828; }
QPushButton#stopBtn:hover { background-color: #d32f2f; }
QTabWidget::pane { border: 1px solid #3a3a5c; border-radius: 6px; }
QTabBar::tab {
    background: #2a2a3e;
    color: #aaa;
    padding: 8px 18px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected { background: #4a4a8a; color: white; }
QProgressBar {
    border: 1px solid #4a4a6a;
    border-radius: 6px;
    text-align: center;
    background: #2a2a3e;
}
QProgressBar::chunk { background-color: #6a6aff; border-radius: 5px; }
QHeaderView::section {
    background-color: #2a2a3e;
    color: #a0a0ff;
    padding: 6px;
    border: none;
}
QStatusBar { background: #161622; color: #888; }
"""


class ScanWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(list)

    def __init__(self, source: str, include_subfolders: bool):
        super().__init__()
        self.source = Path(source)
        self.include_subfolders = include_subfolders
        self._stop = False

    def run(self):
        tracks = scan_library(
            self.source,
            self.include_subfolders,
            lambda cur, total, msg: self.progress.emit(cur, total, msg),
        )
        self.finished.emit(tracks)

    def stop(self):
        self._stop = True


class OrganizeWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(object)

    def __init__(self, source: str, dest: str, options: OrganizeOptions):
        super().__init__()
        self.source = Path(source)
        self.dest = Path(dest)
        self.options = options
        self._stop = False

    def run(self):
        stats = organize_library(
            self.source,
            self.dest,
            self.options,
            lambda cur, total, msg: self.progress.emit(cur, total, msg),
            lambda: self._stop,
        )
        self.finished.emit(stats)

    def stop(self):
        self._stop = True


class StatCard(QFrame):
    def __init__(self, title: str, value: str = "0"):
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(
            "QFrame { background:#2a2a3e; border:1px solid #4a4a6a; border-radius:8px; }"
        )
        layout = QVBoxLayout(self)
        self.value_label = QLabel(value)
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setFont(QFont("Helvetica", 22, QFont.Bold))
        self.value_label.setStyleSheet("color:#8af; border:none;")
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color:#888; border:none; font-size:11px;")
        layout.addWidget(self.value_label)
        layout.addWidget(title_label)

    def set_value(self, value: str):
        self.value_label.setText(value)


class MusicOrganizerAdvanced(QMainWindow):
    SETTINGS_KEY = "OrganizeMyBeats"

    def __init__(self):
        super().__init__()
        self.settings = QSettings(self.SETTINGS_KEY, "OrganizeMyBeats")
        self.worker = None
        self.scan_results: list[TrackMetadata] = []
        self.last_stats: OrganizeStats | None = None

        self.setWindowTitle("Organize My Beats")
        self.setMinimumSize(1050, 750)
        self.setStyleSheet(APP_STYLE)
        self._build_ui()
        self._load_settings()
        self.statusBar().showMessage("Ready — scan your library or start organizing")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        header = QLabel("Organize My Beats")
        header.setFont(QFont("Helvetica", 20, QFont.Bold))
        header.setStyleSheet("color:#a0a0ff; padding:4px 0;")
        sub = QLabel("Sort your music by year, artist, album, genre, or decade")
        sub.setStyleSheet("color:#777; margin-bottom:8px;")
        layout.addWidget(header)
        layout.addWidget(sub)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tabs.addTab(self._build_organize_tab(), "Organize")
        self.tabs.addTab(self._build_library_tab(), "Library Preview")
        self.tabs.addTab(self._build_stats_tab(), "Statistics")

        self.setStatusBar(QStatusBar())

    def _folder_row(self, label: str, attr: str, browse_slot) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        field = QLineEdit()
        field.setPlaceholderText(f"Select {label.lower()}...")
        setattr(self, attr, field)
        btn = QPushButton("Browse")
        btn.clicked.connect(browse_slot)
        row.addWidget(field, stretch=1)
        row.addWidget(btn)
        return row

    def _build_organize_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        folders = QGroupBox("Folders")
        folder_layout = QVBoxLayout(folders)
        folder_layout.addLayout(self._folder_row("Source:", "source_path", self.browse_source))
        folder_layout.addLayout(
            self._folder_row("Destination:", "dest_path", self.browse_dest)
        )
        layout.addWidget(folders)

        rules = QGroupBox("Organization Rules")
        rules_grid = QGridLayout(rules)

        rules_grid.addWidget(QLabel("Sort by:"), 0, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(
            [
                "Year",
                "Artist",
                "Album",
                "Genre",
                "Artist / Album",
                "Decade",
            ]
        )
        rules_grid.addWidget(self.mode_combo, 0, 1)

        rules_grid.addWidget(QLabel("File naming:"), 0, 2)
        self.naming_combo = QComboBox()
        self.naming_combo.addItems(
            [
                "Keep original filename",
                "Artist - Title",
                "Track - Artist - Title",
                "Year - Artist - Title",
            ]
        )
        rules_grid.addWidget(self.naming_combo, 0, 3)

        rules_grid.addWidget(QLabel("Operation:"), 1, 0)
        self.operation_combo = QComboBox()
        self.operation_combo.addItems(["Copy files", "Move files"])
        rules_grid.addWidget(self.operation_combo, 1, 1)

        rules_grid.addWidget(QLabel("Duplicates:"), 1, 2)
        self.duplicate_combo = QComboBox()
        self.duplicate_combo.addItems(["Skip", "Overwrite", "Rename"])
        rules_grid.addWidget(self.duplicate_combo, 1, 3)

        layout.addWidget(rules)

        options = QGroupBox("Options")
        opt_layout = QVBoxLayout(options)
        self.unknown_year_checkbox = QCheckBox(
            "Place files without year/decade into an 'Unknown' folder"
        )
        self.unknown_year_checkbox.setChecked(True)
        self.subfolders_checkbox = QCheckBox("Include subfolders")
        self.subfolders_checkbox.setChecked(True)
        self.dry_run_checkbox = QCheckBox("Dry run (preview only — don't copy or move)")
        self.report_checkbox = QCheckBox("Generate HTML report after organizing")
        self.report_checkbox.setChecked(True)
        for cb in (
            self.unknown_year_checkbox,
            self.subfolders_checkbox,
            self.dry_run_checkbox,
            self.report_checkbox,
        ):
            opt_layout.addWidget(cb)
        layout.addWidget(options)

        progress_row = QHBoxLayout()
        progress_row.addWidget(QLabel("Progress:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_row.addWidget(self.progress_bar)
        layout.addLayout(progress_row)

        btn_row = QHBoxLayout()
        self.start_button = QPushButton("Start Organizing")
        self.start_button.setObjectName("startBtn")
        self.start_button.clicked.connect(self.start_processing)
        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("stopBtn")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_processing)
        self.open_dest_button = QPushButton("Open Destination")
        self.open_dest_button.clicked.connect(self.open_destination)
        btn_row.addWidget(self.start_button)
        btn_row.addWidget(self.stop_button)
        btn_row.addStretch()
        btn_row.addWidget(self.open_dest_button)
        layout.addLayout(btn_row)

        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout(log_group)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(200)
        log_layout.addWidget(self.log_output)
        layout.addWidget(log_group)

        return tab

    def _build_library_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        toolbar = QHBoxLayout()
        self.scan_button = QPushButton("Scan Library")
        self.scan_button.clicked.connect(self.scan_library)
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter by title, artist, album, year, genre...")
        self.filter_input.textChanged.connect(self.apply_library_filter)
        self.missing_year_only = QCheckBox("Show missing year only")
        self.missing_year_only.stateChanged.connect(self.apply_library_filter)
        toolbar.addWidget(self.scan_button)
        toolbar.addWidget(self.filter_input, stretch=1)
        toolbar.addWidget(self.missing_year_only)
        layout.addLayout(toolbar)

        self.library_table = QTableWidget(0, 7)
        self.library_table.setHorizontalHeaderLabels(
            ["Title", "Artist", "Album", "Year", "Genre", "Duration", "File"]
        )
        self.library_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.library_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.library_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.library_table.setAlternatingRowColors(True)
        layout.addWidget(self.library_table)

        self.library_summary = QLabel("No library scanned yet.")
        self.library_summary.setStyleSheet("color:#888; padding:4px;")
        layout.addWidget(self.library_summary)

        return tab

    def _build_stats_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        cards = QHBoxLayout()
        self.card_total = StatCard("Total Files")
        self.card_copied = StatCard("Copied")
        self.card_skipped = StatCard("Skipped")
        self.card_errors = StatCard("Errors")
        for card in (self.card_total, self.card_copied, self.card_skipped, self.card_errors):
            cards.addWidget(card)
        layout.addLayout(cards)

        self.stats_table = QTableWidget(0, 2)
        self.stats_table.setHorizontalHeaderLabels(["Category", "Count"])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.stats_table)

        export_row = QHBoxLayout()
        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.clicked.connect(self.export_stats_csv)
        self.open_report_btn = QPushButton("Open HTML Report")
        self.open_report_btn.clicked.connect(self.open_last_report)
        self.open_report_btn.setEnabled(False)
        export_row.addWidget(self.export_csv_btn)
        export_row.addWidget(self.open_report_btn)
        export_row.addStretch()
        layout.addLayout(export_row)

        self.last_report_path: Path | None = None
        return tab

    def _load_settings(self):
        self.source_path.setText(self.settings.value("source", ""))
        self.dest_path.setText(self.settings.value("dest", ""))
        self.mode_combo.setCurrentIndex(int(self.settings.value("mode", 0)))
        self.naming_combo.setCurrentIndex(int(self.settings.value("naming", 0)))
        self.operation_combo.setCurrentIndex(int(self.settings.value("operation", 0)))
        self.unknown_year_checkbox.setChecked(
            self.settings.value("unknown_year", "true") == "true"
        )
        self.subfolders_checkbox.setChecked(
            self.settings.value("subfolders", "true") == "true"
        )

    def _save_settings(self):
        self.settings.setValue("source", self.source_path.text())
        self.settings.setValue("dest", self.dest_path.text())
        self.settings.setValue("mode", self.mode_combo.currentIndex())
        self.settings.setValue("naming", self.naming_combo.currentIndex())
        self.settings.setValue("operation", self.operation_combo.currentIndex())
        self.settings.setValue("unknown_year", self.unknown_year_checkbox.isChecked())
        self.settings.setValue("subfolders", self.subfolders_checkbox.isChecked())

    def browse_source(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder")
        if folder:
            self.source_path.setText(folder)

    def browse_dest(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if folder:
            self.dest_path.setText(folder)

    def open_destination(self):
        dest = self.dest_path.text().strip()
        if dest and Path(dest).exists():
            webbrowser.open(f"file://{Path(dest).resolve()}")
        else:
            QMessageBox.information(self, "No Destination", "Set a valid destination folder first.")

    def log(self, message: str):
        self.log_output.append(message)
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum()
        )

    def _get_options(self) -> OrganizeOptions:
        mode_map = {
            0: OrganizeMode.YEAR,
            1: OrganizeMode.ARTIST,
            2: OrganizeMode.ALBUM,
            3: OrganizeMode.GENRE,
            4: OrganizeMode.ARTIST_ALBUM,
            5: OrganizeMode.DECADE,
        }
        naming_map = {
            0: NamingTemplate.ORIGINAL,
            1: NamingTemplate.ARTIST_TITLE,
            2: NamingTemplate.TRACK_ARTIST_TITLE,
            3: NamingTemplate.YEAR_ARTIST_TITLE,
        }
        duplicate_map = {
            0: DuplicateMode.SKIP,
            1: DuplicateMode.OVERWRITE,
            2: DuplicateMode.RENAME,
        }
        return OrganizeOptions(
            mode=mode_map[self.mode_combo.currentIndex()],
            naming=naming_map[self.naming_combo.currentIndex()],
            operation=(
                OperationMode.MOVE
                if self.operation_combo.currentIndex() == 1
                else OperationMode.COPY
            ),
            duplicate=duplicate_map[self.duplicate_combo.currentIndex()],
            unknown_year_folder=self.unknown_year_checkbox.isChecked(),
            dry_run=self.dry_run_checkbox.isChecked(),
            include_subfolders=self.subfolders_checkbox.isChecked(),
            generate_report=self.report_checkbox.isChecked(),
        )

    def _validate_paths(self) -> tuple[Path, Path] | None:
        source = self.source_path.text().strip()
        dest = self.dest_path.text().strip()
        if not source or not dest:
            QMessageBox.warning(self, "Missing Information", "Select both source and destination folders.")
            return None

        source_path = Path(source)
        dest_path = Path(dest)

        if not source_path.exists():
            QMessageBox.warning(self, "Invalid Source", "The source folder does not exist.")
            return None

        if source_path.resolve() == dest_path.resolve():
            QMessageBox.warning(
                self,
                "Invalid Paths",
                "Source and destination cannot be the same folder.",
            )
            return None

        if not dest_path.exists():
            reply = QMessageBox.question(
                self,
                "Create Destination",
                f"Create destination folder?\n{dest}",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return None
            try:
                dest_path.mkdir(parents=True)
            except OSError as exc:
                QMessageBox.critical(self, "Error", f"Could not create destination: {exc}")
                return None

        return source_path, dest_path

    def scan_library(self):
        paths = self._validate_paths()
        if not paths:
            return
        source_path, _ = paths

        self.scan_button.setEnabled(False)
        self.statusBar().showMessage("Scanning library...")
        self.worker = ScanWorker(source_path.as_posix(), self.subfolders_checkbox.isChecked())
        self.worker.progress.connect(self._on_scan_progress)
        self.worker.finished.connect(self._on_scan_complete)
        self.worker.start()

    def _on_scan_progress(self, current: int, total: int, message: str):
        if total:
            self.progress_bar.setValue(int((current / total) * 100))
        self.statusBar().showMessage(message)

    def _on_scan_complete(self, tracks: list):
        self.scan_results = tracks
        self._populate_library_table(tracks)
        self.scan_button.setEnabled(True)
        self.progress_bar.setValue(100)
        missing = sum(1 for t in tracks if not t.has_year)
        self.library_summary.setText(
            f"{len(tracks)} tracks found  •  {missing} missing year  •  "
            f"{len({t.artist for t in tracks})} artists  •  "
            f"{len({t.album for t in tracks})} albums"
        )
        self.statusBar().showMessage(f"Scan complete — {len(tracks)} tracks found")
        self.tabs.setCurrentIndex(1)

    def _populate_library_table(self, tracks: list[TrackMetadata]):
        self.library_table.setRowCount(len(tracks))
        for row, track in enumerate(tracks):
            values = [
                track.title,
                track.artist,
                track.album,
                track.year or "—",
                track.genre,
                format_duration(track.duration),
                track.path.name,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if not track.has_year:
                    item.setBackground(QColor("#4a3030"))
                self.library_table.setItem(row, col, item)

    def apply_library_filter(self):
        query = self.filter_input.text().lower().strip()
        missing_only = self.missing_year_only.isChecked()
        filtered = []
        for track in self.scan_results:
            if missing_only and track.has_year:
                continue
            haystack = " ".join(
                [
                    track.title,
                    track.artist,
                    track.album,
                    track.year or "",
                    track.genre,
                    track.path.name,
                ]
            ).lower()
            if not query or query in haystack:
                filtered.append(track)
        self._populate_library_table(filtered)
        self.library_summary.setText(f"Showing {len(filtered)} of {len(self.scan_results)} tracks")

    def start_processing(self):
        paths = self._validate_paths()
        if not paths:
            return
        source_path, dest_path = paths
        self._save_settings()

        options = self._get_options()
        if options.operation == OperationMode.MOVE:
            reply = QMessageBox.warning(
                self,
                "Move Files",
                "Move will remove files from the source folder.\nContinue?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        self.log_output.clear()
        self.progress_bar.setValue(0)
        self.stats_table.setRowCount(0)

        prefix = "[DRY RUN] " if options.dry_run else ""
        self.log(f"{prefix}Starting organization...")
        self.log(f"Mode: {self.mode_combo.currentText()}  |  Naming: {self.naming_combo.currentText()}")
        self.log(f"Source: {source_path}")
        self.log(f"Destination: {dest_path}")

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.worker = OrganizeWorker(source_path.as_posix(), dest_path.as_posix(), options)
        self.worker.progress.connect(self._on_organize_progress)
        self.worker.finished.connect(self._on_organize_complete)
        self.worker.start()

    def stop_processing(self):
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm Stop",
                "Stop the current operation?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.worker.stop()
                self.worker.wait()
                self.log("Operation stopped.")
                self._set_idle_state()

    def _on_organize_progress(self, current: int, total: int, message: str):
        if total:
            self.progress_bar.setValue(int((current / total) * 100))
        self.log(message)
        self.statusBar().showMessage(message)

    def _on_organize_complete(self, stats: OrganizeStats):
        self.last_stats = stats
        self.log("Organization complete.")
        self.log(
            f"Total: {stats.total}  |  Copied: {stats.copied}  |  Moved: {stats.moved}  |  "
            f"Skipped: {stats.skipped}  |  No metadata: {stats.no_metadata}  |  Errors: {stats.errors}"
        )

        self.card_total.set_value(str(stats.total))
        self.card_copied.set_value(str(stats.copied + stats.moved))
        self.card_skipped.set_value(str(stats.skipped))
        self.card_errors.set_value(str(stats.errors))

        options = self._get_options()
        bucket = stats.bucket_for(options.mode)
        sorted_items = sorted(bucket.items(), key=lambda x: x[0], reverse=True)
        self.stats_table.setRowCount(len(sorted_items))
        label = options.mode.value.replace("_", " ").title()
        self.stats_table.setHorizontalHeaderLabels([label, "Count"])
        for row, (key, count) in enumerate(sorted_items):
            self.stats_table.setItem(row, 0, QTableWidgetItem(key))
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignCenter)
            self.stats_table.setItem(row, 1, count_item)

        if options.generate_report and not options.dry_run:
            self.last_report_path = self._generate_report(stats)
            self.open_report_btn.setEnabled(self.last_report_path is not None)

        self.tabs.setCurrentIndex(2)
        self._set_idle_state()
        self.statusBar().showMessage("Organization complete")

    def _generate_report(self, stats: OrganizeStats) -> Path | None:
        dest = Path(self.dest_path.text().strip())
        report = BatchReport(dest)
        report.stats["total_files"] = stats.total
        report.stats["processed_files"] = stats.copied + stats.moved
        report.stats["skipped_files"] = stats.skipped
        report.stats["error_files"] = stats.errors
        report.stats["years"] = stats.years
        report.stats["formats"] = stats.formats
        report.add_source_folder(
            Path(self.source_path.text().strip()),
            stats.total,
            0,
            0.0,
        )
        try:
            path = report.generate_html_report()
            self.log(f"Report saved: {path}")
            return path
        except OSError as exc:
            self.log(f"Could not save report: {exc}")
            return None

    def export_stats_csv(self):
        if self.stats_table.rowCount() == 0:
            QMessageBox.information(self, "No Data", "Run an organization first to export statistics.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Statistics", "organize_stats.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    self.stats_table.horizontalHeaderItem(0).text(),
                    self.stats_table.horizontalHeaderItem(1).text(),
                ]
            )
            for row in range(self.stats_table.rowCount()):
                writer.writerow(
                    [
                        self.stats_table.item(row, 0).text(),
                        self.stats_table.item(row, 1).text(),
                    ]
                )
        self.statusBar().showMessage(f"Exported to {path}")

    def open_last_report(self):
        if self.last_report_path and self.last_report_path.exists():
            webbrowser.open(self.last_report_path.as_uri())

    def _set_idle_state(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)


def main():
    app = QApplication(sys.argv)
    window = MusicOrganizerAdvanced()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
