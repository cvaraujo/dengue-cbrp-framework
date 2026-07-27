#!/usr/bin/env bash
# Copy Boost / LEMON archives from common locations into docker-build-deps/ for Docker COPY.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${ROOT}/docker-build-deps"
mkdir -p "$DEST"

search_dirs=()
for d in "${HOME}/Downloads" "${HOME}/Dropbox" "${HOME}"; do
  [[ -d "$d" ]] && search_dirs+=("$d")
done

found_boost=false
found_lemon=false

for dir in "${search_dirs[@]}"; do
  if [[ -f "${dir}/boost_1_90_0.tar.gz" ]]; then
    cp -f "${dir}/boost_1_90_0.tar.gz" "${DEST}/"
    echo "Copied boost_1_90_0.tar.gz from ${dir}"
    found_boost=true
    break
  fi
done

for dir in "${search_dirs[@]}"; do
  for name in lemon-1.3.1.zip lemon-1.3.1.tar.gz; do
    if [[ -f "${dir}/${name}" ]]; then
      cp -f "${dir}/${name}" "${DEST}/"
      echo "Copied ${name} from ${dir}"
      found_lemon=true
      break 2
    fi
  done
done

if ! "$found_boost"; then
  echo "Note: boost_1_90_0.tar.gz not found under Downloads/Dropbox/home — Docker will wget."
fi
if ! "$found_lemon"; then
  echo "Note: lemon-1.3.1.zip/.tar.gz not found — Docker will wget the official .zip."
fi
