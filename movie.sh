#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/usr/local/bin"
REPO="mesamirh/MovieBox-Tui"
PACKAGE="MovieBox_Linux_x64.tar.gz"

WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

echo "Checking latest MovieBox release..."

LATEST_TAG=$(curl -fsSL \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$REPO/releases/latest" |
    grep '"tag_name":' |
    head -n 1 |
    sed -E 's/.*"tag_name": "([^"]+)".*/\1/')

if [[ -z "$LATEST_TAG" ]]; then
    echo "Could not determine latest release." >&2
    exit 1
fi

CURRENT_VERSION=$(moviebox-tui --version 2>/dev/null |
    grep -oE '[0-9]+\.[0-9]+\.[0-9]+' |
    head -n 1)

if [[ -z "$CURRENT_VERSION" ]]; then
    echo "Could not determine installed version." >&2
    exit 1
fi

CURRENT_TAG="v$CURRENT_VERSION"

echo "Current version: $CURRENT_TAG"
echo "Latest version:  $LATEST_TAG"

if [[ "$CURRENT_TAG" == "$LATEST_TAG" ]]; then
    echo "Already up to date."
    exit 0
fi

URL="https://github.com/$REPO/releases/download/$LATEST_TAG/$PACKAGE"

echo "Downloading $LATEST_TAG..."

if ! curl -fL -o "$WORKDIR/archive.tar.gz" "$URL"; then
    echo "Could not download $LATEST_TAG." >&2
    exit 1
fi

echo "Extracting..."

tar -xzf "$WORKDIR/archive.tar.gz" -C "$WORKDIR"

BINARY=$(find "$WORKDIR" -maxdepth 2 -type f -executable \
    ! -name "*.tar.gz" | head -n 1)

if [[ -z "$BINARY" ]]; then
    echo "No executable found in extracted archive." >&2
    exit 1
fi

chmod +x "$BINARY"

echo "Installing..."

sudo mv "$BINARY" "$INSTALL_DIR/$(basename "$BINARY")"

echo
echo "✓ MovieBox updated: $CURRENT_TAG → $LATEST_TAG"
