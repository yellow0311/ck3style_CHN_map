"""Extract numbered national roads from a Geofabrik OpenStreetMap PBF."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

import osmium
from shapely import line_merge, simplify
from shapely.geometry import MultiLineString


class NationalRoads(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.lines = defaultdict(list)
        self.names = defaultdict(Counter)

    def way(self, way):
        highway = way.tags.get("highway")
        ref = way.tags.get("ref")
        if not ref or highway not in {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified"}:
            return
        routes = []
        for token in re.split(r"[;,/、；]", ref):
            match = re.fullmatch(r"G\s*(\d{1,4})", token.strip(), re.IGNORECASE)
            if not match:
                continue
            digits = match[1]
            kind = "national" if len(digits) == 3 else "expressway"
            if kind == "expressway" and highway not in {"motorway", "trunk"}:
                continue
            routes.append(("G" + digits, kind))
        if not routes:
            return
        points = []
        for node in way.nodes:
            if not node.location.valid():
                return
            point = ((node.lon - 73) * 14, (54 - node.lat) * 17)
            if not points or points[-1] != point:
                points.append(point)
        if len(points) < 2:
            return
        name = way.tags.get("name:zh-Hans") or way.tags.get("name:zh") or way.tags.get("name")
        for route in set(routes):
            self.lines[route].append(points)
            if name:
                self.names[route][name] += len(points)

    def records(self):
        for key, raw_lines in sorted(self.lines.items(), key=lambda item: (item[0][1] != "national", item[0][0])):
            ref, kind = key
            merged = simplify(line_merge(MultiLineString(raw_lines)), 0.036, preserve_topology=False)
            parts = [merged] if merged.geom_type == "LineString" else merged.geoms
            lines = [line for line in parts if line.length > 0.10]
            if not lines or sum(line.length for line in lines) < 2:
                continue
            lengths = self.names[key].most_common(1)
            name = lengths[0][0] if lengths and kind == "expressway" else ref
            bounds = [round(n, 3) for n in MultiLineString(lines).bounds]
            path = "".join("M" + " ".join(f"{x:.3f},{y:.3f}" for x,y in line.coords) for line in lines)
            yield [ref, name, kind, bounds, path]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pbf", type=Path)
    parser.add_argument("--date", required=True, help="ISO date of the PBF snapshot")
    parser.add_argument("--output", type=Path, default=Path("dist/data/roads.json"))
    args = parser.parse_args()
    roads = NationalRoads()
    roads.apply_file(str(args.pbf), locations=True, idx="flex_mem")
    records = list(roads.records())
    if {row[2] for row in records} != {"expressway", "national"}:
        raise SystemExit("Both expressways and ordinary national roads must be present")
    result = {"date": args.date, "roads": records}
    args.output.write_text(json.dumps(result, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(Counter(row[2] for row in records))


if __name__ == "__main__":
    main()
