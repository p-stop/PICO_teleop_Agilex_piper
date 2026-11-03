"""Validate plan017 documentation links, definitions and worked arithmetic.

Run from the repository: .venv/Scripts/python.exe tools/check_data_quality_report.py
This does not evaluate robot data or validate proposed quality thresholds.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from robot_infra.provenance import runtime_identity


def main() -> None:
    files = [
        ROOT / "docs/research/2026-10-22-data-quality-quantification.md",
        ROOT / "docs/data-quality-standard.md",
        ROOT / "plans/017-data-quality-standards.md",
        ROOT / "docs/validation/2026-10-22-data-quality.md",
    ]
    proposal = json.loads(
        (ROOT / "docs/assets/data-quality/metrics-proposal.json").read_text(encoding="utf-8")
    )
    assert proposal["documentation_only"] is True
    assert proposal["runtime_loader_supported"] is False
    ids = [m["id"] for m in proposal["metrics"]]
    assert len(ids) == len(set(ids)) == 20
    sources = {s["id"]: s for s in proposal["sources"]}
    assert len(sources) == len(proposal["sources"]) == 16
    standard = files[1].read_text(encoding="utf-8")
    for metric in proposal["metrics"]:
        assert metric["id"] in standard
        assert metric["dimension"] in proposal["dimensions"]
        assert metric["unit"] and metric["denominator"]
        assert set(metric["source_ids"]) <= sources.keys()
        if metric["threshold"] is None:
            assert metric["default_mode"] == "monitor_only"
        else:
            assert metric["threshold"]["basis"] in proposal["threshold_basis_types"]
    for source in sources.values():
        assert source["url"].startswith("https://")
        assert source["independently_reproduced"] is False

    link_count = 0
    for path in files:
        content = path.read_text(encoding="utf-8")
        assert content.count("$$") % 2 == 0, path
        assert "\ufffd" not in content, path
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
            target = target.strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or not parsed.path:
                continue
            resolved = (path.parent / unquote(parsed.path)).resolve()
            assert resolved.exists(), (str(path), target)
            link_count += 1

    config_fields = 0
    for entry in proposal["historical_local_example_config"]:
        config = json.loads((ROOT / entry["path"]).read_text(encoding="utf-8"))
        for dotted, expected in entry["values"].items():
            actual = config
            for key in dotted.split("."):
                actual = actual[key]
            assert actual == expected, (entry["path"], dotted, expected, actual)
            config_fields += 1

    example = proposal["illustrative_task_budget"]
    budget = example["error_m"] / example["speed_bound_m_s"] - example["clock_error_bound_s"]
    assert math.isclose(budget, example["derived_max_age_s"])
    fast_budget = example["error_m"] / 0.5 - example["clock_error_bound_s"]
    assert math.isclose(fast_budget, 0.005)
    blur = [600 * 0.1 * exposure / 0.4 for exposure in (0.01, 0.03)]
    assert all(math.isclose(x, y) for x, y in zip(blur, [1.5, 4.5]))
    wilson_lower = 20 / (20 + 1.96**2)  # all 20 trials successful
    assert round(wilson_lower, 3) == 0.839
    assert 30 * 0.8 == 24
    identity = runtime_identity()
    result = {
        "scope": "documentation-only; no hardware/data/model evaluation",
        "metric_definitions": len(ids),
        "primary_source_entries": len(sources),
        "local_links_checked": link_count,
        "current_example_config_values_checked": config_fields,
        "worked_examples": {
            "age_budget_s": budget,
            "faster_motion_age_budget_s": fast_budget,
            "blur_px": blur,
            "wilson_20_of_20_lower_95_percent": wilson_lower,
            "minimum_fps_ratio_example": 24,
        },
        "runtime_identity": identity,
        "passed": True,
    }
    artifact = ROOT / "artifacts/validation/017-data-quality/document-check.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
