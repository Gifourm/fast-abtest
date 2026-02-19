from dataclasses import dataclass
from typing import Optional, List
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, Depends, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel

from fast_abtest import ab_test, enable_dependency_support
from fast_abtest.interface import Metric


class MockExporter:
    def __init__(self, *args, **kwargs):
        self.metrics = []
        self.func_name = kwargs.get("func_name", "")
        self.port = kwargs.get("port", 8000)

    def record(self, label, value):
        self.metrics.append((label, value))


class MockMetric(Metric):
    def __init__(self, exporter):
        self.exporter = exporter
        self.calls = []

    def record(self, *args, **kwargs):
        self.calls.append((args, kwargs))


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def mock_exporter():
    return MockExporter


@pytest.fixture
def test_app():
    app = FastAPI()
    enable_dependency_support(app)
    return app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


class UserProfile(BaseModel):
    user_id: int
    email: str
    preferences: Optional[List[str]] = None


@dataclass
class UserData:
    id: int
    name: str
    tags: List[str]


class NestedModel(BaseModel):
    user_id: int
    action: str
    metadata: Optional[str] = None


class ContainerModel(BaseModel):
    item_id: int
    user: UserProfile
    timestamp: float


class TestWithoutConsistencyKey:
    """Tests for behavior when consistency_key is not provided"""

    def test_random_choice_without_key(self, mock_logger, mock_exporter):
        """Without key, different values should get random distribution"""
        results = {"A": 0, "B": 0}

        @ab_test(metrics=[], exporter=mock_exporter, logger=mock_logger)
        def process_data(user_id: int) -> str:
            results["A"] += 1
            return "A"

        @process_data.register_variant(traffic_percent=50)
        def process_data_b(user_id: int) -> str:
            results["B"] += 1
            return "B"

        for i in range(1000):
            process_data(i)

        assert results["A"] > 0
        assert results["B"] > 0
        assert results["A"] + results["B"] == 1000

    def test_same_value_different_choices_without_key(self, mock_logger, mock_exporter):
        """Without key, the same value can get different variants"""
        results = {"A": 0, "B": 0}

        @ab_test(metrics=[], exporter=mock_exporter, logger=mock_logger)
        def get_recommendations(user_id: int) -> str:
            results["A"] += 1
            return "A"

        @get_recommendations.register_variant(traffic_percent=50)
        def get_recommendations_b(user_id: int) -> str:
            results["B"] += 1
            return "B"

        for _ in range(100):
            get_recommendations(42)

        assert results["A"] > 0
        assert results["B"] > 0
        assert results["A"] + results["B"] == 100


class TestConsistencyKeyPrimitives:
    """Tests for consistency_key with primitive types"""

    def test_consistency_with_int_key(self, mock_logger, mock_exporter):
        """Integer key should provide consistent variant selection"""
        results = {}

        @ab_test(metrics=[], exporter=mock_exporter, logger=mock_logger, consistency_key="user_id")
        def get_variant(user_id: int) -> str:
            variant = f"variant_{user_id}"
            results[user_id] = variant
            return variant

        @get_variant.register_variant(traffic_percent=50)
        def get_variant_b(user_id: int) -> str:
            variant = f"variant_b_{user_id}"
            results[user_id] = variant
            return variant

        first_result = get_variant(42)
        for _ in range(10):
            result = get_variant(42)
            assert result == first_result

        results_set = {get_variant(i) for i in range(10)}
        assert len(results_set) > 1

    def test_consistency_with_str_key(self, mock_logger, mock_exporter):
        """String key should provide consistent variant selection"""
        results = {}

        @ab_test(metrics=[], exporter=mock_exporter, logger=mock_logger, consistency_key="username")
        def get_user_variant(username: str) -> str:
            results[username] = results.get(username, 0) + 1
            return "A"

        @get_user_variant.register_variant(traffic_percent=50)
        def get_user_variant_b(username: str) -> str:
            results[username] = results.get(username, 0) + 1
            return "B"

        test_users = ["alice", "bob", "charlie"]
        first_results = {user: get_user_variant(user) for user in test_users}

        for _ in range(10):
            for user in test_users:
                result = get_user_variant(user)
                assert result == first_results[user]

    def test_consistency_with_multiple_args(self, mock_logger, mock_exporter):
        """Key can be one of multiple arguments"""

        @ab_test(metrics=[], exporter=mock_exporter, logger=mock_logger, consistency_key="user_id")
        def process(user_id: int, action: str, value: float) -> str:
            return "A"

        @process.register_variant(traffic_percent=50)
        def process_b(user_id: int, action: str, value: float) -> str:
            return "B"

        first_result = process(42, "login", 1.0)
        assert process(42, "logout", 2.0) == first_result
        assert process(42, "purchase", 3.5) == first_result
        assert process(42, "login", 1.0) == first_result


