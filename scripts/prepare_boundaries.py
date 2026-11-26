"""Build the site's local boundary asset using only Python 3 and curl."""
import argparse
import json
import subprocess
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from itertools import chain
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "dist" / "data"
BASE = "https://geo.datav.aliyun.com/areas_v3/bound"


def fetch(code):
    target = cache / f"{code}.json"
    if not target.exists():
        subprocess.run(["curl", "-fsSL", "--retry", "3", "--max-time", "40",
                        f"{BASE}/{code}_full.json", "-o", str(target)], check=True)
    return json.loads(target.read_bytes())["features"]


def xy(coord):
    return ((coord[0] - 73) * 14, (54 - coord[1]) * 17)


def num(v):
    return f"{v / 1000:.3f}".rstrip("0").rstrip(".")


def encode_ring(vertices):
    """Encode signed millesimal deltas as 5-bit chunks (encoded polyline format)."""
    previous = (0, 0)
    encoded = []
    for point in vertices:
        for value, origin in zip(point, previous):
            delta = value - origin
            code = delta * 2 if delta >= 0 else -delta * 2 - 1
            while code >= 32:
                encoded.append(chr((code & 31) + 95))
                code >>= 5
            encoded.append(chr(code + 63))
        previous = point
    return "".join(encoded)


def projected_rings(geom):
    polygons = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for polygon in polygons:
        for ring in polygon:
            projected = [tuple(round(value * 1000) for value in xy(coord)) for coord in ring]
            if projected[0] == projected[-1]:
                projected.pop()
            yield projected


def ring_edges(ring):
    return zip(ring, chain(ring[1:], ring[:1]))


def outer_rings(children):
    """Cancel matching internal edges and join the remaining edges into closed rings."""
    edges = Counter(tuple(sorted((a, b))) for child in children
                    for ring in projected_rings(child["geometry"]) for a, b in ring_edges(ring) if a != b)
    if any(count > 2 for count in edges.values()):
        return []
    neighbors = defaultdict(list)
    for (a, b), count in edges.items():
        if count == 1:
            neighbors[a].append(b)
            neighbors[b].append(a)
    if any(len(links) != 2 for links in neighbors.values()):
        return []
    rings = []
    while neighbors:
        start = next(iter(neighbors))
        ring = [start]
        previous, current = start, neighbors.pop(start)[0]
        while current != start:
            ring.append(current)
            a, b = neighbors.pop(current)
            previous, current = current, b if a == previous else a
        rings.append(ring)
    return rings


def convert(f, *, compact=True, children=()):
    props = f["properties"]
    rings = list(projected_rings(f["geometry"]))
    detail = outer_rings(children) if children and len(children) == props.get("childrenNum") else []
    xs, ys = zip(*chain.from_iterable(rings+detail))
    bounds = [value / 1000 for value in (min(xs), min(ys), max(xs), max(ys))]
    x, y = xy(props.get("centroid") or props.get("center") or [105, 15])
    result = dict(n=props["name"], id=str(props["adcode"]), p=str(props.get("parent", {}).get("adcode", 100000)),
                  x=round(x, 2), y=round(y, 2), b=bounds)
    if compact:
        result["g"] = "!".join(map(encode_ring, rings))
    else:
        result["d"] = "".join("M" + " ".join(f"{num(x)},{num(y)}" for x, y in ring) + "Z" for ring in rings)
    if detail:
        result["gDetail"] = "!".join(map(encode_ring, detail))
    return result


def save(filename, data):
    (OUTPUT / filename).write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "ck3-admin-cache")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    cache, OUTPUT = args.cache, args.output
    cache.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    national = fetch("100000")
    provinces = [f for f in national if f["properties"].get("level") == "province"]
    maritime = [convert(f, compact=False) for f in national if f["properties"].get("adchar") == "JD"]
    cities, counties = [], []
    children = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        pids = [f["properties"]["adcode"] for f in provinces if f["properties"]["childrenNum"]]
        for code, regions in zip(pids, pool.map(fetch, pids)):
            children[code] = regions
            for f in regions:
                props = f["properties"]
                # Direct-administered county equivalents retain their province parent.
                if props.get("level") == "district" or int(props["adcode"]) % 100:
                    counties.append(f)
                elif props.get("level") == "city":
                    cities.append(f)
        cids = [f["properties"]["adcode"] for f in cities if f["properties"]["childrenNum"]]
        for code, regions in zip(cids, pool.map(fetch, cids)):
            children[code] = [f for f in regions if f["properties"].get("level") == "district"]
            counties.extend(children[code])
    result = {key: [convert(f, children=children.get(f["properties"]["adcode"])) for f in features] for key, features in
              [("province", provinces), ("city", cities), ("county", counties)]}
    for key, records in result.items():
        assert len({r["id"] for r in records}) == len(records), key
    save("admin-boundaries.json", result)
    save("maritime.json", maritime)
    print({k: len(v) for k, v in result.items()})
