"""A tiny persistent MCP client: spawns the real ayurveda-wellness-mcp server
as a subprocess over stdio and keeps one session open in a background thread,
so the Flask demo genuinely calls tools through the MCP protocol rather than
importing the package's logic directly."""

import asyncio
import json
import sys
import threading

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPDemoClient:
    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self._session = None
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=15)

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect())
        self._ready.set()
        self._loop.run_forever()

    async def _connect(self):
        params = StdioServerParameters(
            command=sys.executable,
            args=["-c", "from ayurveda_wellness_mcp.server import main; main()"],
        )
        self._stdio_cm = stdio_client(params)
        read, write = await self._stdio_cm.__aenter__()
        self._session_cm = ClientSession(read, write)
        self._session = await self._session_cm.__aenter__()
        await self._session.initialize()

    def list_tools(self):
        future = asyncio.run_coroutine_threadsafe(self._session.list_tools(), self._loop)
        return future.result(timeout=10).tools

    def call_tool(self, name: str, arguments: dict) -> dict:
        future = asyncio.run_coroutine_threadsafe(self._session.call_tool(name, arguments), self._loop)
        result = future.result(timeout=15)
        text = result.content[0].text
        return json.loads(text)


_client = None
_client_lock = threading.Lock()


def get_client() -> MCPDemoClient:
    global _client
    with _client_lock:
        if _client is None:
            _client = MCPDemoClient()
    return _client
