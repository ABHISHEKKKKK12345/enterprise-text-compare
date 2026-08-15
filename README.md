# Enterprise Text Compare

A local-first, enterprise-grade desktop application for comparing two text
sources — files or pasted text — with line, word, and character-level
diffing, a professional PySide6 GUI, background (non-blocking) comparison,
and export to HTML/TXT/JSON/CSV/Markdown.

Version 1.0.0

---

## 1. Overview

Enterprise Text Compare lets you compare two text sources and clearly see
what was added, removed, modified, or left unchanged. It is built as a
layered, testable application — a GUI-independent comparison engine at the
core, a thin service layer, and a PySide6 GUI on top — rather than a single
monolithic script.

All comparison happens **entirely on your machine**. No document content is
ever transmitted anywhere; the application requires no network access.

## 2. Features

- Line, word, and character-level comparison modes
- Added / removed / modified / unchanged classification with a clear visual
  hierarchy (color **and** row-level context — differences are never
  communicated by color alone)
- Configurable normalization: case sensitivity, leading/trailing whitespace,
  repeated spaces, blank lines, line-ending differences (CRLF/LF/CR), and
  Unicode (NFC) normalization
- Side-by-side diff view in a single synchronized table (line numbers, no
  scroll drift between the two sides)
- Difference navigation: first / previous / next / last, with a
  "Difference N of M" counter
- In-result search with next/previous match (F3 / Shift+F3)
- Font size (zoom) controls
- Paste, open file, or drag-and-drop for each source panel; clear, copy, and
  save-as actions
- Automatic encoding detection (UTF-8, UTF-8 BOM, UTF-16, ASCII, and common
  legacy 8-bit encodings) with graceful fallback
- Background comparison on a worker thread — the GUI never blocks — with a
  progress bar and cooperative cancellation
- Export to HTML (styled report), TXT, JSON (machine-readable), CSV, and
  Markdown
- Light and dark themes
- Persisted settings (comparison options, appearance, performance, logging)
- Enterprise-grade error handling: every anticipated failure mode produces a
  friendly message plus an error ID; raw tracebacks are never shown by
  default but remain available behind "Technical Details"
- Rotating application/error logs; document content is never written to logs

## 3. GUI Overview

```
+--------------------------------------------------------------+
| Enterprise Text Compare   Version 1.0.0     [Settings] [Help]|
+--------------------------------------------------------------+
| [Source A: Open | Clear | Copy | Save]  [Source B: ...]      |
|   (paste text or drop a file into either panel)               |
+--------------------------------------------------------------+
| [Compare] [Cancel] [Settings] [Export]         (progress bar) |
+--------------------------------------------------------------+
| [Search...] [<] [>]      [|<] [<] [>] [>|]  Diff 3 of 12  A- A+|
|  A#  Source A                    B#  Source B                |
|  1   unchanged line              1   unchanged line           |
|  2   removed line                                             |
|                                   2   added line               |
|  3   old text here      ~        3   new text here            |
+--------------------------------------------------------------+
| Lines Compared: 1248  Added: 37  Removed: 21  Modified: 14 …  |
+--------------------------------------------------------------+
| Status bar                                                    |
+--------------------------------------------------------------+
```

The diff view is a **single** table with four columns (A line number,
Source A content, B line number, Source B content), so the two sides always
scroll in lock-step — there is only one scrollbar, so synchronized scrolling
is correct by construction rather than something that can drift.

## 4. Architecture

```
app/
├── main.py            Entry point (python -m app.main)
├── application.py      Bootstrap: logging, QApplication, exception hook
├── core/               Domain models, enums, exceptions, constants
├── comparison/         GUI-independent comparison engine
│   ├── engine.py           Orchestrates alignment + inline diff + stats
│   ├── line_diff.py        Line alignment (difflib.SequenceMatcher)
│   ├── word_diff.py        Word-level inline diff (also backs char diff)
│   ├── char_diff.py        Character-level inline diff
│   ├── normalization.py    Whitespace/case/Unicode normalization
│   └── statistics.py       Added/removed/modified/unchanged counts
├── io/                  File reading/writing, encoding detection
├── services/            ComparisonService, ExportService, SettingsService,
│                        FileService — orchestration layer between the GUI
│                        and the domain/IO layers
├── gui/                 PySide6 GUI (widgets, dialogs, workers, styles)
├── config/              Platform-appropriate settings/log/cache directories
└── utils/               Logging setup, global error handler, helpers
```

