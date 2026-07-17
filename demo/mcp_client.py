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
import os
import sys
import threading

import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

CLAUDE_MODEL = "claude-opus-4-8"

CHAT_SYSTEM_PROMPT = (
    "You are an Ayurvedic wellness assistant. You have tools backed by a "
    "safety-gated MCP server — use them for any question about remedies, "
    "recipes, exercise routines, pranayama, or daily/seasonal routines rather "
    "than answering from your own knowledge. The tools already apply a safety "
    "gate (emergency referral, blacklist refusal, pregnancy/infant/medication "
    "filtering) — trust their output as authoritative and do not soften, "
    "second-guess, or add remedies beyond what a tool returned. If a tool "
    "returns a 'refer' or 'blacklisted' status, relay that clearly and do not "
    "suggest a home remedy instead. Keep answers conversational and concise."
)


class McpClientError(RuntimeError):
    pass


class MCPDemoClient:
    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self._session = None
        self._connect_error = None
        self._anthropic = None
        self._anthropic_tools = []
        self._chat_history = []
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

        if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
            self._anthropic = anthropic.AsyncAnthropic()
            tools_result = await self._session.list_tools()
            self._anthropic_tools = [
                {"name": t.name, "description": t.description, "input_schema": t.inputSchema}
                for t in tools_result.tools
            ]

    def is_alive(self) -> bool:
        return self._thread.is_alive() and self._session is not None

    def has_chat(self) -> bool:
        return self._anthropic is not None

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

    async def _chat_async(self, user_text: str) -> dict:
        self._chat_history.append({"role": "user", "content": user_text})
        tool_calls = []

        while True:
            response = await self._anthropic.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=4096,
                system=CHAT_SYSTEM_PROMPT,
                thinking={"type": "adaptive"},
                tools=self._anthropic_tools,
                messages=self._chat_history,
            )
            self._chat_history.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                break

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                result = await self._session.call_tool(block.name, block.input)
                text = result.content[0].text if result.content else ""
                tool_calls.append({"name": block.name, "input": block.input, "result": text})
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": text, "is_error": result.isError}
                )
            self._chat_history.append({"role": "user", "content": tool_results})

        reply = next((b.text for b in response.content if b.type == "text"), "")
        return {"reply": reply, "tool_calls": tool_calls}

    def chat(self, user_text: str) -> dict:
        if self._anthropic is None:
            raise McpClientError(
                "No Claude API credentials found (ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN). "
                "Set one and restart the demo server to enable chat."
            )
        try:
            future = asyncio.run_coroutine_threadsafe(self._chat_async(user_text), self._loop)
            return future.result(timeout=120)
        except McpClientError:
            raise
        except Exception as exc:
            raise McpClientError(f"Chat turn failed: {exc}") from exc

    def reset_chat(self):
        self._chat_history = []


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
