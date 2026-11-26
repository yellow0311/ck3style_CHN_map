"""Extract UK roads, rail corridors and stations from Geofabrik OSM snapshots."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

import osmium
from shapely import line_merge, make_valid, prepare, simplify, union_all
from shapely.geometry import MultiLineString, Point, shape
from shapely.ops import transform
from shapely.strtree import STRtree

from uk_geometry import project


def svg_lines(lines):
    return "".join("M" + " ".join(f"{x:.3f},{y:.3f}" for x, y in line.coords) for line in lines)


def path_parts(points, tolerance, minimum):
    merged = simplify(line_merge(MultiLineString(points)), tolerance, preserve_topology=False)
    parts = [merged] if merged.geom_type == "LineString" else merged.geoms
    return [line for line in parts if line.length >= minimum]


class Transport:
    def __init__(self, boundary):
        self.boundary = transform(project, boundary).buffer(.28)
        prepare(self.boundary)
        self.road_lines = defaultdict(list)
        self.road_names = defaultdict(Counter)
        self.rail_lines = defaultdict(list)
        self.rail_ids = {}
        self.stations = {}

    def read(self, source):
        keywords = osmium.filter.TagFilter(
            ("highway", "motorway"), ("highway", "trunk"), ("highway", "primary"),
            ("railway", "rail"), ("railway", "station"), ("railway", "halt"),
        )
        stream = osmium.FileProcessor(str(source), osmium.osm.NODE | osmium.osm.WAY)
        for item in stream.with_locations("flex_mem").with_filter(keywords):
            tags = item.tags
            rail = tags.get("railway")
            if item.is_node():
                if rail in {"station", "halt"} and item.location.valid():
                    self.station(item, project(item.lon, item.lat))
                continue
            if rail == "rail" and (tags.get("service") or tags.get("usage") in {"military", "tourism"}):
                continue
            if tags.get("highway") and not tags.get("ref"):
                continue
            points = []
            for node in item.nodes:
                if node.location.valid():
                    point = project(node.lon, node.lat)
                    if not points or points[-1] != point:
                        points.append(point)
            if not points or not self.boundary.covers(Point(points[len(points)//2])):
                continue
            if rail in {"station", "halt"}:
                xs,ys = zip(*points)
                self.station(item, ((min(xs)+max(xs))/2,(min(ys)+max(ys))/2))
            elif len(points) >= 2 and rail == "rail":
                self.railway(item, points)
            elif len(points) >= 2:
                self.road(item, points)

    def station(self, entity, xy):
        tags = entity.tags
        name = tags.get("name")
        if not name or tags.get("station") in {"subway", "light_rail", "tram", "monorail"}:
            return
        if tags.get("subway") == "yes" or tags.get("light_rail") == "yes":
            return
        if not self.boundary.covers(Point(xy)):
            return
        typ = "node" if entity.is_node() else "way"
        key = (name, round(xy[0]), round(xy[1]))
        if key not in self.stations or typ == "node":
            self.stations[key] = {
                "id": f"{typ}:{entity.id}", "osmId": entity.id, "osmType": typ, "n": name,
                "x": round(xy[0], 3), "y": round(xy[1], 3),
                "passenger": tags.get("passenger") != "no", "hub": tags.get("public_transport") == "station",
            }

    def road(self, entity, points):
        name = entity.tags.get("name")
        for token in re.split(r"[;/]", entity.tags.get("ref", "")):
            ref = re.sub(r"\s+", "", token).upper()
            if not re.fullmatch(r"(?:M\d{1,3}|A\d{1,4}(?:\(M\))?)", ref):
                continue
            kind = "expressway" if ref.startswith("M") or ref.endswith("(M)") else "national"
            key = (ref, kind)
            self.road_lines[key].append(points)
            if name:
                self.road_names[key][name] += len(points)

    def railway(self, entity, points):
        tags = entity.tags
        name = tags.get("name:en") or tags.get("name")
        high_speed = tags.get("highspeed") == "yes" or bool(name and re.search(r"High Speed 1|Channel Tunnel Rail Link", name, re.I))
        freight = tags.get("usage") in {"industrial","freight"} or tags.get("passenger") == "no"
        kind = "passenger" if high_speed else "freight" if freight else "mixed"
        key = (name or {"mixed":"Unnamed passenger and freight railway","freight":"Unnamed freight branch","passenger":"Unnamed high-speed railway"}[kind],kind)
        self.rail_lines[key].append(points)
        self.rail_ids.setdefault(key,entity.id)

    def roads(self):
        for key in sorted(self.road_lines, key=lambda item: (item[1] != "national", item[0])):
            ref, kind = key
            parts = path_parts(self.road_lines[key], .08, .22)
            if sum(p.length for p in parts) < (1.0 if kind == "expressway" else 2.7):
                continue
            name = self.road_names[key].most_common(1)
            yield [ref, name[0][0] if kind == "expressway" and name else ref, kind,
                   [round(v,3) for v in MultiLineString(parts).bounds], svg_lines(parts)]

    def railways(self):
        lines, segments, owners, stations = [], [], [], []
        for key in sorted(self.rail_lines):
            name,kind = key
            parts = path_parts(self.rail_lines[key], .053, .18)
            if sum(p.length for p in parts) < (1.5 if kind != "freight" else .7):
                continue
            segments.extend(parts)
            owners.extend([len(lines)] * len(parts))
            lines.append({"id":self.rail_ids[key],"osmType":"way","n":name,"kind":kind,
                          "b":list(MultiLineString(parts).bounds),"d":svg_lines(parts),"stops":[]})
        index = STRtree(segments)
        for station in self.stations.values():
            xy = Point(station["x"],station["y"])
            hit = index.query(xy,predicate="dwithin",distance=.57)
            track = {owners[i] for i in hit}
            if track:
                stations.append(station)
                for i in track:
                    lines[i]["stops"].append(station["id"])
        return {"lines":lines, "stations":stations}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--date", required=True)
    parser.add_argument("--output", type=Path, default=Path("dist/data/uk"))
    args = parser.parse_args()
    boundary = json.loads((args.cache / "lad.geojson").read_text(encoding="utf-8"))["features"]
    land = union_all([make_valid(shape(feature["geometry"])) for feature in boundary])
    network = Transport(land)
    for region in ("great-britain", "ireland-and-northern-ireland"):
        network.read(args.cache / f"{region}.osm.pbf")
        print(f"Processed {region}",flush=True)
    args.output.mkdir(parents=True,exist_ok=True)
    roads = list(network.roads())
    railways = network.railways()
    print(Counter(row[2] for row in roads),"roads",len(railways["lines"]),"rail routes",len(railways["stations"]),"stations")
    for filename,data in {"roads":{"date":args.date,"roads":roads},"railways":railways}.items():
        (args.output / f"{filename}.json").write_text(json.dumps(data, separators=(",",":"),ensure_ascii=False),encoding="utf-8")


if __name__ == "__main__":
    main()
