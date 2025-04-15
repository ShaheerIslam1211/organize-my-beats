"""Music file organization module with year-based categorization"""

import os
import shutil
import datetime
from pathlib import Path
import mutagen
from mutagen.id3 import ID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
import eyed3
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Audio file extensions
AUDIO_EXTENSIONS = ['.mp3', '.flac', '.m4a', '.ogg', '.wav', '.wma', '.aac', '.mp4']

class MusicOrganizer:
    """
    Organizes music files based on various metadata criteria
    with special focus on year-based organization
    """

    def __init__(self, source_dir=None, target_dir=None):
        """Initialize organizer with source and target directories"""
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.stats = {
            "processed_files": 0,
            "organized_files": 0,
            "failed_files": 0,
            "years": {},
            "artists": {},
            "genres": {},
            "errors": []
        }
        self.current_files = []
        self.total_files = 0
        self.abort_requested = False

    def set_source_dir(self, path):
        """Set source directory containing music files"""
        if os.path.exists(path) and os.path.isdir(path):
            self.source_dir = path
            return True
        logger.error(f"Source directory does not exist: {path}")
        return False

    def set_target_dir(self, path):
        """Set target directory for organized files"""
        try:
            path = os.path.abspath(path)
            # Create directory if it doesn't exist
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            self.target_dir = path
            return True
        except Exception as e:
            logger.error(f"Could not set target directory: {e}")
            return False

    def scan_source_directory(self):
        """Scan source directory for audio files"""
        if not self.source_dir:
            return []

        audio_files = []
        for root, _, files in os.walk(self.source_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in AUDIO_EXTENSIONS):
                    file_path = os.path.join(root, file)
                    audio_files.append(file_path)

        self.current_files = audio_files
        self.total_files = len(audio_files)
        return audio_files

    def extract_year(self, file_path):
        """
        Extract year from audio file metadata
        Tries multiple tag fields and formats to find a valid year
        """
        try:
            file_ext = os.path.splitext(file_path)[1].lower()

            if file_ext == '.mp3':
                return self._extract_year_mp3(file_path)
            elif file_ext == '.flac':
                return self._extract_year_flac(file_path)
            elif file_ext in ['.m4a', '.mp4']:
                return self._extract_year_m4a(file_path)
            else:
                # Generic mutagen approach for other formats
                try:
                    audio = mutagen.File(file_path)
                    if audio:
                        # Try common date/year tags
                        for tag in ['date', 'year', 'TDRC', 'TYER', 'TDRL', 'TDOR']:
                            if tag in audio:
                                return self._parse_year_from_string(str(audio[tag][0]))
                except Exception as e:
                    logger.debug(f"Could not extract year from generic file: {e}")

            # Fall back to filename-based extraction
            return self._extract_year_from_filename(file_path)

        except Exception as e:
            logger.debug(f"Year extraction failed for {os.path.basename(file_path)}: {e}")
            return None

    def _extract_year_mp3(self, file_path):
        """Extract year from MP3 file using multiple methods"""
        # Try eyed3 first (specialized for MP3)
        try:
            audio = eyed3.load(file_path)
            if audio and audio.tag:
                # Try release date first
                if audio.tag.release_date:
                    year_str = str(audio.tag.release_date)
                    return self._parse_year_from_string(year_str)

                # Try recording date
                if audio.tag.recording_date:
                    year_str = str(audio.tag.recording_date)
                    return self._parse_year_from_string(year_str)

                # Try original release date
                if audio.tag.original_release_date:
                    year_str = str(audio.tag.original_release_date)
                    return self._parse_year_from_string(year_str)
        except Exception:
            pass  # Fall through to ID3

        # Try ID3 tags
        try:
            audio = ID3(file_path)
            # Try different ID3 date/year tags
            for frame in ['TDRC', 'TYER', 'TDRL', 'TDOR']:
                if frame in audio:
                    year_str = str(audio[frame])
                    return self._parse_year_from_string(year_str)
        except Exception:
            pass

        # If all else fails, try filename
        return self._extract_year_from_filename(file_path)

    def _extract_year_flac(self, file_path):
        """Extract year from FLAC file"""
        try:
            flac = FLAC(file_path)
            # Check DATE tag
            if 'date' in flac:
                return self._parse_year_from_string(flac['date'][0])

            # Try YEAR tag
            if 'year' in flac:
                return self._parse_year_from_string(flac['year'][0])

            # Try COPYRIGHT tag that may contain year
            if 'copyright' in flac:
                copyright_text = flac['copyright'][0]
                return self._extract_year_from_copyright(copyright_text)
        except Exception:
            pass

        return self._extract_year_from_filename(file_path)

    def _extract_year_m4a(self, file_path):
        """Extract year from M4A/MP4 file"""
        try:
            mp4 = MP4(file_path)
            # Try different date tags
            if '©day' in mp4:
                return self._parse_year_from_string(mp4['©day'][0])
            if 'yyyy' in mp4:
                return int(mp4['yyyy'][0])
            if 'dcfd' in mp: # Release Date
                return self._parse_year_from_string(mp4['dcfd'][0])
            if 'cprt' in mp4: # Copyright
                return self._extract_year_from_copyright(mp4['cprt'][0])
        except Exception:
            pass

        return self._extract_year_from_filename(file_path)

    def _parse_year_from_string(self, date_str):
        """Extract year from a date string in various formats"""
        if not date_str:
            return None

        # First try direct conversion (if it's just a year)
        try:
            year = int(date_str.strip())
            if 1900 <= year <= datetime.datetime.now().year:
                return year
        except ValueError:
            pass

        # Try to extract using regular expressions for common date formats
        # YYYY-MM-DD
        match = re.search(r'(\d{4})[/-]', date_str)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= datetime.datetime.now().year:
                return year

        # Just find any 4-digit number that looks like a year
        match = re.search(r'(\d{4})', date_str)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= datetime.datetime.now().year:
                return year

        return None

    def _extract_year_from_copyright(self, copyright_text):
        """Extract year from copyright notice, e.g., '℗ 2020 Label'"""
        if not copyright_text:
            return None

        # Look for year in copyright notice
        match = re.search(r'[©℗]\s*(\d{4})', copyright_text)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= datetime.datetime.now().year:
                return year

        # Try just finding any year
        match = re.search(r'(\d{4})', copyright_text)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= datetime.datetime.now().year:
                return year

        return None

    def _extract_year_from_filename(self, file_path):
        """Try to extract year from the filename or directory structure"""
        # Get filename and directory
        filename = os.path.basename(file_path)
        directory = os.path.dirname(file_path)

        # Try finding year in filename
        match = re.search(r'(\d{4})', filename)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= datetime.datetime.now().year:
                return year

        # Try finding year in directory path (for already organized collections)
        match = re.search(r'(\d{4})', directory)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= datetime.datetime.now().year:
                return year

        return None

    def get_target_path(self, file_path, year=None):
        """
        Determine target path based on organization strategy
        """
        if not year:
            year = self.extract_year(file_path)

        # If year couldn't be determined, use "Unknown"
        year_str = str(year) if year else "Unknown Year"

        # Create target directory structure: target/YEAR/
        target_dir = os.path.join(self.target_dir, year_str)

        # Ensure target directory exists
        os.makedirs(target_dir, exist_ok=True)

        # Determine target filename
        filename = os.path.basename(file_path)
        return os.path.join(target_dir, filename)

    def organize_file(self, file_path):
        """
        Organize a single file based on its metadata
        Returns a dictionary with year and target path
        """
        if not self.target_dir:
            logger.error("Target directory not set")
            return None

        try:
            # Extract year
            year = self.extract_year(file_path)

            # Get target path
            target_path = self.get_target_path(file_path, year)

            # Create result
            result = {
                "source": file_path,
                "target": target_path,
                "year": year,
                "filename": os.path.basename(file_path),
                "success": False
            }

            # Copy file if target doesn't exist or source is newer
            if not os.path.exists(target_path) or os.path.getmtime(file_path) > os.path.getmtime(target_path):
                # Ensure target directory exists
                os.makedirs(os.path.dirname(target_path), exist_ok=True)

                # Copy the file
                shutil.copy2(file_path, target_path)
                result["success"] = True

                # Update statistics
                if year:
                    self.stats["years"][str(year)] = self.stats["years"].get(str(year), 0) + 1

                self.stats["organized_files"] += 1
            else:
                logger.info(f"Skipping {os.path.basename(file_path)} - already exists")

            self.stats["processed_files"] += 1
            return result

        except Exception as e:
            logger.error(f"Error organizing {os.path.basename(file_path)}: {e}")
            self.stats["failed_files"] += 1
            self.stats["errors"].append(f"{os.path.basename(file_path)}: {str(e)}")
            return {
                "source": file_path,
                "target": None,
                "year": None,
                "filename": os.path.basename(file_path),
                "success": False,
                "error": str(e)
            }

    def organize_by_year(self, callback=None, progress_callback=None):
        """
        Organize all files in source directory by year
        With optional callbacks for completion and progress updates
        """
        # Reset stats
        self.stats = {
            "processed_files": 0,
            "organized_files": 0,
            "failed_files": 0,
            "years": {},
            "artists": {},
            "genres": {},
            "errors": []
        }

        # Scan for files if needed
        if not self.current_files:
            self.scan_source_directory()

        results = []

        # Process each file
        for i, file_path in enumerate(self.current_files):
            # Check if abort was requested
            if self.abort_requested:
                logger.info("Organization aborted by user")
                break

            result = self.organize_file(file_path)
            results.append(result)

            # Call progress callback if provided
            if progress_callback:
                progress = (i + 1) / self.total_files
                progress_callback(progress, i + 1, self.total_files, result)

        # Call completion callback if provided
        if callback:
            callback(results, self.stats)

        return results, self.stats

    def abort(self):
        """Abort the organization process"""
        self.abort_requested = True

