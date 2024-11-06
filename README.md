# Audio Format Converter

This repository contains two scripts (Python and Bash) for converting audio files to different formats while preserving metadata. The scripts also handle copying of associated image and NFO files.

## Features

- Convert audio files to various formats
- Support for multiple bitrates
- Preserve metadata during conversion
- Handle image files and NFO files
- Detailed logging and conversion summary
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

### Python Script

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

### Bash Script

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

## Operation Modes

### Copy Mode
- Creates a new directory structure matching the input
- Converts audio files to the specified format
- Copies image and NFO files to the new location
- Preserves original files
- Generates detailed logs of all operations

### Replace Mode
- Converts audio files in place
- Replaces original files with converted versions
- Preserves image and NFO files unchanged
- No output directory needed
- Generates detailed logs of all operations

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

## Examples

Converting a music library to MP3 320k:
```bash
python convert.py ~/Music ~/Music_MP3 mp3 320k
```

Converting and replacing FLAC files with MP3:
```bash
./convert.sh ~/Music mp3 320k --replace
```

Converting to high-quality FLAC:
```bash
python convert.py ~/Music ~/Music_FLAC flac 320k
```

## Notes

- The scripts will automatically check for ffmpeg and offer to install it if missing
- Existing converted files will be skipped to avoid duplicate processing
- File conversion summary is displayed after completion
- Directory structure is preserved in copy mode
- Metadata is preserved during conversion

## License

Copyright (c) 2024 Christian Blank
