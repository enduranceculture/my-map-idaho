"""Run Base v1 completion while safely ignoring non-spatial ArcGIS records.

PAD-US and other ArcGIS services can return valid attribute records whose GeoJSON
geometry is null. Those records cannot contribute to a map layer, so this runner
counts and removes them before the base clipping functions run. All spatial records
continue through the normal topology-repair and exact Idaho clipping path.
"""

import pull_idaho_base_v1_completion as pipeline


_base_clip_polygons = pipeline.clip_polygons
_base_clip_points = pipeline.clip_points


def spatial_only(features: list[dict], label: str) -> list[dict]:
    spatial = [feature for feature in features if feature.get("geometry")]
    skipped = len(features) - len(spatial)
    if skipped:
        print(f"{label}: skipped {skipped} non-spatial record(s) with null geometry")
    return spatial


def clip_polygons(features: list[dict], boundary) -> list[dict]:
    return _base_clip_polygons(spatial_only(features, "polygon source"), boundary)


def clip_points(features: list[dict], boundary) -> list[dict]:
    return _base_clip_points(spatial_only(features, "point source"), boundary)


if __name__ == "__main__":
    pipeline.clip_polygons = clip_polygons
    pipeline.clip_points = clip_points
    pipeline.main()
