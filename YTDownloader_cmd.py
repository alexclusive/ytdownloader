import argparse
import eyed3
import json
from mutagen.mp4 import MP4, MP4Tags, MP4Cover
import os
from PIL import Image
import re
import subprocess
import sys

def sanitise_text(text:str):
    text = text.replace(':', ' -')
    return re.sub(r'[<>"/\\|?*]', '', text)

def convert_ico_to_png(ico_path):
    try:
        img = Image.open(ico_path)
        png_path = ico_path.replace(".ico", ".png")
        img.save(png_path, format="PNG")
        return png_path
    except Exception as e:
        log_progress(0, 0, f"Failed converting .ico to .png. {e}", "")
        return None

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError: # MEIPASS is only set by pyinstaller, this is so it can run without being compiled
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def is_playlist(url) -> bool:
    return "playlist" in url

def log_progress(item_num, total_items, state, title):
    if total_items == 0:
        sys.stdout.write(state)
    elif total_items == 1:
        sys.stdout.write(f"\r{state}: {title}\033[K") # \033[K is an ANSI code to clear the whole cmd line
    else:
        sys.stdout.write(f"\r{state} item {item_num} of {total_items}: {title}\033[K")
    sys.stdout.flush()
    if "Completed" in state or "Fail" in state:
        print()

def determine_output_folder(output_folder, album=None, is_mp3:bool=False):
    base_folder = "downloads/video"
    if output_folder:
        base_folder = output_folder
    elif album:
        base_folder = "downloads/" + sanitise_text(album)
    elif is_mp3:
        base_folder = "downloads/audio"

    if not os.path.exists(base_folder):
        os.makedirs(base_folder)
    return base_folder

