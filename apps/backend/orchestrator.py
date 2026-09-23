from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
import json
import os
import sys
from uuid import uuid4
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import Field, create_model
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
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._available_tools: set[str] = set()

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

    async def start(self) -> list[Any]:
        """Start one MCP session and discover tools for the current request."""
        if self._session is not None:
            available = await self._session.list_tools()
            return list(available.tools)
        self._stack = AsyncExitStack()
        read, write = await self._stack.enter_async_context(
            stdio_client(self._server_parameters())
        )
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()
        available = await self._session.list_tools()
        self._available_tools = {item.name for item in available.tools}
        return list(available.tools)

    async def close(self) -> None:
        """Close the request-scoped MCP subprocess and session."""
        if self._stack is not None:
            await self._stack.aclose()
        self._stack = None
        self._session = None
        self._available_tools = set()

    async def call(self, name: str, arguments: dict) -> dict:
        """Invoke a discovered MCP tool using the current request session."""
        trace_id = arguments.setdefault("trace_id", self.trace_id or str(uuid4()))
        if self._session is None:
            await self.start()
        self.trace.append({"event": "discover", "tool": name, "trace_id": trace_id})
        if name not in self._available_tools:
            raise RuntimeError(f"MCP tool unavailable: {name}")
        self.trace.append({"event": "invoke", "tool": name, "trace_id": trace_id})
        result = await self._session.call_tool(name, arguments)
        if getattr(result, "isError", False):
            raise RuntimeError(f"MCP tool failed: {name}")
        text = next((item.text for item in result.content if hasattr(item, "text")), "{}")
        payload = json.loads(text)
        self.trace.append({"event": "complete", "tool": name, "trace_id": trace_id})
        return payload

    async def discover_tools(self) -> list[Any]:
        """Return the MCP tool definitions used to build LLM adapters."""
        return await self.start()


def _json_type_to_python(schema: dict) -> type:
    """Map the MCP JSON schema primitives used by this server to Python types."""
    return {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }.get(schema.get("type"), Any)


def _args_model(tool_definition: Any) -> type:
    """Create a Pydantic model from an MCP input schema."""
    schema = tool_definition.inputSchema or {}
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    fields = {}
    for name, definition in properties.items():
        if name == "trace_id":
            continue
        annotation = _json_type_to_python(definition)
        default = ... if name in required else definition.get("default", None)
        fields[name] = (annotation, Field(default=default, description=definition.get("description")))
    return create_model(f"{tool_definition.name.title().replace('_', '')}Args", **fields)


def _tools_from_mcp(
    tool_definitions: list[Any], gateway: McpGateway | None = None
) -> list[StructuredTool]:
    """Build LangChain adapters directly from MCP-discovered schemas."""
    gateway = gateway or McpGateway()
    adapters = []
    for definition in tool_definitions:
        async def invoke(_name=definition.name, **arguments):
            return await gateway.call(_name, arguments)

        adapters.append(
            StructuredTool.from_function(
                coroutine=invoke,
                name=definition.name,
                description=definition.description or definition.name,
                args_schema=_args_model(definition),
            )
        )
    return adapters


def build_graph(tools: list[StructuredTool]):
    """Build a LangGraph ReAct loop with LLM-selected MCP tools."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "replace-me":
        raise RuntimeError("Set OPENAI_API_KEY before using the LLM copilot.")
    model = ChatOpenAI(model=os.getenv("LLM_MODEL", "gpt-4o-mini"), api_key=api_key, temperature=0)
    model = model.bind_tools(tools)

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
    graph.add_node("tools", ToolNode(tools))
    graph.add_node("answer", answer)
    graph.set_entry_point("assistant")
    graph.add_conditional_edges("assistant", route, {"tools": "tools", "answer": "answer"})
    graph.add_edge("tools", "assistant")
    graph.add_edge("answer", END)
    return graph.compile()


async def investigate(question: str) -> dict:
    """Run MCP tool-calling, retrieve RAG evidence, and synthesize an answer."""
    docs = retrieve(question)
    gateway = McpGateway()
    gateway.trace_id = str(uuid4())
    try:
        tools = _tools_from_mcp(await gateway.discover_tools(), gateway)
        graph = build_graph(tools)
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
    finally:
        await gateway.close()


def investigate_sync(question: str) -> dict:
    """Synchronous entry point used by Streamlit."""
    return asyncio.run(investigate(question))
