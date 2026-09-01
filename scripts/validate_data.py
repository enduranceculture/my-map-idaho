"""Validate every data layer in the repo.

Checks that each .geojson / .json file under data/:
- parses as valid JSON;
- if GeoJSON: is a FeatureCollection with a non-empty features list,
  and every feature has a geometry and properties;
- if a GeoJSON shard manifest: every shard exists and feature counts reconcile;
- if the Base v1 consumer catalog: layer IDs are unique and delivery paths exist.

Run from repo root:
    python scripts/validate_data.py
Exits non-zero if any file fails, so CI can gate on it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
CATALOG_PATH = DATA_DIR / "catalog" / "base-v1.json"


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


def validate_manifest(path: Path, doc: object) -> list[str]:
    if not isinstance(doc, dict) or doc.get("format") != "geojson-shards-v1":
        return []

    problems: list[str] = []
    feature_count = doc.get("feature_count")
    shards = doc.get("shards")
    if not isinstance(feature_count, int) or feature_count < 0:
        problems.append(f"{path}: manifest feature_count is not a non-negative integer")
    if not isinstance(shards, list) or not shards:
        problems.append(f"{path}: manifest shards is not a non-empty list")
        return problems

    shard_total = 0
    for i, shard in enumerate(shards):
        if not isinstance(shard, dict):
            problems.append(f"{path}: shards[{i}] is not an object")
            continue
        shard_path = shard.get("path")
        shard_count = shard.get("feature_count")
        if not isinstance(shard_path, str) or not shard_path:
            problems.append(f"{path}: shards[{i}].path is missing")
        else:
            target = REPO_ROOT / shard_path
            if not target.is_file():
                problems.append(f"{path}: missing shard {shard_path}")
        if not isinstance(shard_count, int) or shard_count < 0:
            problems.append(f"{path}: shards[{i}].feature_count is invalid")
        else:
            shard_total += shard_count

    if isinstance(feature_count, int) and shard_total != feature_count:
        problems.append(
            f"{path}: shard feature total {shard_total} != feature_count {feature_count}"
        )
    return problems


def validate_catalog(path: Path, doc: object) -> list[str]:
    if path != CATALOG_PATH:
        return []
    if not isinstance(doc, dict):
        return [f"{path}: catalog top level is not a JSON object"]

    problems: list[str] = []
    if doc.get("schema_version") != 1:
        problems.append(f"{path}: schema_version must be 1")

    layers = doc.get("layers")
    if not isinstance(layers, list) or not layers:
        return problems + [f"{path}: layers is not a non-empty list"]

    seen_ids: set[str] = set()
    for i, layer in enumerate(layers):
        if not isinstance(layer, dict):
            problems.append(f"{path}: layers[{i}] is not an object")
            continue

        layer_id = layer.get("id")
        if not isinstance(layer_id, str) or not layer_id:
            problems.append(f"{path}: layers[{i}].id is missing")
        elif layer_id in seen_ids:
            problems.append(f"{path}: duplicate layer id {layer_id!r}")
        else:
            seen_ids.add(layer_id)

        delivery = layer.get("delivery")
        if not isinstance(delivery, dict) or "browser" not in delivery:
            problems.append(f"{path}: layer {layer_id!r} has no browser delivery")
            continue

        for delivery_name in ("browser", "source"):
            item = delivery.get(delivery_name)
            if item is None:
                continue
            if not isinstance(item, dict):
                problems.append(
                    f"{path}: layer {layer_id!r} {delivery_name} delivery is not an object"
                )
                continue
            delivery_type = item.get("type")
            target_path = item.get("path")
            if delivery_type not in {"geojson", "manifest"}:
                problems.append(
                    f"{path}: layer {layer_id!r} has invalid delivery type {delivery_type!r}"
                )
            if not isinstance(target_path, str) or not target_path:
                problems.append(
                    f"{path}: layer {layer_id!r} {delivery_name} path is missing"
                )
                continue
            relative = Path(target_path)
            if relative.is_absolute() or ".." in relative.parts:
                problems.append(
                    f"{path}: layer {layer_id!r} has unsafe path {target_path!r}"
                )
                continue
            if not (REPO_ROOT / relative).is_file():
                problems.append(
                    f"{path}: layer {layer_id!r} points to missing file {target_path}"
                )

    return problems


def main() -> int:
    files = sorted(DATA_DIR.rglob("*.geojson")) + sorted(DATA_DIR.rglob("*.json"))
    if not files:
        print("No data files found — nothing to validate.")
        return 1

    all_problems: list[str] = []
    for path in files:
        rel = path.relative_to(REPO_ROOT)
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            all_problems.append(f"{rel}: invalid JSON — {e}")
            print(f"FAIL {rel}")
            continue

        problems: list[str] = []
        if path.suffix == ".geojson":
            problems.extend(
                p.replace(str(path), str(rel)) for p in validate_geojson(path, doc)
            )
        problems.extend(
            p.replace(str(path), str(rel)) for p in validate_manifest(path, doc)
        )
        problems.extend(
            p.replace(str(path), str(rel)) for p in validate_catalog(path, doc)
        )
        all_problems.extend(problems)

        feature_count = (
            len(doc.get("features", [])) if isinstance(doc, dict) else "n/a"
        )
        if problems:
            print(f"FAIL {rel}")
        else:
            print(f"ok  {rel}  ({feature_count} features)")

    if all_problems:
        print(f"\n{len(all_problems)} problem(s):", file=sys.stderr)
        for problem in all_problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(f"\nAll {len(files)} data files valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
