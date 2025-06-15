import logging
import threading
from random import seed
from unittest.mock import patch

import pytest

from fast_abtest import ab_test


logger = logging.getLogger(__name__)


@pytest.fixture
def reset_random():
    seed(42)


def test_variant_disabling_on_errors(reset_random):
    """Test that variant gets disabled when error threshold is exceeded"""
    error_count = 0

    @ab_test(metrics=[])
    def process_request():
        return "success"

    @process_request.register_variant(traffic_percent=80, disable_threshold=0.5)
    def process_request_b():
        nonlocal error_count
        error_count += 1
        if error_count >= 4:
            raise ValueError("Simulated error")
        return "recovered"

    assert process_request._variants[0].is_active is True

    for _ in range(100):
        try:
            process_request()
        except ValueError:
            pass

    assert process_request._variants[0].is_active is False, process_request._variants[0]


def test_enable_variant_reactivation():
    """Test that enable_variant reactivates a disabled variant"""
    error_count = 0

    @ab_test(metrics=[])
    def api_endpoint():
        return "default"

    @api_endpoint.register_variant(traffic_percent=70, disable_threshold=0.3)
    def api_endpoint_b():
        nonlocal error_count
        error_count += 1
        if error_count >= 2:
            raise RuntimeError("Temporary failure")
        return "premium"

    for _ in range(20):
        try:
            api_endpoint()
        except RuntimeError:
            pass

    assert api_endpoint._variants[0].is_active is False
    api_endpoint.enable_variant("api_endpoint_b")
    assert api_endpoint._variants[0].is_active is True


def test_threshold_edge_cases():
    """Test edge cases for error threshold"""
    with pytest.raises(ValueError, match="threshold must be between"):

        @ab_test(metrics=[])
        def func():
            pass

        @func.register_variant(traffic_percent=90, disable_threshold=1.1)
        def func_b(): ...

    with pytest.raises(ValueError, match="threshold must be between"):

        @ab_test(metrics=[])
        def sensitive_endpoint():
            return "ok"

        @sensitive_endpoint.register_variant(traffic_percent=50, disable_threshold=0.0)
        def sensitive_endpoint_b():
            raise ValueError("Critical error")


def test_thread_safety_for_threshold(reset_random) -> None:
    """Test disabling the thread-safe variant"""
    error_counter = 0
    call_counter = 0

    @ab_test(metrics=[])
    def thread_safe_endpoint():
        nonlocal error_counter, call_counter
        call_counter += 1
        if call_counter <= 15:
            error_counter += 1
            raise ValueError("Simulated error")
        return "success"

    @thread_safe_endpoint.register_variant(traffic_percent=70, disable_threshold=0.5)
    def variant_b():
        return thread_safe_endpoint()

    threads = []
    results: list[str] = []

    def worker():
        try:
            results.append(variant_b())
        except ValueError:
            pass

    for _ in range(20):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert not thread_safe_endpoint._variants[0].is_active
    assert 0.7 <= (error_counter / call_counter) <= 0.8


def test_concurrent_access_to_disabled_variant():
    """Test work with an already disabled option from a variety of threads"""

    @ab_test(metrics=[])
    def endpoint():
        raise ValueError("Error")

    @endpoint.register_variant(traffic_percent=50, disable_threshold=0.1)
    def variant_b():
        return endpoint()

    def worker():
        try:
            endpoint()
        except ValueError:
            pass

    for _ in range(20):
        try:
            endpoint()
        except ValueError:
            pass

    assert not endpoint._variants[0].is_active

    threads = []
    for _ in range(10):
        t = threading.Thread(target=lambda: worker())
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
    assert not endpoint._variants[0].is_active


def test_threshold_precision_with_threads(reset_random):
    """Test the accuracy of error counting in a multithreaded environment"""

    @ab_test(metrics=[])
    def precision_endpoint():
        return "ok"

    @precision_endpoint.register_variant(traffic_percent=80, disable_threshold=0.4)
    def variant_b():
        if threading.get_ident() % 3 == 0:
            raise RuntimeError("Thread error")
        return "variant"

    def worker():
        try:
            precision_endpoint()
        except RuntimeError:
            pass

    threads = []
    for _ in range(1000):
        t = threading.Thread(target=lambda: worker())
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert precision_endpoint._variants[0].is_active
    assert 0.3 <= (precision_endpoint._variants[0].error_count / precision_endpoint._variants[0].call_count) <= 0.4
