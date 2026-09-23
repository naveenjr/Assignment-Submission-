from __future__ import annotations

import asyncio
import json
import os
import sys
from uuid import uuid4
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

from rag.retrieval.search import retrieve

load_dotenv()


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


class McpGateway:
    """Small MCP client used by every LLM tool."""

    def __init__(self) -> None:
        self.trace: list[dict] = []
        self.trace_id = ""

    def _server_parameters(self) -> StdioServerParameters:
        """Build the configured stdio parameters for the MCP server."""
        return StdioServerParameters(
            command=os.getenv("MCP_SERVER_COMMAND", sys.executable),
            args=[os.getenv(
                "MCP_SERVER_SCRIPT",
                str(Path(__file__).parents[2] / "mcp-servers" / "alarm-management" / "server.py"),
            )],
            env=dict(os.environ),
        )

    async def call(self, name: str, arguments: dict) -> dict:
        """Discover tools, invoke one tool, and return its JSON payload."""
        trace_id = arguments.setdefault("trace_id", self.trace_id or str(uuid4()))
        self.trace.append({"event": "discover", "tool": name, "trace_id": trace_id})
        async with stdio_client(self._server_parameters()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                available = await session.list_tools()
                if name not in {item.name for item in available.tools}:
                    raise RuntimeError(f"MCP tool unavailable: {name}")
                self.trace.append({"event": "invoke", "tool": name, "trace_id": trace_id})
                result = await session.call_tool(name, arguments)
                if getattr(result, "isError", False):
                    raise RuntimeError(f"MCP tool failed: {name}")
                text = next((item.text for item in result.content if hasattr(item, "text")), "{}")
                payload = json.loads(text)
                self.trace.append({"event": "complete", "tool": name, "trace_id": trace_id})
                return payload


gateway = McpGateway()


@tool
async def search_assets(query: str) -> dict:
    """Find an asset identifier by its natural-language name."""
    return await gateway.call("search_assets", {"query": query})


@tool
async def get_alarms(asset_id: str, status: str = "active") -> dict:
    """Retrieve alarms for an asset through MCP."""
    return await gateway.call("get_alarms", {"asset_id": asset_id, "status": status})


@tool
async def get_alarm_summary(alarm_id: str) -> dict:
    """Retrieve one alarm summary through MCP."""
    return await gateway.call("get_alarm_summary", {"alarm_id": alarm_id})


@tool
async def get_alarm_correlation(alarm_id: str) -> dict:
    """Retrieve related assets and likely causes through MCP."""
    return await gateway.call("get_alarm_correlation", {"alarm_id": alarm_id})


@tool
async def get_operator_recommendations(alarm_id: str) -> dict:
    """Retrieve immediate operator actions through MCP."""
    return await gateway.call("get_operator_recommendations", {"alarm_id": alarm_id})


TOOLS = [search_assets, get_alarms, get_alarm_summary, get_alarm_correlation, get_operator_recommendations]


def build_graph():
    """Build a LangGraph ReAct loop with LLM-selected MCP tools."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "replace-me":
        raise RuntimeError("Set OPENAI_API_KEY before using the LLM copilot.")
    model = ChatOpenAI(model=os.getenv("LLM_MODEL", "gpt-4o-mini"), api_key=api_key, temperature=0)
    model = model.bind_tools(TOOLS)

    def assistant(state: State):
        response = model.invoke([
            SystemMessage(content=(
                "You investigate industrial alarms. Use MCP tools to resolve assets and retrieve alarm evidence. "
                "Use document evidence supplied by the application. Never invent facts. "
                "End with immediate actions, risks, and citations such as [API:ALM-1001] and [DOC:file]."
            )),
            *state["messages"],
        ])
        return {"messages": [response]}

    def route(state: State):
        return "tools" if getattr(state["messages"][-1], "tool_calls", []) else "answer"

    def answer(state: State):
        return state

    graph = StateGraph(State)
    graph.add_node("assistant", assistant)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_node("answer", answer)
    graph.set_entry_point("assistant")
    graph.add_conditional_edges("assistant", route, {"tools": "tools", "answer": "answer"})
    graph.add_edge("tools", "assistant")
    graph.add_edge("answer", END)
    return graph.compile()


async def investigate(question: str) -> dict:
    """Run MCP tool-calling, retrieve RAG evidence, and synthesize an answer."""
    docs = retrieve(question)
    gateway.trace = []
    gateway.trace_id = str(uuid4())
    graph = build_graph()
    result = await graph.ainvoke({
        "messages": [HumanMessage(content=f"Question: {question}\nDocument evidence: {json.dumps(docs)}")],
    })
    return {
        "answer": result["messages"][-1].content,
        "sources": docs,
        "messages": result["messages"],
        "trace": gateway.trace,
        "trace_id": gateway.trace_id,
    }


def investigate_sync(question: str) -> dict:
    """Synchronous entry point used by Streamlit."""
    return asyncio.run(investigate(question))