class TestConsistencyKeyComplexTypes:
    """Tests for consistency_key with complex data types"""

    def test_pydantic_model_field_key(self, mock_logger, mock_exporter):
        """Key can be a field of a Pydantic model"""

        @ab_test(metrics=[], exporter=mock_exporter, logger=mock_logger, consistency_key="user_id")
        def process_user(user: UserProfile) -> str:
            return "A"

        @process_user.register_variant(traffic_percent=50)
        def process_user_b(user: UserProfile) -> str:
            return "B"

        user1 = UserProfile(user_id=42, email="test@test.com")
        user2 = UserProfile(user_id=42, email="different@test.com", preferences=["dark"])
        user3 = UserProfile(user_id=43, email="other@test.com")

        first_result = process_user(user1)
        assert process_user(user2) == first_result

        result3 = process_user(user3)
        assert result3 in ("A", "B")

    def test_dataclass_field_key(self, mock_logger, mock_exporter):
        """Key can be a field of a dataclass"""

        @ab_test(metrics=[], exporter=mock_exporter, logger=mock_logger, consistency_key="id")
        def process_data(user: UserData) -> str:
            return "A"

        @process_data.register_variant(traffic_percent=50)
        def process_data_b(user: UserData) -> str:
            return "B"

        user1 = UserData(id=42, name="Alice", tags=["admin"])
        user2 = UserData(id=42, name="Bob", tags=["user"])
        user3 = UserData(id=43, name="Charlie", tags=[])

        first_result = process_data(user1)
        assert process_data(user2) == first_result

        result3 = process_data(user3)
        assert result3 in ("A", "B")

    def test_nested_model_field_key(self, mock_logger, mock_exporter):
        """Key can be a field in a nested model structure"""

        @ab_test(metrics=[], exporter=mock_exporter, logger=mock_logger, consistency_key="user_id")
        def process_container(data: ContainerModel) -> str:
            return "A"

        @process_container.register_variant(traffic_percent=50)
        def process_container_b(data: ContainerModel) -> str:
            return "B"

        user1 = UserProfile(user_id=42, email="alice@test.com")
        user2 = UserProfile(user_id=42, email="alice_updated@test.com", preferences=["dark"])
        user3 = UserProfile(user_id=43, email="bob@test.com")

        container1 = ContainerModel(item_id=1, user=user1, timestamp=1000.0)
        container2 = ContainerModel(item_id=2, user=user2, timestamp=2000.0)
        container3 = ContainerModel(item_id=3, user=user3, timestamp=3000.0)

        first_result = process_container(container1)
        assert process_container(container2) == first_result

        result3 = process_container(container3)
        assert result3 in ("A", "B")

    def test_nested_optional_field_key(self, mock_logger, mock_exporter):
        """Key can be an optional field in a nested structure"""

        class DeepModel(BaseModel):
            user_id: Optional[int] = None
            data: Optional[str] = None

        class WrapperModel(BaseModel):
            content: DeepModel
            metadata: str

        @ab_test(metrics=[], exporter=mock_exporter, logger=mock_logger, consistency_key="user_id")
        def process_deep(data: WrapperModel) -> str:
            return "A"

        @process_deep.register_variant(traffic_percent=50)
        def process_deep_b(data: WrapperModel) -> str:
            return "B"

        deep1 = DeepModel(user_id=42, data="test")
        deep2 = DeepModel(user_id=42, data="other")
        deep3 = DeepModel(user_id=None, data="test")

        wrapper1 = WrapperModel(content=deep1, metadata="first")
        wrapper2 = WrapperModel(content=deep2, metadata="second")
        wrapper3 = WrapperModel(content=deep3, metadata="third")

        first_result = process_deep(wrapper1)
        assert process_deep(wrapper2) == first_result

        result3 = process_deep(wrapper3)
        assert result3 in ("A", "B")


