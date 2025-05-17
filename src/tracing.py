from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

def setup_tracing(endpoint = "http://127.0.0.1:6006/v1/traces"):
    """
    Set up OpenTelemetry tracing for LlamaIndex.
    """
    # Set up the OTLP exporter
    # This is the endpoint where the traces will be sent
    # In this case, it's a local endpoint for testing purposes
   
    tracer_provider = trace_sdk.TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint)))

    LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider)

