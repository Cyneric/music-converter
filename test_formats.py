import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from threading import Event
import unittest
from unittest.mock import patch

from music_converter import ffmpeg
from music_converter.history import History
from music_converter.models import AUDIO_FORMATS, ConversionJob, RunConfig
from music_converter.workflow import run


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class FormatTests(unittest.TestCase):
    def test_all_output_formats_and_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'input'
            source.mkdir()
            subprocess.run([
                'ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=duration=0.5',
                '-ac', '2', '-metadata', 'title=Sample title', '-c:a', 'flac', str(source / 'sample.flac'),
            ], check=True, capture_output=True)
            for target in sorted(AUDIO_FORMATS):
                with self.subTest(target=target):
                    destination = root / target
                    config = RunConfig(str(source), str(destination), target, '192k', console_mode='headless')
                    with History(root) as history:
                        result = run(config, history)
                    self.assertEqual(result.failed_files, [])
                    output = destination / ('sample.' + target)
                    self.assertEqual(ffmpeg.probe(output).format, target)
                    with History(root) as history:
                        self.assertEqual(len(run(config, history).skipped_files), 1)

    def test_mislabeled_audio_is_converted_through_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'input'
            source.mkdir()
            path = source / 'misnamed.mp3'
            subprocess.run([
                'ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=duration=0.2',
                '-c:a', 'flac', '-f', 'flac', str(path),
            ], check=True, capture_output=True)
            original = path.read_bytes()
            with History(root) as history:
                result = run(RunConfig(str(source), str(root / 'output'), 'mp3', '192k'), history)
            self.assertEqual(len(result.converted_files), 1)
            self.assertEqual(path.read_bytes(), original)

    def test_metadata_and_embedded_cover_survive_mp3_conversion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.flac'
            subprocess.run([
                'ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=duration=0.3',
                '-f', 'lavfi', '-i', 'color=c=blue:s=32x32:d=0.04', '-map', '0:a', '-map', '1:v',
                '-c:a', 'flac', '-c:v', 'mjpeg', '-frames:v', '1', '-disposition:v', 'attached_pic',
                '-metadata', 'title=Test title', '-metadata', 'artist=Test artist', str(source),
            ], check=True, capture_output=True)
            output = root / 'output.mp3'
            job = ConversionJob(str(source), source.name, 'flac', str(output), str(output), False)
            result = ffmpeg.encode_job(job, '192k', Event())
            self.assertEqual(result.returncode, 0, result.error)
            self.assertFalse(result.artwork_omitted)
            data = json.loads(subprocess.check_output([
                'ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(output),
            ]))
            self.assertEqual(data['format']['tags']['title'], 'Test title')
            self.assertEqual(data['format']['tags']['artist'], 'Test artist')
            self.assertTrue(any(stream.get('disposition', {}).get('attached_pic') for stream in data['streams']))


class ProbeTests(unittest.TestCase):
    def test_aliases_and_lossless_bitrates(self):
        examples = [('mov,mp4,m4a,3gp,3g2,mj2', 'aac', 'm4a'),
                    ('ogg', 'opus', 'opus'), ('ogg', 'vorbis', 'ogg'),
                    ('asf', 'wmav2', 'wma'), ('wav', 'pcm_s16le', 'wav'), ('flac', 'flac', 'flac')]
        for container, codec, target in examples:
            with self.subTest(codec=codec):
                data = {'format': {'format_name': container}, 'streams': [
                    {'codec_type': 'audio', 'codec_name': codec, 'channels': 2,
                     'sample_rate': '44100', 'bit_rate': '192000'}]}
                completed = subprocess.CompletedProcess([], 0, json.dumps(data).encode(), b'')
                with patch.object(ffmpeg.subprocess, 'run', return_value=completed):
                    info = ffmpeg.probe('sample')
                self.assertEqual(info.format, target)
                self.assertTrue(info.matches(target, '192k'))
                if codec in {'flac', 'pcm_s16le'}:
                    self.assertTrue(info.matches(target, '32k'))


if __name__ == '__main__':
    unittest.main()
