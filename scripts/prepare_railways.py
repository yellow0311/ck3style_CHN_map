"""Import selected mainline tracks and station nodes from OpenStreetMap relations."""

import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge

from prepare_boundaries import OUTPUT, xy


CONFIG = Path(__file__).with_name("railway_routes.json")
API = "https://api.openstreetmap.org/api/0.6/relation/{}/full.json"
SIDINGS = {"yard", "siding", "spur", "crossover"}


def fetch(relation, cache):
    target = cache / f"rel-{relation}.json"
    if not target.exists():
        request = Request(API.format(relation), headers={"User-Agent": "ShanheAtlas/1.0"})
        for attempt in range(3):
            try:
                with urlopen(request, timeout=35) as response:
                    payload = response.read()
                json.loads(payload)
                target.write_bytes(payload)
                break
            except (URLError, TimeoutError):
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
    return json.loads(target.read_bytes())["elements"]


def extract(relation, cache, visited):
    if relation in visited:
        return {}, []
    visited.add(relation)
    elements = fetch(relation, cache)
    root = next(item for item in elements if item["type"] == "relation" and item["id"] == relation)
    nodes = {item["id"]: item for item in elements if item["type"] == "node"}
    ways = {item["id"]: item for item in elements if item["type"] == "way"}
    tracks = {}
    station_nodes = []
    for member in root["members"]:
        ref = member["ref"]
        if member["type"] == "relation":
            child = next((item for item in elements if item["type"] == "relation" and item["id"] == ref), None)
            if child and child.get("tags", {}).get("route") in {"railway", "tracks"}:
                child_tracks, child_stations = extract(ref, cache, visited)
                tracks.update(child_tracks)
                station_nodes.extend(child_stations)
        if member["type"] == "node" and ref in nodes:
            station_nodes.append(nodes[ref])
        if member["type"] != "way" or ref not in ways:
            continue
        way = ways[ref]
        tags = way.get("tags", {})
        if tags.get("railway") != "rail" or tags.get("service") in SIDINGS:
            continue
        points = [xy((nodes[ident]["lon"], nodes[ident]["lat"])) for ident in way["nodes"]]
        if len(points) >= 2:
            tracks[ref] = points
        station_nodes.extend(nodes[ident] for ident in way["nodes"] if nodes[ident].get("tags"))
    return tracks, station_nodes


def path_data(tracks):
    paths = linemerge(MultiLineString(tracks))
    if isinstance(paths, LineString):
        paths = [paths]
    else:
        paths = paths.geoms
    tracks = [path.simplify(.004, preserve_topology=False) for path in paths if path.length >= .004]
    coords = [list(path.coords) for path in tracks]
    points = [point for track in coords for point in track]
    x, y = zip(*points)

    def xy_text(point):
        return ",".join(f"{value:.3f}".rstrip("0").rstrip(".") for value in point)

    return (
        [round(min(x), 3), round(min(y), 3), round(max(x), 3), round(max(y), 3)],
        "".join("M" + " ".join(map(xy_text, track)) for track in coords),
    )


def select_stops(nodes, kind, hubs, include_stop_positions):
    results = {}
    named_stations = set()
    for node in nodes:
        tags = node.get("tags", {})
        railway = tags.get("railway")
        stop_position = include_stop_positions and railway == "stop"
        if (railway not in {"station", "halt"} and not stop_position) or tags.get("disused") == "yes":
            continue
        name = tags.get("name:zh-Hans") or tags.get("name:zh") or tags.get("name", "")
        name = name.removesuffix("站")
        if not name or not re.search(r"[\u3400-\u9fff]", name):
            continue
        category = tags.get("railway:station_category", "").removeprefix("CN:")
        known_passenger = tags.get("train") == "yes" or tags.get("public_transport") == "station"
        passenger = kind != "freight" and tags.get("train") != "no" and tags.get("public_transport") != "no"
        major = name in hubs or category in {"0", "1"}
        passenger_stop = passenger and (kind == "passenger" or (known_passenger and category == "2"))
        if not major and not passenger_stop:
            continue
        if include_stop_positions:
            if name in named_stations:
                continue
            named_stations.add(name)
        label = name if name.endswith(("场", "港")) else name + "站"
        x, y = xy((node["lon"], node["lat"]))
        ident = node["id"]
        results[ident] = {
            "id": ident, "osmType": "node", "n": label, "x": round(x, 3), "y": round(y, 3),
            "hub": major, "passenger": passenger,
        }
    return list(results.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path, help="directory for cached OSM relation downloads")
    parser.add_argument("--output", type=Path, default=OUTPUT / "railways.json")
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    hubs = set(config["hubs"].split())
    lines = []
    stations = {}
    for name, kind, *relations in config["lines"]:
        tracks = {}
        candidates = []
        seen = set()
        for relation in relations:
            parts, nodes = extract(relation, args.cache, seen)
            tracks.update(parts)
            candidates.extend(nodes)
        if not tracks:
            raise ValueError(f"{name}: no operating tracks in OSM relations {relations}")
        bounds, svg = path_data(list(tracks.values()))
        include_stop_positions = relations[0] in config.get("stopPositionRoutes", [])
        if include_stop_positions:
            candidates.sort(key=lambda node: node.get("tags", {}).get("railway") == "stop")
        stops = select_stops(candidates, kind, hubs, include_stop_positions)
        for stop in stops:
            old = stations.get(stop["id"])
            if old:
                old["hub"] |= stop["hub"]
                old["passenger"] |= stop["passenger"]
            else:
                stations[stop["id"]] = stop
        lines.append({"id": relations[0], "relations": relations, "n": name, "kind": kind,
                      "b": bounds, "d": svg, "stops": [s["id"] for s in stops]})
        print(f"{name} {len(tracks)} ways, {len(stops)} mapped stops", flush=True)
    ordered_stations = sorted(stations.values(), key=lambda row: not row["hub"])
    args.output.write_text(json.dumps({"lines": lines, "stations": ordered_stations},
                                      ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(dict(Counter(line["kind"] for line in lines)), len(stations), "stations", flush=True)


if __name__ == "__main__":
    main()
