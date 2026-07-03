"""A tiny persistent MCP client: spawns the real ayurveda-wellness-mcp server
as a subprocess over stdio and keeps one session open in a background thread,
so the Flask demo genuinely calls tools through the MCP protocol rather than
importing the package's logic directly.

If the underlying subprocess/session dies (crash, broken pipe), calls raise
McpClientError; app.py catches that, discards the broken client via
reset_client(), and retries once against a freshly spawned connection.
"""

import asyncio
import json
import sys
import threading

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class McpClientError(RuntimeError):
    pass


class MCPDemoClient:
    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self._session = None
        self._connect_error = None
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=15):
            raise McpClientError("Timed out starting the ayurveda-wellness-mcp subprocess.")
        if self._connect_error is not None:
            raise McpClientError(f"Failed to connect to ayurveda-wellness-mcp: {self._connect_error}")

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect())
        except Exception as exc:  # noqa: BLE001 - surfaced to caller via _connect_error
            self._connect_error = exc
        finally:
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

    def is_alive(self) -> bool:
        return self._thread.is_alive() and self._session is not None

    def list_tools(self):
        if self._session is None:
            raise McpClientError("MCP session is not connected.")
        try:
            future = asyncio.run_coroutine_threadsafe(self._session.list_tools(), self._loop)
            return future.result(timeout=10).tools
        except Exception as exc:
            raise McpClientError(f"list_tools failed: {exc}") from exc

    def call_tool(self, name: str, arguments: dict) -> dict:
        if self._session is None:
            raise McpClientError("MCP session is not connected.")
        try:
            future = asyncio.run_coroutine_threadsafe(self._session.call_tool(name, arguments), self._loop)
            result = future.result(timeout=15)
        except Exception as exc:
            raise McpClientError(f"Tool call '{name}' failed: {exc}") from exc
        if result.isError:
            text = result.content[0].text if result.content else "unknown MCP tool error"
            raise McpClientError(f"Tool '{name}' returned an error: {text}")
        return json.loads(result.content[0].text)


_client = None
_client_lock = threading.Lock()


def get_client() -> MCPDemoClient:
    global _client
    with _client_lock:
        if _client is None or not _client.is_alive():
            _client = MCPDemoClient()
    return _client


def reset_client():
    """Discard the current client so the next get_client() spawns a fresh one."""
    global _client
    with _client_lock:
        _client = None


def call_tool_resilient(name: str, arguments: dict) -> dict:
    """Call a tool, retrying once against a freshly spawned client on failure."""
    try:
        return get_client().call_tool(name, arguments)
    except McpClientError:
        reset_client()
        return get_client().call_tool(name, arguments)
