"""OpenTelemetry configuration with Azure Monitor exporters and LangChain auto-instrumentation."""
import os
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from azure.monitor.opentelemetry.exporter import (
    AzureMonitorTraceExporter,
    AzureMonitorMetricExporter,
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.langchain import LangchainInstrumentor


def _build_arm_resource_id() -> str:
    """Construct an ARM resource ID from Azure App Service environment variables.

    Uses WEBSITE_OWNER_NAME (subscription+webspace), WEBSITE_RESOURCE_GROUP,
    and WEBSITE_SITE_NAME to build:
      /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Web/sites/{site}
    """
    owner = os.getenv("WEBSITE_OWNER_NAME", "")
    site_name = os.getenv("WEBSITE_SITE_NAME", "")
    resource_group = os.getenv("WEBSITE_RESOURCE_GROUP", "")
    subscription_id = owner.split("+")[0] if owner else ""

    if subscription_id and site_name and resource_group:
        return (
            f"/subscriptions/{subscription_id}"
            f"/resourceGroups/{resource_group}"
            f"/providers/Microsoft.Web/sites/{site_name}"
        )
    return ""


def get_agent_resource_id() -> str:
    """Return the ARM resource ID for use as the agent identifier."""
    return _build_arm_resource_id()


def setup_telemetry(app=None):
    """Configure OpenTelemetry with Azure Monitor exporter and LangChain auto-instrumentation."""
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    service_name = os.getenv("OTEL_SERVICE_NAME", "demo-agent-app")

    if not connection_string:
        print("Warning: APPLICATIONINSIGHTS_CONNECTION_STRING not set. Telemetry disabled.")
        return trace.get_tracer(service_name)

    resource = Resource.create({SERVICE_NAME: service_name})

    # Traces
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(AzureMonitorTraceExporter(connection_string=connection_string))
    )
    trace.set_tracer_provider(provider)

    # Metrics
    metric_reader = PeriodicExportingMetricReader(
        AzureMonitorMetricExporter(connection_string=connection_string),
        export_interval_millis=60000,
    )
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

    # Auto-instrument FastAPI
    if app:
        FastAPIInstrumentor.instrument_app(app)

    # Auto-instrument LangChain (creates spans for LLM calls, chains, tools, etc.)
    # Use the ARM resource ID as the agent id so spans carry the Azure resource identity.
    agent_id = get_agent_resource_id()
    LangchainInstrumentor(agent_id=agent_id).instrument()

    print(f"OpenTelemetry configured for service: {service_name}")
    return trace.get_tracer(service_name)


def get_tracer(name: str = "demo-agent-app"):
    """Get a tracer instance."""
    return trace.get_tracer(name)