def get_video_title(video_url):
    try:
        command = ["yt-dlp", "-e", video_url]  # The '-e' option extracts the video title
        result = subprocess.run(command, capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        title = result.stdout.strip()
        return title
    except subprocess.CalledProcessError:
        return "Unknown"
    
def get_video_thumbnail(video_url, output_folder):
    try:
        os.makedirs(output_folder, exist_ok=True)

        command = [
            "yt-dlp",
            "--skip-download",
            "--write-thumbnail",
            "-o", f"{output_folder}/%(title)s.%(ext)s",
            video_url
        ]
        subprocess.run(command, check=True)

        for file in os.listdir(output_folder):
            if file.endswith((".jpg", ".png", ".webp")):
                print(f"Thumbnail downloaded: {os.path.join(output_folder, file)}")
                return os.path.join(output_folder, file)

        print("Thumbnail download failed: no file found.")
        log_progress(0, 0, f"Failed to download thumbnail for {video_url}. No file found. {e}", "")
        return None
    except subprocess.CalledProcessError as e:
        log_progress(0, 0, f"Failed to download thumbnail for {video_url}. {e}", "")
        return None

def update_metadata(is_mp3:bool, file_path, title, album=None, chapter=None, artist=None, year=None, icon_path=None, url=None):
    try:
        if is_mp3:
            audiofile_tmp = eyed3.load(file_path)
            if not audiofile_tmp:
                log_progress(0, 0, f"Failed to update metadata for {file_path}. {e}", "")
                return
            audiofile:eyed3.AudioFile = audiofile_tmp
            if audiofile.tag is None:
                audiofile.initTag(version=(2, 3, 0))
            
            audiofile.tag.title = title
            if album:
                audiofile.tag.album = album
            if chapter:
                audiofile.tag.setTextFrame("TRCK", f"{chapter}/0")
            if artist:
                audiofile.tag.artist = artist
            if year:
                audiofile.tag.recording_date = eyed3.core.Date(year)
            if icon_path and os.path.exists(icon_path):
                temp_icon_path = None
                if icon_path.lower().endswith(".ico"):
                    temp_icon_path = convert_ico_to_png(icon_path)
                    icon_path = temp_icon_path
                if icon_path and os.path.exists(icon_path): # Ensure conversion worked
                    with open(icon_path, "rb") as img_file:
                        image_data = img_file.read()
                    if isinstance(image_data, bytes):
                        audiofile.tag.images.set(
                            eyed3.id3.frames.ImageFrame.FRONT_COVER,
                            image_data,
                            "image/jpeg" if icon_path.lower().endswith(".jpg") else "image/png"
                        )
                if temp_icon_path and os.path.exists(temp_icon_path):
                    os.remove(temp_icon_path)
            if url:
                audiofile.tag.comments.set(url)
            audiofile.tag.save(version=(2, 3, 0))
        else:
            video_file = MP4(file_path)
            if video_file.tags is None:
                video_file.tags = MP4Tags()

            video_file.tags["\xa9nam"] = title
            if album:
                video_file.tags["\xa9alb"] = album
            if chapter:
                video_file.tags["trkn"] = [(chapter, 0)]
            if artist:
                video_file.tags["\xa9ART"] = artist
            if year:
                video_file.tags["\xa9day"] = str(year)
            if url:
                video_file.tags["\xa9cmt"] = url

            if icon_path and os.path.exists(icon_path):
                temp_icon_path = None
                if icon_path.lower().endswith(".ico"):
                    temp_icon_path = convert_ico_to_png(icon_path)
                    icon_path = temp_icon_path  # Use the converted .png file
                if icon_path and os.path.exists(icon_path):  # Ensure conversion succeeded
                    with open(icon_path, "rb") as img_file:
                        image_data = img_file.read()
                    video_file.tags["covr"] = [MP4Cover(
                        image_data,
                        MP4Cover.FORMAT_PNG if icon_path.lower().endswith(".png") else MP4Cover.FORMAT_JPEG
                    )]
                if temp_icon_path and os.path.exists(temp_icon_path):
                    os.remove(temp_icon_path)

            video_file.save()
    except Exception as e:
        log_progress(0, 0, f"Failed to update metadata for {file_path}. {e}", "")

def download_mp3(video_url, output_folder, item_num=None, total_items=None, album=None, chapter=None, artist=None, year=None, icon_path=None, title=None) -> bool:
    try:
        if not album:
            album = get_video_title(video_url)
        
        title_set = "Unknown"
        if title:
            title_set = title
        elif album and chapter:
            title_set = f"{album} Chapter {chapter}"
        elif album:
            title_set = album
        else:
            title_set = get_video_title(video_url)
        title_set = sanitise_text(title_set)

        log_progress(item_num, total_items, "Downloading", title_set)
        command = [
            "yt-dlp",
            "-q", "--no-warnings",
            "-x", "--audio-format", "mp3",
            "-o", f"{output_folder}/{title_set}.%(ext)s",
            video_url
        ]
        subprocess.run(command, check=True, creationflags=subprocess.CREATE_NO_WINDOW)

        log_progress(item_num, total_items, "Updating metadata for", title_set)
        file_path = f"{output_folder}/{title_set}.mp3"
        update_metadata(True, file_path, title_set, album, chapter, artist, year, icon_path, video_url)

        log_progress(item_num, total_items, "Completed", title_set)
        return True
    except subprocess.CalledProcessError:
        log_progress(item_num, total_items, "Failed processing", title_set)
        return False

def download_mp4(video_url, output_folder, item_num=None, total_items=None, album=None, chapter=None, artist=None, year=None, icon_path=None, title=None) -> bool:
    try:
        if not album:
            album = get_video_title(video_url)

        if not icon_path:
            icon_path = get_video_thumbnail(video_url, output_folder)

        title_set = "Unknown"
        if title:
            title_set = title        
        elif album and chapter:
            title_set = f"{album} Episode {chapter}"
        elif album:
            title_set = album
        else:
            title_set = get_video_title(video_url)
        title_set = sanitise_text(title_set)

        log_progress(item_num, total_items, "Downloading", title_set)
        command = [
            "yt-dlp",
            "-q", "--no-warnings",
            "-f", "bestaudio[ext=m4a]+bestvideo[ext=mp4]/best",
            "-o", f"{output_folder}/{title_set}.%(ext)s",
            video_url
        ]
        subprocess.run(command, check=True, creationflags=subprocess.CREATE_NO_WINDOW)

        log_progress(item_num, total_items, "Updating metadata for", title_set)
        file_path = f"{output_folder}/{title_set}.mp4"
        update_metadata(False, file_path, title_set, album, chapter, artist, year, icon_path, video_url)

        log_progress(item_num, total_items, "Completed processing for", title_set)
        return True
    except subprocess.CalledProcessError:
        log_progress(item_num, total_items, "Failed processing", title_set)
        return False

def get_playlist_title(url) -> str:
    try:
        command = [
            "yt-dlp",
            "--flat-playlist",
            "-J",  # Output JSON
            url
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        data = json.loads(result.stdout)
        return sanitise_text(data.get("title", "Unnamed Playlist"))
    except subprocess.CalledProcessError:
        return "Unnamed Playlist"

def get_playlist_urls(playlist_url) -> list[str]:
    try:
        command = [
            "yt-dlp",
            "--flat-playlist",
            "-J",  # Output JSON
            playlist_url
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        data = json.loads(result.stdout)
        video_urls = [f"https://www.youtube.com/watch?v={entry['id']}" for entry in data['entries']]
        return video_urls
    except subprocess.CalledProcessError:
        log_progress(0, 0, "Failed extracting playlist videos", "")
        return []
    
def process_playlist(url, output_dir=None, dl_mp3=None, album=None, artist=None, year=None, set_chapters=False, icon_path=None):
    if not album:
        album = get_playlist_title(url)
        output_dir = determine_output_folder(output_dir, album, dl_mp3)

    urls = get_playlist_urls(url)
    if not urls:
        return
    
    total_items = len(urls)
    for num, url in enumerate(urls, start=1):
        # always set chapter number, but if not set_chapter, dont put chapter in name
        chap = num
        title = None
        if not set_chapters:
            title = get_video_title(url)

        if dl_mp3:
            download_mp3(url, output_dir, num, total_items, album, chap, artist, year, icon_path, title)
        else:
            download_mp4(url, output_dir, num, total_items, album, chap, artist, year, icon_path, title)

def read_inputs(url, is_mp3, output_dir_=None, album_=None, artist_=None, year_=None, chapter_=None, set_chapters_=None, icon_=None):
    output_dir = determine_output_folder(output_dir_, album_, is_mp3)
    album = None
    if album_:
        album = album_
    if is_playlist(url):
        if not album_:
            album = get_playlist_title(url)
        process_playlist(url, output_dir, is_mp3, album, artist_, year_, set_chapters_, icon_)
    elif is_mp3:
        download_mp3(url, output_dir, 1, 1, album, chapter_, artist_, year_, icon_)
    else:
        download_mp4(url, output_dir, 1, 1, album, chapter_, artist_, year_, icon_)

def usage():
    print("Usage: ./YTDownloader [-h] [-a ALBUM] [-A ARTIST] [-c CHAPTER] [-C] [-i ICON] [-n NAME] [-o OUTPUT] [-u URL] [-v] [-y YEAR]")
    print("To run using a GUI, run with no command line arguments")
    print()
    print("OPTIONS:")
    print("  -a, --album           <NAME>  Album name for folder and metadata.")
    print("  -A, --artist          <NAME>  Artist name for metadata.")
    print("  -c, --chapter         <NUM>   Chapter number for non-playlist downloads.")
    print("  -C, --set-chapters            Set chapters for metadata for items in playlists.")
    print("  -i, --icon            <PATH>  Path to ico/png/jpg/jpeg file to use as file icon/s.")
    print("  -o, --output          <PATH>  Base output folder (default: downloads/audio or downloads/video).")
    print("  -u  --url             <URL>   URL for youtube video or playlist.")
    print("  -v, --video                   Download as MP4 instead of MP3.")
    print("  -y, --year            <YEAR>  Year to include in the metadata.")

def get_args():
    parser = argparse.ArgumentParser(description="Download YouTube videos or playlists as MP3 or MP4 using yt-dlp.", add_help=False)
    parser.add_argument("-u", "--url")
    parser.add_argument("-a", "--album")
    parser.add_argument("-A", "--artist")
    parser.add_argument("-c", "--chapter", type=int)
    parser.add_argument("-C", "--set-chapters", action="store_true")
    parser.add_argument("-i", "--icon", default=None)
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("-v", "--video", action="store_true")
    parser.add_argument("-y", "--year", type=int)
    return parser.parse_args()

def main():
    args = get_args()
    if not args.url or args.help:
        usage()
        sys.exit()

    try:
        read_inputs(args.url, not args.video, output_dir_=args.output,
            album_=args.album, artist_=args.artist, year_=args.year,
            chapter_=args.chapter, set_chapters_=args.set_chapters, icon_=args.icon)
    except KeyboardInterrupt:
        log_progress(0, 0, "ABORTING", "")
        sys.exit()

if __name__ == "__main__":
    main()