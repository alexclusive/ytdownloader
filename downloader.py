import argparse
import eyed3
import io
import json
from mutagen.mp4 import MP4, MP4Tags, MP4Cover
import os
from PIL import Image, ImageTk
import re
import requests
import subprocess
import sys
import threading
from typing import Callable

using_gui = False

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError: # MEIPASS is only set by pyinstaller, this is so it can run without being compiled
        base_path = os.path.abspath(".")

    full_path = os.path.join(base_path, relative_path)

    return full_path

def log_progress(item_num, total_items, state, title):
    if not using_gui:
        if total_items == 0:
            sys.stdout.write(state)
        elif total_items == 1:
            sys.stdout.write(f"\r{state}: {title}\033[K") # \033[K is an ANSI code to clear the whole cmd line
        else:
            sys.stdout.write(f"\r{state} item {item_num} of {total_items}: {title}\033[K")
        sys.stdout.flush()
        if "Completed" in state or "Fail" in state:
            print()

def get_video_title(video_url):
    try:
        command = ["yt-dlp", "-e", video_url]  # The '-e' option extracts the video title
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        title = result.stdout.strip()
        return title
    except subprocess.CalledProcessError:
        return "Unknown"

def sanitise_text(text):
    return re.sub(r'[<>:"/\\|?*]', '_', text)

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

def convert_ico_to_png(ico_path):
    try:
        img = Image.open(ico_path)
        png_path = ico_path.replace(".ico", ".png")
        img.save(png_path, format="PNG")
        return png_path
    except Exception as e:
        log_progress(0, 0, f"Failed converting .ico to .png. {e}", "")
        return None

def update_metadata(is_mp3:bool, file_path, title, album=None, chapter=None, artist=None, year=None, icon_path=None):
    try:
        if is_mp3:
            audiofile_tmp = eyed3.load(file_path)
            if not audiofile_tmp:
                log_progress(0, 0, f"Failed to update metadata for {file_path}. {e}", "")
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
            if year:
                audiofile.tag.recording_date = eyed3.core.Date(year)

            if icon_path and os.path.exists(icon_path):
                temp_icon_path = None
                if icon_path.lower().endswith(".ico"):
                    temp_icon_path = convert_ico_to_png(icon_path)
                    icon_path = temp_icon_path  # Use the converted .png file
                if icon_path and os.path.exists(icon_path):  # Ensure conversion succeeded
                    with open(icon_path, "rb") as img_file:
                        image_data = img_file.read()
                    audiofile.tag.images.set(
                        eyed3.id3.frames.ImageFrame.FRONT_COVER,
                        image_data,
                        "image/jpeg" if icon_path.lower().endswith(".jpg") else "image/png"
                    )
                if temp_icon_path and os.path.exists(temp_icon_path):
                    os.remove(temp_icon_path)

            audiofile.tag.save()
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

def download_mp3(video_url, output_folder, item_num=None, total_items=None, album=None, chapter=None, artist=None, year=None, icon_path=None) -> bool:
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
        else:
            title = get_video_title(video_url)
        title = sanitise_text(title)

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
        update_metadata(True, file_path, title, album, chapter, artist, year, icon_path)

        log_progress(item_num, total_items, "Completed", title)
        return True
    except subprocess.CalledProcessError:
        log_progress(item_num, total_items, "Failed processing", title)
        return False

def download_mp4(video_url, output_folder, item_num=None, total_items=None, album=None, chapter=None, artist=None, year=None, icon_path=None) -> bool:
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
        else:
            title = get_video_title(video_url)
        title = sanitise_text(title)

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
        update_metadata(False, file_path, title, album, chapter, artist, year, icon_path)

        log_progress(item_num, total_items, "Completed processing for", title)
        return True
    except subprocess.CalledProcessError:
        log_progress(item_num, total_items, "Failed processing", title)
        return False

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
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        video_urls = [f"https://www.youtube.com/watch?v={entry['id']}" for entry in data['entries']]
        return video_urls
    except subprocess.CalledProcessError:
        log_progress(0, 0, "Failed extracting playlist videos", "")
        return []
    
