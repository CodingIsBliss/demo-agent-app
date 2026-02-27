"""LangChain Agent with Azure OpenAI and Azure AI OpenTelemetry tracing.

Tracing is handled by the AzureAIOpenTelemetryTracer from langchain-azure-ai,
passed via .with_config().  It creates spans for LLM calls, chain execution,
and tool invocations, and records token-usage attributes following GenAI
semantic conventions.

disable_streaming=True is required on AzureChatOpenAI so LangChain uses
the non-streaming code path, which populates llm_output.token_usage.
"""
import os
from typing import Optional

from langchain_openai import AzureChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate

from app.telemetry import get_otel_tracer
from app.tools import all_tools

REACT_PROMPT = """You are a helpful assistant with access to tools. Use them when needed.

You have access to the following tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""


def create_agent() -> Optional[AgentExecutor]:
    """Create and configure the LangChain agent with Azure OpenAI."""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

    if not endpoint or not api_key:
        return None

    llm = AzureChatOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        deployment_name=deployment,
        api_version=api_version,
        temperature=0.7,
        disable_streaming=True,  # Required: non-streaming populates token_usage
    )

    prompt = PromptTemplate.from_template(REACT_PROMPT)
    agent = create_react_agent(llm, all_tools, prompt)

    return AgentExecutor(
        agent=agent,
        tools=all_tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5,
    )


async def run_agent(query: str) -> dict:
    """Run the agent with a query and return the response.

    Tracing is handled by the AzureAIOpenTelemetryTracer passed via with_config.
    """
    agent = create_agent()
    if not agent:
        return {"success": False, "error": "Agent not configured.", "response": None}

    try:
        tracer = get_otel_tracer()
        result = await agent.with_config(
            {"callbacks": [tracer]}
        ).ainvoke({"input": query})
        output = result.get("output", "")
        return {"success": True, "response": output, "error": None}
    except Exception as e:
        return {"success": False, "error": str(e), "response": None}