#!/usr/bin/env python3

"""
Author: Christian Blank <christianblank91@gmail.com>
Created: Fri Jul 26 2024
Modified: Wed Nov 06 2024
Copyright: (c) 2024

Audio Format Converter

This script converts audio files to different formats while preserving metadata.
It also handles copying of associated image and NFO files.

Features:
- Convert audio files to various formats (mp3, flac, wav, m4a, ogg, opus, wma, aac)
- Support for multiple bitrates (32k, 64k, 128k, 192k, 256k, 320k)
- Preserve metadata during conversion
- Handle image files (jpg, jpeg, png, gif, bmp, webp)
- Copy NFO files
- Two operation modes: copy to new directory or replace in place
- Detailed logging of all operations
"""

import argparse
import importlib
import json
import logging
import os
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from collections import deque, namedtuple
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from contextlib import contextmanager
from datetime import datetime
from threading import Event, current_thread, main_thread

AUDIO_FORMATS = {"mp3", "flac", "wav", "m4a", "ogg", "opus", "wma", "aac"}


TRANSLATIONS = {
    "de": {
        "rich_missing_prompt": "Rich ist nicht installiert. Jetzt installieren? [J/n] ",
        "rich_declined": "Rich wurde nicht installiert.",
        "rich_installing": "Rich wird fuer diesen Python-Interpreter installiert ...",
        "rich_install_failed": "Rich konnte nicht installiert werden.",
        "rich_import_failed": "Rich wurde installiert, konnte aber nicht geladen werden.",
        "rich_noninteractive": "Rich fehlt und kann ohne interaktive Konsole nicht installiert werden.",
        "app_title": "Audio Format Converter",
        "source": "Quelle",
        "target": "Ziel",
        "format": "Format",
        "mode": "Modus",
        "mode_replace": "Ersetzen",
        "mode_copy": "Kopieren",
        "files_total": "{total} Dateien",
        "directories_checked": "{count} Ordner geprueft",
        "status_line": "konvertiert {converted} | passend {correct} | uebersprungen {skipped} | kopiert {copied} | Fehler {failed}",
        "status_compact": "K {converted}  P {correct}  U {skipped}  C {copied}  F {failed}",
        "warning": "WARNUNG",
        "error": "FEHLER",
        "partial_summary": "Teilzusammenfassung",
        "completed": "Konvertierung abgeschlossen",
        "finished_after": "{heading} nach {elapsed:.1f} Sekunden",
        "converted": "Konvertiert",
        "already_correct": "Bereits passend",
        "skipped": "Uebersprungen",
        "copied": "Kopiert",
        "failed": "Fehlgeschlagen",
        "runtime": "Laufzeit",
        "conversion_rate": "Konvertierungen/min",
        "workers_help": "parallele Konvertierungen (positive Ganzzahl; Standard: 1)",
        "workers_invalid": "--workers muss eine positive Ganzzahl sein.",
        "worker_status": "Aktiv: {active}/{workers} | Wartend: {queued}",
        "live_summary": "Gesamtuebersicht",
        "current_operation": "Aktueller Vorgang",
        "activity": "Letzte Aktivitaeten",
        "waiting": "Warte auf die erste Datei ...",
        "files": "Dateien",
        "log_file": "Logdatei",
        "success_converted": "Konvertiert",
        "phase_non_target": "Andere Formate konvertieren",
        "phase_target": "Vorhandene {format}-Dateien pruefen",
        "phase_sidecar": "Begleitdateien kopieren",
        "interactive_title": "Audio Format Converter - Interaktiver Modus",
        "input_prompt": "Eingabeverzeichnis: ",
        "invalid_input": "Das Eingabeverzeichnis ist ungueltig.",
        "mode_prompt": "Modus waehlen:\n1. In neues Verzeichnis kopieren\n2. Originaldateien ersetzen\nAuswahl (1/2): ",
        "invalid_mode": "Bitte 1 oder 2 eingeben.",
        "output_prompt": "Ausgabeverzeichnis: ",
        "invalid_output": "Das Ausgabeverzeichnis konnte nicht erstellt werden.",
        "format_prompt": "Zielformat {formats}: ",
        "invalid_format": "Ungueltiges Audioformat.",
        "bitrate_prompt": "Bitrate {bitrates}: ",
        "invalid_bitrate": "Ungueltige Bitrate.",
        "ffmpeg_missing_prompt": "ffmpeg ist nicht installiert. Jetzt installieren? [j/N] ",
        "ffmpeg_required": "ffmpeg wird benoetigt.",
        "cli_description": "Audiodateien konvertieren und Metadaten erhalten.",
        "cli_values_help": "Eingabe [Ausgabe] Format Bitrate",
        "replace_help": "Originaldateien durch konvertierte Dateien ersetzen",
        "rich_help": "Rich-Live-Oberflaeche aktivieren",
        "headless_help": "ohne Konsolenausgabe ausfuehren; nur Log und Lock-Datei",
        "language_help": "Sprache der Konsolenoberflaeche",
        "usage_error": "Ungueltige Argumente: {message}",
        "replace_usage": "Replace-Modus erwartet: Eingabe Format Bitrate",
        "copy_usage": "Copy-Modus erwartet: Eingabe Ausgabe Format Bitrate",
        "headless_requires_args": "Headless-Modus benoetigt vollstaendige Positionsargumente.",
        "mode_conflict": "--rich und --headless koennen nicht gemeinsam verwendet werden.",
        "language_invalid": "Die Sprache muss de oder en sein.",
        "help_help": "diese Hilfe anzeigen und beenden",
        "fatal_error": "Fataler Fehler: {message}",
        "python_required": "Python 3.6 oder neuer wird benoetigt.",
    },
    "en": {
        "rich_missing_prompt": "Rich is not installed. Install it now? [Y/n] ",
        "rich_declined": "Rich was not installed.",
        "rich_installing": "Installing Rich for this Python interpreter ...",
        "rich_install_failed": "Rich could not be installed.",
        "rich_import_failed": "Rich was installed but could not be imported.",
        "rich_noninteractive": "Rich is missing and cannot be installed without an interactive console.",
        "app_title": "Audio Format Converter",
        "source": "Source",
        "target": "Target",
        "format": "Format",
        "mode": "Mode",
        "mode_replace": "Replace",
        "mode_copy": "Copy",
        "files_total": "{total} files",
        "directories_checked": "{count} directories checked",
        "status_line": "converted {converted} | correct {correct} | skipped {skipped} | copied {copied} | errors {failed}",
        "status_compact": "C {converted}  O {correct}  S {skipped}  P {copied}  F {failed}",
        "warning": "WARNING",
        "error": "ERROR",
        "partial_summary": "Partial summary",
        "completed": "Conversion complete",
        "finished_after": "{heading} after {elapsed:.1f} seconds",
        "converted": "Converted",
        "already_correct": "Already correct",
        "skipped": "Skipped",
        "copied": "Copied",
        "failed": "Failed",
        "runtime": "Runtime",
        "conversion_rate": "Conversions/min",
        "workers_help": "parallel conversions (positive integer; default: 1)",
        "workers_invalid": "--workers must be a positive integer.",
        "worker_status": "Active: {active}/{workers} | Queued: {queued}",
        "live_summary": "Overall summary",
        "current_operation": "Current operation",
        "activity": "Recent activity",
        "waiting": "Waiting for the first file ...",
        "files": "Files",
        "log_file": "Log file",
        "success_converted": "Converted",
        "phase_non_target": "Convert other formats",
        "phase_target": "Check existing {format} files",
        "phase_sidecar": "Copy sidecar files",
        "interactive_title": "Audio Format Converter - Interactive Mode",
        "input_prompt": "Input directory: ",
        "invalid_input": "The input directory is invalid.",
        "mode_prompt": "Choose mode:\n1. Copy to a new directory\n2. Replace original files\nChoice (1/2): ",
        "invalid_mode": "Please enter 1 or 2.",
        "output_prompt": "Output directory: ",
        "invalid_output": "The output directory could not be created.",
        "format_prompt": "Target format {formats}: ",
        "invalid_format": "Invalid audio format.",
        "bitrate_prompt": "Bitrate {bitrates}: ",
        "invalid_bitrate": "Invalid bitrate.",
        "ffmpeg_missing_prompt": "ffmpeg is not installed. Install it now? [y/N] ",
        "ffmpeg_required": "ffmpeg is required.",
        "cli_description": "Convert audio files while preserving metadata.",
        "cli_values_help": "input [output] format bitrate",
        "replace_help": "replace original files with converted files",
        "rich_help": "enable the Rich live interface",
        "headless_help": "run without console output; log and lock file only",
        "language_help": "console interface language",
        "usage_error": "Invalid arguments: {message}",
        "replace_usage": "Replace mode expects: input format bitrate",
        "copy_usage": "Copy mode expects: input output format bitrate",
        "headless_requires_args": "Headless mode requires complete positional arguments.",
        "mode_conflict": "--rich and --headless cannot be used together.",
        "language_invalid": "Language must be de or en.",
        "help_help": "show this help message and exit",
        "fatal_error": "Fatal error: {message}",
        "python_required": "Python 3.6 or newer is required.",
    },
}


