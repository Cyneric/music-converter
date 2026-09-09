"""Prepare and publish output while protecting source files."""

from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import signal
import stat
import tempfile
from threading import current_thread, main_thread

from .models import EncodingResult, Fingerprint


@contextmanager
def defer_interrupt(raise_after=True):
    if current_thread() is not main_thread():
        yield
        return
    previous = signal.getsignal(signal.SIGINT)
    received = []
    signal.signal(signal.SIGINT, lambda *_: received.append(True))
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous)
    if received and raise_after:
        raise KeyboardInterrupt


def temporary(destination):
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.convert-', suffix=path.suffix, dir=path.parent)
    os.close(fd)
    return name


def copy_job(job, stop):
    try:
        with open(job.source, 'rb') as source, open(job.temporary, 'wb') as output:
            while chunk := source.read(1024 * 1024):
                if stop.is_set():
                    return EncodingResult(None, cancelled=True)
                output.write(chunk)
        shutil.copystat(job.source, job.temporary)
        return EncodingResult(0, cancelled=stop.is_set())
    except OSError as error:
        return EncodingResult(None, str(error), stop.is_set())


def check_source(job):
    if Fingerprint.read(job.source) != job.fingerprint:
        raise OSError('Source changed during processing; output was not saved')


def publish(job, replace_mode):
    if replace_mode:
        os.replace(job.temporary, job.destination)
    elif os.name == 'nt':
        os.rename(job.temporary, job.destination)
    else:
        # Hard linking fails atomically if the destination already exists.
        os.link(job.temporary, job.destination)
        os.unlink(job.temporary)


def remove_source(job):
    if not job.same_path:
        os.remove(job.source)


def cleanup(path):
    path = Path(path)
    try:
        path.unlink(missing_ok=True)
    except PermissionError:
        # A copied read-only source can leave a read-only temporary file on Windows.
        if os.name != 'nt':
            raise
        path.chmod(path.stat().st_mode | stat.S_IWRITE)
        path.unlink()
