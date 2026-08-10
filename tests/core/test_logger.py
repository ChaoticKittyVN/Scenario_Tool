import contextlib
import io
import logging
import multiprocessing
from pathlib import Path

from core.logger import ColoredFormatter


def _write_logs(log_dir, process_id, ready_queue, release_event):
    from core.logger import ScenarioToolLogger

    ScenarioToolLogger.reset()
    ScenarioToolLogger.LOG_DIR = Path(log_dir)
    ScenarioToolLogger.MAX_BYTES = 1024
    ScenarioToolLogger.BACKUP_COUNT = 50

    errors = io.StringIO()
    try:
        with contextlib.redirect_stderr(errors):
            logger = ScenarioToolLogger.get_logger()
            for handler in logger.handlers:
                if type(handler) is logging.StreamHandler:
                    handler.setLevel(logging.CRITICAL + 1)

            for message_id in range(40):
                logger.info(
                    "process-%s-message-%s %s",
                    process_id,
                    message_id,
                    "x" * 200,
                )
            ScenarioToolLogger.reset()
        ready_queue.put((process_id, errors.getvalue(), ""))
    except Exception as exc:
        ready_queue.put((process_id, errors.getvalue(), repr(exc)))
    finally:
        release_event.wait(timeout=30)


def test_colored_formatter_does_not_modify_original_record():
    record = logging.LogRecord(
        "scenario_tool",
        logging.INFO,
        __file__,
        1,
        "message",
        (),
        None,
    )

    console_text = ColoredFormatter("%(levelname)s %(message)s").format(record)
    file_text = logging.Formatter("%(levelname)s %(message)s").format(record)

    assert "\033[" in console_text
    assert record.levelname == "INFO"
    assert file_text == "INFO message"


def test_concurrent_log_rotation_and_reset_release_files(tmp_path):
    context = multiprocessing.get_context("spawn")
    ready_queue = context.Queue()
    release_event = context.Event()
    processes = [
        context.Process(
            target=_write_logs,
            args=(str(tmp_path), process_id, ready_queue, release_event),
        )
        for process_id in range(2)
    ]

    try:
        for process in processes:
            process.start()

        worker_results = sorted(
            ready_queue.get(timeout=30) for _ in processes
        )
        assert worker_results == [(0, "", ""), (1, "", "")]

        log_files = sorted(tmp_path.glob("scenario_tool.log*"))
        assert tmp_path / "scenario_tool.log" in log_files
        assert any(path.name != "scenario_tool.log" for path in log_files)
        assert (tmp_path / ".__scenario_tool.lock").exists()

        log_text = "".join(
            path.read_text(encoding="utf-8") for path in log_files
        )
        for process_id in range(2):
            for message_id in range(40):
                assert f"process-{process_id}-message-{message_id}" in log_text

        # Workers are still alive. Deletion succeeds only if reset() released
        # both the log stream and the concurrent handler's lock stream.
        for path in tmp_path.iterdir():
            path.unlink()
        assert list(tmp_path.iterdir()) == []
    finally:
        release_event.set()
        for process in processes:
            process.join(timeout=30)
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)

    assert all(process.exitcode == 0 for process in processes)
