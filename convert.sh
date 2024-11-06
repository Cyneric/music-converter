#!/bin/bash

#
# @file convert.sh
# @created Fri Jul 26 2024
# @modified Wed Nov 06 2024
# @author Christian Blank <christianblank91@gmail.com>
# @copyright (c) 2024
#
# Audio Format Converter
#
# This script converts audio files to different formats while preserving metadata.
# It also handles copying of associated image and NFO files.
#
# Features:
# - Convert audio files to various formats (mp3, flac, wav, m4a, ogg, opus, wma, aac)
# - Support for multiple bitrates (32k, 64k, 128k, 192k, 256k, 320k)
# - Preserve metadata during conversion
# - Handle image files (jpg, jpeg, png, gif, bmp, webp)
# - Copy NFO files
# - Two operation modes: copy to new directory or replace in place
# - Detailed logging of all operations
#
# Usage Examples:
# 1. Convert files to new directory:
#    ./convert.sh ~/Music/Albums ~/Converted mp3 320k
#    This will convert all audio files to 320k MP3 format and copy them to ~/Converted
#
# 2. Convert and replace original files:
#    ./convert.sh ~/Music mp3 320k --replace
#    This will convert all audio files to 320k MP3 format and replace the originals
#
# 3. Convert to different formats:
#    ./convert.sh ~/Podcasts ~/Compressed opus 64k
#    ./convert.sh ~/Vinyl_Rips ~/Archive flac 320k
#    ./convert.sh ~/DJ_Music ~/Mobile mp3 128k
#
#

# Function: check_ffmpeg
# Description: Check if ffmpeg is installed and offer to install it if missing.
# Supports multiple package managers and installation methods across different OS.
#
# Installation methods:
# - Linux: apt-get, dnf, pacman, zypper, or wget fallback
# - macOS: Homebrew
# - WSL: Native package managers
#
# Returns: None
# Exits with status 1 if installation fails or is declined
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

# Function: check_python
# Description: Check if Python 3 is installed and offer to install it if missing.
# Supports multiple package managers and installation methods.
#
# Installation methods:
# - Linux: apt-get, dnf, pacman, zypper
# - macOS: Homebrew
# - WSL: Native package managers
#
# Returns: None
# Exits with status 1 if installation fails or is declined
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

# Function: setup_logging
# Description: Initialize logging with timestamp-based log file
#
# Global variables used:
# - input_path: Source directory path
# - output_path: Destination directory path
# - music_format: Target audio format
# - bitrate: Target bitrate
# - replace_mode: Whether to replace original files
#
# Returns: Path to the created log file
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

# Function: get_audio_info
# Description: Get audio format and bitrate information using ffprobe
#
# Arguments:
#   $1 - Path to the audio file
#
# Returns: String in format "format:bitrate" or "error:error" if retrieval fails
# Example return: "mp3:320k"
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

# Function: increment_count
# Description: Increment the count for a given file extension in the file_count array
#
# Arguments:
#   $1 - File extension to increment count for
#
# Global variables modified:
#   file_count - Associative array tracking file counts by extension
increment_count() {
    local ext="$1"
    ((file_count[$ext]++))
}

# Function: get_lock_file_path
# Description: Get the path to the lock file for the given output directory
#
# Arguments:
#   $1 - Output directory path
#
# Returns: Path to lock file
get_lock_file_path() {
    local output_dir="$1"
    echo "$output_dir/.convert.lock"
}

# Function: read_lock_file
# Description: Read the lock file containing information about converted files
#
# Arguments:
#   $1 - Path to lock file
#
# Returns: JSON string with conversion information (empty if no lock file)
read_lock_file() {
    local lock_file="$1"
    if [ -f "$lock_file" ]; then
        cat "$lock_file"
    else
        echo "{}"
    fi
}

# Function: update_lock_file
# Description: Update the lock file with new conversion information
#
# Arguments:
#   $1 - Path to lock file
#   $2 - JSON string with new conversion information
update_lock_file() {
    local lock_file="$1"
    local new_data="$2"
    local temp_file

    # Create temporary file
    temp_file=$(mktemp)

    if [ -f "$lock_file" ]; then
        # Merge existing data with new data using jq if available
        if command -v jq &>/dev/null; then
            jq -s '.[0] * .[1]' "$lock_file" <(echo "$new_data") >"$temp_file"
        else
            # Fallback to simple overwrite if jq is not available
            echo "$new_data" >"$temp_file"
        fi
    else
        echo "$new_data" >"$temp_file"
    fi

    # Move temporary file to lock file
    mv "$temp_file" "$lock_file"
}

