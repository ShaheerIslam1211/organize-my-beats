"""Top-level package for organize_my_beats."""

__author__ = "Shaheer Islam"
__email__ = "shaheer.muzaffar.7@gmail.com"
__version__ = "1.0"

# Import main functionality for easier access
from .organize_my_beats import MusicOrganizer, AUDIO_EXTENSIONS, copy_by_year

# Import GUI classes
from .gui import MusicOrganizerApp
from .advanced_gui import MusicOrganizerAdvanced


# Expose main entry points
def run_gui():
    """Run the basic Tkinter GUI."""
    import tkinter as tk

    root = tk.Tk()
    app = MusicOrganizerApp(root)
    root.mainloop()


def run_advanced_gui():
    """Run the advanced PyQt5 GUI."""
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = MusicOrganizerAdvanced()
    window.show()
    sys.exit(app.exec_())


def run_cli():
    """Run the command-line interface."""
    from .cli import main
    import sys

    sys.exit(main())
