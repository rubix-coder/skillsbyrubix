# Ayurveda Wellness — MCP + Demo App

An MCP server exposing safety-gated Ayurvedic wellness tools, plus a Flask
demo app that drives it as a real MCP client over stdio.

## Layout

- `src/ayurveda_wellness_mcp/` — the MCP server package (FastMCP, stdio
  transport). Core logic lives in `logic.py` / `triage.py` and is
  transport-agnostic; `server.py` just wraps it as MCP tools.
- `tests/` — pytest suite covering the safety-gate regression scenarios
  (emergency referral, blacklist, pregnancy/infant filtering, tridoshic
  recipe matching, kapha+hypertension breath-swap, etc).
- `demo/` — a small Flask app (`app.py`) that spawns the real MCP server as
  a subprocess and calls its tools via `mcp_client.py`. The flagship "Chat
  with Claude" tab runs a real Claude API tool-use loop (`claude-opus-4-8`)
  that decides which MCP tools to call from free-form text and shows the
  tool calls it made; the other tabs (symptom check, recipes, daily
  routines, pranayama) call the MCP tools directly for inspection.
- `skill/ayurvedic-wellness/SKILL.md` — the prose-facing Claude skill that
  mirrors the same safety rules for non-MCP contexts.

## Safety gate

Every remedy/routine path runs `triage()` in code before returning anything:

1. **Red flags** → refer to emergency care, zero remedies.
2. **Blacklist** (bhasma, rasa shastra, aconite, datura, self-panchakarma,
   etc.) → refused with a heavy-metal-contamination rationale.
3. **Conditional flags** (pregnancy, infant, young child, medications,
   chronic disease) → caution: remedies filtered by contraindication;
   infant/young child suppresses remedies entirely in favor of
   hydration/comfort guidance + pediatrician referral.
4. Otherwise → clear.

`build_day_plan` runs the same gate on `constraints` and auto-swaps
contraindicated practices (e.g. kapalabhati → nadi shodhana for
kapha + hypertension/medications) instead of dropping the whole plan.

## Run the MCP server standalone

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[test]"
.venv/bin/pytest -q                 # 10/10 regression scenarios
.venv/bin/ayurveda-wellness-mcp     # stdio MCP server
```

Register it with Claude Desktop / Claude Code:

```json
{
  "mcpServers": {
    "ayurveda-wellness": { "command": "/path/to/.venv/bin/ayurveda-wellness-mcp" }
  }
}
```

## Run the demo app

```bash
cd demo
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e ..          # installs ayurveda_wellness_mcp + mcp SDK
.venv/bin/python app.py              # http://127.0.0.1:5050
```

The demo's "MCP Tools" tab calls `list_tools()` live against the running
server to prove it's a genuine MCP connection, not a hardcoded UI.

### Enabling "Chat with Claude"

The chat tab needs a Claude API credential. Put it in a `.env` file at the
**repo root** (gitignored, loaded automatically at startup — never commit
this file):

```
ANTHROPIC_API_KEY=sk-ant-...
```

Without a key, the demo still runs — `/api/health` reports `chat_enabled:
false`, the chat tab shows a clear banner explaining why, and the other
tabs are unaffected since they call MCP tools directly rather than going
through Claude.