class TestConsistencyKeyFastAPI:
    """Tests for consistency_key in FastAPI applications"""

    def test_fastapi_path_param_key(self, client, test_app):
        """Test consistency_key with path parameter"""

        @test_app.get("/users/{user_id}")
        @ab_test(metrics=[], consistency_key="user_id")
        def get_user(user_id: int) -> dict:
            return {"variant": "A", "user_id": user_id}

        @get_user.register_variant(traffic_percent=50)
        def get_user_b(user_id: int) -> dict:
            return {"variant": "B", "user_id": user_id}

        first_response = client.get("/users/42")
        for _ in range(10):
            response = client.get("/users/42")
            assert response.json()["variant"] == first_response.json()["variant"]

        responses = {client.get(f"/users/{i}").json()["variant"] for i in range(10)}
        assert len(responses) > 1

    def test_fastapi_query_param_key(self, client, test_app):
        """Test consistency_key with query parameter"""

        @test_app.get("/search")
        @ab_test(metrics=[], consistency_key="session_id")
        def search(q: str, session_id: str) -> dict:
            return {"variant": "A", "query": q}

        @search.register_variant(traffic_percent=50)
        def search_b(q: str, session_id: str) -> dict:
            return {"variant": "B", "query": q}

        first_response = client.get("/search?q=test&session_id=abc123")
        for _ in range(5):
            response = client.get("/search?q=other&session_id=abc123")
            assert response.json()["variant"] == first_response.json()["variant"]

        response2 = client.get("/search?q=test&session_id=xyz789")
        assert response2.json()["variant"] in ("A", "B")

    def test_fastapi_with_dependency_key(self, client, test_app):
        """Test consistency_key with FastAPI dependencies"""

        async def get_user_id(request: Request) -> int:
            return int(request.headers.get("X-User-ID", "0"))

        @test_app.get("/protected")
        @ab_test(metrics=[], consistency_key="user_id")
        async def protected_endpoint(user_id: int = Depends(get_user_id)) -> dict:
            return {"variant": "A", "user_id": user_id}

        @protected_endpoint.register_variant(traffic_percent=50)
        async def protected_endpoint_b(user_id: int = Depends(get_user_id)) -> dict:
            return {"variant": "B", "user_id": user_id}

        headers = {"X-User-ID": "42"}
        first_response = client.get("/protected", headers=headers)
        for _ in range(5):
            response = client.get("/protected", headers=headers)
            assert response.json()["variant"] == first_response.json()["variant"]

        other_response = client.get("/protected", headers={"X-User-ID": "99"})
        assert other_response.json()["variant"] in ("A", "B")

    def test_fastapi_pydantic_body_key(self, client, test_app):
        """Test consistency_key with Pydantic model in request body"""

        @test_app.post("/process")
        @ab_test(metrics=[], consistency_key="user_id")
        def process_user(user: UserProfile) -> dict:
            return {"variant": "A", "received_id": user.user_id}

        @process_user.register_variant(traffic_percent=50)
        def process_user_b(user: UserProfile) -> dict:
            return {"variant": "B", "received_id": user.user_id}

        user1 = UserProfile(user_id=42, email="alice@test.com")
        user2 = UserProfile(user_id=42, email="alice_updated@test.com", preferences=["dark"])
        user3 = UserProfile(user_id=43, email="bob@test.com")

        first_response = client.post("/process", json=user1.model_dump())
        second_response = client.post("/process", json=user2.model_dump())
        assert second_response.json()["variant"] == first_response.json()["variant"]

        third_response = client.post("/process", json=user3.model_dump())
        assert third_response.json()["variant"] in ("A", "B")

    def test_fastapi_nested_pydantic_key(self, client, test_app):
        """Test consistency_key with nested Pydantic model"""

        @test_app.post("/container")
        @ab_test(metrics=[], consistency_key="user_id")
        def process_container(container: ContainerModel) -> dict:
            return {"variant": "A"}

        @process_container.register_variant(traffic_percent=50)
        def process_container_b(container: ContainerModel) -> dict:
            return {"variant": "B"}

        user1 = UserProfile(user_id=42, email="alice@test.com")
        user2 = UserProfile(user_id=42, email="alice_updated@test.com")
        user3 = UserProfile(user_id=43, email="bob@test.com")

        container1 = ContainerModel(item_id=1, user=user1, timestamp=1000.0)
        container2 = ContainerModel(item_id=2, user=user2, timestamp=2000.0)
        container3 = ContainerModel(item_id=3, user=user3, timestamp=3000.0)

        first_response = client.post("/container", json=container1.model_dump())
        second_response = client.post("/container", json=container2.model_dump())
        assert second_response.json()["variant"] == first_response.json()["variant"]

        third_response = client.post("/container", json=container3.model_dump())
        assert third_response.json()["variant"] in ("A", "B")


