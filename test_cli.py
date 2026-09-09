import contextlib
import importlib.util
import io
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from music_converter import cli
from music_converter.console import NullReporter, Translator, create_reporter

ROOT = Path(__file__).resolve().parent


class CLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'input'
        self.source.mkdir()
        self.output = self.root / 'output'

    def arguments(self, *options):
        return [str(self.source), str(self.output), 'mp3', '192k', *options]

    def test_parser_keeps_legacy_forms_and_defaults(self):
        copy = cli.parse_arguments(self.arguments())
        self.assertEqual((copy.language, copy.workers, copy.replace_mode), ('en', 1, False))
        replace = cli.parse_arguments(['--replace', 'source folder', 'mp3', '--language', 'de', '192k', '--workers=2'])
        self.assertEqual((replace.output_path, replace.language, replace.workers), ('source folder', 'de', 2))
        with patch.object(cli, 'get_user_input', return_value=('in', 'out', 'mp3', '192k', False)):
            self.assertEqual(cli.parse_arguments([]).input_path, 'in')

    def test_invalid_arguments_are_silent_in_headless_mode(self):
        for args in (['--headless'], ['--headless', '--rich'], self.arguments('--headless', '--workers=0')):
            with self.subTest(args=args), contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(cli.main(args, installation_dir=self.root), 1)
                self.assertEqual(out.getvalue() + err.getvalue(), '')

    def test_help_in_both_languages_and_headless(self):
        for language, word in [('en', 'usage:'), ('de', 'Verwendung:')]:
            with self.subTest(language=language), contextlib.redirect_stdout(io.StringIO()) as out:
                with self.assertRaises(SystemExit) as result:
                    cli.main(['--headless', '--language', language, '--help'], installation_dir=self.root)
                self.assertEqual(result.exception.code, 0)
                self.assertIn(word, out.getvalue())
        self.assertFalse((self.root / '.convert-state.sqlite3').exists())

    def test_missing_ffprobe_stops_before_processing(self):
        with patch.object(cli.shutil, 'which', side_effect=lambda name: None if name == 'ffprobe' else '/ffmpeg'), \
                contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(cli.main(self.arguments('--headless'), installation_dir=self.root), 1)
            self.assertEqual(out.getvalue() + err.getvalue(), '')
        self.assertFalse((self.root / '.convert-state.sqlite3').exists())
        self.assertIn('ffprobe', next((self.root / 'logs').iterdir()).read_text(encoding='utf-8'))

    def test_missing_ffmpeg_and_old_python(self):
        with patch.object(cli.shutil, 'which', return_value=None), \
                contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(cli.main(self.arguments('--headless'), installation_dir=self.root), 1)
            self.assertEqual(out.getvalue() + err.getvalue(), '')
        with patch.object(sys, 'version_info', (3, 10)), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(cli.main(self.arguments(), installation_dir=self.root), 1)
            self.assertIn('3.11', err.getvalue())

    def test_root_logger_handlers_are_preserved(self):
        root_logger = logging.getLogger()
        handler = logging.StreamHandler(io.StringIO())
        root_logger.addHandler(handler)
        self.addCleanup(root_logger.removeHandler, handler)
        before = list(root_logger.handlers)
        with patch.object(cli, 'check_dependencies', return_value=True):
            self.assertEqual(cli.main(self.arguments('--headless'), installation_dir=self.root), 0)
        self.assertEqual(root_logger.handlers, before)
        self.assertEqual(logging.getLogger('music_converter').handlers, [])

    def test_imports_do_not_load_rich_or_create_state(self):
        code = '''import os, sys
sys.path.insert(0, sys.argv[1])
import convert
from music_converter import cli, console, models, workflow, ffmpeg, files, history
assert not any(name == 'rich' or name.startswith('rich.') for name in sys.modules)
assert os.listdir('.') == []
'''
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-c', code, str(ROOT)], cwd=directory, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_package_has_useful_error(self):
        script = self.root / 'convert.py'
        shutil.copyfile(ROOT / 'convert.py', script)
        result = subprocess.run([sys.executable, '-I', str(script), '--help'], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('complete project folder', result.stderr)

    def test_rich_missing_does_not_silently_change_mode(self):
        with patch('music_converter.console.import_rich', return_value=False), \
                patch.object(sys.stdin, 'isatty', return_value=False), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(self.arguments('--rich'), installation_dir=self.root), 1)

    @unittest.skipUnless(importlib.util.find_spec('rich'), 'Rich required')
    def test_rich_dashboard_and_summary_render(self):
        from music_converter.models import RunResult
        reporter = create_reporter('rich', Translator('en'))
        output = io.StringIO()
        reporter.console.file = output
        reporter.worker_progress(('track.mp3',), 2, 1)
        reporter.start_phase('Converting', 1)
        reporter.file_finished('converted', 'track.mp3')
        reporter.console.print(reporter._build_dashboard())
        reporter.show_summary(RunResult(converted_files=['track.mp3']), 'sample.log')
        self.assertIn('Conversion complete', output.getvalue())


if __name__ == '__main__':
    unittest.main()
