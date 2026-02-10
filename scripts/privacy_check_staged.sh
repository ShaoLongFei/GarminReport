#!/usr/bin/env bash
set -euo pipefail

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not inside a git repository."
  exit 2
fi

STAGED_FILES=()
while IFS= read -r -d '' file; do
  STAGED_FILES+=("$file")
done < <(git diff --cached --name-only --diff-filter=ACMR -z)

if [ "${#STAGED_FILES[@]}" -eq 0 ]; then
  echo "No staged files to scan."
  exit 0
fi

PATTERNS=(
  "^/[U]sers/"
  "\"birthDate\"[[:space:]]*:"
  "\"userId\"[[:space:]]*:"
  "\"userProfilePK\"[[:space:]]*:"
  "\"full_name\"[[:space:]]*:"
  "GARMIN_PASSWORD[[:space:]]*=[[:space:]]*.+"
)

TMP_OUTPUT="$(mktemp)"
trap 'rm -f "$TMP_OUTPUT"' EXIT

FOUND=0
for file in "${STAGED_FILES[@]}"; do
  if [ "$file" = ".env.example" ] || [ "$file" = "scripts/privacy_check_staged.sh" ]; then
    continue
  fi

  if [ ! -f "$file" ]; then
    continue
  fi

  for pattern in "${PATTERNS[@]}"; do
    if grep -nH -I -E "$pattern" "$file" >>"$TMP_OUTPUT"; then
      FOUND=1
    fi
  done
done

if [ "$FOUND" -eq 1 ]; then
  echo "Privacy scan failed. Sensitive markers found in staged files:"
  cat "$TMP_OUTPUT"
  exit 1
fi

echo "Privacy scan passed. No sensitive markers found in staged files."
