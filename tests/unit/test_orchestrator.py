import asyncio

import pytest
from langchain_core.messages import AIMessage

from apps.backend import orchestrator


def test_llm_configuration_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        orchestrator.build_graph([])


def test_llm_graph_can_complete_with_configured_fake_model(monkeypatch):
    tools = orchestrator._tools_from_mcp([
        type(
            "ToolDefinition",
            (),
            {
                "name": "search_assets",
                "description": "Find an asset.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        )()
    ])

    class FakeModel:
        def bind_tools(self, tools):
            assert tools
            return self

        def invoke(self, messages):
            return AIMessage(content="Fake LLM response")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(orchestrator, "ChatOpenAI", lambda **kwargs: FakeModel())

    result = asyncio.run(
        orchestrator.build_graph(tools).ainvoke({"messages": []})
    )

    assert result["messages"][-1].content == "Fake LLM response"
