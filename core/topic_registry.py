from __future__ import annotations

import json
import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx

from core.domain_config import load_default_sources, load_keyword_list

try:
    import anthropic
except ImportError:  # pragma: no cover
    anthropic = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = PROJECT_ROOT / "runtime"
TOPIC_REGISTRY_TEMPLATE = "{domain}_topic_registry.json"
TOPIC_REFRESH_HOURS = int(os.getenv("TOPIC_REFRESH_HOURS", "6"))
TOPIC_LLM_MODEL = os.getenv("TOPIC_REGISTRY_MODEL", "claude-haiku-4-5").strip()
TOPIC_MAX_AUTO_ACTIVE = int(os.getenv("TOPIC_MAX_AUTO_ACTIVE", "6"))
TOPIC_MAX_QUERY_SOURCES = int(os.getenv("TOPIC_MAX_QUERY_SOURCES", "6"))
TOPIC_OLLAMA_MODEL = os.getenv("TOPIC_REGISTRY_OLLAMA_MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")).strip()
OLLAMA_REMOTE_HOST = os.getenv("OLLAMA_REMOTE_HOST", "").strip()
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").strip()

_STOPWORDS = {
    "the", "and", "for", "with", "from", "into", "using", "your", "this", "that",
    "will", "are", "new", "why", "how", "what", "when", "behind", "future", "growth",
    "reportedly", "year", "wins", "golden", "age", "industry", "revenue", "product",
    "features", "customer", "testimonial", "excerpt", "product", "productivity", "powered",
    "google", "openai", "deepmind", "anthropic", "company", "inc", "corp", "ltd",
    "robot", "robots", "robotics", "ai", "agi", "physical", "autonomous", "automation",
    "learning", "models", "model", "language", "large", "deep", "school", "football",
    "diffusion", "online", "universal", "evaluation", "platform", "approach", "generalization",
    "towards", "under", "experts", "analysis", "representation", "representations",
    "adaptive", "data", "inverse", "mixture", "complete", "version", "true", "target",
}

_DOMAIN_ANCHORS = {
    "robot", "robots", "robotics", "humanoid", "warehouse", "factory", "manufacturing",
    "automation", "industrial", "semiconductor", "chip", "chips", "gpu", "wafer", "foundry",
    "hynix", "samsung", "nvidia", "tsmc", "atlas", "spot", "stretch", "optimus",
    "actuator", "sensor", "lidar", "manipulation", "grasping", "locomotion",
    "fleet", "deployment", "production",
}

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9\.\-\+]{2,}")


def _registry_path(domain: str) -> Path:
    return RUNTIME_DIR / TOPIC_REGISTRY_TEMPLATE.format(domain=domain)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "topic"


def _normalize_topic(text: str) -> str:
    return " ".join(text.strip().lower().split())


def load_seed_topics(domain: str) -> list[str]:
    return load_keyword_list(domain)


def load_generated_topic_registry(domain: str) -> dict[str, Any]:
    path = _registry_path(domain)
    if not path.exists():
        return {"domain": domain, "generated_at": None, "auto_topics": [], "suggested_topics": [], "query_sources": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"domain": domain, "generated_at": None, "auto_topics": [], "suggested_topics": [], "query_sources": []}


def load_active_topics(domain: str) -> list[str]:
    seed = load_seed_topics(domain)
    registry = load_generated_topic_registry(domain)
    active_auto = [
        _normalize_topic(item.get("topic", ""))
        for item in registry.get("auto_topics", [])
        if item.get("active")
    ]
    merged: list[str] = []
    for topic in [*seed, *active_auto]:
        if topic and topic not in merged:
            merged.append(topic)
    return merged


def load_generated_query_sources(domain: str) -> list[dict[str, Any]]:
    registry = load_generated_topic_registry(domain)
    return registry.get("query_sources", []) or []


def _existing_topic_fragments(current_topics: list[str]) -> set[str]:
    fragments: set[str] = set()
    for topic in current_topics:
        topic = _normalize_topic(topic)
        if not topic:
            continue
        fragments.add(topic)
        for token in topic.split():
            if len(token) >= 3:
                fragments.add(token)
    return fragments


