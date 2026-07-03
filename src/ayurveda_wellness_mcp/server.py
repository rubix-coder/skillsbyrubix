"""MCP server exposing Ayurvedic wellness tools over stdio via FastMCP.

Every remedy-adjacent tool runs the safety gate (ayurveda_wellness_mcp.triage)
in code before returning suggestions — the gate is enforced here, not left to
prompt instructions.
"""

import json

from mcp.server.fastmcp import FastMCP

from ayurveda_wellness_mcp import logic

mcp = FastMCP("ayurveda-wellness")


@mcp.tool()
def safety_check(symptoms: str) -> str:
    """Screen free-text symptoms for red-flag emergencies, blacklisted
    substances/practices, or caution flags (pregnancy, infant, young child,
    medications, chronic disease) before any remedy is suggested."""
    return json.dumps(logic.safety_check(symptoms))


@mcp.tool()
def suggest_remedy(symptoms: str, context: str = "") -> str:
    """Suggest home remedies for the given symptoms, gated by safety_check.
    'context' should carry relevant details like pregnancy, age, medications,
    or chronic conditions so the gate can apply the right restrictions."""
    return json.dumps(logic.suggest_remedy(symptoms, context))


@mcp.tool()
def get_remedy_detail(remedy: str) -> str:
    """Get full detail (Sanskrit name, prep, traditional use, modern evidence,
    evidence grade, cautions) for one whitelisted remedy id."""
    return json.dumps(logic.get_remedy_detail(remedy))


@mcp.tool()
def find_recipe(dosha: str = "", season: str = "", query: str = "") -> str:
    """Find Ayurvedic recipes filtered by dosha (vata/pitta/kapha, tridoshic
    recipes always match), season, and/or a free-text ingredient/name query."""
    return json.dumps(logic.find_recipe(dosha, season, query))


@mcp.tool()
def get_exercise_routine(goal: str = "", dosha: str = "", max_minutes: int = 30) -> str:
    """Get a dosha-appropriate exercise routine fitting within max_minutes,
    optionally filtered by goal (e.g. cardio, calm, energy, strength)."""
    return json.dumps(logic.get_exercise_routine(goal, dosha, max_minutes))


@mcp.tool()
def get_pranayama(effect: str = "") -> str:
    """Get pranayama (breathing) techniques, optionally filtered by desired
    effect (calming, energizing, balancing, detox, cooling)."""
    return json.dumps(logic.get_pranayama(effect))


@mcp.tool()
def build_day_plan(dosha: str = "vata", season: str = "all", level: str = "beginner", constraints: str = "") -> str:
    """Build a full daily routine (dinacharya) for a dosha and season,
    combining wake time, daily steps, exercise, and pranayama. 'constraints'
    is gated the same way as suggest_remedy and can auto-swap contraindicated
    practices (e.g. kapalabhati) for a safer alternative."""
    return json.dumps(logic.build_day_plan(dosha, season, level, constraints))


def main():
    mcp.run()


if __name__ == "__main__":
    main()
