# ☁ CloudPrep Organizer

A powerful, manual-control file organizer for preparing data before cloud upload.
Organize files by category and/or metadata before encrypting and uploading to your vault.

---

## 🚀 Quick Start

### 1. Install Python
Download Python 3.10+ from https://www.python.org/downloads/

### 2. Install Dependencies
Open a terminal/command prompt in this folder and run:
```
pip install -r requirements.txt
```

### 3. Run the App
```
python main.py
```

---

## 📋 How to Use

### Step 1 — Select Source
Click **Browse** next to Source Path and pick your drive or folder (e.g. D:\)

### Step 2 — Select Destination
Click **Browse** next to Destination and pick your Vault folder.

### Step 3 — Choose Categories
Check/uncheck the categories you want to organize in this session.
You don't have to do everything at once — just pick what you want today.

### Step 4 — Toggle Metadata (Optional)
Each category has a **"Organize by metadata"** switch:
- **Images** → sorts by Date Taken / Camera / GPS
- **Videos** → sorts by Year / Resolution
- **Audio** → sorts by Artist / Album

### Step 5 — Preview
Click **👁 Preview** to see exactly what will move and where — nothing is touched yet.

### Step 6 — Execute
Click **▶ Execute** to run the operation.
Choose **Copy (Safe)** to keep originals, or **Move** to relocate files.

---

## ⚙️ Settings
- **Conflict Resolution**: rename (default), skip, or overwrite duplicate files
- **Flat Output**: put all files in category root, no subfolders
- **Metadata Fallback**: folder name used when metadata is missing (default: "Unknown")

## ↩ Undo
Go to **↩ Undo Session** in the header to reverse any previous Move operation.
(Copy operations don't need undoing — originals are untouched.)

## 🗂 Manage Categories
Go to the **Manage Categories** tab to:
- Add your own custom categories
- Edit extensions for any existing category
- Delete categories you don't need

---

## 📁 Output Structure Example

**Extension mode (metadata off):**
```
Vault/
├── Images/
├── Videos/
├── Audio/
└── Documents/
```

**Metadata mode (Images by date, Audio by artist):**
```
Vault/
├── Images/
│   ├── 2019/
│   │   └── 03_March/
│   └── 2021/
├── Audio/
│   ├── Eminem/
│   │   └── Recovery/
│   └── Unknown/
└── Videos/
    ├── 2020/
    │   └── 1080p/
    └── 2021/
```

---

## 📦 Dependencies
- `customtkinter` — Modern GUI framework
- `Pillow` — Image EXIF metadata reading
- `mutagen` — Audio tag reading (MP3, M4A, FLAC, etc.)
- `pymediainfo` — Video metadata (resolution, codec, duration)
