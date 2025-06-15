# Fast ABTest

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)

A lightweight Python decorator for implementing A/B testing with automatic traffic distribution. Compatible with FastAPI and works with both synchronous and asynchronous functions.

## Features

- 🎯 Simple decorator-based API
- ⚡ Supports both sync and async functions
- 🚀 Native FastAPI integration
- 📊 Automatic traffic distribution
- 🔒 Type safety with Python type hints
- 🛠️ Supports unlimited variants (A/B/C/D...)

## Installation

For now, you can install directly from GitHub:

```bash
pip install git+https://github.com/gifourm/fast-abtest.git
```

## Quick Start

### Basic Usage

```python
from fast_abtest import ab_test, Metric

@ab_test(metrics=[])
def recommendation_service(user_id: int) -> list[str]:
    # Main variant (A) - receives remaining traffic percentage
    return ["item1", "item2"]

@recommendation_service.register_variant(traffic_percent=30, disable_threshold=0.2)
def recommendation_service_b(user_id: int) -> list[str]:
    # Variant B - gets 30% of the traffic. If the error rate exceeds 0.2, traffic redirection will stop.
    return ["item3", "item4"]
```

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
from fast_abtest import ab_test

app = FastAPI()

@app.get("/recommendations")
@ab_test(metrics=[])
async def get_recommendations(user_id: int):
    return {"items": ["A1", "A2"]}

@get_recommendations.register_variant(traffic_percent=30)
async def get_recommendations_b(user_id: int):
    return {"items": ["B1", "B2"]}
```

**Important**: For FastAPI, the route decorator (`@app.get`) must come **before** `@ab_test`.

## Advanced Usage

### With Dependencies

```python
@app.post("/items")
@ab_test(metrics=[])
def create_item(
    item: Item,
    user: User = Depends(get_current_user)
):
    return create_item_v1(item, user)

@create_item.register_variant(traffic_percent=50)
def create_item_b(item: Item, user: User = Depends(get_current_user)):
    return create_item_v2(item, user)
```

### Response Models

```python
from pydantic import BaseModel

class ItemResponse(BaseModel):
    id: int
    name: str

@app.get("/items/{id}", response_model=ItemResponse)
@ab_test(metrics=[])
def get_item(id: int):
    return {"id": id, "name": "Test Item"}
```

## Metrics Tracking

Currently, tracking metrics is not supported.

## Development Status

Current version: `0.2.0-alpha`

### Roadmap

- [x] Core A/B testing functionality
- [x] FastAPI integration
- [x] Async support
- [x] Auto-disable failing variants
- [ ] Advanced metrics collection
- [ ] Custom metric callbacks
- [ ] Distributed traffic consistency
- [ ] Persistent variant assignment

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

MIT License. See `LICENSE` for details.
