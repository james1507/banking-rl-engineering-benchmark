from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from banking_lab.config import settings

provider = TracerProvider(resource=Resource.create({"service.name": "banking-lab"}))
if settings().otlp_endpoint:
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=settings().otlp_endpoint, timeout=3))
    )
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("banking_lab")
