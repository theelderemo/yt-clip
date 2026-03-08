# yt-clip

A GUI clipboard watcher that automatically downloads URLs using [yt-dlp](https://github.com/yt-dlp/yt-dlp). Copy a link, it gets queued. Single-file Python + tkinter, no Electron, no bloat.

## Features

- **Clipboard watcher** - monitors your clipboard and auto-queues any URL it finds (controlled via a filter list, see below)
- **Download queue** - queued URLs download sequentially; pause/resume at any time
- **Full yt-dlp settings GUI** - format selection, subtitles, post-processing, SponsorBlock, cookies, and more
- **URL filtering** - whitelist or blacklist URLs by glob pattern (e.g. `*youtube.com/*`)
- **Theming** - 4 built-in dark themes (Studio Brutalism, Midnight, Vapor, Retro) + fully custom hex editor
- **Persistent config** - settings, theme, and filter lists saved to `~/.config/yt-clip/`
- **Manual URL entry** - paste a URL directly if you don't want clipboard watching

## Requirements

- Python 3.9+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) installed and on your `PATH`
- tkinter (usually included with Python; on Debian/Ubuntu: `sudo apt install python3-tk`)
- [ffmpeg](https://github.com/FFmpeg/FFmpeg) (required by yt-dlp for merging/remuxing)
- tkinter  — usually bundled with Python; on Debian/Ubuntu: sudo apt install python3-tk

## Install

```bash
git clone https://github.com/theelderemo/yt-clip.git
cd ytclip
pip install pyperclip
```

Or with a venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pyperclip
```

## Usage

```bash
python3 yt_clip.py
```

1. Click **Start Watching Clipboard** to begin monitoring.
2. Copy any URL - it appears in the download queue automatically.
3. Or type/paste a URL into the entry field and click **Add URL**.
4. Adjust settings in the tabs (General, Format, Subtitles, Post-Process, SponsorBlock, Filtering, Theme).
5. Click **Save Settings** to persist everything.

### Tabs

| Tab | What |
|---|---|
| General | Download directory, error handling, playlist behavior, cookies |
| Format | Format string, sort order, merge format, concurrency, rate limit |
| Subtitles | Write/embed subs, languages, format, conversion |
| Post-Process | Remux, recode, extract audio, thumbnails, metadata, chapters |
| SponsorBlock | Mark or remove sponsor segments by category |
| Filtering | Whitelist or blacklist URLs by glob pattern |
| Theme | Switch between built-in themes or create a custom one |

### Filtering

Set the mode to **Use Whitelist** or **Use Blacklist**, then add patterns (one per line):

```
*youtube.com/*
*youtu.be/*
*reddit.com/r/*/comments/*
```

Patterns use glob syntax (`*` matches anything). Whitelist mode silently ignores non-matching clipboard URLs. Blacklist mode blocks matching URLs.

### Themes

Four built-in dark themes adapted from the VRSA Studio design system:

- **Studio Brutalism** - dark monochrome + orange accent (default)
- **Midnight** - near-black + purple accent
- **Vapor** - deep purple + hot pink accent, teal highlights
- **Retro** - warm brown-black + amber CRT aesthetic

Select **Custom** to edit all 10 color slots with hex values. Custom themes are saved to `~/.config/yt-clip/custom_theme.json`.

## Config files

All stored under `~/.config/yt-clip/`:

| File | Purpose |
|---|---|
| `config.json` | All settings (download dir, yt-dlp flags, theme choice, filter mode) |
| `custom_theme.json` | Custom theme hex colors |
| `whitelist.txt` | Whitelist patterns, one per line |
| `blacklist.txt` | Blacklist patterns, one per line |

The download directory (default `~/Downloads/ytdlp/`) contains:

| File | Purpose |
|---|---|
| `failed.txt` | URLs that failed to download (deduplicated) |

## License

[MIT](LICENSE)
