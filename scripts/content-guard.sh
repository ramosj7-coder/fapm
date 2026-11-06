#!/usr/bin/env bash
# Content guard: fails if tracked files contain employer-specific or PHI-shaped content.
# Used by the pre-push hook (.githooks/pre-push) and by CI (.github/workflows/content-guard.yml).
#
# Sources of blocked terms:
#   1. .github/content-guard/patterns.txt          public, generic regex patterns
#   2. ~/.config/content-guard/extra.txt           private literal terms, local only
#   3. $CONTENT_GUARD_EXTRA                        private literal terms, newline-separated (CI secret)
#
# Private terms match whole words only (so "Terri" does not match "territory").
# A line containing "guard:allow" is skipped.

set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

patterns_file=".github/content-guard/patterns.txt"
local_extra="${HOME}/.config/content-guard/extra.txt"

# Files that legitimately describe the blocked terms.
exclude_re='^(CLAUDE\.md|scripts/content-guard\.sh|\.github/content-guard/patterns\.txt)$'

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

grep -vE '^\s*(#|$)' "$patterns_file" > "$tmp/regex" || true

: > "$tmp/literal"
[[ -f "$local_extra" ]] && grep -vE '^\s*(#|$)' "$local_extra" >> "$tmp/literal" || true
[[ -n "${CONTENT_GUARD_EXTRA:-}" ]] && printf '%s\n' "$CONTENT_GUARD_EXTRA" | grep -vE '^\s*$' >> "$tmp/literal" || true

git ls-files -z | while IFS= read -r -d '' f; do
  [[ "$f" =~ $exclude_re ]] && continue
  [[ -f "$f" ]] || continue
  grep -Iq . "$f" 2>/dev/null || continue   # skip binary and empty files
  printf '%s\0' "$f"
done > "$tmp/files"

hits=0
report() {
  # $1 = grep mode flag (-E or -F), $2 = pattern file, $3 = label
  [[ -s "$2" ]] || return 0
  local out
  out="$(xargs -0 -r grep -n -i "$1" -f "$2" -- < "$tmp/files" | grep -v 'guard:allow' || true)"
  if [[ -n "$out" ]]; then
    echo "content-guard: blocked ${3} found:"
    if [[ "$3" == "private terms" ]]; then
      # Never echo private terms into CI logs; print locations only.
      echo "$out" | cut -d: -f1,2 | sed 's/^/  /'
    else
      echo "$out" | sed 's/^/  /'
    fi
    hits=1
  fi
}

report -E "$tmp/regex" "patterns"
report -Fw "$tmp/literal" "private terms"

if [[ "$hits" -ne 0 ]]; then
  echo
  echo "content-guard: FAILED. Remove the content above before pushing."
  exit 1
fi

echo "content-guard: clean ($(tr -cd '\0' < "$tmp/files" | wc -c) files checked)"
