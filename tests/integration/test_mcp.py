import asyncio

from apps.backend.orchestrator import McpGateway


def test_mcp_server_discovers_alarm_tools():
    async def discover():
        gateway = McpGateway()
        params = gateway._server_parameters()
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return {tool.name for tool in (await session.list_tools()).tools}

    tools = asyncio.run(discover())
    assert {"search_assets", "get_alarms", "get_alarm_summary"} <= tools
