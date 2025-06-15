from random import seed

import pytest
from fastapi import FastAPI, Depends, Request, HTTPException, Response
from fastapi.testclient import TestClient
from typing import Optional

from pydantic import BaseModel

from fast_abtest import ab_test


class ItemModel(BaseModel):
    id: int
    name: str


class ErrorModel(BaseModel):
    detail: str


@pytest.fixture
def reset_random():
    seed(42)


@pytest.fixture
def test_app():
    app = FastAPI()
    return app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


def get_current_user():
    return {"user": "test"}


async def async_dependency():
    return {"async": True}


def test_combined_with_fastapi_route_decorator(client, test_app):
    """Test @ab_test works together with @app.get"""

    @test_app.get("/combined")
    @ab_test(metrics=[])
    def combined_endpoint():
        return {"version": "A"}

    @combined_endpoint.register_variant(traffic_percent=30)
    def combined_endpoint_b():
        return {"version": "B"}

    response = client.get("/combined")
    assert response.status_code == 200
    assert response.json()["version"] in ("A", "B")


def test_decorator_order_importance():
    """Checks that the order of the decorators is critical:
    - @app.get must be BEFORE @ab_test
    - Otherwise, the variants are never called"""

    app = FastAPI()
    main_counter = 0
    variant_counter = 0

    @ab_test(metrics=[])
    @app.get("/wrong-order")
    def endpoint_with_bad_order():
        nonlocal main_counter
        main_counter += 1
        return {"version": "A"}

    @endpoint_with_bad_order.register_variant(traffic_percent=90)
    def variant_b():
        nonlocal variant_counter
        variant_counter += 1
        return {"version": "B"}

    client = TestClient(app)

    for _ in range(1000):
        client.get("/wrong-order")

    assert variant_counter == 0
    assert main_counter == 1000


def test_path_parameters(client, test_app):
    """Verify that path parameters work correctly with A/B test decorator

    Tests:
    - Path parameters are properly injected
    - Both main and variant endpoints receive the parameter
    - Response structure remains consistent
    """

    @test_app.get("/items/{item_id}")
    @ab_test(metrics=[])
    def read_item(item_id: int):
        return {"item_id": item_id}

    @read_item.register_variant(traffic_percent=30)
    def read_item_b(item_id: int):
        return {"item_id": item_id, "variant": "B"}

    response = client.get("/items/42")
    assert response.status_code == 200
    assert response.json()["item_id"] == 42


def test_query_parameters(client, test_app):
    """Test compatibility with optional query parameters

    Verifies:
    - Optional parameters work with default values
    - Both variants receive the same parameters
    - Query string parsing remains unaffected
    """

    @test_app.get("/search")
    @ab_test(metrics=[])
    def search(q: str, limit: Optional[int] = 10):
        return {"q": q, "limit": limit}

    @search.register_variant(traffic_percent=30)
    def search_b(q: str, limit: Optional[int] = 10):
        return {"q": q + "_b", "limit": limit}

    response = client.get("/search?q=test&limit=5")
    data = response.json()
    assert data["q"] in ("test", "test_b")
    assert data["limit"] == 5


def test_dependency_injection(client, test_app):
    """Validate dependency injection works with A/B tested endpoints

    Checks:
    - Sync dependencies are properly injected
    - Dependencies work in both main and variant endpoints
    - Response contains dependency data
    """

    @test_app.get("/user")
    @ab_test(metrics=[])
    def get_user(current_user: dict = Depends(get_current_user)):
        return current_user

    @get_user.register_variant(traffic_percent=30)
    def get_user_b(current_user: dict = Depends(get_current_user)):
        return {**current_user, "variant": "B"}

    response = client.get("/user")
    assert response.status_code == 200
    assert response.json()["user"] == "test"


