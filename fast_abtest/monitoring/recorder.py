import traceback
from contextlib import contextmanager
from logging import Logger
from typing import Self, Iterable, Iterator

from fast_abtest.interface import Metric
from fast_abtest.monitoring.interface import Context


class MetricRecorder:
    def __init__(
        self: Self,
        metrics: Iterable[Metric],
        logger: Logger,
    ) -> None:
        self._metrics = metrics
        self._logger = logger

    @contextmanager
    def record(self: Self, context: Context) -> Iterator[None]:
        try:
            for metric in self._metrics:
                context = metric.on_start(context=context)
            yield
        except:
            is_error = True
            raise
        else:
            is_error = False
        finally:
            try:
                for metric in self._metrics:
                    metric.on_end(context=context, is_error=is_error)
            except:
                self._logger.error(traceback.format_exc())
