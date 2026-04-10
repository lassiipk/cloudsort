"""
CloudPrep Organizer — GUI
Simple flow: Select Source → Select Destination → Pick Categories → Scan → Execute
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import os

from app.config import load_config, save_config
from app.scanner import Scanner
from app.mover import MoveEngine

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

DARK_BG   = "#0F1117"
PANEL_BG  = "#1A1D27"
CARD_BG   = "#22263A"
BORDER    = "#2E3350"
ACCENT    = "#5B8CFF"
ACCENT2   = "#4ECDC4"
TEXT      = "#E8ECF4"
TEXT_DIM  = "#7B82A0"
SUCCESS   = "#4ADE80"
WARNING   = "#FBBF24"
ERR       = "#F87171"

F_TITLE  = ("Segoe UI", 19, "bold")
F_BOLD   = ("Segoe UI", 13, "bold")
F_MAIN   = ("Segoe UI", 12)
F_SMALL  = ("Segoe UI", 11)
F_MONO   = ("Consolas", 11)


def fmt_size(b: int) -> str:
    for u in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} PB"


class CloudPrepApp:
    def __init__(self):
        self.config     = load_config()
        self.categories = self.config["categories"]
        self.settings   = self.config["settings"]
        self.scan_result: Dict = {}

        self.root = ctk.CTk()
        self.root.title("CloudPrep Organizer")
        self.root.geometry("1340x860")
        self.root.resizable(False, False)
        self.root.configure(fg_color=DARK_BG)
        self._build_ui()

    def run(self):
        self.root.mainloop()

    # ──────────────────────────────────────────────────────────────────────────
    # LAYOUT
    # ──────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        body = ctk.CTkFrame(self.root, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        body.columnconfigure(0, weight=0, minsize=340)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color=PANEL_BG, corner_radius=12,
                            border_width=1, border_color=BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        right = ctk.CTkFrame(body, fg_color=PANEL_BG, corner_radius=12,
                             border_width=1, border_color=BORDER)
        right.grid(row=0, column=1, sticky="nsew")

        self._build_left(left)
        self._build_right(right)

    def _build_header(self):
        hdr = ctk.CTkFrame(self.root, fg_color=PANEL_BG, height=60,
                           corner_radius=0, border_width=1, border_color=BORDER)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        inner = ctk.CTkFrame(hdr, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=18)
        ctk.CTkLabel(inner, text="☁  CloudPrep Organizer",
                     font=F_TITLE, text_color=TEXT).pack(side="left", pady=14)
        ctk.CTkLabel(inner, text="Organize · Encrypt · Upload",
                     font=F_SMALL, text_color=TEXT_DIM).pack(side="left", padx=14)
        top_btns = ctk.CTkFrame(inner, fg_color="transparent")
        top_btns.pack(side="right", pady=10)
        self.btn_execute = ctk.CTkButton(
            top_btns, text="▶  Start Transfer",
            width=180, height=36,
            font=("Segoe UI", 13, "bold"),
            fg_color=SUCCESS, hover_color="#22C55E",
            text_color="#0F1117", state="disabled",
            command=self._do_execute)
        self.btn_execute.pack(side="left", padx=(0, 10))
        ctk.CTkButton(top_btns, text="⚙  Settings", width=100, height=36,
                      font=F_SMALL, fg_color=CARD_BG, hover_color=BORDER,
                      command=self._open_settings).pack(side="left", padx=4)
        ctk.CTkButton(top_btns, text="↩  Undo", width=90, height=36,
                      font=F_SMALL, fg_color=CARD_BG, hover_color=BORDER,
                      command=self._open_undo).pack(side="left", padx=4)

    # ── Left panel ────────────────────────────────────────────────────────────

    def _build_left(self, parent):
        # ① Source
        self._lbl(parent, "① Source Folder / Drive")
        sf = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=8)
        sf.pack(fill="x", padx=12, pady=(0, 8))
        sf.columnconfigure(0, weight=1)
        self.src_var = tk.StringVar(value=self.settings.get("last_source", ""))
        ctk.CTkEntry(sf, textvariable=self.src_var, height=34, font=F_SMALL,
                     fg_color=DARK_BG, border_color=BORDER,
                     placeholder_text="e.g.  D:\\  or  C:\\Users\\You\\Files"
                     ).grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        ctk.CTkButton(sf, text="Browse", width=72, height=28, font=F_SMALL,
                      fg_color=ACCENT, hover_color="#4070E0",
                      command=self._browse_src
                      ).grid(row=0, column=1, padx=(0, 8), pady=8)

        # ② Destination
        self._lbl(parent, "② Destination (Vault Folder)")
        df = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=8)
        df.pack(fill="x", padx=12, pady=(0, 8))
        df.columnconfigure(0, weight=1)
        self.dst_var = tk.StringVar(value=self.settings.get("last_destination", ""))
        ctk.CTkEntry(df, textvariable=self.dst_var, height=34, font=F_SMALL,
                     fg_color=DARK_BG, border_color=BORDER,
                     placeholder_text="Where organised files will go"
                     ).grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        ctk.CTkButton(df, text="Browse", width=72, height=28, font=F_SMALL,
                      fg_color=ACCENT2, hover_color="#3AB0A8",
                      command=self._browse_dst
                      ).grid(row=0, column=1, padx=(0, 8), pady=8)

        # ③ Mode
        self._lbl(parent, "③ Operation Mode")
        mf = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=8)
        mf.pack(fill="x", padx=12, pady=(0, 8))
        self.op_mode = tk.StringVar(value=self.settings.get("operation_mode", "copy"))
        for lbl, val in [("📋  Copy  (keeps originals — safer)", "copy"),
                          ("✂️  Move  (removes from source)", "move")]:
            ctk.CTkRadioButton(mf, text=lbl, variable=self.op_mode, value=val,
                               font=F_SMALL, text_color=TEXT,
                               fg_color=ACCENT).pack(anchor="w", padx=14, pady=5)

        # ④ Categories
        self._lbl(parent, "④ Categories  (✓ = include in transfer)")
        self.cat_vars         = {}
        self.meta_vars        = {}
        self.cat_count_labels = {}
        cat_scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent", height=200)
        cat_scroll.pack(fill="x", padx=12, pady=(0, 8))
        for cat_name, cat_data in self.categories.items():
            self._build_cat_row(cat_scroll, cat_name, cat_data)

        # Divider
        ctk.CTkFrame(parent, fg_color=BORDER, height=2).pack(fill="x", padx=12, pady=6)

        # ⑤ Scan button
        self.btn_scan = ctk.CTkButton(
            parent, text="🔍  Scan Source", height=44,
            font=F_BOLD, fg_color=ACCENT, hover_color="#4070E0",
            command=self._do_scan)
        self.btn_scan.pack(fill="x", padx=12, pady=(0, 4))

        self.scan_status_var = tk.StringVar(value="")
        ctk.CTkLabel(parent, textvariable=self.scan_status_var,
                     font=F_SMALL, text_color=TEXT_DIM).pack(fill="x", padx=14)
        self.scan_prog_var = tk.DoubleVar(value=0)
        ctk.CTkProgressBar(parent, variable=self.scan_prog_var,
                           fg_color=CARD_BG, progress_color=ACCENT,
                           height=6).pack(fill="x", padx=12, pady=(2, 8))



    def _build_cat_row(self, parent, cat_name, cat_data):
        frame = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=8)
        frame.pack(fill="x", pady=3)
        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(5, 2))
        top.columnconfigure(1, weight=1)

        var = tk.BooleanVar(value=cat_data.get("enabled", True))
        self.cat_vars[cat_name] = var
        ctk.CTkCheckBox(top, text="", variable=var, width=20,
                        fg_color=ACCENT, hover_color="#4070E0"
                        ).grid(row=0, column=0, padx=(0, 6))

        color = cat_data.get("color", ACCENT)
        icon  = cat_data.get("icon",  "📁")
        ctk.CTkLabel(top, text=f"{icon}  {cat_name}",
                     font=F_BOLD, text_color=color
                     ).grid(row=0, column=1, sticky="w")

        count_lbl = ctk.CTkLabel(top, text="", font=F_SMALL, text_color=TEXT_DIM)
        count_lbl.grid(row=0, column=2, padx=4)
        self.cat_count_labels[cat_name] = count_lbl

        if "metadata" in cat_data:
            meta_var = tk.BooleanVar(value=cat_data["metadata"].get("enabled", False))
            self.meta_vars[cat_name] = meta_var
            mr = ctk.CTkFrame(frame, fg_color="transparent")
            mr.pack(fill="x", padx=24, pady=(0, 5))
            ctk.CTkSwitch(mr, text="Sort by metadata", variable=meta_var,
                          font=F_SMALL, text_color=TEXT_DIM,
                          fg_color=BORDER, progress_color=ACCENT2,
                          command=lambda c=cat_name, v=meta_var: self._toggle_meta(c, v)
                          ).pack(side="left")

    # ── Right panel ───────────────────────────────────────────────────────────

    def _build_right(self, parent):
        self.tab_view = ctk.CTkTabview(
            parent, fg_color="transparent",
            segmented_button_fg_color=CARD_BG,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color="#4070E0",
            segmented_button_unselected_color=CARD_BG,
            text_color=TEXT)
        self.tab_view.pack(fill="both", expand=True, padx=12, pady=12)

        self.tab_view.add("📊  Scan Results")
        self.tab_view.add("📋  Transfer Log")
        self.tab_view.add("🗂  Categories")

        self._build_scan_tab(self.tab_view.tab("📊  Scan Results"))
        self._build_log_tab(self.tab_view.tab("📋  Transfer Log"))
        self._build_cat_mgr_tab(self.tab_view.tab("🗂  Categories"))

    def _build_scan_tab(self, parent):
        self.summary_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.summary_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self._draw_empty_summary()

    def _draw_empty_summary(self):
        for w in self.summary_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.summary_frame,
                     text="Select a source folder and click  🔍 Scan Source.",
                     font=F_MAIN, text_color=TEXT_DIM).pack(pady=60)

    def _draw_summary(self, result: dict):
        for w in self.summary_frame.winfo_children():
            w.destroy()

        total_files = sum(len(v) for v in result.values())
        total_size  = sum(e["size"] for v in result.values() for e in v)

        banner = ctk.CTkFrame(self.summary_frame, fg_color=CARD_BG,
                              corner_radius=10, border_width=1, border_color=ACCENT)
        banner.pack(fill="x", padx=4, pady=(4, 12))
        ctk.CTkLabel(banner,
                     text=f"✅  {total_files:,} files found  ·  {fmt_size(total_size)}  —  "
                          f"Check categories on the left, then click  ▶ Start Transfer",
                     font=F_BOLD, text_color=ACCENT).pack(pady=10, padx=14)

        cols = 3
        grid = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=4)
        for i in range(cols):
            grid.columnconfigure(i, weight=1)

        known   = [(k, v) for k, v in result.items() if k != "Uncategorized" and v]
        unknown = [(k, v) for k, v in result.items() if k == "Uncategorized" and v]
        items   = known + unknown

        if not items:
            ctk.CTkLabel(self.summary_frame,
                         text="No files found in that folder.",
                         font=F_MAIN, text_color=TEXT_DIM).pack(pady=20)
            return

        for idx, (cat, entries) in enumerate(items):
            ri, ci    = divmod(idx, cols)
            cat_data  = self.categories.get(cat, {})
            color     = cat_data.get("color", WARNING) if cat != "Uncategorized" else WARNING
            icon      = cat_data.get("icon",  "❓")    if cat != "Uncategorized" else "❓"
            count     = len(entries)
            size      = sum(e["size"] for e in entries)
            is_active = self.cat_vars.get(cat, tk.BooleanVar(value=False)).get()

            card = ctk.CTkFrame(grid, fg_color=CARD_BG, corner_radius=10,
                                border_width=2,
                                border_color=color if is_active else BORDER)
            card.grid(row=ri, column=ci, padx=4, pady=4, sticky="nsew")

            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=12, pady=(10, 0))
            ctk.CTkLabel(top, text=f"{icon}  {cat}",
                         font=F_BOLD, text_color=color).pack(side="left")
            ctk.CTkLabel(top,
                         text="✓ included" if is_active else "— excluded",
                         font=F_SMALL,
                         text_color=SUCCESS if is_active else TEXT_DIM
                         ).pack(side="right")

            ctk.CTkLabel(card, text=f"{count:,} files",
                         font=F_MAIN, text_color=TEXT).pack(anchor="w", padx=12, pady=(4, 0))
            ctk.CTkLabel(card, text=fmt_size(size),
                         font=F_SMALL, text_color=TEXT_DIM).pack(anchor="w", padx=12, pady=(0, 10))

            lbl = self.cat_count_labels.get(cat)
            if lbl:
                lbl.configure(text=f"{count:,}")

    def _build_log_tab(self, parent):
        self.op_prog_var = tk.DoubleVar(value=0)
        ctk.CTkProgressBar(parent, variable=self.op_prog_var,
                           fg_color=CARD_BG, progress_color=SUCCESS,
                           height=8).pack(fill="x", padx=4, pady=(4, 6))
        self.log_box = ctk.CTkTextbox(parent, font=F_MONO,
                                      fg_color=CARD_BG, text_color=TEXT,
                                      state="disabled")
        self.log_box.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        ctk.CTkButton(parent, text="Clear Log", width=90, height=28,
                      font=F_SMALL, fg_color=CARD_BG, hover_color=BORDER,
                      command=self._clear_log).pack(side="right", padx=4, pady=(0, 4))

    def _build_cat_mgr_tab(self, parent):
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", padx=4, pady=8)
        ctk.CTkLabel(top, text="Add, edit or delete categories and their extensions.",
                     font=F_SMALL, text_color=TEXT_DIM).pack(side="left")
        ctk.CTkButton(top, text="+ Add Category", width=130, height=32,
                      font=F_SMALL, fg_color=ACCENT,
                      command=lambda: self._open_cat_editor(None)).pack(side="right")
        self.cat_mgr_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.cat_mgr_frame.pack(fill="both", expand=True, padx=4)
        self._refresh_cat_mgr()

    def _refresh_cat_mgr(self):
        for w in self.cat_mgr_frame.winfo_children():
            w.destroy()
        for cat_name, cat_data in self.categories.items():
            f = ctk.CTkFrame(self.cat_mgr_frame, fg_color=CARD_BG,
                             corner_radius=8, border_width=1, border_color=BORDER)
            f.pack(fill="x", pady=3)
            f.columnconfigure(1, weight=1)
            color = cat_data.get("color", ACCENT)
            icon  = cat_data.get("icon",  "📁")
            ctk.CTkLabel(f, text=f"{icon}  {cat_name}",
                         font=F_BOLD, text_color=color
                         ).grid(row=0, column=0, padx=12, pady=8, sticky="w")
            ctk.CTkLabel(f, text=", ".join(cat_data.get("extensions", [])),
                         font=F_SMALL, text_color=TEXT_DIM, wraplength=480, justify="left"
                         ).grid(row=0, column=1, padx=8, pady=8, sticky="w")
            bf = ctk.CTkFrame(f, fg_color="transparent")
            bf.grid(row=0, column=2, padx=8, pady=8)
            ctk.CTkButton(bf, text="Edit", width=64, height=26, font=F_SMALL,
                          fg_color=ACCENT, hover_color="#4070E0",
                          command=lambda c=cat_name: self._open_cat_editor(c)
                          ).pack(side="left", padx=2)
            ctk.CTkButton(bf, text="Delete", width=64, height=26, font=F_SMALL,
                          fg_color=CARD_BG, hover_color=ERR,
                          text_color=ERR, border_width=1, border_color=ERR,
                          command=lambda c=cat_name: self._delete_category(c)
                          ).pack(side="left", padx=2)

    # ──────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _lbl(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=F_BOLD,
                     text_color=TEXT_DIM).pack(anchor="w", padx=14, pady=(10, 3))

    def _browse_src(self):
        p = filedialog.askdirectory(title="Select Source Folder or Drive")
        if p:
            self.src_var.set(p)

    def _browse_dst(self):
        p = filedialog.askdirectory(title="Select Destination / Vault Folder")
        if p:
            self.dst_var.set(p)

    def _toggle_meta(self, cat, var):
        self.categories[cat]["metadata"]["enabled"] = var.get()
        save_config({"categories": self.categories, "settings": self.settings})

    def _log(self, msg: str):
        self.log_box.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{ts}]  {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    # ──────────────────────────────────────────────────────────────────────────
    # SCAN
    # ──────────────────────────────────────────────────────────────────────────

    def _do_scan(self):
        src = self.src_var.get().strip()
        if not src or not os.path.exists(src):
            messagebox.showerror("Invalid Source",
                                 "Please select a valid source folder or drive.")
            return

        self.scan_result = {}
        self.btn_scan.configure(state="disabled", text="Scanning…")
        self.btn_execute.configure(state="disabled", text="▶  Start Transfer")
        self.scan_prog_var.set(0)
        self._draw_empty_summary()

        def on_progress(cur, total, name):
            pct = cur / total if total else 0
            self.root.after(0, self.scan_prog_var.set, pct)
            self.root.after(0, self.scan_status_var.set,
                            f"{cur:,} / {total:,}  —  {name}")

        def on_done(result):
            self.scan_result = result
            self.root.after(0, self._on_scan_done, result)

        Scanner(src, self.categories,
                progress_callback=on_progress,
                done_callback=on_done).scan_threaded()

    def _on_scan_done(self, result):
        total = sum(len(v) for v in result.values())
        self.btn_scan.configure(state="normal", text="🔍  Scan Source")
        self.btn_execute.configure(
            state="normal",
            text=f"▶  Start Transfer  ({total:,} files)")
        self.scan_status_var.set(f"Done — {total:,} files found.")
        self.scan_prog_var.set(1.0)
        self._draw_summary(result)
        self.tab_view.set("📊  Scan Results")

    # ──────────────────────────────────────────────────────────────────────────
    # EXECUTE
    # ──────────────────────────────────────────────────────────────────────────

    def _do_execute(self):
        dst = self.dst_var.get().strip()
        if not dst:
            messagebox.showerror("No Destination",
                                 "Please set a Destination folder first.")
            return

        if not self.scan_result:
            messagebox.showwarning("No Scan", "Please scan a source folder first.")
            return

        all_files = []
        for cat, checked in self.cat_vars.items():
            if checked.get():
                all_files.extend(self.scan_result.get(cat, []))

        if not all_files:
            messagebox.showwarning("Nothing Selected",
                                   "No files match the selected categories.\n"
                                   "Check at least one category on the left.")
            return

        for cat, var in self.meta_vars.items():
            if cat in self.categories:
                self.categories[cat]["metadata"]["enabled"] = var.get()

        mode = self.op_mode.get()
        verb = "MOVE" if mode == "move" else "COPY"
        if not messagebox.askyesno(
                "Confirm Transfer",
                f"{verb}  {len(all_files):,} files\n\n"
                f"From:  {self.src_var.get()}\n"
                f"To:    {dst}\n\nContinue?"):
            return

        self.settings["operation_mode"]   = mode
        self.settings["last_source"]      = self.src_var.get()
        self.settings["last_destination"] = dst
        save_config({"categories": self.categories, "settings": self.settings})

        self.btn_execute.configure(state="disabled", text="⏳  Running…")
        self.btn_scan.configure(state="disabled")
        self.op_prog_var.set(0)
        self.tab_view.set("📋  Transfer Log")
        self._log(f"Starting {verb} — {len(all_files):,} files → {dst}")

        def on_progress(cur, total, name):
            self.root.after(0, self.op_prog_var.set, cur / total if total else 0)

        def on_log(msg):
            self.root.after(0, self._log, msg)

        def on_done(summary):
            self.root.after(0, self._on_execute_done, summary)

        MoveEngine(dst, self.categories, self.settings,
                   progress_callback=on_progress,
                   log_callback=on_log,
                   done_callback=on_done).execute_threaded(all_files)

    def _on_execute_done(self, summary):
        self.btn_execute.configure(state="normal", text="▶  Start Transfer")
        self.btn_scan.configure(state="normal")
        self.op_prog_var.set(1.0)
        messagebox.showinfo(
            "Transfer Complete",
            f"✅  Transferred:  {summary['success']:,}\n"
            f"⏭  Skipped:      {summary['skipped']:,}\n"
            f"❌  Errors:       {summary['errors']:,}")

    # ──────────────────────────────────────────────────────────────────────────
    # CATEGORY EDITOR
    # ──────────────────────────────────────────────────────────────────────────

    def _open_cat_editor(self, cat_name):
        win = ctk.CTkToplevel(self.root)
        win.title("Edit Category" if cat_name else "New Category")
        win.geometry("500x460")
        win.configure(fg_color=DARK_BG)
        win.grab_set()
        existing = self.categories.get(cat_name, {}) if cat_name else {}

        ctk.CTkLabel(win, text="Category Name:", font=F_BOLD
                     ).pack(anchor="w", padx=20, pady=(20, 4))
        name_var = tk.StringVar(value=cat_name or "")
        ctk.CTkEntry(win, textvariable=name_var, height=36,
                     font=F_MAIN, fg_color=CARD_BG).pack(fill="x", padx=20)

        ctk.CTkLabel(win, text="Icon (emoji):", font=F_BOLD
                     ).pack(anchor="w", padx=20, pady=(12, 4))
        icon_var = tk.StringVar(value=existing.get("icon", "📁"))
        ctk.CTkEntry(win, textvariable=icon_var, height=36,
                     font=F_MAIN, fg_color=CARD_BG, width=80).pack(anchor="w", padx=20)

        ctk.CTkLabel(win, text="Extensions  (comma-separated, include the dot  e.g. .jpg, .mp4):",
                     font=F_BOLD).pack(anchor="w", padx=20, pady=(12, 4))
        ext_box = ctk.CTkTextbox(win, height=130, font=F_MONO, fg_color=CARD_BG)
        ext_box.pack(fill="x", padx=20)
        ext_box.insert("1.0", ", ".join(existing.get("extensions", [])))

        def _save():
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showerror("Error", "Name cannot be empty.", parent=win)
                return
            exts = [e.strip() for e in ext_box.get("1.0", "end").split(",") if e.strip()]
            if cat_name and cat_name != new_name and cat_name in self.categories:
                del self.categories[cat_name]
            self.categories[new_name] = {
                "icon": icon_var.get().strip() or "📁",
                "enabled": existing.get("enabled", True),
                "color": existing.get("color", ACCENT),
                "extensions": exts,
                "metadata": existing.get("metadata", {
                    "enabled": False, "primary_field": "date_modified",
                    "folder_structure": "flat",
                    "available_fields": ["date_modified"]})
            }
            save_config({"categories": self.categories, "settings": self.settings})
            self._refresh_cat_mgr()
            win.destroy()

        ctk.CTkButton(win, text="Save", height=42, font=F_BOLD,
                      fg_color=ACCENT, command=_save).pack(fill="x", padx=20, pady=20)

    def _delete_category(self, cat_name):
        if messagebox.askyesno("Delete", f"Delete  '{cat_name}'?"):
            del self.categories[cat_name]
            save_config({"categories": self.categories, "settings": self.settings})
            self._refresh_cat_mgr()

    # ──────────────────────────────────────────────────────────────────────────
    