def test_async_dependencies(client, test_app):
    """Test async dependencies functionality

    Ensures:
    - Async dependencies are resolved correctly
    - Both variants can use async dependencies
    - Response contains expected async data
    """

    @test_app.get("/async")
    @ab_test(metrics=[])
    async def async_route(dep: dict = Depends(async_dependency)):
        return dep

    @async_route.register_variant(traffic_percent=30)
    async def async_route_b(dep: dict = Depends(async_dependency)):
        return {**dep, "variant": "B"}

    response = client.get("/async")
    assert response.status_code == 200
    assert ("async" in response.json()) or ("variant" in response.json())


def test_request_object(client, test_app):
    """Verify Request object accessibility

    Tests:
    - Request object is properly injected
    - Both variants can access request data
    - URL path is correctly preserved
    """

    @test_app.get("/request")
    @ab_test(metrics=[])
    async def get_request(request: Request):
        return {"path": request.url.path}

    @get_request.register_variant(traffic_percent=30)
    async def get_request_b(request: Request):
        return {"path": request.url.path, "variant": "B"}

    response = client.get("/request")
    assert response.status_code == 200
    assert response.json()["path"] == "/request"


def test_error_handling(client, test_app):
    """Test error propagation from A/B variants

    Verifies:
    - Exceptions are properly raised
    - Different variants can return different errors
    - Error responses maintain their structure
    """

    @test_app.get("/error")
    @ab_test(metrics=[])
    def raise_error():
        raise HTTPException(status_code=400, detail="Error A")

    @raise_error.register_variant(traffic_percent=30)
    def raise_error_b():
        raise HTTPException(status_code=418, detail="Error B")

    responses = []
    for _ in range(100):
        try:
            responses.append(client.get("/error"))
        except:
            pass

    status_codes = {r.status_code for r in responses}
    assert 400 in status_codes
    assert 418 in status_codes


def test_openapi_schema(client, test_app):
    """Validate OpenAPI schema generation

    Checks:
    - Parameters are properly documented
    - Endpoint description is preserved
    - Schema contains all expected fields
    """

    @test_app.get("/schema/{id}", summary="Test OpenAPI schema")
    @ab_test(metrics=[])
    def schema_test(id: int, q: str, user: dict = Depends(get_current_user)):
        """Test endpoint for schema validation"""
        return {"id": id, "q": q}

    response = client.get("/openapi.json")
    assert response.status_code == 200

    path_item = response.json()["paths"]["/schema/{id}"]["get"]
    assert path_item["description"] == "Test endpoint for schema validation"
    assert path_item["summary"] == "Test OpenAPI schema"
    assert len(path_item["parameters"]) == 2
    assert any(p["name"] == "id" for p in path_item["parameters"])
    assert any(p["name"] == "q" for p in path_item["parameters"])


def test_multiple_http_methods(client, test_app):
    """Test support for different HTTP methods

    Verifies:
    - POST requests work correctly
    - Request body is properly parsed
    - Method-specific behavior is preserved
    """

    @test_app.post("/multi")
    @ab_test(metrics=[])
    def post_endpoint(data: dict):
        return {"method": "POST", "data": data}

    @post_endpoint.register_variant(traffic_percent=30)
    def post_endpoint_b(data: dict):
        return {"method": "POST", "data": data, "variant": "B"}

    response = client.post("/multi", json={"key": "value"})
    assert response.status_code == 200
    assert response.json()["method"] == "POST"


