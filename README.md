# jellyfin-rating-cover-burner
## What it does
Automatically burns ratings read from .nfo files into your media covers (folder.jpg) as text like ★ 8.7.

A standalone Python script (tested on Windows) that permanently embeds ratings into your media covers. It can also restore the original artwork, or update score on reuse.

⚠️ IMPORTANT: Enable "Save movie data to *.nfo files" in Jellyfin library settings! for script to scrape rating data.
<img width="1608" height="969" alt="screenshot" src="https://github.com/user-attachments/assets/a0fb6963-e2c1-484b-add6-9d0adea4b479" />

## Features
Backups folder_backup.jpg + timestamped copies

Change detection - auto-creates clean backup if Jellyfin updates to a new poster.

Revert function - restore original covers anytime - disable ratings.

Ratings visible on ALL devices - TVs, phones, Kodi, Plex, Emby (burned into JPEG)

Choose <rating> or <criticrating>

Single folder or recursive entire library

Skip folders without ratings (safe)

<img width="220" height="367" alt="Zrzut ekranu 2026-02-27 235752" src="https://github.com/user-attachments/assets/c12c8c95-f069-4882-bf52-a3f6043dd40f" />


## Perfect companion

**Works perfectly** with [jellyfin-imdb-rating-updater](https://github.com/voc0der/jellyfin-imdb-rating-updater) 
- Gets fresh IMDb ratings → saves to *.nfo
- This script = burns them into covers 🔥
