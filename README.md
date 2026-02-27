# 🎬 jellyfin-rating-cover-burner

> **Automatically burn ratings from `.nfo` files into your media covers (`folder.jpg`) — as clean, visible text like `★ 8.7`.**

A lightweight **standalone Python script** (tested on **Windows**) that permanently embeds ratings into your media covers.  
You can **update**, **revert**, or **re‑run** it safely without damaging your originals.

---

## ⚙️ What it does

- 🔥 Burns ratings (from `.nfo`) directly onto posters  
- ♻️ Can restore the original artwork anytime  
- 🔄 Updates scores automatically if reused  
- 💾 Keeps backups (`folder_backup.jpg`, timestamped versions)

> ⚠️ **Important:**  
> Enable _“Save movie data to \*.nfo files”_ in your Jellyfin **library settings**  
> → the script needs it to read ratings!

<p align="center">
  <img width="1608" height="969" alt="screenshot" src="https://github.com/user-attachments/assets/a0fb6963-e2c1-484b-add6-9d0adea4b479" />
</p>

---

## ✨ Features

- 🧱 **Automatic backups** – `folder_backup.jpg` + timestamp copies  
- 🔍 **Change detection** – auto‑creates new clean backup if Jellyfin updates the poster  
- ♻️ **Revert function** – restore original covers anytime  
- 🌍 **Universal visibility** – ratings visible across **TVs, phones, Kodi, Plex, Emby** (burned into JPEG)  
- ⚡ **Flexible scope** – process a single folder **or entire library recursively**  
- 🛑 **Safe skips** – ignores folders without ratings  
- 🏷️ Choose between `<rating>` or `<criticrating>`

<p align="center">
  <img width="220" height="367" alt="Zrzut ekranu 2026-02-27 235752" src="https://github.com/user-attachments/assets/c12c8c95-f069-4882-bf52-a3f6043dd40f" />
</p>

---

## 🤝 Perfect companion

Works seamlessly with  
👉 [**jellyfin-imdb-rating-updater**](https://github.com/voc0der/jellyfin-imdb-rating-updater)

| Task | Tool |
|------|------|
| 📈 Fetch fresh IMDb ratings → save to `*.nfo` | `jellyfin-imdb-rating-updater` |
| 🖼️ Burn ratings into your covers | **`jellyfin-rating-cover-burner`** |

Together, they give your entire Jellyfin library clean, visually rated covers 🔥

---

## 📜 License

[MIT License](https://github.com/jakub-antos/jellyfin-rating-cover-burner/blob/main/LICENSE)
