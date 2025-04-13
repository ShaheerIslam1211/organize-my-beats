"""Main module."""

import os
import shutil
from pathlib import Path
from mutagen import File as MutagenFile
import threading
from queue import Queue
import time
from typing import Optional, Callable

# Set your root music folder here
SOURCE_DIR = Path(r"/Users/personal_macbook/Music/Music/Media.localized/Music ")
DEST_DIR = Path(
    r"/Users/personal_macbook/ai_completion/yearwise_songs"
)  # Where songs will be copied

# Supported audio file extensions
AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".ogg", ".wav", ".wma", ".aac"}

class MusicOrganizer:
    def __init__(self, source_dir: Path, dest_dir: Path, progress_callback: Optional[Callable] = None):
        self.source_dir = Path(source_dir)
        self.dest_dir = Path(dest_dir)
        self.progress_callback = progress_callback
        self.file_queue = Queue()
        self.processed_files = 0
        self.total_files = 0
        self.stats = {
            "total": 0,
            "copied": 0,
            "skipped": 0,
            "no_year": 0,
            "errors": 0,
            "years": {}
        }
        self.stop_event = threading.Event()
        self.worker_threads = []

    def get_song_year(self, filepath: Path) -> Optional[str]:
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

    def worker(self):
        while not self.stop_event.is_set():
            try:
                filepath = self.file_queue.get_nowait()
            except:
                break

            try:
                year = self.get_song_year(filepath)
                if year:
                    year_folder = self.dest_dir / year
                    year_folder.mkdir(parents=True, exist_ok=True)
                    dest_file = year_folder / filepath.name

                    if not dest_file.exists():
                        shutil.copy2(filepath, dest_file)
                        self.stats["copied"] += 1
                        self.stats["years"][year] = self.stats["years"].get(year, 0) + 1
                    else:
                        self.stats["skipped"] += 1
                else:
                    self.stats["no_year"] += 1

                self.processed_files += 1
                if self.progress_callback:
                    self.progress_callback(self.processed_files, self.total_files, self.stats)

            except Exception as e:
                print(f"Error processing {filepath}: {e}")
                self.stats["errors"] += 1
            finally:
                self.file_queue.task_done()

    def scan_files(self):
        """Scan for audio files and add them to the queue"""
        for root, _, files in os.walk(self.source_dir):
            if self.stop_event.is_set():
                break
            for file in files:
                filepath = Path(root) / file
                if filepath.suffix.lower() in AUDIO_EXTENSIONS:
                    self.file_queue.put(filepath)
                    self.total_files += 1
                    self.stats["total"] += 1

    def organize(self, num_workers: int = 4):
        """Start the organization process with multiple worker threads"""
        self.stop_event.clear()
        self.worker_threads = []

        # Start file scanning in a separate thread
        scanner_thread = threading.Thread(target=self.scan_files)
        scanner_thread.start()

        # Start worker threads
        for _ in range(num_workers):
            t = threading.Thread(target=self.worker)
            t.start()
            self.worker_threads.append(t)

        # Wait for all files to be processed
        self.file_queue.join()
        self.stop_event.set()

        # Wait for all threads to complete
        scanner_thread.join()
        for t in self.worker_threads:
            t.join()

        return self.stats

    def stop(self):
        """Stop the organization process"""
        self.stop_event.set()
        for t in self.worker_threads:
            t.join(timeout=1.0)

def copy_by_year(source_folder: Path, destination_folder: Path, progress_callback: Optional[Callable] = None) -> dict:
    """Organize music files by year with progress updates"""
    organizer = MusicOrganizer(source_folder, destination_folder, progress_callback)
    return organizer.organize()

if __name__ == "__main__":
    # Example usage
    SOURCE_DIR = Path(r"/Users/personal_macbook/Music/Music/Media.localized/Music")
    DEST_DIR = Path(r"/Users/personal_macbook/ai_completion/yearwise_songs")

    def progress_callback(processed, total, stats):
        print(f"\rProcessed: {processed}/{total} files | "
              f"Copied: {stats['copied']} | "
              f"Skipped: {stats['skipped']} | "
              f"No Year: {stats['no_year']} | "
              f"Errors: {stats['errors']}", end="")

    stats = copy_by_year(SOURCE_DIR, DEST_DIR, progress_callback)
    print("\n\n✅ Done organizing by year!")
    print(f"Total files processed: {stats['total']}")
    print(f"Files copied: {stats['copied']}")
    print(f"Files skipped: {stats['skipped']}")
    print(f"Files with no year: {stats['no_year']}")
    print(f"Errors: {stats['errors']}")
    print("\nFiles by year:")
    for year, count in sorted(stats['years'].items()):
        print(f"{year}: {count} files")