class TestHashFunction:
    """Tests for the hashing mechanism used with consistency_key"""

    def test_hash_consistency(self, mock_logger, mock_exporter):
        """Identical objects should produce the same hash result"""

        @ab_test(metrics=[], exporter=mock_exporter, logger=mock_logger, consistency_key="data")
        def hash_test(data: UserProfile) -> str:
            return "A"

        @hash_test.register_variant(traffic_percent=50)
        def hash_test_b(data: UserProfile) -> str:
            return "B"

        user1 = UserProfile(user_id=42, email="test@test.com", preferences=["a", "b"])
        user2 = UserProfile(user_id=42, email="test@test.com", preferences=["a", "b"])

        first_result = hash_test(user1)
        assert hash_test(user2) == first_result

    def test_different_objects_different_hash(self, mock_logger, mock_exporter):
        """Different objects may produce different hash results"""

        @ab_test(metrics=[], exporter=mock_exporter, logger=mock_logger, consistency_key="data")
        def hash_test(data: UserProfile) -> str:
            return "A"

        @hash_test.register_variant(traffic_percent=50)
        def hash_test_b(data: UserProfile) -> str:
            return "B"

        user1 = UserProfile(user_id=42, email="alice@test.com")
        user2 = UserProfile(user_id=43, email="bob@test.com")

        results = {hash_test(user1), hash_test(user2)}
        assert len(results) in (1, 2)

    def test_unpicklable_object_fallback(self, mock_logger, mock_exporter):
        """For objects that cannot be pickled, hash() is used as fallback"""

        class Unpicklable:
            def __init__(self, value):
                self.value = value

            def __hash__(self):
                return hash(self.value)

        @ab_test(metrics=[], exporter=mock_exporter, logger=mock_logger, consistency_key="obj")
        def test_unpicklable(obj: Unpicklable) -> str:
            return "A"

        @test_unpicklable.register_variant(traffic_percent=50)
        def test_unpicklable_b(obj: Unpicklable) -> str:
            return "B"

        obj1 = Unpicklable(42)
        obj2 = Unpicklable(42)
        obj3 = Unpicklable(43)

        first_result = test_unpicklable(obj1)
        assert test_unpicklable(obj2) == first_result

        result3 = test_unpicklable(obj3)
        assert result3 in ("A", "B")


