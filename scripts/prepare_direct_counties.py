"""Prepare supplemental provincial-direct county data from the Xinjiang OSM extract."""

import argparse
import json
from pathlib import Path

import osmium
from shapely import to_geojson

from prepare_boundaries import OUTPUT, convert, xy
from prepare_townships import read_areas


XINJIANG = "650000"
BOUNDARIES = {
    "659011": ("新星市", 12279740),
    "659012": ("白杨市", 15340171),
}
# The available Caohu city boundary covers only part of the new city.
# Mark the government seat in Caohu Town until the full boundary is available.
CAOHU_SEAT = 11058064108


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extract", type=Path, help="Geofabrik Xinjiang .osm.pbf")
    parser.add_argument("--output", type=Path, default=OUTPUT / "direct-counties.json")
    args = parser.parse_args()
    areas = read_areas(args.extract, {name for name, _ in BOUNDARIES.values()})
    records = []
    for code, (name, relation) in BOUNDARIES.items():
        matches = [shape for ref, level, shape in areas[name] if ref == relation and level == "6"]
        if len(matches) != 1:
            raise ValueError(f"{name}: expected one boundary for OSM relation {relation}")
        shape = matches[0]
        center = shape.representative_point()
        record = convert({
            "properties": {
                "name": name, "adcode": code, "parent": {"adcode": XINJIANG},
                "center": [center.x, center.y],
            },
            "geometry": json.loads(to_geojson(shape)),
        })
        records.append({**record, "osmRelation": relation})

    nodes = osmium.FileProcessor(args.extract, osmium.osm.NODE)
    for seat in nodes.with_filter(osmium.filter.IdFilter([CAOHU_SEAT])):
        if seat.tags.get("name:zh") == "草湖镇":
            x, y = xy([seat.lon, seat.lat])
            break
    else:
        raise ValueError(f"草湖镇: expected location from OSM node {CAOHU_SEAT}")
    records.append({
        "id": "659013", "n": "草湖市", "p": XINJIANG,
        "x": round(x, 2), "y": round(y, 2), "osmNode": CAOHU_SEAT,
        "source": "https://www.xinjiang.gov.cn/xinjiang/tzgg/202604/3691350b13064945947d8f78933ccb3e.shtml",
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
