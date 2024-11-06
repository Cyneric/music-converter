#!/bin/bash

#
# @file .convert.sh
#
# @created Fri Jul 26 2024
# @Author Christian Blank <christianblank91@gmail.com>
#
# @Copyright (c) 2024
#

# This script converts audio files to a specified format and bitrate using ffmpeg.
# It also copies image files and nfo files to the output directory.
# The script requires ffmpeg to be installed on the system.

# The script takes three or four arguments:
# 1. input_path: The path to the directory containing the audio files to convert.
# 2. music_format: The format to convert the audio files to (mp3, flac, wav, m4a, ogg, opus, wma, aac).
# 3. bitrate: The bitrate to use for the conversion (32k, 64k, 128k, 192k, 256k, 320k).
# 4. Optional: --replace flag to replace original files instead of copying to output directory
#
# usage: ./convert.sh input_path music_format bitrate [--replace]
# example: ./convert.sh ~/Music mp3 320k --replace
# or: ./convert.sh input_path output_path music_format bitrate

# check if ffmpeg is installed and install if missing
check_ffmpeg() {
    if ! command -v ffmpeg &>/dev/null; then
        read -p "ffmpeg is not installed. Would you like to install it now? (y/n): " choice
        if [ "$choice" = "y" ]; then
            # Detect OS and package manager
            if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$(uname -r)" == *"microsoft-standard"* ]]; then
                # Linux or WSL
                if command -v apt-get &>/dev/null; then
                    sudo apt-get update && sudo apt-get install -y ffmpeg
                elif command -v dnf &>/dev/null; then
                    sudo dnf install -y ffmpeg
                elif command -v pacman &>/dev/null; then
                    sudo pacman -S --noconfirm ffmpeg
                elif command -v zypper &>/dev/null; then
                    sudo zypper install -y ffmpeg
                else
                    echo "Attempting to install ffmpeg using wget..."
                    if ! command -v wget &>/dev/null; then
                        echo "Installing wget first..."
                        if command -v apt-get &>/dev/null; then
                            sudo apt-get update && sudo apt-get install -y wget
                        else
                            echo "Cannot install wget. Please install ffmpeg manually."
                            exit 1
                        fi
                    fi

                    # Create temporary directory
                    tmp_dir="/tmp/ffmpeg_install"
                    mkdir -p "$tmp_dir"
                    cd "$tmp_dir"

                    # Download and extract ffmpeg
                    wget "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
                    tar xf ffmpeg-release-amd64-static.tar.xz

                    # Move ffmpeg to system path
                    ffmpeg_dir=$(ls | grep "ffmpeg-")
                    sudo cp "$ffmpeg_dir/ffmpeg" "/usr/local/bin/"
                    sudo cp "$ffmpeg_dir/ffprobe" "/usr/local/bin/"

                    # Cleanup
                    cd /
                    rm -rf "$tmp_dir"
                    echo "ffmpeg installed successfully using wget"
                fi
            elif [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS
                if command -v brew &>/dev/null; then
                    brew install ffmpeg
                else
                    echo "Homebrew not found. Please install Homebrew first:"
                    echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                    exit 1
                fi
            else
                echo "Unsupported operating system"
                exit 1
            fi
        else
            echo "ffmpeg is required to run this script. Exiting."
            exit 1
        fi
    fi
}

# check if Python 3 is installed and install if missing
check_python() {
    if ! command -v python3 &>/dev/null; then
        read -p "Python 3 is not installed. Would you like to install it now? (y/n): " choice
        if [ "$choice" = "y" ]; then
            if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$(uname -r)" == *"microsoft-standard"* ]]; then
                if command -v apt-get &>/dev/null; then
                    sudo apt-get update && sudo apt-get install -y python3 python3-pip
                elif command -v dnf &>/dev/null; then
                    sudo dnf install -y python3 python3-pip
                elif command -v pacman &>/dev/null; then
                    sudo pacman -S --noconfirm python python-pip
                elif command -v zypper &>/dev/null; then
                    sudo zypper install -y python3 python3-pip
                else
                    echo "Could not detect package manager. Please install Python 3 manually."
                    exit 1
                fi
            elif [[ "$OSTYPE" == "darwin"* ]]; then
                if command -v brew &>/dev/null; then
                    brew install python
                else
                    echo "Homebrew not found. Please install Homebrew first:"
                    echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                    exit 1
                fi
            else
                echo "Unsupported operating system"
                exit 1
            fi
        else
            echo "Python 3 is required to run this script. Exiting."
            exit 1
        fi
    fi
}

# Call the check_ffmpeg function at the start
check_ffmpeg

# Call the check_python function at the start
check_python

# validate input arguments
replace_mode=false
if [ "$#" -eq 4 ] && [ "$4" = "--replace" ]; then
    replace_mode=true
    input_path="$1"
    output_path="$input_path" # In replace mode, output is same as input
    music_format="$2"
    bitrate="$3"
elif [ "$#" -eq 4 ] && [ "$4" != "--replace" ]; then
    input_path="$1"
    output_path="$2"
    music_format="$3"
    bitrate="$4"
else
    echo "Usage: $0 input_path music_format bitrate [--replace]"
    echo "   or: $0 input_path output_path music_format bitrate"
    exit 1
fi

# validate paths and parameters
if [ ! -d "$input_path" ]; then
    echo "The input path does not exist"
    exit 1
fi

if [ "$replace_mode" = false ] && [ ! -d "$output_path" ] && ! mkdir -p "$output_path"; then
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

setup_logging() {
    # Create logs directory
    log_dir="$(dirname "$0")/logs"
    mkdir -p "$log_dir"

    # Create log file with timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    log_file="$log_dir/convert_${timestamp}.log"

    # Start logging (modified to avoid double output)
    exec 1> >(tee -a "$log_file")
    exec 2> >(tee -a "$log_file" >&2)

    echo "Starting conversion process"
    echo "Input path: $input_path"
    echo "Output path: $output_path"
    echo "Format: $music_format"
    echo "Bitrate: $bitrate"
    echo "Replace mode: $replace_mode"

    echo "$log_file"
}

get_audio_info() {
    local file="$1"
    local format_info
    format_info=$(ffprobe -v quiet -print_format json -show_format -show_streams "$file")

    if [ $? -eq 0 ]; then
        # Using jq if available, otherwise fallback to grep and sed
        if command -v jq &>/dev/null; then
            local current_format=$(echo "$format_info" | jq -r '.format.format_name' | cut -d',' -f1)
            local current_bitrate=$(echo "$format_info" | jq -r '.streams[] | select(.codec_type=="audio") | .bit_rate' |
                awk '{ printf "%dk", int($1/1000) }')
            echo "$current_format:$current_bitrate"
        else
            local current_format=$(echo "$format_info" | grep -o '"format_name":"[^"]*"' | cut -d'"' -f4 | cut -d',' -f1)
            local current_bitrate=$(echo "$format_info" | grep -o '"bit_rate":"[^"]*"' | head -1 | cut -d'"' -f4 |
                awk '{ printf "%dk", int($1/1000) }')
            echo "$current_format:$current_bitrate"
        fi
    else
        echo "error:error"
    fi
}

process_files() {
    local dir_path="$1"
    local target_dir
    local converted_count=0
    local skipped_count=0
    local failed_count=0
    local correct_count=0

    if [ "$replace_mode" = true ]; then
        target_dir="$dir_path"
    else
        target_dir="$output_path${dir_path#$input_path}"
        mkdir -p "$target_dir"
    fi

    # Process audio files with logging
    find "$dir_path" -maxdepth 1 -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.wav" -o -iname "*.m4a" -o -iname "*.ogg" \
        -o -iname "*.opus" -o -iname "*.wma" -o -iname "*.aac" \) -print0 | while IFS= read -r -d '' file; do
        local base_name="${file##*/}"
        base_name="${base_name%.*}"

        # Check current format and bitrate
        audio_info=$(get_audio_info "$file")
        current_format="${audio_info%:*}"
        current_bitrate="${audio_info#*:}"

        if [ "$current_format" = "$music_format" ] && [ "$current_bitrate" = "$bitrate" ]; then
            echo "Skipping file already in correct format and bitrate: $file"
            ((correct_count++))
            increment_count "${file##*.}"
            continue
        fi

        if [ "$replace_mode" = true ]; then
            local output_file="$target_dir/${base_name}_temp.$music_format"
            local final_file="$target_dir/${base_name}.$music_format"
        else
            local output_file="$target_dir/${base_name}.$music_format"
            if [ -f "$output_file" ]; then
                echo "Skipping already converted file: $file"
                ((skipped_count++))
                continue
            fi
        fi

        if ffmpeg -i "$file" -b:a "$bitrate" -map_metadata 0 -id3v2_version 3 "$output_file" 2>>"$log_file"; then
            if [ "$replace_mode" = true ]; then
                rm "$file"
                mv "$output_file" "$final_file"
                echo "Successfully converted and replaced: $file"
            else
                echo "Successfully converted: $file -> $output_file"
            fi
            ((converted_count++))
            increment_count "${file##*.}"
        else
            echo "Failed to convert: $file"
            ((failed_count++))
        fi
    done

    # Process image and nfo files
    if [ "$replace_mode" = false ]; then
        find "$dir_path" -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.gif" \
            -o -iname "*.bmp" -o -iname "*.webp" -o -iname "*.nfo" \) -print0 | while IFS= read -r -d '' file; do
            if cp "$file" "$target_dir/"; then
                echo "Copied: $file -> $target_dir/"
                increment_count "${file##*.}"
            else
                echo "Failed to copy: $file"
                ((failed_count++))
            fi
        done
    fi

    # Return counts including correct_count
    echo "$converted_count:$skipped_count:$failed_count:$correct_count"
}

# Add before the find command
log_file=$(setup_logging)

# Add after the find command
echo -e "\nConversion Summary:"
echo "===================="
echo "Total files processed: ${#file_count[@]}"
echo "Successfully converted: $converted_count"
echo "Skipped (already converted): $skipped_count"
echo "Skipped (correct format/bitrate): $correct_count"
echo "Failed conversions: $failed_count"
echo -e "\nFile counts by extension:"
for ext in "${!file_count[@]}"; do
    echo "${ext}: ${file_count[$ext]} files"
done

echo -e "\nLog file: $log_file"
