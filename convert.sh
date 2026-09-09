#!/bin/bash
# Audio Format Converter
# Copyright (c) 2024-2026 Christian Blank

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || exit 1

if [[ ! -f "$script_dir/convert.py" ]]; then
    printf '%s\n' "Cannot find convert.py next to convert.sh. Keep both files together." >&2
    exit 1
fi

for python in python3 python; do
    if command -v "$python" >/dev/null 2>&1 &&
        "$python" -c 'import sys; sys.exit(sys.version_info < (3, 11))' >/dev/null 2>&1; then
        exec "$python" "$script_dir/convert.py" "$@"
    fi
done

printf '%s\n' "Python 3.11 or newer is required. Install it and make python3 or python available on PATH." >&2
exit 1