def _heuristic_topic_candidates(current_topics: list[str], recent_titles: list[str], limit: int = 12) -> list[dict[str, Any]]:
    existing = _existing_topic_fragments(current_topics)
    unigram_counts: Counter[str] = Counter()
    bigram_counts: Counter[str] = Counter()
    evidence: dict[str, str] = {}

    for title in recent_titles:
        title_lower = title.lower()
        tokens = [tok for tok in _TOKEN_RE.findall(title_lower) if tok not in _STOPWORDS]
        for tok in tokens:
            if tok in existing or len(tok) < 4:
                continue
            unigram_counts[tok] += 1
            evidence.setdefault(tok, title)
        for left, right in zip(tokens, tokens[1:]):
            phrase = f"{left} {right}"
            if left in _STOPWORDS or right in _STOPWORDS:
                continue
            if phrase in existing or left in existing or right in existing:
                continue
            if len(left) < 4 or len(right) < 4:
                continue
            bigram_counts[phrase] += 1
            evidence.setdefault(phrase, title)

    merged = Counter()
    for topic, count in unigram_counts.items():
        merged[topic] += count
    for topic, count in bigram_counts.items():
        merged[topic] += count + 1

    ranked = []
    for topic, count in merged.most_common(limit * 2):
        if count < 2 and " " not in topic:
            continue
        ranked.append(
            {
                "topic": topic,
                "confidence": round(min(0.95, 0.45 + count * 0.08), 2),
                "evidence_count": count,
                "reason": "recent_titles_frequency",
                "sample_title": evidence.get(topic, ""),
            }
        )
    return ranked[:limit]


def _anchored_recent_titles(current_topics: list[str], recent_rows: list[dict[str, Any]]) -> list[str]:
    strong_sources = {"arxiv_robotics", "techcrunch_robotics", "boston_dynamics", "ieee_spectrum"}
    titles: list[str] = []
    for row in recent_rows:
        title = str(row.get("title") or "").strip()
        source = str(row.get("source") or "").strip().lower()
        title_lower = title.lower()
        if not title:
            continue
        if source in strong_sources or any(anchor in title_lower for anchor in _DOMAIN_ANCHORS):
            titles.append(title)
    return titles


def _llm_topic_candidates(domain: str, current_topics: list[str], recent_titles: list[str], limit: int = 8) -> list[dict[str, Any]]:
    ollama_topics = _ollama_topic_candidates(domain, current_topics, recent_titles, limit=limit)
    if ollama_topics:
        return ollama_topics

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key or anthropic is None:
        return []

    prompt = (
        "You maintain a 24/7 topic collection system.\n"
        "Task: propose only NEW collection topics not already covered.\n"
        "Rules:\n"
        "- Return JSON only.\n"
        "- Topic must be 1 to 3 words, lowercase.\n"
        "- Reject generic words like ai, robot, startup, industry.\n"
        "- Ground every topic in the recent collected titles.\n"
        "- Prefer monetizable, recurring, decision-useful topics.\n"
        "- Max 8 items.\n\n"
        f"domain={domain}\n"
        f"current_topics={json.dumps(current_topics, ensure_ascii=False)}\n"
        f"recent_titles={json.dumps(recent_titles[:60], ensure_ascii=False)}\n\n"
        "Return shape:\n"
        "{\"topics\": [{\"topic\": \"...\", \"reason\": \"...\", \"sample_title\": \"...\", \"confidence\": 0.0}]}"
    )
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=TOPIC_LLM_MODEL,
            max_tokens=800,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            part.text for part in resp.content if getattr(part, "type", "") == "text"
        ).strip()
        payload = json.loads(text)
        out = []
        seen = set()
        for item in payload.get("topics", []):
            topic = _normalize_topic(str(item.get("topic", "")))
            if not topic or topic in seen or topic in _existing_topic_fragments(current_topics):
                continue
            seen.add(topic)
            out.append(
                {
                    "topic": topic,
                    "confidence": float(item.get("confidence", 0.5) or 0.5),
                    "evidence_count": 1,
                    "reason": str(item.get("reason", "llm_suggested"))[:200],
                    "sample_title": str(item.get("sample_title", ""))[:300],
                }
            )
        return out[:limit]
    except Exception:
        return []