class Translator:
    """Resolve localized user-interface strings."""

    def __init__(self, language):
        self.language = language if language in TRANSLATIONS else "de"

    def __call__(self, key, **values):
        return TRANSLATIONS[self.language][key].format(**values)


RunResult = namedtuple(
    "RunResult",
    [
        "file_count",
        "converted_files",
        "skipped_files",
        "failed_files",
        "correct_files",
        "copied_files",
        "interrupted",
    ],
)


def import_rich():
    """Import Rich components only when Rich mode is requested."""
    global BarColumn, Console, Group, Layout, Live, Panel, Progress, SpinnerColumn
    global Table, TaskProgressColumn, Text, TextColumn, TimeElapsedColumn, TimeRemainingColumn

    try:
        from rich.console import Console, Group
        from rich.layout import Layout
        from rich.live import Live
        from rich.panel import Panel
        from rich.progress import (
            BarColumn,
            Progress,
            SpinnerColumn,
            TaskProgressColumn,
            TextColumn,
            TimeElapsedColumn,
            TimeRemainingColumn,
        )
        from rich.table import Table
        from rich.text import Text
        return True
    except (ImportError, SyntaxError):
        return False


def ensure_rich_available(translate, input_func=input, run_command=subprocess.run):
    """Load Rich or offer installation for an explicitly requested Rich mode."""
    if import_rich():
        return True
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print(translate("rich_noninteractive"))
        return False

    try:
        choice = input_func(translate("rich_missing_prompt")).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n" + translate("rich_declined"))
        return False

    accepted = {"", "j", "ja", "y", "yes"}
    if choice not in accepted:
        print(translate("rich_declined"))
        return False

    print(translate("rich_installing"))
    try:
        result = run_command([sys.executable, "-m", "pip", "install", "rich"])
    except OSError:
        print(translate("rich_install_failed"))
        return False

    if result.returncode != 0:
        print(translate("rich_install_failed"))
        return False

    importlib.invalidate_caches()
    if not import_rich():
        print(translate("rich_import_failed"))
        return False
    return True


class PlainReporter:
    """Compact localized console output without optional dependencies."""

    def __init__(self, translate):
        self.translate = translate
        self.phase_name = ""
        self.phase_counts = self._empty_counts()
        self.started_at = time.monotonic()
        self.interactive = sys.stdout.isatty()
        self.workers = 1
        self.active_paths = ()
        self.queued_jobs = 0

    def worker_progress(self, active_paths, workers, queued):
        self.active_paths = tuple(active_paths)
        self.workers = workers
        self.queued_jobs = queued
        self._write_live(self.translate(
            "worker_status", active=len(self.active_paths), workers=workers, queued=queued
        ))

    @staticmethod
    def _empty_counts():
        return {"converted": 0, "correct": 0, "skipped": 0, "copied": 0, "failed": 0}

    @staticmethod
    def _short_path(path, limit=90):
        if len(path) <= limit:
            return path
        return "..." + path[-(limit - 3):]

    def show_start(self, input_path, output_path, music_format, bitrate, replace_mode):
        mode = self.translate("mode_replace" if replace_mode else "mode_copy")
        print("\n" + self.translate("app_title"))
        print(f"{self.translate('source')}: {input_path}")
        print(f"{self.translate('target')}: {output_path}")
        print(
            f"{self.translate('format')}: {music_format} @ {bitrate} | "
            f"{self.translate('mode')}: {mode}\n"
        )

    def start_phase(self, name, total=None):
        self.phase_name = name
        self.phase_counts = self._empty_counts()
        total_text = (
            f" ({self.translate('files_total', total=total)})"
            if total is not None
            else ""
        )
        print(f"{name}{total_text}")

    def scan_progress(self, directories):
        if directories % 1000 == 0:
            text = self.translate("directories_checked", count=directories)
            self._write_live(f"{self.phase_name}: {text}")

    def file_started(self, relative_path):
        self._write_live(f"{self.phase_name}: {self._short_path(relative_path)}")

    def file_finished(self, status, relative_path=None):
        self.phase_counts[status] += 1
        self._write_live(
            f"{self.phase_name}: "
            + self.translate("status_line", **self.phase_counts)
        )

    def finish_phase(self):
        if self.interactive:
            sys.stdout.write("\n")
        self.phase_name = ""

    def message(self, level, message):
        if self.interactive:
            sys.stdout.write("\n")
        label = self.translate("error" if level >= logging.ERROR else "warning")
        print(f"{label}: {message.splitlines()[0]}")

    def show_summary(self, result, log_file):
        elapsed = time.monotonic() - self.started_at
        heading = self.translate(
            "partial_summary" if result.interrupted else "completed"
        )
        print(
            "\n"
            + self.translate("finished_after", heading=heading, elapsed=elapsed)
        )
        print(f"{self.translate('converted')}: {len(result.converted_files)}")
        print(f"{self.translate('already_correct')}: {len(result.correct_files)}")
        print(f"{self.translate('skipped')}: {len(result.skipped_files)}")
        print(f"{self.translate('copied')}: {len(result.copied_files)}")
        print(f"{self.translate('failed')}: {len(result.failed_files)}")
        rate = len(result.converted_files) * 60 / max(elapsed, 0.001)
        print(f"{self.translate('conversion_rate')}: {rate:.1f}")
        if result.file_count:
            counts = ", ".join(
                f"{ext}: {count}" for ext, count in sorted(result.file_count.items())
            )
            print(f"{self.translate('files')}: {counts}")
        if log_file:
            print(f"{self.translate('log_file')}: {log_file}")

    def close(self):
        pass

    def _write_live(self, text):
        if self.interactive:
            width = max(20, shutil.get_terminal_size((100, 20)).columns - 1)
            sys.stdout.write("\r" + text[:width].ljust(width))
            sys.stdout.flush()


