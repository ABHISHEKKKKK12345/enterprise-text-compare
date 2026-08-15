# Third-Party Notices

Enterprise Text Compare is proprietary software (see `LICENSE`). It is
built on top of, and distributed together with, certain third-party
open-source components. Those components remain governed exclusively by
their own respective licenses; nothing in `LICENSE` claims ownership of,
or restricts rights already granted under, any of the components listed
below.

This file lists the project's **direct** dependencies, as declared in
`requirements.txt` / `pyproject.toml`. License identifiers below were
confirmed against each package's installed distribution metadata
(`pip show <package>`) at the time this file was written. Package
authors, dependency versions, and license terms can change over time —
before redistributing a build of this application, verify the current
license of each dependency actually bundled with that build (e.g. via
`pip show <package>`, or the licenses bundled inside a PyInstaller
build's `_internal` directory) rather than relying solely on this file.

## Runtime dependencies

### PySide6 (Qt for Python)
- **Purpose:** GUI framework — all windows, dialogs, widgets, clipboard,
  file dialogs, drag-and-drop, and platform integration.
- **License:** LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only (PySide6 is
  dual/multi-licensed by The Qt Company; the LGPLv3 option is the one
  generally used for proprietary applications, subject to LGPLv3's own
  terms, e.g. regarding dynamic linking and providing a means for users
  to relink against a modified Qt/PySide6).
- **Project/vendor:** The Qt Company / Qt for Python project.

### charset-normalizer
- **Purpose:** Improves text-encoding detection accuracy (optional —
  the application falls back to a built-in encoding chain without it).
- **License:** MIT.

## Development-only dependencies

These are used for testing and packaging and are **not** bundled into a
built/distributed application; they are listed here for completeness and
development-environment license clarity only.

### pytest
- **Purpose:** Test framework, used to run the project's test suite.
- **License:** MIT (per the pytest project's published license; not
  reported by this environment's package metadata — verify directly
  against the pytest project if this matters for your use case).

### PyInstaller
- **Purpose:** Packages the application into a standalone executable for
  distribution.
- **License:** GPL-2.0-or-later, **with PyInstaller's own explicit
  bootloader exception** that permits using it to build and distribute
  both free and non-free (including commercial/proprietary) applications
  without the built application itself being subject to the GPL. This
  exception is what makes it possible for Enterprise Text Compare to
  remain proprietary while being packaged with PyInstaller. If
  redistributing built executables, retain PyInstaller's own license
  notice as PyInstaller itself directs (see the PyInstaller project's
  `COPYING.txt`).

## Runtime environment

### Python
- **Purpose:** The language runtime the application is written in and
  executed by.
- **License:** Python Software Foundation License (PSF License), a
  permissive license.

## How to regenerate/verify this list

From an environment with the project's dependencies installed:

```bash
pip show PySide6 charset-normalizer pytest pyinstaller
```

For a complete, automatically generated list of every transitive
dependency and its license (not just the direct ones listed above),
consider using a tool such as `pip-licenses`
(`pip install pip-licenses && pip-licenses`) before distributing a build
to a wider audience.
