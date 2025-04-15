"""Advanced Music Player with Album View, Lyrics and Playback Controls"""

import os
import threading
import time
from typing import Dict, List, Optional, Tuple
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import mutagen
from mutagen.id3 import ID3
import pygame
from io import BytesIO
import requests
import json
import re

class AdvancedMusicPlayer(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        # Initialize pygame mixer for audio playback
        pygame.mixer.init()

        # Track the current playing song and its state
        self.current_track = None
        self.paused = True
        self.current_position = 0
        self.track_length = 0
        self.update_id = None

        # Album and artist view state
        self.current_album = None
        self.current_artist = None
        self.current_playlist = []
        self.current_index = 0

        # Create UI elements
        self.create_ui()

        # Start the progress bar update thread
        self._update_thread_running = True
        self._update_thread = threading.Thread(target=self._progress_updater, daemon=True)
        self._update_thread.start()

    def create_ui(self):
        """Create the music player UI with album art, controls, and lyrics"""
        # Main container with two columns
        self.columnconfigure(0, weight=3)  # Left panel
        self.columnconfigure(1, weight=7)  # Right panel

        # === LEFT PANEL - Album Browser ===
        left_panel = ctk.CTkFrame(self, corner_radius=0)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        left_panel.grid_rowconfigure(2, weight=1)  # Albums list should expand

        # Header - Year/Genre filter and search
        filter_frame = ctk.CTkFrame(left_panel, fg_color=("gray90", "gray20"))
        filter_frame.pack(fill="x", padx=10, pady=10)

        # Year and Genre filters
        years = ["All Years", "2024", "2023", "2022", "2021", "2020", "2010s", "2000s", "1990s", "1980s"]
        genres = ["All Genres", "Pop", "Rock", "Hip-Hop", "Jazz", "Electronic", "Classical"]

        filter_label = ctk.CTkLabel(filter_frame, text="Filter:", font=ctk.CTkFont(size=12, weight="bold"))
        filter_label.pack(anchor="w", padx=5, pady=5)

        year_dropdown = ctk.CTkOptionMenu(filter_frame, values=years, width=120)
        year_dropdown.pack(anchor="w", padx=5, pady=2)

        genre_dropdown = ctk.CTkOptionMenu(filter_frame, values=genres, width=120)
        genre_dropdown.pack(anchor="w", padx=5, pady=2)

        # Search box for albums
        search_frame = ctk.CTkFrame(left_panel, fg_color=("gray90", "gray20"))
        search_frame.pack(fill="x", padx=10, pady=(0, 10))

        search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search albums...", height=35)
        search_entry.pack(fill="x", padx=10, pady=10)

        # Albums Section Title
        ctk.CTkLabel(
            left_panel,
            text="ALBUMS",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(fill="x", padx=15, pady=5)

        # Albums scroll view
        albums_scroll = ctk.CTkScrollableFrame(left_panel)
        albums_scroll.pack(fill="both", expand=True, padx=10, pady=5)

        # Sample Albums
        sample_albums = [
            {"title": "Thriller", "artist": "Michael Jackson", "year": "1982", "cover": "🎵"},
            {"title": "Back in Black", "artist": "AC/DC", "year": "1980", "cover": "🎸"},
            {"title": "The Dark Side of the Moon", "artist": "Pink Floyd", "year": "1973", "cover": "🌑"},
            {"title": "Abbey Road", "artist": "The Beatles", "year": "1969", "cover": "🚶‍♂️"},
            {"title": "Rumours", "artist": "Fleetwood Mac", "year": "1977", "cover": "👥"},
            {"title": "Born to Run", "artist": "Bruce Springsteen", "year": "1975", "cover": "🏃"},
            {"title": "Purple Rain", "artist": "Prince", "year": "1984", "cover": "☔"},
            {"title": "OK Computer", "artist": "Radiohead", "year": "1997", "cover": "💻"},
        ]

        for album in sample_albums:
            self.create_album_item(albums_scroll, album)

        # === RIGHT PANEL - Player with Lyrics ===
        right_panel = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray95", "gray16"))
        right_panel.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

        # Currently playing view
        now_playing_frame = ctk.CTkFrame(right_panel, fg_color=("gray90", "gray18"))
        now_playing_frame.pack(fill="x", padx=20, pady=20)

        # Currently playing header
        header_frame = ctk.CTkFrame(now_playing_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 0))

        ctk.CTkLabel(
            header_frame,
            text="NOW PLAYING",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#3D7EFF", "#5E88FF")
        ).pack(side="left")

        # Track info and controls
        content_frame = ctk.CTkFrame(now_playing_frame, fg_color="transparent")
        content_frame.pack(fill="x", padx=20, pady=20)
        content_frame.columnconfigure(0, weight=1)  # Album art and track info
        content_frame.columnconfigure(1, weight=1)  # Lyrics

        # Album Art and Track Info (left side)
        track_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        track_frame.grid(row=0, column=0, sticky="nsew", padx=10)

        # Album placeholder (a large square with icon)
        self.album_art_frame = ctk.CTkFrame(track_frame, width=250, height=250, fg_color=("#3D7EFF", "#0A51BB"))
        self.album_art_frame.pack(pady=20)
        self.album_art_frame.pack_propagate(False)

        album_icon = ctk.CTkLabel(
            self.album_art_frame,
            text="🎵",
            font=ctk.CTkFont(size=80)
        )
        album_icon.place(relx=0.5, rely=0.5, anchor="center")

        # Track info
        track_info_frame = ctk.CTkFrame(track_frame, fg_color="transparent")
        track_info_frame.pack(fill="x", pady=10)

        self.track_title_label = ctk.CTkLabel(
            track_info_frame,
            text="Select a track to play",
            font=ctk.CTkFont(size=20, weight="bold"),
            wraplength=250
        )
        self.track_title_label.pack(fill="x")

        self.artist_label = ctk.CTkLabel(
            track_info_frame,
            text="",
            font=ctk.CTkFont(size=16),
            text_color=("gray40", "gray60")
        )
        self.artist_label.pack(fill="x")

        self.album_label = ctk.CTkLabel(
            track_info_frame,
            text="",
            font=ctk.CTkFont(size=14),
            text_color=("gray50", "gray70")
        )
        self.album_label.pack(fill="x")

        # Player controls
        controls_frame = ctk.CTkFrame(track_frame, fg_color="transparent")
        controls_frame.pack(fill="x", pady=15)

        # Progress bar and time
        progress_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        progress_frame.pack(fill="x", padx=10, pady=5)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            variable=self.progress_var,
            height=8
        )
        self.progress_bar.pack(fill="x", padx=5, pady=5)

        time_frame = ctk.CTkFrame(progress_frame, fg_color="transparent")
        time_frame.pack(fill="x")

        self.current_time_label = ctk.CTkLabel(
            time_frame,
            text="0:00",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60")
        )
        self.current_time_label.pack(side="left")

        self.total_time_label = ctk.CTkLabel(
            time_frame,
            text="0:00",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60")
        )
        self.total_time_label.pack(side="right")

        # Playback control buttons
        buttons_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        buttons_frame.pack(pady=10)

        prev_button = ctk.CTkButton(
            buttons_frame,
            text="⏮️",
            width=60,
            command=self.prev_track,
            fg_color=("gray80", "gray30")
        )
        prev_button.pack(side="left", padx=5)

        self.play_button = ctk.CTkButton(
            buttons_frame,
            text="▶️",
            width=60,
            command=self.toggle_play,
            fg_color=("#3D7EFF", "#0A51BB")
        )
        self.play_button.pack(side="left", padx=5)

        next_button = ctk.CTkButton(
            buttons_frame,
            text="⏭️",
            width=60,
            command=self.next_track,
            fg_color=("gray80", "gray30")
        )
        next_button.pack(side="left", padx=5)

        # Volume control
        volume_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        volume_frame.pack(fill="x", pady=5)

        volume_icon = ctk.CTkLabel(
            volume_frame,
            text="🔊",
            font=ctk.CTkFont(size=14)
        )
        volume_icon.pack(side="left", padx=(0, 5))

        self.volume_var = tk.DoubleVar(value=0.7)
        volume_slider = ctk.CTkSlider(
            volume_frame,
            from_=0,
            to=1,
            variable=self.volume_var,
            command=self.set_volume
        )
        volume_slider.pack(side="left", fill="x", expand=True)

        # Lyrics Section (right side)
        lyrics_frame = ctk.CTkFrame(content_frame, fg_color=("gray85", "gray22"))
        lyrics_frame.grid(row=0, column=1, sticky="nsew", padx=10)

        ctk.CTkLabel(
            lyrics_frame,
            text="LYRICS",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(15, 10))

        self.lyrics_text = ctk.CTkTextbox(
            lyrics_frame,
            wrap="word",
            width=300,
            height=350,
            font=ctk.CTkFont(size=13)
        )
        self.lyrics_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Bottom section - Album tracks
        album_tracks_frame = ctk.CTkFrame(right_panel, fg_color=("gray90", "gray18"))
        album_tracks_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        ctk.CTkLabel(
            album_tracks_frame,
            text="ALBUM TRACKS",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=20, pady=15)

        self.tracks_list = ctk.CTkScrollableFrame(album_tracks_frame)
        self.tracks_list.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Sample tracks
        sample_tracks = [
            {"title": "Track 1", "duration": "3:45", "artist": "Artist Name"},
            {"title": "Track 2", "duration": "4:12", "artist": "Artist Name"},
            {"title": "Track 3", "duration": "3:33", "artist": "Artist Name"},
            {"title": "Track 4", "duration": "2:55", "artist": "Artist Name"},
            {"title": "Track 5", "duration": "4:18", "artist": "Artist Name"}
        ]

        for i, track in enumerate(sample_tracks):
            self.create_track_item(i, track)

    def create_album_item(self, parent, album):
        """Create album item in the albums list"""
        album_frame = ctk.CTkFrame(parent, fg_color=("gray85", "gray22"), corner_radius=10, height=70)
        album_frame.pack(fill="x", padx=5, pady=5)
        album_frame.pack_propagate(False)

        # Album cover
        cover_label = ctk.CTkLabel(
            album_frame,
            text=album["cover"],
            font=ctk.CTkFont(size=24),
            width=50,
            height=50
        )
        cover_label.pack(side="left", padx=10)

        # Album info
        info_frame = ctk.CTkFrame(album_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=5)

        ctk.CTkLabel(
            info_frame,
            text=album["title"],
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(10, 0))

        ctk.CTkLabel(
            info_frame,
            text=f"{album['artist']} • {album['year']}",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
            anchor="w"
        ).pack(fill="x")

        # Make clickable
        album_frame.bind("<Button-1>", lambda e, a=album: self.show_album(a))
        cover_label.bind("<Button-1>", lambda e, a=album: self.show_album(a))
        info_frame.bind("<Button-1>", lambda e, a=album: self.show_album(a))

    def create_track_item(self, index, track):
        """Create track item in the tracks list"""
        track_frame = ctk.CTkFrame(self.tracks_list, fg_color="transparent")
        track_frame.pack(fill="x", pady=2)

        # Track number
        number_label = ctk.CTkLabel(
            track_frame,
            text=f"{index + 1}",
            width=30,
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60")
        )
        number_label.pack(side="left", padx=(5, 10))

        # Track title and artist
        info_frame = ctk.CTkFrame(track_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True)

        title_label = ctk.CTkLabel(
            info_frame,
            text=track["title"],
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        )
        title_label.pack(fill="x")

        artist_label = ctk.CTkLabel(
            info_frame,
            text=track["artist"],
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
            anchor="w"
        )
        artist_label.pack(fill="x")

        # Duration
        duration_label = ctk.CTkLabel(
            track_frame,
            text=track["duration"],
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60")
        )
        duration_label.pack(side="right", padx=10)

        # Add hover effect and click handler
        for widget in [track_frame, title_label, artist_label, number_label, duration_label]:
            widget.bind("<Enter>", lambda e, f=track_frame: self.on_track_hover(f, True))
            widget.bind("<Leave>", lambda e, f=track_frame: self.on_track_hover(f, False))
            widget.bind("<Button-1>", lambda e, t=track: self.play_track(t))

    def on_track_hover(self, frame, is_hover):
        """Handle track item hover effect"""
        if is_hover:
            frame.configure(fg_color=("gray80", "gray25"))
        else:
            frame.configure(fg_color="transparent")

    def show_album(self, album):
        """Display album details and tracks"""
        self.current_album = album

        # Update album label
        self.album_label.configure(text=f"{album['title']} ({album['year']})")

        # Clear existing tracks
        for widget in self.tracks_list.winfo_children():
            widget.destroy()

        # Sample tracks for the album
        sample_tracks = [
            {"title": f"Track 1 - {album['title']}", "duration": "3:45", "artist": album["artist"]},
            {"title": f"Track 2 - {album['title']}", "duration": "4:12", "artist": album["artist"]},
            {"title": f"Track 3 - {album['title']}", "duration": "3:33", "artist": album["artist"]},
            {"title": f"Track 4 - {album['title']}", "duration": "2:55", "artist": album["artist"]},
            {"title": f"Track 5 - {album['title']}", "duration": "4:18", "artist": album["artist"]}
        ]

        # Create playlist from these tracks
        self.current_playlist = sample_tracks

        # Create track items
        for i, track in enumerate(sample_tracks):
            self.create_track_item(i, track)

    def play_track(self, track):
        """Play the selected track"""
        self.current_track = track

        # Update UI
        self.track_title_label.configure(text=track["title"])
        self.artist_label.configure(text=track["artist"])

        # Check if track has a file path (real track)
        if "file_path" in track and os.path.exists(track["file_path"]):
            # Play the actual file using pygame
            try:
                pygame.mixer.music.load(track["file_path"])
                pygame.mixer.music.play()

                # Update button to show pause icon
                self.play_button.configure(text="⏸️")
                self.paused = False

                # Reset position and get actual track length
                self.current_position = 0

                # Get actual duration from file
                import mutagen
                audio = mutagen.File(track["file_path"])
                if audio and hasattr(audio.info, 'length'):
                    self.track_length = audio.info.length
                else:
                    # Use approximate duration from track info
                    duration = track.get("duration", "0:00")
                    mins, secs = map(int, duration.split(':'))
                    self.track_length = mins * 60 + secs

                self.total_time_label.configure(text=self.format_time(self.track_length))

                # Show lyrics
                self.show_lyrics()
                return
            except Exception as e:
                print(f"Error playing track: {e}")

        # Fall back to dummy playback for demo tracks
        self.play_button.configure(text="⏸️")
        self.paused = False
        self.track_length = 225  # 3:45 in seconds
        self.total_time_label.configure(text=self.format_time(self.track_length))
        self.show_lyrics()

    def show_lyrics(self):
        """Display lyrics for the current track"""
        if not self.current_track:
            return

        # Clear existing lyrics
        self.lyrics_text.delete("0.0", "end")

        # In a real app, you would fetch lyrics from a service or ID3 tags
        # For now, generate dummy lyrics
        sample_lyrics = f"""
[Verse 1]
This is where the lyrics would go
For the track "{self.current_track['title']}"
By {self.current_track['artist']}
The lyrics would be displayed in sync with the music

[Chorus]
This is the chorus of the song
With the main hook that repeats
Throughout the track
And gets stuck in your head

[Verse 2]
The second verse continues the story
With more details and emotion
Building upon the themes
Established in the first verse

[Bridge]
And here the song changes direction
Before returning to the familiar chorus
With a different perspective
And deeper understanding

[Chorus]
This is the chorus of the song
With the main hook that repeats
Throughout the track
And gets stuck in your head

[Outro]
The song concludes with final thoughts
Wrapping up the musical journey
And leaving the listener
With something to remember
"""
        self.lyrics_text.insert("0.0", sample_lyrics.strip())

    def toggle_play(self):
        """Play or pause the current track"""
        if not self.current_track:
            return

        if self.paused:
            # Resume playback
            # pygame.mixer.music.unpause()
            self.play_button.configure(text="⏸️")
            self.paused = False
        else:
            # Pause playback
            # pygame.mixer.music.pause()
            self.play_button.configure(text="▶️")
            self.paused = True

    def prev_track(self):
        """Play the previous track in the playlist"""
        if not self.current_playlist:
            return

        self.current_index = max(0, self.current_index - 1)
        self.play_track(self.current_playlist[self.current_index])

    def next_track(self):
        """Play the next track in the playlist"""
        if not self.current_playlist:
            return

        self.current_index = min(len(self.current_playlist) - 1, self.current_index + 1)
        self.play_track(self.current_playlist[self.current_index])

    def set_volume(self, value):
        """Set the playback volume"""
        # pygame.mixer.music.set_volume(value)
        pass

    def format_time(self, seconds):
        """Format seconds as mm:ss"""
        minutes, seconds = divmod(int(seconds), 60)
        return f"{minutes}:{seconds:02d}"

    def _progress_updater(self):
        """Update the progress bar in a separate thread"""
        while self._update_thread_running:
            if self.current_track and not self.paused:
                if "file_path" in self.current_track and os.path.exists(self.current_track["file_path"]):
                    # Real track - get actual position
                    try:
                        if pygame.mixer.music.get_busy():
                            pos = pygame.mixer.music.get_pos() / 1000
                            self.current_position = pos
                        else:
                            # Track finished
                            self.next_track()
                    except:
                        # Fallback if pygame fails
                        self.current_position = min(self.current_position + 0.1, self.track_length)
                else:
                    # Dummy track - increment position
                    self.current_position = min(self.current_position + 0.1, self.track_length)

                # Update progress bar
                if self.track_length > 0:
                    progress = self.current_position / self.track_length
                    self.progress_var.set(progress)

                # Update time label
                self.current_time_label.configure(text=self.format_time(self.current_position))

                # Check if track ended
                if self.current_position >= self.track_length:
                    self.next_track()

            time.sleep(0.1)

    def on_close(self):
        """Clean up resources when closing"""
        self._update_thread_running = False
        if self._update_thread.is_alive():
            self._update_thread.join(1.0)
        # pygame.mixer.quit()

    def load_directory(self, directory_path):
        """Load music from a directory and populate the player"""
        if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
            return False

        # Check if this is a year directory
        is_year_dir = os.path.basename(directory_path).isdigit()

        # Find the album scrollable frame
        album_scroll = None
        left_panel = None

        # Look for left_panel (first child of self)
        for widget in self.winfo_children():
            if isinstance(widget, ctk.CTkFrame) and widget.grid_info().get('column') == 0:
                left_panel = widget
                break

        if left_panel:
            # Find scrollable frame in left_panel (albums container)
            for widget in left_panel.winfo_children():
                if isinstance(widget, ctk.CTkScrollableFrame):
                    album_scroll = widget
                    break

        if not album_scroll:
            print("Could not find album scroll view")
            return False

        # Clear current albums
        for widget in album_scroll.winfo_children():
            widget.destroy()

        # Create an album for this directory
        if is_year_dir:
            # Year directory - create one album for the year
            year = os.path.basename(directory_path)
            album = {
                "title": f"Year {year}",
                "artist": "Various Artists",
                "year": year,
                "cover": "📅",
                "directory": directory_path
            }
            self.create_album_item(album_scroll, album)

            # Show this album
            self.show_year_album(album)
        else:
            # Regular directory - scan for audio files and group by album
            audio_files = []
            for root, _, files in os.walk(directory_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in ['.mp3', '.flac', '.m4a', '.ogg', '.wav']):
                        audio_files.append(os.path.join(root, file))

            # Group by album
            albums = self._group_files_by_album(audio_files)

            # Create album items
            for album in albums:
                self.create_album_item(album_scroll, album)

            # Show first album if any
            if albums:
                self.show_album(albums[0])

        return True

    def _group_files_by_album(self, audio_files):
        """Group audio files by album"""
        albums = {}

        for file_path in audio_files:
            try:
                # Extract metadata
                import mutagen
                audio = mutagen.File(file_path, easy=True)

                if audio:
                    # Get album and artist info
                    album_name = audio.get('album', ['Unknown Album'])[0]
                    artist_name = audio.get('artist', ['Unknown Artist'])[0]
                    year = audio.get('date', [''])[0][:4]  # Extract year from date

                    # Create album key
                    album_key = f"{album_name}|{artist_name}"

                    if album_key not in albums:
                        albums[album_key] = {
                            "title": album_name,
                            "artist": artist_name,
                            "year": year if year.isdigit() else "Unknown",
                            "cover": "🎵",  # Default cover
                            "tracks": []
                        }

                    # Add track to album
                    title = audio.get('title', [os.path.basename(file_path)])[0]
                    track_num = audio.get('tracknumber', ['0'])[0].split('/')[0]

                    # Get duration
                    duration = "0:00"
                    if hasattr(audio.info, 'length'):
                        mins = int(audio.info.length // 60)
                        secs = int(audio.info.length % 60)
                        duration = f"{mins}:{secs:02d}"

                    albums[album_key]["tracks"].append({
                        "title": title,
                        "artist": artist_name,
                        "album": album_name,
                        "duration": duration,
                        "track_num": int(track_num) if track_num.isdigit() else 0,
                        "file_path": file_path
                    })
            except Exception as e:
                print(f"Error processing {os.path.basename(file_path)}: {e}")

        # Sort tracks in each album by track number
        for album_key in albums:
            albums[album_key]["tracks"].sort(key=lambda t: t["track_num"])

        # Convert to list and sort by album name
        album_list = list(albums.values())
        album_list.sort(key=lambda a: a["title"])

        return album_list

    def show_year_album(self, album):
        """Display year album with tracks from the directory"""
        self.current_album = album

        # Update album label
        self.album_label.configure(text=f"{album['title']} ({album['year']})")

        # Clear existing tracks
        for widget in self.tracks_list.winfo_children():
            widget.destroy()

        # Get tracks from directory
        directory = album.get("directory", "")
        if not directory or not os.path.isdir(directory):
            return

        tracks = []
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path) and any(file.lower().endswith(ext) for ext in ['.mp3', '.flac', '.m4a', '.ogg', '.wav']):
                try:
                    # Extract metadata
                    import mutagen
                    audio = mutagen.File(file_path, easy=True)

                    if audio:
                        # Get track info
                        title = audio.get('title', [file])[0]
                        artist = audio.get('artist', ['Unknown Artist'])[0]

                        # Get duration
                        duration = "0:00"
                        if hasattr(audio.info, 'length'):
                            mins = int(audio.info.length // 60)
                            secs = int(audio.info.length % 60)
                            duration = f"{mins}:{secs:02d}"

                        tracks.append({
                            "title": title,
                            "artist": artist,
                            "duration": duration,
                            "file_path": file_path
                        })
                except Exception as e:
                    print(f"Error processing {file}: {e}")

        # Create playlist from these tracks
        self.current_playlist = tracks

        # Create track items
        for i, track in enumerate(tracks):
            self.create_track_item(i, track)

def main():
    app = ctk.CTk()
    app.geometry("1200x800")
    app.title("Advanced Music Player")

    # Set up the player
    player = AdvancedMusicPlayer(app)
    player.pack(fill="both", expand=True)

    # Clean up on close
    app.protocol("WM_DELETE_WINDOW", lambda: (player.on_close(), app.destroy()))

    app.mainloop()

if __name__ == "__main__":
    main()