class NullReporter:
    """Reporter that intentionally produces no console output."""

    def show_start(self, *args, **kwargs):
        pass

    def worker_progress(self, *args, **kwargs):
        pass

    def start_phase(self, *args, **kwargs):
        pass

    def scan_progress(self, *args, **kwargs):
        pass

    def file_started(self, *args, **kwargs):
        pass

    def file_finished(self, *args, **kwargs):
        pass

    def finish_phase(self):
        pass

    def message(self, *args, **kwargs):
        pass

    def show_summary(self, *args, **kwargs):
        pass

    def close(self):
        pass


class RichReporter(PlainReporter):
    """Full-screen Rich dashboard with live totals and recent activity."""

    def __init__(self, translate):
        super().__init__(translate)
        self.console = Console()
        self.overall_counts = self._empty_counts()
        self.activity_lines = deque(maxlen=500)
        self.start_details = None
        self.current_path = ""
        self.directories = 0
        self.progress = Progress(
            SpinnerColumn(),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("{task.fields[stats]}", markup=False),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console,
            auto_refresh=False,
            expand=True,
        )
        self.task_id = None
        self.live = None
        self.last_refresh = 0

    def __rich__(self):
        return self._build_dashboard()

    def _dashboard_sizes(self):
        summary = 7 if self.console.width < 80 else 5
        header = 5 if self.console.height >= summary + 13 else 3
        file_rows = max(1, min(self.workers, self.console.height - summary - header - 7))
        current = 4 + file_rows
        activity_rows = max(1, self.console.height - header - summary - current - 2)
        return header, summary, current, activity_rows

    def _build_dashboard(self):
        narrow = self.console.width < 80
        header_height, summary_height, current_height, available_rows = self._dashboard_sizes()
        file_rows = current_height - 4
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=header_height),
            Layout(name="summary", size=summary_height),
            Layout(name="current", size=current_height),
            Layout(name="activity"),
        )
        layout["header"].update(
            Panel(
                self.start_details or Text(self.translate("app_title")),
                title=self.translate("app_title"),
                border_style="cyan",
            )
        )

        summary = Table.grid(expand=True, padding=(0, 1))
        for _ in range(3 if narrow else 6):
            summary.add_column(justify="center", ratio=1)
        labels = [
            self.translate("converted"),
            self.translate("already_correct"),
            self.translate("skipped"),
            self.translate("copied"),
            self.translate("failed"),
            self.translate("runtime"),
        ]
        elapsed = time.monotonic() - self.started_at
        values = [
            Text(str(self.overall_counts["converted"]), style="bold green"),
            Text(str(self.overall_counts["correct"]), style="bold cyan"),
            str(self.overall_counts["skipped"]),
            str(self.overall_counts["copied"]),
            Text(str(self.overall_counts["failed"]), style="bold red"),
            f"{elapsed:.1f} s",
        ]
        columns = 3 if narrow else 6
        for offset in range(0, 6, columns):
            summary.add_row(*[
                Text(label, overflow="ellipsis", no_wrap=True)
                for label in labels[offset:offset + columns]
            ])
            summary.add_row(*values[offset:offset + columns])
        rate = self.overall_counts['converted'] * 60 / max(elapsed, 0.001)
        layout["summary"].update(
            Panel(
                Group(summary, Text(
                    f"{self.translate('conversion_rate')}: {rate:.1f}",
                    no_wrap=True, overflow="ellipsis",
                )),
                title=self.translate("live_summary"),
                subtitle=self.translate("directories_checked", count=self.directories),
                border_style="cyan",
            )
        )

        current = (
            Group(
                Text(self.phase_name, style="bold cyan", no_wrap=True, overflow="ellipsis"),
                self.progress.get_renderable(),
                *[self._path_text(path) for path in
                  (self.active_paths or (self.current_path,))[:file_rows]],
            )
            if self.task_id is not None
            else Text(self.translate("waiting"), style="dim")
        )
        layout["current"].update(
            Panel(
                current,
                title=self.translate("current_operation"),
                subtitle=self.translate(
                    "worker_status", active=len(self.active_paths),
                    workers=self.workers, queued=self.queued_jobs,
                ),
                border_style="cyan",
            )
        )

        visible_lines = list(self.activity_lines)[-available_rows:]
        activity = Group(*[
            self._activity_text(kind, message) for kind, message in visible_lines
        ]) if visible_lines else Text(
            self.translate("waiting"), style="dim"
        )
        layout["activity"].update(
            Panel(
                activity,
                title=self.translate("activity"),
                border_style="cyan",
            )
        )
        return layout

    def _path_text(self, path, width=None):
        width = max(4, self.console.width - 4) if width is None else max(4, width)
        text = Text(path, no_wrap=True, overflow="ellipsis")
        if text.cell_len > width:
            # Binary search a suffix that fits terminal cells, including wide Unicode.
            low, high = 0, len(path)
            while low < high:
                middle = (low + high) // 2
                if Text(path[middle:]).cell_len > width - 3:
                    low = middle + 1
                else:
                    high = middle
            text = Text("..." + path[low:], no_wrap=True, overflow="ellipsis")
        return text

    def _activity_text(self, kind, message):
        if kind == "converted":
            prefix = "\u2713 " + self.translate("success_converted") + ": "
            style = "green"
        else:
            prefix = self.translate(kind) + ": "
            style = "red" if kind == "error" else "yellow"
        line = Text(prefix, style=style, no_wrap=True, overflow="ellipsis")
        line.append_text(self._path_text(message, self.console.width - 4 - line.cell_len))
        return line

    def _refresh(self):
        now = time.monotonic()
        if self.live is not None and now - self.last_refresh >= 0.125:
            self.last_refresh = now
            self.live.refresh()

    def show_start(self, input_path, output_path, music_format, bitrate, replace_mode):
        mode = self.translate("mode_replace" if replace_mode else "mode_copy")
        details = Table.grid(padding=(0, 1))
        details.add_column(no_wrap=True)
        details.add_column(overflow="ellipsis", no_wrap=True)
        details.add_row(self.translate("source") + ":", Text(input_path))
        details.add_row(self.translate("target") + ":", Text(output_path))
        details.add_row(
            self.translate("format") + ":",
            f"{music_format} @ {bitrate} | {self.translate('mode')}: {mode}",
        )
        self.start_details = details
        self.live = Live(
            self,
            console=self.console,
            refresh_per_second=8,
            screen=True,
            vertical_overflow="crop",
        )
        self.live.start(refresh=True)

    def start_phase(self, name, total=None):
        self.phase_name = name
        self.phase_counts = self._empty_counts()
        self.current_path = ""
        if self.task_id is not None:
            self.progress.remove_task(self.task_id)
        self.task_id = self.progress.add_task(
            name,
            total=total,
            stats="",
            current="",
        )
        self._refresh()

    def scan_progress(self, directories):
        self.directories = directories
        if self.task_id is not None:
            self._refresh()

    def file_started(self, relative_path):
        self.current_path = relative_path
        if self.task_id is not None:
            self._refresh()

    def worker_progress(self, active_paths, workers, queued):
        self.active_paths = tuple(active_paths)
        self.workers = workers
        self.queued_jobs = queued
        self._refresh()

    def file_finished(self, status, relative_path=None):
        self.phase_counts[status] += 1
        self.overall_counts[status] += 1
        if self.task_id is not None:
            stats = self.translate("files_total", total=sum(self.phase_counts.values()))
            self.progress.update(self.task_id, advance=1, stats=stats)

        if status == "converted" and relative_path:
            self.activity_lines.append(("converted", relative_path))
        self._refresh()

    def finish_phase(self):
        if self.task_id is not None:
            self.progress.stop_task(self.task_id)
        self._refresh()

    def message(self, level, message):
        kind = "error" if level >= logging.ERROR else "warning"
        message = message.splitlines()[0] if message else ""
        if self.live is None:
            self.console.print(self._activity_text(kind, message))
        self.activity_lines.append((kind, message))
        self._refresh()

    def show_summary(self, result, log_file):
        self.close()
        elapsed = time.monotonic() - self.started_at
        title = self.translate(
            "partial_summary" if result.interrupted else "completed"
        )
        table = Table(title=title, border_style="cyan", show_header=False)
        table.add_column("Status", style="bold")
        table.add_column("Count", justify="right")
        table.add_row(
            self.translate("converted"),
            str(len(result.converted_files)),
            style="green",
        )
        table.add_row(
            self.translate("already_correct"),
            str(len(result.correct_files)),
            style="cyan",
        )
        table.add_row(self.translate("skipped"), str(len(result.skipped_files)))
        table.add_row(self.translate("copied"), str(len(result.copied_files)))
        table.add_row(
            self.translate("failed"),
            str(len(result.failed_files)),
            style="red",
        )
        table.add_row(self.translate("runtime"), f"{elapsed:.1f} s")
        rate = len(result.converted_files) * 60 / max(elapsed, 0.001)
        table.add_row(self.translate("conversion_rate"), f"{rate:.1f}")
        self.console.print(table)
        if result.file_count:
            counts = "  ".join(
                f"{ext}: {count}"
                for ext, count in sorted(result.file_count.items())
            )
            self.console.print(Text(counts, style="dim"))
        if log_file:
            self.console.print(
                Text(f"{self.translate('log_file')}: {log_file}", style="dim")
            )

    def close(self):
        if self.live is not None:
            self.live.stop()
            self.live = None
            count = self._dashboard_sizes()[3]
            for kind, message in list(self.activity_lines)[-count:]:
                self.console.print(self._activity_text(kind, message))


