"""Console output and translations; Rich is loaded only when requested."""

import importlib
import logging
import shutil
import subprocess
import sys
import time
from collections import deque
from types import SimpleNamespace

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
        "headless_help": "ohne Konsolenausgabe ausfuehren; nur Log und Verlauf",
        "language_help": "Sprache der Konsolenoberflaeche",
        "usage_error": "Ungueltige Argumente: {message}",
        "replace_usage": "Replace-Modus erwartet: Eingabe Format Bitrate",
        "copy_usage": "Copy-Modus erwartet: Eingabe Ausgabe Format Bitrate",
        "headless_requires_args": "Headless-Modus benoetigt vollstaendige Positionsargumente.",
        "mode_conflict": "--rich und --headless koennen nicht gemeinsam verwendet werden.",
        "language_invalid": "Die Sprache muss de oder en sein.",
        "help_help": "diese Hilfe anzeigen und beenden",
        "fatal_error": "Fataler Fehler: {message}",
        "python_required": "Python 3.11 oder neuer wird benoetigt.",
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
        "headless_help": "run without console output; log and history only",
        "language_help": "console interface language",
        "usage_error": "Invalid arguments: {message}",
        "replace_usage": "Replace mode expects: input format bitrate",
        "copy_usage": "Copy mode expects: input output format bitrate",
        "headless_requires_args": "Headless mode requires complete positional arguments.",
        "mode_conflict": "--rich and --headless cannot be used together.",
        "language_invalid": "Language must be de or en.",
        "help_help": "show this help message and exit",
        "fatal_error": "Fatal error: {message}",
        "python_required": "Python 3.11 or newer is required.",
    },
}

class Translator:
    """Resolve localized user-interface strings."""

    def __init__(self, language):
        self.language = language if language in TRANSLATIONS else "en"

    def __call__(self, key, **values):
        return TRANSLATIONS[self.language][key].format(**values)

