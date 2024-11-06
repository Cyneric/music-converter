#!/usr/bin/env python3

"""
Author: Christian Blank <christianblank91@gmail.com>
Created: Fri Jul 26 2024
Modified: Wed Nov 06 2024
Copyright: (c) 2024

Audio Format Converter

This script converts audio files to different formats while preserving metadata.
It also handles copying of associated image and NFO files.

Features:
- Convert audio files to various formats (mp3, flac, wav, m4a, ogg, opus, wma, aac)
- Support for multiple bitrates (32k, 64k, 128k, 192k, 256k, 320k)
- Preserve metadata during conversion
- Handle image files (jpg, jpeg, png, gif, bmp, webp)
- Copy NFO files
- Two operation modes: copy to new directory or replace in place
- Detailed logging of all operations
"""

import os
import subprocess
import sys
import shutil
import logging
from datetime import datetime
import json

def check_python_version():
    """
    Check if the current Python version meets requirements (3.6 or higher).
    """
    if sys.version_info < (3, 6):
        print("Python 3.6 or higher is required to run this script. Exiting.")
        sys.exit(1)

def check_ffmpeg():
    """
    Check if ffmpeg is installed and offer to install it if missing.
    Supports multiple package managers and installation methods across different OS.

    Installation methods:
    - Linux: apt-get, dnf, pacman, zypper, or wget fallback
    - macOS: Homebrew
    - Windows: winget or manual installation
    - WSL: Native package managers

    Raises:
        SystemExit: If ffmpeg installation fails or is declined
    """
    if shutil.which("ffmpeg") is None:
        choice = input("ffmpeg is not installed. Would you like to install it now? (y/n): ")
        if choice.lower() == 'y':
            # Detect OS and use appropriate package manager
            if sys.platform.startswith('linux') or "microsoft-standard" in os.uname().release.lower():  # Linux or WSL
                # Check for different package managers
                if shutil.which("apt-get"):
                    subprocess.run(["sudo", "apt-get", "update"])
                    subprocess.run(["sudo", "apt-get", "install", "-y", "ffmpeg"])
                elif shutil.which("dnf"):
                    subprocess.run(["sudo", "dnf", "install", "-y", "ffmpeg"])
                elif shutil.which("pacman"):
                    subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"])
                elif shutil.which("zypper"):
                    subprocess.run(["sudo", "zypper", "install", "-y", "ffmpeg"])
                else:
                    # Try wget as fallback
                    try:
                        print("Attempting to install ffmpeg using wget...")
                        if not shutil.which("wget"):
                            print("Installing wget first...")
                            subprocess.run(["sudo", "apt-get", "update"])
                            subprocess.run(["sudo", "apt-get", "install", "-y", "wget"])

                        # Create temporary directory
                        tmp_dir = "/tmp/ffmpeg_install"
                        os.makedirs(tmp_dir, exist_ok=True)
                        os.chdir(tmp_dir)

                        # Download and extract ffmpeg
                        subprocess.run(["wget", "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"])
                        subprocess.run(["tar", "xf", "ffmpeg-release-amd64-static.tar.xz"])

                        # Move ffmpeg to system path
                        ffmpeg_dir = next(d for d in os.listdir() if d.startswith('ffmpeg-'))
                        subprocess.run(["sudo", "cp", f"{ffmpeg_dir}/ffmpeg", "/usr/local/bin/"])
                        subprocess.run(["sudo", "cp", f"{ffmpeg_dir}/ffprobe", "/usr/local/bin/"])

                        # Cleanup
                        os.chdir("/")
                        shutil.rmtree(tmp_dir)
                        print("ffmpeg installed successfully using wget")
                    except Exception as e:
                        print(f"Failed to install ffmpeg using wget: {e}")
                        print("Please install ffmpeg manually.")
                        sys.exit(1)
            elif sys.platform == "darwin":
                if shutil.which("brew"):
                    subprocess.run(["brew", "install", "ffmpeg"])
                else:
                    print("Homebrew not found. Please install Homebrew first:")
                    print("  /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
                    sys.exit(1)
            elif sys.platform == "win32":
                if shutil.which("winget"):
                    try:
                        print("Attempting to install ffmpeg using winget...")
                        subprocess.run(["winget", "install", "Gyan.FFmpeg"], check=True)
                        print("Please restart your terminal for the changes to take effect.")
                        print("Then run this script again.")
                        sys.exit(0)
                    except subprocess.CalledProcessError:
                        print("Failed to install ffmpeg using winget.")
                        print("Attempting manual installation instructions...")

                print("On Windows, you can:")
                print("1. Install using winget (Windows Package Manager):")
                print("   winget install Gyan.FFmpeg")
                print("\n2. Or install manually:")
                print("   a. Download from https://www.gyan.dev/ffmpeg/builds/")
                print("   b. Extract the archive")
                print("   c. Add the bin folder to your system PATH")
                print("\n3. Or use Windows Subsystem for Linux (WSL)")
                sys.exit(1)
            else:
                print("Unsupported operating system")
                sys.exit(1)
        else:
            print("ffmpeg is required to run this script. Exiting.")
            sys.exit(1)

def validate_arguments():
    """
    Validate and parse command line arguments.

    Returns:
        tuple: (input_path, output_path, music_format, bitrate, replace_mode)

    Raises:
        SystemExit: If arguments are invalid or missing
    """
    if len(sys.argv) not in [4, 5]:
        print("Usage: {} input_path music_format bitrate [--replace]".format(sys.argv[0]))
        print("   or: {} input_path output_path music_format bitrate".format(sys.argv[0]))
        sys.exit(1)

    replace_mode = "--replace" in sys.argv
    if replace_mode:
        sys.argv.remove("--replace")
        input_path = sys.argv[1]
        output_path = input_path  # In replace mode, output is same as input
        music_format = sys.argv[2]
        bitrate = sys.argv[3]
    else:
        if len(sys.argv) != 5:
            print("Usage: {} input_path music_format bitrate [--replace]".format(sys.argv[0]))
            print("   or: {} input_path output_path music_format bitrate".format(sys.argv[0]))
            sys.exit(1)
        input_path = sys.argv[1]
        output_path = sys.argv[2]
        music_format = sys.argv[3]
        bitrate = sys.argv[4]

    return input_path, output_path, music_format, bitrate, replace_mode

def validate_paths_and_parameters(input_path, output_path, music_format, bitrate):
    """
    Validate input/output paths and conversion parameters.

    Args:
        input_path (str): Path to source files
        output_path (str): Path for converted files
        music_format (str): Target audio format
        bitrate (str): Target bitrate

    Raises:
        SystemExit: If any validation fails
    """
    if not os.path.isdir(input_path):
        print("The input path does not exist")
        sys.exit(1)

    if not os.path.isdir(output_path):
        try:
            os.makedirs(output_path)
        except Exception as e:
            print(f"Failed to create the output path: {e}")
            sys.exit(1)

    valid_formats = {"mp3", "flac", "wav", "m4a", "ogg", "opus", "wma", "aac"}
    if music_format not in valid_formats:
        print("The music format is not valid")
        sys.exit(1)

    valid_bitrates = {"32k", "64k", "128k", "192k", "256k", "320k"}
    if bitrate not in valid_bitrates:
        print("The bitrate is not valid")
        sys.exit(1)

def setup_logging(input_path):
    """
    Set up logging configuration with both file and console output.

    Args:
        input_path (str): Path to source files, used in initial log entry

    Returns:
        str: Path to the created log file
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # Setup logging with timestamp in filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'convert_{timestamp}.log')

    # Configure logging with UTF-8 encoding
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),  # Specify UTF-8 encoding for file
            logging.StreamHandler(sys.stdout)  # Use stdout for console output
        ]
    )

    # Log initial information
    logging.info(f"Starting conversion process")
    logging.info(f"Input path: {input_path}")
    return log_file

def get_audio_info(file_path):
    """
    Get audio format and bitrate information using ffprobe.

    Args:
        file_path (str): Path to the audio file

    Returns:
        tuple: (format_name, bitrate) or (None, None) if retrieval fails
    """
    try:
        # Handle Unicode paths by encoding properly
        encoded_path = os.fsdecode(file_path)

        # Add timeout to prevent hanging
        result = subprocess.run([
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            encoded_path
        ], capture_output=True, text=True, encoding='utf-8', timeout=10)  # Add 10 second timeout

        if result.returncode == 0 and result.stdout:
            try:
                info = json.loads(result.stdout)
                for stream in info.get('streams', []):
                    if stream.get('codec_type') == 'audio':
                        # Get format
                        format_name = info['format']['format_name'].split(',')[0]

                        # Get bitrate
                        bitrate = stream.get('bit_rate')
                        if bitrate:
                            bitrate = f"{int(int(bitrate)/1000)}k"

                        return format_name, bitrate
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON for {file_path}: {str(e)}")
                return None, None
        return None, None
    except subprocess.TimeoutExpired:
        logging.error(f"Timeout while processing {file_path}")
        return None, None
    except Exception as e:
        logging.error(f"Error getting audio info for {file_path}: {str(e)}")
        return None, None

def get_lock_file_path():
    """
    Get the path to the lock file, which is stored next to the script.
    Creates the lock file if it doesn't exist.
    
    Returns:
        str: Path to lock file
    """
    lock_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.convert.lock')
    if not os.path.exists(lock_file):
        try:
            with open(lock_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=2, ensure_ascii=False)
            logging.info(f"Created new lock file: {lock_file}")
        except Exception as e:
            logging.error(f"Failed to create lock file: {str(e)}")
    return lock_file

def read_lock_file(lock_file):
    """
    Read the lock file containing information about converted files.

    Args:
        lock_file (str): Path to lock file

    Returns:
        dict: Dictionary with file paths as keys and conversion info as values
    """
    try:
        if os.path.exists(lock_file):
            with open(lock_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Error reading lock file: {str(e)}")
    return {}

def update_lock_file(lock_file, converted_files_info):
    """
    Update the lock file with new conversion information.

    Args:
        lock_file (str): Path to lock file
        converted_files_info (dict): Dictionary with conversion information to add
    """
    try:
        # Read existing data
        lock_data = read_lock_file(lock_file)
        # Update with new data
        lock_data.update(converted_files_info)
        # Write back to file
        with open(lock_file, 'w', encoding='utf-8') as f:
            json.dump(lock_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Error updating lock file: {str(e)}")

def process_files(input_path, output_path, music_format, bitrate, replace_mode):
    """
    Process all files in the input directory, converting audio files and copying others as needed.

    Args:
        input_path (str): Source directory path
        output_path (str): Destination directory path
        music_format (str): Target audio format
        bitrate (str): Target bitrate
        replace_mode (bool): Whether to replace original files

    Returns:
        tuple: (file_count, converted_files, skipped_files, failed_files, correct_files)
            - file_count: Dict mapping extensions to count of processed files
            - converted_files: List of successfully converted files
            - skipped_files: List of files skipped (already exist)
            - failed_files: List of files that failed conversion
            - correct_files: List of files already in target format/bitrate
    """
    file_count = {}  # Dictionary to keep track of file counts
    converted_files = []  # List to store successfully converted files
    skipped_files = []   # List to store skipped files
    failed_files = []    # List to store failed conversions
    correct_files = []   # List to store files already in correct format/bitrate

    # Get lock file path
    lock_file = get_lock_file_path()
    converted_files_info = read_lock_file(lock_file)
    new_conversions = {}

    def increment_count(ext):
        if ext not in file_count:
            file_count[ext] = 0
        file_count[ext] += 1

    for root, _, files in os.walk(input_path):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(root, input_path)
            target_dir = root if replace_mode else os.path.join(output_path, relative_path)

            if not replace_mode:
                os.makedirs(target_dir, exist_ok=True)

            ext = os.path.splitext(file)[1][1:].lower()

            # Process audio files
            if ext in {"mp3", "flac", "wav", "m4a", "ogg", "opus", "wma", "aac"}:
                # Check if file is in lock file
                file_info = converted_files_info.get(file_path)
                if file_info and file_info.get('format') == music_format and file_info.get('bitrate') == bitrate:
                    logging.info(f"Skipping previously processed file (from lock): {file_path}")
                    skipped_files.append(file_path)
                    increment_count(ext)
                    continue

                # Check current format and bitrate
                current_format, current_bitrate = get_audio_info(file_path)
                
                if current_format == music_format and current_bitrate == bitrate:
                    logging.info(f"Skipping file already in correct format and bitrate: {file_path}")
                    # Add to lock file info
                    new_conversions[file_path] = {
                        'format': music_format,
                        'bitrate': bitrate,
                        'timestamp': datetime.now().isoformat(),
                        'status': 'correct_format'
                    }
                    correct_files.append(file_path)
                    increment_count(ext)
                    continue

                if replace_mode:
                    output_file = os.path.join(target_dir, f"{os.path.splitext(file)[0]}_temp.{music_format}")
                else:
                    output_file = os.path.join(target_dir, f"{os.path.splitext(file)[0]}.{music_format}")
                    if os.path.exists(output_file):
                        logging.info(f"Skipping already converted file: {file_path}")
                        skipped_files.append(file_path)
                        continue

                try:
                    result = subprocess.run(
                        ["ffmpeg", "-i", file_path, "-b:a", bitrate, "-map_metadata", "0", "-id3v2_version", "3", output_file],
                        capture_output=True,
                        text=True
                    )

                    if result.returncode == 0:
                        if replace_mode:
                            os.remove(file_path)
                            final_path = os.path.join(target_dir, f"{os.path.splitext(file)[0]}.{music_format}")
                            os.rename(output_file, final_path)
                            logging.info(f"Successfully converted and replaced: {file_path}")
                        else:
                            logging.info(f"Successfully converted: {file_path} -> {output_file}")

                        # Add to lock file info
                        new_conversions[file_path] = {
                            'format': music_format,
                            'bitrate': bitrate,
                            'timestamp': datetime.now().isoformat(),
                            'status': 'converted'
                        }
                        converted_files.append(file_path)
                    else:
                        logging.error(f"Failed to convert {file_path}: {result.stderr}")
                        failed_files.append(file_path)
                        continue

                except Exception as e:
                    logging.error(f"Error processing {file_path}: {str(e)}")
                    failed_files.append(file_path)
                    continue

                increment_count(ext)

            # Handle image and nfo files
            elif ext in {"jpg", "jpeg", "png", "gif", "bmp", "webp", "nfo"}:
                if not replace_mode:
                    try:
                        shutil.copy(file_path, target_dir)
                        logging.info(f"Copied: {file_path} -> {target_dir}")
                        increment_count(ext)
                    except Exception as e:
                        logging.error(f"Failed to copy {file_path}: {str(e)}")

    # Update lock file with new conversions
    if new_conversions:
        update_lock_file(lock_file, new_conversions)

    # Print and log summary
    summary = "\nConversion Summary:\n" + "="*50 + "\n"
    summary += f"Total files processed: {sum(file_count.values())}\n"
    summary += f"Successfully converted: {len(converted_files)}\n"
    summary += f"Skipped (already converted): {len(skipped_files)}\n"
    summary += f"Skipped (correct format/bitrate): {len(correct_files)}\n"
    summary += f"Failed conversions: {len(failed_files)}\n\n"

    summary += "File counts by extension:\n" + "-"*30 + "\n"
    for ext, count in file_count.items():
        summary += f"{ext}: {count} files\n"

    if failed_files:
        summary += "\nFailed files:\n" + "-"*30 + "\n"
        for file in failed_files:
            summary += f"- {file}\n"

    logging.info(summary)

    return file_count, converted_files, skipped_files, failed_files, correct_files

def main():
    """
    Main function orchestrating the conversion process.

    Process:
    1. Check dependencies (Python version, ffmpeg)
    2. Validate command line arguments
    3. Set up logging
    4. Process all files
    5. Generate summary
    """
    check_python_version()
    check_ffmpeg()
    input_path, output_path, music_format, bitrate, replace_mode = validate_arguments()
    validate_paths_and_parameters(input_path, output_path, music_format, bitrate)

    # Setup logging
    log_file = setup_logging(input_path)
    logging.info(f"Output path: {output_path}")
    logging.info(f"Format: {music_format}")
    logging.info(f"Bitrate: {bitrate}")
    logging.info(f"Replace mode: {replace_mode}")

    # Process files and get statistics
    file_count, converted_files, skipped_files, failed_files, correct_files = process_files(
        input_path, output_path, music_format, bitrate, replace_mode
    )

    logging.info(f"Conversion completed. Log file: {log_file}")

if __name__ == "__main__":
    main()