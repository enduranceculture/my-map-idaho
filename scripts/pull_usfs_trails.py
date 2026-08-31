"""Pull USFS National Forest System trail data and save as GeoJSON layers.

Source: USFS Enterprise Data Warehouse (public domain), updated daily by USFS.
https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0

Add more regions to REGIONS to expand coverage. Run from repo root:
    python scripts/pull_usfs_trails.py
"""
import urllib.request, urllib.parse, json, time, os

BASE = 'https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0/query'

# region_name -> bbox as 'min_lon,min_lat,max_lon,max_lat' (WGS84)
REGIONS = {
    'woodriver_sawtooth': '-115.2,43.3,-114.0,44.3',
}

FIELDS = ('trail_name,trail_no,trail_type,trail_class,gis_miles,trail_surface,'
          'typical_trail_grade,typical_tread_width,national_trail_designation,'
          'terra_motorized,allowed_terra_use,bicycle_managed,bicycle_accpt,'
          'bicycle_disc,bicycle_restricted,e_bike_class1_managed,'
          'motorcycle_managed,admin_org,managing_org')

OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'trails')


def fetch_region(bbox):
    features, offset = [], 0
    while True:
        params = {'geometry': bbox, 'geometryType': 'esriGeometryEnvelope',
                  'inSR': '4326', 'spatialRel': 'esriSpatialRelIntersects',
                  'where': '1=1', 'outFields': FIELDS, 'returnGeometry': 'true',
                  'outSR': '4326', 'resultOffset': str(offset),
                  'resultRecordCount': '500', 'f': 'geojson'}
        r = urllib.request.urlopen(BASE + '?' + urllib.parse.urlencode(params), timeout=120)
        feats = json.loads(r.read().decode()).get('features', [])
        features.extend(feats)
        if len(feats) < 500:
            return features
        offset += 500
        time.sleep(1)


def is_bike(props):
    return bool(props.get('bicycle_managed') or props.get('bicycle_accpt'))


def save(path, features):
    with open(path, 'w') as f:
        json.dump({'type': 'FeatureCollection', 'features': features}, f)


if __name__ == '__main__':
    for name, bbox in REGIONS.items():
        feats = fetch_region(bbox)
        save(os.path.join(OUT_DIR, f'usfs_trails_{name}.geojson'), feats)
        bike = [f for f in feats if is_bike(f['properties'])]
        save(os.path.join(OUT_DIR, f'usfs_bike_trails_{name}.geojson'), bike)
        miles = sum(f['properties'].get('gis_miles') or 0 for f in feats)
        print(f'{name}: {len(feats)} segments ({miles:,.0f} mi), {len(bike)} bike-legal segments')
