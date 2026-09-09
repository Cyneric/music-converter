# Changelog

## Unreleased

Compared with published commit
[`2066898`](https://github.com/Cyneric/music-converter/commit/206689849685d773cc6ea83973a4f596a7928519)
(November 6, 2024). These changes apply to Python unless stated otherwise.
Read [UPGRADING.md](UPGRADING.md) for behavior changes affecting existing users.

### Added

- Optional Rich dashboard, silent headless mode, and German/English interfaces.
- `--workers N` with bounded queuing and one worker by default.
- Worker activity, phase progress, runtime, throughput, and separate sidecar counts.
- Coordinated processing cancellation, temporary-file cleanup, and progress saving.
- Atomic JSON history updates and best-effort recovery of truncated history,
  preserving a corrupt-file backup.
- Two encoding regression tests: FLAC content named `.mp3` and forced-MP3 fallback.

### Changed

- Default console is compact and German; legacy positional commands remain valid.
- Failed-file completion returns `2`; argument/dependency/fatal failures return `1`;
  handled processing interruption returns `130`.
- Files with other extensions are converted before files with the target extension.
  Sidecars are copied last.
- Files with other extensions no longer need a separate probe before conversion.
  Output folders inside the input folder are excluded from scanning.
- Each conversion uses a unique temporary file. Replace mode saves the output before deleting a
  different-format source and can overwrite an existing same-basename target.
- Copy mode leaves existing audio destinations alone and uses hard links on POSIX.
- Replace mode retries remaining sources with other extensions, even with an old resume entry.
- Added audio-only retries for artwork failures and forced MP3 decoding as a fallback
  after automatic content detection fails. Audio-only success can omit embedded art.
- Removed Python's wget installation fallback. Rich installation is offered
  only when requested; headless runs do not prompt for or install dependencies.
- Changed internal Python helper signatures and the `process_files` return value.

### Documentation

- Added upgrade instructions and a description of the differences between Python and Bash.
- Corrected the lock file location. Python must be installed before running the script.
- Noted that the Python 3.6 requirement needs correcting before release.
- Explained when copy mode skips files and when embedded artwork may be omitted.

`convert.sh` is unchanged.
