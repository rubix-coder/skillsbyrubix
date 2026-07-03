from ayurveda_wellness_mcp import logic
from ayurveda_wellness_mcp.server import mcp


def test_chest_pain_refers_with_zero_remedies():
    result = logic.suggest_remedy("severe chest pain")
    assert result["status"] == "refer"
    assert result["remedies"] == []


def test_bhasma_is_blacklisted():
    result = logic.suggest_remedy("joint pain", context="taking swarna bhasma")
    assert result["status"] == "blacklisted"
    assert result["remedies"] == []


def test_mild_nausea_pregnant_gives_ginger_only():
    result = logic.suggest_remedy("mild nausea", context="I am pregnant")
    assert result["status"] == "caution"
    ids = {r["id"] for r in result["remedies"]}
    assert ids == {"ginger_tea"}


def test_constipation_is_clear_with_triphala():
    result = logic.suggest_remedy("constipation")
    assert result["status"] == "clear"
    ids = {r["id"] for r in result["remedies"]}
    assert "triphala" in ids


def test_infant_cough_suppresses_remedies_entirely():
    result = logic.suggest_remedy("cough", context="8-month-old baby")
    assert result["status"] == "caution"
    assert result["remedies"] == []
    assert "guidance" in result


def test_adult_cough_includes_honey():
    result = logic.suggest_remedy("cough")
    ids = {r["id"] for r in result["remedies"]}
    assert "honey_lemon" in ids


def test_pitta_recipe_includes_tridoshic_khichdi():
    result = logic.find_recipe(dosha="pitta")
    ids = {r["id"] for r in result["recipes"]}
    assert "moong_dal_khichdi" in ids


def test_kapha_day_plan_with_hypertension_swaps_breath():
    result = logic.build_day_plan(dosha="kapha", constraints="hypertension, on blood pressure medication")
    assert result["status"] == "caution"
    assert result["routine"]["pranayama"]["name"] != "Kapalabhati (Skull-Shining Breath)"
    assert "swapped_note" in result


def test_unknown_remedy_returns_error_and_whitelist():
    result = logic.get_remedy_detail("snake_oil")
    assert result["status"] == "error"
    assert "available_remedies" in result
    assert "ginger_tea" in result["available_remedies"]


def test_list_tools_returns_all_seven():
    import asyncio

    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert names == {
        "safety_check",
        "suggest_remedy",
        "get_remedy_detail",
        "find_recipe",
        "get_exercise_routine",
        "get_pranayama",
        "build_day_plan",
    }
