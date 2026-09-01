"""Complete the reusable Idaho base-intelligence layer.

Adds three authoritative statewide sources:
- USGS PAD-US 4.1 fee/public-land managers;
- USFS Ranger District boundaries;
- rich USFS recreation infrastructure sites.

All geometry is clipped to the exact Census Idaho boundary already versioned in this
repo. Source-faithful and lightweight map derivatives are kept separate.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from shapely.geometry import (
    GeometryCollection,
    MultiPolygon,
    Point,
    Polygon,
    mapping,
    shape,
)

ROOT = Path(__file__).resolve().parent.parent
BOUNDARY_PATH = ROOT / "data" / "boundaries" / "idaho_census_2025.geojson"
BOUNDARY_DIR = ROOT / "data" / "boundaries"
ACCESS_DIR = ROOT / "data" / "access"
IDAHO_BBOX = (-117.30, 41.90, -111.00, 49.10)
MAP_SIMPLIFY_TOLERANCE_DEGREES = 0.00008
MAX_WORKERS = 4
USER_AGENT = "my-map-idaho/1.3 (+https://github.com/enduranceculture/my-map-idaho)"

PADUS_URL = (
    "https://services.arcgis.com/v01gqwM5QqNysAAi/ArcGIS/rest/services/"
    "Fee_Managers_PADUS/FeatureServer/0"
)
RANGER_URL = (
    "https://apps.fs.usda.gov/arcx/rest/services/EDW/"
    "EDW_RangerDistricts_01/MapServer/0"
)
REC_SITE_URL = (
    "https://apps.fs.usda.gov/arcx/rest/services/EDW/"
    "EDW_RecInfraRecreationSites_02/MapServer/0"
)

PADUS_FIELDS = (
    "OBJECTID,FeatClass,Category,Own_Type,Own_Name,Loc_Own,Mang_Type,Mang_Name,"
    "Loc_Mang,Des_Tp,Loc_Ds,Unit_Nm,Loc_Nm,State_Nm,Agg_Src,GIS_Src,Src_Date,"
    "GIS_Acres,Source_PAID,Pub_Access,Access_Src,Access_Dt,GAP_Sts,Date_Est,Comments"
)
REC_FIELDS = (
    "objectid,site_cn,managing_org,site_id,site_name,site_type,activity_type_list,"
    "service_type_list,seasonal_operational_status,op_status_reason,development_status,"
    "development_scale,total_capacity,fee_charged,fee_type,recarea_name,"
    "recarea_description,information_center,official_designation,fee_description,"
    "operational_hours,open_season,best_season,busiest_season,usage_level,pack_in_out,"
    "public_site_name,alternative_name,rec1stop_url,usda_portal_url,important_info,"
    "rentals_and_guides,passes,permit_information,restrictions,closest_towns,"
    "water_availability,restroom_availability,operated_by,season_description,directions,"
    "maximum_elevation,minimum_elevation,season_name,site_season_start_date,"
    "site_season_end_date,max_nbr_people,passes_accepted,latitude,longitude,"
    "infra_last_update,edw_last_modify,globalid"
)
PUBLIC_MANAGER_TYPES = {"FED", "TRIB", "STAT", "LOC", "DIST", "JNT", "TERR"}


def request_json(url: str, params: dict, attempts: int = 4) -> dict:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{query}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    last_error: object = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, dict) and payload.get("error"):
                last_error = payload["error"]
            else:
                return payload
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
        if attempt < attempts - 1:
            time.sleep(2**attempt)
    raise RuntimeError(f"Failed ArcGIS request to {url}: {last_error}")


def query_ids(url: str, where: str = "1=1") -> list[int]:
    payload = request_json(
        f"{url}/query",
        {
            "where": where,
            "geometry": ",".join(str(value) for value in IDAHO_BBOX),
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "returnIdsOnly": "true",
            "f": "json",
        },
    )
    ids = sorted({int(value) for value in (payload.get("objectIds") or [])})
    if not ids:
        raise RuntimeError(f"No Idaho object IDs returned from {url}")
    return ids


def fetch_features(
    url: str,
    ids: list[int],
    fields: str,
    chunk_size: int = 700,
) -> list[dict]:
    chunks = [ids[start : start + chunk_size] for start in range(0, len(ids), chunk_size)]

    def fetch_chunk(chunk: list[int]) -> list[dict]:
        payload = request_json(
            f"{url}/query",
            {
                "objectIds": ",".join(str(value) for value in chunk),
                "outFields": fields,
                "returnGeometry": "true",
                "outSR": "4326",
                "geometryPrecision": "7",
                "f": "geojson",
            },
        )
        return payload.get("features") or []

    pages: list[list[dict] | None] = [None] * len(chunks)
    workers = min(MAX_WORKERS, len(chunks))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch_chunk, chunk): index for index, chunk in enumerate(chunks)}
        for future in as_completed(futures):
            pages[futures[future]] = future.result()
    features = [feature for page in pages if page for feature in page]
    if not features:
        raise RuntimeError(f"No features returned from {url}")
    return features


def load_idaho_boundary():
    doc = json.loads(BOUNDARY_PATH.read_text(encoding="utf-8"))
    geometries = [shape(feature["geometry"]) for feature in doc["features"]]
    boundary = geometries[0]
    for geometry in geometries[1:]:
        boundary = boundary.union(geometry)
    return boundary


def polygonal_only(geometry):
    if isinstance(geometry, (Polygon, MultiPolygon)):
        return geometry
    if isinstance(geometry, GeometryCollection):
        parts = [
            part
            for part in geometry.geoms
            if isinstance(part, (Polygon, MultiPolygon))
        ]
        if not parts:
            return None
        merged = parts[0]
        for part in parts[1:]:
            merged = merged.union(part)
        return merged
    return None


def clip_polygons(features: list[dict], boundary) -> list[dict]:
    clipped = []
    for feature in features:
        geometry = shape(feature["geometry"])
        if not geometry.intersects(boundary):
            continue
        geometry = polygonal_only(geometry.intersection(boundary))
        if geometry is None or geometry.is_empty:
            continue
        clipped.append(
            {
                "type": "Feature",
                "geometry": mapping(geometry),
                "properties": feature.get("properties") or {},
            }
        )
    return clipped


def clip_points(features: list[dict], boundary) -> list[dict]:
    clipped = []
    for feature in features:
        geometry = shape(feature["geometry"])
        if not isinstance(geometry, Point) or not boundary.covers(geometry):
            continue
        clipped.append(
            {
                "type": "Feature",
                "geometry": mapping(geometry),
                "properties": feature.get("properties") or {},
            }
        )
    return clipped


def feature_collection(
    layer: str,
    source: str,
    features: list[dict],
    note: str,
) -> dict:
    return {
        "type": "FeatureCollection",
        "metadata": {
            "layer": layer,
            "scope": "Idaho",
            "feature_count": len(features),
            "source": source,
            "note": note,
        },
        "features": features,
    }


def simplify_polygons(features: list[dict], keep_fields: tuple[str, ...]) -> list[dict]:
    simplified = []
    for feature in features:
        geometry = shape(feature["geometry"]).simplify(
            MAP_SIMPLIFY_TOLERANCE_DEGREES,
            preserve_topology=True,
        )
        properties = feature.get("properties") or {}
        simplified.append(
            {
                "type": "Feature",
                "geometry": mapping(geometry),
                "properties": {key: properties.get(key) for key in keep_fields},
            }
        )
    return simplified


def slim_points(features: list[dict], keep_fields: tuple[str, ...]) -> list[dict]:
    slimmed = []
    for feature in features:
        properties = feature.get("properties") or {}
        slimmed.append(
            {
                "type": "Feature",
                "geometry": feature["geometry"],
                "properties": {key: properties.get(key) for key in keep_fields},
            }
        )
    return slimmed


def write_geojson(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"saved {path.relative_to(ROOT)}: {len(doc['features'])} features")


def pull_padus(boundary) -> None:
    ids = query_ids(PADUS_URL)
    source = fetch_features(PADUS_URL, ids, PADUS_FIELDS, chunk_size=600)
    public = [
        feature
        for feature in source
        if (feature.get("properties") or {}).get("Mang_Type") in PUBLIC_MANAGER_TYPES
    ]
    clipped = clip_polygons(public, boundary)
    if not clipped:
        raise RuntimeError("PAD-US public-land manager layer clipped to zero features")
    map_features = simplify_polygons(
        clipped,
        (
            "OBJECTID",
            "Own_Type",
            "Own_Name",
            "Loc_Own",
            "Mang_Type",
            "Mang_Name",
            "Loc_Mang",
            "Unit_Nm",
            "Loc_Nm",
            "Pub_Access",
            "GIS_Acres",
            "Source_PAID",
        ),
    )
    source_name = "USGS Protected Areas Database of the United States (PAD-US) 4.1"
    note = (
        "Fee/public-land manager view. Private, NGO, and unknown manager types are "
        "excluded from this base public-land layer."
    )
    write_geojson(
        BOUNDARY_DIR / "usgs_padus4_1_public_land_managers_idaho.geojson",
        feature_collection("public-land-managers", source_name, clipped, note),
    )
    write_geojson(
        BOUNDARY_DIR / "usgs_padus4_1_public_land_managers_idaho_map.geojson",
        feature_collection("public-land-managers-map", source_name, map_features, note),
    )


def pull_ranger_districts(boundary) -> None:
    ids = query_ids(RANGER_URL)
    clipped = clip_polygons(
        fetch_features(RANGER_URL, ids, "*", chunk_size=500),
        boundary,
    )
    if not clipped:
        raise RuntimeError("USFS Ranger District layer clipped to zero features")
    map_features = simplify_polygons(
        clipped,
        (
            "objectid",
            "rangerdistrictid",
            "region",
            "forestnumber",
            "forestname",
            "districtnumber",
            "districtname",
            "districtorgcode",
        ),
    )
    source_name = "USFS EDW Ranger District Boundaries"
    note = "Current Forest Service Ranger District boundaries clipped exactly to Idaho."
    write_geojson(
        BOUNDARY_DIR / "usfs_ranger_districts_idaho.geojson",
        feature_collection("ranger-districts", source_name, clipped, note),
    )
    write_geojson(
        BOUNDARY_DIR / "usfs_ranger_districts_idaho_map.geojson",
        feature_collection("ranger-districts-map", source_name, map_features, note),
    )


def pull_rich_recreation(boundary) -> None:
    ids = query_ids(REC_SITE_URL)
    clipped = clip_points(
        fetch_features(REC_SITE_URL, ids, REC_FIELDS, chunk_size=700),
        boundary,
    )
    if not clipped:
        raise RuntimeError("USFS rich recreation layer clipped to zero features")
    map_features = slim_points(
        clipped,
        (
            "objectid",
            "site_cn",
            "site_id",
            "site_name",
            "site_type",
            "managing_org",
            "activity_type_list",
            "service_type_list",
            "seasonal_operational_status",
            "fee_charged",
            "open_season",
            "usage_level",
            "water_availability",
            "restroom_availability",
            "usda_portal_url",
        ),
    )
    trailheads = [
        feature
        for feature in clipped
        if "TRAILHEAD"
        in str((feature.get("properties") or {}).get("site_type") or "").upper()
    ]
    source_name = "USFS EDW Recreation Infrastructure Sites"
    note = (
        "Public-facing recreation infrastructure with activity/service lists, "
        "operations, fees, seasons, permits, restrictions, water/restrooms, and "
        "directions when published."
    )
    write_geojson(
        ACCESS_DIR / "usfs_recreation_sites_rich_idaho.geojson",
        feature_collection("recreation-sites-rich", source_name, clipped, note),
    )
    write_geojson(
        ACCESS_DIR / "usfs_recreation_sites_rich_idaho_map.geojson",
        feature_collection("recreation-sites-rich-map", source_name, map_features, note),
    )
    if trailheads:
        write_geojson(
            ACCESS_DIR / "usfs_trailheads_rich_idaho.geojson",
            feature_collection("trailheads-rich", source_name, trailheads, note),
        )


def main() -> None:
    boundary = load_idaho_boundary()
    pull_padus(boundary)
    pull_ranger_districts(boundary)
    pull_rich_recreation(boundary)


if __name__ == "__main__":
    main()