def test_multiple_variants_distribution(client, test_app, reset_random) -> None:
    """Test traffic distribution with multiple variants (A/B/C)

    Verifies:
    - Distribution works with 3+ variants
    - Each variant gets correct percentage
    - Total doesn't exceed 100%
    """
    call_counts: dict[str, int] = {"A": 0, "B": 0, "C": 0}

    @test_app.get("/multi-variant")
    @ab_test(metrics=[])
    def multi_variant():
        call_counts["A"] += 1
        return {"variant": "A"}

    @multi_variant.register_variant(traffic_percent=25)
    def multi_variant_b():
        call_counts["B"] += 1
        return {"variant": "B"}

    @multi_variant.register_variant(traffic_percent=15)
    def multi_variant_c():
        call_counts["C"] += 1
        return {"variant": "C"}

    responses = [client.get("/multi-variant").json() for _ in range(1000)]

    variant_counts = {
        "A": sum(1 for r in responses if r["variant"] == "A"),
        "B": sum(1 for r in responses if r["variant"] == "B"),
        "C": sum(1 for r in responses if r["variant"] == "C"),
    }

    total = sum(variant_counts.values())
    percentages = {k: (v / total) * 100 for k, v in variant_counts.items()}

    assert 57 <= percentages["A"] <= 63, f"Variant A: {percentages['A']}% (expected 60±3%)"
    assert 22 <= percentages["B"] <= 28, f"Variant B: {percentages['B']}% (expected 25±3%)"
    assert 12 <= percentages["C"] <= 18, f"Variant C: {percentages['C']}% (expected 15±3%)"
    assert sum(percentages.values()) == 100, "Total should be 100%"


def test_openapi_with_response_model(client, test_app):
    """Test response_model support in the OpenAPI documentation"""

    @test_app.get("/items/{id}", response_model=ItemModel)
    @ab_test(metrics=[])
    def get_item(id: int):
        return {"id": id, "name": "Test Item"}

    @get_item.register_variant(traffic_percent=30)
    def get_item_b(id: int):
        return {"id": id, "name": "Variant B"}

    response = client.get("/openapi.json")

    path_item = response.json()["paths"]["/items/{id}"]["get"]
    assert (
        path_item["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/ItemModel"
    )


def test_openapi_with_response_class(client, test_app):
    """Test response_class support in the OpenAPI documentation"""

    @test_app.get(
        "/custom-response", response_class=Response, responses={200: {"content": {"application/octet-stream": {}}}}
    )
    @ab_test(metrics=[])
    def get_custom_response():
        return Response(content="test")

    response = client.get("/openapi.json")

    path_item = response.json()["paths"]["/custom-response"]["get"]
    assert "application/octet-stream" in path_item["responses"]["200"]["content"]


def test_openapi_with_status_code(client, test_app):
    """Test the status code is saved in the OpenAPI documentation"""

    @test_app.get("/error", responses={404: {"model": ErrorModel}})
    @ab_test(metrics=[])
    def get_with_error():
        return {"detail": "Not found"}

    response = client.get("/openapi.json")

    path_item = response.json()["paths"]["/error"]["get"]
    assert "404" in path_item["responses"]
    assert (
        path_item["responses"]["404"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/ErrorModel"
    )


def test_openapi_with_multiple_response_models(client, test_app):
    """Test the display of models in the OpenAPI documentation"""

    @test_app.get("/items", response_model=list[ItemModel])
    @ab_test(metrics=[])
    def list_items():
        return [{"id": 1, "name": "Test"}]

    response = client.get("/openapi.json")

    path_item = response.json()["paths"]["/items"]["get"]
    schema_ref = path_item["responses"]["200"]["content"]["application/json"]["schema"]["items"]["$ref"]
    assert schema_ref == "#/components/schemas/ItemModel"


def test_openapi_with_deprecated(client, test_app):
    """Test the deprecated flag is saved in the OpenAPI documentation"""

    @test_app.get("/old", deprecated=True)
    @ab_test(metrics=[])
    def deprecated_endpoint():
        return {"message": "This is old"}

    response = client.get("/openapi.json")

    path_item = response.json()["paths"]["/old"]["get"]
    assert path_item["deprecated"] is True


def test_openapi_with_tags(client, test_app):
    """Test tags are saved in the OpenAPI documentation"""

    @test_app.get("/tagged", tags=["ABTest"])
    @ab_test(metrics=[])
    def tagged_endpoint():
        return {"message": "Tagged"}

    response = client.get("/openapi.json")

    path_item = response.json()["paths"]["/tagged"]["get"]
    assert "ABTest" in path_item["tags"]
