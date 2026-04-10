# ☁️ CloudPrep Organizer

> Organize files by category and metadata before encrypting and uploading to cloud storage.

Built for people who want full control over how their files are sorted before a cloud backup — not an auto-sorter that does everything at once, but a manual, session-based tool you run on your own terms.

---

## Features

- **Pick any source** — a drive (D:\), folder, or path
- **Choose categories per session** — Images today, Videos tomorrow, no need to do it all at once
- **Metadata organization** — sort Images by date taken, Audio by artist/album, Videos by resolution (toggle per category, off by default)
- **Preview before anything moves** — full dry-run showing every file's destination
- **Copy or Move** — copy first to verify, move when confident
- **Conflict resolution** — rename duplicates automatically, never silent overwrite
- **Undo** — every Move session is logged and fully reversible
- **Custom categories** — add, edit, or delete categories and their extensions anytime
- **Config persists** — your categories and settings are saved to `config.json`

---

## Setup

**Requirements:** Python 3.10+

```bash
pip install -r requirements.txt
python main.py
```

---

## How It Works

```
① Select Source      →  Pick your drive or folder (e.g. D:\)
② Select Destination →  Pick your Vault / output folder
③ Pick Categories    →  Check only what you want this session
④ Toggle Metadata    →  Optional: sort by date, artist, resolution, etc.
⑤ Preview & Plan     →  See exactly what will move and where
⑥ Start Transfer     →  Copy or Move with live progress log
```

---

## Output Structure

**Default (extension-based):**
```
Vault/
├── Images/
├── Videos/
├── Audio/
└── Documents/
```

**With metadata on:**
```
Vault/
├── Images/
│   ├── 2021/03_March/
│   └── 2019/08_August/
├── Audio/
│   └── Eminem/Recovery/
└── Videos/
    └── 2022/1080p/
```

---

## File Structure

```
CloudPrep/
├── main.py           ← Entry point
├── requirements.txt
└── app/
    ├── config.py     ← Categories, defaults, persistence
    ├── scanner.py    ← File scanner + metadata extractor
    ├── mover.py      ← Copy/move engine + undo system
    └── gui.py        ← CustomTkinter GUI
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `customtkinter` | Modern dark-theme GUI |
| `Pillow` | Image EXIF metadata (date, camera, GPS) |
| `mutagen` | Audio tags (artist, album, year, genre) |
| `pymediainfo` | Video metadata (resolution, codec, duration) |
