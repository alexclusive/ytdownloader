# YTDownloader

Yes ChatGPT made this whole thing, don't @ me  

**YTDownloader** is a Python script that allows you to download YouTube videos and playlists in either MP3 (audio) or MP4 (video) formats using `yt-dlp`. It supports setting custom metadata (like title, album, and year) for both audio and video files.

## Features
- Download YouTube playlists or single videos.
- Download as MP3 (audio only) or MP4 (video).
- Set custom metadata for audio (MP3) and video (MP4) files.
- Customize download folder and metadata attributes such as title and year.
- Easily compile the script into an executable with `pyinstaller`.

## Usage

### Options:
```bash
Usage: python script.py [OPTIONS]

OPTIONS:
  -p, --playlist        <URL>   Download all videos from a YouTube playlist.
  -s, --single-video    <URL>   Download a single YouTube video.
  -a, --audio                   Download as MP3 (audio only).
  -v, --video                   Download as MP4 (video).
  -o, --output          <PATH>  Base output folder (default: downloads/audio or downloads/video).
  -n, --name            <NAME>  Custom name for the output folder and metadata.
  -y, --year            <YEAR>  Year to include in metadata (e.g., 2023).
  
NOTES:
  - At least one of -a (audio) or -v (video) must be specified.
  - For playlists, you can omit -n to use the YouTube playlist title as the folder name.

EXAMPLES:
  1. Download a playlist as MP3:
     python script.py -p <playlist_url> -a

  2. Download a single video as MP4 to a specific folder:
     python script.py -s <video_url> -v -o /path/to/downloads

  3. Download a playlist as MP3 with a custom name:
     python script.py -p <playlist_url> -a -n "My Playlist"

  4. Download a single video as MP3 with metadata year 2023:
     python script.py -s <video_url> -a -y 2023
```

## Compilation
If you'd like to convert this Python script into a standalone executable, you can use PyInstaller. Follow the steps below to compile the script.

### Step 1: Install PyInstaller
First, you need to install `PyInstaller`. Run the following command in your terminal or command prompt:

```bash
pip install pyinstaller
```

### Step 2: Prepare the Script
Ensure your script (e.g. `script.py`) is working properly. Test it by running it in your terminal with various options to make sure there are no errors.

### Step 3: Compile the Script into an Executable
Run the following command to compile the Python script into a single executable file:

```bash
pyinstaller --onefile --name YTDownloader script.py
```

### Step 4: Locate the Executable
After PyInstaller completes the compilation process, the executable file will be located in the `dist/` folder inside your project directory. The executable will have the name you specified, like `YTDownloader` (on Windows, it will be `YTDownloader.exe`).

### Step 5: Run the Executable
You can now run the executable directly from the command line:

```bash
./dist/YTDownloader [OPTIONS]
```
Or, on Windows:

```bash
dist\YTDownloader.exe [OPTIONS]
```