class ReporterLogHandler(logging.Handler):
    """Forward warnings and errors to the active console reporter."""

    def __init__(self, reporter):
        super().__init__(level=logging.WARNING)
        self.reporter = reporter

    def emit(self, record):
        try:
            self.reporter.message(record.levelno, record.getMessage())
        except Exception:
            self.handleError(record)


def create_reporter(mode, translate):
    """Create the explicitly requested console reporter."""
    if mode == "headless":
        return NullReporter()
    if mode == "rich":
        return RichReporter(translate)
    return PlainReporter(translate)

class CLIError(Exception):
    """Raised when command-line arguments are invalid."""


class ConverterArgumentParser(argparse.ArgumentParser):
    """Argument parser that lets main control localized error output."""

    def __init__(self, translate, *args, **kwargs):
        self.translate = translate
        super().__init__(*args, **kwargs)

    def error(self, message):
        raise CLIError(message)

    def format_help(self):
        help_text = super().format_help()
        if self.translate.language == "de":
            help_text = help_text.replace("usage:", "Verwendung:")
            help_text = help_text.replace("positional arguments:", "Positionsargumente:")
            help_text = help_text.replace("options:", "Optionen:")
        return help_text


RunConfig = namedtuple(
    "RunConfig",
    [
        "input_path",
        "output_path",
        "music_format",
        "bitrate",
        "replace_mode",
        "console_mode",
        "language",
        "workers",
    ],
)


def check_python_version():
    """Return whether the current Python version is supported."""
    return sys.version_info >= (3, 6)


