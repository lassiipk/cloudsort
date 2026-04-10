"""
CloudPrep Organizer — Main GUI
Built with CustomTkinter for a modern, clean desktop UI.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from app.config import load_config, save_config, DEFAULT_CATEGORIES
from app.scanner import Scanner
from app.mover import MoveEngine


# ─── Theme ────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

DARK_BG     = "#0F1117"
PANEL_BG    = "#1A1D27"
CARD_BG     = "#22263A"
BORDER      = "#2E3350"
ACCENT      = "#5B8CFF"
ACCENT2     = "#4ECDC4"
TEXT        = "#E8ECF4"
TEXT_DIM    = "#7B82A0"
SUCCESS     = "#4ADE80"
WARNING     = "#FBBF24"
ERROR_COL   = "#F87171"
FONT_MAIN   = ("Segoe UI", 13)
FONT_BOLD   = ("Segoe UI", 13, "bold")
FONT_TITLE  = ("Segoe UI", 20, "bold")
FONT_SMALL  = ("Segoe UI", 11)
FONT_MONO   = ("Consolas", 11)


def fmt_size(b: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


class CloudPrepApp:
    def __init__(self):
        self.config = load_config()
        self.categories = self.config["categories"]
        self.settings = self.config["settings"]

        self.scan_result: Dict = {}
        self.selected_files: List[dict] = []
        self.preview_result: List[dict] = []

        self.root = ctk.CTk()
        self.root.title("CloudPrep Organizer")
        self.root.geometry("1280x820")
        self.root.resizable(False, False)
        self.root.configure(fg_color=DARK_BG)

        self._build_ui()

    def run(self):
        self.root.mainloop()

    # ──────────────────────────────────────────────────────────────────────────
    # UI CONSTRUCTION
    # ──────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        self._build_header()
        # Main layout: left sidebar + right content
        main = ctk.CTkFrame(self.root, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        main.columnconfigure(0, weight=0, minsize=320)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # Left panel
        left = ctk.CTkFrame(main, fg_color=PANEL_BG, corner_radius=12,
                            border_width=1, border_color=BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._build_left_panel(left)

        # Right panel (tabbed)
        right = ctk.CTkFrame(main, fg_color=PANEL_BG, corner_radius=12,
                             border_width=1, border_color=BORDER)
        right.grid(row=0, column=1, sticky="nsew")
        self._build_right_panel(right)

    def _build_header(self):
        hdr = ctk.CTkFrame(self.root, fg_color=PANEL_BG, corner_radius=0, height=64,
                           border_width=1, border_color=BORDER)
        hdr.pack(fill="x", padx=0, pady=0)
        hdr.pack_propagate(False)

        inner = ctk.CTkFrame(hdr, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20)

        ctk.CTkLabel(inner, text="☁  CloudPrep Organizer",
                     font=FONT_TITLE, text_color=TEXT).pack(side="left", pady=16)

        ctk.CTkLabel(inner, text="Organize · Encrypt · Upload",
                     font=FONT_SMALL, text_color=TEXT_DIM).pack(side="left", padx=16, pady=16)

        # Top-right buttons
        btn_frame = ctk.CTkFrame(inner, fg_color="transparent")
        btn_frame.pack(side="right", pady=12)

        ctk.CTkButton(btn_frame, text="⚙ Settings", width=100, height=32,
                      font=FONT_SMALL, fg_color=CARD_BG, hover_color=BORDER,
                      command=self._open_settings).pack(side="left", padx=4)

        ctk.CTkButton(btn_frame, text="↩ Undo Session", width=120, height=32,
                      font=FONT_SMALL, fg_color=CARD_BG, hover_color=BORDER,
                      command=self._open_undo).pack(side="left", padx=4)

    def _build_left_panel(self, parent):
        parent.columnconfigure(0, weight=1)

        # ── Source ────────────────────────────────────────────────────────
        self._section_label(parent, "① Source Path")

        src_frame = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=8)
        src_frame.pack(fill="x", padx=12, pady=(0, 10))
        src_frame.columnconfigure(0, weight=1)

        self.src_var = tk.StringVar(value=self.settings.get("last_source", ""))
        src_entry = ctk.CTkEntry(src_frame, textvariable=self.src_var, height=36,
                                 font=FONT_SMALL, fg_color=DARK_BG, border_color=BORDER,
                                 placeholder_text="Select source folder or drive…")
        src_entry.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        ctk.CTkButton(src_frame, text="Browse", width=70, height=28,
                      font=FONT_SMALL, fg_color=ACCENT, hover_color="#4070E0",
                      command=self._browse_source).grid(row=0, column=1, padx=(0, 8), pady=8)

        self.btn_scan = ctk.CTkButton(parent, text="🔍  Scan Source", height=38,
                                      font=FONT_BOLD, fg_color=ACCENT, hover_color="#4070E0",
                                      command=self._start_scan)
        self.btn_scan.pack(fill="x", padx=12, pady=(0, 12))

        # ── Destination ────────────────────────────────────────────────────
        self._section_label(parent, "② Destination (Vault)")

        dst_frame = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=8)
        dst_frame.pack(fill="x", padx=12, pady=(0, 12))
        dst_frame.columnconfigure(0, weight=1)

        self.dst_var = tk.StringVar(value=self.settings.get("last_destination", ""))
        dst_entry = ctk.CTkEntry(dst_frame, textvariable=self.dst_var, height=36,
                                 font=FONT_SMALL, fg_color=DARK_BG, border_color=BORDER,
                                 placeholder_text="Select destination folder…")
        dst_entry.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        ctk.CTkButton(dst_frame, text="Browse", width=70, height=28,
                      font=FONT_SMALL, fg_color=ACCENT2, hover_color="#3AB0A8",
                      command=self._browse_dest).grid(row=0, column=1, padx=(0, 8), pady=8)

        # ── Operation Mode ─────────────────────────────────────────────────
        self._section_label(parent, "③ Operation Mode")

        mode_frame = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=8)
        mode_frame.pack(fill="x", padx=12, pady=(0, 12))

        self.op_mode = tk.StringVar(value=self.settings.get("operation_mode", "copy"))
        modes = [("📋  Copy (Safe)", "copy"), ("✂️  Move", "move")]
        for label, val in modes:
            ctk.CTkRadioButton(mode_frame, text=label, variable=self.op_mode, value=val,
                               font=FONT_SMALL, text_color=TEXT,
                               fg_color=ACCENT).pack(anchor="w", padx=12, pady=6)

        # ── Category Selection ─────────────────────────────────────────────
        self._section_label(parent, "④ Categories")

        cat_scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                            label_text="", height=260)
        cat_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.cat_vars = {}
        self.meta_vars = {}
        self.cat_frames = {}

        for cat_name, cat_data in self.categories.items():
            self._build_category_row(cat_scroll, cat_name, cat_data)

        # ── Action Buttons ─────────────────────────────────────────────────
        sep = ctk.CTkFrame(parent, fg_color=BORDER, height=1)
        sep.pack(fill="x", padx=12, pady=8)

        self.btn_preview = ctk.CTkButton(parent, text="👁  Preview & Plan", height=42,
                                         font=FONT_BOLD, fg_color=ACCENT,
                                         hover_color="#4070E0", text_color=TEXT,
                                         command=self._run_preview, state="disabled")
        self.btn_preview.pack(fill="x", padx=12, pady=(0, 12))

    def _build_category_row(self, parent, cat_name, cat_data):
        frame = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=8)
        frame.pack(fill="x", pady=3)
        self.cat_frames[cat_name] = frame

        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(6, 2))
        top.columnconfigure(1, weight=1)

        # Checkbox
        var = tk.BooleanVar(value=cat_data.get("enabled", True))
        self.cat_vars[cat_name] = var
        cb = ctk.CTkCheckBox(top, text="", variable=var, width=20,
                             fg_color=ACCENT, hover_color="#4070E0",
                             command=lambda c=cat_name: self._on_cat_toggle(c))
        cb.grid(row=0, column=0, padx=(0, 6))

        # Icon + Name
        color = cat_data.get("color", ACCENT)
        icon = cat_data.get("icon", "📁")
        ctk.CTkLabel(top, text=f"{icon}  {cat_name}",
                     font=FONT_BOLD, text_color=color).grid(row=0, column=1, sticky="w")

        # File count badge (updated after scan)
        self.cat_frames[f"{cat_name}_count"] = ctk.CTkLabel(
            top, text="—", font=FONT_SMALL, text_color=TEXT_DIM)
        self.cat_frames[f"{cat_name}_count"].grid(row=0, column=2, padx=4)

        # Metadata toggle
        has_meta = "metadata" in cat_data
        if has_meta:
            meta_var = tk.BooleanVar(value=cat_data["metadata"].get("enabled", False))
            self.meta_vars[cat_name] = meta_var

            meta_row = ctk.CTkFrame(frame, fg_color="transparent")
            meta_row.pack(fill="x", padx=24, pady=(0, 6))

            ctk.CTkSwitch(meta_row, text="Organize by metadata",
                          variable=meta_var, font=FONT_SMALL,
                          text_color=TEXT_DIM, fg_color=BORDER,
                          progress_color=ACCENT2,
                          command=lambda c=cat_name, v=meta_var: self._on_meta_toggle(c, v)
                          ).pack(side="left")

    def _build_right_panel(self, parent):
        parent.pack_propagate(True)
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        self.tab_view = ctk.CTkTabview(parent, fg_color="transparent",
                                       segmented_button_fg_color=CARD_BG,
                                       segmented_button_selected_color=ACCENT,
                                       segmented_button_selected_hover_color="#4070E0",
                                       segmented_button_unselected_color=CARD_BG,
                                       text_color=TEXT)
        self.tab_view.pack(fill="both", expand=True, padx=12, pady=12)

        self.tab_view.add("📊  Scan Results")
        self.tab_view.add("👁  Preview")
        self.tab_view.add("📋  Operation Log")
        self.tab_view.add("🗂  Manage Categories")

        self._build_scan_tab(self.tab_view.tab("📊  Scan Results"))
        self._build_preview_tab(self.tab_view.tab("👁  Preview"))
        self._build_log_tab(self.tab_view.tab("📋  Operation Log"))
        self._build_categories_tab(self.tab_view.tab("🗂  Manage Categories"))

    def _build_scan_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        # Progress bar
        self.scan_progress_var = tk.DoubleVar(value=0)
        self.scan_status_var = tk.StringVar(value="Select a source folder and click Scan.")
        ctk.CTkLabel(parent, textvariable=self.scan_status_var,
                     font=FONT_SMALL, text_color=TEXT_DIM).pack(fill="x", pady=(4, 2))
        self.scan_progress = ctk.CTkProgressBar(parent, variable=self.scan_progress_var,
                                                fg_color=CARD_BG, progress_color=ACCENT)
        self.scan_progress.pack(fill="x", padx=8, pady=(0, 8))

        # Summary cards
        self.summary_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.summary_frame.pack(fill="both", expand=True)
        self._draw_empty_summary()

    def _draw_empty_summary(self):
        for w in self.summary_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.summary_frame,
                     text="No scan results yet.\nSelect a source and click Scan.",
                     font=FONT_MAIN, text_color=TEXT_DIM).pack(pady=40)

    def _draw_summary(self, scan_result):
        for w in self.summary_frame.winfo_children():
            w.destroy()

        total_files = sum(len(v) for v in scan_result.values())
        total_size  = sum(e["size"] for v in scan_result.values() for e in v)

        # ── Total banner ──────────────────────────────────────────────────
        banner = ctk.CTkFrame(self.summary_frame, fg_color=CARD_BG, corner_radius=10,
                              border_width=1, border_color=ACCENT)
        banner.pack(fill="x", padx=4, pady=(4, 10))
        ctk.CTkLabel(banner,
                     text=f"✅  Scan Complete  —  {total_files:,} files  |  {fmt_size(total_size)}",
                     font=FONT_BOLD, text_color=ACCENT).pack(side="left", padx=16, pady=10)
        ctk.CTkLabel(banner,
                     text="Checkboxes on the left control which categories get transferred.",
                     font=FONT_SMALL, text_color=TEXT_DIM).pack(side="left", padx=4, pady=10)

        # ── Per-category cards (ALL categories, including Uncategorized) ──
        cols = 3
        grid = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=4)
        for i in range(cols):
            grid.columnconfigure(i, weight=1)

        # Sort: known categories first, Uncategorized last
        known   = [(k, v) for k, v in scan_result.items() if k != "Uncategorized" and v]
        unknown = [(k, v) for k, v in scan_result.items() if k == "Uncategorized" and v]
        items   = known + unknown

        if not items:
            ctk.CTkLabel(self.summary_frame,
                         text="No files found in source folder.",
                         font=FONT_MAIN, text_color=TEXT_DIM).pack(pady=20)
            return

        for idx, (cat, entries) in enumerate(items):
            row_idx, col = divmod(idx, cols)
            cat_data = self.categories.get(cat, {})
            color    = cat_data.get("color", TEXT_DIM) if cat != "Uncategorized" else WARNING
            icon     = cat_data.get("icon",  "📁")      if cat != "Uncategorized" else "❓"
            count    = len(entries)
            size     = sum(e["size"] for e in entries)

            # Highlight whether this category is checked or not
            is_active = self.cat_vars.get(cat, tk.BooleanVar(value=False)).get()
            border_col = color if is_active else BORDER

            card = ctk.CTkFrame(grid, fg_color=CARD_BG, corner_radius=10,
                                border_width=2, border_color=border_col)
            card.grid(row=row_idx, column=col, padx=4, pady=4, sticky="ew")

            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=12, pady=(10, 0))
            ctk.CTkLabel(top_row, text=f"{icon}  {cat}",
                         font=FONT_BOLD, text_color=color).pack(side="left")
            status = "✓ selected" if is_active else "— skipped"
            status_col = SUCCESS if is_active else TEXT_DIM
            ctk.CTkLabel(top_row, text=status,
                         font=FONT_SMALL, text_color=status_col).pack(side="right")

            ctk.CTkLabel(card, text=f"{count:,} files",
                         font=FONT_MAIN, text_color=TEXT).pack(anchor="w", padx=12, pady=(2, 0))
            ctk.CTkLabel(card, text=fmt_size(size),
                         font=FONT_SMALL, text_color=TEXT_DIM).pack(anchor="w", padx=12, pady=(0, 10))

            # Update sidebar badge
            label = self.cat_frames.get(f"{cat}_count")
            if label:
                label.configure(text=f"{count:,}")

    def _build_preview_tab(self, parent):
        # Top bar: summary + execute button
        top_bar = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=8)
        top_bar.pack(fill="x", padx=4, pady=(4, 6))
        top_bar.columnconfigure(0, weight=1)

        self.preview_summary_var = tk.StringVar(value="Run a preview to see the full operation plan before anything is moved.")
        ctk.CTkLabel(top_bar, textvariable=self.preview_summary_var,
                     font=FONT_SMALL, text_color=TEXT_DIM).grid(row=0, column=0, sticky="w", padx=12, pady=10)

        self.btn_execute = ctk.CTkButton(top_bar, text="▶  Start Transfer", width=160, height=36,
                                         font=FONT_BOLD, fg_color=SUCCESS,
                                         hover_color="#22C55E", text_color=DARK_BG,
                                         command=self._run_execute, state="disabled")
        self.btn_execute.grid(row=0, column=1, padx=12, pady=8)

        # Fixed-width column header using a canvas-based approach
        COL_WIDTHS = [280, 260, 80, 80]
        COL_NAMES  = ["File", "Destination", "Action", "Size"]

        hdr_frame = ctk.CTkFrame(parent, fg_color=BORDER, corner_radius=6, height=30)
        hdr_frame.pack(fill="x", padx=4, pady=(0, 2))
        hdr_frame.pack_propagate(False)

        x = 8
        for name, w in zip(COL_NAMES, COL_WIDTHS):
            lbl = ctk.CTkLabel(hdr_frame, text=name, font=FONT_BOLD,
                               text_color=TEXT_DIM, width=w, anchor="w")
            lbl.place(x=x, y=4)
            x += w

        # Scrollable body
        self.preview_tree_frame = ctk.CTkScrollableFrame(parent, fg_color=CARD_BG, corner_radius=8)
        self.preview_tree_frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self._COL_WIDTHS = COL_WIDTHS
        self._draw_preview_placeholder()

    def _draw_preview_placeholder(self):
        for w in self.preview_tree_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.preview_tree_frame,
                     text="No preview yet.\nRun a scan, then click  👁 Preview & Plan.",
                     font=FONT_MAIN, text_color=TEXT_DIM).pack(pady=40)

    def _draw_preview(self, preview: list):
        for w in self.preview_tree_frame.winfo_children():
            w.destroy()

        action_colors = {"copy": ACCENT, "move": WARNING, "skip": TEXT_DIM}
        COL_WIDTHS = self._COL_WIDTHS

        for i, item in enumerate(preview[:500]):
            bg = CARD_BG if i % 2 == 0 else "#1E2235"
            row_frame = ctk.CTkFrame(self.preview_tree_frame, fg_color=bg,
                                     corner_radius=0, height=26)
            row_frame.pack(fill="x", pady=0)
            row_frame.pack_propagate(False)

            src_name = Path(item["src"]).name
            dest_short = (Path(item["dest"]).parent.name + "/") if item["dest"] != "SKIP" else "SKIP"
            action = item["action"]
            color = action_colors.get(action, TEXT)

            values = [src_name, dest_short, action.upper(), fmt_size(item["size"])]
            txt_colors = [TEXT, TEXT_DIM, color, TEXT_DIM]

            x = 8
            for val, w, tc in zip(values, COL_WIDTHS, txt_colors):
                ctk.CTkLabel(row_frame, text=val, font=FONT_MONO,
                             text_color=tc, width=w - 16, anchor="w").place(x=x, y=3)
                x += w

        if len(preview) > 500:
            ctk.CTkLabel(self.preview_tree_frame,
                         text=f"… and {len(preview) - 500:,} more files (showing first 500)",
                         font=FONT_SMALL, text_color=TEXT_DIM).pack(pady=8)

    def _build_log_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        self.op_progress_var = tk.DoubleVar(value=0)
        ctk.CTkProgressBar(parent, variable=self.op_progress_var,
                           fg_color=CARD_BG, progress_color=SUCCESS).pack(fill="x", padx=4, pady=(4, 6))

        self.log_box = ctk.CTkTextbox(parent, font=FONT_MONO, fg_color=CARD_BG,
                                      text_color=TEXT, state="disabled")
        self.log_box.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill="x", pady=(4, 0))
        ctk.CTkButton(btn_row, text="Clear Log", width=100, height=30,
                      font=FONT_SMALL, fg_color=CARD_BG, hover_color=BORDER,
                      command=self._clear_log).pack(side="right", padx=4)

    def _build_categories_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", pady=8, padx=4)
        ctk.CTkLabel(top, text="Manage categories and their file extensions.",
                     font=FONT_SMALL, text_color=TEXT_DIM).pack(side="left")
        ctk.CTkButton(top, text="+ Add Category", width=130, height=32,
                      font=FONT_SMALL, fg_color=ACCENT,
                      command=self._add_category).pack(side="right", padx=4)

        self.cat_mgr_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.cat_mgr_frame.pack(fill="both", expand=True, padx=4)
        self._refresh_category_manager()

    def _refresh_category_manager(self):
        for w in self.cat_mgr_frame.winfo_children():
            w.destroy()
        for cat_name, cat_data in self.categories.items():
            self._build_cat_mgr_row(self.cat_mgr_frame, cat_name, cat_data)

    def _build_cat_mgr_row(self, parent, cat_name, cat_data):
        frame = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=8,
                             border_width=1, border_color=BORDER)
        frame.pack(fill="x", pady=4)
        frame.columnconfigure(1, weight=1)

        color = cat_data.get("color", ACCENT)
        icon = cat_data.get("icon", "📁")
        ctk.CTkLabel(frame, text=f"{icon}  {cat_name}",
                     font=FONT_BOLD, text_color=color).grid(row=0, column=0, padx=12, pady=8, sticky="w")

        ext_text = ", ".join(cat_data.get("extensions", []))
        ext_label = ctk.CTkLabel(frame, text=ext_text, font=FONT_SMALL,
                                 text_color=TEXT_DIM, wraplength=500, justify="left")
        ext_label.grid(row=0, column=1, padx=8, pady=8, sticky="w")

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=8, pady=8)
        ctk.CTkButton(btn_frame, text="Edit", width=70, height=28,
                      font=FONT_SMALL, fg_color=ACCENT, hover_color="#4070E0",
                      command=lambda c=cat_name: self._edit_category(c)).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="Delete", width=70, height=28,
                      font=FONT_SMALL, fg_color=CARD_BG, hover_color=ERROR_COL,
                      text_color=ERROR_COL, border_width=1, border_color=ERROR_COL,
                      command=lambda c=cat_name: self._delete_category(c)).pack(side="left", padx=2)

    # ──────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _section_label(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=FONT_BOLD,
                     text_color=TEXT_DIM).pack(anchor="w", padx=12, pady=(10, 4))

    def _append_log(self, msg: str):
        color_map = {"[OK]": SUCCESS, "[ERROR]": ERROR_COL,
                     "[WARN]": WARNING, "[DONE]": ACCENT2, "[SKIP]": TEXT_DIM}
        self.log_box.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{ts}] {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _browse_source(self):
        path = filedialog.askdirectory(title="Select Source Folder / Drive")
        if path:
            self.src_var.set(path)

    def _browse_dest(self):
        path = filedialog.askdirectory(title="Select Destination Folder")
        if path:
            self.dst_var.set(path)

    def _get_active_categories(self):
        return {k: v for k, v in self.categories.items()
                if self.cat_vars.get(k, tk.BooleanVar(value=True)).get()}

    def _on_cat_toggle(self, cat_name):
        pass  # State is read dynamically

    def _on_meta_toggle(self, cat_name, var):
        self.categories[cat_name]["metadata"]["enabled"] = var.get()
        save_config({"categories": self.categories, "settings": self.settings})

    # ──────────────────────────────────────────────────────────────────────────
    # SCAN
    # ──────────────────────────────────────────────────────────────────────────

    def _start_scan(self):
        src = self.src_var.get().strip()
        if not src or not os.path.exists(src):
            messagebox.showerror("Invalid Source", "Please select a valid source folder.")
            return

        self.scan_result = {}
        self._draw_empty_summary()
        self.btn_scan.configure(state="disabled", text="Scanning…")
        self.btn_preview.configure(state="disabled")
        self.scan_progress_var.set(0)

        # Always scan using ALL categories — checkboxes only affect Preview/Transfer
        def on_progress(current, total, name):
            pct = current / total if total else 0
            self.root.after(0, lambda: self.scan_progress_var.set(pct))
            self.root.after(0, lambda: self.scan_status_var.set(
                f"Scanning {current:,}/{total:,}  —  {name}"))

        def on_done(result):
            self.scan_result = result
            self.root.after(0, self._on_scan_done, result)

        scanner = Scanner(src, self.categories, progress_callback=on_progress, done_callback=on_done)
        scanner.scan_threaded()

    def _on_scan_done(self, result):
        self.btn_scan.configure(state="normal", text="🔍  Scan Source")
        self.scan_progress_var.set(1.0)
        self.scan_status_var.set(
            f"Scan complete — {sum(len(v) for v in result.values()):,} files found.")
        self._draw_summary(result)
        self.btn_preview.configure(state="normal")
        self.tab_view.set("📊  Scan Results")

    # ──────────────────────────────────────────────────────────────────────────
    # PREVIEW
    # ──────────────────────────────────────────────────────────────────────────

    def _run_preview(self):
        # Check scan was actually done and has files
        total_scanned = sum(len(v) for v in self.scan_result.values())
        if total_scanned == 0:
            messagebox.showwarning("No Scan Results",
                                   "Please scan a source folder first.")
            return

        # Collect files from checked categories only
        active = self._get_active_categories()
        all_files = []
        for cat in active:
            all_files.extend(self.scan_result.get(cat, []))

        if not all_files:
            messagebox.showinfo("Nothing Selected",
                                "No files match the selected categories.\n"
                                "Check at least one category on the left panel.")
            return

        # Apply metadata toggle states
        for cat, var in self.meta_vars.items():
            if cat in self.categories:
                self.categories[cat]["metadata"]["enabled"] = var.get()

        self.settings["operation_mode"] = self.op_mode.get()

        # Use a placeholder destination for preview path building
        dst = self.dst_var.get().strip() or "Destination"
        engine = MoveEngine(dst, self.categories, self.settings)
        self.preview_result = engine.preview(all_files)

        total     = len(self.preview_result)
        total_sz  = sum(p["size"] for p in self.preview_result)
        skips     = sum(1 for p in self.preview_result if p["action"] == "skip")
        self.preview_summary_var.set(
            f"{total:,} files ready  |  {fmt_size(total_sz)}  |  {skips} conflicts/skips"
            + ("  —  ⚠ Set destination before transferring!" if not self.dst_var.get().strip() else ""))

        self._draw_preview(self.preview_result)
        self.btn_execute.configure(
            state="normal",
            text=f"▶  Start Transfer  ({total:,} files)")
        self.tab_view.set("👁  Preview")

    # ──────────────────────────────────────────────────────────────────────────
    # EXECUTE
    # ──────────────────────────────────────────────────────────────────────────

    def _run_execute(self):
        if not self.preview_result:
            messagebox.showwarning("No Preview", "Please run Preview & Plan first.")
            return

        # Enforce destination at transfer time
        dst = self.dst_var.get().strip()
        if not dst:
            messagebox.showerror("No Destination",
                                 "Please set a Destination folder before transferring.")
            return

        mode = self.op_mode.get()
        verb = "MOVE" if mode == "move" else "COPY"
        count = len([p for p in self.preview_result if p["action"] != "skip"])
        if not messagebox.askyesno(
                "Confirm Transfer",
                f"About to {verb} {count:,} files to:\n{dst}\n\nContinue?"):
            return

        self.btn_execute.configure(state="disabled", text="⏳  Running…")
        self.btn_preview.configure(state="disabled")
        self.op_progress_var.set(0)
        self.tab_view.set("📋  Operation Log")
        self._append_log(f"Starting {verb} operation — {count:,} files…")

        self.settings["operation_mode"] = mode
        self.settings["last_source"] = self.src_var.get()
        self.settings["last_destination"] = self.dst_var.get()
        save_config({"categories": self.categories, "settings": self.settings})

        # Build file entry list from preview
        file_entries = [{"path": p["src"], "name": Path(p["src"]).name,
                         "ext": Path(p["src"]).suffix, "size": p["size"],
                         "category": p["category"], "metadata": {}}
                        for p in self.preview_result if p["action"] != "skip"]

        def on_progress(current, total, name):
            pct = current / total if total else 0
            self.root.after(0, self.op_progress_var.set, pct)

        def on_log(msg):
            self.root.after(0, self._append_log, msg)

        def on_done(summary):
            self.root.after(0, self._on_execute_done, summary)

        engine = MoveEngine(dst, self.categories, self.settings,
                            progress_callback=on_progress,
                            log_callback=on_log,
                            done_callback=on_done)
        engine.execute_threaded(file_entries)

    def _on_execute_done(self, summary):
        self.btn_execute.configure(state="normal", text="▶  Start Transfer")
        self.btn_preview.configure(state="normal", text="👁  Preview & Plan")
        self.op_progress_var.set(1.0)
        messagebox.showinfo("Done",
                            f"Operation complete!\n\n"
                            f"✅ Processed: {summary['success']:,}\n"
                            f"⏭ Skipped:   {summary['skipped']:,}\n"
                            f"❌ Errors:    {summary['errors']:,}")

    # ──────────────────────────────────────────────────────────────────────────
    # CATEGORY MANAGEMENT
    # ──────────────────────────────────────────────────────────────────────────

    def _add_category(self):
        self._open_cat_editor(None)

    def _edit_category(self, cat_name):
        self._open_cat_editor(cat_name)

    def _delete_category(self, cat_name):
        if messagebox.askyesno("Delete Category",
                               f"Delete category '{cat_name}'?\nThis cannot be undone."):
            del self.categories[cat_name]
            save_config({"categories": self.categories, "settings": self.settings})
            self._refresh_category_manager()

    def _open_cat_editor(self, cat_name):
        win = ctk.CTkToplevel(self.root)
        win.title("Edit Category" if cat_name else "New Category")
        win.geometry("520x480")
        win.configure(fg_color=DARK_BG)
        win.grab_set()

        existing = self.categories.get(cat_name, {}) if cat_name else {}

        ctk.CTkLabel(win, text="Category Name:", font=FONT_BOLD).pack(anchor="w", padx=20, pady=(20, 4))
        name_var = tk.StringVar(value=cat_name or "")
        ctk.CTkEntry(win, textvariable=name_var, height=36, font=FONT_MAIN,
                     fg_color=CARD_BG).pack(fill="x", padx=20)

        ctk.CTkLabel(win, text="Icon (emoji):", font=FONT_BOLD).pack(anchor="w", padx=20, pady=(12, 4))
        icon_var = tk.StringVar(value=existing.get("icon", "📁"))
        ctk.CTkEntry(win, textvariable=icon_var, height=36, font=FONT_MAIN,
                     fg_color=CARD_BG, width=80).pack(anchor="w", padx=20)

        ctk.CTkLabel(win, text="Extensions (comma-separated, e.g. .jpg,.png):",
                     font=FONT_BOLD).pack(anchor="w", padx=20, pady=(12, 4))
        ext_box = ctk.CTkTextbox(win, height=120, font=FONT_MONO, fg_color=CARD_BG)
        ext_box.pack(fill="x", padx=20)
        ext_box.insert("1.0", ", ".join(existing.get("extensions", [])))

        def save():
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showerror("Error", "Category name cannot be empty.", parent=win)
                return
            raw_exts = ext_box.get("1.0", "end").strip()
            exts = [e.strip() for e in raw_exts.split(",") if e.strip()]
            # Remove old name if renaming
            if cat_name and cat_name != new_name and cat_name in self.categories:
                del self.categories[cat_name]
            self.categories[new_name] = {
                "icon": icon_var.get().strip() or "📁",
                "enabled": existing.get("enabled", True),
                "color": existing.get("color", ACCENT),
                "extensions": exts,
                "metadata": existing.get("metadata", {
                    "enabled": False, "primary_field": "date_modified",
                    "folder_structure": "flat", "available_fields": ["date_modified"]
                })
            }
            save_config({"categories": self.categories, "settings": self.settings})
            self._refresh_category_manager()
            win.destroy()

        ctk.CTkButton(win, text="Save Category", height=40, font=FONT_BOLD,
                      fg_color=ACCENT, command=save).pack(fill="x", padx=20, pady=20)

    # ──────────────────────────────────────────────────────────────────────────
    # SETTINGS
    # ──────────────────────────────────────────────────────────────────────────

    def _open_settings(self):
        win = ctk.CTkToplevel(self.root)
        win.title("Settings")
        win.geometry("460x380")
        win.configure(fg_color=DARK_BG)
        win.grab_set()

        def row(parent, label, widget_fn):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(fill="x", padx=20, pady=6)
            ctk.CTkLabel(f, text=label, font=FONT_BOLD, width=200, anchor="w").pack(side="left")
            widget_fn(f)

        ctk.CTkLabel(win, text="Settings", font=FONT_TITLE).pack(pady=(20, 12))

        conflict_var = tk.StringVar(value=self.settings.get("conflict_resolution", "rename"))
        row(win, "Conflict Resolution:",
            lambda p: ctk.CTkOptionMenu(p, variable=conflict_var,
                                        values=["rename", "skip", "overwrite"],
                                        fg_color=CARD_BG, button_color=ACCENT).pack(side="left"))

        flat_var = tk.BooleanVar(value=self.settings.get("flat_output", False))
        row(win, "Flat Output (no subfolders):",
            lambda p: ctk.CTkSwitch(p, variable=flat_var, text="",
                                    fg_color=BORDER, progress_color=ACCENT).pack(side="left"))

        fallback_var = tk.StringVar(value=self.settings.get("metadata_fallback", "Unknown"))
        row(win, "Metadata Fallback Name:",
            lambda p: ctk.CTkEntry(p, textvariable=fallback_var,
                                   width=140, fg_color=CARD_BG).pack(side="left"))

        def save_settings():
            self.settings["conflict_resolution"] = conflict_var.get()
            self.settings["flat_output"] = flat_var.get()
            self.settings["metadata_fallback"] = fallback_var.get()
            save_config({"categories": self.categories, "settings": self.settings})
            win.destroy()

        ctk.CTkButton(win, text="Save Settings", height=40, font=FONT_BOLD,
                      fg_color=ACCENT, command=save_settings).pack(fill="x", padx=20, pady=24)

    # ──────────────────────────────────────────────────────────────────────────
    # UNDO
    # ──────────────────────────────────────────────────────────────────────────

    def _open_undo(self):
        from app.config import SESSION_LOG_DIR
        log_dir = SESSION_LOG_DIR
        if not log_dir.exists() or not list(log_dir.glob("*.json")):
            messagebox.showinfo("No Sessions", "No session logs found to undo.")
            return

        win = ctk.CTkToplevel(self.root)
        win.title("Undo Session")
        win.geometry("560x420")
        win.configure(fg_color=DARK_BG)
        win.grab_set()

        ctk.CTkLabel(win, text="Select a session to undo (move operations only):",
                     font=FONT_BOLD).pack(pady=(20, 8), padx=20, anchor="w")

        logs = sorted(log_dir.glob("*.json"), reverse=True)
        selected = tk.StringVar(value=str(logs[0]) if logs else "")

        scroll = ctk.CTkScrollableFrame(win, fg_color=CARD_BG, corner_radius=8, height=240)
        scroll.pack(fill="both", expand=True, padx=20, pady=8)

        for log_path in logs:
            ctk.CTkRadioButton(scroll, text=log_path.name, variable=selected,
                               value=str(log_path), font=FONT_MONO,
                               fg_color=ACCENT).pack(anchor="w", padx=12, pady=4)

        log_box = ctk.CTkTextbox(win, height=80, font=FONT_MONO,
                                 fg_color=CARD_BG, state="disabled")
        log_box.pack(fill="x", padx=20, pady=4)

        def do_undo():
            log_file = selected.get()
            if not log_file:
                return
            log_box.configure(state="normal")

            def log_cb(msg):
                log_box.insert("end", msg + "\n")
                log_box.see("end")

            result = MoveEngine.undo_session(log_file, log_callback=log_cb)
            log_box.configure(state="disabled")
            messagebox.showinfo("Undo Complete",
                                f"Restored: {result['success']}\nErrors: {result['errors']}")

        ctk.CTkButton(win, text="↩ Undo Selected Session", height=38,
                      font=FONT_BOLD, fg_color=WARNING, text_color=DARK_BG,
                      command=do_undo).pack(fill="x", padx=20, pady=12)
