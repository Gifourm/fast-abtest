import logging
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

    @process_request.register_variant(traffic_percent=50, disable_threshold=0.3)
    def process_request_b():
        nonlocal error_count
        error_count += 1
        if error_count <= 4:
            raise ValueError("Simulated error")
        return "recovered"

    assert process_request._variants[0].is_active is True

    results = []
    for _ in range(100):
        try:
            results.append(process_request())
        except ValueError:
            pass

    assert process_request._variants[0].is_active is False


def test_enable_variant_reactivation():
    """Test that enable_variant reactivates a disabled variant"""
    error_count = 0

    @ab_test(metrics=[])
    def api_endpoint():
        return "default"

    @api_endpoint.register_variant(traffic_percent=70, disable_threshold=0.5)
    def api_endpoint_b():
        nonlocal error_count
        error_count += 1
        if error_count <= 2:
            raise RuntimeError("Temporary failure")
        return "premium"

    for _ in range(3):
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
