import os
import argparse
import subprocess
import sys
import re

def log_progress(message):
    """Log progress to the console, overwriting the previous line."""
    sys.stdout.write(f"\r{message}")
    sys.stdout.flush()

def sanitize_filename(filename):
    """Sanitize filename by removing invalid characters."""
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def download_audio(video_url, output_folder, name=None, chapter=None):
    """Download audio from a single video as MP3 using yt-dlp."""
    try:
        # Ensure output folder exists
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        title = f"{name} Chapter {chapter}" if name and chapter else "Unknown"
        sanitized_title = sanitize_filename(title)
        log_progress(f"Downloading audio for: {sanitized_title} ...")
        
        # yt-dlp command for downloading audio as MP3
        command = [
            "yt-dlp",
            "-x", "--audio-format", "mp3",
            "-o", f"{output_folder}/{sanitized_title} - %(title)s.%(ext)s",
            video_url
        ]
        subprocess.run(command, check=True)

        # Update the metadata (only for MP3)
        mp3_file_path = f"{output_folder}/{sanitized_title} - %(title)s.mp3"
        update_metadata(mp3_file_path, name, chapter)

        log_progress(f"Audio download complete: {sanitized_title}\n")
    except subprocess.CalledProcessError as e:
        log_progress(f"Failed to download audio {video_url}: {e}\n")

def download_video(video_url, output_folder, name=None, chapter=None):
    """Download video as MP4 using yt-dlp."""
    try:
        # Ensure output folder exists
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        title = f"{name} Chapter {chapter}" if name and chapter else "Unknown"
        sanitized_title = sanitize_filename(title)
        log_progress(f"Downloading video for: {sanitized_title} ...")
        
        # yt-dlp command for downloading video as MP4
        command = [
            "yt-dlp",
            "-f", "bestvideo+bestaudio/best",
            "-o", f"{output_folder}/{sanitized_title} - %(title)s.%(ext)s",
            video_url
        ]
        subprocess.run(command, check=True)

        log_progress(f"Video download complete: {sanitized_title}\n")
    except subprocess.CalledProcessError as e:
        log_progress(f"Failed to download video {video_url}: {e}\n")

def update_metadata(file_path, name, chapter):
    """Update the metadata of the downloaded MP3 file."""
    try:
        import eyed3
        if file_path.endswith(".mp3"):
            audiofile = eyed3.load(file_path)
            audiofile.tag.title = f"{name} Chapter {chapter}"
            audiofile.tag.album = name
            audiofile.tag.track = chapter
            audiofile.tag.save()
            print(f"Metadata updated for: {file_path}")
    except Exception as e:
        print(f"Failed to update metadata for {file_path}: {e}")

def process_playlist(playlist_url, output_folder, download_audio_flag, download_video_flag, name):
    """Download all videos or audios from a playlist using yt-dlp."""
    try:
        chapter = 1
        if download_audio_flag:
            log_progress(f"Downloading playlist as audio for {name}...")
            command = [
                "yt-dlp",
                "--yes-playlist", "-x", "--audio-format", "mp3",
                "-o", f"{output_folder}/{name}/%(playlist_title)s - %(chapter_number)s.%(ext)s",
                playlist_url
            ]
            subprocess.run(command, check=True)
            log_progress(f"Audio playlist download complete: {name}\n")
        
        if download_video_flag:
            log_progress(f"Downloading playlist as video for {name}...")
            command = [
                "yt-dlp",
                "--yes-playlist", "-f", "bestvideo+bestaudio/best",
                "-o", f"{output_folder}/{name}/%(playlist_title)s - %(chapter_number)s.%(ext)s",
                playlist_url
            ]
            subprocess.run(command, check=True)
            log_progress(f"Video playlist download complete: {name}\n")
        
        # Process each video or audio and apply metadata
        for video_url in playlist_url:
            if download_audio_flag:
                download_audio(video_url, output_folder, name, chapter)
            if download_video_flag:
                download_video(video_url, output_folder, name, chapter)
            chapter += 1
    except subprocess.CalledProcessError as e:
        log_progress(f"Failed to download playlist {playlist_url}: {e}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download YouTube videos or playlists as MP3 or MP4 using yt-dlp.")
    parser.add_argument("-p", "--playlist", help="YouTube playlist URL to download.")
    parser.add_argument("-s", "--single-video", help="YouTube single video URL to download.")
    parser.add_argument("-a", "--audio", action="store_true", help="Download as MP3.")
    parser.add_argument("-v", "--video", action="store_true", help="Download as MP4.")
    parser.add_argument("-o", "--output", default="downloads", help="Output folder for downloaded files.")
    parser.add_argument("-n", "--name", help="Name of the playlist or video for metadata.")
    
    args = parser.parse_args()

    if not args.audio and not args.video:
        print("You must specify what to download: audio (-a) or video (-v). Use -h for help.")
        exit(1)

    if args.playlist:
        process_playlist(args.playlist, args.output, args.audio, args.video, args.name)
    elif args.single_video:
        if args.audio:
            download_audio(args.single_video, args.output, args.name)
        if args.video:
            download_video(args.single_video, args.output, args.name)
    else:
        print("You must provide either a playlist URL (-p) or a single video URL (-s). Use -h for help.")
