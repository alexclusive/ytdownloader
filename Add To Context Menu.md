# How To Add Script Into Context Menu In File Explorer

## Add The Batch File To Regedit
You'll need two different scripts for this, they do the same thing, idk why they have to be different.  
These will also need to be put into different locations in regedit.
1. To be able to access via right-clicking a folder
     - `{Location}`:  
        ```mathematica
        HKEY_CLASSES_ROOT\Directory\shell
        ```
     - `{Script}`:  
        ```perl
        C:\path\to\YTDownloader.exe "%1"
        ```
        `%1` is the selected directory
2. To be able to access via right-clicking empty space in file explorer
     - `{Location}`:  
        ```mathematica
        HKEY_CLASSES_ROOT\Directory\Background\shell
        ```
     - `{Script}`:  
        ```perl
        C:\path\to\YTDownloader.exe "%V"
        ```
        `%V` is the current directory

 - Navigate to `{Location}`, and create a new key called `YTDownloader`
 - Inside the `YTDownloader` key, set the value of `(Default)` to `YTDownloader Here`
     - Put an `&` before the letter in `(Default)` that you want to be able to use as a shortcut.  
        e.g. `&YTDownloader Here` will allow you press `Y` when the context menu is open to run the script. Or `YT&Downloader Here` for `D`.
 - Inside the `YTDownloader` key, create a new `String Value` called `Icon` and set the value to the location of `heart.icon`
 - Create a subkey under `YTDownloader`, called `command`
 - Inside the `command` key, set the value of `(Default)` to `{Script}`

In the end, it should look like this:  
```
HKEY_CLASSES_ROOT
└── Directory
    └── Background
        └── shell
            └── YTDownloader
                └── command
    └── shell
        └── YTDownloader
            └── command
```
