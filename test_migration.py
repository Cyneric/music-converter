from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from music_converter import history as history_module
from music_converter.history import History, HistoryError
from music_converter.models import RunConfig
from music_converter.workflow import run
from test_launcher import BASH
from test_workflow import TestEncoder

ROOT = Path(__file__).resolve().parent


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'music files'
        self.state = self.root / 'installation'
        self.source.mkdir()
        self.state.mkdir()
        self.legacy = self.state / '.convert.lock'
        self.encoder = TestEncoder()
        self.config = RunConfig(str(self.source), str(self.source), 'mp3', '192k', True)
        handler = logging.NullHandler()
        logger = logging.getLogger('music_converter')
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)

    def track(self, name='track.mp3'):
        path = self.source / name
        path.write_bytes(b'previously processed audio')
        return path

    def entry(self, **changes):
        entry = dict(format='mp3', bitrate='192k', status='converted',
                     timestamp=(datetime.now(timezone.utc) + timedelta(seconds=5)).isoformat())
        entry.update(changes)
        return entry

    def write_legacy(self, entries):
        self.legacy.write_text(json.dumps(entries), encoding='utf-8')

    def convert(self, **kwargs):
        with History(self.state) as store:
            return run(self.config, store, encoder=self.encoder, **kwargs)

    def records(self):
        connection = sqlite3.connect(self.state / '.convert-state.sqlite3')
        try:
            return connection.execute('SELECT status FROM records').fetchall()
        finally:
            connection.close()

    def test_imports_python_and_bash_entries_without_audio_work(self):
        entries = {}
        for index, status in enumerate(['converted', 'correct_format', None, 'converted']):
            track = self.track(f'{index}.mp3')
            entry = self.entry(status=status)
            if status is None:
                del entry['status']
                entry['timestamp'] = (datetime.now() + timedelta(seconds=5)).isoformat()
            if index == 1:
                entry['timestamp'] = entry['timestamp'].replace('+00:00', 'Z')
            if index == 3:
                entry['timestamp'] = (datetime.now(timezone(timedelta(hours=5, minutes=30)))
                                      + timedelta(seconds=5)).isoformat()
            entries[str(track)] = entry
        self.write_legacy(entries)
        original = self.legacy.read_bytes()
        with patch.object(self.encoder, 'probe', side_effect=AssertionError('must not probe')), \
                patch.object(self.encoder, 'validate', side_effect=AssertionError('must not decode')), \
                patch.object(self.encoder, 'encode_job', side_effect=AssertionError('must not encode')), \
                self.assertLogs('music_converter', level='INFO') as logs:
            result = self.convert()
            self.assertEqual(len(result.skipped_files), 4)
            self.assertEqual(result.failed_files, [])
            self.assertEqual(len(self.convert().skipped_files), 4)
        self.assertIn('Imported 4 legacy records', '\n'.join(logs.output))
        self.assertEqual(self.records(), [('legacy_imported',)] * 4)
        self.assertEqual(self.legacy.read_bytes(), original)

    def test_ineligible_entries_use_normal_validation(self):
        changes = [dict(format='flac'), dict(bitrate='128k'), dict(status='failed'),
                   dict(timestamp='invalid'), dict(timestamp=None), dict(timestamp='2026-01-01'),
                   dict(timestamp='2000-01-01T00:00:00+00:00')]
        entries = {str(self.track(f'{index}.mp3')): self.entry(**change)
                   for index, change in enumerate(changes)}
        entries[str(self.track('missing-timestamp.mp3'))] = {'format': 'mp3', 'bitrate': '192k'}
        entries[str(self.track('invalid-entry.mp3'))] = []
        self.write_legacy(entries)
        self.assertEqual(len(self.convert().correct_files), len(entries))

    def test_empty_files_and_relative_or_ambiguous_paths_are_not_imported(self):
        empty = self.track('empty.mp3')
        empty.write_bytes(b'')
        relative = self.track('relative.mp3')
        duplicate = self.track('duplicate.mp3')
        exact = self.track('exact.mp3')
        entries = {str(empty): self.entry(), relative.name: self.entry(),
                   str(duplicate): self.entry(),
                   str(duplicate.parent) + os.sep + '.' + os.sep + duplicate.name: self.entry()}
        text = json.dumps(entries)
        # Preserve a repeated raw JSON key, which a normal dict would discard.
        pair = json.dumps(str(exact)) + ':' + json.dumps(self.entry())
        self.legacy.write_text(text[:-1] + ',' + pair + ',' + pair + '}', encoding='utf-8')
        self.assertEqual(len(self.convert().correct_files), 4)

    def test_symbolic_link_is_not_imported(self):
        target = self.root / 'audio.mp3'
        target.write_bytes(b'audio')
        link = self.source / 'link.mp3'
        try:
            link.symlink_to(target)
        except OSError as error:
            self.skipTest(f'Symbolic links unavailable: {error}')
        self.write_legacy({str(link): self.entry()})
        self.assertEqual(len(self.convert().failed_files), 1)
        self.assertEqual(self.records(), [])
        self.assertTrue(link.is_symlink())

    def test_changed_source_during_import_fails(self):
        track = self.track()
        self.write_legacy({str(track): self.entry()})
        original = history_module._regular_fingerprint
        calls = 0

        def change(path):
            nonlocal calls
            calls += 1
            if calls == 2:
                track.write_bytes(b'changed while importing')
            return original(path)

        with patch.object(history_module, '_regular_fingerprint', side_effect=change):
            result = self.convert()
        self.assertEqual(len(result.failed_files), 1)
        self.assertEqual(self.records(), [])
        self.assertEqual(track.read_bytes(), b'changed while importing')

    def test_existing_sqlite_record_prevents_legacy_reimport(self):
        track = self.track()
        self.write_legacy({str(track): self.entry()})
        self.assertEqual(len(self.convert().skipped_files), 1)
        track.write_bytes(b'changed after migration')
        self.assertEqual(len(self.convert().correct_files), 1)
        self.assertEqual(self.records(), [('correct',)])
        self.assertEqual(len(self.convert().skipped_files), 1)

    def test_sqlite_record_for_other_settings_also_prevents_import(self):
        track = self.track()
        self.assertEqual(len(self.convert().correct_files), 1)
        self.config = RunConfig(str(self.source), str(self.source), 'mp3', '128k', True)
        self.write_legacy({str(track): self.entry(bitrate='128k')})
        result = self.convert()
        self.assertEqual(len(result.converted_files), 1)
        self.assertEqual(self.encoder.calls, [str(track)])

    def test_copy_mode_still_creates_missing_outputs_and_preserves_conflicts(self):
        track = self.track()
        self.write_legacy({str(track): self.entry()})
        output = self.root / 'output'
        output.mkdir()
        self.config = RunConfig(str(self.source), str(output), 'mp3', '192k')
        self.assertEqual(len(self.convert().copied_files), 1)
        destination = output / track.name
        destination.write_bytes(b'unverified output')
        self.assertEqual(len(self.convert().failed_files), 1)
        self.assertEqual(destination.read_bytes(), b'unverified output')

    def test_legacy_entry_for_another_extension_does_not_suppress_conversion(self):
        track = self.track('track.flac')
        self.write_legacy({str(track): self.entry()})
        self.assertEqual(len(self.convert().converted_files), 1)
        self.assertEqual(self.encoder.calls, [str(track)])

    def test_phase_boundary_flushes_small_import_batch(self):
        track = self.track()
        self.write_legacy({str(track): self.entry()})
        finished = False

        def check(event):
            nonlocal finished
            if event.kind == 'finished':
                finished = True
            if event.kind == 'phase_finished' and finished:
                self.assertEqual(self.records(), [('legacy_imported',)])

        self.convert(emit=check)

    def test_batches_and_interrupt_flush_completed_imports(self):
        self.write_legacy({str(self.track(f'{i:04}.mp3')): self.entry() for i in range(252)})
        finished = 0

        def interrupt(event):
            nonlocal finished
            if event.kind == 'finished':
                finished += 1
                if finished == 249:
                    self.assertEqual(len(self.records()), 0)
                if finished == 251:
                    self.assertEqual(len(self.records()), 250)
                    raise KeyboardInterrupt

        result = self.convert(emit=interrupt)
        self.assertTrue(result.interrupted)
        self.assertEqual(len(self.records()), 251)
        self.assertEqual(len(self.convert().skipped_files), 252)
        self.assertEqual(len(self.records()), 252)

    def test_uncommitted_import_can_be_retried_after_abrupt_close(self):
        track = self.track()
        self.write_legacy({str(track): self.entry()})
        store = History(self.state).__enter__()
        try:
            self.assertTrue(store.import_legacy(str(track), str(track), 'replace', 'mp3', '192k'))
            self.assertEqual(self.records(), [])
        finally:
            store.close()
        self.assertEqual(len(self.convert().skipped_files), 1)

    def test_database_import_failure_is_fatal_and_retryable(self):
        track = self.track()
        self.write_legacy({str(track): self.entry()})
        with History(self.state) as store:
            store.connection.execute('PRAGMA query_only=ON')
            with self.assertRaisesRegex(HistoryError, 'Cannot save legacy history'):
                run(self.config, store, encoder=self.encoder)
            store.connection.execute('PRAGMA query_only=OFF')
        self.assertEqual(self.records(), [])
        self.assertEqual(len(self.convert().skipped_files), 1)

    def test_failed_batch_rolls_back_all_imports(self):
        self.write_legacy({str(self.track(f'{i:04}.mp3')): self.entry() for i in range(250)})
        with History(self.state) as store:
            store.connection.execute('''CREATE TRIGGER fail_import BEFORE INSERT ON records
                WHEN NEW.destination LIKE '%0100.mp3'
                BEGIN SELECT RAISE(ABORT, 'injected failure'); END''')
            with self.assertRaisesRegex(HistoryError, 'injected failure'):
                run(self.config, store, encoder=self.encoder)
            self.assertEqual(self.records(), [])
            store.connection.execute('DROP TRIGGER fail_import')
        self.assertEqual(len(self.convert().skipped_files), 250)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
    def test_migration_through_both_entry_commands(self):
        commands = [[sys.executable, str(self.state / 'convert.py')]]
        if BASH:
            commands.append([BASH, '--noprofile', '--norc', (self.state / 'convert.sh').as_posix()])
        shutil.copytree(ROOT / 'music_converter', self.state / 'music_converter')
        for name in ('convert.py', 'convert.sh'):
            shutil.copyfile(ROOT / name, self.state / name)
        track = self.source / 'generated audio.mp3'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=duration=0.1',
                        '-b:a', '192k', str(track)], check=True, capture_output=True)
        env = os.environ.copy()
        env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + env['PATH']
        for command in commands:
            for language in ('en', 'de'):
                with self.subTest(command=command[0], language=language):
                    database = self.state / '.convert-state.sqlite3'
                    database.unlink(missing_ok=True)
                    self.write_legacy({str(track): self.entry()})
                    result = subprocess.run(command + [str(self.source), 'mp3', '192k', '--replace',
                                                       '--headless', '--language', language],
                                            env=env, capture_output=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout + result.stderr, b'')
                    self.assertEqual(self.records(), [('legacy_imported',)])


if __name__ == '__main__':
    unittest.main()
