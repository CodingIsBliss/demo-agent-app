"""OpenTelemetry configuration with Azure Monitor and LangChain Azure AI tracing.

The AzureAIOpenTelemetryTracer calls ``configure_azure_monitor()`` internally,
which sets up TracerProvider, MeterProvider, and exporters for Application
Insights.  We therefore avoid manual provider setup and let the library handle it.
"""
import os
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from langchain_azure_ai.callbacks.tracers import AzureAIOpenTelemetryTracer

_otel_tracer: AzureAIOpenTelemetryTracer | None = None


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
    """Configure OpenTelemetry with Azure Monitor and LangChain tracing.

    Creates the AzureAIOpenTelemetryTracer which internally calls
    ``configure_azure_monitor()`` to set up all providers and exporters.
    """
    global _otel_tracer
    service_name = os.getenv("OTEL_SERVICE_NAME", "demo-agent-app")
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

    if not connection_string:
        print("Warning: APPLICATIONINSIGHTS_CONNECTION_STRING not set. Telemetry disabled.")
        return trace.get_tracer(service_name)

    # Ensure the service name is available to the SDK resource detector
    os.environ.setdefault("OTEL_SERVICE_NAME", service_name)

    # Create the AzureAI tracer (calls configure_azure_monitor internally)
    _otel_tracer = AzureAIOpenTelemetryTracer(id=get_agent_resource_id())

    # Auto-instrument FastAPI
    if app:
        FastAPIInstrumentor.instrument_app(app)

    print(f"OpenTelemetry configured for service: {service_name}")
    return trace.get_tracer(service_name)


def get_tracer(name: str = "demo-agent-app"):
    """Get a tracer instance."""
    return trace.get_tracer(name)


def get_otel_tracer() -> AzureAIOpenTelemetryTracer:
    """Return the cached AzureAIOpenTelemetryTracer instance."""
    global _otel_tracer
    if _otel_tracer is None:
        _otel_tracer = AzureAIOpenTelemetryTracer(id=get_agent_resource_id())
    return _otel_tracer