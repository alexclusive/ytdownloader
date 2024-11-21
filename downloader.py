import os
import argparse
import subprocess
import sys
import re
import json
import eyed3
from mutagen.mp4 import MP4, MP4Tags

def log_progress(item_num, total_items, state, title):
    """Log progress to the console for a specific item's state."""
    if total_items == 1:
        sys.stdout.write(f"\r{state}: {title}")    
    else:
        sys.stdout.write(f"\r{state} item {item_num} of {total_items}: {title}")
    sys.stdout.flush()

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def determine_output_folder(output_folder, is_mp3:bool):
    base_folder = "downloads/video"
    if output_folder:
        base_folder = output_folder
    elif is_mp3:
        base_folder = "downloads/audio"
    if not os.path.exists(base_folder):
        os.makedirs(base_folder)
    return base_folder

def update_metadata(is_mp3:bool, file_path, title, album=None, chapter=None, artist=None, year=None):
    try:
        if is_mp3:
            audiofile_tmp = eyed3.load(file_path)
            if not audiofile_tmp:
                print(f"\nWarning: Failed to update metadata for {file_path}. {e}")
                return
            audiofile:eyed3.AudioFile = audiofile_tmp
            if audiofile.tag is None:
                audiofile.initTag()

            audiofile.tag.title = title

            if album:
                audiofile.tag.album = album

            if chapter:
                audiofile.tag.track = chapter
                
            if artist:
                audiofile.tag.artist = artist

            if year != 0:
                audiofile.tag.recording_date = eyed3.core.Date(year)

            audiofile.tag.save()
        else:
            video_file = MP4(file_path)
            if video_file.tags is None:
                video_file.tags = MP4Tags()

            video_file.tags["\xa9nam"] = title  # Title
            if artist:
                video_file.tags["\xa9ART"] = artist  # Artist
            if year:
                video_file.tags["\xa9day"] = str(year)  # Year

            video_file.save()
    except Exception as e:
        print(f"\nWarning: Failed to update metadata for {file_path}. {e}")

def download_mp3(video_url, output_folder, item_num=None, total_items=None, album=None, chapter=None, artist=None, year=None):
    try:
        if not album:
            command = ["yt-dlp", "-e", video_url]
            result = subprocess.run(command, capture_output=True, text=True)
            album = result.stdout.strip()
        
        title = "Unknown"
        if album and chapter:
            title = f"{album} Chapter {chapter}"
        elif album:
            title = album
        title = sanitize_filename(title)

        log_progress(item_num, total_items, "Downloading", title)
        command = [
            "yt-dlp",
            "-q", "--no-warnings",
            "-x", "--audio-format", "mp3",
            "-o", f"{output_folder}/{title}.%(ext)s",
            video_url
        ]
        subprocess.run(command, check=True)

        log_progress(item_num, total_items, "Updating metadata for", title)
        file_path = f"{output_folder}/{title}.mp3"
        update_metadata(True, file_path, title, album, chapter, artist, year)

        log_progress(item_num, total_items, "Completed", title)
        print("")
    except subprocess.CalledProcessError:
        log_progress(item_num, total_items, "Failed processing", title)
        print("")

def download_mp4(video_url, output_folder, item_num=None, total_items=None, album=None, chapter=None, artist=None, year=None):
    try:
        if not album:
            command = ["yt-dlp", "-e", video_url]
            result = subprocess.run(command, capture_output=True, text=True)
            album = result.stdout.strip()

        title = "Unknown"
        if album and chapter:
            title = f"{album} Episode {chapter}"
        elif album:
            title = album
        title = sanitize_filename(title)

        log_progress(item_num, total_items, "Downloading", title)
        command = [
            "yt-dlp",
            "-q", "--no-warnings",
            "-f", "bestaudio[ext=m4a]+bestvideo[ext=mp4]/best",
            "-o", f"{output_folder}/{title}.%(ext)s",
            video_url
        ]
        subprocess.run(command, check=True)

        log_progress(item_num, total_items, "Updating metadata for", title)
        file_path = f"{output_folder}/{title}.mp4"
        update_metadata(False, file_path, title, album, chapter, artist, year)

        log_progress(item_num, total_items, "Completed processing for", title)
        print("")
    except subprocess.CalledProcessError:
        log_progress(item_num, total_items, "Failed processing", title)
        print("")

