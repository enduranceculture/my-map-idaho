"""Build a lightweight downstream-directed line for one named USGS river.

The NHDPlus HR network stores FromNode at the upstream end and ToNode at the
downstream end of each flowline. Only features whose FlowDir is WithDigitized
are accepted, so the merged coordinate order can drive repeatable map arrows.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

SERVICE = (
    "https://hydro.nationalmap.gov/arcgis/rest/services/"
    "NHDPlus_HR/MapServer/3"
)
QUERY_URL = SERVICE + "/query"
USER_AGENT = (
    "my-map-idaho/1.3 "
    "(+https://github.com/enduranceculture/my-map-idaho)"
)
FIELDS = (
    "permanent_identifier,gnis_id,gnis_name,lengthkm,reachcode,fcode,"
    "nhdplusid,fromnode,tonode,streamorde,levelpathi,pathlength,"
    "arbolatesu,maxelevsmo,minelevsmo"
)


def request_json(params: dict[str, str], retries: int = 3) -> dict:
    """POST one ArcGIS query with bounded retries."""
    body = urllib.parse.urlencode(params).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(
                QUERY_URL,
                data=body,
                headers={
                    "User-Agent": USER_AGENT,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=75) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("error"):
                raise RuntimeError(json.dumps(payload["error"], sort_keys=True))
            return payload
        except Exception as exc:  # noqa: BLE001 - retry service failures
            last_error = exc
            if attempt < retries - 1:
                time.sleep(min(2**attempt, 8))
    raise RuntimeError(f"USGS query failed: {last_error}")


def sql_text(value: str) -> str:
    return value.replace("'", "''")


def source_object_ids(name: str, gnis_id: str | None) -> list[int]:
    clauses = [
        f"gnis_name='{sql_text(name)}'",
        "innetwork=1",
        "flowdir=1",
    ]
    if gnis_id:
        clauses.append(f"gnis_id='{sql_text(gnis_id)}'")
    payload = request_json(
        {
            "where": " AND ".join(clauses),
            "returnIdsOnly": "true",
            "f": "json",
        }
    )
    ids = sorted({int(value) for value in payload.get("objectIds") or []})
    if not ids:
        raise RuntimeError(f"No downstream-digitized USGS flowlines found for {name!r}")
    return ids


def fetch_features(object_ids: list[int]) -> list[dict]:
    features: list[dict] = []
    for start in range(0, len(object_ids), 800):
        chunk = object_ids[start : start + 800]
        payload = request_json(
            {
                "objectIds": ",".join(str(value) for value in chunk),
                "outFields": FIELDS,
                "returnGeometry": "true",
                "returnZ": "false",
                "returnM": "false",
                "outSR": "4326",
                "geometryPrecision": "5",
                "maxAllowableOffset": "0.00005",
                "f": "geojson",
            }
        )
        features.extend(payload.get("features") or [])
    if len(features) != len(object_ids):
        raise RuntimeError(
            f"USGS returned {len(features)} features for {len(object_ids)} IDs"
        )
    return features


def select_level_path(
    features: list[dict], requested: str | None
) -> tuple[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for feature in features:
        groups[str(feature["properties"]["levelpathi"])].append(feature)

    if requested is not None:
        selected = groups.get(requested)
        if not selected:
            raise RuntimeError(
                f"Level path {requested} is absent; available: {sorted(groups)}"
            )
        return requested, selected

    if len(groups) != 1:
        choices = ", ".join(
            f"{key} ({len(value)} segments)"
            for key, value in sorted(groups.items())
        )
        raise RuntimeError(
            "River name spans multiple level paths; pass --level-path-id. "
            f"Available: {choices}"
        )
    return next(iter(groups.items()))


def ordered_chain(features: list[dict]) -> list[dict]:
    by_from: dict[str, dict] = {}
    downstream_nodes: set[str] = set()
    for feature in features:
        properties = feature["properties"]
        from_node = str(properties["fromnode"])
        to_node = str(properties["tonode"])
        if from_node in by_from:
            raise RuntimeError(f"Ambiguous branch at FromNode {from_node}")
        by_from[from_node] = feature
        downstream_nodes.add(to_node)

    starts = [
        feature
        for feature in features
        if str(feature["properties"]["fromnode"]) not in downstream_nodes
    ]
    if len(starts) != 1:
        raise RuntimeError(f"Expected one upstream start, found {len(starts)}")

    ordered: list[dict] = []
    seen: set[str] = set()
    current: dict | None = starts[0]
    while current is not None:
        feature_id = str(current["properties"]["nhdplusid"])
        if feature_id in seen:
            raise RuntimeError("Cycle detected in selected level path")
        seen.add(feature_id)
        ordered.append(current)
        current = by_from.get(str(current["properties"]["tonode"]))

    if len(ordered) != len(features):
        raise RuntimeError(
            f"Selected level path is disconnected: {len(ordered)}/{len(features)}"
        )
    return ordered


def merge_coordinates(features: list[dict]) -> list[list[float]]:
    merged: list[list[float]] = []
    for feature in features:
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "LineString":
            raise RuntimeError("Directional river source must contain LineStrings")
        coordinates = geometry.get("coordinates") or []
        if len(coordinates) < 2:
            raise RuntimeError("Flowline contains fewer than two coordinates")
        if merged:
            if merged[-1] != coordinates[0]:
                raise RuntimeError("Flowline coordinate order breaks node continuity")
            merged.extend(coordinates[1:])
        else:
            merged.extend(coordinates)
    return merged


def output_document(
    name: str,
    gnis_id: str | None,
    level_path_id: str,
    features: list[dict],
    retrieved: str,
    source_updated: str | None,
) -> dict:
    ordered = ordered_chain(features)
    coordinates = merge_coordinates(ordered)
    length_km = round(
        sum(float(feature["properties"].get("lengthkm") or 0) for feature in ordered),
        3,
    )
    properties = {
        "name": name,
        "display_name": name,
        "flow_direction": "Downstream — follow arrows",
        "direction_basis": (
            "USGS NHDPlus HR FlowDir is WithDigitized; coordinates run from "
            "the upstream FromNode to the downstream ToNode."
        ),
        "length_km": length_km,
        "source_segment_count": len(ordered),
        "gnis_id": gnis_id,
        "level_path_id": level_path_id,
        "source": (
            "U.S. Geological Survey · National Hydrography Dataset Plus "
            "High Resolution"
        ),
        "source_retrieved": retrieved,
        "source_url": SERVICE,
        "accuracy_note": (
            "Official public hydrography generalized for browser display. "
            "Flow direction is authoritative for this path; verify current "
            "local conditions for navigation."
        ),
    }
    if source_updated:
        properties["source_updated"] = source_updated
    return {
        "type": "FeatureCollection",
        "name": f"{name.lower().replace(' ', '_')}_flow_v1",
        "features": [
            {
                "type": "Feature",
                "id": f"usgs-nhdplus-hr-{name.lower().replace(' ', '-')}",
                "properties": properties,
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates,
                },
            }
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--gnis-id")
    parser.add_argument("--level-path-id")
    parser.add_argument("--retrieved", required=True)
    parser.add_argument("--source-updated")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    object_ids = source_object_ids(args.name, args.gnis_id)
    features = fetch_features(object_ids)
    level_path_id, selected = select_level_path(features, args.level_path_id)
    document = output_document(
        args.name,
        args.gnis_id,
        level_path_id,
        selected,
        args.retrieved,
        args.source_updated,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, separators=(",", ":"), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    feature = document["features"][0]
    print(
        f"Wrote {args.output}: {feature['properties']['source_segment_count']} "
        f"segments, {feature['properties']['length_km']} km, "
        f"{len(feature['geometry']['coordinates'])} coordinates"
    )


if __name__ == "__main__":
    main()
