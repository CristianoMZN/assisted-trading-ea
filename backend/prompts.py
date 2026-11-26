"""Load immutable, versioned analysis prompts shipped with the backend."""

from __future__ import annotations

from pathlib import Path


PROMPT_VERSIONS = {
    "news_analysis": "macroeconomic-news-v7",
    "technical_interpretation": "technical-interpretation-v1",
    "decision": "market-decision-v1",
}
ANALYSIS_VERSIONS = {"technical_indicators": "technical-indicators-v1", **PROMPT_VERSIONS}
PROMPT_DIR = Path(__file__).with_name("prompts")


def load_prompt(component: str, *, instrument: str | None = None) -> str:
    if component not in PROMPT_VERSIONS:
        raise ValueError(f"Unknown prompt component: {component}")
    if component == "news_analysis":
        if instrument not in ("WIN", "WDO"):
            raise ValueError("news_analysis requires instrument WIN or WDO")
        filename = f"news_analysis_{instrument.lower()}_v7.txt"
    else:
        filename = f"{component}_v1.txt"
    path = PROMPT_DIR / filename
    return path.read_text(encoding="utf-8")


def version_records() -> list[dict]:
    return [
        {"component": component, "version": version}
        for component, version in sorted(ANALYSIS_VERSIONS.items())
    ]
