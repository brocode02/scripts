#!/bin/bash
set -e
git add .

read -rp "Commit message: " commit

if
  git commit -m "$commit" 2 &
  1 >/dev/null
then
  if git push -u origin main &>/dev/null; then

    echo
    echo "=================================="
    echo "✓ Successfully pushed to origin/main"
    echo "=================================="
  fi
fi
