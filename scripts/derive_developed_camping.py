"""Build the lightweight developed-camping delivery layer from USFS site data."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACCESS_DIR = ROOT / "data" / "access"
SOURCE_PATH = ACCESS_DIR / "usfs_recreation_sites_rich_idaho.geojson"
OUTPUT_PATH = ACCESS_DIR / "usfs_developed_campgrounds_idaho.geojson"
DEVELOPED_CAMP_TYPES = {"CAMPGROUND", "GROUP CAMPGROUND", "HORSE CAMP"}
SOURCE_NAME = "USFS EDW Recreation Infrastructure Sites"
NOTE = (
    "Developed USFS camping facilities only: CAMPGROUND, GROUP CAMPGROUND, "
    "and HORSE CAMP. Broad CAMPING AREA and individual CAMP UNIT records are "
    "excluded to avoid ambiguous sites and duplicate map markers. Operational "
    "status is source-published context, not a live guarantee."
)


def clean_value(value):
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned or cleaned.lower() in {"no data", "feet"}:
            return None
        return cleaned
    return value


def yes_no(value):
    cleaned = clean_value(value)
    if cleaned == "Y":
        return "Yes"
    if cleaned == "N":
        return "No"
    return cleaned


def source_date(value):
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date().isoformat()


def developed_camping_points(features: list[dict]) -> list[dict]:
    """Create one stable, map-facing record per developed camping facility."""
    camp_type_labels = {
        "CAMPGROUND": "Developed campground",
        "GROUP CAMPGROUND": "Group campground",
        "HORSE CAMP": "Horse camp",
    }
    camping = []
    for feature in features:
        source_properties = feature.get("properties") or {}
        site_type = str(source_properties.get("site_type") or "").upper()
        if site_type not in DEVELOPED_CAMP_TYPES:
            continue

        site_cn = str(source_properties.get("site_cn") or "").strip()
        name = (
            source_properties.get("public_site_name")
            or source_properties.get("recarea_name")
            or source_properties.get("site_name")
            or "USFS camping site"
        )
        properties = {
            "id": f"usfs-camp:{site_cn}" if site_cn else None,
            "name": clean_value(name),
            "camp_type": camp_type_labels[site_type],
            "site_type": site_type,
            "agency": "USDA Forest Service",
            "managing_org_code": clean_value(source_properties.get("managing_org")),
            "operated_by": clean_value(source_properties.get("operated_by")),
            "status": clean_value(source_properties.get("seasonal_operational_status")),
            "status_reason": clean_value(source_properties.get("op_status_reason")),
            "description": clean_value(source_properties.get("recarea_description")),
            "capacity": clean_value(source_properties.get("total_capacity")),
            "max_people": clean_value(source_properties.get("max_nbr_people")),
            "fee_charged": yes_no(source_properties.get("fee_charged")),
            "fee_type": clean_value(source_properties.get("fee_type")),
            "fee_description": clean_value(source_properties.get("fee_description")),
            "open_season": clean_value(source_properties.get("open_season")),
            "season_description": clean_value(source_properties.get("season_description")),
            "operational_hours": clean_value(source_properties.get("operational_hours")),
            "usage_level": clean_value(source_properties.get("usage_level")),
            "water": clean_value(source_properties.get("water_availability")),
            "restrooms": clean_value(source_properties.get("restroom_availability")),
            "pack_in_out": yes_no(source_properties.get("pack_in_out")),
            "permits": clean_value(source_properties.get("permit_information")),
            "passes": clean_value(
                source_properties.get("passes_accepted") or source_properties.get("passes")
            ),
            "restrictions": clean_value(source_properties.get("restrictions")),
            "important_info": clean_value(source_properties.get("important_info")),
            "closest_towns": clean_value(source_properties.get("closest_towns")),
            "directions": clean_value(source_properties.get("directions")),
            "recreation_gov_url": clean_value(source_properties.get("rec1stop_url")),
            "usfs_url": clean_value(source_properties.get("usda_portal_url")),
            "minimum_elevation": clean_value(source_properties.get("minimum_elevation")),
            "maximum_elevation": clean_value(source_properties.get("maximum_elevation")),
            "source_updated": source_date(source_properties.get("infra_last_update")),
        }
        camping.append(
            {
                "type": "Feature",
                "geometry": feature["geometry"],
                "properties": properties,
            }
        )
    return camping


def main() -> None:
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    features = developed_camping_points(source["features"])
    document = {
        "type": "FeatureCollection",
        "metadata": {
            "layer": "developed-camping",
            "scope": "Idaho",
            "feature_count": len(features),
            "source": SOURCE_NAME,
            "note": NOTE,
        },
        "features": features,
    }
    OUTPUT_PATH.write_text(
        json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"saved {OUTPUT_PATH.relative_to(ROOT)}: {len(features)} features")


if __name__ == "__main__":
    main()
