"""Verified conversion history and exclusive access to a state store."""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sqlite3
import stat
import time

from .models import Fingerprint

logger = logging.getLogger('music_converter')
SCHEMA_VERSION = 1
IMPORT_BATCH_SIZE = 250


class HistoryError(RuntimeError):
    pass


def normalized(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


class _LegacyObject(dict):
    """Retain duplicate keys so ambiguous JSON records cannot be trusted."""

    def __init__(self, pairs):
        super().__init__()
        self.duplicates = set()
        for key, value in pairs:
            if key in self:
                self.duplicates.add(key)
            self[key] = value


def _legacy_key(path):
    # Do not resolve every path in a large library just to build the index.
    return os.path.normcase(os.path.normpath(path))


def _regular_fingerprint(path):
    info = os.lstat(path)
    if not stat.S_ISREG(info.st_mode):
        return None
    return Fingerprint(info.st_size, info.st_mtime_ns)


def _completion_ns(value):
    if not isinstance(value, str) or ('T' not in value and ' ' not in value):
        raise ValueError('expected a completion date and time')
    # astimezone interprets older timezone-free Python timestamps as local time.
    stamp = datetime.fromisoformat(value).astimezone(timezone.utc)
    elapsed = stamp - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return ((elapsed.days * 86400 + elapsed.seconds) * 1000000 + elapsed.microseconds) * 1000


class History:
    """Commit completed work immediately and legacy imports in small batches."""

    def __init__(self, directory):
        self.directory = Path(directory)
        self.database = self.directory / '.convert-state.sqlite3'
        self.connection = None
        self._lock = None
        self._legacy = {}
        self._pending_imports = {}
        self._imports_failed = False
        self.imported_count = 0

    def __enter__(self):
        try:
            self._acquire()
            self.connection = sqlite3.connect(self.database, timeout=0)
            version = self.connection.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, SCHEMA_VERSION):
                raise HistoryError(f'Unsupported history version: {version}')
            if self.connection.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise HistoryError('History database failed its integrity check')
            if version == 0:
                if self.connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone():
                    raise HistoryError('Unrecognized history database; refusing to overwrite it')
                with self.connection:
                    self.connection.execute('''CREATE TABLE records (
                        mode TEXT NOT NULL, source TEXT NOT NULL, destination TEXT NOT NULL,
                        format TEXT NOT NULL, bitrate TEXT NOT NULL,
                        source_size INTEGER NOT NULL, source_mtime INTEGER NOT NULL,
                        output_size INTEGER NOT NULL, output_mtime INTEGER NOT NULL,
                        status TEXT NOT NULL, completed INTEGER NOT NULL,
                        PRIMARY KEY (mode, source, destination, format, bitrate))''')
                    self.connection.execute('CREATE INDEX replacement ON records(mode, destination, format, bitrate)')
                    self.connection.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
            self.connection.execute('PRAGMA synchronous=FULL')
            self._inspect_legacy()
            return self
        except Exception as error:
            self.close()
            if isinstance(error, HistoryError):
                raise
            raise HistoryError(f'Cannot open conversion history: {error}') from error

    def _acquire(self):
        self._lock = open(self.directory / '.convert-state.runlock', 'a+b')
        self._lock.seek(0, os.SEEK_END)
        if self._lock.tell() == 0:
            self._lock.write(b'0')
            self._lock.flush()
        self._lock.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self._lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise HistoryError('Another converter is using this history directory') from error

    def _inspect_legacy(self):
        legacy = self.directory / '.convert.lock'
        if not legacy.exists():
            return
        try:
            with legacy.open(encoding='utf-8') as stream:
                entries = json.load(stream, object_pairs_hook=_LegacyObject)
            if not isinstance(entries, dict):
                raise ValueError('expected a JSON object')
            for path, entry in entries.items():
                if not Path(path).is_absolute():
                    continue
                key = _legacy_key(path)
                if key in self._legacy or path in entries.duplicates:
                    self._legacy[key] = None
                else:
                    self._legacy[key] = entry
            logger.info('Legacy history contains %s entries; eligible in-place records will be imported', len(entries))
        except (OSError, ValueError) as error:
            self._legacy.clear()
            logger.warning('Cannot read legacy history; files will be rechecked: %s', error)

    def import_legacy(self, source, destination, mode, music_format, bitrate):
        """Trust eligible old in-place records and establish a new fingerprint."""
        if mode != 'replace' or Path(source).suffix[1:].lower() != music_format:
            return False
        entry = self._legacy.get(_legacy_key(os.path.abspath(source)))
        if not isinstance(entry, dict) or getattr(entry, 'duplicates', None):
            return False
        if (entry.get('format') != music_format or entry.get('bitrate') != bitrate
                or ('status' in entry and entry['status'] not in ('converted', 'correct_format'))):
            return False
        key = normalized(destination)
        if normalized(source) != key or key in self._pending_imports:
            return False
        try:
            # Any previous replacement record takes precedence, even when stale
            # or recorded with different settings.
            if self.connection.execute(
                "SELECT 1 FROM records WHERE mode='replace' AND destination=? LIMIT 1", (key,)
            ).fetchone():
                return False
        except sqlite3.Error as error:
            raise HistoryError(f'Cannot read conversion history: {error}') from error
        before = _regular_fingerprint(source)
        if before is None or before.size == 0:
            return False
        try:
            completed = _completion_ns(entry.get('timestamp'))
        except (ValueError, TypeError, OverflowError, OSError):
            return False
        if before.mtime_ns > completed:
            return False
        if _regular_fingerprint(source) != before:
            raise OSError(f'Source changed during legacy import: {source}')
        self._pending_imports[key] = (
            'replace', key, key, music_format, bitrate, before.size, before.mtime_ns,
            before.size, before.mtime_ns, 'legacy_imported', time.time_ns())
        if len(self._pending_imports) >= IMPORT_BATCH_SIZE:
            self.flush_imports()
        return True

    def flush_imports(self):
        if not self._pending_imports or self._imports_failed:
            return
        try:
            with self.connection:
                self.connection.executemany(
                    'INSERT INTO records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    self._pending_imports.values())
        except sqlite3.Error as error:
            self._imports_failed = True
            raise HistoryError(f'Cannot save legacy history: {error}') from error
        self.imported_count += len(self._pending_imports)
        self._pending_imports.clear()

    def matches(self, source, destination, mode, music_format, bitrate):
        source, destination = normalized(source), normalized(destination)
        if mode == 'replace' and source != destination:
            return False
        try:
            source_fp = Fingerprint.read(source)
            output_fp = Fingerprint.read(destination)
        except OSError:
            return False
        try:
            if mode == 'replace':
                row = self.connection.execute('''SELECT output_size, output_mtime FROM records
                    WHERE mode=? AND destination=? AND format=? AND bitrate=?
                    ORDER BY completed DESC LIMIT 1''', (mode, destination, music_format, bitrate)).fetchone()
                return row is not None and tuple(row) == (output_fp.size, output_fp.mtime_ns)
            row = self.connection.execute('''SELECT source_size, source_mtime, output_size, output_mtime
                FROM records WHERE mode=? AND source=? AND destination=? AND format=? AND bitrate=?''',
                (mode, source, destination, music_format, bitrate)).fetchone()
            return row is not None and tuple(row) == (
                source_fp.size, source_fp.mtime_ns, output_fp.size, output_fp.mtime_ns)
        except sqlite3.Error as error:
            raise HistoryError(f'Cannot read conversion history: {error}') from error

    def record(self, job, mode, music_format, bitrate, status):
        self.flush_imports()
        try:
            output = Fingerprint.read(job.destination)
            with self.connection:
                self.connection.execute('''INSERT OR REPLACE INTO records VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
                    mode, normalized(job.source), normalized(job.destination), music_format, bitrate,
                    job.fingerprint.size, job.fingerprint.mtime_ns, output.size, output.mtime_ns,
                    status, time.time_ns()))
        except (sqlite3.Error, OSError) as error:
            raise HistoryError(f'Cannot save conversion history: {error}') from error

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        if self._lock is not None:
            # Closing releases the operating system lock, including on failure.
            self._lock.close()
            self._lock = None

    def __exit__(self, exc_type, *_):
        try:
            if exc_type is None or issubclass(exc_type, KeyboardInterrupt):
                self.flush_imports()
            if self.imported_count:
                logger.info('Imported %d legacy records without audio checks', self.imported_count)
        finally:
            self.close()
