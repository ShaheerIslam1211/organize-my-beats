#!/usr/bin/env python
"""
Command-line interface for organize_my_beats.

This module provides a command-line interface for the music organizer,
allowing users to run the tool from the terminal with various options.
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from mutagen import File as MutagenFile

# Supported audio file extensions
AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".ogg", ".wav", ".wma", ".aac"}


def get_song_year(filepath):
    """
    Extract year information from audio file metadata.

    Args:
        filepath: Path to the audio file

    Returns:
        String containing the year if found, None otherwise
    """
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
        if args.verbose:
            print(f"⚠️ Error reading metadata: {filepath.name} - {str(e)}")
    return None


def copy_by_year(source_folder, destination_folder, options):
    """
    Process audio files and copy them to year-based folders.

    Args:
        source_folder: Path to the source directory
        destination_folder: Path to the destination directory
        options: Dictionary containing processing options

    Returns:
        Dictionary with processing statistics
    """
    stats = {
        "total": 0,
        "copied": 0,
        "skipped": 0,
        "no_year": 0,
        "errors": 0,
        "years": {},
    }

    # Count total files for progress tracking
    total_files = 0
    if options.get("verbose"):
        print("🔍 Counting audio files...")
        for item in Path(source_folder).glob("**/*"):
            if item.is_file() and item.suffix.lower() in AUDIO_EXTENSIONS:
                total_files += 1
        print(f"Found {total_files} audio files to process")

    # Process files
    processed_files = 0
    for root, dirs, files in os.walk(source_folder):
        for file in files:
            filepath = Path(root) / file
            if filepath.suffix.lower() not in AUDIO_EXTENSIONS:
                continue

            stats["total"] += 1
            processed_files += 1

            # Show progress
            if options.get("verbose") and total_files > 0 and processed_files % 10 == 0:
                progress = int((processed_files / total_files) * 100)
                print(f"Progress: {progress}% ({processed_files}/{total_files})")

            try:
                year = get_song_year(filepath)
                if year:
                    # Update year statistics
                    if year not in stats["years"]:
                        stats["years"][year] = 0
                    stats["years"][year] += 1

                    # Create year folder and copy file
                    year_folder = Path(destination_folder) / year
                    year_folder.mkdir(parents=True, exist_ok=True)
                    dest_file = year_folder / filepath.name

                    if not dest_file.exists() or options.get("overwrite"):
                        shutil.copy2(filepath, dest_file)
                        stats["copied"] += 1
                        if options.get("verbose"):
                            print(f"✅ Copied to {year}: {filepath.name}")
                    else:
                        stats["skipped"] += 1
                        if options.get("verbose"):
                            print(f"⚠️ Skipped (already exists): {filepath.name}")
                else:
                    stats["no_year"] += 1
                    if options.get("verbose"):
                        print(f"❓ No year found: {filepath.name}")

                    # Handle files with no year metadata if option is enabled
                    if options.get("unknown_year_folder"):
                        unknown_folder = Path(destination_folder) / "Unknown Year"
                        unknown_folder.mkdir(parents=True, exist_ok=True)
                        dest_file = unknown_folder / filepath.name

                        if not dest_file.exists() or options.get("overwrite"):
                            shutil.copy2(filepath, dest_file)
                            if options.get("verbose"):
                                print(
                                    f"📁 Copied to Unknown Year folder: {filepath.name}"
                                )
            except Exception as e:
                stats["errors"] += 1
                if options.get("verbose"):
                    print(f"❌ Error processing {filepath.name}: {str(e)}")

    return stats


def main():
    """
    Main entry point for the command-line interface.
    """
    parser = argparse.ArgumentParser(
        description="Organize music files by year based on metadata",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("source", help="Source directory containing music files")

    parser.add_argument(
        "destination", help="Destination directory where organized files will be copied"
    )

    parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help="Overwrite existing files in destination",
    )

    parser.add_argument(
        "-u",
        "--unknown-year",
        action="store_true",
        help="Create 'Unknown Year' folder for files without year metadata",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed progress information",
    )

    parser.add_argument(
        "-s", "--stats", action="store_true", help="Show statistics after completion"
    )

    global args
    args = parser.parse_args()

    # Validate paths
    source_path = Path(args.source)
    dest_path = Path(args.destination)

    if not source_path.exists():
        print(f"Error: Source directory '{args.source}' does not exist")
        return 1

    if not dest_path.exists():
        try:
            dest_path.mkdir(parents=True)
            print(f"Created destination directory: {args.destination}")
        except Exception as e:
            print(f"Error: Could not create destination directory: {str(e)}")
            return 1

    # Process options
    options = {
        "overwrite": args.overwrite,
        "unknown_year_folder": args.unknown_year,
        "verbose": args.verbose,
    }

    print(f"🚀 Starting organization process...")
    print(f"📂 Source: {args.source}")
    print(f"📁 Destination: {args.destination}")

    # Process files
    stats = copy_by_year(args.source, args.destination, options)

    # Show completion message and statistics
    print("\n✅ Organization complete!")

    if args.stats or args.verbose:
        print(f"\n📊 Statistics:")
        print(f"   - Total files processed: {stats['total']}")
        print(f"   - Files copied: {stats['copied']}")
        print(f"   - Files skipped (already exist): {stats['skipped']}")
        print(f"   - Files without year metadata: {stats['no_year']}")
        print(f"   - Errors encountered: {stats['errors']}")

        if stats["years"]:
            print("\n📅 Files by year:")
            for year, count in sorted(stats["years"].items(), reverse=True):
                print(f"   - {year}: {count} files")

    return 0


if __name__ == "__main__":
    sys.exit(main())
