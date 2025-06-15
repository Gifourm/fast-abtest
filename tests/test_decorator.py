from random import seed

import pytest

from fast_abtest import ab_test


@pytest.fixture
def reset_random():
    seed(42)


def test_traffic_distribution(reset_random) -> None:
    """Test traffic distribution of each scenario of the A/B test"""

    @ab_test(metrics=[])
    def process_data(x: int) -> int:
        return x * 2

    @process_data.register_variant(traffic_percent=30)
    def process_data_b(x: int) -> int:
        return x * 3

    results = [process_data(5) for _ in range(1000)]
    assert 680 <= results.count(10) <= 720
    assert 280 <= results.count(15) <= 320


def test_traffic_distribution_validation() -> None:
    """Test traffic percentage validation"""
    with pytest.raises(ValueError, match="must be between 1 and 99"):

        @ab_test(metrics=[])
        def func():
            pass

        @func.register_variant(traffic_percent=0)
        def func_b():
            pass

    with pytest.raises(ValueError, match="exceeds 100"):

        @ab_test(metrics=[])
        def func():
            pass

        @func.register_variant(traffic_percent=50)
        def func_b():
            pass

        @func.register_variant(traffic_percent=60)
        def func_c():
            pass


def test_multiple_variants(reset_random) -> None:
    """Test A/B/C testing with multiple variants"""

    @ab_test(metrics=[])
    def recommend(user_id: int) -> str:
        return "A"  # Base variant

    @recommend.register_variant(traffic_percent=20)
    def recommend_b(user_id: int) -> str:
        return "B"  # 20%

    @recommend.register_variant(traffic_percent=30)
    def recommend_c(user_id: int) -> str:
        return "C"  # 30%

    results = [recommend(1) for _ in range(1000)]
    assert set(results) == {"A", "B", "C"}
    assert 480 <= results.count("A") <= 520
    assert 180 <= results.count("B") <= 220
    assert 280 <= results.count("C") <= 320


def test_type_safety() -> None:
    """Test that type hints are enforced"""

    @ab_test(metrics=[])
    def typed_func(x: int) -> float:
        return float(x)

    result: float = typed_func(5)
    assert result == 5.0

    with pytest.raises(ValueError):
        typed_func("string")  # type: ignore


def test_variant_type_consistency() -> None:
    """Test that variants maintain type consistency"""

    @ab_test(metrics=[])
    def base_func(x: int) -> float:
        return float(x)

    @base_func.register_variant(traffic_percent=20)
    def variant_func(x: int) -> float:
        return float(x**2)

    with pytest.raises(TypeError):

        @base_func.register_variant(traffic_percent=20)
        def bad_variant(x: str) -> float:  # type: ignore
            return 0.0


def test_decorator_returns_abtestfunction() -> None:
    """Test the decorator returns proper ABTestFunction type"""

    @ab_test(metrics=[])
    def sample() -> int:
        return 42

    assert hasattr(sample, "register_variant")
    assert callable(sample.register_variant)
    assert sample() == 42