def get_playlist_title(url) -> str:
    try:
        command = [
            "yt-dlp",
            "--flat-playlist",
            "-J",  # Output JSON
            url
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return sanitize_filename(data.get("title", "Unnamed Playlist"))
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
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        video_urls = [f"https://www.youtube.com/watch?v={entry['id']}" for entry in data['entries']]
        return video_urls
    except subprocess.CalledProcessError:
        print("\nFailed to extract playlist videos. Please check the playlist URL.")
        return []
    
def process_playlist(url, output_dir=None, dl_mp3=None, album=None, artist=None, year=None, set_chapters=False):
    if not album:
        album = get_playlist_title(url)
    output_dir = determine_output_folder(output_dir, album)
    urls = get_playlist_urls(url)
    if not urls:
        print("\nNo videos found in the playlist.")
        return
    
    total_items = len(urls)
    
    for num, url in enumerate(urls, start=1):
        if dl_mp3:
            if set_chapters:
                download_mp3(url, output_dir, num, total_items, album, num, artist, year)
            else:
                download_mp3(url, output_dir, num, total_items, album, None, artist, year)
        else:
            if set_chapters:
                download_mp4(url, output_dir, num, total_items, album, num, artist, year)
            else:
                download_mp4(url, output_dir, num, total_items, album, None, artist, year)
    print("All Downloads Complete.")

def usage():
    print("Usage: ./YTDownloader [-h] [-a ALBUM] [-A ARTIST] [-c CHAPTER] [-C] [-n NAME] [-o OUTPUT] [-u <URL>] [-v] [-y YEAR]")
    print("To run using a GUI, run with no command line arguments")
    print()
    print("OPTIONS:")
    print("  -a, --album           <NAME>  Album name for folder and metadata.")
    print("  -A, --artist          <NAME>  Artist name for metadata.")
    print("  -c, --chapter         <NUM>   Chapter number for non-playlist downloads.")
    print("  -C, --set-chapters            Set chapters for metadata for MP3s in playlists.")
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
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("-v", "--video", action="store_true")
    parser.add_argument("-y", "--year", type=int)
    return parser.parse_args()

def is_playlist(url) -> bool:
    return "playlist" in url

def gui():
    import tkinter as tk
    from tkinter import ttk
    from datetime import datetime
    from tkinter import filedialog

    def download_button():
        pass

    def get_url():
        pass

    def get_is_mp4():
        pass

    def get_artist():
        pass

    def get_year():
        pass

    def browse_directory_button():
        directory = filedialog.askdirectory()
        if directory:
            directory_var.set(directory)
            
    def browse_icon_button():
        filetypes = [("Image files", "*.png *.ico *.jpg *.jpeg"), ("All files", "*.*")]
        file_path = filedialog.askopenfilename(filetypes=filetypes, title="Select an Image")
        if file_path:
            icon_var.set(file_path)

    window = tk.Tk()
    window.title("YTDownloader")
    
    main_row = 1
    # URL
    url_var = tk.StringVar()
    url_label = tk.Label(window, text="URL")
    url_text = ttk.Entry(window, width=50, textvariable=url_var)
    url_label.grid(row=main_row, column=1, columnspan=2)
    url_text.grid(row=main_row+1, column=1, columnspan=2, sticky="EW")
    # MP3 or MP4
    as_mp4 = tk.BooleanVar(value=False)
    radio_mp3 = ttk.Radiobutton(window, text="MP3", variable=as_mp4, value=False)
    radio_mp4 = ttk.Radiobutton(window, text="MP4", variable=as_mp4, value=True)
    radio_mp3.grid(row=main_row+2, column=1)
    radio_mp4.grid(row=main_row+2, column=2)

    general_row = 4
    info_all = tk.Label(window, text="General Settings")
    info_all.grid(row=general_row, column=1, columnspan=2)
    # Directory
    directory_var = tk.StringVar()
    directory_label = tk.Label(window, text="Directory")
    directory_text = ttk.Entry(window, width=25, textvariable=directory_var)
    directory_button = ttk.Button(window, text="Browse", command=browse_directory_button)
    directory_label.grid(row=general_row+1, column=1, columnspan=2)
    directory_text.grid(row=general_row+2, column=1, sticky="EW")
    directory_button.grid(row=general_row+2, column=2, sticky="NESW")
    # Album
    album_name_var = tk.StringVar()
    album_name_label = tk.Label(window, text="Album Name") # Sets album
    album_name_text = ttk.Entry(window, width=50, textvariable=album_name_var)
    album_name_label.grid(row=general_row+3, column=1, columnspan=2)
    album_name_text.grid(row=general_row+4, column=1, columnspan=2, sticky="EW")
    # Artist
    artist_var = tk.StringVar()
    artist_name_label = tk.Label(window, text="Artist Name")
    artist_name_text = ttk.Entry(window, width=50, textvariable=artist_var)
    artist_name_label.grid(row=general_row+5, column=1, columnspan=2)
    artist_name_text.grid(row=general_row+6, column=1, columnspan=2, sticky="EW")
    # Year
    use_year_var = tk.BooleanVar(value=False)
    use_year_check = ttk.Checkbutton(window, text="Set Year?", variable=use_year_var)
    year_spinbox = ttk.Spinbox(window, from_=1900, to=2100)
    year_spinbox.set(datetime.now().year)
    use_year_check.grid(row=general_row+7, column=1)
    year_spinbox.grid(row=general_row+7, column=2, sticky="EW")
    # Image
    icon_var = tk.StringVar()
    icon_label = tk.Label(window, text="Icon")
    icon_text = ttk.Entry(window, width=25, textvariable=icon_var)
    icon_button = ttk.Button(window, text="Browse", command=browse_icon_button)
    icon_label.grid(row=general_row+8, column=1, columnspan=2)
    icon_text.grid(row=general_row+9, column=1, sticky="EW")
    icon_button.grid(row=general_row+9, column=2, sticky="NESW")

    playlist_row = 14
    info_optional = tk.Label(window, text="Playlist Settings")
    info_optional.grid(row=playlist_row, column=1, columnspan=2)
    # Set_Chapters
    set_chapters_var = tk.BooleanVar(value=True)
    set_chapters_check = ttk.Checkbutton(window, text="Set Chapter Metadata?", variable=set_chapters_var)
    set_chapters_check.grid(row=playlist_row+1, column=1, columnspan=2)

    non_playlist_row = 16
    info_optional = tk.Label(window, text="Non-Playlist Settings")
    info_optional.grid(row=non_playlist_row, column=1, columnspan=2)
    # Chapter
    use_chapter_var = tk.BooleanVar(value=False)
    use_chapter_check = ttk.Checkbutton(window, text="Set Chapter?", variable=use_chapter_var)
    chapter_spinbox = ttk.Spinbox(window, from_=0, to=sys.maxsize)
    chapter_spinbox.set(1)
    use_chapter_check.grid(row=non_playlist_row+1, column=1)
    chapter_spinbox.grid(row=non_playlist_row+1, column=2, sticky="EW")

    # empty = tk.Label(window)
    # empty.grid(row=21)

    download_row = 18
    info_progress = tk.Label(window, text="Download")
    info_progress.grid(row=download_row, column=1, columnspan=2)
    # Download and progress
    progress_var = tk.StringVar(value="Progress N/A")
    progress_label = tk.Label(window, textvariable=progress_var)
    download = ttk.Button(window, text="Download", command=download_button)
    progress_label.grid(row=download_row+1, column=1, sticky="EW")
    download.grid(row=download_row+1, column=2, sticky="NESW")

    window.mainloop()

def main():
    if len(sys.argv) == 1: # no args given, run with gui
        gui()
        sys.exit()

    args = get_args()

    if not args.url or args.help:
        usage()
        sys.exit()

    try:
        album = "Unknown"
        if args.album:
            album = args.album

        if is_playlist(args.url):
            if not args.album:
                album = get_playlist_title(args.url)
            output_dir = determine_output_folder(output_dir, album)
            process_playlist(args.url, output_dir, not args.video, album, args.artist, args.year, args.set_chapters)
        elif args.video:
            download_mp4(args.url, output_dir, 1, 1, album, args.chapter, args.artist, args.year)
        else:
            download_mp3(args.url, output_dir, 1, 1, album, args.chapter, args.artist, args.year)

    except KeyboardInterrupt:
        print("ABORTING")
        sys.exit()

if __name__ == "__main__":
    main()