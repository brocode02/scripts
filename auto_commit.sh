#!/bin/bash
set -e
git add .

read -rp "Commit message: " commit

if git commit -m "$commit"; then
  if git push -u origin main; then

    echo
    echo "=================================="
    echo "✓ Successfully pushed to origin/main"
    echo "=================================="
  fi
fi
