import pathlib
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

import convert


class EncodingTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
    def test_flac_named_mp3(self):
        with tempfile.TemporaryDirectory() as directory:
            source = pathlib.Path(directory) / 'source.mp3'
            output = pathlib.Path(directory) / 'output.mp3'
            subprocess.run([
                'ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                'sine=frequency=440:duration=0.2', '-c:a', 'flac',
                '-f', 'flac', str(source),
            ], check=True)
            original = source.read_bytes()
            job = convert.ConversionJob(str(source), source.name, 'mp3',
                                        str(output), str(output), False)
            result = convert.encode_job(job, '192k', threading.Event())
            self.assertEqual(result.returncode, 0, result.error)
            probe = subprocess.check_output([
                'ffprobe', '-v', 'error', '-select_streams', 'a:0',
                '-show_entries', 'stream=codec_name,bit_rate',
                '-of', 'default=nw=1', str(output),
            ], text=True)
            self.assertIn('codec_name=mp3', probe)
            self.assertIn('bit_rate=192000', probe)
            self.assertEqual(source.read_bytes(), original)

    def test_forced_mp3_fallback(self):
        job = convert.ConversionJob('source.mp3', 'source.mp3', 'mp3',
                                    'out.mp3', 'out.mp3', False)
        failure = convert.EncodingResult(1, 'probe failed', False)
        success = convert.EncodingResult(0, '', False)
        with patch.object(convert, '_run_ffmpeg', side_effect=[failure, failure, success]) as run:
            result = convert.encode_job(job, '192k', threading.Event())
        self.assertEqual(result.returncode, 0)
        self.assertNotIn('-f', run.call_args_list[0].args[0])
        forced = run.call_args_list[2].args[0]
        self.assertEqual(forced[forced.index('-f') + 1], 'mp3')


if __name__ == '__main__':
    unittest.main()
