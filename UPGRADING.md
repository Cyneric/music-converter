# Upgrading from the published November 2024 version

This guide covers the unreleased Python update since
[`206689849685d773cc6ea83973a4f596a7928519`](https://github.com/Cyneric/music-converter/tree/206689849685d773cc6ea83973a4f596a7928519).
`convert.sh` is unchanged.

## What existing commands retain

These forms still work:

```bash
python convert.py INPUT OUTPUT mp3 192k
python convert.py INPUT mp3 192k --replace
python convert.py
```

The third form starts interactive setup. The same eight audio extensions and
six bitrate choices remain. One worker is still the default. Rich is optional
and is neither imported nor installed in plain/headless mode.

## Changes that can affect existing users

| Area | Previous behavior | What changes |
| --- | --- | --- |
| Language | English console | German by default. Add `--language en` to request English. |
| Console | Verbose per-file colored logging | Compact plain display; optional `--rich` dashboard or silent `--headless`. Text and summary labels differ; adjust output-parsing wrappers. English does not restore the old layout. |
| Failed files | Normal completion could exit `0` despite failures | Exit `2` when one or more files fail, including sidecar operations. Scheduled jobs must handle this. |
| Invalid command shape | Could fall back to interactive questions | Returns `1`; run without positionals for interactive setup. |
| Existing target in replace mode | Remove source, then rename; on Windows an existing target could make rename fail after source deletion | Publish successful output first, overwriting a same-basename target, then remove a different-format source. Review collisions before using `--replace`. |
| Output publication | Fixed `_temp` filename in replace mode; direct output in copy mode | Unique temporary file in the destination directory. Failed encoding/publication preserves the source and pre-existing target. POSIX copy publication requires hard-link support. |
| Processing order | One directory walk, filesystem order | Other extensions first, target extension second, sidecars last. Multiple sources mapping to one output do not all get converted; an already reserved destination is skipped. |
| Resume | Matching source-path/format/bitrate entry skipped | Same JSON shape. In replace mode, remaining non-target sources are retried despite old entries; completed replacements are recorded under the destination path. |
| Interruptions | No coordinated cancellation/checkpoint handling | During processing, Ctrl+C stops workers, cleans temporary outputs, saves completed progress, and returns `130`. This is not a guarantee against power loss. |
| Installation | Included Python FFmpeg wget fallback | Uses available platform package managers after a prompt. No Python wget fallback; headless mode never installs dependencies. |
| Python imports | Helper functions and five-item `process_files` tuple | Several helper signatures changed; `process_files` returns a seven-field `RunResult`. Code importing this script needs adaptation. The CLI is the documented entry point. |

The format/bitrate flags do not guarantee identical encoded bytes across FFmpeg
versions. New audio-only retries may omit broken embedded artwork. Sidecar
images are preserved in place or copied separately; no automatic extraction of
embedded artwork is provided.

## Update an existing installation

1. Let the active run finish or stop it cleanly. Save a copy of the old scripts
   and their adjacent `.convert.lock` before updating. Back up audio separately
   if using replace mode; a script rollback cannot restore overwritten audio.
2. Replace the script in its existing directory so the existing lock remains
   beside it. If moving installations, transfer that lock deliberately while
   preserving the source paths it refers to. Do not delete it as an upgrade step.
3. Check Python, `ffmpeg`, and `ffprobe`. The old Python 3.6 statement is not
   reliable. This update has been tested on Windows with Python 3.13.15; other
   versions and operating systems still need testing before release.
4. Adjust automation for exit codes `0` (completed without failed files), `1`
   (arguments/dependencies/fatal error), `2` (failed files), and `130` (handled
   processing interruption). Use `--headless` for silent jobs. Explicit `--help`
   still prints help.
5. Try copied sample inputs using a separate script directory and its own lock,
   with output outside the sample input. Start with one worker; then try two.
   Check decoded audio, tags, artwork, output count, and logs before replacing
   files in a full library. There is no dry-run flag in this update.

Example with explicit language and worker count:

```bash
python convert.py INPUT OUTPUT mp3 192k --language en --workers 1
```

## Resume limitations retained from the published code

`.convert.lock` lives beside the script in both modes, despite the old README
claiming it lived in the input/output directory. It is a JSON history cache,
not an inter-process lock. Its entries do not include the output directory or a
source fingerprint. A different destination or changed source contents can
therefore be skipped because of earlier progress. For a separate conversion
destination, use a separate script directory and lock instead of resetting a
production lock.

Copy mode skips already-correct audio without copying it to the destination.
It also skips existing audio destinations; sidecars can be copied over existing
sidecars. A zero exit code means no recorded failures, not that every source
file is present in the output. Verify completeness.

Do not run Python and Bash, or multiple Python processes, against a shared
library/lock concurrently. Parallelize within one Python process using
`--workers` instead.

## Returning to the old script

Keep the original script and a backup of its lock together. Both versions can
read the JSON format, but they record replacement paths and decide when to retry
differently. Restoring an older lock can cause files processed since that backup
to be processed again. Check the library before running again. Restoring a script
or lock does not restore deleted or overwritten audio.
