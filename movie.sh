#!/usr/bin/env bash
set -euo pipefail

URL="https://github.com/mesamirh/MovieBox-Tui/releases/download/v0.1.14/MovieBox_Linux_x64.tar.gz"
WORKDIR=$(mktemp -d)
INSTALL_DIR="/usr/local/bin"

curl -L -o "$WORKDIR/archive.tar.gz" "$URL"

tar -xzf "$WORKDIR/archive.tar.gz" -C "$WORKDIR"

BINARY=$(find "$WORKDIR" -maxdepth 2 -type f -executable ! -name "*.tar.gz" | head -n 1)

if [[ -z "$BINARY" ]]; then
    echo "No executable found in extracted archive." >&2
    exit 1
fi

chmod +x "$BINARY"
sudo mv "$BINARY" "$INSTALL_DIR/$(basename "$BINARY")"

rm -rf "$WORKDIR"

echo "Installed as $INSTALL_DIR/$(basename "$BINARY")"