def _ffmpeg_install_command():
    """Return a suitable package-manager command for the current platform."""
    if sys.platform == "win32" and shutil.which("winget"):
        return ["winget", "install", "Gyan.FFmpeg"]
    if sys.platform == "darwin" and shutil.which("brew"):
        return ["brew", "install", "ffmpeg"]
    if sys.platform.startswith("linux"):
        managers = (
            ("apt-get", ["sudo", "apt-get", "install", "-y", "ffmpeg"]),
            ("dnf", ["sudo", "dnf", "install", "-y", "ffmpeg"]),
            ("pacman", ["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"]),
            ("zypper", ["sudo", "zypper", "install", "-y", "ffmpeg"]),
        )
        for executable, command in managers:
            if shutil.which(executable):
                return command
    return None


def check_ffmpeg(translate, interactive):
    """Check ffmpeg and optionally offer installation outside headless mode."""
    if shutil.which("ffmpeg") is not None:
        return True

    logging.error("ffmpeg is not installed")
    if not interactive:
        return False

    try:
        choice = input(translate("ffmpeg_missing_prompt")).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(translate("ffmpeg_required"))
        return False

    if choice not in {"j", "ja", "y", "yes"}:
        print(translate("ffmpeg_required"))
        return False

    command = _ffmpeg_install_command()
    if command is None:
        print(translate("ffmpeg_required"))
        return False

    try:
        result = subprocess.run(command)
    except OSError:
        print(translate("ffmpeg_required"))
        return False

    if result.returncode != 0 or shutil.which("ffmpeg") is None:
        print(translate("ffmpeg_required"))
        return False
    return True


def get_user_input(translate):
    """Collect conversion parameters for interactive mode."""
    print("\n" + translate("interactive_title"))

    while True:
        input_path = input(translate("input_prompt")).strip()
        if os.path.isdir(input_path):
            break
        print(translate("invalid_input"))

    while True:
        mode = input(translate("mode_prompt")).strip()
        if mode in {"1", "2"}:
            replace_mode = mode == "2"
            break
        print(translate("invalid_mode"))

    output_path = input_path
    if not replace_mode:
        while True:
            output_path = input(translate("output_prompt")).strip()
            try:
                os.makedirs(output_path, exist_ok=True)
                break
            except OSError:
                print(translate("invalid_output"))

    formats = ", ".join(sorted(AUDIO_FORMATS))
    while True:
        music_format = input(
            translate("format_prompt", formats=formats)
        ).strip().lower()
        if music_format in AUDIO_FORMATS:
            break
        print(translate("invalid_format"))

    valid_bitrates = {"32k", "64k", "128k", "192k", "256k", "320k"}
    bitrates = ", ".join(sorted(valid_bitrates))
    while True:
        bitrate = input(
            translate("bitrate_prompt", bitrates=bitrates)
        ).strip().lower()
        if bitrate in valid_bitrates:
            break
        print(translate("invalid_bitrate"))

    return input_path, output_path, music_format, bitrate, replace_mode


def detect_language(arguments):
    """Read the requested language before building localized help text."""
    for index, argument in enumerate(arguments):
        if argument.startswith("--language="):
            return argument.split("=", 1)[1]
        if argument == "--language" and index + 1 < len(arguments):
            return arguments[index + 1]
    return "de"


def build_argument_parser(translate):
    """Build the localized command-line parser."""
    parser = ConverterArgumentParser(
        translate,
        description=translate("cli_description"),
        add_help=False,
    )
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        help=translate("help_help"),
    )
    parser.add_argument(
        "values",
        nargs="*",
        metavar="VALUE",
        help=translate("cli_values_help"),
    )
    parser.add_argument(
        "--rich",
        action="store_true",
        help=translate("rich_help"),
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help=translate("headless_help"),
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help=translate("replace_help"),
    )
    parser.add_argument(
        "--language",
        default=translate.language,
        metavar="{de,en}",
        help=translate("language_help"),
    )
    parser.add_argument("--workers", default="1", metavar="N", help=translate("workers_help"))
    return parser


def normalize_arguments(arguments):
    """Move known options ahead of positionals for Python 3.6 argparse."""
    options = []
    values = []
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in {"--rich", "--headless", "--replace", "--help", "-h"}:
            options.append(argument)
        elif argument in {"--language", "--workers"}:
            options.append(argument)
            if index + 1 < len(arguments):
                index += 1
                options.append(arguments[index])
        elif argument.startswith(("--language=", "--workers=")):
            options.append(argument)
        elif argument.startswith("--"):
            options.append(argument)
        else:
            values.append(argument)
        index += 1
    return options + values


def parse_arguments(arguments=None):
    """Parse both legacy positional forms plus the new console flags."""
    arguments = list(sys.argv[1:] if arguments is None else arguments)
    language = detect_language(arguments)
    if language not in TRANSLATIONS:
        language = "de"
    translate = Translator(language)
    parser = build_argument_parser(translate)
    parsed = parser.parse_args(normalize_arguments(arguments))
    if parsed.language not in TRANSLATIONS:
        raise CLIError(translate("language_invalid"))
    translate = Translator(parsed.language)
    try:
        workers = int(parsed.workers)
    except ValueError:
        raise CLIError(translate("workers_invalid"))
    if workers < 1:
        raise CLIError(translate("workers_invalid"))

    if parsed.rich and parsed.headless:
        raise CLIError(translate("mode_conflict"))

    if parsed.headless and not parsed.values:
        raise CLIError(translate("headless_requires_args"))

    if not parsed.values:
        input_path, output_path, music_format, bitrate, replace_mode = get_user_input(
            translate
        )
    elif parsed.replace:
        if len(parsed.values) != 3:
            raise CLIError(translate("replace_usage"))
        input_path, music_format, bitrate = parsed.values
        output_path = input_path
        replace_mode = True
    else:
        if len(parsed.values) != 4:
            raise CLIError(translate("copy_usage"))
        input_path, output_path, music_format, bitrate = parsed.values
        replace_mode = False

    console_mode = "headless" if parsed.headless else "rich" if parsed.rich else "plain"
    return RunConfig(
        input_path=input_path,
        output_path=output_path,
        music_format=music_format.lower(),
        bitrate=bitrate.lower(),
        replace_mode=replace_mode,
        console_mode=console_mode,
        language=parsed.language,
        workers=workers,
    )


def validate_paths_and_parameters(config, translate):
    """Validate paths and conversion values, raising localized errors."""
    if not os.path.isdir(config.input_path):
        raise ValueError(translate("invalid_input"))

    if not os.path.isdir(config.output_path):
        try:
            os.makedirs(config.output_path)
        except OSError:
            raise ValueError(translate("invalid_output"))

    if config.music_format not in AUDIO_FORMATS:
        raise ValueError(translate("invalid_format"))

    valid_bitrates = {"32k", "64k", "128k", "192k", "256k", "320k"}
    if config.bitrate not in valid_bitrates:
        raise ValueError(translate("invalid_bitrate"))