def _ollama_topic_candidates(domain: str, current_topics: list[str], recent_titles: list[str], limit: int = 8) -> list[dict[str, Any]]:
    prompt = (
        "Return JSON only. Propose new collection topics.\n"
        "Rules: lowercase, 1-3 words, non-generic, grounded in recent titles, not overlapping current topics.\n"
        "Format: {\"topics\":[{\"topic\":\"...\",\"reason\":\"...\",\"sample_title\":\"...\",\"confidence\":0.0}]}\n"
        f"domain={domain}\n"
        f"current_topics={json.dumps(current_topics[:80], ensure_ascii=False)}\n"
        f"recent_titles={json.dumps(recent_titles[:50], ensure_ascii=False)}"
    )
    for host, label in [(OLLAMA_REMOTE_HOST, "mbp"), (OLLAMA_HOST, "mini")]:
        if not host:
            continue
        try:
            tags = httpx.get(f"{host}/api/tags", timeout=2.5)
            if tags.status_code != 200:
                continue
            resp = httpx.post(
                f"{host}/api/chat",
                json={
                    "model": TOPIC_OLLAMA_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
                timeout=8,
            )
            resp.raise_for_status()
            content = (((resp.json() or {}).get("message") or {}).get("content") or "").strip()
            payload = json.loads(content)
            out = []
            seen = set()
            for item in payload.get("topics", []):
                topic = _normalize_topic(str(item.get("topic", "")))
                if not topic or topic in seen or topic in _existing_topic_fragments(current_topics):
                    continue
                seen.add(topic)
                out.append(
                    {
                        "topic": topic,
                        "confidence": float(item.get("confidence", 0.5) or 0.5),
                        "evidence_count": 1,
                        "reason": f"ollama_{label}:{str(item.get('reason', ''))[:160]}",
                        "sample_title": str(item.get("sample_title", ""))[:300],
                    }
                )
            if out:
                return out[:limit]
        except Exception:
            continue
    return []


def _compose_query_sources(domain: str, auto_topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources = []
    for item in auto_topics:
        if not item.get("active"):
            continue
        topic = _normalize_topic(item.get("topic", ""))
        if not topic:
            continue
        sources.append(
            {
                "name": f"google_news_{_slugify(topic)}",
                "url": (
                    "https://news.google.com/rss/search?"
                    f"q={quote_plus(topic)}&hl=en-US&gl=US&ceid=US:en"
                ),
                "stale_minutes": 720,
                "reliability_score": 0.55,
                "expected_signal_type": f"topic_query:{topic}",
                "generated": True,
                "topic": topic,
                "domain": domain,
            }
        )
        if len(sources) >= TOPIC_MAX_QUERY_SOURCES:
            break
    return sources


def refresh_topic_registry(domain: str, recent_rows: list[dict[str, Any]]) -> dict[str, Any]:
    path = _registry_path(domain)
    path.parent.mkdir(parents=True, exist_ok=True)

    seed_topics = load_seed_topics(domain)
    current_topics = load_active_topics(domain)
    recent_titles = _anchored_recent_titles(current_topics, recent_rows)
    heuristic = _heuristic_topic_candidates(current_topics, recent_titles, limit=12)
    llm_topics = _llm_topic_candidates(domain, current_topics, recent_titles, limit=8)

    merged_candidates: list[dict[str, Any]] = []
    seen = set()
    for item in [*llm_topics, *heuristic]:
        topic = _normalize_topic(item.get("topic", ""))
        if not topic or topic in seen or topic in _existing_topic_fragments(current_topics):
            continue
        seen.add(topic)
        merged_candidates.append(
            {
                "topic": topic,
                "confidence": round(float(item.get("confidence", 0.5) or 0.5), 2),
                "evidence_count": int(item.get("evidence_count", 1) or 1),
                "reason": str(item.get("reason", ""))[:200],
                "sample_title": str(item.get("sample_title", ""))[:300],
                "active": False,
            }
        )

    auto_topics = []
    for item in merged_candidates[:TOPIC_MAX_AUTO_ACTIVE]:
        if item["confidence"] >= 0.8 and item["evidence_count"] >= 4:
            item["active"] = True
        auto_topics.append(item)

    query_sources = _compose_query_sources(domain, auto_topics)
    payload = {
        "domain": domain,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed_topics": seed_topics,
        "auto_topics": auto_topics,
        "suggested_topics": [item for item in merged_candidates if not item["active"]][:8],
        "query_sources": query_sources,
        "recent_title_count": len(recent_titles),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def ensure_fresh_topic_registry(domain: str, recent_rows: list[dict[str, Any]]) -> dict[str, Any]:
    current = load_generated_topic_registry(domain)
    generated_at = current.get("generated_at")
    if generated_at:
        try:
            ts = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - ts < timedelta(hours=TOPIC_REFRESH_HOURS):
                return current
        except Exception:
            pass
    return refresh_topic_registry(domain, recent_rows)


def merged_sources_with_generated(domain: str, base_sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    generated = load_generated_query_sources(domain)
    seen = set()
    out = []
    for source in [*base_sources, *generated]:
        key = (source.get("name"), source.get("url"))
        if key in seen:
            continue
        seen.add(key)
        out.append(source)
    return out
