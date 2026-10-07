"""Pull Oakridge / Westfir USFS recreation access points."""
import json, os, time, urllib.parse, urllib.request
BASE="https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_RecInfraRecreationSites_02/MapServer/0/query"
BBOX="-122.75,43.35,-121.65,44.25"
OUT_DIR=os.path.join(os.path.dirname(__file__),"..","data","access")
FIELDS=("objectid,site_cn,managing_org,site_id,site_name,site_type,activity_type_list,"
"service_type_list,seasonal_operational_status,op_status_reason,development_status,"
"fee_charged,fee_type,recarea_name,public_site_name,alternative_name,rec1stop_url,"
"usda_portal_url,important_info,permit_information,restrictions,closest_towns,"
"water_availability,restroom_availability,operated_by,season_description,directions,"
"maximum_elevation,minimum_elevation,site_season_start_date,site_season_end_date,"
"latitude,longitude,infra_last_update,edw_last_modify,globalid")
CAMP_TYPES={"CAMPGROUND","GROUP CAMPGROUND","HORSE CAMP"}

def req(params):
    url=BASE+"?"+urllib.parse.urlencode(params)
    last=None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url,timeout=120) as response:
                payload=json.loads(response.read().decode("utf-8"))
            if not payload.get("error"): return payload
            last=payload["error"]
        except Exception as exc: last=exc
        time.sleep(2**attempt)
    raise RuntimeError(f"USFS recreation request failed: {last}")

def fetch_all():
    ids=req({"where":"1=1","geometry":BBOX,"geometryType":"esriGeometryEnvelope","inSR":"4326","spatialRel":"esriSpatialRelIntersects","returnIdsOnly":"true","f":"json"}).get("objectIds") or []
    ids=sorted({int(x) for x in ids}); out=[]
    for start in range(0,len(ids),500):
        payload=req({"objectIds":",".join(str(x) for x in ids[start:start+500]),"outFields":FIELDS,"returnGeometry":"true","outSR":"4326","geometryPrecision":"6","f":"geojson"})
        out.extend(payload.get("features") or []); time.sleep(.5)
    return out

def write(name,features,note):
    os.makedirs(OUT_DIR,exist_ok=True)
    payload={"type":"FeatureCollection","metadata":{"source":"USFS EDW Recreation Infrastructure Sites","region":"oakridge_oregon","bbox":[-122.75,43.35,-121.65,44.25],"note":note},"features":[f for f in features if f.get("geometry")]}
    with open(os.path.join(OUT_DIR,name),"w") as handle: json.dump(payload,handle,separators=(",",":"))
    print(f"{name}: {len(payload['features'])} features")

if __name__=="__main__":
    source=fetch_all()
    trailheads=[f for f in source if "TRAILHEAD" in str((f.get("properties") or {}).get("site_type") or "").upper()]
    campgrounds=[f for f in source if str((f.get("properties") or {}).get("site_type") or "").upper() in CAMP_TYPES]
    write("usfs_trailheads_oakridge_oregon.geojson",trailheads,"Official USFS trailhead infrastructure in the Oakridge / Westfir field area.")
    write("usfs_developed_campgrounds_oakridge_oregon.geojson",campgrounds,"Official developed USFS campgrounds in the Oakridge / Westfir field area.")
