#!/usr/bin/env python3
"""macOS application entry point for Organize My Beats."""

import sys


def main() -> None:
    """Launch the advanced GUI as a standalone macOS app."""
    if sys.platform == "darwin":
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QApplication

        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    from organize_my_beats import run_advanced_gui

    run_advanced_gui()


if __name__ == "__main__":
    main()
