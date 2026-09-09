import json
import logging
import os
from pathlib import Path
import sqlite3
import tempfile
from threading import Event
import unittest
from unittest.mock import patch

from music_converter import files
from music_converter.ffmpeg import AudioInfo
from music_converter.history import History, HistoryError
from music_converter.models import EncodingResult, RunConfig
from music_converter.workflow import run


class TestEncoder:
    """A controlled encoder for failures that are hard to reproduce with FFmpeg."""

    def __init__(self):
        self.calls = []
        self.error = None
        self.validation_error = None
        self.after_encode = None
        self.artwork_omitted = False

    def probe(self, path):
        format_name = Path(path).suffix[1:]
        return AudioInfo(format_name, format_name, 192000, 2, 44100)

    def encode_job(self, job, bitrate, stop):
        self.calls.append(job.source)
        Path(job.temporary).write_bytes(b'encoded:' + Path(job.source).read_bytes())
        if self.after_encode:
            self.after_encode(job, stop)
        return EncodingResult(1 if self.error else 0, self.error or '', stop.is_set(), self.artwork_omitted)

    def validate(self, path, target, stop):
        if self.validation_error:
            raise OSError(self.validation_error)
        return not stop.is_set()


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'input'
        self.output = self.root / 'output'
        self.state = self.root / 'state'
        for directory in (self.source, self.output, self.state):
            directory.mkdir()
        self.encoder = TestEncoder()
        handler = logging.NullHandler()
        logger = logging.getLogger('music_converter')
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)

    def track(self, name='track.flac', content=b'original'):
        path = self.source / name
        path.write_bytes(content)
        return path

    def convert(self, *, replace=False, output=None, bitrate='192k', workers=2, **kwargs):
        config = RunConfig(str(self.source), str(self.source if replace else output or self.output),
                           'mp3', bitrate, replace_mode=replace, workers=workers)
        with History(self.state) as history:
            return run(config, history, encoder=self.encoder, **kwargs)

    def test_correct_audio_and_sidecar_copied_then_resumed(self):
        source = self.track('already.mp3')
        self.track('cover.jpg', b'cover')
        result = self.convert()
        self.assertEqual(len(result.copied_files), 2)
        self.assertEqual(self.encoder.calls, [])
        self.assertEqual((self.output / source.name).read_bytes(), source.read_bytes())
        self.assertEqual(len(self.convert().skipped_files), 2)

    def test_history_checks_both_paths_source_settings_and_output(self):
        source = self.track()
        self.assertEqual(len(self.convert().converted_files), 1)
        self.assertEqual(len(self.convert().skipped_files), 1)
        other = self.root / 'other output'
        self.assertEqual(len(self.convert(output=other).converted_files), 1)
        destination = self.output / 'track.mp3'
        destination.unlink()
        self.assertEqual(len(self.convert().converted_files), 1)
        original_output = destination.read_bytes()
        source.write_bytes(b'changed source with different length')
        self.assertEqual(len(self.convert().failed_files), 1)
        self.assertEqual(destination.read_bytes(), original_output)
        destination.unlink()
        self.assertEqual(len(self.convert().converted_files), 1)
        self.assertEqual(len(self.convert(bitrate='128k').failed_files), 1)
        destination.write_bytes(b'changed output')
        self.assertEqual(len(self.convert().failed_files), 1)
        self.assertEqual(destination.read_bytes(), b'changed output')

    def test_unrecorded_outputs_and_sidecars_are_conflicts(self):
        self.track('track.mp3')
        self.track('cover.jpg')
        (self.output / 'track.mp3').write_bytes(b'existing audio')
        (self.output / 'cover.jpg').write_bytes(b'existing cover')
        result = self.convert()
        self.assertEqual(len(result.failed_files), 2)
        self.assertEqual((self.output / 'track.mp3').read_bytes(), b'existing audio')
        self.assertEqual((self.output / 'cover.jpg').read_bytes(), b'existing cover')

    def test_replace_records_result_and_rechecks_changed_files(self):
        source = self.track()
        self.assertEqual(len(self.convert(replace=True).converted_files), 1)
        self.assertFalse(source.exists())
        self.assertEqual(len(self.convert(replace=True).skipped_files), 1)
        target = self.source / 'track.mp3'
        target.write_bytes(b'changed but still correct audio')
        self.assertEqual(len(self.convert(replace=True).correct_files), 1)
        self.track(content=b'new lossless source')
        self.assertEqual(len(self.convert(replace=True).converted_files), 1)
        self.assertEqual(target.read_bytes(), b'encoded:new lossless source')

    def test_legacy_history_is_read_only_and_rechecked_once(self):
        source = self.track('track.mp3')
        legacy = self.state / '.convert.lock'
        content = json.dumps({str(source): {'format': 'mp3', 'bitrate': '192k'}}).encode()
        legacy.write_bytes(content)
        self.assertEqual(len(self.convert(replace=True).correct_files), 1)
        with patch.object(self.encoder, 'probe', side_effect=AssertionError('already verified')):
            self.assertEqual(len(self.convert(replace=True).skipped_files), 1)
        self.assertEqual(legacy.read_bytes(), content)
        self.assertEqual(len(self.convert().copied_files), 1)

    def test_corrupt_legacy_history_is_preserved(self):
        self.track('track.mp3')
        legacy = self.state / '.convert.lock'
        legacy.write_bytes(b'{"unfinished":')
        with self.assertLogs('music_converter', level='WARNING'):
            result = self.convert(replace=True)
        self.assertEqual(len(result.correct_files), 1)
        self.assertEqual(legacy.read_bytes(), b'{"unfinished":')

    def test_failed_encoding_or_validation_preserves_both_files(self):
        source = self.track()
        target = self.track('track.mp3', b'existing')
        for stage in ('error', 'validation_error'):
            with self.subTest(stage=stage):
                setattr(self.encoder, stage, 'injected failure')
                result = self.convert(replace=True)
                self.assertEqual(len(result.failed_files), 1)
                self.assertEqual(source.read_bytes(), b'original')
                self.assertEqual(target.read_bytes(), b'existing')
                self.assertFalse(list(self.source.glob('.convert-*')))
                setattr(self.encoder, stage, None)

    def test_publication_and_source_removal_failures(self):
        source = self.track()
        target = self.track('track.mp3', b'existing')
        with patch.object(files, 'publish', side_effect=OSError('permission denied')):
            result = self.convert(replace=True)
        self.assertEqual(len(result.failed_files), 1)
        self.assertTrue(source.exists())
        self.assertEqual(target.read_bytes(), b'existing')
        with patch.object(files, 'remove_source', side_effect=OSError('permission denied')):
            result = self.convert(replace=True)
        self.assertEqual(len(result.failed_files), 1)
        self.assertTrue(source.exists())
        self.assertEqual(target.read_bytes(), b'encoded:original')
        with History(self.state) as history:
            self.assertEqual(history.connection.execute('SELECT count(*) FROM records').fetchone()[0], 0)

    def test_source_changed_during_work_is_not_published(self):
        source = self.track()
        target = self.track('track.mp3', b'existing')
        self.encoder.after_encode = lambda job, stop: source.write_bytes(b'changed while encoding')
        result = self.convert(replace=True)
        self.assertEqual(len(result.failed_files), 1)
        self.assertEqual(target.read_bytes(), b'existing')
        self.assertEqual(source.read_bytes(), b'changed while encoding')

    def test_readonly_copy_failure_cleans_temporary_output(self):
        source = self.track('track.mp3')
        source.chmod(0o444)
        self.addCleanup(source.chmod, 0o600)
        self.encoder.validation_error = 'invalid audio'
        self.assertEqual(len(self.convert().failed_files), 1)
        self.assertTrue(source.exists())
        self.assertFalse(list(self.output.iterdir()))

    def test_same_destination_workers_report_conflict(self):
        self.track('track.flac', b'first')
        other = self.track('track.wav', b'second')
        result = self.convert(replace=True)
        self.assertEqual(len(result.converted_files), 1)
        self.assertEqual(len(result.failed_files), 1)
        self.assertTrue(other.exists())
        self.assertEqual(len(self.encoder.calls), 1)

    def test_destination_created_during_work_is_not_overwritten(self):
        self.track()
        destination = self.output / 'track.mp3'
        self.encoder.after_encode = lambda job, stop: destination.write_bytes(b'created elsewhere')
        self.assertEqual(len(self.convert().failed_files), 1)
        self.assertEqual(destination.read_bytes(), b'created elsewhere')

    def test_nested_output_is_not_scanned(self):
        self.track()
        output = self.source / 'nested output'
        output.mkdir()
        (output / 'unrelated.flac').write_bytes(b'leave alone')
        result = self.convert(output=output)
        self.assertEqual(len(result.converted_files), 1)
        self.assertFalse((output / 'nested output').exists())

    def test_keyboard_interrupt_stops_active_workers(self):
        self.track()
        active = Event()

        def delay(job, stop):
            active.set()
            stop.wait(5)

        self.encoder.after_encode = delay

        def interrupt(event):
            if event.kind == 'workers' and event.active_paths and active.is_set():
                raise KeyboardInterrupt

        result = self.convert(emit=interrupt)
        self.assertTrue(result.interrupted)
        self.assertFalse((self.output / 'track.mp3').exists())
        self.assertTrue((self.source / 'track.flac').exists())
        self.assertFalse(list(self.output.glob('.convert-*')))

    def test_interrupted_migration_keeps_completed_history(self):
        for index in range(4):
            self.track(f'{index}.mp3')
        stop = Event()

        def interrupt(event):
            if event.kind == 'finished':
                stop.set()

        result = self.convert(replace=True, emit=interrupt, stop=stop)
        self.assertTrue(result.interrupted)
        self.assertEqual(len(result.correct_files), 1)
        result = self.convert(replace=True)
        self.assertEqual(len(result.skipped_files), 1)
        self.assertEqual(len(result.correct_files), 3)

    def test_history_write_failure_stops_run(self):
        self.track()
        with patch.object(History, 'record', side_effect=HistoryError('disk full')):
            with self.assertRaisesRegex(HistoryError, 'disk full'):
                self.convert()
        self.assertFalse(list(self.output.glob('.convert-*')))

    def test_artwork_fallback_is_reported(self):
        self.track()
        self.encoder.artwork_omitted = True
        with self.assertLogs('music_converter', level='WARNING') as messages:
            self.assertEqual(len(self.convert().converted_files), 1)
        self.assertIn('without embedded artwork', '\n'.join(messages.output))


class HistoryTests(unittest.TestCase):
    def test_exclusive_store_and_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            with History(directory):
                with self.assertRaisesRegex(HistoryError, 'Another converter'):
                    with History(directory):
                        pass
            with History(directory) as store:
                self.assertEqual(store.connection.execute('PRAGMA user_version').fetchone()[0], 1)

    def test_corrupt_or_newer_database_fails_without_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / '.convert-state.sqlite3'
            database.write_bytes(b'corrupt database')
            with self.assertRaises(HistoryError):
                with History(directory):
                    pass
            self.assertEqual(database.read_bytes(), b'corrupt database')
            database.unlink()
            with sqlite3.connect(database) as connection:
                connection.execute('PRAGMA user_version=999')
            connection.close()
            with self.assertRaisesRegex(HistoryError, 'Unsupported history version'):
                with History(directory):
                    pass


if __name__ == '__main__':
    unittest.main()
