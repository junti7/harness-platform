import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_ROOT = PROJECT_ROOT / "configs" / "sources"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "reviews" / "collection_scope_audit"

REQUIRED = {
    "edu_consulting": {
        "parenting_ai": ["부모", "학부모", "parent", "children", "보호자"],
        "worker_ai": ["직장인", "workplace", "workers", "job", "업무"],
        "job_seeker_ai": ["취준생", "취업 준비", "job seeker", "resume", "면접"],
        "military_ai": ["군대", "military", "입대", "defense"],
        "career_major": ["진로", "전공", "major", "future jobs", "직업"],
        "digital_dependence": ["스마트폰", "digital dependence", "screen time", "중독", "의존"],
    },
    "physical_ai": {
        "embodiment_robotics": ["robot", "robotics", "humanoid", "automation"],
        "memory_packaging": ["hbm", "packaging", "chiplet", "interposer"],
        "networking_optics": ["ethernet", "infiniband", "optical", "networking"],
        "power_cooling": ["power", "grid", "cooling", "datacenter"],
        "simulation_software": ["digital twin", "simulation", "industrial software"],
        "warehouse_deployment": ["warehouse", "logistics", "deployment"],
    },
}


def _load(name: str) -> dict:
    return json.loads((CONFIG_ROOT / f"{name}.json").read_text(encoding="utf-8"))


def _haystack(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False).lower()


def _audit_domain(name: str) -> list[str]:
    payload = _load(name)
    text = _haystack(payload)
    lines = [f"# {name} scope audit"]
    for cluster, terms in REQUIRED[name].items():
        hits = [term for term in terms if term.lower() in text]
        status = "OK" if hits else "MISSING"
        lines.append(f"- {cluster}: {status} | hits={', '.join(hits) if hits else '-'}")
    return lines


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = []
    for domain in ("edu_consulting", "physical_ai"):
        report.extend(_audit_domain(domain))
        report.append("")
    path = OUTPUT_DIR / "collection_scope_audit_2026-06-03.md"
    path.write_text("\n".join(report), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
