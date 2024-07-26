#!/bin/bash

# usage: ./convert.sh input_path output_path music_format bitrate
# example: ./convert.sh ~/Music ~/Music/converted mp3 320k

# check if ffmpeg is installed
if ! command -v ffmpeg &>/dev/null; then
    read -p "ffmpeg is not installed. Would you like to install it now? (y/n): " choice
    if [ "$choice" = "y" ]; then
        sudo apt-get update && sudo apt-get install -y ffmpeg
    else
        echo "ffmpeg is required to run this script. Exiting."
        exit 1
    fi
fi

# validate input arguments
if [ $# -ne 4 ]; then
    echo "Usage: $0 input_path output_path music_format bitrate"
    exit 1
fi

input_path="$1"
output_path="$2"
music_format="$3"
bitrate="$4"

# validate paths and parameters
if [ ! -d "$input_path" ]; then
    echo "The input path does not exist"
    exit 1
fi

if [ ! -d "$output_path" ] && ! mkdir -p "$output_path"; then
    echo "Failed to create the output path"
    exit 1
fi

if [[ ! "$music_format" =~ ^(mp3|flac|wav|m4a|ogg|opus|wma|aac)$ ]]; then
    echo "The music format is not valid"
    exit 1
fi

if [[ ! "$bitrate" =~ ^(32k|64k|128k|192k|256k|320k)$ ]]; then
    echo "The bitrate is not valid"
    exit 1
fi

declare -A file_count

increment_count() {
    local ext="$1"
    ((file_count[$ext]++))
}

process_files() {
    local dir_path="$1"
    local target_dir="$output_path${dir_path#$input_path}"

    mkdir -p "$target_dir"

    find "$dir_path" -maxdepth 1 -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.wav" -o -iname "*.m4a" -o -iname "*.ogg" \
        -o -iname "*.opus" -o -iname "*.wma" -o -iname "*.aac" \) -print0 | while IFS= read -r -d '' file; do
        local output_file="$target_dir/${file##*/}"
        output_file="${output_file%.*}.$music_format"

        # Skip conversion if output file already exists
        if [ -f "$output_file" ]; then
            echo "Skipping already converted file: $file"
            continue
        fi

        ffmpeg -i "$file" -b:a "$bitrate" -map_metadata 0 -id3v2_version 3 "$output_file"
        increment_count "${file##*.}"
    done

    find "$dir_path" -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.gif" -o -iname "*.bmp" -o -iname "*.webp" \) -print0 | while IFS= read -r -d '' file; do
        cp "$file" "$target_dir/"
        increment_count "${file##*.}"
    done

    find "$dir_path" -maxdepth 1 -type f -iname "*.nfo" -print0 | while IFS= read -r -d '' file; do
        cp "$file" "$target_dir/"
        increment_count "nfo"
    done
}

export -f increment_count
export -f process_files
export input_path
export output_path
export music_format
export bitrate

find "$input_path" -type d -exec bash -c 'process_files "$0"' {} \;

echo "File conversion summary:"
for ext in "${!file_count[@]}"; do
    echo "${ext}: ${file_count[$ext]} files processed"
done
