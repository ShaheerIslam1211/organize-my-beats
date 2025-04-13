"""Main module."""

import os
import shutil
from pathlib import Path
from mutagen import File as MutagenFile

# Set your root music folder here
SOURCE_DIR = Path(r"/Users/personal_macbook/Music/Music/Media.localized/Music ")
DEST_DIR = Path(
    r"/Users/personal_macbook/ai_completion/yearwise_songs"
)  # Where songs will be copied

# Supported audio file extensions
AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".ogg", ".wav", ".wma", ".aac"}


def get_song_year(filepath):
    try:
        audio = MutagenFile(filepath, easy=True)
        if not audio:
            return None
        # Try common fields for year
        for tag in ("date", "year", "originaldate", "copyright"):
            if tag in audio:
                year_str = str(audio[tag][0])
                if len(year_str) >= 4 and year_str[:4].isdigit():
                    return year_str[:4]
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return None


def copy_by_year(source_folder, destination_folder):
    for root, dirs, files in os.walk(source_folder):
        for file in files:
            filepath = Path(root) / file
            if filepath.suffix.lower() not in AUDIO_EXTENSIONS:
                continue
            year = get_song_year(filepath)
            if year:
                year_folder = destination_folder / year
                year_folder.mkdir(parents=True, exist_ok=True)
                dest_file = year_folder / file
                # Avoid overwriting if the same file exists
                if not dest_file.exists():
                    try:
                        shutil.copy2(filepath, dest_file)
                        print(f"Copied: {filepath} --> {dest_file}")
                    except Exception as e:
                        print(f"Failed to copy {filepath}: {e}")
            else:
                print(f"Year not found for: {filepath}")


if __name__ == "__main__":
    copy_by_year(SOURCE_DIR, DEST_DIR)
    print("\n✅ Done organizing by year!")
