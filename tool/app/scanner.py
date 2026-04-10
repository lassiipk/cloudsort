"""
Scanner module — recursively scans source paths and extracts file metadata.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import threading


def get_extension(filepath: Path) -> str:
    """Get lowercased extension, handling multi-dot names like .tar.gz"""
    name = filepath.name.lower()
    # Check for compound extensions
    for compound in [".tar.gz", ".tar.bz2", ".tar.xz"]:
        if name.endswith(compound):
            return compound
    suffix = filepath.suffix.lower()
    # Handle weird thumb extensions like .jpg_128x96
    if not suffix:
        parts = name.split(".")
        if len(parts) > 1:
            return "." + parts[-1]
    return suffix


def categorize_file(ext: str, categories: dict) -> Optional[str]:
    """Return the category name for a given extension, or None if uncategorized."""
    ext_lower = ext.lower()
    for cat_name, cat_data in categories.items():
        if ext_lower in [e.lower() for e in cat_data.get("extensions", [])]:
            return cat_name
    return None


def extract_image_metadata(filepath: Path) -> dict:
    """Extract EXIF metadata from image files."""
    meta = {"date_taken": None, "camera_model": None, "resolution": None, "gps_location": None}
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS
        img = Image.open(filepath)
        meta["resolution"] = f"{img.width}x{img.height}"
        exif_data = img._getexif()
        if exif_data:
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == "DateTimeOriginal" and value:
                    try:
                        dt = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                        meta["date_taken"] = dt
                    except Exception:
                        pass
                elif tag == "Model" and value:
                    meta["camera_model"] = str(value).strip()
                elif tag == "GPSInfo" and value:
                    gps = {}
                    for gps_tag_id, gps_val in value.items():
                        gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                        gps[gps_tag] = gps_val
                    lat = _convert_gps(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef"))
                    lon = _convert_gps(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef"))
                    if lat and lon:
                        meta["gps_location"] = f"{lat:.4f},{lon:.4f}"
    except Exception:
        pass
    return meta


def _convert_gps(coord, ref) -> Optional[float]:
    try:
        d, m, s = coord
        val = float(d) + float(m) / 60 + float(s) / 3600
        if ref in ["S", "W"]:
            val = -val
        return val
    except Exception:
        return None


def extract_audio_metadata(filepath: Path) -> dict:
    """Extract ID3/audio metadata using mutagen."""
    meta = {"artist": None, "album": None, "year": None, "genre": None}
    try:
        from mutagen import File as MutagenFile
        audio = MutagenFile(filepath, easy=True)
        if audio:
            meta["artist"] = _first(audio.get("artist"))
            meta["album"] = _first(audio.get("album"))
            meta["genre"] = _first(audio.get("genre"))
            year_raw = _first(audio.get("date") or audio.get("year"))
            if year_raw:
                meta["year"] = str(year_raw)[:4]
    except Exception:
        pass
    return meta


def extract_video_metadata(filepath: Path) -> dict:
    """Extract video metadata using pymediainfo or fallback to file dates."""
    meta = {"date_created": None, "resolution": None, "duration": None, "codec": None}
    try:
        from pymediainfo import MediaInfo
        info = MediaInfo.parse(filepath)
        for track in info.tracks:
            if track.track_type == "Video":
                if track.width and track.height:
                    h = int(track.height)
                    if h >= 2160:
                        meta["resolution"] = "4K"
                    elif h >= 1080:
                        meta["resolution"] = "1080p"
                    elif h >= 720:
                        meta["resolution"] = "720p"
                    elif h >= 480:
                        meta["resolution"] = "480p"
                    else:
                        meta["resolution"] = f"{track.width}x{track.height}"
                if track.codec_id:
                    meta["codec"] = str(track.codec_id)
                if track.duration:
                    secs = int(float(track.duration)) // 1000
                    meta["duration"] = f"{secs // 60}m{secs % 60}s"
                if track.encoded_date:
                    try:
                        dt_str = str(track.encoded_date).replace("UTC ", "")
                        meta["date_created"] = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        pass
    except Exception:
        pass
    return meta


def extract_file_metadata(filepath: Path, category: str) -> dict:
    """Route to correct metadata extractor based on category."""
    stat = filepath.stat()
    base = {
        "date_modified": datetime.fromtimestamp(stat.st_mtime),
        "date_created": datetime.fromtimestamp(stat.st_ctime),
        "size": stat.st_size
    }
    if category == "Images":
        base.update(extract_image_metadata(filepath))
    elif category == "Audio":
        base.update(extract_audio_metadata(filepath))
    elif category == "Videos":
        base.update(extract_video_metadata(filepath))
    return base


def _first(val):
    """Get first item from list or return value directly."""
    if isinstance(val, (list, tuple)) and val:
        return val[0]
    return val


def build_metadata_folder(meta: dict, category: str, cat_config: dict, fallback: str = "Unknown") -> str:
    """Build a folder path string from metadata based on category config."""
    structure = cat_config.get("metadata", {}).get("folder_structure", "flat")
    primary = cat_config.get("metadata", {}).get("primary_field", "date_modified")

    def safe(val, fb=fallback):
        if val is None:
            return fb
        if isinstance(val, datetime):
            return str(val.year)
        s = str(val).strip()
        # Sanitize folder name
        for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
            s = s.replace(ch, "_")
        return s if s else fb

    if category == "Audio":
        artist = safe(meta.get("artist"))
        album = safe(meta.get("album"))
        if structure == "artist/album":
            return os.path.join(artist, album)
        elif structure == "artist":
            return artist
        else:
            return safe(meta.get(primary))

    elif category in ("Images", "Videos", "Documents"):
        date_val = meta.get("date_taken") or meta.get("date_created") or meta.get("date_modified")
        year = safe(date_val)
        month = date_val.strftime("%m_%B") if isinstance(date_val, datetime) else fallback

        if structure == "year/month":
            return os.path.join(year, month)
        elif structure == "year/resolution":
            res = safe(meta.get("resolution"))
            return os.path.join(year, res)
        elif structure == "year":
            return year
        else:
            return safe(meta.get(primary, date_val))

    else:
        return safe(meta.get(primary) or meta.get("date_modified"))


class Scanner:
    """Scans source directory and builds a file manifest."""

    def __init__(self, source_path: str, categories: dict,
                 excluded_folders: List[str] = None,
                 progress_callback=None, done_callback=None):
        self.source = Path(source_path)
        self.categories = categories
        self.excluded = [f.lower() for f in (excluded_folders or [])]
        self.progress_callback = progress_callback
        self.done_callback = done_callback
        self._stop = False

    def stop(self):
        self._stop = True

    def scan(self) -> Dict:
        """
        Returns a dict:
        {
          category_name: [
            { path, size, ext, metadata_available, metadata }, ...
          ]
        }
        Plus "Uncategorized" key for unmatched files.
        """
        result = {cat: [] for cat in self.categories}
        result["Uncategorized"] = []

        all_files = []
        for root, dirs, files in os.walk(self.source):
            if self._stop:
                break
            # Filter excluded folders
            dirs[:] = [d for d in dirs if d.lower() not in self.excluded]
            for f in files:
                all_files.append(Path(root) / f)

        total = len(all_files)
        for i, filepath in enumerate(all_files):
            if self._stop:
                break
            if self.progress_callback:
                self.progress_callback(i + 1, total, str(filepath.name))

            ext = get_extension(filepath)
            cat = categorize_file(ext, self.categories)

            try:
                size = filepath.stat().st_size
            except Exception:
                size = 0

            entry = {
                "path": str(filepath),
                "name": filepath.name,
                "ext": ext,
                "size": size,
                "category": cat or "Uncategorized",
                "metadata": {}
            }

            if cat:
                result[cat].append(entry)
            else:
                result["Uncategorized"].append(entry)

        if self.done_callback:
            self.done_callback(result)
        return result

    def scan_threaded(self):
        """Run scan in a background thread."""
        t = threading.Thread(target=self.scan, daemon=True)
        t.start()
        return t
