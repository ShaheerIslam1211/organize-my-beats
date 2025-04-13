#!/usr/bin/env python
"""
Main entry point for organize_my_beats package.

This module allows the package to be run as a script using:
    python -m organize_my_beats
"""

import sys
import argparse

from organize_my_beats import run


def main():
    """
    Parse command line arguments and launch the appropriate interface.
    """
    parser = argparse.ArgumentParser(
        description="Organize music files by year based on metadata",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Interface selection arguments
    parser.add_argument(
        "--advanced",
        action="store_true",
        help="Launch the advanced GUI (PyQt6)"
    )

    # Parse arguments
    args = parser.parse_args()

    # Run the application
    run(sys.argv[1:])


if __name__ == "__main__":
    main()
