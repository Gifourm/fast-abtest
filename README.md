# Fast ABTest

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)

A lightweight Python decorator for implementing A/B testing with automatic traffic distribution and built-in metrics monitoring. Compatible with FastAPI and works with both synchronous and asynchronous functions.

## Features

- 🎯 Simple decorator-based API
- ⚡ Supports both sync and async functions
- 🚀 Native FastAPI integration
- 📊 Automatic traffic distribution
- 📈 Built-in Prometheus metrics
- 🛠️ Custom metrics support
- 🔍 Real-time insights
- ♾️ Unlimited variants

## Installation

```bash
pip install git+https://github.com/gifourm/fast-abtest.git
```

## Quick Start

### Basic Usage

```python
from fast_abtest import ab_test, Metric

@ab_test(metrics=[Metric.LATENCY, Metric.ERRORS_TOTAL])
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

## Accessing Metrics

Built-in Prometheus metrics are available by default at:

```text
http://localhost:8009/metrics
```

## Monitoring Integration

### Built-in Prometheus Support
- Request latencies (histograms)
- Call counts
- Error counts

## Custom Metrics and Exporters

The library provides flexible interfaces for implementing custom metrics and exporters to integrate with various monitoring systems.

### Custom Exporters

To create a custom exporter, implement the `Exporter` protocol that handles:
- Initialization with metric configuration
- Recording metric values with labels

**Interface Requirements:**
```python
class Exporter(Protocol):
    def __init__(
        self,
        metrics: Iterable[str],
        func_name: str,
        labelnames: Iterable[str],
        port: int
    ) -> None: ...
    
    def record(self, label: MetricLabel, value: float | int) -> None: ...
```

## Creating Custom Metrics

To implement custom metrics in your A/B tests, you need to adhere to the following protocol:

```python
class Metric(Protocol):
    def __init__(
        self: Self,
        exporter: Exporter
    ) -> None: ...
    
    def on_start(self: Self, context: Context) -> Context: ...
    
    def on_end(self: Self, context: Context, is_error: bool) -> None: ...
```

## Configuration

### Environment Variables

| Variable         | Default               | Description                          |
|------------------|-----------------------|--------------------------------------|
| `ABTEST_PORT`    | 8009                | Prometheus-server metrics port       |
| `ABTEST_LABELS`  | "variant,func,metric" | Default metric labels. You can extend this with additional custom labels              |
| `ABTEST_BUCKETS` | "0.1,0.5,1.0,2.0,5.0" | Default histogram buckets |

## Development Status

Current version: `0.3.0-alpha`

### Roadmap

- [x] Core A/B testing functionality
- [x] FastAPI integration
- [x] Async support
- [x] Auto-disable failing variants
- [x] Advanced metrics collection
- [x] Custom metric callbacks
- [ ] Distributed traffic consistency
- [ ] Persistent variant assignment

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

MIT License. See `LICENSE` for details.
