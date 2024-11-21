import os
import argparse
import subprocess
import sys
import re
import json

def log_progress(item_num, total_items, state, title):
    """Log progress to the console for a specific item's state."""
    sys.stdout.write(f"\r{state} item {item_num} of {total_items}: {title}")
    sys.stdout.flush()

def sanitize_filename(filename):
    """Sanitize filename by removing invalid characters."""
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def create_output_folder(base_folder, name=None):
    """Create an output folder based on the base folder and optional name."""
    if name:
        folder = os.path.join(base_folder, sanitize_filename(name))
    else:
        folder = base_folder
    if not os.path.exists(folder):
        os.makedirs(folder)
    return folder

def determine_default_output_folder(output_folder, audio_flag, video_flag):
    """Determine the default output folder if none is provided."""
    if not output_folder:
        base_folder = "downloads/audio" if audio_flag else "downloads/video"
    else:
        base_folder = output_folder
    if not os.path.exists(base_folder):
        os.makedirs(base_folder)
    return base_folder

def update_audio_metadata(file_path, name, chapter, artist, year):
    """Update the metadata of the downloaded MP3 file."""
    try:
        import eyed3
        if file_path.endswith(".mp3"):
            audiofile = eyed3.load(file_path)
            if audiofile.tag is None:
                audiofile.initTag()
            audiofile.tag.title = f"{name} Chapter {chapter}" if name and chapter else name or "Unknown"
            audiofile.tag.artist = artist or "Unknown"
            audiofile.tag.album = name if name else "Unknown"
            if year:
                audiofile.tag.recording_date = eyed3.core.Date(year)
            audiofile.tag.save()
    except Exception as e:
        print(f"\nWarning: Failed to update metadata for {file_path}. {e}")

def update_video_metadata(file_path, title, artist, year):
    """Update the metadata of the downloaded MP4 file."""
    try:
        import mutagen
        from mutagen.mp4 import MP4, MP4Tags

        if file_path.endswith(".mp4"):
            video_file = MP4(file_path)
            if video_file.tags is None:
                video_file.tags = MP4Tags()
            video_file.tags["\xa9nam"] = title  # Title
            video_file.tags["\xa9ART"] = artist or "Unknown"  # Artist
            if year:
                video_file.tags["\xa9day"] = str(year)  # Year
            video_file.save()
    except Exception as e:
        print(f"\nWarning: Failed to update metadata for {file_path}. {e}")

