"""Loads package-bundled JSON data via importlib.resources, cached per process."""

import json
from functools import lru_cache
from importlib import resources


@lru_cache(maxsize=None)
def load(name: str):
    with resources.files("ayurveda_wellness_mcp.data").joinpath(f"{name}.json").open("r", encoding="utf-8") as f:
        return json.load(f)
