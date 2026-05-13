import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_ROOT = PROJECT_ROOT / "configs"


def load_keyword_list(name: str) -> list[str]:
    path = CONFIG_ROOT / "keywords" / f"{name}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    keywords = payload.get("keywords", [])
    if not isinstance(keywords, list):
        raise ValueError(f"Invalid keyword config: {path}")
    return [str(item).strip().lower() for item in keywords if str(item).strip()]


def load_prompt_text(name: str) -> str:
    path = CONFIG_ROOT / "prompts" / f"{name}.md"
    return path.read_text(encoding="utf-8").strip()


def load_default_sources(name: str) -> list[dict]:
    path = CONFIG_ROOT / "sources" / f"{name}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    sources = payload.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError(f"Invalid source config: {path}")
    return sources
