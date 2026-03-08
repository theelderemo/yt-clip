#!/usr/bin/env python3
"""yt-clip: GUI clipboard watcher for yt-dlp"""

import os, re, json, threading, subprocess, time, shlex, queue, fnmatch, tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from pathlib import Path

try:
    import pyperclip
except ImportError:
    print("pip install pyperclip"); exit(1)

CONFIG_PATH = Path.home() / ".config" / "yt-clip" / "config.json"
WHITELIST_PATH = Path.home() / ".config" / "yt-clip" / "whitelist.txt"
BLACKLIST_PATH = Path.home() / ".config" / "yt-clip" / "blacklist.txt"
CUSTOM_THEME_PATH = Path.home() / ".config" / "yt-clip" / "custom_theme.json"

VIDEO_FMTS = ["", "mp4", "mkv", "webm", "avi", "mov", "flv"]
AUDIO_FMTS = ["best", "mp3", "aac", "flac", "opus", "vorbis", "wav", "m4a", "alac"]
MERGE_FMTS = ["", "mp4", "mkv", "webm", "avi", "mov", "flv"]
THUMB_FMTS = ["", "jpg", "png", "webp"]
SUB_FMTS = ["best", "srt", "ass", "vtt", "lrc"]
SUB_CONV = ["", "srt", "ass", "vtt", "lrc"]
BROWSERS = ["", "firefox", "chrome", "chromium", "brave", "edge", "opera", "vivaldi"]
SB_CATS = ["sponsor", "intro", "outro", "selfpromo", "preview",
           "filler", "interaction", "music_offtopic"]

# -- Theme definitions -------------------------------------------------------
# Keys map to the semantic roles used throughout the app.
#   bg          - main window background
#   bg_sec      - card / secondary panel background
#   fg          - primary text
#   fg_dim      - muted / secondary text
#   accent      - primary accent (headings, active tab, error-ish highlights)
#   success     - positive feedback (green)
#   warning     - caution / informational (yellow / amber)
#   surface     - button / inactive-tab background
#   entry_bg    - text entry / input field background
#   accent_hover- button hover tint for Go/primary button

THEME_KEYS = [
    "bg", "bg_sec", "fg", "fg_dim", "accent",
    "success", "warning", "surface", "entry_bg", "accent_hover",
]

THEMES = {
    "Studio Brutalism": {
        "bg":           "#1a1a1a",
        "bg_sec":       "#2d2d2d",
        "fg":           "#f5f3f0",
        "fg_dim":       "#6b6b6b",
        "accent":       "#ff6b35",
        "success":      "#4ade80",
        "warning":      "#fbbf24",
        "surface":      "#444444",
        "entry_bg":     "#2d2d2d",
        "accent_hover": "#cc5529",
    },
    "Midnight": {
        "bg":           "#0f0f12",
        "bg_sec":       "#161619",
        "fg":           "#ededed",
        "fg_dim":       "#7f7f7f",
        "accent":       "#844cf7",
        "success":      "#4ade80",
        "warning":      "#fbbf24",
        "surface":      "#1f2023",
        "entry_bg":     "#1c1c1e",
        "accent_hover": "#6b35d9",
    },
    "Vapor": {
        "bg":           "#0b0716",
        "bg_sec":       "#110e1e",
        "fg":           "#e5e0ef",
        "fg_dim":       "#7b7588",
        "accent":       "#f110c1",
        "success":      "#00a8a9",
        "warning":      "#e5e0ef",
        "surface":      "#1c192b",
        "entry_bg":     "#181623",
        "accent_hover": "#c40d9a",
    },
    "Retro": {
        "bg":           "#110d05",
        "bg_sec":       "#16120a",
        "fg":           "#f7ecd7",
        "fg_dim":       "#968c79",
        "accent":       "#f2c900",
        "success":      "#f2c900",
        "warning":      "#f7ecd7",
        "surface":      "#2e2511",
        "entry_bg":     "#201b13",
        "accent_hover": "#c4a300",
    },
}

THEME_NAMES = list(THEMES.keys()) + ["Custom"]

DEFAULT_CFG = {
    "download_dir": str(Path.home() / "Downloads" / "ytdlp"),
    "theme": "Studio Brutalism",
    "general": {
        "ignore_errors": True, "no_abort_on_error": True,
        "abort_on_error": False, "no_playlist": False,
        "live_from_start": False, "mark_watched": False,
        "restrict_filenames": False, "no_overwrites": False,
        "write_description": False, "write_info_json": False,
        "cookies_from_browser": "",
    },
    "format": {
        "format": "", "format_sort": "",
        "merge_output_format": "",
        "concurrent_fragments": "1", "limit_rate": "", "retries": "10",
    },
    "subtitles": {
        "write_subs": False, "write_auto_subs": False, "embed_subs": False,
        "sub_langs": "", "sub_format": "best", "convert_subs": "",
    },
    "postprocess": {
        "remux_video": "", "recode_video": "",
        "extract_audio": False, "audio_format": "best", "audio_quality": "5",
        "embed_thumbnail": False, "write_thumbnail": False,
        "embed_metadata": False, "embed_chapters": False,
        "convert_thumbnails": "",
    },
    "sponsorblock": {
        "enabled": False, "mark_cats": [], "remove_cats": [],
    },
    "extra_args": "",
    "filter_mode": "",
}

