#!/bin/bash

# Helper script to download and run the build-ffmpeg script.

clear

# VERIFY THE SCRIPT DOES NOT HAVE ROOT ACCESS BEFORE CONTINUING
# THIS CAN CAUSE ISSUES USING THE 'IF WHICH' COMMANDS IF RUN AS ROOT
if [ "$EUID" -eq '0' ]; then
    exec bash "$0" "$@"
fi

make_dir ()
{
    if [ ! -d "$1" ]; then
        if ! mkdir "$1"; then            
            printf '\n%s\n\n' "Failed to create dir: $1";
            exit 1
        fi
    fi    
}

command_exists()
{
    if ! [[ -x $(command -v "$1") ]]; then
        return 1
    fi

    return 0
}

build_dir='ffmpeg-build'

if ! command_exists 'curl'; then
    printf '\n%s\n\n%s\n\n' \
        'The curl command is not installed.' \
        'To install it run the command: sudo apt install curl'
    exit 1
fi

echo 'ffmpeg-build-script-downloader v0.1'
echo '========================================================'
echo

echo 'First we create the ffmpeg build directory' "$build_dir"
echo '========================================================'
echo
make_dir "$build_dir" && cd "$build_dir" || exit 1

echo 'Now we download and execute the build script'
echo '========================================================'
echo

bash <(curl -sSL 'https://raw.githubusercontent.com/slyfox1186/ffmpeg-build-script/main/build-ffmpeg.sh') --build --latest
