#!/usr/bin/env bash
# Run once per clone: points git at the repo's hooks so the content guard runs before every push.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git config core.hooksPath .githooks
chmod +x .githooks/* scripts/*.sh
mkdir -p "${HOME}/.config/content-guard"
touch "${HOME}/.config/content-guard/extra.txt"
echo "Hooks enabled. Add private terms (one per line) to ${HOME}/.config/content-guard/extra.txt"
