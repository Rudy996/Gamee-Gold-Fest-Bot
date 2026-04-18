from __future__ import annotations

import faulthandler
import sys
import threading
import traceback
from pathlib import Path


def _install_console_hooks() -> None:
    """
    Вывод в консоль CMD при сбоях:
    - построчная буферизация stderr (иначе буфер может не сброситься при аварийном выходе);
    - faulthandler — часть нативных падений и зависаний (не всё на Windows);
    - главный поток и остальные потоки Python;
    - сообщения Qt (Critical/Fatal) в stderr.
    """
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, OSError):
        pass
    try:
        sys.stderr.reconfigure(line_buffering=True)
    except (AttributeError, OSError):
        pass

    faulthandler.enable(all_threads=True)

    def _excepthook(exc_type, exc, tb) -> None:
        print(
            "--- Необработанное исключение (главный поток Python) ---",
            file=sys.stderr,
            flush=True,
        )
        traceback.print_exception(exc_type, exc, tb, file=sys.stderr)
        sys.stderr.flush()

    sys.excepthook = _excepthook

    def _thread_excepthook(args: threading.ExceptHookArgs) -> None:
        print(
            f"--- Необработанное исключение в потоке {args.thread.name!r} ---",
            file=sys.stderr,
            flush=True,
        )
        traceback.print_exception(
            args.exc_type,
            args.exc_value,
            args.exc_traceback,
            file=sys.stderr,
        )
        sys.stderr.flush()

    threading.excepthook = _thread_excepthook


def _install_qt_message_handler() -> None:
    """Предупреждения и фатальные сообщения Qt — в stderr (видно в той же CMD)."""
    from PySide6.QtCore import QtMsgType, qInstallMessageHandler

    def handler(mode, context, message: str) -> None:
        if mode < QtMsgType.QtWarningMsg:
            return
        try:
            name = mode.name
        except AttributeError:
            name = str(mode)
        loc = ""
        if context.file:
            loc = f" {context.file}:{context.line}"
        print(f"[Qt {name}]{loc} {message}", file=sys.stderr, flush=True)

    qInstallMessageHandler(handler)


def _preimport_heavy_libs() -> None:
    """Import httpx / httpcore *before* any QThread starts.

    httpcore uses lazy submodule imports that trigger bytecode compilation,
    which in turn can fire the cyclic garbage collector in a background
    thread.  If that GC finalises PySide6 C++ wrappers that the main
    (GUI) thread is using at the same moment, Qt crashes with an access
    violation.  Importing everything up front avoids the problem entirely.
    """
    import httpx          # noqa: F401  – pulls in httpcore
    import httpcore        # noqa: F401
    import httpcore._sync  # noqa: F401  – the subpackage that triggers late imports
    try:
        import httpcore._sync.connection  # noqa: F401
    except ImportError:
        pass
    try:
        import socksio  # noqa: F401 – optional SOCKS support
    except ImportError:
        pass


def main() -> None:
    _install_console_hooks()
    _preimport_heavy_libs()

    from gamee_bot.ui.main_window import run_app

    base = Path(__file__).resolve().parent
    config_path = base / "config.yaml"
    try:
        code = run_app(config_path, after_qapp=_install_qt_message_handler)
    except BaseException:
        print(
            "--- Исключение при запуске / выходе из приложения ---",
            file=sys.stderr,
            flush=True,
        )
        traceback.print_exc()
        sys.stderr.flush()
        code = 1
    sys.exit(code)


if __name__ == "__main__":
    main()
