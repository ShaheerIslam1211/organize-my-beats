# Organize My Beats

A smart music organizer that scans your library, reads release years from metadata, and copies tracks into neatly sorted folders by year — perfect for curating your collection or importing into Apple Music.

## Features

-   **Metadata Scanning**: Automatically extracts release year information from audio file metadata
-   **Smart Organization**: Creates year-based folders and copies files to their appropriate locations
-   **Multiple Interfaces**:
    -   Advanced GUI with PyQt5 (modern, feature-rich interface)
    -   Basic GUI with Tkinter (lightweight alternative)
    -   Command-line interface for automation and scripting
-   **Detailed Statistics**: View breakdown of songs by year
-   **Preserves Originals**: Only copies files, never modifies or moves your original collection
-   **Handles Missing Metadata**: Option to place files with no year information in a separate folder

## Installation

### From PyPI (Recommended)

```bash
pip install organize-my-beats
```

### From Source

```bash
git clone https://github.com/ShaheerIslam1211/organize_my_beats.git
cd organize_my_beats
pip install -e .
```

## Usage

### Advanced GUI (Recommended)

The advanced GUI provides a modern interface with more features:

```bash
organize-my-beats-gui
```

Or run as a module:

```bash
python -m organize_my_beats
```

### Basic GUI

For a simpler interface:

```bash
python -m organize_my_beats --gui
```

### Command Line

For automation or batch processing:

```bash
organize-my-beats --cli source_directory destination_directory [options]
```

Or:

```bash
python -m organize_my_beats --cli source_directory destination_directory [options]
```

Command-line options:

```
-o, --overwrite       Overwrite existing files in destination
-u, --unknown-year    Create 'Unknown Year' folder for files without year metadata
-v, --verbose         Show detailed progress information
-s, --stats           Show statistics after completion
```

## Example

```bash
organize-my-beats --cli ~/Music ~/Organized_Music --unknown-year --stats
```

This will scan all audio files in your Music folder, extract year information from metadata, and copy them to year-based folders in the Organized_Music directory. Files without year metadata will be placed in an "Unknown Year" folder, and statistics will be displayed after completion.

## Supported File Formats

-   MP3 (.mp3)
-   FLAC (.flac)
-   AAC (.m4a)
-   Ogg Vorbis (.ogg)
-   WAV (.wav)
-   WMA (.wma)
-   AAC (.aac)

## License

MIT License
