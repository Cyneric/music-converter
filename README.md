# Audio Format Converter

This repository contains two scripts (Python and Bash) for converting audio files to different formats while preserving metadata. The scripts also handle copying of associated image and NFO files.

## Features

- Convert audio files to various formats
- Support for multiple bitrates
- Preserve metadata during conversion
- Handle image files and NFO files
- Detailed logging and conversion summary
- Lock file system to track conversions
- Two operation modes:
  - Copy mode: Convert files to a new directory
  - Replace mode: Convert and replace original files

## Requirements

- Python 3.6 or higher (will be installed automatically if possible)
- ffmpeg (will be installed automatically if possible)

### Supported Operating Systems

#### Linux
- Debian/Ubuntu (apt-get)
- Fedora (dnf)
- Arch Linux (pacman)
- openSUSE (zypper)
- Other distributions (wget fallback method)

#### Windows
- Automatic installation via winget (Windows Package Manager)
- Manual installation option
- Python script only
- WSL (Windows Subsystem for Linux) fully supported
- Recommended to use WSL for better compatibility

#### macOS
- Requires Homebrew (will provide installation instructions if missing)

The scripts will automatically:
1. Detect your operating system (including WSL)
2. Check for required dependencies
3. Try multiple installation methods:
   - Native package manager (apt-get, dnf, pacman, zypper)
   - wget fallback method for other Linux distributions
   - Homebrew for macOS
   - winget for Windows
4. Provide manual installation instructions when needed

## Installation

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
# Copy mode (output to new directory):
python convert.py /path/to/input /path/to/output format bitrate
# Example:
python convert.py ~/Music ~/converted mp3 320k

# Replace mode (convert in place):
python convert.py /path/to/input format bitrate --replace
# Example:
python convert.py ~/Music mp3 320k --replace
```

#### Bash Script
```bash
# Copy mode (output to new directory):
./convert.sh /path/to/input /path/to/output format bitrate
# Example:
./convert.sh ~/Music ~/converted mp3 320k

# Replace mode (convert in place):
./convert.sh /path/to/input format bitrate --replace
# Example:
./convert.sh ~/Music mp3 320k --replace
```

## Console Output

The scripts use color-coded output for better readability:

- 🟣 Purple: Section headers and titles
- 🔵 Blue: Information and skipped files
- 🟢 Green: Successful operations
- 🟡 Yellow: Warnings
- 🔴 Red: Errors and failures
- Bold: Numbers and important information

Example colored output:
```
🟣 Conversion Summary:
==================================================
Total files processed: Bold42
🟢 Successfully converted: 35
🔵 Skipped (already converted): 5
🔴 Failed conversions: 2

🟣 File counts by extension:
------------------------------
mp3: Bold20 files
flac: Bold15 files
jpg: Bold5 files
nfo: Bold2 files

🔴 Failed files:
------------------------------
- /path/to/failed/file1.mp3
- /path/to/failed/file2.flac

🔵 Log file: /path/to/script/logs/convert_20240726_123456.log
```

Note: Colors are only shown in the console output. Log files contain plain text without color codes.

## Operation Modes

### Copy Mode
- Creates a new directory structure matching the input
- Converts audio files to the specified format
- Copies image and NFO files to the new location
- Preserves original files
- Creates/updates lock file to track conversions
- Generates detailed logs of all operations

### Replace Mode
- Converts audio files in place
- Replaces original files with converted versions
- Preserves image and NFO files unchanged
- Creates/updates lock file to track conversions
- No output directory needed
- Generates detailed logs of all operations

## Lock File System

The scripts maintain a lock file (.convert.lock) to track converted files and avoid unnecessary reprocessing.

### Lock File Location
- Copy mode: `.convert.lock` in the output directory
- Replace mode: `.convert.lock` in the input directory

### Lock File Format
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

### Lock File Benefits
- Avoids unnecessary reprocessing of already converted files
- Maintains conversion history
- Improves performance on subsequent runs
- Tracks conversion parameters for each file

### Processing Order
1. Check lock file for previous conversions
2. Check current file format and bitrate
3. Process only files that need conversion
4. Update lock file with new conversions

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

2. **Backup with Format Standardization**
   ```bash
   python convert.py ~/Music ~/Backup mp3 320k
   ```
   Creates a backup while standardizing all audio to one format

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
- Existing converted files will be skipped to avoid duplicate processing
- File conversion summary is displayed after completion
- Directory structure is preserved in copy mode
- Metadata is preserved during conversion

## License

Copyright (c) 2024 Christian Blank
