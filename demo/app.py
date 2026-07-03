"""Flask demo app for the ayurveda-wellness MCP server.

Every /api/* route calls the real MCP server over stdio via mcp_client.py —
this app is an MCP client, not a reimplementation of the server's logic.
"""

from flask import Flask, jsonify, render_template, request

from mcp_client import get_client

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/tools")
def api_tools():
    tools = get_client().list_tools()
    return jsonify([{"name": t.name, "description": t.description} for t in tools])


@app.route("/api/suggest-remedy", methods=["POST"])
def api_suggest_remedy():
    body = request.get_json(force=True)
    result = get_client().call_tool(
        "suggest_remedy",
        {"symptoms": body.get("symptoms", ""), "context": body.get("context", "")},
    )
    return jsonify(result)


@app.route("/api/remedy/<remedy_id>")
def api_remedy_detail(remedy_id):
    result = get_client().call_tool("get_remedy_detail", {"remedy": remedy_id})
    return jsonify(result)


@app.route("/api/recipes")
def api_recipes():
    result = get_client().call_tool(
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
    result = get_client().call_tool("get_pranayama", {"effect": request.args.get("effect", "")})
    return jsonify(result)


@app.route("/api/day-plan", methods=["POST"])
def api_day_plan():
    body = request.get_json(force=True)
    result = get_client().call_tool(
        "build_day_plan",
        {
            "dosha": body.get("dosha", "vata"),
            "season": body.get("season", "all"),
            "level": body.get("level", "beginner"),
            "constraints": body.get("constraints", ""),
        },
    )
    return jsonify(result)


if __name__ == "__main__":
    get_client()  # warm the MCP connection before serving
    app.run(host="127.0.0.1", port=5050, debug=False)
