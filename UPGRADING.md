# Upgrading from the published November 2024 version

This guide covers the unreleased update since
[`206689849685d773cc6ea83973a4f596a7928519`](https://github.com/Cyneric/music-converter/tree/206689849685d773cc6ea83973a4f596a7928519).
The implementation now lives in `music_converter/`. Download the complete
project folder and keep the package beside `convert.py` and `convert.sh`.
No package installation step is needed for this project. Both commands use the
same converter and require Python 3.11 or newer.

## What existing commands retain

These forms still work:

```bash
python convert.py INPUT OUTPUT mp3 192k
python convert.py INPUT mp3 192k --replace
python convert.py
```

The third form starts interactive setup. The same eight audio extensions and
six bitrate choices remain. One worker is still the default. Rich is optional
and is neither imported nor installed in plain/headless mode. English is the
default; use `--language de` for German.

## Changes for Bash users

The old Bash command forms still work:

```bash
./convert.sh INPUT OUTPUT mp3 192k
./convert.sh INPUT mp3 192k --replace
./convert.sh
```

Keep both launchers and the package together. The launcher tries `python3`, then
`python`, and uses the first one running Python 3.11 or newer. Install Python beforehand;
the launcher no longer offers to install it. `jq` is no longer needed.

All Python options, including `--rich`, `--headless`, `--language`, and
`--workers`, are available through Bash. Output, exit codes, replacement, and
resume behavior now match Python. Relative paths are still resolved from the
directory where you run the command.

Output names now replace the original extension: `track.flac` becomes
`track.mp3`, rather than `track.flac.mp3`. Previously created files are not
renamed or removed automatically. Check for both names before converting again,
especially in replace mode, which can overwrite an existing `track.mp3`.

The launcher uses the `.convert-state.sqlite3` beside `convert.py`. The old
`.convert.lock` is left untouched. Eligible in-place records from either old
script are imported automatically. Other files receive normal checks.

If a suitable Python, `convert.py`, or the package is missing, startup exits with code `1` and prints
an error to stderr, even with `--headless`. Once Python starts, its documented
headless behavior applies.

## Changes that can affect existing users

| Area | Previous behavior | What changes |
| --- | --- | --- |
| Language | English console | English remains the default; use `--language de` for German. |
| Installation files | A standalone Python script | Download the full project, including `music_converter/`. Python 3.11+ is required. |
| Copy completeness | Already-correct audio was skipped without copying | Copy matching audio without re-encoding and count it as copied. |
| Existing copy outputs | Audio skipped; sidecars could be overwritten | Skip only verified outputs; preserve others and report conflicts with exit code `2`. |
| Console | Verbose per-file colored logging | Compact plain display; optional `--rich` dashboard or silent `--headless`. Text and summary labels differ; adjust output-parsing wrappers. English does not restore the old layout. |
| Failed files | Normal completion could exit `0` despite failures | Exit `2` when one or more files fail, including sidecar operations. Scheduled jobs must handle this. |
| Invalid command shape | Could fall back to interactive questions | Returns `1`; run without positionals for interactive setup. |
| Existing target in replace mode | Remove source, then rename; on Windows an existing target could make rename fail after source deletion | Publish successful output first, overwriting a same-basename target, then remove a different-format source. Review collisions before using `--replace`. |
| Output publication | Fixed `_temp` filename in replace mode; direct output in copy mode | Unique temporary file in the destination directory. Failed encoding/publication preserves the source and pre-existing target. POSIX copy publication requires hard-link support. |
| Processing order | One directory walk, filesystem order | Other extensions first, target extension second, sidecars last. Multiple sources mapping to one output produce a conflict for the second source. |
| Resume | Matching source-path/format/bitrate entry skipped | SQLite checks both source and output, including paths, sizes, modification times, mode, and settings. Legacy JSON remains untouched. |
| Interruptions | No coordinated cancellation/checkpoint handling | During processing, Ctrl+C stops workers, cleans temporary outputs, saves completed progress, and returns `130`. This is not a guarantee against power loss. |
| Installation | Included Python FFmpeg wget fallback | Uses available platform package managers after a prompt. No Python wget fallback; headless mode never installs dependencies. |
| Python imports | Helpers lived in `convert.py` | Helpers have moved into the package. The command line is the supported interface; internal modules may change. |

The format/bitrate flags do not guarantee identical encoded bytes across FFmpeg
versions. New audio-only retries may omit broken embedded artwork. Sidecar
images are preserved in place or copied separately; no automatic extraction of
embedded artwork is provided.

## Update an existing installation

1. Let the active run finish or stop it cleanly. Save a copy of the old scripts
   and their adjacent `.convert.lock` before updating. Back up audio separately
   if using replace mode; a script rollback cannot restore overwritten audio.
2. Download the full project into the existing directory so history remains
   beside the launchers. If moving installations, transfer the state files while
   preserving the source paths it refers to. Do not delete it as an upgrade step.
3. Install Python 3.11+ and check `ffmpeg` and `ffprobe`. Both executables are
   checked at startup. Local testing used Windows and Python 3.13.15; native
   CI results for Windows, Linux, and macOS on 3.11 and 3.13 must be checked before release.
4. Adjust automation for exit codes `0` (completed without failed files), `1`
   (arguments/dependencies/fatal error), `2` (failed files), and `130` (handled
   processing interruption). Use `--headless` for silent jobs. Explicit `--help`
   still prints help.
5. Try copied sample inputs using a separate project folder and its own state,
   with output outside the sample input. Start with one worker; then try two.
   Check decoded audio, tags, artwork, output count, and logs before replacing
   files in a full library. There is no dry-run flag in this update.

Example with explicit language and worker count:

```bash
python convert.py INPUT OUTPUT mp3 192k --language en --workers 1
```

## Moving from JSON to SQLite

New records are stored in `.convert-state.sqlite3` beside `convert.py`. The old
`.convert.lock` remains untouched for reference and rollback. Both old scripts
already stored it beside the script, despite earlier README instructions.

Matching in-place entries are imported automatically without ffprobe, audio
decoding, or re-encoding. No new option is needed. The directory scan still runs
to discover files, but eligible entries need only filesystem metadata checks.

An entry must use an absolute path identifying the current file, match its
extension and the requested format and bitrate, and contain a valid completion
timestamp. Status may be `converted`, `correct_format`, or absent for older Bash
records. The file must be nonempty and regular, without a symbolic link, and its
modification time must not be later than the recorded completion. Timezone-free
timestamps from older Python versions are interpreted in the local timezone.
Missing or ambiguous information falls back to normal validation. Paths are not
remapped to guess moved libraries or older Bash output names.

Fast migration preserves the old script's trust in its history. It cannot prove
that a file remained unchanged before its first SQLite fingerprint was recorded.
Once a destination has a SQLite replacement record, legacy history can never be
used to bypass checks for later file or settings changes.

Imported files count as skipped, and the log reports the number imported.
Imports are saved in transactions of up to 250 records, with remaining records
saved at phase boundaries and orderly cancellation. After a forced stop, only
an uncommitted batch needs importing again. Newly completed conversions and
copies are still recorded immediately.

Legacy entries do not identify a copy destination, so missing copy outputs are
created and unverifiable existing outputs remain conflicts. Choose a new output
directory or review the conflicting files before retrying. Damaged legacy JSON
is logged and left untouched while files are checked directly. An unreadable,
unsupported, or unwritable SQLite database stops the run instead of discarding
history.

Records contain the operation mode, paths, format, bitrate, file size, and
modification time in nanoseconds. Copy mode checks both source and destination;
replace mode checks the resulting file. Changed files or settings invalidate a
resume match. Full-file hashing is not used, so changes preserving both size and
modification time cannot be detected. Files are also checked for changes while
processing, before saving their output.

`.convert-state.runlock` prevents simultaneous runs using the same history
directory. The operating system releases the lock when a process exits, even
though the file remains. Separate installations must not modify the same library
concurrently. Use `--workers` within one run instead. Keep the project and state
on local storage when processing a network library.

Copy mode includes supported audio and sidecar files, not unrelated file types
or empty directories. Conflicts count as failures and cause exit code `2`.

## Returning to the old script

Restore the saved old scripts and their JSON history together. Old scripts do
not read SQLite and will not know about work completed since the upgrade. They
may process files again. Check the library first. Restoring scripts or history
does not restore deleted or overwritten audio.
