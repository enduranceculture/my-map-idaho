"""Run the Idaho access/hydro/names pipeline with bounded parallel ArcGIS fetches.

The base module owns source definitions, clipping, normalization, and outputs.
This runner applies one product-level scope rule — keep USFS roads that the
published Forest Service symbology classifies as passenger-car roads or roads
not maintained for passenger cars — then replaces serial chunk retrieval with
bounded parallel requests.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

import pull_idaho_access_hydro_names as pipeline

MAX_WORKERS = 4

# High-value access intelligence, not every administrative road geometry.
# 517 paved; 518 gravel passenger-car; 515 dirt passenger-car;
# 106 not maintained for passenger cars / typically rougher access.
pipeline.SOURCES["roads"]["where"] = (
    "symbol_code IN ('106','515','517','518')"
)


def parallel_fetch_features_by_ids(config: dict, object_ids: list[int]) -> list[dict]:
    if not object_ids:
        raise RuntimeError(f"{config['name']} returned zero Idaho IDs")

    query_url = config["url"].rstrip("/") + "/query"
    chunk_size = int(config["chunk_size"])
    chunks = [
        object_ids[start : start + chunk_size]
        for start in range(0, len(object_ids), chunk_size)
    ]

    def fetch_chunk(chunk: list[int]) -> list[dict]:
        payload = pipeline.request_json(
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
        return payload.get("features") or []

    pages: list[list[dict] | None] = [None] * len(chunks)
    completed_ids = 0
    workers = min(MAX_WORKERS, len(chunks))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch_chunk, chunk): index for index, chunk in enumerate(chunks)}
        for future in as_completed(futures):
            index = futures[future]
            pages[index] = future.result()
            completed_ids += len(chunks[index])
            print(
                f"{config['name']}: fetched {completed_ids}/{len(object_ids)} IDs "
                f"across {workers} workers"
            )

    features = [feature for page in pages if page for feature in page]
    if not features:
        raise RuntimeError(f"{config['name']} returned zero features for Idaho IDs")

    def oid_sort_key(feature: dict) -> int:
        props = feature.get("properties") or {}
        value = props.get("OBJECTID", props.get("objectid", 0))
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    features.sort(key=oid_sort_key)
    return features


if __name__ == "__main__":
    pipeline.fetch_features_by_ids = parallel_fetch_features_by_ids
    pipeline.main()
