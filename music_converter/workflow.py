"""Coordinate scanning, workers, file completion, and history."""

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import logging
import os
from pathlib import Path
from threading import Event

from . import ffmpeg, files
from .history import HistoryError, normalized
from .models import (AUDIO_FORMATS, SIDECAR_FORMATS, ConversionJob, EncodingResult,
                     Fingerprint, ProgressEvent, RunResult)

logger = logging.getLogger('music_converter')


def run(config, history, *, encoder=ffmpeg, emit=None, stop=None, file_ops=files):
    """Run one conversion using an open history store and an optional event sink."""
    return _Workflow(config, history, encoder, emit or (lambda event: None),
                     stop or Event(), file_ops).run()


class _Workflow:
    def __init__(self, config, history, encoder, emit, stop, file_ops):
        if config.workers < 1:
            raise ValueError('workers must be positive')
        self.config, self.history, self.encoder = config, history, encoder
        self.emit, self.stop, self.files = emit, stop, file_ops
        self.result = RunResult()
        self.pending = {}
        self.reserved = set()
        self.generated = set()
        self.replaced_targets = set()
        self.counts = {'target': 0, 'sidecar': 0}
        self.mode = 'replace' if config.replace_mode else 'copy'
        self.input_root = normalized(config.input_path)
        self.output_root = normalized(config.output_path)
        if not config.replace_mode and self.input_root == self.output_root:
            raise ValueError('Copy mode requires different input and output directories')

    def record(self, status, source, extension):
        names = {'converted': 'converted_files', 'correct': 'correct_files',
                 'copied': 'copied_files', 'skipped': 'skipped_files', 'failed': 'failed_files'}
        getattr(self.result, names[status]).append(source)
        self.result.file_count[extension] = self.result.file_count.get(extension, 0) + 1
        logger.info('%s: %s', status, source)
        self.emit(ProgressEvent('finished', path=os.path.relpath(source, self.config.input_path), status=status))

    def fail(self, source, extension, error):
        lines = str(error).strip().splitlines()
        logger.error('Failed to process %s: %s', source, lines[-1] if lines else type(error).__name__)
        if len(lines) > 1:
            logger.info('Full conversion error for %s:\n%s', source, error)
        self.record('failed', source, extension)

    def workers(self):
        active = tuple(job.relative_path for future, job in self.pending.items() if future.running())
        queued = sum(not f.running() and not f.done() for f in self.pending)
        self.emit(ProgressEvent('workers', active_paths=active, workers=self.config.workers, queued=queued))

    def scan(self, phase):
        def scan_error(error):
            self.fail(error.filename or self.config.input_path, 'directory', error)
        for count, (root, dirs, names) in enumerate(os.walk(self.config.input_path, onerror=scan_error), 1):
            dirs[:] = sorted(d for d in dirs if self.config.replace_mode or normalized(os.path.join(root, d)) != self.output_root)
            if count % 50 == 0:
                self.emit(ProgressEvent('scan', directories=count))
                self.collect()
            for name in sorted(names):
                if self.stop.is_set():
                    return
                if name.startswith('.convert-'):
                    continue
                source = os.path.join(root, name)
                extension = Path(name).suffix[1:].lower()
                if phase == 'other':
                    if extension == self.config.music_format:
                        self.counts['target'] += 1
                    elif extension in SIDECAR_FORMATS:
                        self.counts['sidecar'] += 1
                    if extension in AUDIO_FORMATS and extension != self.config.music_format:
                        yield source, extension
                elif phase == 'target' and extension == self.config.music_format:
                    key = normalized(source)
                    if key not in self.generated and key not in self.replaced_targets:
                        yield source, extension
                elif phase == 'sidecar' and extension in SIDECAR_FORMATS:
                    yield source, extension

    def prepare(self, job):
        if self.stop.is_set():
            return EncodingResult(None, cancelled=True)
        try:
            result = (self.files.copy_job(job, self.stop) if job.copy
                      else self.encoder.encode_job(job, self.config.bitrate, self.stop))
            if self.stop.is_set():
                return EncodingResult(None, cancelled=True)
            if result.returncode != 0 or result.cancelled:
                return result
            if not job.sidecar and not self.encoder.validate(job.temporary, self.config.music_format, self.stop):
                return EncodingResult(None, cancelled=True)
            return result
        except Exception as error:
            return EncodingResult(None, str(error), self.stop.is_set())

    def clean(self, path):
        try:
            self.files.cleanup(path)
        except OSError as error:
            logger.error('Could not remove temporary file %s: %s', path, error)

    def finish(self, future, job):
        try:
            if future.cancelled():
                return
            result = future.result()
            if result.cancelled:
                return
            if result.returncode != 0:
                raise OSError(result.error or 'Conversion failed')
            self.files.check_source(job)
            if not Path(job.temporary).is_file():
                raise OSError('No output file was produced')
            if not job.sidecar and Path(job.temporary).stat().st_size == 0:
                raise OSError('Output audio is empty')
            self.files.publish(job, self.config.replace_mode)
            self.generated.add(normalized(job.destination))
            if self.config.replace_mode:
                self.files.remove_source(job)
            status = 'copied' if job.copy else 'converted'
            self.history.record(job, self.mode, 'sidecar' if job.sidecar else self.config.music_format,
                                '' if job.sidecar else self.config.bitrate, status)
            if result.artwork_omitted:
                logger.warning('Converted without embedded artwork: %s', job.source)
            logger.info('%s: %s -> %s', status.capitalize(), job.source, job.destination)
            self.record(status, job.source, job.extension)
        except HistoryError:
            # Stop the run rather than continuing without durable progress.
            raise
        except Exception as error:
            self.fail(job.source, job.extension, error)
        finally:
            self.clean(job.temporary)

    def collect(self, block=False):
        if self.pending and block:
            wait(tuple(self.pending), timeout=0.1, return_when=FIRST_COMPLETED)
        for future in list(self.pending):
            if future.done():
                with files.defer_interrupt():
                    job = self.pending.pop(future)
                    self.finish(future, job)
        self.workers()

    def consider(self, source, extension, phase, pool):
        sidecar = phase == 'sidecar'
        relative = os.path.relpath(source, self.config.input_path)
        destination = (source if self.config.replace_mode else os.path.join(self.config.output_path, relative))
        if not sidecar:
            destination = str(Path(destination).with_suffix('.' + self.config.music_format))
        key = normalized(destination)
        same_path = normalized(source) == key
        settings = ('sidecar', '') if sidecar else (self.config.music_format, self.config.bitrate)
        self.emit(ProgressEvent('started', path=relative))
        try:
            if key in self.reserved:
                raise FileExistsError(f'Conflict: another source uses {destination}')
            if self.history.matches(source, destination, self.mode, *settings):
                self.reserved.add(key)
                self.record('skipped', source, extension)
                return
            if not self.config.replace_mode and os.path.lexists(destination):
                raise FileExistsError(f'Conflict: existing output cannot be verified: {destination}')
            if os.path.islink(destination):
                raise OSError(f'Refusing to replace a symbolic link: {destination}')
            with files.defer_interrupt():
                if self.history.import_legacy(source, destination, self.mode, *settings):
                    self.reserved.add(key)
                    self.record('skipped', source, extension)
                    return
            fingerprint = Fingerprint.read(source)
            correct = False
            if not sidecar and extension == self.config.music_format:
                try:
                    correct = self.encoder.probe(source).matches(*settings)
                except (OSError, ValueError):
                    # Encoding still has content detection and decoder fallbacks.
                    pass
            if correct and self.config.replace_mode and same_path:
                if not self.encoder.validate(source, self.config.music_format, self.stop):
                    return
                job = ConversionJob(source, relative, extension, destination, '', True, fingerprint)
                with files.defer_interrupt():
                    self.files.check_source(job)
                    self.history.record(job, self.mode, *settings, 'correct')
                    self.reserved.add(key)
                    self.record('correct', source, extension)
                return
            if self.config.replace_mode and not same_path and os.path.lexists(destination):
                self.replaced_targets.add(key)
            # Reserve before allocating work so two sources cannot race to one output.
            with files.defer_interrupt():
                temporary = self.files.temporary(destination)
                job = ConversionJob(source, relative, extension, destination, temporary, same_path,
                                    fingerprint, copy=correct or sidecar, sidecar=sidecar)
                self.reserved.add(key)
                try:
                    self.pending[pool.submit(self.prepare, job)] = job
                except Exception:
                    self.clean(temporary)
                    raise
            self.workers()
        except HistoryError:
            raise
        except Exception as error:
            self.fail(source, extension, error)

    def run(self):
        pool = ThreadPoolExecutor(max_workers=self.config.workers)
        phase_open = False
        fatal = False
        try:
            self.workers()
            phases = ['other', 'target'] + ([] if self.config.replace_mode else ['sidecar'])
            for phase in phases:
                if self.stop.is_set():
                    break
                total = self.counts.get(phase)
                if phase == 'target':
                    total = max(0, total - len(self.replaced_targets))
                self.emit(ProgressEvent('phase', phase=phase, total=total))
                logger.info('Starting phase: %s; workers=%d', phase, self.config.workers)
                phase_open = True
                for source, extension in self.scan(phase):
                    while len(self.pending) >= 2 * self.config.workers and not self.stop.is_set():
                        self.collect(block=True)
                    if self.stop.is_set():
                        break
                    self.collect()
                    self.consider(source, extension, phase, pool)
                while self.pending and not self.stop.is_set():
                    self.collect(block=True)
                with files.defer_interrupt():
                    self.history.flush_imports()
                self.emit(ProgressEvent('phase_finished'))
                phase_open = False
        except KeyboardInterrupt:
            self.stop.set()
            logger.warning('Interrupted; stopping workers and saving completed progress')
        except BaseException:
            fatal = True
            raise
        finally:
            with files.defer_interrupt(raise_after=False):
                self.result.interrupted = self.stop.is_set()
                self.stop.set()
                for future in self.pending:
                    future.cancel()
                pool.shutdown(wait=True)
                # After a fatal error, clean prepared outputs without publishing more.
                try:
                    for future, job in list(self.pending.items()):
                        if not fatal:
                            self.finish(future, job)
                    if not fatal:
                        self.history.flush_imports()
                finally:
                    for job in self.pending.values():
                        self.clean(job.temporary)
                    self.pending.clear()
                    self.workers()
                    if phase_open:
                        self.emit(ProgressEvent('phase_finished'))
        return self.result