**Design principle:** `app/comparison/` has zero Qt/PySide6 imports. It can
be imported and used from a plain script or unit test with no display
server available — see `tests/unit/test_engine.py`. The GUI layer only ever
calls into services; it never runs diff algorithms or file I/O inline in an
event handler.

### Data flow

1. `SourcePanel` (GUI) collects text/file input.
2. File loads go through `FileLoadWorker` (background `QThread`) →
   `ComparisonService.load_source_from_file` → `app.io.file_reader` (which
   detects encoding and returns a `SourceDocument` + `FileMetadata`).
3. Comparison goes through `ComparisonWorker` (background `QThread`) →
   `ComparisonService.compare` → `ComparisonEngine.compare`, which produces
   a `ComparisonResult` (list of `Difference` + `DifferenceStatistics`).
4. `DiffView` renders the result via a `QAbstractTableModel`
   (`DiffTableModel`) and a custom delegate that draws inline word/character
   highlight spans as rich text.
5. `ExportService` renders a `ComparisonResult` to HTML/TXT/JSON/CSV/MD.

## 5. Requirements

- Python 3.11 or later
- PySide6 6.6+ (Qt 6)
- `charset-normalizer` (optional but recommended; improves encoding
  detection — the app runs without it via a fallback encoding chain)

See `requirements.txt` / `pyproject.toml` for exact pins. No other runtime
dependencies are used.

## 6. Installation

**Recommended entry point: `run.py`.** Run it with `python run.py` from the
project root on every platform. `app/main.py` is an internal package module
(imported as `app.main`) — it is not meant to be double-clicked or executed
directly as `python app/main.py`; use either `python run.py` or
`python -m app.main` instead, both of which correctly set up the package
import path.

### Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks the activation script with an execution-policy error,
run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or activate
via `.venv\Scripts\activate.bat` from `cmd.exe` instead.

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### All platforms — development extras (tests, packaging)

```bash
python -m pip install -r requirements-dev.txt
```

## 7. Running from Source

```bash
python run.py
# or, equivalently:
python -m app.main
```

On Windows this is exactly `python run.py` (or `py run.py` if using the
Python launcher) from a PowerShell or cmd.exe terminal with the virtual
environment activated — there is nothing platform-specific about invoking
it. `run.py` carries a standard Unix shebang line
(`#!/usr/bin/env python3`) so it can also be executed directly as
`./run.py` from a Unix shell (Linux/macOS/WSL) once marked executable;
Windows' `python.exe` simply ignores that line as a comment when you run
`python run.py`, so its presence does not affect Windows users.

### Running from VS Code

1. Open the project root folder in VS Code.
2. Install the official **Python** extension (`ms-python.python`) if
   prompted — this project's `.vscode/extensions.json` recommends it.
3. Select the project's interpreter: `Ctrl+Shift+P` / `Cmd+Shift+P` →
   **Python: Select Interpreter** → choose `.venv` (VS Code auto-detects it
   once created as above).
4. Press **F5**, or open the Run and Debug panel and choose
   **"Enterprise Text Compare (run.py)"** — this project's
   `.vscode/launch.json` runs `run.py` through the Python extension's
   `debugpy` debugger, using whichever interpreter you selected in step 3,
   with breakpoints fully supported. This works identically on Windows,
   Linux, and macOS.

**Avoid running `run.py` via the "Code Runner" extension or any mechanism
that executes the file directly as a shell script** (e.g. `./run.py` from
a Git Bash/MSYS terminal on Windows). Doing so causes the *shell* — not
Python — to read the file's first line and try to launch its own
interpreter for it; on a minimal Windows/Git-Bash environment
`/usr/bin/env` typically is not on `PATH`, producing an
`'/usr/bin/env' is not recognized...` error. This is a property of how
that shell executes files, not of the project itself — `python run.py`
(via a terminal, a VS Code task, or the provided `launch.json`) always
invokes the interpreter directly and never triggers shebang parsing at
all. If you use Code Runner, configure it to run `python run.py` from the
project root rather than "Run" the file directly; the included
`.vscode/tasks.json` ("Run Enterprise Text Compare", accessible via
`Ctrl+Shift+P` → **Tasks: Run Task**) provides an already-correct
alternative that needs no extension at all.

## 8. Testing

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

