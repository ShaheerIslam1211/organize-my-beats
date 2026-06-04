"""Core music organization engine shared by GUI and CLI."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Iterator, Optional

from mutagen import File as MutagenFile

AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".ogg", ".wav", ".wma", ".aac"}

INVALID_CHARS = re.compile(r'[\\/:*?"<>|]')
WHITESPACE = re.compile(r"\s+")


class OrganizeMode(str, Enum):
    YEAR = "year"
    ARTIST = "artist"
    ALBUM = "album"
    GENRE = "genre"
    ARTIST_ALBUM = "artist_album"
    DECADE = "decade"


class NamingTemplate(str, Enum):
    ORIGINAL = "original"
    ARTIST_TITLE = "artist_title"
    TRACK_ARTIST_TITLE = "track_artist_title"
    YEAR_ARTIST_TITLE = "year_artist_title"


class OperationMode(str, Enum):
    COPY = "copy"
    MOVE = "move"


class DuplicateMode(str, Enum):
    SKIP = "skip"
    OVERWRITE = "overwrite"
    RENAME = "rename"


@dataclass
class TrackMetadata:
    path: Path
    title: str = "Unknown Title"
    artist: str = "Unknown Artist"
    album: str = "Unknown Album"
    year: Optional[str] = None
    genre: str = "Unknown Genre"
    track: Optional[int] = None
    duration: Optional[float] = None
    format: str = ""

    @property
    def decade(self) -> Optional[str]:
        if not self.year or not self.year.isdigit():
            return None
        decade = (int(self.year) // 10) * 10
        return f"{decade}s"

    @property
    def has_year(self) -> bool:
        return self.year is not None


@dataclass
class OrganizeOptions:
    mode: OrganizeMode = OrganizeMode.YEAR
    naming: NamingTemplate = NamingTemplate.ORIGINAL
    operation: OperationMode = OperationMode.COPY
    duplicate: DuplicateMode = DuplicateMode.SKIP
    unknown_year_folder: bool = True
    dry_run: bool = False
    include_subfolders: bool = True
    generate_report: bool = True


@dataclass
class OrganizeStats:
    total: int = 0
    copied: int = 0
    moved: int = 0
    skipped: int = 0
    no_metadata: int = 0
    errors: int = 0
    years: dict[str, int] = field(default_factory=dict)
    artists: dict[str, int] = field(default_factory=dict)
    genres: dict[str, int] = field(default_factory=dict)
    formats: dict[str, int] = field(default_factory=dict)
    tracks: list[TrackMetadata] = field(default_factory=list)
    log_lines: list[str] = field(default_factory=list)

    def bucket_for(self, mode: OrganizeMode) -> dict[str, int]:
        if mode == OrganizeMode.YEAR:
            return self.years
        if mode in (OrganizeMode.ARTIST, OrganizeMode.ARTIST_ALBUM):
            return self.artists
        if mode == OrganizeMode.GENRE:
            return self.genres
        return self.years


def sanitize_name(value: str, fallback: str = "Unknown") -> str:
    cleaned = WHITESPACE.sub(" ", str(value or "").strip())
    cleaned = INVALID_CHARS.sub("-", cleaned)
    cleaned = cleaned.strip(". ")
    return (cleaned[:180] or fallback)


def _parse_year(value: object) -> Optional[str]:
    if value is None:
        return None
    text = str(value[0] if isinstance(value, list) else value)
    match = re.search(r"(19|20)\d{2}", text)
    if not match:
        return None
    year = int(match.group())
    current_year = datetime.now().year
    if 1900 <= year <= current_year + 1:
        return str(year)
    return None


def _parse_track(value: object) -> Optional[int]:
    if value is None:
        return None
    text = str(value[0] if isinstance(value, list) else value)
    match = re.match(r"(\d+)", text)
    return int(match.group(1)) if match else None


def _first_tag(audio, *keys: str) -> Optional[str]:
    for key in keys:
        if key in audio and audio[key]:
            value = audio[key]
            if isinstance(value, list):
                value = value[0]
            text = str(value).strip()
            if text:
                return text
    return None


def read_metadata(filepath: Path) -> TrackMetadata:
    """Read common audio metadata from a file."""
    meta = TrackMetadata(
        path=filepath,
        format=filepath.suffix.lower().lstrip(".") or "unknown",
    )

    try:
        audio = MutagenFile(filepath, easy=True)
        if audio is not None:
            meta.title = sanitize_name(
                _first_tag(audio, "title", "TIT2") or filepath.stem, "Unknown Title"
            )
            meta.artist = sanitize_name(
                _first_tag(audio, "artist", "albumartist", "TPE1", "TPE2"),
                "Unknown Artist",
            )
            meta.album = sanitize_name(
                _first_tag(audio, "album", "TALB") or "Unknown Album", "Unknown Album"
            )
            meta.genre = sanitize_name(
                _first_tag(audio, "genre", "TCON") or "Unknown Genre", "Unknown Genre"
            )
            meta.year = _parse_year(_first_tag(audio, "date", "year", "originaldate"))
            meta.track = _parse_track(_first_tag(audio, "tracknumber", "TRCK"))

        full = MutagenFile(filepath)
        if full is not None and hasattr(full, "info") and full.info:
            meta.duration = getattr(full.info, "length", None)

        if meta.title == "Unknown Title" and filepath.stem:
            meta.title = sanitize_name(filepath.stem, "Unknown Title")
    except Exception:
        pass

    return meta


def iter_audio_files(source_dir: Path, include_subfolders: bool = True) -> Iterator[Path]:
    """Yield audio files from a directory."""
    pattern = "**/*" if include_subfolders else "*"
    for item in sorted(source_dir.glob(pattern)):
        if item.is_file() and item.suffix.lower() in AUDIO_EXTENSIONS:
            yield item


def build_filename(meta: TrackMetadata, template: NamingTemplate) -> str:
    ext = meta.path.suffix
    if template == NamingTemplate.ORIGINAL:
        return meta.path.name

    if template == NamingTemplate.ARTIST_TITLE:
        return f"{meta.artist} - {meta.title}{ext}"

    if template == NamingTemplate.TRACK_ARTIST_TITLE:
        track = f"{meta.track:02d} - " if meta.track is not None else ""
        return f"{track}{meta.artist} - {meta.title}{ext}"

    year = meta.year or "Unknown Year"
    return f"{year} - {meta.artist} - {meta.title}{ext}"


def build_destination_path(
    meta: TrackMetadata, dest_dir: Path, options: OrganizeOptions
) -> Optional[Path]:
    """Build the destination path for a track based on organize mode."""
    filename = build_filename(meta, options.naming)

    if options.mode == OrganizeMode.YEAR:
        if not meta.year:
            if options.unknown_year_folder:
                return dest_dir / "Unknown Year" / filename
            return None
        return dest_dir / meta.year / filename

    if options.mode == OrganizeMode.DECADE:
        bucket = meta.decade or ("Unknown Decade" if options.unknown_year_folder else None)
        if not bucket:
            return None
        return dest_dir / bucket / filename

    if options.mode == OrganizeMode.ARTIST:
        return dest_dir / meta.artist / filename

    if options.mode == OrganizeMode.ALBUM:
        return dest_dir / meta.album / filename

    if options.mode == OrganizeMode.GENRE:
        return dest_dir / meta.genre / filename

    if options.mode == OrganizeMode.ARTIST_ALBUM:
        return dest_dir / meta.artist / meta.album / filename

    return dest_dir / (meta.year or "Unknown Year") / filename


def resolve_duplicate_path(dest_file: Path, mode: DuplicateMode) -> tuple[Path, bool]:
    """Resolve destination when a file already exists."""
    if not dest_file.exists():
        return dest_file, True

    if mode == DuplicateMode.OVERWRITE:
        return dest_file, True

    if mode == DuplicateMode.RENAME:
        stem = dest_file.stem
        suffix = dest_file.suffix
        parent = dest_file.parent
        counter = 1
        while True:
            candidate = parent / f"{stem} ({counter}){suffix}"
            if not candidate.exists():
                return candidate, True
            counter += 1

    return dest_file, False


def transfer_file(
    source: Path, destination: Path, operation: OperationMode, dry_run: bool
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        return
    if operation == OperationMode.MOVE:
        shutil.move(str(source), str(destination))
    else:
        shutil.copy2(source, destination)


ProgressCallback = Callable[[int, int, str], None]


def scan_library(
    source_dir: Path,
    include_subfolders: bool = True,
    progress_callback: Optional[ProgressCallback] = None,
) -> list[TrackMetadata]:
    """Scan a library and return metadata for every audio file."""
    files = list(iter_audio_files(source_dir, include_subfolders))
    results: list[TrackMetadata] = []
    total = len(files)

    for index, filepath in enumerate(files, start=1):
        meta = read_metadata(filepath)
        results.append(meta)
        if progress_callback:
            progress_callback(index, total, f"Scanned {filepath.name}")

    return results


def organize_library(
    source_dir: Path,
    dest_dir: Path,
    options: OrganizeOptions,
    progress_callback: Optional[ProgressCallback] = None,
    should_stop: Optional[Callable[[], bool]] = None,
) -> OrganizeStats:
    """Organize audio files according to the selected options."""
    stats = OrganizeStats()
    files = list(iter_audio_files(source_dir, options.include_subfolders))
    total = len(files)

    for index, filepath in enumerate(files, start=1):
        if should_stop and should_stop():
            break

        stats.total += 1
        try:
            meta = read_metadata(filepath)
            stats.tracks.append(meta)
            stats.formats[meta.format] = stats.formats.get(meta.format, 0) + 1

            if meta.year:
                stats.years[meta.year] = stats.years.get(meta.year, 0) + 1
            stats.artists[meta.artist] = stats.artists.get(meta.artist, 0) + 1
            stats.genres[meta.genre] = stats.genres.get(meta.genre, 0) + 1

            dest_file = build_destination_path(meta, dest_dir, options)
            if dest_file is None:
                stats.no_metadata += 1
                message = f"No metadata bucket for: {filepath.name}"
                stats.log_lines.append(message)
                if progress_callback:
                    progress_callback(index, total, message)
                continue

            dest_file, proceed = resolve_duplicate_path(dest_file, options.duplicate)
            if not proceed:
                stats.skipped += 1
                message = f"Skipped duplicate: {filepath.name}"
                stats.log_lines.append(message)
                if progress_callback:
                    progress_callback(index, total, message)
                continue

            transfer_file(filepath, dest_file, options.operation, options.dry_run)

            if options.dry_run:
                verb = "Would copy" if options.operation == OperationMode.COPY else "Would move"
            elif options.operation == OperationMode.MOVE:
                verb = "Moved"
                stats.moved += 1
            else:
                verb = "Copied"
                stats.copied += 1

            relative = dest_file.relative_to(dest_dir)
            message = f"{verb} -> {relative}"
            stats.log_lines.append(message)
            if progress_callback:
                progress_callback(index, total, message)

        except Exception as exc:
            stats.errors += 1
            message = f"Error processing {filepath.name}: {exc}"
            stats.log_lines.append(message)
            if progress_callback:
                progress_callback(index, total, message)

    return stats


def format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "--:--"
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
