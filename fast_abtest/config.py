import os


class ABTestConfig:
    """Configuration class for A/B testing library settings.

    Provides immutable configuration for Prometheus exporter and metric collection.
    Supports initialization from environment variables via from_env() classmethod.

    Attributes:
        prometheus_port (int): Port for Prometheus metrics server (1024-65535)
        default_labels (list[str]): Default metric label names for all exporters
        histogram_buckets (list[float]): Bucket values for histogram metrics

    Examples:
       config = ABTestConfig(prometheus_port=9000)
       env_config = ABTestConfig.from_env()
    """

    __slots__ = ("prometheus_port", "default_labels", "histogram_buckets", "extra")

    def __init__(
        self,
        *,
        prometheus_port: int = 8009,
        default_labels: list[str] | None = None,
        histogram_buckets: list[float] | None = None,
    ):
        self.prometheus_port = self._validate_port(prometheus_port)
        self.default_labels = default_labels or ["variant", "func", "metric"]
        self.histogram_buckets = histogram_buckets or [0.1, 0.5, 1.0, 2.0, 5.0]

    def __setattr__(self, name, value):
        if hasattr(self, name):
            raise AttributeError("Configuration is immutable")
        super().__setattr__(name, value)

    @staticmethod
    def _validate_port(value: int) -> int:
        if not 1024 <= value <= 65535:
            raise ValueError("Port must be between 1024 and 65535")
        return value

    @classmethod
    def from_env(cls: type["ABTestConfig"]) -> "ABTestConfig":
        """Create configuration from environment variables.

        Reads:
            ABTEST_PORT: Prometheus exporter port (default: 8009)
            ABTEST_LABELS: Comma-separated default labels
            ABTEST_BUCKETS: Comma-separated histogram bucket values

        Returns:
            New ABTestConfig instance populated from environment
        """
        return cls(
            prometheus_port=int(os.getenv("ABTEST_PORT", "8009")),
            default_labels=os.getenv("ABTEST_LABELS", "0").split(",") or None,
            histogram_buckets=[float(value) for value in os.getenv("ABTEST_BUCKETS", "0").split(",")]
            or [0.1, 0.5, 1.0, 2.0, 5.0],
        )


class ConfigManager:
    """Global configuration manager for A/B testing library.

    Maintains and provides access to the current configuration state.

    Example:
        current_config = ConfigManager.get_config()
    """

    _current_config: ABTestConfig = ABTestConfig()

    @classmethod
    def get_config(cls: type["ConfigManager"]) -> ABTestConfig:
        return cls._current_config
