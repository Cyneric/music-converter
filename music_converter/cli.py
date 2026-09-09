"""Command-line setup and presentation for a conversion run."""

import argparse
from datetime import datetime
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from .console import (Translator, TRANSLATIONS, NullReporter, ReporterLogHandler,
                      EventReporter, create_reporter, ensure_rich_available)
from .history import History
from .models import AUDIO_FORMATS, BITRATES, RunConfig
from .workflow import run

logger = logging.getLogger('music_converter')


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
    return "en"


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
        language = "en"
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


def validate_paths_and_parameters(config):
    if not os.path.isdir(config.input_path):
        raise ValueError('The input directory is invalid')
    if config.music_format not in AUDIO_FORMATS or config.bitrate not in BITRATES:
        raise ValueError('Invalid format or bitrate')
    if not config.replace_mode and os.path.realpath(config.input_path) == os.path.realpath(config.output_path):
        raise ValueError('Copy mode requires different input and output directories')
    Path(config.output_path).mkdir(parents=True, exist_ok=True)


def check_dependencies(translate, interactive):
    missing = [name for name in ('ffmpeg', 'ffprobe') if shutil.which(name) is None]
    if not missing:
        return True
    logger.error('Missing required executable(s): %s', ', '.join(missing))
    if not interactive:
        return False
    try:
        answer = input(translate('ffmpeg_missing_prompt')).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    if answer not in {'j', 'ja', 'y', 'yes'}:
        return False
    command = _ffmpeg_install_command()
    if command is None:
        return False
    result = subprocess.run(command)
    return result.returncode == 0 and all(shutil.which(name) for name in ('ffmpeg', 'ffprobe'))


def setup_logging(installation_dir, reporter):
    directory = Path(installation_dir) / 'logs'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ('convert_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.log')
    handler = logging.FileHandler(path, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    handlers = [handler, ReporterLogHandler(reporter)]
    previous = logger.level, logger.propagate
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for item in handlers:
        logger.addHandler(item)
    return str(path), handlers, previous


def main(arguments=None, *, installation_dir=None):
    arguments = list(sys.argv[1:] if arguments is None else arguments)
    installation_dir = Path(installation_dir) if installation_dir else Path(__file__).resolve().parent.parent
    headless = '--headless' in arguments
    translate = Translator(detect_language(arguments))
    if sys.version_info < (3, 11):
        if not headless:
            print(translate('python_required'), file=sys.stderr)
        return 1
    reporter = NullReporter()
    handlers = []
    previous = logger.level, logger.propagate
    try:
        try:
            config = parse_arguments(arguments)
        except CLIError as error:
            if headless:
                _, handlers, previous = setup_logging(installation_dir, reporter)
                logger.error('%s', error)
            else:
                print(translate('usage_error', message=str(error)), file=sys.stderr)
            return 1
        translate = Translator(config.language)
        if config.console_mode == 'rich' and not ensure_rich_available(translate):
            return 1
        reporter = create_reporter(config.console_mode, translate)
        log_file, handlers, previous = setup_logging(installation_dir, reporter)
        validate_paths_and_parameters(config)
        if not check_dependencies(translate, not headless and sys.stdin.isatty()):
            return 1
        logger.info('Starting conversion: %s', config)
        reporter.worker_progress((), config.workers, 0)
        reporter.show_start(config.input_path, config.output_path, config.music_format, config.bitrate, config.replace_mode)
        started = time.monotonic()
        with History(installation_dir) as history:
            result = run(config, history, emit=EventReporter(reporter, translate, config.music_format))
        elapsed = time.monotonic() - started
        logger.info('Runtime: %.1fs; conversions/min: %.1f', elapsed,
                    len(result.converted_files) * 60 / max(elapsed, 0.001))
        logger.info('Conversion summary: converted=%d correct=%d skipped=%d copied=%d failed=%d interrupted=%s',
                    len(result.converted_files), len(result.correct_files), len(result.skipped_files),
                    len(result.copied_files), len(result.failed_files), result.interrupted)
        reporter.show_summary(result, log_file)
        return 130 if result.interrupted else 2 if result.failed_files else 0
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        if handlers:
            logger.exception('Converter stopped: %s', error)
        elif not headless:
            print(translate('fatal_error', message=str(error)), file=sys.stderr)
        return 1
    finally:
        reporter.close()
        for handler in handlers:
            logger.removeHandler(handler)
            handler.close()
        logger.setLevel(previous[0])
        logger.propagate = previous[1]