def import_rich():
    """Import Rich components only when Rich mode is requested."""

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
        return SimpleNamespace(**locals())
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
        self.rich = import_rich()
        self.console = self.rich.Console()
        self.overall_counts = self._empty_counts()
        self.activity_lines = deque(maxlen=500)
        self.start_details = None
        self.current_path = ""
        self.directories = 0
        self.progress = self.rich.Progress(
            self.rich.SpinnerColumn(),
            self.rich.BarColumn(),
            self.rich.TaskProgressColumn(),
            self.rich.TextColumn("{task.fields[stats]}", markup=False),
            self.rich.TimeElapsedColumn(),
            self.rich.TimeRemainingColumn(),
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
        layout = self.rich.Layout()
        layout.split_column(
            self.rich.Layout(name="header", size=header_height),
            self.rich.Layout(name="summary", size=summary_height),
            self.rich.Layout(name="current", size=current_height),
            self.rich.Layout(name="activity"),
        )
        layout["header"].update(
            self.rich.Panel(
                self.start_details or self.rich.Text(self.translate("app_title")),
                title=self.translate("app_title"),
                border_style="cyan",
            )
        )

        summary = self.rich.Table.grid(expand=True, padding=(0, 1))
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
            self.rich.Text(str(self.overall_counts["converted"]), style="bold green"),
            self.rich.Text(str(self.overall_counts["correct"]), style="bold cyan"),
            str(self.overall_counts["skipped"]),
            str(self.overall_counts["copied"]),
            self.rich.Text(str(self.overall_counts["failed"]), style="bold red"),
            f"{elapsed:.1f} s",
        ]
        columns = 3 if narrow else 6
        for offset in range(0, 6, columns):
            summary.add_row(*[
                self.rich.Text(label, overflow="ellipsis", no_wrap=True)
                for label in labels[offset:offset + columns]
            ])
            summary.add_row(*values[offset:offset + columns])
        rate = self.overall_counts['converted'] * 60 / max(elapsed, 0.001)
        layout["summary"].update(
            self.rich.Panel(
                self.rich.Group(summary, self.rich.Text(
                    f"{self.translate('conversion_rate')}: {rate:.1f}",
                    no_wrap=True, overflow="ellipsis",
                )),
                title=self.translate("live_summary"),
                subtitle=self.translate("directories_checked", count=self.directories),
                border_style="cyan",
            )
        )

        current = (
            self.rich.Group(
                self.rich.Text(self.phase_name, style="bold cyan", no_wrap=True, overflow="ellipsis"),
                self.progress.get_renderable(),
                *[self._path_text(path) for path in
                  (self.active_paths or (self.current_path,))[:file_rows]],
            )
            if self.task_id is not None
            else self.rich.Text(self.translate("waiting"), style="dim")
        )
        layout["current"].update(
            self.rich.Panel(
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
        activity = self.rich.Group(*[
            self._activity_text(kind, message) for kind, message in visible_lines
        ]) if visible_lines else self.rich.Text(
            self.translate("waiting"), style="dim"
        )
        layout["activity"].update(
            self.rich.Panel(
                activity,
                title=self.translate("activity"),
                border_style="cyan",
            )
        )
        return layout

    def _path_text(self, path, width=None):
        width = max(4, self.console.width - 4) if width is None else max(4, width)
        text = self.rich.Text(path, no_wrap=True, overflow="ellipsis")
        if text.cell_len > width:
            # Binary search a suffix that fits terminal cells, including wide Unicode.
            low, high = 0, len(path)
            while low < high:
                middle = (low + high) // 2
                if self.rich.Text(path[middle:]).cell_len > width - 3:
                    low = middle + 1
                else:
                    high = middle
            text = self.rich.Text("..." + path[low:], no_wrap=True, overflow="ellipsis")
        return text

    def _activity_text(self, kind, message):
        if kind == "converted":
            prefix = "\u2713 " + self.translate("success_converted") + ": "
            style = "green"
        else:
            prefix = self.translate(kind) + ": "
            style = "red" if kind == "error" else "yellow"
        line = self.rich.Text(prefix, style=style, no_wrap=True, overflow="ellipsis")
        line.append_text(self._path_text(message, self.console.width - 4 - line.cell_len))
        return line

    def _refresh(self):
        now = time.monotonic()
        if self.live is not None and now - self.last_refresh >= 0.125:
            self.last_refresh = now
            self.live.refresh()

    def show_start(self, input_path, output_path, music_format, bitrate, replace_mode):
        mode = self.translate("mode_replace" if replace_mode else "mode_copy")
        details = self.rich.Table.grid(padding=(0, 1))
        details.add_column(no_wrap=True)
        details.add_column(overflow="ellipsis", no_wrap=True)
        details.add_row(self.translate("source") + ":", self.rich.Text(input_path))
        details.add_row(self.translate("target") + ":", self.rich.Text(output_path))
        details.add_row(
            self.translate("format") + ":",
            f"{music_format} @ {bitrate} | {self.translate('mode')}: {mode}",
        )
        self.start_details = details
        self.live = self.rich.Live(
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
        table = self.rich.Table(title=title, border_style="cyan", show_header=False)
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
            self.console.print(self.rich.Text(counts, style="dim"))
        if log_file:
            self.console.print(
                self.rich.Text(f"{self.translate('log_file')}: {log_file}", style="dim")
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


class EventReporter:
    """Translate workflow events into console updates."""

    def __init__(self, reporter, translate, music_format):
        self.reporter, self.translate, self.music_format = reporter, translate, music_format

    def __call__(self, event):
        if event.kind == 'phase':
            key = {'other': 'phase_non_target', 'target': 'phase_target', 'sidecar': 'phase_sidecar'}[event.phase]
            self.reporter.start_phase(self.translate(key, format=self.music_format.upper()), event.total)
        elif event.kind == 'scan':
            self.reporter.scan_progress(event.directories)
        elif event.kind == 'started':
            self.reporter.file_started(event.path)
        elif event.kind == 'finished':
            self.reporter.file_finished(event.status, event.path)
        elif event.kind == 'workers':
            self.reporter.worker_progress(event.active_paths, event.workers, event.queued)
        elif event.kind == 'phase_finished':
            self.reporter.finish_phase()
