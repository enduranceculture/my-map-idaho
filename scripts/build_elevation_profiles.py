#!/usr/bin/env python3
"""Build source-backed, shared trail elevation profiles from MYDAHO's canonical GeoJSON.

No user GPS is used. Elevation tiles are the same public Mapzen/AWS Terrarium
dataset MYDAHO uses for its Relief terrain. Calculations are DEM estimates,
not measured trail grades or guaranteed ride direction.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import io
import json
import math
from pathlib import Path
import statistics
import struct
import time
import urllib.error
import urllib.request

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LAYERS = {
    "trails-oakridge-oregon": "data/trails/usfs_trails_oakridge_oregon_map.geojson",
    "trails-woodriver-sawtooth": "data/trails/usfs_trails_woodriver_sawtooth_map.geojson",
    "trails-warm-springs-bonneville": "data/trails/usfs_trails_warm_springs_bonneville_map.geojson",
}
TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
METERS_PER_MILE = 1609.344
EARTH_RADIUS_M = 6371008.8
JOIN_TOLERANCE_M = 12.0


def normalize(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def normalized_field(props: dict, *names: str) -> str:
    fields = {k.replace("_", "").replace("-", "").replace(" ", "").lower(): v
              for k, v in props.items()}
    for name in names:
        value = fields.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def trail_identity(layer: str, props: dict) -> tuple[str, str]:
    name = normalized_field(props, "trailname", "trailnm", "name", "routename", "trail")
    number = normalized_field(props, "trailno", "trailnumber")
    if not name and number:
        name = f"Trail {number}"
    if not name:
        return "", ""
    seed = f"{layer}|{normalize(name)}|{normalize(number)}"
    # Match src/lib/personal-places.ts hashString, including JS UTF-16 code units.
    encoded = seed.encode("utf-16-le")
    h = 2166136261
    for (code_unit,) in struct.iter_unpack("<H", encoded):
        h ^= code_unit
        h = (h * 16777619) & 0xFFFFFFFF
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    base36 = ""
    while h:
        base36 = chars[h % 36] + base36
        h //= 36
    return f"{layer}:trail:{base36 or '0'}", name


def distance_m(a: list[float], b: list[float]) -> float:
    lat1, lat2 = math.radians(a[1]), math.radians(b[1])
    dy = lat2 - lat1
    dx = math.radians(b[0] - a[0])
    h = math.sin(dy / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dx / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1, math.sqrt(h)))


def line_distance(line: list) -> float:
    return sum(distance_m(a, b) for a, b in zip(line, line[1:]))


def lines_from_geometry(geom: dict) -> list[list[list[float]]]:
    if geom.get("type") == "LineString":
        raw = [geom.get("coordinates", [])]
    elif geom.get("type") == "MultiLineString":
        raw = geom.get("coordinates", [])
    else:
        return []
    result = []
    for part in raw:
        points = [[float(p[0]), float(p[1])] for p in part
                  if isinstance(p, list) and len(p) >= 2 and
                  all(isinstance(v, (int, float)) and math.isfinite(v) for v in p[:2])]
        if len(points) >= 2:
            result.append(points)
    return result


def stitch_components(lines: list[list]) -> list[list]:
    """Join only source-line endpoints within 12 m; NEVER bridge a disconnected gap."""
    remaining = [list(line) for line in lines if len(line) >= 2]
    components = []
    while remaining:
        chain = remaining.pop(0)
        while True:
            matched = None
            for i, line in enumerate(remaining):
                options = [
                    (distance_m(chain[-1], line[0]), "tail", False),
                    (distance_m(chain[-1], line[-1]), "tail", True),
                    (distance_m(chain[0], line[-1]), "head", False),
                    (distance_m(chain[0], line[0]), "head", True),
                ]
                d, side, reverse = min(options, key=lambda item: item[0])
                if d <= JOIN_TOLERANCE_M:
                    matched = (i, side, reverse)
                    break
            if matched is None:
                break
            i, side, reverse = matched
            line = remaining.pop(i)
            line = list(reversed(line)) if reverse else line
            if side == "tail":
                chain.extend(line[1:])
            else:
                chain = line[:-1] + chain
        components.append(chain)
    return sorted(components, key=line_distance, reverse=True)


def sample_line(line: list, step_m: float) -> list[tuple[float, float, float]]:
    """Distance-interpolate; preserve endpoints and never connect separate components."""
    lengths = [distance_m(a, b) for a, b in zip(line, line[1:])]
    total = sum(lengths)
    if total < 20:
        return []
    targets = [min(total, i * step_m) for i in range(math.ceil(total / step_m) + 1)]
    if targets[-1] < total:
        targets.append(total)
    samples = []
    segment = 0
    offset = 0.0
    for target in targets:
        while segment < len(lengths) - 1 and target > offset + lengths[segment]:
            offset += lengths[segment]
            segment += 1
        length = lengths[segment]
        ratio = max(0.0, min(1.0, (target - offset) / length)) if length else 0.0
        a, b = line[segment], line[segment + 1]
        lng = a[0] + (b[0] - a[0]) * ratio
        lat = a[1] + (b[1] - a[1]) * ratio
        samples.append((target, lng, lat))
    return samples


def tile_position(lng: float, lat: float, zoom: int) -> tuple[int, int, float, float]:
    n = 2 ** zoom
    lat = max(-85.051, min(85.051, lat))
    fx = (lng + 180) / 360 * n
    fy = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    x, y = int(math.floor(fx)), int(math.floor(fy))
    return x, y, (fx - x) * 256, (fy - y) * 256


def decode_terrarium(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb[:3]
    return r * 256 + g + b / 256 - 32768


def fetch_tile(tile: tuple[int, int, int]) -> tuple[tuple[int, int, int], Image.Image | None]:
    zoom, x, y = tile
    url = TILE_URL.format(z=zoom, x=x, y=y)
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "MYDAHO-Trail-Elevation/1.0"})
            with urllib.request.urlopen(request, timeout=20) as response:
                content = response.read()
            im = Image.open(io.BytesIO(content)).convert("RGB")
            if im.size != (256, 256):
                raise ValueError("unexpected terrain tile dimensions")
            return tile, im
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as error:
            if attempt == 2:
                print(f"Tile {tile} unavailable: {error}", flush=True)
                return tile, None
            time.sleep(0.3 * (attempt + 1))
    return tile, None


def elevation_from_tile(tile: Image.Image, px: float, py: float) -> float:
    x, y = min(254, int(px)), min(254, int(py))
    fx, fy = px - int(px), py - int(py)
    if px >= 255:
        x, fx = 254, 1
    if py >= 255:
        y, fy = 254, 1
    a = decode_terrarium(tile.getpixel((x, y)))
    b = decode_terrarium(tile.getpixel((x + 1, y)))
    c = decode_terrarium(tile.getpixel((x, y + 1)))
    d = decode_terrarium(tile.getpixel((x + 1, y + 1)))
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def filtered_elevation(elevations: list[float]) -> list[float]:
    # Median window suppresses single-pixel DEM artifacts without moving trail coordinates.
    return [statistics.median(elevations[max(0, i - 2):min(len(elevations), i + 3)])
            for i in range(len(elevations))]


def climb_descent(values: list[float], threshold_m: float = 3.0) -> tuple[float, float]:
    # A minimum 3 m sustained change prevents micro-jitter from inflating total gain.
    if not values:
        return 0.0, 0.0
    gain, descent = 0.0, 0.0
    anchor = values[0]
    for value in values[1:]:
        delta = value - anchor
        if abs(delta) >= threshold_m:
            if delta > 0:
                gain += delta
            else:
                descent -= delta
            anchor = value
    return gain, descent


def grouped_profiles(layers: dict[str, Path]) -> dict[str, dict]:
    groups: dict[str, dict] = {}
    for layer, source in layers.items():
        features = json.loads(source.read_text(encoding="utf-8"))["features"]
        by_key = {}
        for feature in features:
            key, name = trail_identity(layer, feature.get("properties") or {})
            if not key:
                continue
            parts = lines_from_geometry(feature.get("geometry") or {})
            if not parts:
                continue
            item = by_key.setdefault(key, {"name": name, "parts": []})
            item["parts"].extend(parts)
        groups[layer] = by_key
        print(f"{layer}: {len(features)} source features, {len(by_key)} trail identities", flush=True)
    return groups


def generate(layers: dict[str, Path], zoom: int, step_m: float, max_chart_points: int) -> dict:
    groups = grouped_profiles(layers)
    tracks = {}
    requested_tiles = set()
    for layer, by_key in groups.items():
        for key, entry in by_key.items():
            components = stitch_components(entry["parts"])
            if not components:
                continue
            source_distance = sum(line_distance(line) for line in components)
            chain = components[0]
            chain_distance = line_distance(chain)
            spacing = max(step_m, chain_distance / 800)
            sampled = sample_line(chain, spacing)
            if len(sampled) < 2:
                continue
            tiles = [tile_position(lng, lat, zoom) for _dist, lng, lat in sampled]
            requested_tiles.update((zoom, x, y) for x, y, _, _ in tiles)
            tracks[(layer, key)] = (entry, sampled, tiles, len(components), source_distance)
    print(f"{len(tracks)} trail profiles, {len(requested_tiles)} shared terrain tiles at z{zoom}", flush=True)

    fetched = {}
    with ThreadPoolExecutor(max_workers=14) as pool:
        futures = [pool.submit(fetch_tile, t) for t in sorted(requested_tiles)]
        for i, future in enumerate(as_completed(futures), 1):
            tile_key, tile_data = future.result()
            fetched[tile_key] = tile_data
            if i % 100 == 0:
                print(f"Terrain tiles: {i}/{len(futures)}", flush=True)

    result = {layer: {} for layer in layers}
    skipped = 0
    for (layer, key), (entry, sampled, positions, component_count, source_distance) in tracks.items():
        elevations = []
        for _point, (x, y, px, py) in zip(sampled, positions):
            tile = fetched.get((zoom, x, y))
            if tile is None:
                break
            elevations.append(elevation_from_tile(tile, px, py))
        if len(elevations) != len(sampled) or not all(-500 <= e <= 6000 for e in elevations):
            skipped += 1
            continue
        smooth = filtered_elevation(elevations)
        gain, descent = climb_descent(smooth)
        indices = [round(i * (len(sampled) - 1) / (min(max_chart_points, len(sampled)) - 1))
                   for i in range(min(max_chart_points, len(sampled)))]
        coords = [[round(sampled[i][0]), round(smooth[i], 1),
                   round(sampled[i][1], 6), round(sampled[i][2], 6)] for i in sorted(set(indices))]
        distance = sampled[-1][0]
        result[layer][key] = {
            "name": entry["name"],
            "distanceM": round(distance),
            "gainM": round(gain),
            "descentM": round(descent),
            "minM": round(min(smooth)),
            "maxM": round(max(smooth)),
            "sourceComponents": component_count,
            "sourceCoverage": round(distance / source_distance, 3) if source_distance else 1,
            "samples": coords,
        }
    print(f"Produced {sum(map(len, result.values()))} profiles, skipped {skipped} with missing/invalid DEM", flush=True)
    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "terrainSource": "Mapzen/AWS Terrarium elevation tiles, derived from USGS elevation",
        "tileZoom": zoom,
        "sampleStepM": step_m,
        "verticalUnits": "meters",
        "source": "MYDAHO canonical USFS trail geometry",
        "layers": result,
    }


def smoke_test() -> None:
    a, b, c = [-122.0, 43.0], [-122.0, 43.001], [-121.999, 43.001]
    lines = stitch_components([[b, c], [a, b]])
    assert len(lines) == 1 and len(lines[0]) == 3
    assert len(stitch_components([[a, b], [[-122.1, 43.1], [-122.1, 43.101]]])) == 2
    assert len(sample_line([a, b], 30)) >= 4
    assert decode_terrarium((128, 0, 0)) == 0
    assert climb_descent([100, 101, 102, 120, 116, 102]) == (20, 18)
    assert len(trail_identity("trails-oakridge-oregon", {"trail_name": "Lawler", "trail_no": "347"})[0]) > 15
    print("Elevation preprocessing smoke tests passed", flush=True)


def write_shards(payload: dict, out_dir: Path) -> None:
    """Publish tiny, deterministic cloud files keyed by the final base36 hash digit."""
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    counts = {}
    for layer, profiles in payload["layers"].items():
        counts[layer] = len(profiles)
        folder = out_dir / "shards" / layer
        folder.mkdir(parents=True, exist_ok=True)
        for digit in alphabet:
            shard = {key: profile for key, profile in profiles.items() if key.endswith(digit)}
            data = {
                "schemaVersion": 1,
                "generatedAt": payload["generatedAt"],
                "terrainSource": payload["terrainSource"],
                "verticalUnits": "meters",
                "layerId": layer,
                "profiles": shard,
            }
            (folder / f"{digit}.json").write_text(
                json.dumps(data, separators=(",", ":"), ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
    manifest = {
        "schemaVersion": 1,
        "generatedAt": payload["generatedAt"],
        "terrainSource": payload["terrainSource"],
        "tileZoom": payload["tileZoom"],
        "sampleStepM": payload["sampleStepM"],
        "sharding": "final-personalKey-character",
        "counts": counts,
    }
    (out_dir / "index_v1.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8",
    )
    previous_monolith = out_dir / "trail_profiles_v1.json"
    if previous_monolith.exists():
        previous_monolith.unlink()
    print(f"Cloud sharded profiles: {counts}; 108 files, one tiny request per trail", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/elevation")
    parser.add_argument("--tile-zoom", type=int, default=13)
    parser.add_argument("--step-m", type=float, default=45.0)
    parser.add_argument("--max-chart-points", type=int, default=161)
    parser.add_argument("--smoke-test", action="store_true")
    opts = parser.parse_args()
    smoke_test()
    if opts.smoke_test:
        return
    if not (10 <= opts.tile_zoom <= 14):
        raise ValueError("Terrain zoom must be between 10 and 14")
    if not (20 <= opts.step_m <= 150):
        raise ValueError("Invalid sample interval")
    path = ROOT / opts.out
    path.mkdir(parents=True, exist_ok=True)
    profile = generate({key: ROOT / rel for key, rel in LAYERS.items()},
                       opts.tile_zoom, opts.step_m, opts.max_chart_points)
    write_shards(profile, path)


if __name__ == "__main__":
    main()
