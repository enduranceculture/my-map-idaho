"""Shard oversized GeoJSON so authoritative Idaho layers remain GitHub-friendly.

The data pipelines intentionally preserve useful statewide geometry. Some source-faithful
layers exceed GitHub's single-file limit, so this packager deterministically splits any
GeoJSON larger than TARGET_SHARD_BYTES and writes a manifest beside the shards.

Consumers should load every shard listed in the manifest. The original monolith is
removed only after all shards are written successfully.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TARGET_SHARD_BYTES = 35 * 1024 * 1024
SHARD_PATTERN = re.compile(r"_part\d{3}\.geojson$")


def compact_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def clear_stale_outputs(path: Path) -> None:
    stem = path.stem
    for stale in path.parent.glob(f"{stem}_part*.geojson"):
        stale.unlink()
    manifest = path.with_name(f"{stem}_manifest.json")
    if manifest.exists():
        manifest.unlink()


def write_geojson(path: Path, doc: dict) -> int:
    payload = compact_bytes(doc) + b"\n"
    path.write_bytes(payload)
    return len(payload)


def package_file(path: Path) -> bool:
    if SHARD_PATTERN.search(path.name):
        return False

    clear_stale_outputs(path)
    size = path.stat().st_size
    if size <= TARGET_SHARD_BYTES:
        print(f"keep {path.relative_to(ROOT)} ({size / 1024 / 1024:.1f} MB)")
        return False

    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("type") != "FeatureCollection" or not isinstance(doc.get("features"), list):
        raise RuntimeError(f"Cannot shard non-FeatureCollection: {path}")

    features = doc["features"]
    top_level = {key: value for key, value in doc.items() if key != "features"}
    shards: list[list[dict]] = []
    current: list[dict] = []
    current_bytes = len(compact_bytes(top_level)) + 64

    for feature in features:
        feature_bytes = len(compact_bytes(feature)) + 1
        if current and current_bytes + feature_bytes > TARGET_SHARD_BYTES:
            shards.append(current)
            current = []
            current_bytes = len(compact_bytes(top_level)) + 64
        current.append(feature)
        current_bytes += feature_bytes
    if current:
        shards.append(current)

    if len(shards) < 2:
        raise RuntimeError(f"Expected multiple shards for oversized file: {path}")

    shard_records = []
    for index, shard_features in enumerate(shards, start=1):
        shard_path = path.with_name(f"{path.stem}_part{index:03d}.geojson")
        shard_doc = dict(top_level)
        shard_doc["shard"] = {
            "index": index,
            "count": len(shards),
            "source_monolith": path.name,
        }
        shard_doc["features"] = shard_features
        shard_size = write_geojson(shard_path, shard_doc)
        if shard_size > 50 * 1024 * 1024:
            raise RuntimeError(
                f"Shard still exceeds conservative GitHub target: {shard_path} "
                f"({shard_size / 1024 / 1024:.1f} MB)"
            )
        shard_records.append(
            {
                "path": str(shard_path.relative_to(ROOT)),
                "feature_count": len(shard_features),
                "bytes": shard_size,
            }
        )

    manifest = {
        "format": "geojson-shards-v1",
        "source_monolith": str(path.relative_to(ROOT)),
        "feature_count": len(features),
        "shard_count": len(shard_records),
        "shards": shard_records,
        "usage": "Load every shard as the same logical layer; shard boundaries have no geographic meaning.",
    }
    manifest_path = path.with_name(f"{path.stem}_manifest.json")
    manifest_path.write_bytes(compact_bytes(manifest) + b"\n")
    path.unlink()
    print(
        f"sharded {path.relative_to(ROOT)}: {len(features)} features -> "
        f"{len(shards)} files"
    )
    return True


def main() -> None:
    candidates = sorted(DATA_DIR.rglob("*.geojson"))
    changed = 0
    for path in candidates:
        if path.exists() and package_file(path):
            changed += 1
    print(f"Packaging complete; sharded {changed} oversized layer(s).")


if __name__ == "__main__":
    main()
