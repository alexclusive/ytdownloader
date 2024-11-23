# YTDownloader
I made this python application because I'm sick and tired of all those dumb websites that are terrible at the one thing they set out to do. Turns out it's actually really easy to download youtube videos. I haven't actually tested the max quality this is capable of - one way to find out!  

## Ways to Run
There are two versions packed into one .exe file: command-line and gui. These both do the same thing, and I'll explain each feature a little later.  
I don't know if this works on mac and frankly I do not care :)

### Command-line
To run this version of the program, run the program with more than zero command line arguments (e.g. `-h`).

#### Usage
```bash
Usage: ./YTDownloader.exe [-h] [-a ALBUM] [-A ARTIST] [-c CHAPTER] [-C] [-i ICON] [-n NAME] [-o OUTPUT] [-u URL] [-v] [-y YEAR]
To run using a GUI, run with no command line arguments

OPTIONS:
  -a, --album           <NAME>  Album name for folder and metadata.
  -A, --artist          <NAME>  Artist name for metadata.
  -c, --chapter         <NUM>   Chapter number for non-playlist downloads.
  -C, --set-chapters            Set chapters for metadata for items in playlists.
  -i, --icon            <PATH>  Path to ico/png/jpg/jpeg file to use as file icon/s
  -o, --output          <PATH>  Base output folder (default: downloads/audio or downloads/video).
  -u  --url             <URL>   URL for youtube video or playlist.
  -v, --video                   Download as MP4 instead of MP3.
  -y, --year            <YEAR>  Year to include in the metadata.
```

### GUI
To run using a GUI, run with no command line arguments. I made two versions of this because my friend liked the retro look.  

#### Retro
<img src="./assets/readme/ui_retro.png" width=400>

#### Updated
<img src="./assets/readme/ui_v1.png" width=500>

## Functionality
There are quite a few functions that the script can handle, most of them are optional. However, you will need to give a URL and filetype.

### Required
#### URL
The URL can be given for a single video, or for an entire playlist. The application will figure out which one you've given, so there's no need to have an option for it.  
Command line option: `-u <URL>` or `--url <URL>`  
<img src="./assets/readme/ui_url.png" width=400>

#### Filetype
You need to set if you want to download as MP3 (audio), or MP4 (video). In the GUI, you can select the filetype by clicking the different buttons for `Download MP3` or `Download MP4`. To download as MP4 in command-line, provide the `-v` or `--video` option. The command-line application will download as MP3 if no `video` flag is set.  
<img src="./assets/readme/ui_download.png" width=400>

### Optional - General
#### Output Directory
Where to download the MP3/MP4 file/s to. If not specified, will create a `downloads` directory and download into there, with subdirectories for `audio` or `video`. If a path is given, no additional subdirectories are created.  
Command line option: `-o <PATH>` or `--output <PATH>`  
<img src="./assets/readme/ui_directory.png" width=400>

#### Album
What to set the `album` metadata to. Also will group downloads into a subdirectory with the same name as the album - unless an output directory is specified.  
Command line option: `-a <NAME>` or `--album <NAME>`  
<img src="./assets/readme/ui_album.png" width=400>

#### Artist
What to set the `artist` metadata to.  
Command line option: `-A <NAME>` or `--artist <NAME>`  
<img src="./assets/readme/ui_artist.png" width=400>

#### Year
What to set the `year` metadata to.  
Command line option: `-y <YEAR>` or `--year <YEAR>`  
<img src="./assets/readme/ui_calendar.png" width=400>

#### Icon
Sets the icon for the files when shown in file explorer.  
Command line option: `-i <PATH>` or `--icon <PATH>`  
<img src="./assets/readme/ui_icon.png" width=400>

### Optional - Playlists
#### Set Chapters
Set this flag if you want to set the `track` metadata for each video in the playlist. i.e. first video is set as track 1, second as track 2, etc.  
Command line option: `-C` or `--set-chapters`  
<img src="./assets/readme/ui_playlist_chapter.png" width=400>

### Optional - Non-Playlists
#### Chapter
Sets the `track` metadata to the given number (0 to maxint).  
Command line option: `-c <NUM>` or `--chapter <NUM>`  
<img src="./assets/readme/ui_non-playlist_chapter.png" width=400>

### Other
#### Progress
Shows the progress of what you're downloading. Works with playlists (e.g. `3 of 20` / `6 or 10`), and also for non-playlists (e.g. `Downloading` / `Downloaded`).  
<img src="./assets/readme/ui_progress.png" width=400>

## Compilation
If you want to take the python code and build it in to an executable (useful if you wanna make some changes of your own), you can use PyInstaller - `pip install pyinstaller`. Here is a basic command you can use to compile:  

```bash
pyinstaller downloader.py --onefile --name YTDownloader --icon "./assets/heart.ico" --add-data "./assets/*;assets"
```

This will give you an executable called `YTDownloader.exe` and put it into the `dist` folder.

### PyInstaller Explanation
 - `--onefile`  
  Create an executable file
 - `--name`  
  Name to call the executable
 - `--icon`  
  Icon for executable (different to icon for window title, which is set during execution). Must be `.ico`.
 - `--add-data`  
  Add additional data into the executable. Here I'm taking the local `./assets/*` directory, and making it available to the excecutable via `assets`. If you wanna see how that works, look at `resource_path()` in the code.