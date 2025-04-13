#!/usr/bin/env python
"""
Main entry point for organize_my_beats package.

This module allows the package to be run as a script using:
    python -m organize_my_beats
"""

import sys
import argparse

from organize_my_beats import run_gui, run_advanced_gui, run_cli


def main():
    """
    Parse command line arguments and launch the appropriate interface.
    """
    parser = argparse.ArgumentParser(
        description="Organize music files by year based on metadata",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Interface selection arguments
    interface_group = parser.add_mutually_exclusive_group()
    interface_group.add_argument(
        "-g", "--gui", action="store_true", help="Launch the basic GUI (Tkinter)"
    )
    interface_group.add_argument(
        "-a",
        "--advanced-gui",
        action="store_true",
        help="Launch the advanced GUI (PyQt5)",
    )
    interface_group.add_argument(
        "-c", "--cli", action="store_true", help="Run in command-line mode"
    )

    # Parse arguments
    args, remaining_args = parser.parse_known_args()

    # Determine which interface to launch
    if args.cli:
        # Pass remaining arguments to CLI
        sys.argv = [sys.argv[0]] + remaining_args
        run_cli()
    elif args.gui:
        run_gui()
    elif args.advanced_gui or not (args.cli or args.gui):
        # Default to advanced GUI if no interface specified
        run_advanced_gui()


if __name__ == "__main__":
    main()