# Function: process_files
# Description: Process all files in the input directory
#
# Arguments:
#   $1 - Directory path to process
#
# Global variables used:
#   replace_mode - Whether to replace original files
#   music_format - Target audio format
#   bitrate - Target bitrate
#   output_path - Destination directory path
#   file_count - Associative array tracking file counts
#
# Operations:
# - Converts audio files to specified format and bitrate
# - Copies image and NFO files in non-replace mode
# - Handles file replacement in replace mode
# - Tracks conversion statistics
#
# Returns: String with counts in format "converted:skipped:failed:correct"
process_files() {
    local dir_path="$1"
    local target_dir
    local converted_count=0
    local skipped_count=0
    local failed_count=0
    local correct_count=0
    local new_conversions="{}"

    if [ "$replace_mode" = true ]; then
        target_dir="$dir_path"
    else
        target_dir="$output_path${dir_path#$input_path}"
        mkdir -p "$target_dir"
    fi

    # Get lock file path and read existing conversions
    local lock_file
    lock_file=$(get_lock_file_path "$([ "$replace_mode" = true ] && echo "$input_path" || echo "$output_path")")
    local lock_data
    lock_data=$(read_lock_file "$lock_file")

    # Process audio files with logging
    find "$dir_path" -maxdepth 1 -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.wav" -o -iname "*.m4a" -o -iname "*.ogg" \
        -o -iname "*.opus" -o -iname "*.wma" -o -iname "*.aac" \) -print0 | while IFS= read -r -d '' file; do

        # Check if file is in lock file
        if echo "$lock_data" | grep -q "\"$file\""; then
            local file_format
            local file_bitrate
            if command -v jq &>/dev/null; then
                file_format=$(echo "$lock_data" | jq -r ".[\"$file\"].format")
                file_bitrate=$(echo "$lock_data" | jq -r ".[\"$file\"].bitrate")
            else
                file_format=$(echo "$lock_data" | grep -o "\"format\":\"[^\"]*\"" | cut -d'"' -f4)
                file_bitrate=$(echo "$lock_data" | grep -o "\"bitrate\":\"[^\"]*\"" | cut -d'"' -f4)
            fi

            if [ "$file_format" = "$music_format" ] && [ "$file_bitrate" = "$bitrate" ]; then
                echo "Skipping previously converted file (from lock): $file"
                ((skipped_count++))
                increment_count "${file##*.}"
                continue
            fi
        fi

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
            local output_file="$target_dir/${file##*/}_temp.$music_format"
            local final_file="$target_dir/${file##*/}.$music_format"
        else
            local output_file="$target_dir/${file##*/}.$music_format"
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

        # After successful conversion, add to new_conversions
        if [ $? -eq 0 ]; then
            # Create JSON entry for the converted file
            local timestamp
            timestamp=$(date -Iseconds)
            new_conversions=$(echo "$new_conversions" | jq --arg file "$file" \
                --arg format "$music_format" \
                --arg bitrate "$bitrate" \
                --arg ts "$timestamp" \
                '. + {($file): {"format": $format, "bitrate": $bitrate, "timestamp": $ts}}')
        fi
    done

    # Update lock file with new conversions if any were made
    if [ "$new_conversions" != "{}" ]; then
        update_lock_file "$lock_file" "$new_conversions"
    fi

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

# Script execution starts here
# Initialize required variables and perform dependency checks
# Check dependencies
check_ffmpeg
check_python

# Initialize tracking variables
declare -A file_count
converted_count=0
skipped_count=0
failed_count=0
correct_count=0

# Validate input arguments
if [ "$#" -eq 4 ] && [ "$4" = "--replace" ]; then
    replace_mode=true
    input_path="$1"
    output_path="$input_path" # In replace mode, output is same as input
    music_format="$2"
    bitrate="$3"
elif [ "$#" -eq 4 ] && [ "$4" != "--replace" ]; then
    replace_mode=false
    input_path="$1"
    output_path="$2"
    music_format="$3"
    bitrate="$4"
else
    echo "Usage: $0 input_path music_format bitrate [--replace]"
    echo "   or: $0 input_path output_path music_format bitrate"
    exit 1
fi

# Validate paths and parameters
if [ ! -d "$input_path" ]; then
    echo "The input path does not exist"
    exit 1
fi

if [ "$replace_mode" = false ] && [ ! -d "$output_path" ]; then
    mkdir -p "$output_path" || {
        echo "Failed to create the output path"
        exit 1
    }
fi

# Validate format
if [[ ! "$music_format" =~ ^(mp3|flac|wav|m4a|ogg|opus|wma|aac)$ ]]; then
    echo "The music format is not valid"
    exit 1
fi

# Validate bitrate
if [[ ! "$bitrate" =~ ^(32k|64k|128k|192k|256k|320k)$ ]]; then
    echo "The bitrate is not valid"
    exit 1
fi

# Set up logging and process files
log_file=$(setup_logging)

# Process all directories recursively
find "$input_path" -type d -exec bash -c 'process_files "$0"' {} \;

# After all processing is done, print summary once
{
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
} | tee -a "$log_file"
