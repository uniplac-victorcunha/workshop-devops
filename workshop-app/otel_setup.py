"""
Configuração central do OpenTelemetry.
Exporta traces, metrics e logs via OTLP HTTP para o otel-collector do SigNoz.
"""
import logging
import os

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "workshop-app")
OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://signoz-otel-collector:4318")


def _resource() -> Resource:
    return Resource.create(
        {
            "service.name": SERVICE_NAME,
            "service.version": "1.0.0",
            "deployment.environment": os.getenv("DEPLOY_ENV", "workshop"),
        }
    )


def setup_tracing() -> trace.Tracer:
    provider = TracerProvider(resource=_resource())
    exporter = OTLPSpanExporter(endpoint=f"{OTLP_ENDPOINT}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(SERVICE_NAME)


def setup_metrics() -> metrics.Meter:
    exporter = OTLPMetricExporter(endpoint=f"{OTLP_ENDPOINT}/v1/metrics")
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=15_000)
    provider = MeterProvider(resource=_resource(), metric_readers=[reader])
    metrics.set_meter_provider(provider)
    return metrics.get_meter(SERVICE_NAME)


def setup_logging() -> None:
    provider = LoggerProvider(resource=_resource())
    exporter = OTLPLogExporter(endpoint=f"{OTLP_ENDPOINT}/v1/logs")
    provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
    set_logger_provider(provider)

    handler = LoggingHandler(level=logging.INFO, logger_provider=provider)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    console = logging.StreamHandler()
    console.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s "
            "(trace_id=%(otelTraceID)s span_id=%(otelSpanID)s) - %(message)s"
        )
    )
    root.addHandler(console)


def init_telemetry():
    tracer = setup_tracing()
    meter = setup_metrics()
    setup_logging()
    return tracer, meter