(`python -m pytest` is used rather than a bare `pytest` command so it
unambiguously runs under the currently-active virtual environment's
interpreter on every platform, including Windows.) From VS Code, use
**Run Task → "Run Tests (pytest)"**, or the **"Run All Tests (pytest)"**
configuration in the Run and Debug panel (`.vscode/launch.json`) to run
with breakpoints enabled.

Test layout:

- `tests/unit/` — comparison engine, normalization, word/char diff,
  encoding detection, error handler. No Qt dependency.
- `tests/integration/` — file reader edge cases (missing file, permission
  denied, BOM/UTF-16, unsupported/binary files, huge-file confirmation),
  comparison service, export service (HTML/TXT/JSON/CSV/MD), settings
  persistence.
- `tests/gui/` — headless GUI smoke tests (main window construction, text
  input, the real `QThread`-backed compare action, export, theme
  switching). Runs via the Qt `offscreen` platform plugin automatically
  (see `tests/conftest.py`); no display server is required.

Last full run: **71 passed, 1 skipped** (the skipped test simulates a
POSIX permission-denied file and is skipped automatically when running as
root, since permission checks don't apply).

## 9. Configuration

Settings are persisted as JSON in the OS-appropriate configuration
directory (resolved via Qt's `QStandardPaths`, never hard-coded):

- Windows: `%APPDATA%\EnterpriseTextCompare\`
- Linux: `~/.config/EnterpriseTextCompare/` (or `$XDG_CONFIG_HOME`)
- macOS: `~/Library/Application Support/EnterpriseTextCompare/`

Logs and cache follow the same pattern via `AppDataLocation` /
`CacheLocation`. A corrupted or missing settings file never prevents
startup — the application silently falls back to defaults and logs a
warning.

Configurable via the Settings dialog (Comparison / Appearance / Performance
/ Logging tabs): comparison mode and normalization options, theme, font,
default export format, worker thread count, large-file threshold, and log
level.

## 10. Supported File Types

Treated as text: `.txt .log .csv .json .xml .html .htm .md .yaml .yml` and
common source/config files (`.py .java .js .ts .c .cpp .h .hpp .cs .go .rs
.rb .php .sql .ini .cfg .conf .toml .sh .bat .ps1` and others — see
`SUPPORTED_TEXT_EXTENSIONS` in `app/core/constants.py`). Files with no
extension are also allowed. Anything else — or any file whose first 8KB
contains a NUL byte (a strong binary indicator; UTF-16/UTF-32 BOM-prefixed
files are explicitly exempted from this check since they legitimately
contain NUL bytes) — is rejected with a clear "unsupported/binary file"
message rather than corrupting the display.

Encoding handling: UTF-8, UTF-8 BOM, UTF-16 (BOM-detected), ASCII, and a
fallback chain through common legacy 8-bit encodings (cp1252, latin-1).
`latin-1` never fails to decode, so detection always degrades gracefully
(lower confidence) rather than raising. Line endings CRLF/LF/CR are all
read correctly; normalization only affects comparison, never the displayed
original text, and files are **never modified** during read, compare, or
export.

## 11. Comparison Modes

- **Line** — compares complete lines (default).
- **Word** — compares changed lines word-by-word, highlighting exactly
  which words differ.
- **Character** — compares changed lines character-by-character.

Independent toggles: case sensitivity, ignore leading/trailing whitespace,
ignore repeated spaces, ignore blank lines, ignore line-ending differences,
Unicode (NFC) normalization. All are off/on explicitly in Settings — nothing
is silently normalized.

## 12. Export Formats

- **HTML** — styled report with metadata, settings summary, statistics, and
  a full colored diff table.
- **TXT** — plain-text summary and unified-style difference listing.
- **JSON** — machine-readable: settings, statistics, and structured
  difference records.
- **CSV** — one row per difference (type, line numbers, content).
- **Markdown** — statistics table plus a per-difference breakdown.

Export never modifies the original source files; it only reads the
in-memory `ComparisonResult`.

## 13. Logging

Three rotating log files (5 MB per file, 5 backups) in the OS log
directory: `application.log` (INFO+), `error.log` (WARNING+), and
`debug.log` (only created when the log level is set to DEBUG). Document
content is never written to logs. Log level is configurable in Settings.

## 14. Error Handling

Every anticipated failure — missing file, permission denied, unsupported/
binary file, undecodable encoding, huge file, empty file, empty source,
identical files, comparison failure, export failure, worker failure — is
caught and converted into a friendly message with a unique error ID (e.g.
`ETC-20260813-7F31A`). A global exception hook also catches any truly
unexpected error so the application stays open instead of crashing to a
bare traceback. Technical details (the original exception/traceback) are
available behind an expandable "Technical Details" section in the error
dialog and are always written to `error.log`.

## 15. Privacy & Security

- No network access is required or performed by the application.
- Document content never leaves the machine.
- Document content is never written to logs.
- Writes (export, "Save source") use atomic temp-file-then-rename so a
  crash never leaves a truncated destination file, and temp files are
  cleaned up on failure.
- No credentials, tokens, or secrets are used or stored anywhere in the
  application.
- All file paths are handled via `pathlib`; no shell interpolation of
  user-supplied paths is performed anywhere in the codebase.

## 16. Large-File Considerations

Files at or above the configured large-file threshold (10 MB by default,
adjustable in Settings) require explicit user confirmation before being
read. Comparison always runs on a background thread with progress
reporting and cooperative cancellation, so the GUI stays responsive
regardless of file size — but comparison time and memory use still scale
with input size (the engine holds both documents' lines in memory to
align them). Practical guidance: comparisons up to a few hundred thousand
lines complete in well under a second; multi-million-line files will take
longer and use proportionally more memory. There is no hard-coded upper
limit, but very large files should be confirmed deliberately via the
large-file warning rather than assumed to be unlimited.

## 17-19. Platform Notes

The application is built to run unmodified on Windows, Linux, and macOS:
all paths use `pathlib`; all config/log/cache directories are resolved via
Qt's `QStandardPaths` (never hard-coded); all GUI, clipboard, file-dialog,
drag-and-drop, and keyboard-shortcut behavior goes through Qt, which
adapts shortcuts and dialogs to platform convention automatically (e.g.
Qt maps `Ctrl` sequences to `Cmd` on macOS as appropriate for the
platform's `QKeySequence` conventions). High-DPI scaling is handled
automatically by Qt 6 without extra configuration.

**Windows 10/11** — Standard installation as above. No Windows-specific
code paths exist; QFileDialog uses native dialogs, clipboard uses the
native clipboard.

**Linux** — Tested against the `xcb` Qt platform plugin (X11) and the
`offscreen` plugin (headless/CI). Wayland is supported by Qt 6's `wayland`
platform plugin where available on the distribution. On minimal server
images you may need to install system Qt runtime dependencies (e.g.
`libxcb-cursor0`) for the `xcb` platform plugin to load; the application
itself has no Linux-specific code.

**macOS (Intel & Apple Silicon)** — No architecture-specific code. Build
natively on each architecture (or produce a `universal2` PyInstaller build
— see below) since PyInstaller does not cross-compile.

## 20. PyInstaller Build Instructions

**Important:** PyInstaller always builds a native executable for the OS
it runs on. There is no cross-compilation — to produce a Windows `.exe`
you must run PyInstaller on Windows, and likewise for Linux and macOS.

The build bundles `LICENSE` and `THIRD_PARTY_NOTICES.md` alongside the
executable so a distributed build always carries its own licensing terms.

```bash
python -m pip install -r requirements-dev.txt
```

### Windows

```powershell
pyinstaller packaging\enterprise_text_compare.spec --distpath packaging\dist --workpath packaging\build
```

Produces `packaging\dist\EnterpriseTextCompare\EnterpriseTextCompare.exe`
plus its supporting files. Provide `resources\icons\app_icon.ico` before
building to brand the executable (optional — falls back to the default
PyInstaller icon otherwise).

### Linux

```bash
pyinstaller packaging/enterprise_text_compare.spec --distpath packaging/dist --workpath packaging/build
```

Produces `packaging/dist/EnterpriseTextCompare/EnterpriseTextCompare`, a
self-contained folder build (this was verified to build and launch
successfully in this project's Linux CI environment). For distribution,
zip/tar the `EnterpriseTextCompare` folder, or wrap it as an AppImage or
`.deb` if your distribution pipeline requires a single-file/installable
package — the recommended enterprise approach is to ship the folder build
directly (via internal package repositories or a zip), since AppImage/deb
packaging adds nontrivial build infrastructure for comparatively little
benefit for an internally-distributed tool.

### macOS (Intel and Apple Silicon)

```bash
pyinstaller packaging/enterprise_text_compare.spec --distpath packaging/dist --workpath packaging/build
```

Produces `packaging/dist/EnterpriseTextCompare.app`. Build separately on
an Intel Mac and an Apple Silicon Mac for native binaries, or set
`target_arch="universal2"` in `packaging/enterprise_text_compare.spec`
(requires a universal2 Python interpreter and universal2 PySide6 build) to
produce a single binary that runs natively on both. Provide
`resources/icons/app_icon.icns` before building to brand the bundle
(optional). For distribution outside your organization, the `.app` should
be code-signed and notarized with an Apple Developer ID; unsigned builds
will be blocked by Gatekeeper on other machines unless the user explicitly
overrides it (System Settings → Privacy & Security).

## 21. Troubleshooting

- **"This plugin does not support propagateSizeHints()" on Linux** — a
  harmless message from the `offscreen`/`xcb` Qt platform plugin; it does
  not indicate an error.
- **Qt fails to start with "could not load the Qt platform plugin"** on a
  minimal Linux server — install `libxcb-cursor0` (or your distribution's
  equivalent) and the standard X11 client libraries, or run with
  `QT_QPA_PLATFORM=offscreen` for headless use.
- **Locale warning ("Detected locale... which is not UTF-8")** — Qt falls
  back to `C.UTF-8` automatically; this is informational only.
- **Settings don't seem to persist** — check that the process has write
  access to the config directory reported in `app/config/settings.py`
  (`get_config_dir()`); a `SettingsPersistenceError` dialog will also be
  shown if a save genuinely fails.
- **A file won't load ("unsupported file type")** — the file was detected
  as binary (either by extension or by a NUL byte in its first 8KB). This
  is intentional; text comparison of binary content is not supported.

## 22. Development Guidelines

- Keep `app/comparison/` free of any Qt import — it must remain usable and
  testable headlessly.
- Route all file I/O through `app/io/`; never call `open()`/`Path.read_*`
  directly from GUI or service code.
- Raise `ApplicationError` subclasses (see `app/core/exceptions.py`) for
  any anticipated failure, with a user-safe `user_message`; let genuinely
  unexpected exceptions propagate to the global handler rather than
  swallowing them.
- Long-running work (comparison, file loads) must run on a background
  `QThread` via the `QObject` + `moveToThread` pattern (see
  `app/gui/workers/`), never directly on the GUI thread.
- Run `pytest` before submitting changes; add tests alongside new engine
  or service behavior in `tests/unit/` or `tests/integration/`.

## 23. Known Limitations

- No PDF export (would require an additional dependency such as a
  PDF-rendering library; deliberately omitted to avoid an unnecessary
  dependency per the project's minimal-dependency principle — HTML export
  can be converted to PDF externally, e.g. via a browser's "Print to
  PDF").
- No true streaming/chunked diff for arbitrarily large files — both
  documents' lines are held in memory during comparison. This is
  appropriate for the documented use case (text documents, logs, source
  files, configuration) but is not designed for multi-gigabyte inputs.
- AppImage/`.deb` packaging is documented but not provided pre-built;
  the folder-based PyInstaller build is the primary supported Linux
  distribution mechanism.
- macOS builds are not code-signed/notarized by this project; that step is
  the responsibility of whoever distributes the built `.app` externally.
- Encoding detection beyond BOM-prefixed files relies on `charset-normalizer`
  when installed; without it, detection falls back to a fixed ordered list
  of common encodings and may be less accurate for ambiguous 8-bit content.

## 24. Version Information

**Enterprise Text Compare 1.0.0** (semantic versioning; version is
centralized in `app/core/constants.py::APPLICATION_VERSION`).

## License

Enterprise Text Compare is **proprietary software**.

**Copyright © 2026 Abhishek. All rights reserved.**

Use, reproduction, modification, and distribution of this software are
governed exclusively by the terms in the [`LICENSE`](LICENSE) file
included with this project. No rights are granted except as explicitly
authorized there or in a separate written agreement with the copyright
owner.

### Third-party components

This application is built on top of open-source components — notably
Python, Qt/PySide6, and the other packages listed in `requirements.txt`
— each of which remains governed by its own respective license,
independent of this project's proprietary license. See
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for details on the
direct dependencies and their licenses. Nothing in this project's license
claims ownership of, or restricts rights already granted under, any
third-party component.
