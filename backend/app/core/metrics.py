import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger("metrics-middleware")


metrics_collector = None


class MetricsMiddleware(BaseHTTPMiddleware):
    """Custom middleware to track request counts and durations, exposing them in Prometheus format."""

    def __init__(self, app):
        super().__init__(app)
        self.request_counts: dict[tuple[str, str, str], int] = {}
        self.request_latencies: dict[tuple[str, str], tuple[float, int]] = {}
        global metrics_collector
        metrics_collector = self

    async def dispatch(self, request: Request, call_next) -> Response:
        # Avoid circular logging or tracking metrics/health endpoints themselves
        path = request.url.path
        if path == "/metrics" or "/health" in path:
            return await call_next(request)

        start_time = time.time()
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            status_code = str(response.status_code)
        except Exception as e:
            duration = time.time() - start_time
            status_code = "500"
            raise e from None
        finally:
            method = request.method

            count_key = (method, path, status_code)
            self.request_counts[count_key] = self.request_counts.get(count_key, 0) + 1

            latency_key = (method, path)
            dur_sum, count = self.request_latencies.get(latency_key, (0.0, 0))
            self.request_latencies[latency_key] = (dur_sum + duration, count + 1)

        return response

    def get_prometheus_metrics(self) -> str:
        """Format metrics into Prometheus text exposition format."""
        lines = []

        lines.append("# HELP http_requests_total Total number of HTTP requests processed.")
        lines.append("# TYPE http_requests_total counter")
        for (method, path, status), count in self.request_counts.items():
            lines.append(f'http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}')

        lines.append("# HELP http_request_duration_seconds HTTP request execution durations.")
        lines.append("# TYPE http_request_duration_seconds summary")
        for (method, path), (d_sum, d_count) in self.request_latencies.items():
            lines.append(f'http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {d_sum:.6f}')
            lines.append(f'http_request_duration_seconds_count{{method="{method}",path="{path}"}} {d_count}')

        return "\n".join(lines) + "\n"
