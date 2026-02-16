"""
Custom tools for the LangChain agent with OpenTelemetry GenAI semantic convention tracing.
"""
import random
from typing import Optional
from langchain_core.tools import tool
from opentelemetry import trace
from opentelemetry.trace import SpanKind
from app.telemetry import get_tracer

tracer = get_tracer("agent-tools")


@tool
def calculator(expression: str) -> str:
    """Perform mathematical calculations. Input should be a valid math expression like '2 + 2' or '25 * 4'."""
    with tracer.start_as_current_span(
        "execute_tool calculator",
        kind=SpanKind.INTERNAL,
        attributes={
            "gen_ai.operation.name": "execute_tool",
            "gen_ai.tool.name": "calculator",
            "gen_ai.tool.type": "function",
        },
    ) as span:
        try:
            allowed_chars = set("0123456789+-*/.() ")
            if not all(c in allowed_chars for c in expression):
                result = "Error: Invalid characters in expression"
            else:
                result = str(eval(expression))
            return result
        except Exception as e:
            error_msg = f"Error evaluating expression: {str(e)}"
            span.set_attribute("error.type", type(e).__name__)
            return error_msg


@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location. Returns temperature, conditions, and humidity."""
    with tracer.start_as_current_span(
        "execute_tool get_weather",
        kind=SpanKind.INTERNAL,
        attributes={
            "gen_ai.operation.name": "execute_tool",
            "gen_ai.tool.name": "get_weather",
            "gen_ai.tool.type": "function",
        },
    ) as span:
        weather_data = {
            "seattle": {"temp": 52, "condition": "Rainy", "humidity": 85},
            "new york": {"temp": 45, "condition": "Cloudy", "humidity": 60},
            "los angeles": {"temp": 72, "condition": "Sunny", "humidity": 40},
            "miami": {"temp": 82, "condition": "Partly Cloudy", "humidity": 75},
            "chicago": {"temp": 38, "condition": "Windy", "humidity": 55},
            "denver": {"temp": 48, "condition": "Clear", "humidity": 30},
        }

        location_lower = location.lower()
        if location_lower in weather_data:
            data = weather_data[location_lower]
        else:
            data = {
                "temp": random.randint(30, 85),
                "condition": random.choice(["Sunny", "Cloudy", "Rainy", "Clear"]),
                "humidity": random.randint(30, 90),
            }

        result = f"Weather in {location}: {data['temp']}°F, {data['condition']}, Humidity: {data['humidity']}%"
        return result


@tool
def web_search(query: str) -> str:
    """Search the web for information. Returns relevant search results."""
    with tracer.start_as_current_span(
        "execute_tool web_search",
        kind=SpanKind.INTERNAL,
        attributes={
            "gen_ai.operation.name": "execute_tool",
            "gen_ai.tool.name": "web_search",
            "gen_ai.tool.type": "function",
        },
    ) as span:
        mock_results = [
            f"Result 1: Information about '{query}' from Wikipedia - A comprehensive overview of the topic.",
            f"Result 2: Latest news about '{query}' - Recent developments and updates.",
            f"Result 3: Expert analysis on '{query}' - In-depth research and findings.",
        ]
        result = "\n".join(mock_results)
        return result


# Export all tools
all_tools = [calculator, get_weather, web_search]
