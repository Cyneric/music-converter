"""FFmpeg probing, encoding, and cancellation."""

import json
import os
import subprocess
from dataclasses import dataclass

from .models import EncodingResult


@dataclass(frozen=True)
class AudioInfo:
    format: str
    codec: str
    bitrate: int | None
    channels: int
    sample_rate: int

    def matches(self, target, bitrate):
        if self.format != target:
            return False
        if self.codec in {'flac', 'alac', 'wmalossless'} or self.codec.startswith('pcm_'):
            return True
        if self.bitrate is None:
            return False
        requested = int(bitrate[:-1]) * 1000
        # AAC and Vorbis report the measured average rather than the requested rate.
        tolerance = 1000 if self.codec == 'mp3' else requested * 0.05
        return abs(self.bitrate - requested) < tolerance


def probe(path):
    result = subprocess.run([
        'ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)
    ], capture_output=True, timeout=10)
    if result.returncode:
        raise OSError(result.stderr.decode('utf-8', errors='replace').strip() or 'ffprobe failed')
    data = json.loads(result.stdout)
    stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'audio'), None)
    if not stream or not stream.get('channels') or not int(stream.get('sample_rate', 0)):
        raise OSError('No readable audio stream')
    codec = stream.get('codec_name', '')
    container = set(data.get('format', {}).get('format_name', '').split(','))
    if codec == 'opus' and 'ogg' in container:
        format_name = 'opus'
    elif codec == 'vorbis' and 'ogg' in container:
        format_name = 'ogg'
    elif container & {'mov', 'mp4', 'm4a'} and codec in {'aac', 'alac'}:
        format_name = 'm4a'
    elif 'asf' in container and codec.startswith('wma'):
        format_name = 'wma'
    else:
        format_name = next((f for f in ('mp3', 'flac', 'wav', 'aac') if f in container), '')
    rate = stream.get('bit_rate')
    return AudioInfo(format_name, codec, int(rate) if rate and str(rate).isdigit() else None,
                     int(stream['channels']), int(stream['sample_rate']))


def _ffmpeg_args(job, bitrate, only_audio, force_input=False):
    args = ['ffmpeg', '-hide_banner', '-nostdin', '-y']
    if force_input:
        args += ['-f', 'mp3']
    args += ['-i', job.source]
    if only_audio:
        args += ['-map', '0:a']
    args += ['-b:a', bitrate, '-map_metadata', '0', '-id3v2_version', '3', job.temporary]
    return args


def _run_ffmpeg(args, stop):
    """Run one ffmpeg attempt to completion, honoring cancellation via stop."""
    options = {}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
    process = subprocess.Popen(
        args,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE, **options
    )
    cancelled = False
    try:
        while True:
            if stop.is_set() and process.poll() is None:
                cancelled = True
                process.terminate()
                try:
                    _, stderr = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    _, stderr = process.communicate()
                break
            try:
                _, stderr = process.communicate(timeout=0.1)
                break
            except subprocess.TimeoutExpired:
                continue
        return EncodingResult(
            process.returncode, (stderr or b"").decode("utf-8", errors="replace"), cancelled
        )
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()


def encode_job(job, bitrate, stop):
    if stop.is_set():
        return EncodingResult(None, cancelled=True)
    errors = []
    try:
        for forced in ([False, True] if job.extension == 'mp3' else [False]):
            for audio_only in (False, True):
                result = _run_ffmpeg(_ffmpeg_args(job, bitrate, audio_only, forced), stop)
                if result.cancelled or stop.is_set():
                    return EncodingResult(result.returncode, result.error, True)
                if result.returncode == 0:
                    return EncodingResult(0, artwork_omitted=audio_only)
                errors.append(result.error)
        return EncodingResult(result.returncode, '\n'.join(errors))
    except Exception as error:
        return EncodingResult(None, str(error), stop.is_set())


def validate(path, target, stop):
    info = probe(path)
    if info.format != target:
        raise OSError(f'Output format is {info.format or info.codec}, expected {target}')
    result = _run_ffmpeg([
        'ffmpeg', '-hide_banner', '-nostdin', '-v', 'error', '-xerror',
        '-i', str(path), '-map', '0:a:0', '-f', 'null', '-'
    ], stop)
    if result.cancelled or stop.is_set():
        return False
    if result.returncode:
        raise OSError('Output audio failed validation: ' + result.error.strip())
    return True
