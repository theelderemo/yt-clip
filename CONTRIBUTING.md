# Contributing

Contributions are welcome. yt-clip is a single-file tkinter app and the goal is to keep it simple and dependency-light.

## Getting started

1. Fork and clone the repo.
2. Create a venv and install the one dependency:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pyperclip
```

3. Run the app:

```bash
python3 yt_clip.py
```

## Guidelines

### Code style

- The project is a single file (`yt_clip.py`). Keep it that way unless there's a strong reason to split.
- No external GUI frameworks — tkinter only.
- Keep the dependency list minimal. New pip dependencies need a good justification.
- No type stubs or heavy linting configs — just keep it readable.

### Commits

- Write clear, concise commit messages.
- One logical change per commit.
- Reference issue numbers where applicable.

### Pull requests

- Open an issue first if the change is non-trivial (new feature, large refactor).
- Keep PRs focused — don't mix unrelated changes.
- Test your changes on at least one platform before submitting.
- Make sure `python3 -c "import ast; ast.parse(open('yt_clip.py').read())"` passes.

### What to work on

- Bug fixes are always welcome.
- Check the issue tracker for open items.
- Feature ideas: tray icon, progress bars, per-URL format overrides, playlist handling — open an issue to discuss first.

### What to avoid

- Adding Electron, Qt, or other heavy GUI frameworks.
- Adding dependencies that don't work cross-platform.
- Vendoring large libraries into the repo.

## Reporting bugs

Open an issue with:

- Your OS and Python version (`python3 --version`)
- yt-dlp version (`yt-dlp --version`)
- Steps to reproduce
- The error output from the log panel or terminal

## License

By contributing, you agree that your contributions will be licensed under the [MIT](LICENSE) license.