def setup_logging(input_path, reporter):
    """Configure detailed file logging and compact console warnings."""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'convert_{timestamp}.log')

    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        handler.close()

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(ReporterLogHandler(reporter))

    logging.info("Starting conversion process")
    logging.info(f"Input path: {input_path}")
    return log_file

def get_audio_info(file_path):
    """
    Get audio format and bitrate information using ffprobe.

    Args:
        file_path (str): Path to the audio file

    Returns:
        tuple: (format_name, bitrate) or (None, None) if retrieval fails
    """
    try:
        # Handle Unicode paths by encoding properly
        encoded_path = os.fsdecode(file_path)

        # Add timeout to prevent hanging
        result = subprocess.run([
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            encoded_path
        ], capture_output=True, text=True, encoding='utf-8', timeout=10)  # Add 10 second timeout

        if result.returncode == 0 and result.stdout:
            try:
                info = json.loads(result.stdout)
                for stream in info.get('streams', []):
                    if stream.get('codec_type') == 'audio':
                        # Get format
                        format_name = info['format']['format_name'].split(',')[0]

                        # Get bitrate
                        bitrate = stream.get('bit_rate')
                        if bitrate:
                            bitrate = f"{int(int(bitrate)/1000)}k"

                        return format_name, bitrate
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON for {file_path}: {str(e)}")
                return None, None
        return None, None
    except subprocess.TimeoutExpired:
        logging.error(f"Timeout while processing {file_path}")
        return None, None
    except Exception as e:
        logging.error(f"Error getting audio info for {file_path}: {str(e)}")
        return None, None

def get_lock_file_path():
    """
    Get the path to the lock file, which is stored next to the script.
    Creates the lock file if it doesn't exist.
    
    Returns:
        str: Path to lock file
    """
    lock_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.convert.lock')
    if not os.path.exists(lock_file):
        try:
            with open(lock_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=2, ensure_ascii=False)
            logging.info(f"Created new lock file: {lock_file}")
        except Exception as e:
            logging.error(f"Failed to create lock file: {str(e)}")
    return lock_file

def read_lock_file(lock_file):
    """
    Read the lock file containing information about converted files.

    Args:
        lock_file (str): Path to lock file

    Returns:
        dict: Dictionary with file paths as keys and conversion info as values
    """
    try:
        if os.path.exists(lock_file):
            with open(lock_file, 'r', encoding='utf-8') as f:
                lock_content = f.read()
            return json.loads(lock_content)
    except json.JSONDecodeError as e:
        backup_file = f"{lock_file}.corrupt-{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        logging.warning(f"Lock file is incomplete; preserving a backup at: {backup_file}")

        try:
            shutil.copy2(lock_file, backup_file)

            # Keep all complete top-level entries before the truncated entry.
            entry_start = lock_content.rfind('\n  "', 0, e.pos)
            if entry_start > 0:
                repaired_content = lock_content[:entry_start].rstrip()
                if repaired_content.endswith(','):
                    repaired_content = repaired_content[:-1]
                repaired_data = json.loads(f"{repaired_content}\n}}")

                temp_file = f"{lock_file}.tmp.{os.getpid()}"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(repaired_data, f, indent=2, ensure_ascii=False)
                os.replace(temp_file, lock_file)
                logging.info(f"Recovered {len(repaired_data)} entries from the lock file")
                return repaired_data
        except Exception as repair_error:
            logging.error(f"Could not repair lock file: {str(repair_error)}")
    except Exception as e:
        logging.error(f"Error reading lock file: {str(e)}")
    return {}

def update_lock_file(lock_file, converted_files_info):
    """
    Update the lock file with new conversion information.

    Args:
        lock_file (str): Path to lock file
        converted_files_info (dict): Dictionary with conversion information to add
    """
    temp_file = f"{lock_file}.tmp.{os.getpid()}"
    try:
        # Read existing data
        lock_data = read_lock_file(lock_file)
        # Update with new data
        lock_data.update(converted_files_info)
        # Replace atomically so an interruption cannot truncate the lock file.
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(lock_data, f, indent=2, ensure_ascii=False)
        os.replace(temp_file, lock_file)
        return True
    except Exception as e:
        logging.error(f"Error updating lock file: {str(e)}")
        return False
    finally:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass

ConversionJob = namedtuple(
    "ConversionJob", "source relative_path extension destination temporary same_path"
)
EncodingResult = namedtuple("EncodingResult", "returncode error cancelled")


@contextmanager
def defer_interrupt(raise_after=True):
    """Defer Ctrl+C while publishing output or completing shutdown."""
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


# Some source mp3 files trip ffmpeg's container auto-probe (it misdetects
# them as RIFF/WAV or raw H.263 despite valid ID3v2 headers). Forcing the
# demuxer for known-mp3 sources skips that faulty probe entirely.
_FORCED_INPUT_FORMATS = {"mp3": "mp3"}


def _ffmpeg_args(job, bitrate, only_audio, force_input=False):
    args = ["ffmpeg", "-hide_banner", "-nostdin", "-y"]
    forced_format = _FORCED_INPUT_FORMATS.get(job.extension) if force_input else None
    if forced_format:
        args += ["-f", forced_format]
    args += ["-i", job.source]
    if only_audio:
        args += ["-map", "0:a"]
    args += [
        "-b:a", bitrate, "-map_metadata", "0",
        "-id3v2_version", "3", job.temporary,
    ]
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
    """Encode only; publishing files and shared state belong to the coordinator."""
    if stop.is_set():
        return EncodingResult(None, "", True)
    try:
        # Extensions can be wrong (for example FLAC audio named .mp3).
        # Prefer content detection; force the extension's demuxer only as
        # a fallback for genuine MP3 files that confuse auto-probing.
        attempts = [False, True] if job.extension in _FORCED_INPUT_FORMATS else [False]
        errors = []
        for force_input in attempts:
            # Retry without embedded art if its codec declaration is broken.
            for only_audio in (False, True):
                result = _run_ffmpeg(
                    _ffmpeg_args(job, bitrate, only_audio, force_input), stop
                )
                if result.returncode == 0 or result.cancelled or stop.is_set():
                    return result
                errors.append(result.error)
        return EncodingResult(result.returncode, "\n".join(errors), False)
    except Exception as error:
        return EncodingResult(None, str(error), stop.is_set())


def publish_conversion(job, replace_mode):
    """Atomically replace targets in replace mode; never overwrite in copy mode."""
    if replace_mode:
        os.replace(job.temporary, job.destination)
    elif os.name == "nt":
        # Windows rename fails if the destination exists, including on SMB.
        os.rename(job.temporary, job.destination)
    else:
        # Unlike POSIX rename, creating a hard link cannot overwrite a collision.
        os.link(job.temporary, job.destination)
        os.remove(job.temporary)


