"""Validate every data layer in the repo.

Checks that each .geojson / .json file under data/:
- parses as valid JSON;
- if GeoJSON: is a FeatureCollection with a non-empty features list,
  and every feature has a geometry and properties.

Run from repo root:
    python scripts/validate_data.py
Exits non-zero if any file fails, so CI can gate on it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def validate_geojson(path: Path, doc: object) -> list[str]:
    problems: list[str] = []
    if not isinstance(doc, dict):
        return [f"{path}: top level is not a JSON object"]
    if doc.get("type") != "FeatureCollection":
        problems.append(f"{path}: type is {doc.get('type')!r}, expected 'FeatureCollection'")
        return problems
    features = doc.get("features")
    if not isinstance(features, list):
        problems.append(f"{path}: 'features' is not a list")
        return problems
    if len(features) == 0:
        problems.append(f"{path}: FeatureCollection has zero features")
    for i, feat in enumerate(features):
        if not isinstance(feat, dict) or feat.get("type") != "Feature":
            problems.append(f"{path}: features[{i}] is not a Feature")
        elif feat.get("geometry") is None:
            problems.append(f"{path}: features[{i}] has null geometry")
        elif "properties" not in feat:
            problems.append(f"{path}: features[{i}] is missing properties")
        if len(problems) >= 5:
            problems.append(f"{path}: ...stopping after 5 problems")
            break
    return problems


def main() -> int:
    files = sorted(DATA_DIR.rglob("*.geojson")) + sorted(DATA_DIR.rglob("*.json"))
    if not files:
        print("No data files found — nothing to validate.")
        return 1
    all_problems: list[str] = []
    for path in files:
        rel = path.relative_to(DATA_DIR.parent)
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            all_problems.append(f"{rel}: invalid JSON — {e}")
            continue
        if path.suffix == ".geojson":
            all_problems.extend(
                p.replace(str(path), str(rel)) for p in validate_geojson(path, doc)
            )
        feature_count = (
            len(doc.get("features", [])) if isinstance(doc, dict) else "n/a"
        )
        print(f"ok  {rel}  ({feature_count} features)" if str(rel) not in "".join(all_problems) else f"FAIL {rel}")
    if all_problems:
        print(f"\n{len(all_problems)} problem(s):", file=sys.stderr)
        for p in all_problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(f"\nAll {len(files)} data files valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
