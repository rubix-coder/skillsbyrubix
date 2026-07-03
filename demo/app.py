"""Flask demo app for the ayurveda-wellness MCP server.

Every /api/* route calls the real MCP server over stdio via mcp_client.py —
this app is an MCP client, not a reimplementation of the server's logic.
"""

import logging

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from mcp_client import McpClientError, call_tool_resilient, get_client

app = Flask(__name__)
log = logging.getLogger(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    return "", 204


@app.route("/api/health")
def api_health():
    try:
        tools = get_client().list_tools()
        return jsonify({"status": "ok", "tool_count": len(tools)})
    except McpClientError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 503


@app.route("/api/tools")
def api_tools():
    tools = get_client().list_tools()
    return jsonify([{"name": t.name, "description": t.description} for t in tools])


@app.route("/api/suggest-remedy", methods=["POST"])
def api_suggest_remedy():
    body = request.get_json(force=True)
    result = call_tool_resilient(
        "suggest_remedy",
        {"symptoms": body.get("symptoms", ""), "context": body.get("context", "")},
    )
    return jsonify(result)


@app.route("/api/remedy/<remedy_id>")
def api_remedy_detail(remedy_id):
    result = call_tool_resilient("get_remedy_detail", {"remedy": remedy_id})
    return jsonify(result)


@app.route("/api/recipes")
def api_recipes():
    result = call_tool_resilient(
        "find_recipe",
        {
            "dosha": request.args.get("dosha", ""),
            "season": request.args.get("season", ""),
            "query": request.args.get("query", ""),
        },
    )
    return jsonify(result)


@app.route("/api/pranayama")
def api_pranayama():
    result = call_tool_resilient("get_pranayama", {"effect": request.args.get("effect", "")})
    return jsonify(result)


@app.route("/api/day-plan", methods=["POST"])
def api_day_plan():
    body = request.get_json(force=True)
    result = call_tool_resilient(
        "build_day_plan",
        {
            "dosha": body.get("dosha", "vata"),
            "season": body.get("season", "all"),
            "level": body.get("level", "beginner"),
            "constraints": body.get("constraints", ""),
        },
    )
    return jsonify(result)


@app.errorhandler(McpClientError)
def handle_mcp_error(exc):
    log.exception("MCP client error")
    return jsonify({"status": "error", "message": str(exc)}), 502


@app.errorhandler(HTTPException)
def handle_http_error(exc):
    return jsonify({"status": "error", "message": exc.description}), exc.code


@app.errorhandler(Exception)
def handle_unexpected_error(exc):
    log.exception("Unexpected error")
    return jsonify({"status": "error", "message": "Unexpected server error. Check server logs."}), 500


if __name__ == "__main__":
    get_client()  # warm the MCP connection before serving
    app.run(host="127.0.0.1", port=5050, debug=False)
