"""Values shared by the converter modules."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

AUDIO_FORMATS = frozenset({'mp3', 'flac', 'wav', 'm4a', 'ogg', 'opus', 'wma', 'aac'})
SIDECAR_FORMATS = frozenset({'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'nfo'})
BITRATES = frozenset({'32k', '64k', '128k', '192k', '256k', '320k'})


@dataclass(frozen=True)
class RunConfig:
    input_path: str
    output_path: str
    music_format: str
    bitrate: str
    replace_mode: bool = False
    console_mode: str = 'plain'
    language: str = 'en'
    workers: int = 1


@dataclass(frozen=True)
class Fingerprint:
    size: int
    mtime_ns: int

    @classmethod
    def read(cls, path):
        info = Path(path).stat()
        return cls(info.st_size, info.st_mtime_ns)


@dataclass(frozen=True)
class ConversionJob:
    source: str
    relative_path: str
    extension: str
    destination: str
    temporary: str
    same_path: bool
    fingerprint: Fingerprint | None = None
    copy: bool = False
    sidecar: bool = False


@dataclass(frozen=True)
class EncodingResult:
    returncode: int | None
    error: str = ''
    cancelled: bool = False
    artwork_omitted: bool = False


@dataclass
class RunResult:
    file_count: dict[str, int] = field(default_factory=dict)
    converted_files: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)
    failed_files: list[str] = field(default_factory=list)
    correct_files: list[str] = field(default_factory=list)
    copied_files: list[str] = field(default_factory=list)
    interrupted: bool = False


@dataclass(frozen=True)
class ProgressEvent:
    kind: Literal['phase', 'scan', 'started', 'finished', 'workers', 'phase_finished']
    path: str = ''
    status: str = ''
    phase: str = ''
    total: int | None = None
    directories: int = 0
    active_paths: tuple[str, ...] = ()
    workers: int = 1
    queued: int = 0
