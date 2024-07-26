#!/bin/bash

# takes an input path as an argument to a library of folders containing different file types and an output path to store the converted files
# also takes an argument for the desired music format and the bitrate
# loop through the folders and files and convert them to the desired music format using ffmpeg but leaving the original files untouched
# copy all found images and .nfo files in the folders to the output path
# store the converted files in the output path with the same folder structure as the input path

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

# check if the input path is provided
if [ -z "$1" ]; then
    echo "Please provide the input path as the first argument"
    exit 1
fi

# check if the output path is provided
if [ -z "$2" ]; then
    echo "Please provide the output path as the second argument"
    exit 1
fi

# check if the music format is provided
if [ -z "$3" ]; then
    echo "Please provide the music format as the third argument"
    exit 1
fi

# check if the bitrate is provided
if [ -z "$4" ]; then
    echo "Please provide the bitrate as the fourth argument"
    exit 1
fi

# check if the input path exists
if [ ! -d "$1" ]; then
    echo "The input path does not exist"
    exit 1
fi

# check if the output path exists
if [ ! -d "$2" ]; then
    if ! mkdir -p "$2"; then
        echo "Failed to create the output path"
        exit 1
    fi
fi

# check if the music format is valid
if [[ ! "$3" =~ ^(mp3|flac|wav|m4a|ogg|opus|wma|aac)$ ]]; then
    echo "The music format is not valid"
    exit 1
fi

# check if the bitrate is valid
if [[ ! "$4" =~ ^(32k|64k|128k|192k|256k|320k)$ ]]; then
    echo "The bitrate is not valid"
    exit 1
fi

input_path="$1"
output_path="$2"
music_format="$3"
bitrate="$4"

declare -A file_count

# function to update file count
increment_count() {
    local ext="$1"
    ((file_count[$ext]++))
}

# loop through each directory below input path and process files within each folder one by one
find "$input_path" -type d | while IFS= read -r dir_path; do
    echo "Processing folder: $dir_path"
    relative_dir="${dir_path#$input_path}"
    target_dir="$output_path$relative_dir"

    mkdir -p "$target_dir"

    # convert audio files
    find "$dir_path" -maxdepth 1 -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.wav" -o -iname "*.m4a" -o -iname "*.ogg" -o -iname "*.opus" -o -iname "*.wma" -o -iname "*.aac" \) -print0 | while IFS= read -r -d '' file; do
        relative_path="${file#$input_path/}"
        output_file="$output_path/${relative_path%.*}.$music_format"
        ffmpeg -i "$file" -b:a "$bitrate" -map_metadata 0 -id3v2_version 3 "$output_file"
        increment_count "${file##*.}"
    done

    # copy images
    find "$dir_path" -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.gif" -o -iname "*.bmp" -o -iname "*.webp" \) -print0 | while IFS= read -r -d '' file; do
        cp "$file" "$target_dir/"
        increment_count "${file##*.}"
    done

    # copy .nfo files
    find "$dir_path" -maxdepth 1 -type f -iname "*.nfo" -print0 | while IFS= read -r -d '' file; do
        cp "$file" "$target_dir/"
        increment_count "nfo"
    done
done

# print the file count summary
echo "File conversion summary:"
for ext in "${!file_count[@]}"; do
    echo "${ext}: ${file_count[$ext]} files processed"
done
