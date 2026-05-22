from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    BatchSpanProcessor,
)


def setup_tracing() -> None:
    """
    Configure OpenTelemetry tracing with console exporter.
    Call once at application startup from api.py.
    """
    provider = TracerProvider()
    provider.add_span_processor(
        BatchSpanProcessor(ConsoleSpanExporter())
    )
    trace.set_tracer_provider(provider)


tracer = trace.get_tracer(__name__)