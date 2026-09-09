"""Verified conversion history and exclusive access to a state store."""

import json
import logging
import os
from pathlib import Path
import sqlite3
import time

from .models import Fingerprint

logger = logging.getLogger('music_converter')
SCHEMA_VERSION = 1


class HistoryError(RuntimeError):
    pass


def normalized(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


class History:
    """Commit completed files individually so a stopped run can resume."""

    def __init__(self, directory):
        self.directory = Path(directory)
        self.database = self.directory / '.convert-state.sqlite3'
        self.connection = None
        self._lock = None

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
                entries = json.load(stream)
            if not isinstance(entries, dict):
                raise ValueError('expected a JSON object')
            logger.info('Legacy history contains %s entries; unverified files will be rechecked', len(entries))
        except (OSError, ValueError) as error:
            # No old record can prove a source/output match, even if valid.
            # Verify files directly and leave damaged legacy data untouched.
            logger.warning('Cannot read legacy history; files will be rechecked: %s', error)

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

    def __exit__(self, *_):
        self.close()