URL_PATTERN = re.compile(r'https?://\S+')


def _load_custom_theme():
    if CUSTOM_THEME_PATH.exists():
        try:
            t = json.loads(CUSTOM_THEME_PATH.read_text())
            base = dict(THEMES["Studio Brutalism"])
            base.update({k: v for k, v in t.items() if k in THEME_KEYS})
            return base
        except Exception:
            pass
    return dict(THEMES["Studio Brutalism"])


def _save_custom_theme(theme_dict):
    CUSTOM_THEME_PATH.parent.mkdir(parents=True, exist_ok=True)
    CUSTOM_THEME_PATH.write_text(json.dumps(theme_dict, indent=2))


def get_theme(name):
    if name == "Custom":
        return _load_custom_theme()
    return dict(THEMES.get(name, THEMES["Studio Brutalism"]))


def _deep_merge(base, override):
    out = base.copy()
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return _deep_merge(json.loads(json.dumps(DEFAULT_CFG)), json.load(f))
    return json.loads(json.dumps(DEFAULT_CFG))


def save_config(cfg):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def build_cmd(url, cfg):
    g, fm, s, pp, sb = (cfg["general"], cfg["format"],
                         cfg["subtitles"], cfg["postprocess"], cfg["sponsorblock"])
    out_tmpl = os.path.join(cfg["download_dir"], "%(title)s.%(ext)s")
    cmd = ["yt-dlp", "-o", out_tmpl]

    if g.get("ignore_errors"):       cmd.append("-i")
    if g.get("no_abort_on_error"):   cmd.append("--no-abort-on-error")
    if g.get("abort_on_error"):      cmd.append("--abort-on-error")
    if g.get("no_playlist"):         cmd.append("--no-playlist")
    if g.get("live_from_start"):     cmd.append("--live-from-start")
    if g.get("mark_watched"):        cmd.append("--mark-watched")
    if g.get("restrict_filenames"):  cmd.append("--restrict-filenames")
    if g.get("no_overwrites"):       cmd.append("--no-overwrites")
    if g.get("write_description"):   cmd.append("--write-description")
    if g.get("write_info_json"):     cmd.append("--write-info-json")
    if g.get("cookies_from_browser"):
        cmd += ["--cookies-from-browser", g["cookies_from_browser"]]

    if fm.get("format"):             cmd += ["-f", fm["format"]]
    if fm.get("format_sort"):        cmd += ["-S", fm["format_sort"]]
    if fm.get("merge_output_format"):
        cmd += ["--merge-output-format", fm["merge_output_format"]]
    n = int(fm.get("concurrent_fragments", 1) or 1)
    if n > 1:                        cmd += ["-N", str(n)]
    if fm.get("limit_rate"):         cmd += ["-r", fm["limit_rate"]]
    r = str(fm.get("retries", "10"))
    if r != "10":                    cmd += ["-R", r]

    if s.get("write_subs"):          cmd.append("--write-subs")
    if s.get("write_auto_subs"):     cmd.append("--write-auto-subs")
    if s.get("embed_subs"):          cmd.append("--embed-subs")
    if s.get("sub_langs"):           cmd += ["--sub-langs", s["sub_langs"]]
    sf = s.get("sub_format", "best")
    if sf and sf != "best":          cmd += ["--sub-format", sf]
    if s.get("convert_subs"):        cmd += ["--convert-subs", s["convert_subs"]]

    if pp.get("remux_video"):        cmd += ["--remux-video", pp["remux_video"]]
    if pp.get("recode_video"):       cmd += ["--recode-video", pp["recode_video"]]
    if pp.get("extract_audio"):
        cmd.append("-x")
        af = pp.get("audio_format", "best")
        if af and af != "best":      cmd += ["--audio-format", af]
        aq = str(pp.get("audio_quality", "5"))
        if aq and aq != "5":         cmd += ["--audio-quality", aq]
    if pp.get("embed_thumbnail"):    cmd.append("--embed-thumbnail")
    if pp.get("write_thumbnail"):    cmd.append("--write-thumbnail")
    if pp.get("embed_metadata"):     cmd.append("--embed-metadata")
    if pp.get("embed_chapters"):     cmd.append("--embed-chapters")
    if pp.get("convert_thumbnails"):
        cmd += ["--convert-thumbnails", pp["convert_thumbnails"]]

    if sb.get("enabled"):
        mc = sb.get("mark_cats", [])
        rc = sb.get("remove_cats", [])
        if mc: cmd += ["--sponsorblock-mark", ",".join(mc)]
        if rc: cmd += ["--sponsorblock-remove", ",".join(rc)]

    if cfg.get("extra_args"):        cmd += shlex.split(cfg["extra_args"])
    cmd.append(url)
    return cmd


