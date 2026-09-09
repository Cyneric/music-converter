# Audio Format Converter

Convert an audio library to another format with `convert.py`, or use the
`convert.sh` launcher from Bash. Both commands use the same converter and handle
metadata, image files, and NFO files.

## Upgrading

This update changes the converter since
[`2066898` revision](https://github.com/Cyneric/music-converter/tree/206689849685d773cc6ea83973a4f596a7928519).
The original copy and replace command forms still work, and conversion remains
sequential unless you set `--workers`. Console output, error exit codes, and
replace-mode collision handling have changed. The interface defaults
to English; use `--language de` for German.

Read [UPGRADING.md](UPGRADING.md) before updating an existing installation,
especially one used by scheduled jobs or with `--replace`. See
[CHANGELOG.md](CHANGELOG.md) for the unreleased changes.

`convert.sh` now starts `convert.py`. Both commands support the same console
modes, parallel conversion, and file replacement behavior. Keep the launchers
and the `music_converter/` package together.

## Features

- Convert audio files to various formats
- Support for multiple bitrates
- Preserve metadata during conversion
- Handle image files and NFO files
- Detailed logging and conversion summary
- SQLite history to resume verified conversions
- Two operation modes:
  - Copy mode: Convert files to a new directory
  - Replace mode: Convert and replace original files

## Requirements

- Python 3.11 or newer, installed before running the converter.
- Install both `ffmpeg` and `ffprobe` and make them available on `PATH`.
- Rich (optional; the Python script offers to install it for the live console)

Tested on Windows with Python 3.13.15 and FFmpeg 9.0.1. Other versions and
operating systems still need testing before release.

Python 3.11 is the minimum for this release. Earlier versions are rejected at
startup. Rich is optional; plain and headless modes use only the standard library.

### Supported Operating Systems

The Python script includes support for Windows, Linux/WSL, and macOS.
In a non-headless run, if FFmpeg or ffprobe is missing, it can ask to install it using an
available package manager: winget on Windows, Homebrew on macOS, or apt-get,
dnf, pacman, or zypper on Linux. Installation is optional and can fail; manual
installation is supported. The Python wget fallback has been removed.

Headless runs never install dependencies. Verify `ffmpeg -version` and
`ffprobe -version` before unattended use. Startup checks require both commands. On Windows, open a new terminal after changing `PATH`.

The Bash launcher looks for `python3`, then `python`, and requires Python 3.11 or newer.
It reports an error if neither works. Once Python starts, dependency checks
and installation prompts are handled by `convert.py`. The launcher does not
install Python and no longer needs `jq`.

## Installation

Download or clone the complete project folder. Keep `convert.py`, `convert.sh`,
and `music_converter/` together. Downloading `convert.py` alone is no longer enough.
The package runs directly from this folder; there is no `pip install` step for
this project. The folder must be writable for logs and conversion history.


### Python
Python can be installed in several ways depending on your operating system:

#### Windows
1. Using Windows Package Manager (recommended):
   ```powershell
   winget install Python.Python.3.11
   ```
2. Manual installation:
   - Download from https://www.python.org/downloads/
   - Run the installer
   - Make sure to check "Add Python to PATH"

#### Linux
- Debian/Ubuntu:
  ```bash
  sudo apt-get update && sudo apt-get install -y python3 python3-pip
  ```
- Fedora:
  ```bash
  sudo dnf install -y python3 python3-pip
  ```
- Arch Linux:
  ```bash
  sudo pacman -S python python-pip
  ```
- openSUSE:
  ```bash
  sudo zypper install -y python3 python3-pip
  ```

#### macOS
Using Homebrew:
```bash
brew install python
```

### FFmpeg
FFmpeg can be installed in several ways:
1. Using Windows Package Manager (recommended):
   ```powershell
   winget install Gyan.FFmpeg
   ```
2. Manual installation:
   - Download from https://www.gyan.dev/ffmpeg/builds/
   - Extract the archive
   - Add the bin folder to your system PATH
3. Using WSL (alternative approach)

### Rich Live Console (Optional)

Rich is only loaded when the Python script is started with `--rich`. If the
package is missing in an interactive terminal, the script offers to install it
for the same Python interpreter:

```text
Rich ist nicht installiert. Jetzt installieren? [J/n]
```

Press Enter or answer `j` to install it. If you decline or installation fails,
the script exits with code `1`. Run again without `--rich` to use the plain console.

Rich can also be installed manually:

```powershell
python -m pip install rich
```

Plain and headless runs neither import Rich nor ask to install it.

## Supported Formats

### Audio Formats
- Input & Output formats:
  - MP3 (.mp3)
  - FLAC (.flac)
  - WAV (.wav)
  - M4A (.m4a)
  - OGG Vorbis (.ogg)
  - Opus (.opus)
  - WMA (.wma)
  - AAC (.aac)

### Image Formats (automatically copied)
- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- BMP (.bmp)
- WebP (.webp)

### Other Files
- NFO files (.nfo)

## Bitrate Options
Available bitrates for audio conversion:
- 32k
- 64k
- 128k
- 192k
- 256k
- 320k

## Usage

The scripts can be run in two ways:
1. Command-line mode with arguments
2. Interactive mode (when run without arguments)

### Interactive Mode

Simply run the script without arguments:
```bash
# Python script
python convert.py

# Bash script
./convert.sh
```

The script will guide you through the process, asking for:
1. Input directory path
2. Operation mode (copy/replace)
3. Output directory path (if copy mode)
4. Output format
5. Bitrate

### Command-line Mode

#### Python Script

```bash
# Copy mode with the default compact text console:
python convert.py /path/to/input /path/to/output mp3 320k

# Replace mode:
python convert.py /path/to/input mp3 192k --replace

# Rich full-screen dashboard with live summary and activity history:
python convert.py /path/to/input mp3 192k --replace --rich

# English Rich interface:
python convert.py /path/to/input mp3 192k --replace --rich --language en

# Silent automation run; output is written only to logs and conversion history:
python convert.py /path/to/input mp3 192k --replace --headless
```

The flags may appear before, between, or after positional arguments.
`--rich` and `--headless` cannot be combined.

### Parallel Conversion

Use `--workers N` to encode up to N tracks concurrently. N must be a positive
integer; the default is `1`, preserving sequential behavior for existing calls.
For a NAS, start with two workers:

```powershell
python .\convert.py Q:\music mp3 192k --replace --rich --language en --workers 2
```

Conversion starts while the script scans the library. Files with other extensions
are processed before files with the requested extension. Image and NFO files are
copied after the audio finishes. The queue holds at most twice the worker count.
Workers use the CPU, with the same audio settings as a single-worker run.

Each conversion writes to a separate temporary file in the destination directory.
In replace mode, the finished output replaces the destination before the source
is removed. For example, converting `track.flac` to MP3 can replace an existing
`track.mp3`. If encoding or saving the output fails, the source and existing
destination are kept. If removing the source fails, both files remain and the
operation is reported as failed.

Copy mode checks existing audio and sidecar destinations against saved history.
An unverifiable destination is kept and reported as a conflict. If two sources
would produce the same destination, the second source is reported as a conflict.
On Linux and macOS, copy mode requires a destination filesystem that supports hard links. See
[UPGRADING.md](UPGRADING.md) for details about replacement and resume behavior.

Ctrl+C cancels queued work and stops active encoders (force-stopping after a
five-second grace period when necessary). Finished results are recorded,
temporary files are cleaned up, and completed history is saved. Do not
run multiple converter instances against the same library or shared history directory.
To change the worker count, stop the current run cleanly and restart it.

The Rich dashboard shows active workers, queued jobs, and filenames. The summary
and log show successful conversions per minute; skipped files do not count.
More workers are not always faster, especially on a NAS. Compare small runs with
one, two, and four workers using copied sample inputs, fresh output folders, and
a separate project folder and history database for each run. Use copy mode for these tests.

#### Bash Script

Keep `convert.sh` beside `convert.py` and the `music_converter/` package. The
launcher passes every argument to Python and keeps your working directory, so relative input and output paths
work the same way with either command.

```bash
# Copy mode (output to new directory):
./convert.sh /path/to/input /path/to/output format bitrate
# Example:
./convert.sh ~/Music ~/converted mp3 320k

# Replace mode (convert in place):
./convert.sh /path/to/input format bitrate --replace
# Example:
./convert.sh ~/Music mp3 320k --replace

# The Python options are also available through Bash:
./convert.sh ~/Music ~/converted mp3 192k --rich --language en --workers 2
```

The launcher returns Python's exit code and hands control to Python with `exec`,
so Ctrl+C is handled by the converter. If a supported Python, `convert.py`, or the package
is missing, the launcher prints an error to stderr and exits with code `1`,
including when `--headless` was requested. It does not create a log in that case.
If executable permissions were lost when downloading, use `bash convert.sh`
or run `chmod +x convert.sh`.

## Console Modes

| Mode | Flag | Behavior |
| --- | --- | --- |
| Plain | none | Compact built-in text display; Rich is not imported |
| Rich | `--rich` | Full-screen dashboard with fixed totals, current operation, and recent activity |
| Headless | `--headless` | No stdout, stderr, prompts, or dependency installation; logs and history only |

### Rich Mode

The Rich display keeps configuration, live totals, runtime, and the current
operation fixed at the top of the terminal. Successful conversions, warnings,
and errors appear in the recent-activity area below. The complete history is
still written to the log file. The latest visible events and final summary
remain in the normal console after the dashboard closes. This uses the
terminal's alternate screen to keep the top
area fixed; the activity area shows only the latest events that fit on screen.
Warnings are yellow and errors are red. The fixed live status area includes:

- The current phase, active relative filenames, worker occupancy, and queue size
- An immediate spinner for non-target audio formats
- Determinate progress bars for existing target files and sidecars
- Converted, correct, skipped, copied, and failed counters
- Elapsed time and an estimate when a total is known
- Successful conversions per minute

Already-correct, skipped, and copied files update counters and the detailed log
without filling the visible history. Long paths are shortened only on screen;
the log keeps their complete value.

### Language

Use `--language de` or `--language en` for console help, prompts, progress,
warnings, and summaries. English is the default. Technical log messages remain
in English for stable diagnostics.

### Exit Codes

| Code | Meaning |
| --- | --- |
| `0` | Run completed without failed files |
| `1` | Invalid arguments, mode conflict, missing dependency, or fatal error |
| `2` | Run completed, but one or more files failed |
| `130` | Interrupted with Ctrl+C after saving completed progress |

Explicit `--help` output remains visible in every mode. Other valid headless
runs produce no console output.

## Operation Modes

These modes behave the same through `convert.py` and `convert.sh`.

### Copy Mode
- Creates destination directories for processed files; empty directories are not replicated
- Converts audio files to the specified format
- Copies image and NFO files to the new location
- Preserves original files
- Records verified output in the history database
- Generates detailed logs of all operations

Audio already matching the requested format and bitrate is copied without
re-encoding. Audio and sidecar copies count as copied files. Existing outputs
are skipped only when their saved source, destination, and settings still match.
Otherwise they are kept and reported as conflicts, which produce exit code `2`.
Choose a new output directory or review the conflicting files before retrying.
Copy mode processes supported files; it does not copy unrelated file types or
replicate empty directories.

### Replace Mode
- Converts audio files in place
- Replaces original files with converted versions
- Replaces an existing same-basename target only after successful conversion, then removes the source
- Preserves image and NFO files unchanged
- Records verified output in the history database
- No output directory needed
- Generates detailed logs of all operations

## Conversion History

New progress is stored in `.convert-state.sqlite3` beside `convert.py`. The
Bash launcher uses the same database. Each record includes the operation mode,
source and destination paths, conversion settings, and both files' sizes and
modification times. A different output directory or a changed file will not be
skipped based on an old record.

Records are saved in transactions after each successful operation. Only the
coordinator writes history. `.convert-state.runlock` prevents two runs from
using the same history directory at once; its presence alone does not mean a
converter is running. The operating system releases the lock when the process
exits. Do not use separate installations to modify the same library concurrently.

Keep the project and its state on a local disk when processing a network music
library. SQLite and file-lock behavior depend on the filesystem. An unreadable,
unsupported, or unwritable database stops the run with an error rather than
silently discarding history.

### Upgrading JSON History

The old `.convert.lock` remains untouched. Both published scripts stored it
beside the script, despite earlier documentation saying otherwise. In replace
mode, matching entries are imported automatically without probing, decoding, or
re-encoding the audio. The converter still scans the directory to find files.

An imported entry must identify the current file by its absolute path, match the
requested format and bitrate, and have a valid completion timestamp. The file
must be nonempty, be a regular file rather than a symbolic link, and have a
modification time no later than that timestamp. Renamed files and ambiguous
records are not guessed. Entries that cannot be imported receive normal checks.
Existing SQLite replacement records always take precedence, even after a file or
its conversion settings change.

This migration trusts the old script's completed records and establishes size
and modification-time fingerprints for future runs. Old records cannot prove
that audio remained unchanged before migration. Imported files count as skipped;
the log reports how many legacy records were reused.

Imports are committed in batches of up to 250, including a final batch at each
phase boundary or orderly interruption. A forced stop can leave the last batch
to be imported again. Completed conversions and copies are still saved
immediately. The next run uses the records already saved.

Copy mode still creates missing outputs and reports conflicts for existing
outputs without verified records: legacy entries do not record the destination
directory. Damaged legacy JSON is left untouched and reported in the log; it does
not prevent checking the audio files directly.

Example of the old JSON format, retained for reference:

```json
{
  "/path/to/file1.mp3": {
    "format": "mp3",
    "bitrate": "320k",
    "timestamp": "2024-11-06T15:30:45.123456"
  },
  "/path/to/file2.flac": {
    "format": "flac",
    "bitrate": "320k",
    "timestamp": "2024-11-06T15:31:12.345678"
  }
}
```

### Limits

File checks use size and modification time in nanoseconds, not a full content
hash. Edits that preserve both values cannot be detected by the resume check.
Files are also checked for changes between the start of processing and saving
the output. Keep other applications from editing the library during a run.

### Processing Order

1. Convert files with other extensions.
2. Check files with the target extension and copy or convert them as needed.
3. Copy image and NFO files in copy mode.

Workers write separate temporary files. Audio output is probed and decoded for
validation before it is saved. The coordinator saves the result, removes a
source only in replace mode, and records the completed operation.

If embedded artwork prevents encoding, the converter retries audio-only and
reports that the cover was omitted. It does not extract a replacement sidecar.
Metadata is passed to FFmpeg, but preservation depends on the destination format.

## Logging

The scripts create detailed logs of all operations in a `logs` directory:

### Log Location
- Logs are stored in the `logs` directory next to the script
- Each run creates a new log file with timestamp: `convert_YYYYMMDD_HHMMSS.log`

### Log Contents
- Start time and script parameters
- Input/output paths and conversion settings
- All file operations (conversions, copies, skips)
- Error messages and failed operations
- Detailed conversion summary

### Summary Information
The scripts provide a summary at completion showing:
- Total files processed
- Successfully converted files
- Skipped files (already existing)
- Failed conversions
- Breakdown by file extension
- Path to the log file

Example summary:
```
Conversion Summary:
==================================================
Total files processed: 42
Successfully converted: 35
Skipped files: 5
Failed conversions: 2

File counts by extension:
------------------------------
mp3: 20 files
flac: 15 files
jpg: 5 files
nfo: 2 files

Failed files:
------------------------------
- /path/to/failed/file1.mp3
- /path/to/failed/file2.flac

Log file: /path/to/script/logs/convert_20240726_123456.log
```

## Usage Examples

### Basic Usage

Converting MP3 files to FLAC:
```bash
# Using Python script
python convert.py ~/Music/Albums ~/Converted/FLAC flac 320k

# Using Bash script
./convert.sh ~/Music/Albums ~/Converted/FLAC flac 320k
```

### Replace Mode Examples

Converting all audio files to MP3 and replacing originals:
```bash
# Using Python script
python convert.py ~/Music/Collection mp3 320k --replace

# Using Bash script
./convert.sh ~/Music/Collection mp3 320k --replace
```

### Real-World Examples

1. Converting a DJ music collection to lower bitrate for mobile device:
```bash
python convert.py ~/Music/DJ_Collection ~/Mobile_Music mp3 128k
```

2. Converting podcast files to opus format for better compression:
```bash
./convert.sh ~/Podcasts ~/Podcasts_Compressed opus 64k
```

3. Converting vinyl rips to high-quality FLAC:
```bash
python convert.py ~/Vinyl_Rips ~/Archive flac 320k
```

4. Standardizing a mixed format collection to MP3:
```bash
./convert.sh ~/Mixed_Music mp3 320k --replace
```

### Directory Structure Example

Input directory:
```
~/Music/
├── Rock/
│   ├── Artist1/
│   │   ├── album.nfo
│   │   ├── cover.jpg
│   │   ├── track1.flac
│   │   └── track2.flac
│   └── Artist2/
│       ├── album.nfo
│       ├── cover.png
│       └── track1.wav
└── Jazz/
    └── Artist3/
        ├── album.nfo
        ├── cover.jpg
        └── track1.m4a
```

Converting to MP3:
```bash
python convert.py ~/Music ~/Converted mp3 320k
```

Output directory:
```
~/Converted/
├── Rock/
│   ├── Artist1/
│   │   ├── album.nfo
│   │   ├── cover.jpg
│   │   ├── track1.mp3
│   │   └── track2.mp3
│   └── Artist2/
│       ├── album.nfo
│       ├── cover.png
│       └── track1.mp3
└── Jazz/
    └── Artist3/
        ├── album.nfo
        ├── cover.jpg
        └── track1.mp3
```

### Common Use Cases

1. **Mobile Device Optimization**
   ```bash
   ./convert.sh ~/Music ~/Mobile mp3 128k
   ```
   Converts music to a mobile-friendly format and size

2. **Additional Converted Collection**
   ```bash
   python convert.py ~/Music ~/Backup mp3 320k
   ```
   Converts eligible files to one format; verify output completeness as described in Copy Mode

3. **Storage Space Optimization**
   ```bash
   ./convert.sh ~/Large_Audio_Collection opus 128k --replace
   ```
   Converts and replaces files with a space-efficient format

4. **Archive Creation**
   ```bash
   python convert.py ~/Original_Records ~/Archive flac 320k
   ```
   Creates high-quality archives of original recordings

## Notes

- The scripts will automatically check for ffmpeg and offer to install it if missing
- Verified outputs are skipped; unverifiable existing outputs are reported as conflicts
- File conversion summary is displayed after completion
- Directory structure is preserved in copy mode
- Metadata is preserved during conversion

## Development

Run `python -m unittest discover -v` from the project folder. Tests use generated
audio, temporary directories, and separate history databases. Install FFmpeg and
ffprobe for conversion tests, and Rich to check the dashboard. GitHub Actions
runs the suite on Windows, Linux, and macOS with Python 3.11 and 3.13.

The implementation lives in `music_converter/`:

| Module | Responsibility |
| --- | --- |
| `cli` | Arguments, setup, logging, and exit codes |
| `models` | Configuration, jobs, results, and progress events |
| `console` | Plain, Rich, and headless output and translations |
| `workflow` | Scanning, scheduling, completion, and cancellation |
| `ffmpeg` | Audio probing, encoding, validation, and subprocesses |
| `files` | Temporary files, copying, and replacement |
| `history` | SQLite progress and legacy JSON inspection |

The command line is the supported interface. Internal Python helpers may change.

## License

Copyright (c) 2024-2026 Christian Blank
