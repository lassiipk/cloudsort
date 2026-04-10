"""
Mover engine — handles copy/move operations, conflict resolution, and session logging.
"""

import os
import shutil
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Callable, Optional

from app.config import ensure_session_log_dir
from app.scanner import extract_file_metadata, build_metadata_folder


class MoveEngine:
    """
    Handles the actual file operations.
    Supports: copy, move, dry-run, undo.
    """

    def __init__(self,
                 destination: str,
                 categories: dict,
                 settings: dict,
                 progress_callback: Callable = None,
                 log_callback: Callable = None,
                 done_callback: Callable = None):
        self.destination = Path(destination)
        self.categories = categories
        self.settings = settings
        self.progress_cb = progress_callback
        self.log_cb = log_callback
        self.done_cb = done_callback
        self._stop = False
        self._session_log = []

    def stop(self):
        self._stop = True

    def _log(self, msg: str, level: str = "INFO"):
        entry = {"time": datetime.now().isoformat(), "level": level, "msg": msg}
        self._session_log.append(entry)
        if self.log_cb:
            self.log_cb(f"[{level}] {msg}")

    def _resolve_conflict(self, dest_path: Path) -> Path:
        """Handle filename conflicts based on settings."""
        mode = self.settings.get("conflict_resolution", "rename")
        if not dest_path.exists():
            return dest_path
        if mode == "skip":
            return None
        if mode == "overwrite":
            return dest_path
        # rename: add _1, _2, etc.
        stem = dest_path.stem
        suffix = dest_path.suffix
        parent = dest_path.parent
        counter = 1
        while True:
            new_path = parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1

    def build_dest_path(self, entry: dict, dry_run: bool = False) -> Optional[Path]:
        """Compute the destination path for a single file entry."""
        cat = entry["category"]
        cat_config = self.categories.get(cat, {})
        use_metadata = cat_config.get("metadata", {}).get("enabled", False)
        fallback = self.settings.get("metadata_fallback", "Unknown")
        flat = self.settings.get("flat_output", False)

        # Build subfolder
        if flat:
            subfolder = Path(cat)
        elif use_metadata:
            # Extract metadata now for destination computation
            filepath = Path(entry["path"])
            meta = extract_file_metadata(filepath, cat)
            entry["metadata"] = meta
            meta_folder = build_metadata_folder(meta, cat, cat_config, fallback)
            subfolder = Path(cat) / meta_folder
        else:
            subfolder = Path(cat)

        dest_folder = self.destination / subfolder
        if not dry_run:
            dest_folder.mkdir(parents=True, exist_ok=True)

        return dest_folder / entry["name"]

    def preview(self, file_entries: List[dict]) -> List[dict]:
        """
        Dry run — compute destinations without touching files.
        Returns list of {src, dest, action, conflict}.
        """
        results = []
        for entry in file_entries:
            dest = self.build_dest_path(entry, dry_run=True)
            if dest is None:
                continue
            conflict = dest.exists()
            resolved = self._resolve_conflict(dest) if conflict else dest
            action = "skip" if resolved is None else self.settings.get("operation_mode", "copy")
            results.append({
                "src": entry["path"],
                "dest": str(resolved) if resolved else "SKIP",
                "action": action,
                "size": entry["size"],
                "conflict": conflict,
                "category": entry["category"]
            })
        return results

    def execute(self, file_entries: List[dict]):
        """Run the actual file operation in the calling thread."""
        total = len(file_entries)
        success = 0
        skipped = 0
        errors = 0
        mode = self.settings.get("operation_mode", "copy")

        for i, entry in enumerate(file_entries):
            if self._stop:
                self._log("Operation cancelled by user.", "WARN")
                break

            src = Path(entry["path"])
            if self.progress_cb:
                self.progress_cb(i + 1, total, src.name)

            try:
                dest = self.build_dest_path(entry)
                if dest is None:
                    self._log(f"SKIP (no dest): {src.name}", "SKIP")
                    skipped += 1
                    continue

                resolved = self._resolve_conflict(dest)
                if resolved is None:
                    self._log(f"SKIP (conflict): {src.name}", "SKIP")
                    skipped += 1
                    continue

                if mode == "copy":
                    shutil.copy2(str(src), str(resolved))
                else:
                    shutil.move(str(src), str(resolved))

                self._session_log.append({
                    "time": datetime.now().isoformat(),
                    "action": mode,
                    "src": str(src),
                    "dest": str(resolved),
                    "category": entry["category"]
                })
                self._log(f"{mode.upper()}: {src.name} → {resolved.parent.name}/", "OK")
                success += 1

            except Exception as e:
                self._log(f"ERROR: {src.name} — {e}", "ERROR")
                errors += 1

        self._save_session_log()
        summary = {"success": success, "skipped": skipped, "errors": errors, "total": total}
        self._log(
            f"Done — {success} {'copied' if mode == 'copy' else 'moved'}, "
            f"{skipped} skipped, {errors} errors.", "DONE"
        )
        if self.done_cb:
            self.done_cb(summary)

    def execute_threaded(self, file_entries: List[dict]):
        t = threading.Thread(target=self.execute, args=(file_entries,), daemon=True)
        t.start()
        return t

    def _save_session_log(self):
        """Save session log to disk for undo capability."""
        log_dir = ensure_session_log_dir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"session_{ts}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(self._session_log, f, indent=2)
        self._log(f"Session log saved: {log_file.name}", "INFO")
        return log_file

    @staticmethod
    def undo_session(log_file: str, log_callback: Callable = None) -> dict:
        """
        Reverse a previous session by reading its log file.
        Only works for 'move' operations (copy leaves originals intact).
        """
        success = 0
        errors = 0
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except Exception as e:
            if log_callback:
                log_callback(f"[ERROR] Cannot read log: {e}")
            return {"success": 0, "errors": 1}

        for entry in entries:
            if entry.get("action") != "move":
                continue
            src = Path(entry["dest"])
            dst = Path(entry["src"])
            try:
                if src.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(dst))
                    if log_callback:
                        log_callback(f"[UNDO] {src.name} → {dst.parent.name}/")
                    success += 1
                else:
                    if log_callback:
                        log_callback(f"[SKIP] File no longer exists: {src.name}")
            except Exception as e:
                if log_callback:
                    log_callback(f"[ERROR] {src.name}: {e}")
                errors += 1

        return {"success": success, "errors": errors}