def process_files(
    input_path,
    output_path,
    music_format,
    bitrate,
    replace_mode,
    reporter=None,
    log_file=None,
    translate=None,
    workers=1,
):
    """Stream priority phases through a bounded pool of FFmpeg processes."""
    if not isinstance(workers, int) or workers < 1:
        raise ValueError("workers must be a positive integer")
    translate = translate or Translator("de")
    reporter = reporter or PlainReporter(translate)
    started_at = time.monotonic()
    file_count = {}
    converted_files, skipped_files, failed_files = [], [], []
    correct_files, copied_files = [], []
    interrupted = False
    lock_file = get_lock_file_path()
    converted_files_info = read_lock_file(lock_file)
    new_conversions = {}
    generated_target_files = set()
    replacement_targets = set()
    reserved_destinations = set()
    temporary_files = set()
    pending = {}
    stop = Event()
    pool = ThreadPoolExecutor(max_workers=workers)
    phase_open = False

    def normalized(path):
        return os.path.normcase(os.path.abspath(path))

    source_root = normalized(input_path)
    output_root = normalized(output_path)
    supported_sidecar_formats = {"jpg", "jpeg", "png", "gif", "bmp", "webp", "nfo"}
    discovered_counts = {"target_audio": 0, "sidecar": 0}
    status_files = {
        "converted": converted_files, "skipped": skipped_files,
        "failed": failed_files, "correct": correct_files, "copied": copied_files,
    }

    def record(status, path, relative_path, extension):
        status_files[status].append(path)
        file_count[extension] = file_count.get(extension, 0) + 1
        reporter.file_finished(status, relative_path)

    def queue_lock_update(path, status):
        info = {
            "format": music_format, "bitrate": bitrate,
            "timestamp": datetime.now().isoformat(), "status": status,
        }
        converted_files_info[path] = info
        new_conversions[path] = info

    def flush_lock():
        if new_conversions:
            if not update_lock_file(lock_file, new_conversions):
                raise OSError("Could not save conversion progress to the lock file")
            new_conversions.clear()

    def clean_temporary(path):
        try:
            if os.path.exists(path):
                os.remove(path)
            temporary_files.discard(path)
        except OSError as error:
            logging.error(f"Could not remove temporary file {path}: {error}")

    def report_workers():
        active = [
            job.relative_path for future, job in pending.items()
            if future.running() and not future.done()
        ]
        queued = sum(not future.running() and not future.done() for future in pending)
        reporter.worker_progress(active, workers, queued)

    def finish_job(future, job):
        try:
            if future.cancelled():
                return
            result = future.result()
            if result.cancelled:
                return
            if result.returncode != 0:
                raise OSError(result.error or "FFmpeg conversion failed")
            if not os.path.isfile(job.temporary) or os.path.getsize(job.temporary) == 0:
                raise OSError("FFmpeg did not produce a non-empty output file")
            publish_conversion(job, replace_mode)
            generated_target_files.add(normalized(job.destination))
            if replace_mode and not job.same_path:
                os.remove(job.source)
            queue_lock_update(job.destination if replace_mode else job.source, "converted")
            logging.info(f"Successfully converted: {job.source} -> {job.destination}")
            record("converted", job.source, job.relative_path, job.extension)
        except Exception as error:
            logging.error(f"Failed to convert {job.source}: {error}")
            record("failed", job.source, job.relative_path, job.extension)
        finally:
            clean_temporary(job.temporary)

    def collect_finished(block=False):
        if not pending:
            return
        if block:
            wait(tuple(pending), timeout=0.1, return_when=FIRST_COMPLETED)
        for future in list(pending):
            if future.done():
                # A signal cannot split publication from its statistics/lock record.
                with defer_interrupt():
                    job = pending.pop(future)
                    finish_job(future, job)
        report_workers()
        if len(new_conversions) >= 250:
            with defer_interrupt():
                flush_lock()

    def iter_phase(phase):
        directories = 0
        for root, dirs, files in os.walk(input_path):
            if not replace_mode and source_root != output_root:
                dirs[:] = [d for d in dirs if normalized(os.path.join(root, d)) != output_root]
            directories += 1
            if directories % 50 == 0:
                reporter.scan_progress(directories)
                collect_finished()
            if directories % 1000 == 0:
                logging.info(f"Scan progress: {directories} directories checked")
            for filename in files:
                if filename.startswith(".convert-"):
                    continue
                extension = os.path.splitext(filename)[1][1:].lower()
                path = os.path.join(root, filename)
                if phase == "non_target_audio":
                    if extension == music_format:
                        discovered_counts["target_audio"] += 1
                    elif extension in supported_sidecar_formats:
                        discovered_counts["sidecar"] += 1
                    if extension in AUDIO_FORMATS and extension != music_format:
                        yield path, extension
                elif phase == "target_audio" and extension == music_format:
                    key = normalized(path)
                    if key not in generated_target_files and key not in replacement_targets:
                        yield path, extension
                elif phase == "sidecar" and extension in supported_sidecar_formats:
                    yield path, extension
        reporter.scan_progress(directories)

    phases = [
        ("non_target_audio", translate("phase_non_target")),
        ("target_audio", translate("phase_target", format=music_format.upper())),
    ]
    if not replace_mode:
        phases.append(("sidecar", translate("phase_sidecar")))
    try:
        reporter.worker_progress((), workers, 0)
        for phase, name in phases:
            total = discovered_counts.get(phase)
            if phase == "target_audio":
                total = max(0, total - len(replacement_targets))
            reporter.start_phase(name, total)
            phase_open = True
            logging.info(f"Starting phase: {phase}; workers={workers}")
            for file_path, ext in iter_phase(phase):
                while len(pending) >= 2 * workers:
                    collect_finished(block=True)
                collect_finished()
                relative_path = os.path.relpath(file_path, input_path)
                target_dir = (
                    os.path.dirname(file_path) if replace_mode
                    else os.path.join(output_path, os.path.dirname(relative_path))
                )
                if phase == "sidecar":
                    reporter.file_started(relative_path)
                    try:
                        os.makedirs(target_dir, exist_ok=True)
                        shutil.copy(file_path, target_dir)
                        logging.info(f"Copied: {file_path} -> {target_dir}")
                        record("copied", file_path, relative_path, ext)
                    except OSError as error:
                        logging.error(f"Failed to copy {file_path}: {error}")
                        record("failed", file_path, relative_path, ext)
                    continue

                info = converted_files_info.get(file_path)
                if (
                    info and info.get("format") == music_format
                    and info.get("bitrate") == bitrate
                    and (not replace_mode or ext == music_format)
                ):
                    logging.info(f"Skipping previously processed file (from lock): {file_path}")
                    record("skipped", file_path, relative_path, ext)
                    continue
                if ext == music_format:
                    reporter.file_started(relative_path)
                    current_format, current_bitrate = get_audio_info(file_path)
                    if current_format == music_format and current_bitrate == bitrate:
                        with defer_interrupt():
                            queue_lock_update(file_path, "correct_format")
                            logging.info(f"Skipping file already in correct format and bitrate: {file_path}")
                            record("correct", file_path, relative_path, ext)
                        if len(new_conversions) >= 250:
                            flush_lock()
                        continue
                else:
                    logging.info(f"Converting non-{music_format} audio without probing: {file_path}")

                destination = os.path.join(
                    target_dir, os.path.splitext(os.path.basename(file_path))[0] + "." + music_format
                )
                destination_key = normalized(destination)
                same_path = normalized(file_path) == destination_key
                if destination_key in reserved_destinations or (
                    os.path.lexists(destination) and not replace_mode
                ):
                    logging.warning(f"Skipping because target exists or is reserved: {file_path} -> {destination}")
                    record("skipped", file_path, relative_path, ext)
                    continue

                if replace_mode and not same_path and os.path.lexists(destination):
                    # Do not process an old target separately if its replacement fails.
                    replacement_targets.add(destination_key)
                    logging.info(f"Replacing existing target after successful conversion: {file_path} -> {destination}")
                try:
                    os.makedirs(target_dir, exist_ok=True)
                    with defer_interrupt():
                        fd, temporary = tempfile.mkstemp(
                            prefix=".convert-", suffix="." + music_format, dir=target_dir
                        )
                        os.close(fd)
                        job = ConversionJob(file_path, relative_path, ext, destination, temporary, same_path)
                        reserved_destinations.add(destination_key)
                        temporary_files.add(temporary)
                        future = pool.submit(encode_job, job, bitrate, stop)
                        pending[future] = job
                    report_workers()
                except OSError as error:
                    logging.error(f"Failed to prepare conversion {file_path}: {error}")
                    record("failed", file_path, relative_path, ext)
            while pending:
                collect_finished(block=True)
            reporter.finish_phase()
            phase_open = False
    except KeyboardInterrupt:
        interrupted = True
        logging.warning("Conversion interrupted; stopping workers and saving completed progress")
    finally:
        # Further Ctrl+C presses must not leave encoders writing into abandoned files.
        with defer_interrupt(raise_after=False):
            stop.set()
            for future in pending:
                future.cancel()
            pool.shutdown(wait=True)
            for future, job in list(pending.items()):
                finish_job(future, job)
            pending.clear()
            for path in list(temporary_files):
                clean_temporary(path)
            reporter.worker_progress((), workers, 0)
            if phase_open:
                reporter.finish_phase()
            flush_lock()

    elapsed = time.monotonic() - started_at
    logging.info(
        f"Conversion throughput: {len(converted_files) * 60 / max(elapsed, 0.001):.1f} "
        f"conversions/min; workers={workers}; elapsed={elapsed:.1f}s"
    )

    result = RunResult(
        file_count=file_count,
        converted_files=converted_files,
        skipped_files=skipped_files,
        failed_files=failed_files,
        correct_files=correct_files,
        copied_files=copied_files,
        interrupted=interrupted,
    )
    summary_lines = [
        "Conversion Summary:",
        f"Successfully converted: {len(converted_files)}",
        f"Skipped (already converted): {len(skipped_files)}",
        f"Skipped (correct format/bitrate): {len(correct_files)}",
        f"Copied sidecar files: {len(copied_files)}",
        f"Failed operations: {len(failed_files)}",
        "File counts by extension: "
        + ", ".join(f"{ext}={count}" for ext, count in sorted(file_count.items())),
    ]
    if failed_files:
        summary_lines.append("Failed files:")
        summary_lines.extend(f"- {file_path}" for file_path in failed_files)
    logging.info("\n" + "\n".join(summary_lines))
    reporter.show_summary(result, log_file)

    return result