# Utility function to get information about a music file
def get_file_info(file_path):
    """
    Extract comprehensive metadata from an audio file
    Returns a dictionary with file information
    """
    if not os.path.exists(file_path):
        return {"error": "File not found"}

    file_ext = os.path.splitext(file_path)[1].lower()

    info = {
        "path": file_path,
        "filename": os.path.basename(file_path),
        "extension": file_ext,
        "size": os.path.getsize(file_path),
        "modified": datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S'),
    }

    # Extract basic metadata using appropriate library
    try:
        if file_ext == '.mp3':
            audiofile = eyed3.load(file_path)
            if audiofile and audiofile.tag:
                info["title"] = audiofile.tag.title
                info["artist"] = audiofile.tag.artist
                info["album"] = audiofile.tag.album
                info["genre"] = str(audiofile.tag.genre) if audiofile.tag.genre else None
                info["year"] = audiofile.tag.release_date.year if audiofile.tag.release_date else None
                info["track"] = audiofile.tag.track_num[0] if audiofile.tag.track_num else None
                if audiofile.info:
                    info["duration"] = audiofile.info.time_secs
                    info["bitrate"] = audiofile.info.bit_rate[1]
        else:
            # Generic mutagen approach for other formats
            audio = mutagen.File(file_path)
            if audio:
                info["duration"] = audio.info.length if hasattr(audio.info, 'length') else None
                info["bitrate"] = audio.info.bitrate if hasattr(audio.info, 'bitrate') else None

                # Handle common tags across formats
                if hasattr(audio, 'tags'):
                    tags = audio.tags
                    for tag, key in [
                        (['title', '©nam'], "title"),
                        (['artist', '©ART', 'TPE1'], "artist"),
                        (['album', '©alb', 'TALB'], "album"),
                        (['genre', '©gen', 'TCON'], "genre"),
                    ]:
                        for t in tag:
                            if t in tags:
                                info[key] = str(tags[t][0])
                                break

                # Extract year using our specialized function
                organizer = MusicOrganizer()
                info["year"] = organizer.extract_year(file_path)
    except Exception as e:
        info["error"] = str(e)

    return info

# Function to organize a directory by year
def organize_directory_by_year(source_dir, target_dir, progress_callback=None, completion_callback=None):
    """
    Organize a directory of music files by year

    Args:
        source_dir: Source directory containing music files
        target_dir: Target directory for organized files
        progress_callback: Optional callback function for progress updates
        completion_callback: Optional callback function when complete

    Returns:
        Tuple of (results, stats)
    """
    organizer = MusicOrganizer(source_dir, target_dir)
    organizer.scan_source_directory()
    return organizer.organize_by_year(completion_callback, progress_callback)
