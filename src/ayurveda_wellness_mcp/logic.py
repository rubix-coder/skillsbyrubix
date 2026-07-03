"""Core domain logic behind every MCP tool. Kept transport-agnostic and plain
Python so it can be unit-tested directly, without going through FastMCP."""

from ayurveda_wellness_mcp import constants
from ayurveda_wellness_mcp.loader import load
from ayurveda_wellness_mcp.triage import triage

PEDIATRIC_FLAGS = {"infant", "young_child"}


def safety_check(symptoms: str) -> dict:
    return triage(symptoms)


def _expand_synonyms(symptoms_lower: str) -> str:
    """Append canonical indication words for any lay-language phrase found,
    so free-text symptoms (e.g. 'runny nose') match indication tags (e.g.
    'cold') without requiring the user to guess our vocabulary."""
    synonyms = load("symptom_synonyms")
    expansions = [canonical for phrase, canon in synonyms.items() if phrase in symptoms_lower for canonical in canon]
    if not expansions:
        return symptoms_lower
    return symptoms_lower + " " + " ".join(expansions)


def _matching_remedies(symptoms: str):
    remedies = load("remedies")
    symptoms_lower = _expand_synonyms((symptoms or "").lower())
    return [
        {"id": rid, **r}
        for rid, r in remedies.items()
        if any(ind in symptoms_lower for ind in r["indications"])
    ]


def suggest_remedy(symptoms: str, context: str = "") -> dict:
    combined = f"{symptoms or ''} {context or ''}".strip()
    result = triage(combined)
    status = result["status"]

    if status == "refer":
        return {"status": status, "remedies": [], "message": result["message"]}

    if status == "blacklisted":
        return {"status": status, "remedies": [], "message": result["message"]}

    candidates = _matching_remedies(symptoms)

    if status == "caution":
        active = set(result["flags"])
        if active & PEDIATRIC_FLAGS:
            return {
                "status": status,
                "remedies": [],
                "guidance": constants.PEDIATRIC_GUIDANCE,
                "flags": result["flags"],
                "message": result["message"],
                "disclaimer": constants.DISCLAIMER,
            }
        filtered = [r for r in candidates if not (set(r["contraindications"]) & active)]
        return {
            "status": status,
            "remedies": filtered,
            "flags": result["flags"],
            "message": result["message"],
            "disclaimer": constants.DISCLAIMER,
        }

    return {"status": status, "remedies": candidates, "disclaimer": constants.DISCLAIMER}


def get_remedy_detail(remedy: str) -> dict:
    remedies = load("remedies")
    if remedy not in remedies:
        return {
            "status": "error",
            "message": f"Unknown remedy '{remedy}'.",
            "available_remedies": sorted(remedies.keys()),
        }
    return {"status": "ok", "remedy": {"id": remedy, **remedies[remedy]}, "disclaimer": constants.DISCLAIMER}


def find_recipe(dosha: str = "", season: str = "", query: str = "") -> dict:
    recipes = load("recipes")
    dosha = (dosha or "").lower().strip()
    season = (season or "").lower().strip()
    query = (query or "").lower().strip()

    matches = []
    for rid, r in recipes.items():
        if dosha and not ("tridoshic" in r["dosha"] or dosha in r["dosha"]):
            continue
        if season and not ("all" in r["season"] or season in r["season"]):
            continue
        if query:
            haystack = " ".join([r["name"], *r["ingredients"]]).lower()
            if query not in haystack:
                continue
        matches.append({"id": rid, **r})

    return {"status": "ok", "recipes": matches}


def get_exercise_routine(goal: str = "", dosha: str = "", max_minutes: int = 30) -> dict:
    routines = load("routines")
    dosha = (dosha or "").lower().strip()
    goal = (goal or "").lower().strip()

    pool = routines["exercise"].get(dosha, [])
    if goal:
        pool = [e for e in pool if goal in e["goals"]] or pool

    selected = []
    total = 0
    for exercise in pool:
        if total + exercise["duration_min"] > max_minutes and selected:
            continue
        selected.append(exercise)
        total += exercise["duration_min"]

    return {"status": "ok", "dosha": dosha, "goal": goal or None, "exercises": selected, "total_minutes": total}


def get_pranayama(effect: str = "") -> dict:
    pranayama = load("pranayama")
    effect = (effect or "").lower().strip()
    matches = [
        {"id": pid, **p}
        for pid, p in pranayama.items()
        if not effect or effect in p["effect"]
    ]
    return {"status": "ok", "techniques": matches}


def _default_pranayama_id(dosha: str) -> str:
    return {"vata": "nadi_shodhana", "pitta": "bhramari", "kapha": "kapalabhati"}.get(dosha, "nadi_shodhana")


def build_day_plan(dosha: str = "vata", season: str = "all", level: str = "beginner", constraints: str = "") -> dict:
    dosha = (dosha or "vata").lower().strip()
    season = (season or "all").lower().strip()

    gate = triage(constraints or "")
    status = gate["status"]

    if status == "refer":
        return {"status": status, "message": gate["message"], "routine": {}}

    if status == "blacklisted":
        return {"status": status, "message": gate["message"], "routine": {}}

    routines = load("routines")
    pranayama = load("pranayama")

    dinacharya = routines["dinacharya"].get(dosha, routines["dinacharya"]["vata"])
    ritucharya_note = routines["ritucharya"].get(season, routines["ritucharya"]["winter"])
    exercise = get_exercise_routine(dosha=dosha, max_minutes=30 if level == "advanced" else 20)

    pranayama_id = _default_pranayama_id(dosha)
    swapped_note = None

    if status == "caution":
        active = set(gate["flags"])
        chosen = pranayama[pranayama_id]
        if set(chosen["contraindications"]) & active:
            pranayama_id = "nadi_shodhana"
            swapped_note = (
                f"{chosen['name']} was swapped for Nadi Shodhana because it is contraindicated "
                "given the condition/medication mentioned (e.g. pregnancy, hypertension, heart "
                "disease, or blood-pressure medication)."
            )

    plan = {
        "wake_time": dinacharya["wake_time"],
        "daily_steps": dinacharya["steps"],
        "seasonal_focus": ritucharya_note,
        "exercise": exercise["exercises"],
        "pranayama": pranayama[pranayama_id],
    }

    result = {
        "status": status,
        "dosha": dosha,
        "season": season,
        "level": level,
        "routine": plan,
        "disclaimer": constants.DISCLAIMER,
    }
    if status == "caution":
        result["flags"] = gate["flags"]
        result["message"] = gate["message"]
    if swapped_note:
        result["swapped_note"] = swapped_note

    return result
