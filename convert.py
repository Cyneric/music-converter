#!/usr/bin/env python3

import os
import subprocess
import sys
import shutil

def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        choice = input("ffmpeg is not installed. Would you like to install it now? (y/n): ")
        if choice.lower() == 'y':
            subprocess.run(["sudo", "apt-get", "update"])
            subprocess.run(["sudo", "apt-get", "install", "-y", "ffmpeg"])
        else:
            print("ffmpeg is required to run this script. Exiting.")
            sys.exit(1)

def validate_arguments():
    if len(sys.argv) != 5:
        print("Usage: {} input_path output_path music_format bitrate".format(sys.argv[0]))
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    music_format = sys.argv[3]
    bitrate = sys.argv[4]
    return input_path, output_path, music_format, bitrate

def validate_paths_and_parameters(input_path, output_path, music_format, bitrate):
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

def process_files(input_path, output_path, music_format, bitrate):
    file_count = {}  # Dictionary to keep track of file counts

    def increment_count(ext):
        if ext not in file_count:
            file_count[ext] = 0
        file_count[ext] += 1

    for root, _, files in os.walk(input_path):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(root, input_path)
            target_dir = os.path.join(output_path, relative_path)
            os.makedirs(target_dir, exist_ok=True)
            ext = os.path.splitext(file)[1][1:].lower()

            # Process audio files
            if ext in {"mp3", "flac", "wav", "m4a", "ogg", "opus", "wma", "aac"}:
                output_file = os.path.join(target_dir, f"{os.path.splitext(file)[0]}.{music_format}")
                if os.path.exists(output_file):
                    print(f"Skipping already converted file: {output_file}")
                    continue
                subprocess.run(["ffmpeg", "-i", file_path, "-b:a", bitrate, "-map_metadata", "0", "-id3v2_version", "3", output_file])
                increment_count(ext)

            # Copy image files
            elif ext in {"jpg", "jpeg", "png", "gif", "bmp", "webp"}:
                shutil.copy(file_path, target_dir)
                increment_count(ext)

            # Copy .nfo files
            elif ext == "nfo":
                shutil.copy(file_path, target_dir)
                increment_count(ext)

    print("File conversion summary:")
    for ext, count in file_count.items():
        print(f"{ext}: {count} files processed")

def main():
    check_ffmpeg()
    input_path, output_path, music_format, bitrate = validate_arguments()
    validate_paths_and_parameters(input_path, output_path, music_format, bitrate)
    process_files(input_path, output_path, music_format, bitrate)

if __name__ == "__main__":
    main()