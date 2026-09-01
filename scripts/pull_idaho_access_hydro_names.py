"""Build high-value Idaho access, hydrography, and named-place layers.

This repository is an intelligence layer, not a basemap replacement. The script
prioritizes authoritative information that adds useful, queryable context above
whatever visual basemap a consuming app chooses.

Large ArcGIS layers use an ID-first strategy: query only object IDs intersecting
Idaho, deduplicate those IDs, then fetch geometry in manageable POST batches.
That avoids slow/fragile geometry pagination across national services. All
features are finally clipped to the exact Census Idaho polygon stored in this
repository.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
    mapping,
    shape,
)
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
BOUNDARY_PATH = ROOT / "data" / "boundaries" / "idaho_census_2025.geojson"
ACCESS_DIR = ROOT / "data" / "access"
HYDRO_DIR = ROOT / "data" / "hydro"
PLACES_DIR = ROOT / "data" / "places"

USER_AGENT = "my-map-idaho/1.1 (+https://github.com/enduranceculture/my-map-idaho)"
IDAHO_BBOX = (-117.30, 41.90, -111.00, 49.10)
MAP_SIMPLIFY_TOLERANCE_DEGREES = 0.00004  # roughly 3-4 m in Idaho

SOURCES = {
    "roads": {
        "name": "USFS National Forest System Roads",
        "url": "https://apps.fs.usda.gov/ArcX/rest/services/EDW/EDW_RoadBasic_01/MapServer/0",
        "fields": (
            "objectid,rte_cn,bmp,emp,id,name,symbol_code,symbol_name,seg_length,"
            "gis_miles,jurisdiction,system,route_status,oper_maint_level,"
            "objective_maint_level,functional_class,surface_type,lanes,"
            "primary_maintainer,admin_org,service_life,level_of_service,"
            "pfsr_classification,managing_org,openforuseto,ivm_symbol,globalid"
        ),
        "chunk_size": 800,
        "tiled": True,
        "source_note": "USFS EDW National Forest System Roads.",
    },
    "recreation": {
        "name": "USFS Recreation Opportunities",
        "url": "https://apps.fs.usda.gov/ArcX/rest/services/EDW/EDW_RecreationOpportunities_01/MapServer/0",
        "fields": (
            "objectid,recareaid,recareaname,recareaurl,forestname,forestorgcode,"
            "markertype,markeractivity,markeractivitygroup,recareadescription,"
            "feedescription,operational_hours,reservation_info,restrictions,"
            "accessibility,openstatus,open_season_start,open_season_end,infra_cn"
        ),
        "chunk_size": 1000,
        "tiled": True,
        "source_note": "USFS Recreation Opportunities; upstream feed is refreshed nightly.",
    },
    "flowlines": {
        "name": "USGS 3D Hydrography Program Flowline",
        "url": "https://hydro.nationalmap.gov/arcgis/rest/services/3DHP_all/MapServer/50",
        "fields": (
            "OBJECTID,id3dhp,featuredate,mainstemid,gnisid,gnisidlabel,featuretype,"
            "featuretypelabel,lengthkm,flowdirection,flowdirectionlabel,onsurface,"
            "onsurfacelabel,streamlevel,streamorder,hydrosequence,workunitid"
        ),
        "chunk_size": 900,
        "tiled": True,
        "where": "gnisid IS NOT NULL",
        "source_note": "USGS 3DHP; named flowlines only for this intelligence layer.",
    },
    "waterbodies": {
        "name": "USGS 3D Hydrography Program Waterbody",
        "url": "https://hydro.nationalmap.gov/arcgis/rest/services/3DHP_all/MapServer/60",
        "fields": (
            "OBJECTID,id3dhp,featuredate,mainstemid,gnisid,gnisidlabel,featuretype,"
            "featuretypelabel,areasqkm,workunitid"
        ),
        "chunk_size": 900,
        "tiled": True,
        "where": "gnisid IS NOT NULL",
        "source_note": "USGS 3DHP; named waterbodies only for this intelligence layer.",
    },
    "springs": {
        "name": "USGS 3D Hydrography Program Springs",
        "url": "https://hydro.nationalmap.gov/arcgis/rest/services/3DHP_all/MapServer/20",
        "fields": (
            "OBJECTID,id3dhp,featuredate,mainstemid,universalreferenceid,gnisid,"
            "gnisidlabel,featuretype,featuretypelabel,workunitid"
        ),
        "chunk_size": 1000,
        "tiled": True,
        "where": "featuretype = 7",
        "source_note": "USGS 3DHP HydroLocation records classified as Spring.",
    },
    "landforms": {
        "name": "USGS GNIS / The National Map Gazetteer Landforms",
        "url": "https://carto-wfs.nationalmap.gov/arcgis/rest/services/geonames/FeatureServer/2",
        "fields": (
            "OBJECTID,gaz_id,gaz_name,gaz_featureclass,state_alpha,county_name,"
            "isunknowncoords,fcode"
        ),
        "chunk_size": 1000,
        "tiled": False,
        "where": "state_alpha = 'ID'",
        "source_note": "GNIS is the federal and national standard for geographic nomenclature.",
    },
}


def request_json(url: str, params: dict, retries: int = 3, timeout: int = 75) -> dict:
    """POST an ArcGIS query with bounded retries and fail closed on service errors."""
    body = urllib.parse.urlencode(params).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "User-Agent": USER_AGENT,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, dict) and payload.get("error"):
                raise RuntimeError(json.dumps(payload["error"], sort_keys=True))
            return payload
        except Exception as exc:  # noqa: BLE001 - retry network/service failures
            last_error = exc
            if attempt == retries - 1:
                break
            time.sleep(min(2**attempt, 8))
    raise RuntimeError(f"Failed ArcGIS request to {url}: {last_error}")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, separators=(",", ":"), ensure_ascii=False)
        handle.write("\n")


def load_idaho_boundary():
    with BOUNDARY_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    features = payload.get("features") or []
    if not features:
        raise RuntimeError(f"No Idaho boundary feature found in {BOUNDARY_PATH}")
    geom = shape(features[0]["geometry"])
    if not geom.is_valid:
        geom = geom.buffer(0)
    return geom


def tile_bboxes(cols: int = 3, rows: int = 4) -> list[tuple[float, float, float, float]]:
    xmin, ymin, xmax, ymax = IDAHO_BBOX
    dx = (xmax - xmin) / cols
    dy = (ymax - ymin) / rows
    return [
        (
            xmin + col * dx,
            ymin + row * dy,
            xmin + (col + 1) * dx,
            ymin + (row + 1) * dy,
        )
        for row in range(rows)
        for col in range(cols)
    ]


def query_ids(config: dict, bbox=None) -> list[int]:
    params = {
        "where": config.get("where", "1=1"),
        "returnIdsOnly": "true",
        "f": "json",
    }
    if bbox is not None:
        params.update(
            {
                "geometry": ",".join(f"{value:.6f}" for value in bbox),
                "geometryType": "esriGeometryEnvelope",
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
            }
        )
    payload = request_json(config["url"].rstrip("/") + "/query", params)
    return [int(value) for value in (payload.get("objectIds") or [])]


def collect_source_ids(config: dict) -> list[int]:
    if not config.get("tiled"):
        ids = sorted(set(query_ids(config)))
        print(f"{config['name']}: {len(ids)} Idaho IDs")
        return ids

    all_ids: set[int] = set()
    tiles = tile_bboxes()
    for index, bbox in enumerate(tiles, start=1):
        ids = query_ids(config, bbox=bbox)
        all_ids.update(ids)
        print(
            f"{config['name']}: ID tile {index}/{len(tiles)} -> {len(ids)} IDs; "
            f"{len(all_ids)} unique total"
        )
    return sorted(all_ids)


def fetch_features_by_ids(config: dict, object_ids: list[int]) -> list[dict]:
    if not object_ids:
        raise RuntimeError(f"{config['name']} returned zero Idaho IDs")

    query_url = config["url"].rstrip("/") + "/query"
    chunk_size = int(config["chunk_size"])
    features: list[dict] = []
    for start in range(0, len(object_ids), chunk_size):
        chunk = object_ids[start : start + chunk_size]
        payload = request_json(
            query_url,
            {
                "objectIds": ",".join(str(value) for value in chunk),
                "outFields": config["fields"],
                "returnGeometry": "true",
                "outSR": "4326",
                "geometryPrecision": "7",
                "f": "geojson",
            },
        )
        page = payload.get("features") or []
        features.extend(page)
        print(
            f"{config['name']}: fetched {min(start + len(chunk), len(object_ids))}/"
            f"{len(object_ids)} IDs -> {len(features)} features"
        )
    if not features:
        raise RuntimeError(f"{config['name']} returned zero features for Idaho IDs")
    return features


def fetch_source(config: dict) -> list[dict]:
    return fetch_features_by_ids(config, collect_source_ids(config))


def _linear_only(geom):
    if isinstance(geom, (LineString, MultiLineString)):
        return geom
    if isinstance(geom, GeometryCollection):
        parts = [g for g in geom.geoms if isinstance(g, (LineString, MultiLineString))]
        return unary_union(parts) if parts else None
    return None


def _polygonal_only(geom):
    if isinstance(geom, (Polygon, MultiPolygon)):
        return geom
    if isinstance(geom, GeometryCollection):
        parts = [g for g in geom.geoms if isinstance(g, (Polygon, MultiPolygon))]
        return unary_union(parts) if parts else None
    return None


def _pointlike_only(geom):
    if isinstance(geom, (Point, MultiPoint)):
        return geom
    if isinstance(geom, GeometryCollection):
        parts = [g for g in geom.geoms if isinstance(g, (Point, MultiPoint))]
        return unary_union(parts) if parts else None
    return None


def clip_features(features: list[dict], boundary, kind: str, source: dict) -> list[dict]:
    output: list[dict] = []
    for feature in features:
        geometry = feature.get("geometry")
        if not geometry:
            continue
        geom = shape(geometry)
        if not geom.is_valid:
            geom = geom.buffer(0)
        if geom.is_empty or not geom.intersects(boundary):
            continue

        result = {
            "point": _pointlike_only,
            "line": _linear_only,
            "polygon": _polygonal_only,
        }[kind](geom.intersection(boundary))
        if result is None or result.is_empty:
            continue

        props = dict(feature.get("properties") or {})
        props.update(
            {
                "source": source["name"],
                "source_url": source["url"],
                "scope": "Idaho",
            }
        )
        output.append(
            {"type": "Feature", "properties": props, "geometry": mapping(result)}
        )
    return output


def collection(features: list[dict], source: dict, layer: str, **metadata) -> dict:
    base = {
        "scope": "Idaho",
        "layer": layer,
        "source": source["name"],
        "source_url": source["url"],
        "source_note": source["source_note"],
        "feature_count": len(features),
        "clip_boundary": "US Census Bureau 2025 Idaho Cartographic Boundary",
        "retrieval_method": "ArcGIS ID-first spatial selection, chunked feature fetch, exact local Idaho clip",
    }
    base.update(metadata)
    return {"type": "FeatureCollection", "metadata": base, "features": features}


def simplify_features(
    features: list[dict], tolerance: float = MAP_SIMPLIFY_TOLERANCE_DEGREES
) -> list[dict]:
    result = []
    for feature in features:
        geom = shape(feature["geometry"])
        if isinstance(geom, (LineString, MultiLineString, Polygon, MultiPolygon)):
            geom = geom.simplify(tolerance, preserve_topology=True)
        result.append(
            {
                "type": "Feature",
                "properties": feature["properties"],
                "geometry": mapping(geom),
            }
        )
    return result


def road_access_class(props: dict) -> str:
    code = str(props.get("symbol_code") or "").strip()
    label = str(props.get("symbol_name") or "").lower()
    if code in {"517", "518", "515"}:
        return "passenger-car"
    if code == "106" or "not maintained for passenger" in label:
        return "high-clearance-or-rough"
    return "unknown"


def normalize_roads(features: list[dict]) -> list[dict]:
    for feature in features:
        props = feature["properties"]
        rte = props.get("rte_cn") or props.get("id") or props.get("objectid")
        props["road_id"] = f"usfs-road:{rte}"
        props["access_class"] = road_access_class(props)
    return features


def first_nonempty(records: list[dict], field: str):
    for record in records:
        value = record.get(field)
        if value not in (None, ""):
            return value
    return None


def aggregate_recreation(features: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    geometries: dict[str, dict] = {}
    for feature in features:
        props = feature.get("properties") or {}
        key = str(props.get("recareaid") or props.get("objectid"))
        groups.setdefault(key, []).append(props)
        geometries.setdefault(key, feature["geometry"])

    output = []
    copy_fields = [
        "recareaid",
        "recareaname",
        "recareaurl",
        "forestname",
        "forestorgcode",
        "recareadescription",
        "feedescription",
        "operational_hours",
        "reservation_info",
        "restrictions",
        "accessibility",
        "openstatus",
        "open_season_start",
        "open_season_end",
        "infra_cn",
    ]
    for key, records in groups.items():
        props = {field: first_nonempty(records, field) for field in copy_fields}
        props.update(
            {
                "site_id": f"usfs-rec:{key}",
                "activities": sorted(
                    {
                        str(record.get("markeractivity")).strip()
                        for record in records
                        if record.get("markeractivity")
                    }
                ),
                "activity_groups": sorted(
                    {
                        str(record.get("markeractivitygroup")).strip()
                        for record in records
                        if record.get("markeractivitygroup")
                    }
                ),
                "marker_types": sorted(
                    {
                        str(record.get("markertype")).strip()
                        for record in records
                        if record.get("markertype")
                    }
                ),
                "source": SOURCES["recreation"]["name"],
                "source_url": SOURCES["recreation"]["url"],
                "scope": "Idaho",
            }
        )
        output.append(
            {"type": "Feature", "properties": props, "geometry": geometries[key]}
        )
    return output


def is_trailhead(feature: dict) -> bool:
    props = feature["properties"]
    name = str(props.get("recareaname") or "").lower()
    activities = [str(item).lower() for item in props.get("activities") or []]
    return "trailhead" in name or any("trailhead" in item for item in activities)


def normalize_hydro(features: list[dict], prefix: str) -> list[dict]:
    for feature in features:
        props = feature["properties"]
        source_id = props.get("id3dhp") or props.get("OBJECTID") or props.get("objectid")
        props["hydro_id"] = f"3dhp:{prefix}:{source_id}"
        props["name"] = props.get("gnisidlabel")
    return features


def normalize_landforms(features: list[dict]) -> list[dict]:
    for feature in features:
        props = feature["properties"]
        gaz_id = props.get("gaz_id") or props.get("OBJECTID")
        props["place_id"] = f"gnis:{gaz_id}"
        props["name"] = props.get("gaz_name")
        props["feature_class"] = props.get("gaz_featureclass")
        props.update(
            {
                "source": SOURCES["landforms"]["name"],
                "source_url": SOURCES["landforms"]["url"],
                "scope": "Idaho",
            }
        )
    return features


def main() -> None:
    boundary = load_idaho_boundary()
    ACCESS_DIR.mkdir(parents=True, exist_ok=True)
    HYDRO_DIR.mkdir(parents=True, exist_ok=True)
    PLACES_DIR.mkdir(parents=True, exist_ok=True)

    roads = normalize_roads(
        clip_features(fetch_source(SOURCES["roads"]), boundary, "line", SOURCES["roads"])
    )
    write_json(
        ACCESS_DIR / "usfs_roads_idaho.geojson",
        collection(
            roads,
            SOURCES["roads"],
            "usfs-roads",
            map_facing=False,
            geometry_precision="WGS84 service output retained to 7 decimal places",
        ),
    )
    write_json(
        ACCESS_DIR / "usfs_roads_idaho_map.geojson",
        collection(
            simplify_features(roads),
            SOURCES["roads"],
            "usfs-roads",
            map_facing=True,
            simplification_tolerance_degrees=MAP_SIMPLIFY_TOLERANCE_DEGREES,
        ),
    )
    print(f"saved USFS roads: {len(roads)} Idaho segments")

    recreation_raw = clip_features(
        fetch_source(SOURCES["recreation"]), boundary, "point", SOURCES["recreation"]
    )
    recreation = aggregate_recreation(recreation_raw)
    trailheads = [feature for feature in recreation if is_trailhead(feature)]
    write_json(
        ACCESS_DIR / "usfs_recreation_opportunities_idaho.geojson",
        collection(
            recreation,
            SOURCES["recreation"],
            "usfs-recreation-opportunities",
            aggregation="One feature per RECAREAID; activities consolidated from duplicate opportunity rows.",
        ),
    )
    write_json(
        ACCESS_DIR / "usfs_trailheads_idaho.geojson",
        collection(
            trailheads,
            SOURCES["recreation"],
            "usfs-trailheads",
            derivation="Subset whose name or published activity contains 'Trailhead'.",
        ),
    )
    print(f"saved recreation sites: {len(recreation)}; trailheads: {len(trailheads)}")

    named_flowlines = normalize_hydro(
        clip_features(
            fetch_source(SOURCES["flowlines"]), boundary, "line", SOURCES["flowlines"]
        ),
        "flowline",
    )
    write_json(
        HYDRO_DIR / "usgs_3dhp_named_flowlines_idaho.geojson",
        collection(named_flowlines, SOURCES["flowlines"], "3dhp-named-flowlines"),
    )
    write_json(
        HYDRO_DIR / "usgs_3dhp_named_flowlines_idaho_map.geojson",
        collection(
            simplify_features(named_flowlines),
            SOURCES["flowlines"],
            "3dhp-named-flowlines",
            map_facing=True,
            simplification_tolerance_degrees=MAP_SIMPLIFY_TOLERANCE_DEGREES,
        ),
    )

    named_waterbodies = normalize_hydro(
        clip_features(
            fetch_source(SOURCES["waterbodies"]),
            boundary,
            "polygon",
            SOURCES["waterbodies"],
        ),
        "waterbody",
    )
    write_json(
        HYDRO_DIR / "usgs_3dhp_named_waterbodies_idaho.geojson",
        collection(named_waterbodies, SOURCES["waterbodies"], "3dhp-named-waterbodies"),
    )
    write_json(
        HYDRO_DIR / "usgs_3dhp_named_waterbodies_idaho_map.geojson",
        collection(
            simplify_features(named_waterbodies),
            SOURCES["waterbodies"],
            "3dhp-named-waterbodies",
            map_facing=True,
            simplification_tolerance_degrees=MAP_SIMPLIFY_TOLERANCE_DEGREES,
        ),
    )

    springs = normalize_hydro(
        clip_features(
            fetch_source(SOURCES["springs"]), boundary, "point", SOURCES["springs"]
        ),
        "spring",
    )
    write_json(
        HYDRO_DIR / "usgs_3dhp_springs_idaho.geojson",
        collection(springs, SOURCES["springs"], "3dhp-springs"),
    )
    print(
        f"saved 3DHP named flowlines: {len(named_flowlines)}; "
        f"named waterbodies: {len(named_waterbodies)}; springs: {len(springs)}"
    )

    landforms = normalize_landforms(
        clip_features(
            fetch_source(SOURCES["landforms"]), boundary, "point", SOURCES["landforms"]
        )
    )
    write_json(
        PLACES_DIR / "usgs_gnis_landforms_idaho.geojson",
        collection(
            landforms,
            SOURCES["landforms"],
            "gnis-landforms",
            examples="Summits, gaps, valleys, canyons, ridges and other named physical landforms.",
        ),
    )
    print(f"saved GNIS landforms: {len(landforms)}")


if __name__ == "__main__":
    main()