def extract_playlist_videos(playlist_url):
    """Extract video URLs from a playlist using yt-dlp."""
    try:
        command = [
            "yt-dlp",
            "--flat-playlist",
            "-J",  # Output JSON
            playlist_url
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        video_urls = [f"https://www.youtube.com/watch?v={entry['id']}" for entry in data['entries']]
        return video_urls
    except subprocess.CalledProcessError:
        print("\nFailed to extract playlist videos. Please check the playlist URL.")
        return []

def get_playlist_title(playlist_url):
    """Retrieve the title of the playlist from YouTube."""
    try:
        command = [
            "yt-dlp",
            "--flat-playlist",
            "-J",  # Output JSON
            playlist_url
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return sanitize_filename(data.get("title", "Unnamed Playlist"))
    except subprocess.CalledProcessError:
        return "Unnamed Playlist"
    
def process_playlist(playlist_url, output_folder, download_audio_flag, download_video_flag, name, year):
    """Download all videos or audios from a playlist using yt-dlp."""
    if not name:
        name = get_playlist_title(playlist_url)

    output_folder = create_output_folder(output_folder, name)
    video_urls = extract_playlist_videos(playlist_url)
    if not video_urls:
        print("\nNo videos found in the playlist.")
        return

    total_items = len(video_urls)
    chapter = 1

    for item_num, video_url in enumerate(video_urls, start=1):
        if download_audio_flag:
            download_audio(video_url, output_folder, name, chapter, item_num, total_items, None, year)
        if download_video_flag:
            download_video(video_url, output_folder, name, chapter, item_num, total_items, None, year)
        chapter += 1
    print("All downloads complete.")

def download_audio(video_url, output_folder, name=None, chapter=None, item_num=None, total_items=None, artist=None, year=None):
    """Download audio from a single video as MP3 using yt-dlp."""
    try:
        if not name:
            command = ["yt-dlp", "-e", video_url]
            result = subprocess.run(command, capture_output=True, text=True)
            name = result.stdout.strip()

        title = f"{name} Chapter {chapter}" if name and chapter else name or "Unknown"
        sanitized_title = sanitize_filename(title)

        log_progress(item_num, total_items, "Downloading", sanitized_title)
        command = [
            "yt-dlp",
            "-q", "--no-warnings",
            "-x", "--audio-format", "mp3",
            "-o", f"{output_folder}/{sanitized_title}.%(ext)s",
            video_url
        ]
        subprocess.run(command, check=True)

        log_progress(item_num, total_items, "Updating metadata for", sanitized_title)
        mp3_file_path = f"{output_folder}/{sanitized_title}.mp3"
        update_audio_metadata(mp3_file_path, name, chapter, artist, year)

        log_progress(item_num, total_items, "Completed processing for", sanitized_title)
        print("")
    except subprocess.CalledProcessError:
        log_progress(item_num, total_items, "Failed processing", sanitized_title)
        print("")

def download_video(video_url, output_folder, name=None, chapter=None, item_num=None, total_items=None, artist=None, year=None):
    """Download video as MP4 using yt-dlp."""
    try:
        if not name:
            command = ["yt-dlp", "-e", video_url]
            result = subprocess.run(command, capture_output=True, text=True)
            name = result.stdout.strip()

        title = f"{name} Chapter {chapter}" if name and chapter else name or "Unknown"
        sanitized_title = sanitize_filename(title)

        log_progress(item_num, total_items, "Downloading", sanitized_title)
        command = [
            "yt-dlp",
            "-q", "--no-warnings",
            "-f", "bestaudio[ext=m4a]+bestvideo[ext=mp4]/best",
            "-o", f"{output_folder}/{sanitized_title}.%(ext)s",
            video_url
        ]
        subprocess.run(command, check=True)

        log_progress(item_num, total_items, "Updating metadata for", sanitized_title)
        video_file_path = f"{output_folder}/{sanitized_title}.mp4"
        update_video_metadata(video_file_path, sanitized_title, artist, year)

        log_progress(item_num, total_items, "Completed processing for", sanitized_title)
        print("")
    except subprocess.CalledProcessError:
        log_progress(item_num, total_items, "Failed processing", sanitized_title)
        print("")

def print_usage():
    """Print usage instructions for the script."""
    usage_message = """
    Usage: python script.py [OPTIONS]

    OPTIONS:
      -p, --playlist        <URL>   Download all videos from a YouTube playlist.
      -s, --single-video    <URL>   Download a single YouTube video.
      -a, --audio                   Download as MP3 (audio only).
      -v, --video                   Download as MP4 (video).
      -o, --output          <PATH>  Base output folder (default: downloads/audio or downloads/video).
      -n, --name            <NAME>  Custom name for the folder and metadata.
      -A, --artist          <NAME>  Artist name for metadata.
      -c, --chapter         <NUM>   Chapter number for non-playlist downloads.
      -y, --year            <YEAR>  Year to include in the metadata (e.g., 2023).
    """
    print(usage_message)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download YouTube videos or playlists as MP3 or MP4 using yt-dlp.")
    parser.add_argument("-p", "--playlist", help="YouTube playlist URL to download.")
    parser.add_argument("-s", "--single-video", help="YouTube single video URL to download.")
    parser.add_argument("-a", "--audio", action="store_true", help="Download as MP3.")
    parser.add_argument("-v", "--video", action="store_true", help="Download as MP4.")
    parser.add_argument("-o", "--output", default=None, help="Output folder for downloads.")
    parser.add_argument("-n", "--name", help="Custom name for the folder and metadata.")
    parser.add_argument("-A", "--artist", help="Artist name for metadata.")
    parser.add_argument("-c", "--chapter", type=int, help="Chapter number for non-playlist downloads.")
    parser.add_argument("-y", "--year", type=int, help="Year to include in metadata (e.g., 2023).")
    args = parser.parse_args()

    if not args.audio and not args.video:
        print_usage()
        sys.exit(1)

    try:
        if args.single_video:
            output_folder = determine_default_output_folder(args.output, args.audio, args.video)
            if args.audio:
                download_audio(args.single_video, output_folder, args.name, args.chapter, 1, 1, args.artist, args.year)
            if args.video:
                download_video(args.single_video, output_folder, args.name, args.chapter, 1, 1, args.artist, args.year)
        elif args.playlist:
            output_folder = determine_default_output_folder(args.output, args.audio, args.video)
            process_playlist(args.playlist, output_folder, args.audio, args.video, args.name, args.year)
        else:
            print_usage()
    except KeyboardInterrupt:
        print("ABORTING")
        sys.exit(0)