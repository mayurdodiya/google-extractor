"""Google Places Extractor — desktop UI (ttkbootstrap)."""
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk

from exporter import COLUMNS, export_to_excel, default_filename
from scraper import Scraper

APP_TITLE = "Google Places Extractor"
LIGHT, DARK = "flatly", "darkly"
COL_WIDTHS = {"#": 45, "Name": 220, "Category": 140, "Address": 340, "Area": 110, "Phone": 130,
              "Phone 2": 130, "Phone 3": 160, "Website": 200, "Email": 200, "Instagram": 220,
              "Facebook": 220, "Pincode": 75, "City": 90, "State": 90, "Maps Link": 230, "Page": 55}
CENTER_COLS = {"#", "Pincode", "Page"}


class App(ttk.Window):
    def __init__(self):
        super().__init__(title=APP_TITLE, themename=LIGHT, size=(1200, 760), minsize=(880, 560))
        self.place_window_center()

        self.q = queue.Queue()
        self.stop_event = threading.Event()
        self.continue_event = threading.Event()
        self.worker = None
        self.records = []
        self.log_visible = False

        self._build()
        self.after(150, self._poll)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ================= layout =================
    def _build(self):
        root = ttk.Frame(self, padding=(16, 12))
        root.pack(fill="both", expand=True)

        # --- header ---
        header = ttk.Frame(root)
        header.pack(fill="x")
        ttk.Label(header, text="🔍 Google Places Extractor", font=("Segoe UI", 16, "bold"),
                  bootstyle="primary").pack(side="left")
        self.theme_btn = ttk.Button(header, text="🌙 Dark", bootstyle="secondary-outline",
                                    command=self._toggle_theme, width=9)
        self.theme_btn.pack(side="right")

        # --- search card ---
        search = ttk.Labelframe(root, text=" Search ", padding=12, bootstyle="primary")
        search.pack(fill="x", pady=(10, 8))
        self.type_var = tk.StringVar(value="garment shop")
        self.location_var = tk.StringVar(value="Varachha, Surat")
        self.email_var = tk.BooleanVar(value=False)

        fields = ttk.Frame(search)
        fields.pack(fill="x")
        for i, (label, hint, var) in enumerate((
                ("Business type", "e.g. garment shop, restaurant, hospital", self.type_var),
                ("Location", "e.g. Varachha, Surat  or  395006, Surat", self.location_var))):
            box = ttk.Frame(fields)
            box.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 12, 0))
            ttk.Label(box, text=label, font=("Segoe UI", 9, "bold")).pack(anchor="w")
            e = ttk.Entry(box, textvariable=var, font=("Segoe UI", 10))
            e.pack(fill="x", ipady=2)
            e.bind("<Return>", lambda _e: self.start())
            ttk.Label(box, text=hint, font=("Segoe UI", 8), bootstyle="secondary").pack(anchor="w")
            fields.columnconfigure(i, weight=1, uniform="field")

        actions = ttk.Frame(search)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Checkbutton(actions, text="Also check each shop's website for email (slower)",
                        variable=self.email_var, bootstyle="round-toggle").pack(side="left")
        self.extract_btn = ttk.Button(actions, text="⬇  Extract to Excel", bootstyle="info",
                                      command=self.extract, state="disabled", width=18)
        self.extract_btn.pack(side="right")
        self.cont_btn = ttk.Button(actions, text="Continue", bootstyle="warning",
                                   command=self.cont, state="disabled", width=10)
        self.cont_btn.pack(side="right", padx=(0, 8))
        self.stop_btn = ttk.Button(actions, text="■  Stop", bootstyle="danger",
                                   command=self.stop, state="disabled", width=10)
        self.stop_btn.pack(side="right", padx=(0, 8))
        self.start_btn = ttk.Button(actions, text="▶  Start", bootstyle="success",
                                    command=self.start, width=10)
        self.start_btn.pack(side="right", padx=(0, 8))

        # --- stat cards + progress ---
        stats = ttk.Frame(root)
        stats.pack(fill="x", pady=(4, 8))
        self.stat_vars = {}
        for i, (key, label, style) in enumerate((("rows", "Records extracted", "primary"),
                                                 ("pages", "Pages done", "info"),
                                                 ("left", "Pages left", "success"),
                                                 ("time", "Working time", "warning"))):
            card = ttk.Frame(stats, bootstyle=style, padding=(14, 8))
            card.grid(row=0, column=i, sticky="nsew", padx=(0, 10))
            var = tk.StringVar(value=self._stat_default(key))
            self.stat_vars[key] = var
            ttk.Label(card, textvariable=var, font=("Segoe UI", 20, "bold"),
                      bootstyle=f"inverse-{style}").pack(anchor="w")
            ttk.Label(card, text=label, font=("Segoe UI", 9),
                      bootstyle=f"inverse-{style}").pack(anchor="w")
            stats.columnconfigure(i, weight=1, uniform="stat")

        prog = ttk.Frame(stats)
        prog.grid(row=0, column=4, sticky="nsew")
        stats.columnconfigure(4, weight=3)
        self.status_var = tk.StringVar(value="Enter your search and click Start.")
        ttk.Label(prog, textvariable=self.status_var, font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 4))
        self.progress = ttk.Progressbar(prog, mode="determinate", maximum=100,
                                        bootstyle="success-striped")
        self.progress.pack(fill="x", ipady=3)

        # --- results table ---
        table_card = ttk.Frame(root)
        table_card.pack(fill="both", expand=True)
        filt = ttk.Frame(table_card)
        filt.pack(fill="x", pady=(0, 6))
        ttk.Label(filt, text="Results", font=("Segoe UI", 12, "bold")).pack(side="left")
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_: self._refresh_table())
        ttk.Entry(filt, textvariable=self.filter_var, width=34).pack(side="right")
        ttk.Label(filt, text="🔎 Filter:").pack(side="right", padx=(0, 6))
        self.shown_var = tk.StringVar(value="")
        ttk.Label(filt, textvariable=self.shown_var, bootstyle="secondary").pack(side="left", padx=10)

        grid = ttk.Frame(table_card)
        grid.pack(fill="both", expand=True)
        cols = ["#"] + COLUMNS
        self.table = ttk.Treeview(grid, columns=cols, show="headings", bootstyle="primary")
        for c in cols:
            self.table.heading(c, text=c, anchor="center" if c in CENTER_COLS else "w")
            self.table.column(c, width=COL_WIDTHS.get(c, 100), minwidth=40, stretch=False,
                              anchor="center" if c in CENTER_COLS else "w")
        ysb = ttk.Scrollbar(grid, orient="vertical", command=self.table.yview, bootstyle="round")
        xsb = ttk.Scrollbar(grid, orient="horizontal", command=self.table.xview, bootstyle="round")
        self.table.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")
        grid.rowconfigure(0, weight=1)
        grid.columnconfigure(0, weight=1)
        self.table.bind("<Double-1>", self._copy_cell)
        self._style_rows()

        # --- collapsible log ---
        logbar = ttk.Frame(root)
        logbar.pack(fill="x", pady=(8, 0))
        self.log_btn = ttk.Button(logbar, text="▸ Show log", bootstyle="link", command=self._toggle_log)
        self.log_btn.pack(side="left")
        ttk.Label(logbar, text="Tip: double-click a cell to copy it", bootstyle="secondary").pack(side="right")
        self.log_frame = ttk.Frame(root)
        self.log = tk.Text(self.log_frame, height=8, wrap="none", state="disabled",
                           font=("Consolas", 9), relief="flat")
        lsb = ttk.Scrollbar(self.log_frame, command=self.log.yview, bootstyle="round")
        self.log.configure(yscrollcommand=lsb.set)
        lsb.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True)

    @staticmethod
    def _stat_default(key):
        return {"time": "0s", "left": "–"}.get(key, "0")

    def _update_pages(self):
        """Pages left = highest page number Google shows so far − pages done."""
        self.stat_vars["pages"].set(str(self.pages_done))
        if self.pages_total:
            self.stat_vars["left"].set(str(max(self.pages_total - self.pages_done, 0)))

    def _style_rows(self):
        dark = self.style.theme.type == "dark"
        self.style.configure("Treeview", rowheight=28, font=("Segoe UI", 9))
        self.style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        self.table.tag_configure("odd", background="#2b3035" if dark else "#ffffff")
        self.table.tag_configure("even", background="#343a40" if dark else "#eef4fb")

    # ================= table helpers =================
    def _matches(self, rec):
        f = self.filter_var.get().strip().lower()
        return not f or any(f in str(v).lower() for v in rec.values())

    def _insert_row(self, idx, rec):
        n = len(self.table.get_children()) + 1
        values = [idx] + [rec.get(c, "") for c in COLUMNS]
        self.table.insert("", "end", values=values, tags=("even" if n % 2 == 0 else "odd",))

    def _refresh_table(self):
        self.table.delete(*self.table.get_children())
        for i, rec in enumerate(self.records, 1):
            if self._matches(rec):
                self._insert_row(i, rec)
        self._update_counts()

    def _add_record(self, rec):
        self.records.append(rec)
        if self._matches(rec):
            self._insert_row(len(self.records), rec)
            self.table.yview_moveto(1.0)
        self._update_counts()

    def _update_counts(self):
        self.stat_vars["rows"].set(str(len(self.records)))
        shown = len(self.table.get_children())
        self.shown_var.set(f"showing {shown} of {len(self.records)}" if self.filter_var.get().strip() else "")

    def _copy_cell(self, event):
        row = self.table.identify_row(event.y)
        col = self.table.identify_column(event.x)
        if not row or not col:
            return
        value = self.table.item(row, "values")[int(col[1:]) - 1]
        self.clipboard_clear()
        self.clipboard_append(str(value))
        self.status_var.set(f"Copied: {value}")

    def _append_log(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _toggle_log(self):
        self.log_visible = not self.log_visible
        if self.log_visible:
            self.log_frame.pack(fill="x", pady=(4, 0))
            self.log_btn.configure(text="▾ Hide log")
        else:
            self.log_frame.pack_forget()
            self.log_btn.configure(text="▸ Show log")

    def _toggle_theme(self):
        dark = self.style.theme.type == "dark"
        self.style.theme_use(LIGHT if dark else DARK)
        self.theme_btn.configure(text="🌙 Dark" if dark else "☀ Light")
        self._style_rows()

    # ================= actions =================
    def start(self):
        if self.worker and self.worker.is_alive():
            return
        btype = self.type_var.get().strip()
        if not btype:
            messagebox.showwarning(APP_TITLE, "Please enter a business type (e.g. garment shop).")
            return
        if self.records and not messagebox.askyesno(
                APP_TITLE, f"You have {len(self.records)} results. Start a new search and discard them?"):
            return
        self.records = []
        self._refresh_table()
        for k in ("pages", "left", "time"):
            self.stat_vars[k].set(self._stat_default(k))
        self.pages_done = 0
        self.pages_total = 0
        self.progress.configure(value=0)
        self.started_at = time.time()
        self.stop_event.clear()
        self.continue_event.clear()
        self.log.configure(state="normal"); self.log.delete("1.0", "end"); self.log.configure(state="disabled")

        scraper = Scraper(btype, self.location_var.get(), self.email_var.get(),
                          self.q, self.stop_event, self.continue_event)
        self.worker = threading.Thread(target=scraper.run, daemon=True)
        self.worker.start()
        self._tick()
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.extract_btn.configure(state="disabled")
        self.status_var.set("Starting browser…")

    def stop(self):
        self.stop_event.set()
        self.continue_event.set()
        self.status_var.set("Stopping… (keeping results collected so far)")

    def cont(self):
        self.continue_event.set()
        self.cont_btn.configure(state="disabled")
        self.status_var.set("Continuing…")

    def extract(self):
        if not self.records:
            messagebox.showinfo(APP_TITLE, "No data to export yet.")
            return
        path = filedialog.asksaveasfilename(
            title="Save Excel file", defaultextension=".xlsx",
            initialfile=default_filename(self.type_var.get(), self.location_var.get(), ""),
            filetypes=[("Excel workbook", "*.xlsx")])
        if not path:
            return
        try:
            export_to_excel(self.records, path)
        except PermissionError:
            messagebox.showerror(APP_TITLE, "Could not save — is the file open in Excel? Close it and try again.")
            return
        if messagebox.askyesno(APP_TITLE, f"Saved {len(self.records)} rows to:\n{path}\n\nOpen the file now?"):
            os.startfile(path)

    # ================= worker messages =================
    def _poll(self):
        try:
            while True:
                kind, data = self.q.get_nowait()
                if kind == "log":
                    self._append_log(data)
                elif kind == "status":
                    self.status_var.set(data)
                    if data.startswith("Continuing"):
                        self.cont_btn.configure(state="disabled")
                elif kind == "progress":
                    page_no, i, n = data
                    self.progress.configure(value=100 * i / max(n, 1))
                elif kind == "page_done":
                    self.pages_done = data[0]
                    self._update_pages()
                elif kind == "pages_total":
                    # Google reveals more page numbers as you go, so the total only grows.
                    self.pages_total = max(self.pages_total, data)
                    self._update_pages()
                elif kind == "last_page":
                    self.pages_total = data  # no "Next" link: nothing left
                    self._update_pages()
                elif kind == "record":
                    self._add_record(data)
                elif kind == "captcha":
                    self.cont_btn.configure(state="normal")
                    self.status_var.set("⚠ CAPTCHA — solve it in the Chrome window; it will continue automatically.")
                    self.bell()
                    self.lift()
                elif kind == "done":
                    self._finished()
        except queue.Empty:
            pass
        self.after(150, self._poll)

    def _tick(self):
        """Update the Working time card every second while a run is active."""
        secs = int(time.time() - self.started_at)
        m, s = divmod(secs, 60)
        h, m = divmod(m, 60)
        self.stat_vars["time"].set(f"{h}h {m:02d}m {s:02d}s" if h else (f"{m}m {s:02d}s" if m else f"{s}s"))
        if self.worker is None or self.worker.is_alive():
            self.after(1000, self._tick)

    def _finished(self):
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.cont_btn.configure(state="disabled")
        self.progress.configure(value=100)
        n = len(self.records)
        self.extract_btn.configure(state="normal" if n else "disabled")
        self.status_var.set(f"✔ Completed — {n} records. Click 'Extract to Excel' to save.")
        messagebox.showinfo(APP_TITLE, f"Completed!\n\n{n} businesses collected.\nClick 'Extract to Excel' to save them.")

    def _on_close(self):
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno(APP_TITLE, "Extraction is running. Stop and exit?"):
                return
            self.stop()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