def process_playlist(url, output_dir=None, dl_mp3=None, album=None, artist=None, year=None, set_chapters=False, icon_path=None, set_progress_function:Callable=None):
    if not album:
        album = get_playlist_title(url)
    output_dir = determine_output_folder(output_dir, album)
    urls = get_playlist_urls(url)
    if not urls:
        return
    
    total_items = len(urls)
    
    for num, url in enumerate(urls, start=1):
        if set_progress_function:
            set_progress_function(f"{num} of {total_items}")

        chap = None
        if set_chapters:
            chap = num

        if dl_mp3:
            download_mp3(url, output_dir, num, total_items, album, chap, artist, year, icon_path)
        else:
            download_mp4(url, output_dir, num, total_items, album, chap, artist, year, icon_path)

def is_playlist(url) -> bool:
    return "playlist" in url

def gui():
    import tkinter as tk
    from tkinter import ttk, filedialog
    from datetime import datetime

    def start_download(is_mp3:bool):
        def run_download():
            try:
                gui_url = get_url()
                gui_dir = get_directory()
                gui_album = get_album()
                gui_artist = get_artist()
                gui_year = get_year()
                gui_icon_path = get_icon_path()

                gui_set_chapters = get_set_chapters()
                gui_chapter = get_chapter()

                album = "Unknown"
                if gui_album:
                    album = gui_album

                output = determine_output_folder(gui_dir, album)
                if is_playlist(gui_url):
                    if not gui_album:
                        album = get_playlist_title(gui_url)
                    process_playlist(gui_url, output, is_mp3, album, gui_artist, gui_year, gui_set_chapters, gui_icon_path, set_progress)
                elif is_mp3:
                    set_progress("Downloading")
                    success = download_mp3(gui_url, output, 1, 1, album, gui_chapter, gui_artist, gui_year, gui_icon_path)
                    if success:
                        set_progress("Downloaded")
                    else:
                        set_progress("Failed")
                else:
                    set_progress("Downloading")
                    success = download_mp4(gui_url, output, 1, 1, album, gui_chapter, gui_artist, gui_year, gui_icon_path)
                    if success:
                        set_progress("Downloaded")
                    else:
                        set_progress("Failed")
            except Exception:
                set_progress("Error :(")
        
        thread = threading.Thread(target=run_download)
        thread.daemon = True  # Ensure the thread exits when the main program exits
        thread.start()

    def set_progress(progress:str):
        progress_var.set(progress)
        window.after(0, lambda: progress_label.update())

    def download_button_mp3():
        start_download(True)

    def download_button_mp4():
        start_download(False)

    def get_url():
        url = url_var.get()
        if len(url) > 0:
            return url
        return None
    
    def get_directory():
        directory = directory_var.get()
        if len(directory) > 0:
            return directory
        return None
    
    def get_album():
        album = album_name_var.get()
        if len(album) > 0:
            return album
        return None

    def get_artist():
        artist = artist_var.get()
        if len(artist) > 0:
            return artist
        return None

    def get_year():
        if use_year_var.get():
            return int(year_spinbox.get())
        return None
    
    def get_icon_path():
        icon = icon_var.get()
        if len(icon) > 0:
            return icon
        return None
    
    def get_set_chapters():
        return set_chapters_var.get()

    def get_chapter():
        if use_chapter_var.get():
            return int(chapter_spinbox.get())
        return None

    def browse_directory_button():
        directory = filedialog.askdirectory()
        if directory:
            directory_var.set(directory)
            
    def browse_icon_button():
        filetypes = [("Image files", "*.png *.ico *.jpg *.jpeg"), ("All files", "*.*")]
        file_path = filedialog.askopenfilename(filetypes=filetypes, title="Select an Image")
        if file_path:
            icon_var.set(file_path)

    def get_image(filename=None, url=None):
        try:
            image = None
            if filename == url:
                return None
            if filename and not url:
                filename = resource_path("assets/") + filename
                image = Image.open(filename)
            elif url and not filename:
                response = requests.get(url)
                response.raise_for_status() # Error if not found
                image = Image.open(io.BytesIO(response.content))
            image = image.convert("RGBA") # Enable transparency
            image.resize((32,32))
            return ImageTk.PhotoImage(image)
        except Exception:
            return None

    window = tk.Tk()
    window.title("YTDownloader")
    padding = 2

    # URL
    url_var = tk.StringVar()
    url_text = ttk.Entry(window, textvariable=url_var)
    url_text.grid(row=1, column=2, columnspan=2, sticky="EW", pady=padding)
    # Directory
    directory_button = ttk.Button(window, text="Browse", command=browse_directory_button)
    directory_var = tk.StringVar()
    directory_text = ttk.Entry(window, textvariable=directory_var)
    directory_button.grid(row=2, column=2, sticky="EW", pady=padding)
    directory_text.grid(row=2, column=3, sticky="EW", pady=padding)
    # Album
    album_name_var = tk.StringVar()
    album_name_label = tk.Label(window, text="Album")
    album_name_text = ttk.Entry(window, textvariable=album_name_var)
    album_name_label.grid(row=3, column=2)
    album_name_text.grid(row=3, column=3, sticky="EW", pady=padding)
    # Artist
    artist_var = tk.StringVar()
    artist_name_label = tk.Label(window, text="Artist")
    artist_name_text = ttk.Entry(window, textvariable=artist_var)
    artist_name_label.grid(row=4, column=2)
    artist_name_text.grid(row=4, column=3, sticky="EW", pady=padding)
    # Year
    use_year_var = tk.BooleanVar(value=False)
    use_year_check = ttk.Checkbutton(window, text="Set Year?", variable=use_year_var)
    year_spinbox = ttk.Spinbox(window, from_=1900, to=2100)
    year_spinbox.set(datetime.now().year)
    use_year_check.grid(row=5, column=2)
    year_spinbox.grid(row=5, column=3, sticky="EW", pady=padding)
    # Image
    icon_button = ttk.Button(window, text="Browse", command=browse_icon_button)
    icon_var = tk.StringVar()
    icon_text = ttk.Entry(window, textvariable=icon_var)
    icon_button.grid(row=6, column=2, sticky="EW", pady=padding)
    icon_text.grid(row=6, column=3, sticky="EW", pady=padding)

    # Download
    download_mp3_button = ttk.Button(window, text="Download MP3", command=download_button_mp3)
    download_mp4_button = ttk.Button(window, text="Download MP4", command=download_button_mp4)
    download_mp3_button.grid(row=1, column=5, sticky="NSEW", pady=padding)
    download_mp4_button.grid(row=1, column=6, sticky="NSEW", pady=padding)
    # Progress
    progress_var = tk.StringVar(value="Progress N/A")
    progress_label = tk.Label(window, textvariable=progress_var)
    progress_label.grid(row=2, column=5, columnspan=2, sticky="NSEW", pady=padding)
    # Playlist
    info_optional = tk.Label(window, text="Playlist")
    info_optional.grid(row=3, column=5, columnspan=2, sticky="SEW", pady=padding)
    # Set_Chapters
    set_chapters_var = tk.BooleanVar(value=True)
    set_chapters_check = ttk.Checkbutton(window, text="Set Chapters?", variable=set_chapters_var)
    set_chapters_check.grid(row=4, column=5, columnspan=2, pady=padding)
    # Non-Playlist
    info_optional = tk.Label(window, text="Non-Playlist")
    info_optional.grid(row=5, column=5, columnspan=2, sticky="SEW", pady=padding)
    # Chapter
    use_chapter_var = tk.BooleanVar(value=False)
    use_chapter_check = ttk.Checkbutton(window, text="Set Chapter?", variable=use_chapter_var)
    chapter_spinbox = ttk.Spinbox(window, from_=0, to=sys.maxsize, width=8)
    chapter_spinbox.set(1)
    use_chapter_check.grid(row=6, column=5, pady=padding)
    chapter_spinbox.grid(row=6, column=6, sticky="EW", pady=padding)

    # Images
    image_url = get_image(filename="url.png")
    image_dir = get_image(filename="directory.png")
    image_album = get_image(filename="album.png")
    image_artist = get_image(filename="artist.png")
    image_year = get_image(filename="calendar.png")
    image_icon = get_image(filename="icon.png")
    image_download = get_image(filename="download.png")
    image_progress = get_image(filename="progress.png")
    image_chapter = get_image(filename="track.png")
    image_heart = get_image(filename="heart.ico")
    
    # See here for all images: https://imgur.com/a/1DROK6r
    # image_url = get_image(url="https://imgur.com/7JNryMI")
    # image_dir = get_image(url="https://imgur.com/tu4nft0")
    # image_album = get_image(url="https://imgur.com/mHVSuBo")
    # image_artist = get_image(url="https://imgur.com/WdyNMye")
    # image_year = get_image(url="https://imgur.com/47EUA4U")
    # image_icon = get_image(url="https://imgur.com/eZR4zqG")
    # image_download = get_image(url="https://imgur.com/pjQbxNz")
    # image_progress = get_image(url="https://imgur.com/jK0fe1s")
    # image_chapter = get_image(url="https://imgur.com/da8GeId")
    # image_heart = get_image(url="https://imgur.com/egHLCTf")

    if image_url:
        image_label_url = tk.Label(window, image=image_url)
        image_label_url.grid(row=1, column=1, sticky="NSEW", pady=padding)
    if image_dir:
        image_label_dir = tk.Label(window, image=image_dir)
        image_label_dir.grid(row=2, column=1, sticky="NSEW", pady=padding)
    if image_album:
        image_label_album = tk.Label(window, image=image_album)
        image_label_album.grid(row=3, column=1, sticky="NSEW", pady=padding)
    if image_artist:
        image_label_artist = tk.Label(window, image=image_artist)
        image_label_artist.grid(row=4, column=1, sticky="NSEW", pady=padding)
    if image_year:
        image_label_year = tk.Label(window, image=image_year)
        image_label_year.grid(row=5, column=1, sticky="NSEW", pady=padding)
    if image_icon:
        image_label_icon = tk.Label(window, image=image_icon)
        image_label_icon.grid(row=6, column=1, sticky="NSEW", pady=padding)
    if image_download:
        image_label_download = tk.Label(window, image=image_download)
        image_label_download.grid(row=1, column=4, sticky="NSEW", pady=padding)
    if image_progress:
        image_label_progress = tk.Label(window, image=image_progress)
        image_label_progress.grid(row=2, column=4, sticky="NSEW", pady=padding)
    if image_chapter:
        image_label_chapter_1 = tk.Label(window, image=image_chapter)
        image_label_chapter_2 = tk.Label(window, image=image_chapter)
        image_label_chapter_1.grid(row=4, column=4, sticky="NSEW", pady=padding)
        image_label_chapter_2.grid(row=6, column=4, sticky="NSEW", pady=padding)
    if image_heart:
        window.iconphoto(False, image_heart)

    window.config(padx=5, pady=5)
    for i in range(1, 7):
        if i == 1 or i == 4:
            window.grid_columnconfigure(i, minsize=40, weight=1)
        else:
            window.grid_columnconfigure(i, minsize=100, weight=1)

    window.mainloop()

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
    global using_gui

    if len(sys.argv) == 1: # no args given, run with gui
        using_gui = True
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

        output_dir = determine_output_folder(args.output, album)
        if is_playlist(args.url):
            if not args.album:
                album = get_playlist_title(args.url)
            process_playlist(args.url, output_dir, not args.video, album, args.artist, args.year, args.set_chapters, args.icon)
        elif args.video:
            download_mp4(args.url, output_dir, 1, 1, album, args.chapter, args.artist, args.year, args.icon)
        else:
            download_mp3(args.url, output_dir, 1, 1, album, args.chapter, args.artist, args.year, args.icon)

    except KeyboardInterrupt:
        log_progress(0, 0, "ABORTING", "")
        sys.exit()

if __name__ == "__main__":
    main()