"""Pull USFS National Forest System trail data and save as GeoJSON layers.

Source: USFS Enterprise Data Warehouse (public domain), updated daily by USFS.
https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0

Add more regions to REGIONS to expand coverage. Run from repo root:
    python scripts/pull_usfs_trails.py
"""
import json
import os
import time
import urllib.parse
import urllib.request

BASE = "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0/query"

# region_name -> bbox as 'min_lon,min_lat,max_lon,max_lat' (WGS84)
REGIONS = {
    "woodriver_sawtooth": "-115.2,43.3,-114.0,44.3",
}

# Keep the raw layers rich enough for future trail intelligence. trail_cn is the
# USFS control number; objectid is retained as a source-record/segment identifier.
FIELDS = (
    "objectid,trail_cn,trail_name,trail_no,trail_type,trail_class,gis_miles,trail_surface,"
    "typical_trail_grade,typical_tread_width,national_trail_designation,"
    "terra_motorized,allowed_terra_use,bicycle_managed,bicycle_accpt,"
    "bicycle_disc,bicycle_restricted,e_bike_class1_managed,"
    "motorcycle_managed,admin_org,managing_org"
)

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "trails")

# ~4 m in latitude around central Idaho. This keeps every source segment and its
# true endpoints while making the all-trails browser layer far cheaper to parse.
MAP_SIMPLIFY_TOLERANCE_DEGREES = 0.00004

MAP_PROPERTY_FIELDS = (
    "trail_name",
    "trail_no",
    "trail_class",
    "gis_miles",
    "trail_surface",
    "typical_trail_grade",
    "typical_tread_width",
    "admin_org",
    "managing_org",
)


def fetch_region(bbox):
    features, offset = [], 0
    while True:
        params = {
            "geometry": bbox,
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "where": "1=1",
            "outFields": FIELDS,
            "returnGeometry": "true",
            "outSR": "4326",
            "resultOffset": str(offset),
            "resultRecordCount": "500",
            "f": "geojson",
        }
        response = urllib.request.urlopen(
            BASE + "?" + urllib.parse.urlencode(params), timeout=120
        )
        feats = json.loads(response.read().decode()).get("features", [])
        features.extend(feats)
        if len(feats) < 500:
            return features
        offset += 500
        time.sleep(1)


def is_bike(props):
    return bool(props.get("bicycle_managed") or props.get("bicycle_accpt"))


def bike_status(props):
    """Normalize USFS management fields without inventing access where data is blank."""
    if props.get("bicycle_restricted"):
        return "restricted"
    if props.get("bicycle_disc"):
        return "discouraged"
    if props.get("bicycle_managed") or props.get("bicycle_accpt"):
        return "confirmed"
    return "unknown"


def _distance_sq_to_segment(point, start, end):
    x, y = point[:2]
    x1, y1 = start[:2]
    x2, y2 = end[:2]
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return (x - x1) ** 2 + (y - y1) ** 2
    t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
    px = x1 + t * dx
    py = y1 + t * dy
    return (x - px) ** 2 + (y - py) ** 2


def simplify_line(points, tolerance=MAP_SIMPLIFY_TOLERANCE_DEGREES):
    """Douglas-Peucker simplification preserving the true first and last coordinate."""
    if len(points) <= 2:
        return [[round(value, 6) for value in point[:2]] for point in points]

    keep = [False] * len(points)
    keep[0] = True
    keep[-1] = True
    stack = [(0, len(points) - 1)]
    tolerance_sq = tolerance * tolerance

    while stack:
        start_idx, end_idx = stack.pop()
        max_distance_sq = -1.0
        split_idx = None
        for idx in range(start_idx + 1, end_idx):
            distance_sq = _distance_sq_to_segment(
                points[idx], points[start_idx], points[end_idx]
            )
            if distance_sq > max_distance_sq:
                max_distance_sq = distance_sq
                split_idx = idx

        if split_idx is not None and max_distance_sq > tolerance_sq:
            keep[split_idx] = True
            stack.append((start_idx, split_idx))
            stack.append((split_idx, end_idx))

    return [
        [round(value, 6) for value in point[:2]]
        for idx, point in enumerate(points)
        if keep[idx]
    ]


def simplify_geometry(geometry):
    if not geometry:
        return geometry
    geom_type = geometry.get("type")
    coordinates = geometry.get("coordinates") or []
    if geom_type == "LineString":
        simplified = simplify_line(coordinates)
    elif geom_type == "MultiLineString":
        simplified = [simplify_line(line) for line in coordinates]
    else:
        simplified = coordinates
    return {"type": geom_type, "coordinates": simplified}


def browser_feature(feature):
    """Create the lightweight, normalized feature apps should render directly."""
    source_props = feature.get("properties") or {}
    trail_cn = source_props.get("trail_cn")
    trail_no = source_props.get("trail_no")
    objectid = source_props.get("objectid")
    canonical = trail_cn or trail_no or objectid

    props = {key: source_props.get(key) for key in MAP_PROPERTY_FIELDS}
    props.update(
        {
            "trail_id": f"usfs:{canonical}" if canonical is not None else None,
            "segment_id": f"usfs-objectid:{objectid}" if objectid is not None else None,
            "trail_cn": trail_cn,
            "source_objectid": objectid,
            "bike_status": bike_status(source_props),
            "bike_season": source_props.get("bicycle_managed")
            or source_props.get("bicycle_accpt"),
            "bike_restricted_season": source_props.get("bicycle_restricted"),
            "source": "USFS EDW TrailNFS",
        }
    )
    return {
        "type": "Feature",
        "properties": props,
        "geometry": simplify_geometry(feature.get("geometry")),
    }


def save(path, features):
    with open(path, "w") as handle:
        json.dump({"type": "FeatureCollection", "features": features}, handle)


def save_browser_layer(path, features, region):
    payload = {
        "type": "FeatureCollection",
        "metadata": {
            "source": "USFS EDW TrailNFS",
            "region": region,
            "simplification_tolerance_degrees": MAP_SIMPLIFY_TOLERANCE_DEGREES,
            "access_note": (
                "bike_status=unknown means USFS bicycle fields are blank; it does not mean bicycles are prohibited"
            ),
        },
        "features": [browser_feature(feature) for feature in features],
    }
    with open(path, "w") as handle:
        json.dump(payload, handle, separators=(",", ":"))


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, bbox in REGIONS.items():
        feats = fetch_region(bbox)
        save(os.path.join(OUT_DIR, f"usfs_trails_{name}.geojson"), feats)
        bike = [feature for feature in feats if is_bike(feature["properties"])]
        save(os.path.join(OUT_DIR, f"usfs_bike_trails_{name}.geojson"), bike)

        browser_path = os.path.join(OUT_DIR, f"usfs_trails_{name}_map.geojson")
        save_browser_layer(browser_path, feats, name)

        miles = sum(feature["properties"].get("gis_miles") or 0 for feature in feats)
        browser_mb = os.path.getsize(browser_path) / 1_000_000
        print(
            f"{name}: {len(feats)} segments ({miles:,.0f} mi), "
            f"{len(bike)} bike-confirmed segments, browser layer {browser_mb:.1f} MB"
        )
