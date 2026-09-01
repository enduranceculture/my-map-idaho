"""Build authoritative Idaho foundation layers from public GIS sources.

The script intentionally avoids ArcGIS spatial filters for the mature/old-growth
service because that endpoint has intermittently rejected spatial queries even
while ordinary pagination remained healthy. Instead it downloads authoritative
features in stable pages and clips them locally to Idaho.

Outputs:
  data/boundaries/idaho_census_2025.geojson
  data/boundaries/usfs_administrative_forests_idaho.geojson
  data/boundaries/usfs_administrative_forests_idaho_map.geojson
  data/boundaries/usfs_wilderness_idaho.geojson
  data/boundaries/usfs_wilderness_idaho_map.geojson
  data/old-growth/usda_mature_old_growth_firesheds_idaho.geojson
  data/old-growth/usda_mature_old_growth_firesheds_idaho_map.geojson
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, mapping, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
BOUNDARY_DIR = ROOT / "data" / "boundaries"
OLD_GROWTH_DIR = ROOT / "data" / "old-growth"

IDAHO_BOUNDARY_SEED = (
    "https://raw.githubusercontent.com/enduranceculture/forest-atlas-v2/"
    "main/scripts/lib/idaho-boundary.geojson"
)
IDAHO_BOUNDARY_SOURCE = (
    "US Census Bureau 2025 Cartographic Boundary Files, States, 1:500,000"
)
IDAHO_BOUNDARY_SOURCE_URL = (
    "https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_us_state_500k.zip"
)

SOURCES = {
    "forests": {
        "name": "USFS Administrative Forest Boundaries",
        "url": (
            "https://apps.fs.usda.gov/arcx/rest/services/EDW/"
            "EDW_ForestSystemBoundaries_01/MapServer/0"
        ),
        "fields": (
            "objectid,adminforestid,region,forestnumber,forestorgcode,"
            "forestname,gis_acres"
        ),
        "page_size": 2000,
    },
    "wilderness": {
        "name": "USFS National Wilderness Areas",
        "url": (
            "https://apps.fs.usda.gov/ArcX/rest/services/EDW/"
            "EDW_Wilderness_02/MapServer/0"
        ),
        "fields": (
            "objectid,wildernessid,wildernessname,areaid,boundarystatus,"
            "gis_acres,wid"
        ),
        "page_size": 2000,
    },
    "old_growth": {
        "name": "USDA Forest Service Fireshed Mature and Old Growth Area",
        "url": (
            "https://apps.fs.usda.gov/fsgisx02/rest/services/wo_nfs_gstc/"
            "WO_OSC_GapAnalysis_OldGrowthAndMatureForests/MapServer/29"
        ),
        "fields": (
            "OBJECTID,Fireshed_Name,MajRegion,MATURE_ACRES,MATURE_SE_PERC,"
            "OLD_GROWTH_ACRES,OLD_GROWTH_SE_PERC,ForestType,Division,"
            "Nine_Class,Trimmed_Area"
        ),
        "page_size": 200,
    },
}

MAP_SIMPLIFY_TOLERANCE_DEGREES = 0.00008
USER_AGENT = "my-map-idaho/1.0 (+https://github.com/enduranceculture/my-map-idaho)"


def fetch_json(url: str, retries: int = 6, timeout: int = 120) -> dict:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, dict) and payload.get("error"):
                raise RuntimeError(json.dumps(payload["error"], sort_keys=True))
            return payload
        except Exception as exc:  # noqa: BLE001 - retry network/service failures
            last_error = exc
            if attempt == retries - 1:
                break
            time.sleep(min(2 ** attempt, 20))
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def write_json(path: Path, payload: dict, compact: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        if compact:
            json.dump(payload, handle, separators=(",", ":"))
        else:
            json.dump(payload, handle, indent=2)
            handle.write("\n")


def load_idaho_boundary() -> tuple[dict, object]:
    raw = fetch_json(IDAHO_BOUNDARY_SEED)
    features = raw.get("features") or []
    if not features:
        raise RuntimeError("Idaho boundary seed contains no features")
    feature = next(
        (
            item
            for item in features
            if str((item.get("properties") or {}).get("GEOID")) == "16"
        ),
        features[0],
    )
    properties = dict(feature.get("properties") or {})
    properties.update(
        {
            "source": IDAHO_BOUNDARY_SOURCE,
            "source_url": IDAHO_BOUNDARY_SOURCE_URL,
            "source_seed": IDAHO_BOUNDARY_SEED,
        }
    )
    normalized = {
        "type": "FeatureCollection",
        "metadata": {
            "scope": "Idaho",
            "source": IDAHO_BOUNDARY_SOURCE,
            "source_url": IDAHO_BOUNDARY_SOURCE_URL,
            "seed_copy": IDAHO_BOUNDARY_SEED,
        },
        "features": [
            {
                "type": "Feature",
                "properties": properties,
                "geometry": feature["geometry"],
            }
        ],
    }
    geom = shape(feature["geometry"])
    if not geom.is_valid:
        geom = geom.buffer(0)
    return normalized, geom


def fetch_arcgis_features(config: dict) -> list[dict]:
    query_url = config["url"].rstrip("/") + "/query"
    page_size = int(config["page_size"])
    fields = config["fields"]
    offset = 0
    features: list[dict] = []

    while True:
        params = {
            "where": "1=1",
            "outFields": fields,
            "returnGeometry": "true",
            "outSR": "4326",
            "orderByFields": "OBJECTID ASC",
            "resultOffset": str(offset),
            "resultRecordCount": str(page_size),
            "f": "geojson",
        }
        payload = fetch_json(query_url + "?" + urllib.parse.urlencode(params))
        page = payload.get("features") or []
        if not page:
            break
        features.extend(page)
        print(f"{config['name']}: fetched {len(features)} features")
        if len(page) < page_size:
            break
        offset += len(page)

    if not features:
        raise RuntimeError(f"{config['name']} returned zero features")
    return features


def polygonal_only(geometry):
    if isinstance(geometry, (Polygon, MultiPolygon)):
        return geometry
    if isinstance(geometry, GeometryCollection):
        parts = [item for item in geometry.geoms if isinstance(item, (Polygon, MultiPolygon))]
        if not parts:
            return None
        return unary_union(parts)
    return None


def clip_features(features: list[dict], boundary, source: dict) -> list[dict]:
    clipped: list[dict] = []
    for feature in features:
        geometry = feature.get("geometry")
        if not geometry:
            continue
        geom = shape(geometry)
        if not geom.is_valid:
            geom = geom.buffer(0)
        if geom.is_empty or not geom.intersects(boundary):
            continue
        result = polygonal_only(geom.intersection(boundary))
        if result is None or result.is_empty:
            continue

        properties = dict(feature.get("properties") or {})
        properties.update(
            {
                "source": source["name"],
                "source_url": source["url"],
                "scope": "Idaho",
            }
        )
        clipped.append(
            {
                "type": "Feature",
                "properties": properties,
                "geometry": mapping(result),
            }
        )
    return clipped


def feature_collection(features: list[dict], source: dict) -> dict:
    return {
        "type": "FeatureCollection",
        "metadata": {
            "scope": "Idaho",
            "source": source["name"],
            "source_url": source["url"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "feature_count": len(features),
            "clip_boundary": IDAHO_BOUNDARY_SOURCE,
            "method": "authoritative national ArcGIS pagination, then exact local clip to Idaho",
        },
        "features": features,
    }


def simplified_collection(collection: dict) -> dict:
    simplified = []
    for feature in collection["features"]:
        geom = shape(feature["geometry"])
        reduced = geom.simplify(MAP_SIMPLIFY_TOLERANCE_DEGREES, preserve_topology=True)
        simplified.append(
            {
                "type": "Feature",
                "properties": feature["properties"],
                "geometry": mapping(reduced),
            }
        )
    metadata = dict(collection["metadata"])
    metadata.update(
        {
            "map_facing": True,
            "simplification_tolerance_degrees": MAP_SIMPLIFY_TOLERANCE_DEGREES,
        }
    )
    return {"type": "FeatureCollection", "metadata": metadata, "features": simplified}


def save_layer(raw_path: Path, map_path: Path, features: list[dict], source: dict) -> None:
    collection = feature_collection(features, source)
    write_json(raw_path, collection)
    write_json(map_path, simplified_collection(collection))
    print(
        f"saved {raw_path.relative_to(ROOT)} ({len(features)} features) and "
        f"{map_path.relative_to(ROOT)}"
    )


def main() -> None:
    BOUNDARY_DIR.mkdir(parents=True, exist_ok=True)
    OLD_GROWTH_DIR.mkdir(parents=True, exist_ok=True)

    boundary_collection, boundary_geom = load_idaho_boundary()
    write_json(BOUNDARY_DIR / "idaho_census_2025.geojson", boundary_collection, compact=False)

    forest_features = clip_features(
        fetch_arcgis_features(SOURCES["forests"]), boundary_geom, SOURCES["forests"]
    )
    save_layer(
        BOUNDARY_DIR / "usfs_administrative_forests_idaho.geojson",
        BOUNDARY_DIR / "usfs_administrative_forests_idaho_map.geojson",
        forest_features,
        SOURCES["forests"],
    )

    wilderness_features = clip_features(
        fetch_arcgis_features(SOURCES["wilderness"]), boundary_geom, SOURCES["wilderness"]
    )
    save_layer(
        BOUNDARY_DIR / "usfs_wilderness_idaho.geojson",
        BOUNDARY_DIR / "usfs_wilderness_idaho_map.geojson",
        wilderness_features,
        SOURCES["wilderness"],
    )

    old_growth_features = clip_features(
        fetch_arcgis_features(SOURCES["old_growth"]), boundary_geom, SOURCES["old_growth"]
    )
    save_layer(
        OLD_GROWTH_DIR / "usda_mature_old_growth_firesheds_idaho.geojson",
        OLD_GROWTH_DIR / "usda_mature_old_growth_firesheds_idaho_map.geojson",
        old_growth_features,
        SOURCES["old_growth"],
    )


if __name__ == "__main__":
    main()
