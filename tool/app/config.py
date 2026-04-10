"""
Configuration manager for CloudPrep Organizer.
Handles default categories, user config persistence, and session logs.
"""

import json
import os
from pathlib import Path

# App data directory (next to main.py)
APP_DIR = Path(__file__).parent.parent
CONFIG_FILE = APP_DIR / "config.json"
SESSION_LOG_DIR = APP_DIR / "session_logs"

DEFAULT_CATEGORIES = {
    "Images": {
        "icon": "🖼️",
        "enabled": True,
        "color": "#4ECDC4",
        "extensions": [
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff",
            ".tif", ".heic", ".heif", ".raw", ".cr2", ".nef", ".arw",
            ".svg", ".ico", ".psd", ".ai",
            ".jpg_128x96", ".jpg_240x320", ".jpg_320x240", ".jpeg_240x320"
        ],
        "metadata": {
            "enabled": False,
            "primary_field": "date_taken",
            "folder_structure": "year/month",
            "available_fields": ["date_taken", "camera_model", "gps_location", "resolution"]
        }
    },
    "Videos": {
        "icon": "🎬",
        "enabled": True,
        "color": "#FF6B6B",
        "extensions": [
            ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".3gp",
            ".3g2", ".m4v", ".webm", ".vob", ".mpg", ".mpeg", ".ts",
            ".mts", ".m2ts", ".f4v", ".rmvb", ".rm"
        ],
        "metadata": {
            "enabled": False,
            "primary_field": "date_created",
            "folder_structure": "year/resolution",
            "available_fields": ["date_created", "resolution", "duration", "codec"]
        }
    },
    "Audio": {
        "icon": "🎵",
        "enabled": True,
        "color": "#A855F7",
        "extensions": [
            ".mp3", ".m4a", ".wav", ".flac", ".aac", ".ogg", ".wma",
            ".amr", ".aiff", ".alac", ".opus", ".mid", ".midi"
        ],
        "metadata": {
            "enabled": False,
            "primary_field": "artist",
            "folder_structure": "artist/album",
            "available_fields": ["artist", "album", "year", "genre"]
        }
    },
    "Documents": {
        "icon": "📄",
        "enabled": True,
        "color": "#3B82F6",
        "extensions": [
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
            ".txt", ".rtf", ".odt", ".ods", ".odp", ".csv", ".md",
            ".htm", ".html", ".xml", ".json"
        ],
        "metadata": {
            "enabled": False,
            "primary_field": "date_modified",
            "folder_structure": "year",
            "available_fields": ["date_modified", "date_created"]
        }
    },
    "Archives": {
        "icon": "📦",
        "enabled": True,
        "color": "#F59E0B",
        "extensions": [
            ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
            ".tar.gz", ".tar.bz2", ".iso", ".dmg"
        ],
        "metadata": {
            "enabled": False,
            "primary_field": "date_modified",
            "folder_structure": "year",
            "available_fields": ["date_modified"]
        }
    },
    "Executables": {
        "icon": "⚙️",
        "enabled": True,
        "color": "#EF4444",
        "extensions": [
            ".exe", ".msi", ".apk", ".ipa", ".dmg", ".deb", ".rpm",
            ".sh", ".bat", ".cmd", ".ps1", ".crx", ".xpi"
        ],
        "metadata": {
            "enabled": False,
            "primary_field": "date_modified",
            "folder_structure": "year",
            "available_fields": ["date_modified"]
        }
    },
    "Junk_Cache": {
        "icon": "🗑️",
        "enabled": True,
        "color": "#6B7280",
        "extensions": [
            ".dthumb", ".crdownload", ".tmp", ".temp", ".cache",
            ".lnk", ".nomedia", ".ds_store", ".thumbs", ".ini",
            ".bup", ".ifo"
        ],
        "metadata": {
            "enabled": False,
            "primary_field": "date_modified",
            "folder_structure": "flat",
            "available_fields": ["date_modified"]
        }
    },
    "Database_System": {
        "icon": "🗄️",
        "enabled": True,
        "color": "#10B981",
        "extensions": [
            ".db", ".sqlite", ".sqlite3", ".mdb", ".accdb",
            ".dat", ".log", ".bak", ".sql"
        ],
        "metadata": {
            "enabled": False,
            "primary_field": "date_modified",
            "folder_structure": "flat",
            "available_fields": ["date_modified"]
        }
    }
}


def load_config():
    """Load config from file, or return defaults if not found."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Merge with defaults to handle new categories added in updates
            merged = {**DEFAULT_CATEGORIES}
            merged.update(data.get("categories", {}))
            return {"categories": merged, "settings": data.get("settings", default_settings())}
        except Exception:
            pass
    return {"categories": dict(DEFAULT_CATEGORIES), "settings": default_settings()}


def save_config(config: dict):
    """Persist config to disk."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def default_settings():
    return {
        "operation_mode": "copy",       # "copy" or "move"
        "conflict_resolution": "rename", # "rename", "skip", "overwrite"
        "flat_output": False,            # True = no subfolders per category
        "metadata_fallback": "Unknown",  # Folder name when metadata missing
        "last_source": "",
        "last_destination": ""
    }


def ensure_session_log_dir():
    SESSION_LOG_DIR.mkdir(exist_ok=True)
    return SESSION_LOG_DIR
