import logging
import threading
from typing import List

import pytest

from truss.util.log_utils import LogInterceptor


def setup_root_logger():
    root = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.handlers = [handler]
    return root, handler


@pytest.fixture
def log_interceptor():
    interceptor = LogInterceptor()
    root, _ = setup_root_logger()
    LogInterceptor._thread_local.handlers = []
    yield interceptor
    # Cleanup
    root.handlers = []


def test_log_interceptor_emit():
    interceptor = LogInterceptor()
    interceptor._thread_local.handlers = [interceptor]
    interceptor._formatter = logging.Formatter("%(message)s")

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    interceptor.emit(record)
    logs = interceptor.get_logs()
    assert len(logs) == 1
    assert "Test message" in logs[0]


def test_log_interceptor_emit_no_formatter():
    interceptor = LogInterceptor()
    interceptor._thread_local.handlers = [interceptor]

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    interceptor.emit(record)
    logs = interceptor.get_logs()
    assert len(logs) == 1
    assert "Test message" in logs[0]


def test_log_interceptor_emit_no_thread_local():
    interceptor = LogInterceptor()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    interceptor.emit(record)
    assert len(interceptor.get_logs()) == 0


def test_log_interceptor_get_logs_empty():
    interceptor = LogInterceptor()
    assert len(interceptor.get_logs()) == 0


def test_log_interceptor_thread_isolation():
    def thread_func(
        messages: List[str], results: List[str], formatter: logging.Formatter
    ) -> None:
        interceptor = LogInterceptor()
        try:
            interceptor._thread_local.handlers = [interceptor]
            interceptor._formatter = formatter
            for msg in messages:
                record = logging.LogRecord(
                    name="test",
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg=msg,
                    args=(),
                    exc_info=None,
                )
                interceptor.emit(record)
            results.extend(interceptor.get_logs())
        finally:
            LogInterceptor._thread_local.handlers = []

    formatter = logging.Formatter("%(message)s")
    thread1_msgs = ["Thread 1 Message 1", "Thread 1 Message 2"]
    thread2_msgs = ["Thread 2 Message 1", "Thread 2 Message 2"]

    thread1_results: List[str] = []
    thread2_results: List[str] = []

    t1 = threading.Thread(
        target=thread_func, args=(thread1_msgs, thread1_results, formatter)
    )
    t2 = threading.Thread(
        target=thread_func, args=(thread2_msgs, thread2_results, formatter)
    )

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(thread1_results) == 2
    assert thread1_msgs[0] in thread1_results[0]
    assert thread1_msgs[1] in thread1_results[1]

    assert len(thread2_results) == 2
    assert thread2_msgs[0] in thread2_results[0]
    assert thread2_msgs[1] in thread2_results[1]