class TestConsistencyKeyEdgeCases:
    """Tests for edge cases with consistency_key"""

    def test_key_not_found_error(self, mock_logger, mock_exporter):
        """Non-existent key should raise an error"""

        with pytest.raises(ValueError, match="unreachable"):

            @ab_test(metrics=[], exporter=mock_exporter, logger=mock_logger, consistency_key="nonexistent_field")
            def test_func(user_id: int) -> str:
                return "A"

    def test_key_in_optional_default_param(self, mock_logger, mock_exporter):
        """Key can be in a parameter with default value"""

        @ab_test(metrics=[], exporter=mock_exporter, logger=mock_logger, consistency_key="session_id")
        def test_func(user_id: int, session_id: str = "default") -> str:
            return "A"

        @test_func.register_variant(traffic_percent=50)
        def test_func_b(user_id: int, session_id: str = "default") -> str:
            return "B"

        first_result = test_func(42)
        for _ in range(5):
            result = test_func(42)
            assert result == first_result

        result_with_session = test_func(42, session_id="custom")
        assert result_with_session in ("A", "B")

    def test_key_in_kwargs_only(self, mock_logger, mock_exporter):
        """Key can be passed only as a keyword argument"""

        @ab_test(metrics=[], exporter=mock_exporter, logger=mock_logger, consistency_key="session_id")
        def test_func(user_id: int, *, session_id: str) -> str:
            return "A"

        @test_func.register_variant(traffic_percent=50)
        def test_func_b(user_id: int, *, session_id: str) -> str:
            return "B"

        first_result = test_func(42, session_id="abc123")
        assert test_func(99, session_id="abc123") == first_result

        result2 = test_func(42, session_id="xyz789")
        assert result2 in ("A", "B")

    def test_key_in_dataclass_with_default(self, mock_logger, mock_exporter):
        """Key can be in a dataclass field with default value"""

        @dataclass
        class Config:
            user_id: int
            settings: str = "default"

        @ab_test(metrics=[], exporter=mock_exporter, logger=mock_logger, consistency_key="user_id")
        def test_func(config: Config) -> str:
            return "A"

        @test_func.register_variant(traffic_percent=50)
        def test_func_b(config: Config) -> str:
            return "B"

        config1 = Config(user_id=42)
        config2 = Config(user_id=42, settings="custom")
        config3 = Config(user_id=43)

        first_result = test_func(config1)
        assert test_func(config2) == first_result

        result3 = test_func(config3)
        assert result3 in ("A", "B")

    def test_multilevel_nesting_with_optional(self, mock_logger, mock_exporter):
        """Key can be deeply nested with optional fields"""

        class Level2(BaseModel):
            user_id: Optional[int] = None
            data: str

        class Level1(BaseModel):
            level2: Level2
            meta: str

        class Root(BaseModel):
            level1: Level1
            root_id: int

        @ab_test(metrics=[], exporter=mock_exporter, logger=mock_logger, consistency_key="user_id")
        def test_func(root: Root) -> str:
            return "A"

        @test_func.register_variant(traffic_percent=50)
        def test_func_b(root: Root) -> str:
            return "B"

        level2_a = Level2(user_id=42, data="test")
        level2_b = Level2(user_id=42, data="other")
        level2_c = Level2(user_id=None, data="test")

        level1_a = Level1(level2=level2_a, meta="first")
        level1_b = Level1(level2=level2_b, meta="second")
        level1_c = Level1(level2=level2_c, meta="third")

        root_a = Root(level1=level1_a, root_id=1)
        root_b = Root(level1=level1_b, root_id=2)
        root_c = Root(level1=level1_c, root_id=3)

        first_result = test_func(root_a)
        assert test_func(root_b) == first_result

        result_c = test_func(root_c)
        assert result_c in ("A", "B")