class YtClipApp:
    def __init__(self):
        self.config = load_config()
        self.theme = get_theme(self.config.get("theme", "Studio Brutalism"))
        self.last_clip = ""
        self.watching = False
        self._dl_queue = queue.Queue()
        self._queued_urls = []
        self._queue_lock = threading.Lock()
        self._current_url = None
        self._log_q = queue.Queue()
        self._vars = {}
        self._filter_mode_lock = threading.Lock()
        self._filter_mode_val = self.config.get("filter_mode", "")
        self._proc_lock = threading.Lock()
        self._proc = None
        self._cancelled = False
        self._downloading = threading.Event()
        self._downloading.set()
        Path(self.config["download_dir"]).mkdir(parents=True, exist_ok=True)
        self.root = tk.Tk()
        self.root.title("yt-clip")
        self.root.minsize(780, 640)
        self._setup_styles()
        self._build_ui()
        self._apply_theme()
        self._poll_log()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        threading.Thread(target=self._worker, daemon=True).start()

    def _setup_styles(self):
        self._style = ttk.Style(self.root)
        self._style.theme_use("clam")

    def _apply_theme(self):
        t = self.theme
        s = self._style
        self.root.configure(bg=t["bg"])

        s.configure("TFrame", background=t["bg"])
        s.configure("TLabel", background=t["bg"], foreground=t["fg"],
                     font=("sans-serif", 10))
        s.configure("H.TLabel", background=t["bg"], foreground=t["accent"],
                     font=("sans-serif", 12, "bold"))
        s.configure("TCheckbutton", background=t["bg"], foreground=t["fg"],
                     font=("sans-serif", 10))
        s.map("TCheckbutton",
              background=[("active", t["bg"])],
              foreground=[("active", t["fg"])])
        s.configure("TRadiobutton", background=t["bg"], foreground=t["fg"],
                     font=("sans-serif", 9))
        s.map("TRadiobutton",
              background=[("active", t["bg"])],
              foreground=[("active", t["fg"])])
        s.configure("Go.TButton", background=t["accent"], foreground=t["bg"],
                     font=("sans-serif", 10, "bold"), padding=(12, 6))
        s.map("Go.TButton", background=[("active", t["accent_hover"])])
        s.configure("TButton", background=t["surface"], foreground=t["fg"],
                     font=("sans-serif", 10), padding=(10, 5))
        s.map("TButton", background=[("active", t["entry_bg"])])
        s.configure("TEntry", fieldbackground=t["entry_bg"], foreground=t["fg"],
                     insertcolor=t["fg"])
        s.configure("TNotebook", background=t["bg"], borderwidth=0)
        s.configure("TNotebook.Tab", background=t["surface"], foreground=t["fg"],
                     font=("sans-serif", 10), padding=(14, 6))
        s.map("TNotebook.Tab",
              background=[("selected", t["bg_sec"])],
              foreground=[("selected", t["accent"])])
        s.configure("TCombobox", fieldbackground=t["entry_bg"], foreground=t["fg"])
        s.configure("TSeparator", background=t["surface"])

        if hasattr(self, "_qlist"):
            self._qlist.configure(bg=t["bg_sec"], fg=t["fg"],
                                  selectbackground=t["surface"])
        if hasattr(self, "_log"):
            self._log.configure(bg=t["bg_sec"], fg=t["fg"],
                                insertbackground=t["fg"])
            self._log.tag_configure("ok", foreground=t["success"])
            self._log.tag_configure("err", foreground=t["accent"])
            self._log.tag_configure("info", foreground=t["warning"])
        if hasattr(self, "_bl_text"):
            self._bl_text.configure(bg=t["entry_bg"], fg=t["fg"],
                                    insertbackground=t["fg"])
        if hasattr(self, "_wl_text"):
            self._wl_text.configure(bg=t["entry_bg"], fg=t["fg"],
                                    insertbackground=t["fg"])
        if hasattr(self, "_status_lbl"):
            fg = t["success"] if self.watching else t["fg_dim"]
            self._status_lbl.config(foreground=fg)
        if hasattr(self, "_dl_status"):
            fg = t["success"] if self._downloading.is_set() else t["warning"]
            self._dl_status.config(foreground=fg)
        if hasattr(self, "_q_count"):
            self._q_count.config(foreground=t["fg_dim"])
        if hasattr(self, "_save_lbl"):
            self._save_lbl.config(foreground=t["success"])
        if hasattr(self, "_filter_hint_lbl"):
            self._filter_hint_lbl.config(foreground=t["fg_dim"])
        if hasattr(self, "_theme_swatches"):
            for swatch in self._theme_swatches.values():
                swatch.configure(highlightbackground=t["fg_dim"])
        if hasattr(self, "_theme_entries"):
            for key, ent in self._theme_entries.items():
                ent.configure(style="TEntry")

    def _chk(self, parent, sec, key, text, **kw):
        v = tk.BooleanVar(value=self.config[sec].get(key, False))
        self._vars[(sec, key)] = v
        ttk.Checkbutton(parent, text=text, variable=v).grid(sticky="w", **kw)

    def _entry(self, parent, sec, key, label, w=30, **kw):
        r = kw.pop("row"); c = kw.pop("column", 0)
        ttk.Label(parent, text=label).grid(row=r, column=c, sticky="w", padx=4, pady=2)
        v = tk.StringVar(value=str(self.config[sec].get(key, "")))
        self._vars[(sec, key)] = v
        ttk.Entry(parent, textvariable=v, width=w).grid(
            row=r, column=c+1, sticky="w", padx=4, pady=2, **kw)

    def _combo(self, parent, sec, key, vals, label, w=12, **kw):
        r = kw.pop("row"); c = kw.pop("column", 0)
        ttk.Label(parent, text=label).grid(row=r, column=c, sticky="w", padx=4, pady=2)
        v = tk.StringVar(value=self.config[sec].get(key, vals[0]))
        self._vars[(sec, key)] = v
        ttk.Combobox(parent, textvariable=v, values=vals, width=w,
                     state="readonly").grid(row=r, column=c+1, sticky="w", padx=4, pady=2)

    def _radios(self, parent, sec, key, vals, label, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=2)
        f = ttk.Frame(parent); f.grid(row=row, column=1, columnspan=3, sticky="w")
        v = tk.StringVar(value=self.config[sec].get(key, vals[0]))
        self._vars[(sec, key)] = v
        for fmt in vals:
            ttk.Radiobutton(f, text=fmt or "None", variable=v, value=fmt).pack(
                side="left", padx=4)

    def _tab_general(self, nb):
        f = ttk.Frame(nb); nb.add(f, text=" General ")
        p = ttk.Frame(f); p.pack(fill="both", padx=12, pady=8)

        ttk.Label(p, text="Download directory:").grid(row=0, column=0, sticky="w", padx=4)
        self._vars["download_dir"] = tk.StringVar(value=self.config["download_dir"])
        ttk.Entry(p, textvariable=self._vars["download_dir"], width=44).grid(
            row=0, column=1, padx=4, sticky="ew")
        ttk.Button(p, text="Browse", command=self._browse_dir).grid(row=0, column=2, padx=4)

        checks = [
            ("ignore_errors",    "-i / --ignore-errors"),
            ("no_abort_on_error","--no-abort-on-error"),
            ("abort_on_error",   "--abort-on-error"),
            ("no_playlist",      "--no-playlist"),
            ("live_from_start",  "--live-from-start"),
            ("mark_watched",     "--mark-watched"),
            ("restrict_filenames","--restrict-filenames"),
            ("no_overwrites",    "--no-overwrites"),
            ("write_description","--write-description"),
            ("write_info_json",  "--write-info-json"),
        ]
        for i, (key, label) in enumerate(checks):
            r, c = 1 + i // 3, i % 3
            self._chk(p, "general", key, label, row=r, column=c, padx=6, pady=1)

        br = 1 + (len(checks) - 1) // 3 + 1
        self._combo(p, "general", "cookies_from_browser", BROWSERS,
                    "Cookies from browser:", w=14, row=br, column=0)

    def _tab_format(self, nb):
        f = ttk.Frame(nb); nb.add(f, text=" Format ")
        p = ttk.Frame(f); p.pack(fill="both", padx=12, pady=8)

        self._entry(p, "format", "format", "-f / --format:", w=40, row=0)
        self._entry(p, "format", "format_sort", "-S / --format-sort:", w=40, row=1)
        self._radios(p, "format", "merge_output_format", MERGE_FMTS,
                     "Merge output format:", 2)
        self._entry(p, "format", "concurrent_fragments",
                    "Concurrent fragments:", w=6, row=3)
        self._entry(p, "format", "limit_rate",
                    "Rate limit (e.g. 50K):", w=12, row=4)
        self._entry(p, "format", "retries", "Retries:", w=6, row=5)

    def _tab_subtitles(self, nb):
        f = ttk.Frame(nb); nb.add(f, text=" Subtitles ")
        p = ttk.Frame(f); p.pack(fill="both", padx=12, pady=8)

        self._chk(p, "subtitles", "write_subs", "--write-subs",
                  row=0, column=0, padx=6)
        self._chk(p, "subtitles", "write_auto_subs", "--write-auto-subs",
                  row=0, column=1, padx=6)
        self._chk(p, "subtitles", "embed_subs", "--embed-subs",
                  row=0, column=2, padx=6)
        self._entry(p, "subtitles", "sub_langs",
                    "Languages (e.g. en,ja,all):", w=24, row=1)
        self._combo(p, "subtitles", "sub_format", SUB_FMTS,
                    "Subtitle format:", row=2)
        self._combo(p, "subtitles", "convert_subs", SUB_CONV,
                    "Convert subs to:", row=3)

    def _tab_postprocess(self, nb):
        f = ttk.Frame(nb); nb.add(f, text=" Post-Process ")
        p = ttk.Frame(f); p.pack(fill="both", padx=12, pady=8)

        self._radios(p, "postprocess", "remux_video", VIDEO_FMTS, "Remux video:", 0)
        self._radios(p, "postprocess", "recode_video", VIDEO_FMTS, "Recode video:", 1)

        self._chk(p, "postprocess", "extract_audio", "-x / Extract audio",
                  row=2, column=0, padx=6)
        self._combo(p, "postprocess", "audio_format", AUDIO_FMTS,
                    "Audio format:", row=3)
        self._entry(p, "postprocess", "audio_quality",
                    "Audio quality (0=best 10=worst):", w=6, row=4)

        self._chk(p, "postprocess", "embed_thumbnail", "--embed-thumbnail",
                  row=5, column=0, padx=6)
        self._chk(p, "postprocess", "write_thumbnail", "--write-thumbnail",
                  row=5, column=1, padx=6)
        self._chk(p, "postprocess", "embed_metadata", "--embed-metadata",
                  row=6, column=0, padx=6)
        self._chk(p, "postprocess", "embed_chapters", "--embed-chapters",
                  row=6, column=1, padx=6)
        self._combo(p, "postprocess", "convert_thumbnails", THUMB_FMTS,
                    "Convert thumbnails:", row=7)

    def _tab_sponsorblock(self, nb):
        f = ttk.Frame(nb); nb.add(f, text=" SponsorBlock ")
        p = ttk.Frame(f); p.pack(fill="both", padx=12, pady=8)

        self._chk(p, "sponsorblock", "enabled", "Enable SponsorBlock",
                  row=0, column=0, padx=6)

        ttk.Label(p, text="Mark as chapters:", style="H.TLabel").grid(
            row=1, column=0, columnspan=4, sticky="w", padx=4, pady=(8, 2))
        self._sb_mark = {}
        mf = ttk.Frame(p); mf.grid(row=2, column=0, columnspan=4, sticky="w")
        for i, cat in enumerate(SB_CATS):
            v = tk.BooleanVar(value=cat in self.config["sponsorblock"].get("mark_cats", []))
            self._sb_mark[cat] = v
            ttk.Checkbutton(mf, text=cat, variable=v).grid(
                row=i // 4, column=i % 4, sticky="w", padx=6)

        ttk.Label(p, text="Remove segments:", style="H.TLabel").grid(
            row=3, column=0, columnspan=4, sticky="w", padx=4, pady=(8, 2))
        self._sb_remove = {}
        rf = ttk.Frame(p); rf.grid(row=4, column=0, columnspan=4, sticky="w")
        for i, cat in enumerate(SB_CATS):
            v = tk.BooleanVar(value=cat in self.config["sponsorblock"].get("remove_cats", []))
            self._sb_remove[cat] = v
            ttk.Checkbutton(rf, text=cat, variable=v).grid(
                row=i // 4, column=i % 4, sticky="w", padx=6)

    def _load_filter_list(self, path):
        if path.exists():
            return [l for l in path.read_text().splitlines() if l.strip()]
        return []

    def _save_filter_list(self, path, lines):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n" if lines else "")

    def _url_matches_filter(self, url, patterns):
        for pat in patterns:
            pat = pat.strip()
            if not pat:
                continue
            if fnmatch.fnmatchcase(url.lower(), pat.lower()):
                return True
        return False

    def _tab_filtering(self, nb):
        f = ttk.Frame(nb); nb.add(f, text=" Filtering ")
        p = ttk.Frame(f); p.pack(fill="both", expand=True, padx=12, pady=8)

        ctrl = ttk.Frame(p); ctrl.pack(fill="x", pady=(0, 6))
        ttk.Label(ctrl, text="Filtering mode:").pack(side="left", padx=4)
        self._filter_mode = tk.StringVar(
            value=self.config.get("filter_mode", ""))
        for val, label in [("", "Off"), ("blacklist", "Use Blacklist"),
                           ("whitelist", "Use Whitelist")]:
            ttk.Radiobutton(ctrl, text=label, variable=self._filter_mode,
                            value=val).pack(side="left", padx=6)
        self._filter_mode.trace_add("write",
            lambda *_: self._on_filter_mode_change())

        panes = ttk.Frame(p); panes.pack(fill="both", expand=True)
        panes.columnconfigure(0, weight=1)
        panes.columnconfigure(1, weight=1)

        lf_bl = ttk.Frame(panes); lf_bl.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        ttk.Label(lf_bl, text="Blacklist (one pattern per line):",
                  style="H.TLabel").pack(anchor="w")
        self._bl_text = tk.Text(lf_bl, height=8, bg=self.theme["entry_bg"],
                                fg=self.theme["fg"],
                                insertbackground=self.theme["fg"],
                                font=("monospace", 9),
                                highlightthickness=0, bd=0, wrap="word")
        self._bl_text.pack(fill="both", expand=True, pady=2)
        bl_lines = self._load_filter_list(BLACKLIST_PATH)
        if bl_lines:
            self._bl_text.insert("1.0", "\n".join(bl_lines))

        lf_wl = ttk.Frame(panes); lf_wl.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        ttk.Label(lf_wl, text="Whitelist (one pattern per line):",
                  style="H.TLabel").pack(anchor="w")
        self._wl_text = tk.Text(lf_wl, height=8, bg=self.theme["entry_bg"],
                                fg=self.theme["fg"],
                                insertbackground=self.theme["fg"],
                                font=("monospace", 9),
                                highlightthickness=0, bd=0, wrap="word")
        self._wl_text.pack(fill="both", expand=True, pady=2)
        wl_lines = self._load_filter_list(WHITELIST_PATH)
        if wl_lines:
            self._wl_text.insert("1.0", "\n".join(wl_lines))

        hint = ttk.Frame(p); hint.pack(fill="x", pady=(4, 0))
        self._filter_hint_lbl = ttk.Label(
            hint, text="Patterns use glob syntax: https://youtube.com/* , *reddit.com/*, https://example.com/*",
            foreground=self.theme["fg_dim"])
        self._filter_hint_lbl.pack(anchor="w")

    def _tab_theme(self, nb):
        f = ttk.Frame(nb); nb.add(f, text=" Theme ")
        p = ttk.Frame(f); p.pack(fill="both", expand=True, padx=12, pady=8)

        sel = ttk.Frame(p); sel.pack(fill="x", pady=(0, 8))
        ttk.Label(sel, text="Theme:").pack(side="left", padx=4)
        self._theme_var = tk.StringVar(
            value=self.config.get("theme", "Studio Brutalism"))
        for name in THEME_NAMES:
            ttk.Radiobutton(sel, text=name, variable=self._theme_var,
                            value=name,
                            command=self._on_theme_change).pack(
                                side="left", padx=6)

        ttk.Label(p, text="Custom theme colors (hex):",
                  style="H.TLabel").pack(anchor="w", pady=(4, 4))

        grid = ttk.Frame(p); grid.pack(fill="x")
        self._theme_entries = {}
        self._theme_svars = {}
        self._theme_swatches = {}
        custom = _load_custom_theme()
        labels = {
            "bg": "Background", "bg_sec": "Card / Panel",
            "fg": "Text", "fg_dim": "Muted text",
            "accent": "Accent", "success": "Success",
            "warning": "Warning", "surface": "Button / Tab",
            "entry_bg": "Input field", "accent_hover": "Accent hover",
        }
        for i, key in enumerate(THEME_KEYS):
            r, c = i // 2, (i % 2) * 3
            ttk.Label(grid, text=labels.get(key, key) + ":").grid(
                row=r, column=c, sticky="w", padx=4, pady=2)
            swatch = tk.Canvas(grid, width=18, height=18,
                               highlightthickness=1,
                               highlightbackground=self.theme["fg_dim"])
            swatch.grid(row=r, column=c + 1, padx=(0, 2), pady=2)
            color = custom.get(key, self.theme[key])
            swatch.configure(bg=color)
            self._theme_swatches[key] = swatch
            sv = tk.StringVar(value=color)
            sv.trace_add("write", lambda *_a, k=key, v=sv: self._on_swatch_edit(k, v))
            ent = ttk.Entry(grid, textvariable=sv, width=10)
            ent.grid(row=r, column=c + 2, sticky="w", padx=4, pady=2)
            self._theme_entries[key] = ent
            self._theme_svars[key] = sv

        self._custom_enabled = self._theme_var.get() == "Custom"
        self._set_custom_entries_state()

    def _on_swatch_edit(self, key, sv):
        val = sv.get().strip()
        if re.fullmatch(r'#[0-9a-fA-F]{6}', val):
            self._theme_swatches[key].configure(bg=val)

    def _set_custom_entries_state(self):
        st = "normal" if self._theme_var.get() == "Custom" else "disabled"
        for ent in self._theme_entries.values():
            ent.configure(state=st)

    def _on_theme_change(self):
        name = self._theme_var.get()
        self._set_custom_entries_state()
        if name == "Custom":
            custom = {}
            for key, ent in self._theme_entries.items():
                val = self._theme_svars[key].get().strip()
                if re.fullmatch(r'#[0-9a-fA-F]{6}', val):
                    custom[key] = val
            base = _load_custom_theme()
            base.update(custom)
            self.theme = base
        else:
            self.theme = get_theme(name)
            for key in THEME_KEYS:
                self._theme_svars[key].set(self.theme[key])
        self.config["theme"] = name
        self._apply_theme()

    def _build_ui(self):
        pad = {"padx": 8, "pady": 3}
        m = ttk.Frame(self.root)
        m.pack(fill="both", expand=True, padx=6, pady=6)

        top = ttk.Frame(m); top.pack(fill="x", **pad)
        self._watch_btn = ttk.Button(top, text="Start Watching Clipboard",
                                     style="Go.TButton", command=self._toggle_watch)
        self._watch_btn.pack(side="left")
        self._status_lbl = ttk.Label(top, text="Stopped",
                                     foreground=self.theme["fg_dim"])
        self._status_lbl.pack(side="left", padx=12)

        self._dl_btn = ttk.Button(top, text="Pause Downloads",
                                  command=self._toggle_downloads)
        self._dl_btn.pack(side="left", padx=(12, 0))
        self._cancel_btn = ttk.Button(top, text="Cancel Current",
                                      command=self._cancel_current)
        self._cancel_btn.pack(side="left", padx=(6, 0))
        self._dl_status = ttk.Label(top, text="Downloads: running",
                                     foreground=self.theme["success"])
        self._dl_status.pack(side="left", padx=8)

        nb = ttk.Notebook(m); nb.pack(fill="x", **pad)
        self._tab_general(nb)
        self._tab_format(nb)
        self._tab_subtitles(nb)
        self._tab_postprocess(nb)
        self._tab_sponsorblock(nb)
        self._tab_filtering(nb)
        self._tab_theme(nb)

        sf = ttk.Frame(m); sf.pack(fill="x", **pad)
        ttk.Label(sf, text="Extra args:").pack(side="left")
        self._vars["extra_args"] = tk.StringVar(value=self.config.get("extra_args", ""))
        ttk.Entry(sf, textvariable=self._vars["extra_args"], width=55).pack(
            side="left", fill="x", expand=True, padx=6)
        ttk.Button(sf, text="Save Settings", command=self._save_settings).pack(side="left", padx=(6, 0))
        self._save_lbl = ttk.Label(sf, text="", foreground=self.theme["success"])
        self._save_lbl.pack(side="left", padx=6)

        ttk.Separator(m).pack(fill="x", pady=6, padx=8)

        qh = ttk.Frame(m); qh.pack(fill="x", **pad)
        ttk.Label(qh, text="Download Queue", style="H.TLabel").pack(side="left")
        self._q_count = ttk.Label(qh, text="(empty)",
                                   foreground=self.theme["fg_dim"])
        self._q_count.pack(side="left", padx=8)

        uf = ttk.Frame(m); uf.pack(fill="x", **pad)
        self._url_var = tk.StringVar()
        ttk.Entry(uf, textvariable=self._url_var, width=56).pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(uf, text="Add URL", command=self._add_url).pack(side="left")

        self._qlist = tk.Listbox(m, height=4, bg=self.theme["bg_sec"],
                                  fg=self.theme["fg"],
                                  selectbackground=self.theme["surface"],
                                  highlightthickness=0,
                                  bd=0, font=("monospace", 9))
        self._qlist.pack(fill="x", **pad)
        self._qlist.bind("<Delete>", self._delete_queued)

        self._log = scrolledtext.ScrolledText(
            m, height=8, bg=self.theme["bg_sec"], fg=self.theme["fg"],
            insertbackground=self.theme["fg"],
            highlightthickness=0, bd=0, font=("monospace", 9),
            state="disabled", wrap="word")
        self._log.pack(fill="both", expand=True, **pad)
        self._log.tag_configure("ok", foreground=self.theme["success"])
        self._log.tag_configure("err", foreground=self.theme["accent"])
        self._log.tag_configure("info", foreground=self.theme["warning"])

    def _read_gui(self):
        self.config["download_dir"] = self._vars["download_dir"].get()
        self.config["extra_args"] = self._vars["extra_args"].get().strip()
        for k, var in self._vars.items():
            if not isinstance(k, tuple):
                continue
            sec, key = k
            if sec in self.config and isinstance(self.config[sec], dict):
                default = self.config[sec].get(key)
                val = var.get()
                if isinstance(default, bool):
                    self.config[sec][key] = bool(val)
                else:
                    self.config[sec][key] = str(val)
        self.config["sponsorblock"]["mark_cats"] = [
            c for c, v in self._sb_mark.items() if v.get()]
        self.config["sponsorblock"]["remove_cats"] = [
            c for c, v in self._sb_remove.items() if v.get()]
        self.config["filter_mode"] = self._filter_mode.get()
        with self._filter_mode_lock:
            self._filter_mode_val = self.config["filter_mode"]
        self.config["theme"] = self._theme_var.get()

    def _get_snapshot(self):
        snap = {}
        ev = threading.Event()
        def _sync():
            self._read_gui()
            snap.update(json.loads(json.dumps(self.config)))
            ev.set()
        self.root.after_idle(_sync)
        ev.wait(timeout=5.0)
        if not ev.is_set():
            snap.update(json.loads(json.dumps(self.config)))
        return snap

    def _browse_dir(self):
        d = filedialog.askdirectory(initialdir=self._vars["download_dir"].get())
        if d: self._vars["download_dir"].set(d)

    def _save_settings(self):
        self._read_gui()
        save_config(self.config)
        if self._theme_var.get() == "Custom":
            custom = {}
            for key, ent in self._theme_entries.items():
                val = self._theme_svars[key].get().strip()
                if re.fullmatch(r'#[0-9a-fA-F]{6}', val):
                    custom[key] = val
            _save_custom_theme(custom)
        bl = [l for l in self._bl_text.get("1.0", "end").splitlines() if l.strip()]
        wl = [l for l in self._wl_text.get("1.0", "end").splitlines() if l.strip()]
        self._save_filter_list(BLACKLIST_PATH, bl)
        self._save_filter_list(WHITELIST_PATH, wl)
        Path(self.config["download_dir"]).mkdir(parents=True, exist_ok=True)
        self._save_lbl.config(text="Saved!")
        self.root.after(2000, lambda: self._save_lbl.config(text=""))

    def _toggle_watch(self):
        if self.watching:
            self.watching = False
            self._watch_btn.config(text="Start Watching Clipboard")
            self._status_lbl.config(text="Stopped",
                                    foreground=self.theme["fg_dim"])
            self._logm("[yt-clip] Watcher stopped.", "info")
        else:
            with self._filter_mode_lock:
                self._filter_mode_val = self._filter_mode.get()
            self.watching = True
            self._watch_btn.config(text="Stop Watching Clipboard")
            self._status_lbl.config(text="Watching...",
                                    foreground=self.theme["success"])
            threading.Thread(target=self._clipboard_loop, daemon=True).start()
            self._logm("[yt-clip] Watching clipboard", "info")

    def _toggle_downloads(self):
        if self._downloading.is_set():
            self._downloading.clear()
            self._dl_btn.config(text="Resume Downloads")
            self._dl_status.config(text="Downloads: paused",
                                   foreground=self.theme["warning"])
            self._logm("Downloads paused (current download will finish)", "info")
        else:
            self._downloading.set()
            self._dl_btn.config(text="Pause Downloads")
            self._dl_status.config(text="Downloads: running",
                                   foreground=self.theme["success"])
            self._logm("Downloads resumed", "info")

    def _cancel_current(self):
        with self._proc_lock:
            if self._proc:
                self._cancelled = True
                self._proc.terminate()
                self._logm("Cancelled current download", "info")
            else:
                self._logm("No download in progress", "info")

    def _delete_queued(self, _event=None):
        sel = self._qlist.curselection()
        if not sel:
            return
        idx = sel[0]
        with self._queue_lock:
            if idx >= len(self._queued_urls):
                return
            url = self._queued_urls[idx]
            if url == self._current_url:
                self._logm("Can't remove the active download (use Cancel Current)", "info")
                return
            self._queued_urls.remove(url)
            new_q = queue.Queue()
            for u in self._queued_urls:
                if u != self._current_url:
                    new_q.put(u)
            self._dl_queue = new_q
        self._logm(f"- removed: {url}", "info")
        self._refresh_q()

    def _on_filter_mode_change(self):
        with self._filter_mode_lock:
            self._filter_mode_val = self._filter_mode.get()

    def _add_url(self):
        url = self._url_var.get().strip()
        if not url: return
        self._url_var.set("")
        if URL_PATTERN.match(url):
            self._enqueue(url)
        else:
            self._logm(f"Not a valid URL: {url}", "err")

    def _enqueue(self, url, from_clipboard=False):
        with self._filter_mode_lock:
            mode = self._filter_mode_val
        if mode == "whitelist":
            patterns = self._load_filter_list(WHITELIST_PATH)
            if not self._url_matches_filter(url, patterns):
                if not from_clipboard:
                    self._logm(f"Skipped (not on whitelist): {url}", "info")
                return
        elif mode == "blacklist":
            patterns = self._load_filter_list(BLACKLIST_PATH)
            if self._url_matches_filter(url, patterns):
                if not from_clipboard:
                    self._logm(f"Blocked (on blacklist): {url}", "info")
                return
        with self._queue_lock:
            if url in self._queued_urls:
                if not from_clipboard:
                    self._logm(f"Already queued: {url}", "info")
                return
            self._queued_urls.append(url)
        self._dl_queue.put(url)
        self._logm(f"+ queued: {url}", "info")
        self._refresh_q()

    def _worker(self):
        while True:
            url = self._dl_queue.get()
            self._downloading.wait()
            self._current_url = url
            self._refresh_q()
            snap = self._get_snapshot()
            cmd = build_cmd(url, snap)
            self._logm(f"Downloading: {url}")
            with self._proc_lock:
                self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                              stderr=subprocess.STDOUT, text=True)
                proc = self._proc
            for line in proc.stdout:
                self._logm("  " + line.rstrip())
            proc.wait()
            with self._proc_lock:
                self._proc = None
                cancelled = self._cancelled
                self._cancelled = False
            if cancelled:
                self._logm(f"Cancelled: {url}", "info")
            elif proc.returncode == 0:
                self._logm(f"Done: {url}", "ok")
            else:
                self._logm(f"Failed (exit {proc.returncode}): {url}", "err")
                fp = Path(snap["download_dir"]) / "failed.txt"
                existing = set()
                if fp.exists():
                    existing = set(fp.read_text().splitlines())
                if url not in existing:
                    with open(fp, "a") as fh: fh.write(url + "\n")
                self._logm(f"Saved to {fp}", "info")
            with self._queue_lock:
                if url in self._queued_urls: self._queued_urls.remove(url)
            self._current_url = None
            self._refresh_q()
            self._dl_queue.task_done()

    def _clipboard_loop(self):
        while self.watching:
            try:
                cur = pyperclip.paste()
                if cur != self.last_clip:
                    self.last_clip = cur
                    m = URL_PATTERN.search(cur)
                    if m:
                        self._enqueue(m.group(0), from_clipboard=True)
            except Exception as e:
                self._logm(f"Clipboard error: {e}", "err")
            time.sleep(0.5)

    def _logm(self, text, tag=None):
        self._log_q.put((text, tag))

    def _poll_log(self):
        while not self._log_q.empty():
            text, tag = self._log_q.get_nowait()
            self._log.config(state="normal")
            self._log.insert("end", text + "\n", (tag,) if tag else ())
            self._log.config(state="disabled")
            self._log.see("end")
        self.root.after(100, self._poll_log)

    def _refresh_q(self):
        self.root.after_idle(self._do_refresh_q)

    def _do_refresh_q(self):
        self._qlist.delete(0, "end")
        with self._queue_lock:
            urls = list(self._queued_urls)
        for url in urls:
            pfx = "  >> Downloading: " if url == self._current_url else "     Queued: "
            self._qlist.insert("end", pfx + url)
        n = len(urls)
        self._q_count.config(
            text=f"({n} item{'s' if n != 1 else ''})" if n else "(empty)")

    def _on_close(self):
        self.watching = False
        with self._proc_lock:
            if self._proc:
                self._proc.terminate()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    YtClipApp().run()