def main(arguments=None):
    """Run the converter and return a stable process exit code."""
    arguments = list(sys.argv[1:] if arguments is None else arguments)
    language = detect_language(arguments)
    translate = Translator(language)
    headless_requested = "--headless" in arguments

    if not check_python_version():
        if not headless_requested:
            print(translate("python_required"))
        return 1

    try:
        config = parse_arguments(arguments)
    except CLIError as error:
        message = translate("usage_error", message=str(error))
        if headless_requested:
            try:
                reporter = NullReporter()
                setup_logging("<arguments>", reporter)
                logging.error(message)
            except OSError:
                pass
        else:
            print(message)
        return 1

    translate = Translator(config.language)
    if config.console_mode == "rich":
        if not ensure_rich_available(translate):
            return 1

    reporter = create_reporter(config.console_mode, translate)
    try:
        log_file = setup_logging(config.input_path, reporter)
    except OSError as error:
        if config.console_mode != "headless":
            print(translate("fatal_error", message=str(error)))
        return 1

    try:
        validate_paths_and_parameters(config, translate)
        if not check_ffmpeg(
            translate,
            interactive=config.console_mode != "headless",
        ):
            return 1

        logging.info(f"Output path: {config.output_path}")
        logging.info(f"Format: {config.music_format}")
        logging.info(f"Bitrate: {config.bitrate}")
        logging.info(f"Replace mode: {config.replace_mode}")
        logging.info(f"Console mode: {config.console_mode}")
        logging.info(f"Language: {config.language}")
        logging.info(f"Parallel workers: {config.workers}")
        reporter.worker_progress((), config.workers, 0)
        reporter.show_start(
            config.input_path,
            config.output_path,
            config.music_format,
            config.bitrate,
            config.replace_mode,
        )

        result = process_files(
            config.input_path,
            config.output_path,
            config.music_format,
            config.bitrate,
            config.replace_mode,
            reporter=reporter,
            log_file=log_file,
            translate=translate,
            workers=config.workers,
        )
        logging.info(f"Conversion completed. Log file: {log_file}")

        if result.interrupted:
            return 130
        if result.failed_files:
            return 2
        return 0
    except ValueError as error:
        logging.error(str(error))
        return 1
    except Exception as error:
        logging.exception(f"Fatal converter error: {str(error)}")
        return 1
    finally:
        reporter.close()

if __name__ == "__main__":
    sys.exit(main())
