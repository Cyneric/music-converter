#!/usr/bin/env python3
"""Audio Format Converter.

Author: Christian Blank <christianblank91@gmail.com>
Created: Fri Jul 26 2024
Copyright: (c) 2024-2026 Christian Blank
"""

from pathlib import Path
import sys


def main(arguments=None):
    arguments = list(sys.argv[1:] if arguments is None else arguments)
    if sys.version_info < (3, 11):
        if '--headless' not in arguments:
            print('Python 3.11 or newer is required.', file=sys.stderr)
        return 1
    try:
        from music_converter.cli import main as run
    except ModuleNotFoundError as error:
        if not (error.name == 'music_converter' or error.name.startswith('music_converter.')):
            raise
        print('Cannot find the music_converter package. Download the complete project folder.', file=sys.stderr)
        return 1
    return run(arguments, installation_dir=Path(__file__).resolve().parent)


if __name__ == '__main__':
    sys.exit(main())
