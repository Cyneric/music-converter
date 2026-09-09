import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parent


def find_bash():
    if os.name == 'nt':
        # Use Git Bash rather than the Windows WSL launcher.
        git = shutil.which('git')
        candidate = pathlib.Path(git).parent.parent / 'bin' / 'bash.exe' if git else None
        return str(candidate) if candidate and candidate.is_file() else None
    return shutil.which('bash')


BASH = find_bash()


@unittest.skipUnless(BASH, 'Bash required')
class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.install = self.root / 'converter files'
        self.install.mkdir()
        self.cwd = self.root / 'music files'
        self.cwd.mkdir()
        self.launcher = self.install / 'convert.sh'
        shutil.copyfile(ROOT / 'convert.sh', self.launcher)
        self.env = os.environ.copy()
        self.env.pop('BASH_ENV', None)
        # Make this test's Python interpreter available to the launcher.
        self.env['PATH'] = str(pathlib.Path(sys.executable).parent) + os.pathsep + self.env['PATH']

    def run_launcher(self, args):
        return subprocess.run(
            [BASH, '--noprofile', '--norc', self.launcher.as_posix()] + args,
            cwd=self.cwd, env=self.env, capture_output=True,
            text=True, encoding='utf-8', errors='replace', timeout=30,
        )

    def test_arguments_working_directory_and_exit_codes(self):
        (self.install / 'convert.py').write_text(
            'import json, os, sys\n'
            'print(json.dumps({"args": sys.argv[1:], "cwd": os.getcwd()}))\n'
            'sys.exit(int(os.environ["LAUNCHER_TEST_EXIT"]))\n', encoding='utf-8',
        )
        cases = [
            [],
            ['relative input', '../output folder', 'mp3', '192k'],
            ['music with spaces', 'mp3', '192k', '--replace'],
            ['--headless', 'music $dollar & [brackets]', 'mp3', '192k',
             '--replace', '--language', 'en', '--workers', '2'],
        ]
        for args, exit_code in zip(cases, (0, 1, 2, 130)):
            with self.subTest(args=args, exit_code=exit_code):
                self.env['LAUNCHER_TEST_EXIT'] = str(exit_code)
                result = self.run_launcher(args)
                self.assertEqual(result.returncode, exit_code, result.stderr)
                self.assertEqual(result.stderr, '')
                data = json.loads(result.stdout)
                self.assertEqual(data['args'], args)
                self.assertEqual(pathlib.Path(data['cwd']).resolve(), self.cwd.resolve())

    def test_missing_companion_script(self):
        result = self.run_launcher(['--help'])
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertIn('Cannot find convert.py', result.stderr)

    def reject_interpreters(self, names):
        directory = self.root / 'unavailable interpreters'
        directory.mkdir()
        for name in names:
            shim = directory / name
            shim.write_text('#!/bin/sh\nexit 1\n', encoding='utf-8')
            shim.chmod(0o755)
        self.env['PATH'] = str(directory) + os.pathsep + self.env['PATH']

    def test_falls_back_to_python(self):
        (self.install / 'convert.py').write_text('print("started")\n', encoding='utf-8')
        self.reject_interpreters(['python3'])
        result = self.run_launcher([])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'started')

    def test_no_working_python(self):
        (self.install / 'convert.py').write_text('print("started")\n', encoding='utf-8')
        self.reject_interpreters(['python3', 'python'])
        result = self.run_launcher(['--headless'])
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertIn('Python 3.11 or newer is required', result.stderr)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
    def test_real_copy_replace_and_failure(self):
        shutil.copyfile(ROOT / 'convert.py', self.install / 'convert.py')
        shutil.copytree(ROOT / 'music_converter', self.install / 'music_converter', ignore=shutil.ignore_patterns('__pycache__'))
        subprocess.run([
            'ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
            'sine=frequency=440:duration=0.2', '-c:a', 'flac',
            str(self.cwd / 'track.flac'),
        ], check=True, capture_output=True)
        original = (self.cwd / 'track.flac').read_bytes()
        (self.cwd / 'cover.jpg').write_bytes(b'sidecar')
        result = self.run_launcher(['.', '../converted files', 'mp3', '192k', '--headless'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout + result.stderr, '')
        output = self.root / 'converted files'
        self.assertEqual((self.cwd / 'track.flac').read_bytes(), original)
        self.assertTrue((output / 'track.mp3').is_file())
        self.assertFalse((output / 'track.flac.mp3').exists())
        self.assertEqual((output / 'cover.jpg').read_bytes(), b'sidecar')
        self.assertTrue((self.install / '.convert-state.sqlite3').is_file())

        # A previous copy entry must not suppress an in-place FLAC replacement.
        (self.cwd / 'track.mp3').write_bytes(b'old target')
        result = self.run_launcher(['.', 'mp3', '192k', '--replace', '--headless', '--workers', '2'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout + result.stderr, '')
        self.assertFalse((self.cwd / 'track.flac').exists())
        probe = subprocess.check_output([
            'ffprobe', '-v', 'error', '-select_streams', 'a:0',
            '-show_entries', 'stream=codec_name,bit_rate', '-of', 'json',
            str(self.cwd / 'track.mp3'),
        ], text=True)
        self.assertEqual(json.loads(probe)['streams'][0], {'codec_name': 'mp3', 'bit_rate': '192000'})

        (self.cwd / 'broken.mp3').write_bytes(b'invalid audio')
        result = self.run_launcher(['.', 'mp3', '192k', '--replace', '--headless'])
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout + result.stderr, '')
        self.assertEqual((self.cwd / 'broken.mp3').read_bytes(), b'invalid audio')
        self.assertFalse(list(self.cwd.glob('.convert-*')))


if __name__ == '__main__':
    unittest.main()
