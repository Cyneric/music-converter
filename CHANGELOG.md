# Changelog

## Unreleased

Compared with published commit
[`2066898`](https://github.com/Cyneric/music-converter/commit/206689849685d773cc6ea83973a4f596a7928519)
(November 6, 2024). The Bash launcher now uses the Python converter, so its
conversion behavior matches Python.
Read [UPGRADING.md](UPGRADING.md) for behavior changes affecting existing users.

### Added

- MIT license with Christian Blank's copyright attribution.
- Optional Rich dashboard, silent headless mode, and German/English interfaces.
- `--workers N` with bounded queuing and one worker by default.
- Worker activity, phase progress, runtime, throughput, and separate sidecar counts.
- Coordinated processing cancellation, temporary-file cleanup, and progress saving.
- SQLite history with source and destination checks, transactions, and exclusive access.
- Output validation and checks for sources changed during processing.
- Tests for formats, metadata, artwork, resume, conflicts, cancellation, failures,
  console modes, and the Bash launcher.
- CI for Windows, Linux, and macOS on Python 3.11 and 3.13.

### Changed

- Moved the implementation into `music_converter/`. Download the complete project
  folder; `convert.py` alone is no longer sufficient. No project installation step is needed.
- Require Python 3.11+ and check FFmpeg and ffprobe before starting conversions.
- Replaced the separate Bash converter with a launcher for `convert.py`.
  Existing command forms still work, and all Python options are available.
- Bash output names now replace the source extension: `track.flac` becomes
  `track.mp3`. Existing files with double extensions are left alone.
- The launcher requires Python 3.11+, no longer uses `jq`, and passes through
  arguments and Python's exit code. It uses `exec` to hand over control.
- Default console is compact and English; use `--language de` for German.
- Failed-file completion returns `2`; argument/dependency/fatal failures return `1`;
  handled processing interruption returns `130`.
- Files with other extensions are converted before files with the target extension.
  Sidecars are copied last.
- Files with other extensions no longer need a separate probe before conversion.
  Output folders inside the input folder are excluded from scanning.
- Each conversion uses a unique temporary file. Replace mode saves the output before deleting a
  different-format source and can overwrite an existing same-basename target.
- Copy already-correct audio without re-encoding instead of leaving it out.
- Keep unverifiable existing audio and sidecar outputs and report conflicts.
  POSIX copy mode uses hard links to avoid overwriting files.
- Automatically import eligible in-place records from `.convert.lock` using
  metadata checks, without probing or decoding audio. Keep the old file untouched.
  Import in batches of up to 250 and resume after interruption. Existing SQLite
  records take precedence; changed or ambiguous legacy entries receive normal checks.
- Save new progress in `.convert-state.sqlite3`; old scripts do not read this
  database. Legacy history cannot verify existing copy destinations.
- Replace mode retries remaining sources with other extensions, even with an old resume entry.
- Added audio-only retries for artwork failures and forced MP3 decoding as a fallback
  after automatic content detection fails. Audio-only success can omit embedded art.
- Removed Python's wget installation fallback. Rich installation is offered
  only when requested; headless runs do not prompt for or install dependencies.
- Moved internal helpers into the package; the command line remains the supported interface.
- Keep Rich imports optional and use a dedicated logger.
- Update copyright notices to 2024-2026 and remove the stale modification date.

### Documentation

- Added upgrade instructions, including the Bash launcher and output filename changes.
- Corrected the lock file location. Python must be installed before running the script.
- Documented the Python 3.11 minimum, package layout, SQLite migration, and rollback.
- Explained when copy mode skips files and when embedded artwork may be omitted.
- Explain the legacy import requirements and the limits of trusting old records.
