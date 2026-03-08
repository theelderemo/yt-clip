# Security Policy

## Supported Versions

Only the latest version of yt-clip is actively maintained and receives security fixes.

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public issue.
2. Instead, use GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability) feature on the repository.
3. Include a description of the vulnerability, steps to reproduce, and any potential impact.

You should expect an initial response within 72 hours. I will work with you to understand the issue and coordinate a fix before any public disclosure.

## Scope

yt-clip is a local GUI tool that shells out to `yt-dlp`. Security considerations include:

- **Arbitrary command execution** — yt-clip passes user-supplied URLs and configuration to `yt-dlp` via subprocess. Input handling should prevent injection.
- **Clipboard content** — the clipboard watcher processes anything on the clipboard. Malformed or adversarial clipboard content should not cause unexpected behavior.
- **Config file handling** — settings are read from and written to `~/.config/yt-clip/`. Malformed config files should not lead to code execution.

Issues in `yt-dlp` itself should be reported to the [yt-dlp project](https://github.com/yt-dlp/yt-dlp/security).
