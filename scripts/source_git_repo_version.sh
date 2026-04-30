#!/usr/bin/env bash

# This script will return the latest release version of a GitHub repository.
# Example usage: ./source-git-repo-version.sh "https://github.com/rust-lang/rust.git"

fetch_html() {
    curl -fsSL "$1" 2>/dev/null
}

# Function to fetch and parse the latest release version
get_latest_release_version() {
    local url releases_url tags_url html_content main_content releases_content tags_content
    local first_match second_match exclude_words
    url="${1%/}"
    url="${url%.git}"
    releases_url="${url}/releases"
    tags_url="${url}/tags"

    first_match='href="[^"]*/tag/\K[^"]*'
    second_match='(?:[a-z-]+-)?\K([0-9]+(?:[._-][0-9]+)*(?:-[a-zA-Z0-9]+)?)'
    exclude_words='alpha|beta|dev|early|init|m[0-9]+|next|pending|pre|rc|tentative|^.$'

    # Fetch HTML content from both URLs
    main_content="$(fetch_html "$url")"
    releases_content="$(fetch_html "$releases_url")"
    tags_content="$(fetch_html "$tags_url")"
    html_content="$releases_content $main_content $tags_content"

    printf '%s\n' "$html_content" | grep -oP "$first_match" | grep -oP "$second_match" | grep -Eiv "$exclude_words" | sort -rV | head -n1 | sed -e 's/-$//' -e 's/^v//'
}

# Main script execution
[[ -z "$1" ]] && { echo "Usage: $0 <url>"; exit 1; }

version=$(get_latest_release_version "$1")
echo "$version"
