"""Build local elevation grids and water vectors from Mapzen and Natural Earth."""

import argparse
import gzip
import json
import math
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
from zipfile import ZipFile

import numpy as np
import shapefile
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
MAPZEN = "https://s3.amazonaws.com/elevation-tiles-prod/geotiff"
NATURAL_EARTH = "https://naturalearth.s3.amazonaws.com/10m_physical"
WEST, SOUTH, EAST, NORTH = 60, 0, 150, 60


def download(url, cache, name=None):
    target = cache / (name or url.rsplit("/", 1)[-1])
    if not target.exists():
        partial = target.with_suffix(target.suffix + ".part")
        for attempt in range(3):
            try:
                with urlopen(url, timeout=22) as source, partial.open("wb") as out:
                    shutil.copyfileobj(source, out)
                break
            except (URLError, OSError):
                if attempt == 2:
                    raise
        partial.replace(target)
    return target


def shape_reader(name, cache):
    archive = download(f"{NATURAL_EARTH}/ne_10m_{name}.zip", cache)
    with ZipFile(archive) as source:
        return shapefile.Reader(shp=BytesIO(source.read(f"ne_10m_{name}.shp")),
                                dbf=BytesIO(source.read(f"ne_10m_{name}.dbf")))


def overlaps(box, bounds):
    return box[0] <= bounds[2] and box[2] >= bounds[0] and box[1] <= bounds[3] and box[3] >= bounds[1]


def areas(name, cache):
    areas = []
    for shape in shape_reader(name, cache).shapes():
        if not overlaps(shape.bbox, (WEST, SOUTH, EAST, NORTH)):
            continue
        geo = shape.__geo_interface__
        polygons = geo["coordinates"] if geo["type"] == "MultiPolygon" else [geo["coordinates"]]
        for rings in polygons:
            xs, ys = zip(*rings[0])
            areas.append(((min(xs), min(ys), max(xs), max(ys)), rings))
    return areas


def area_mask(rows, cols, west, north, samples, areas):
    box = (west, north - rows / samples, west + cols / samples, north)
    mask = Image.new("1", (cols, rows))
    painter = ImageDraw.Draw(mask)
    for bounds, rings in areas:
        if overlaps(bounds, box):
            for i, ring in enumerate(rings):
                pixels = [((x - west) * samples - 0.5, (north - y) * samples - 0.5) for x, y in ring]
                painter.polygon(pixels, fill=int(i == 0))
    return np.asarray(mask)


def save_grid(output, height, west, north, samples, land, lakes):
    rows, cols = height.shape
    inland = area_mask(rows, cols, west, north, samples, lakes)
    water = ~area_mask(rows, cols, west, north, samples, land) & ~inland
    # Ocean and lake samples use separate offsets. Lakes retain their surface height.
    values = np.rint(np.clip(height, -11000, 8900)).astype("<i2")
    values[water] = np.minimum(values[water], 0) - 16000
    values[inland] = np.maximum(values[inland], -2000) + 16000
    delta = np.diff(values, axis=1, prepend=np.zeros((rows, 1), dtype="<i2"))
    output.write_bytes(gzip.compress(delta.astype("<i2", copy=False).tobytes(), compresslevel=5, mtime=0))


def water_vectors(cache):
    bounds = (WEST, SOUTH, EAST, NORTH)
    vectors = []
    for kind, name in (("lake", "lakes"), ("river", "rivers_lake_centerlines")):
        for record in shape_reader(name, cache).iterShapeRecords():
            shape = record.shape
            if not overlaps(shape.bbox, bounds):
                continue
            # Natural Earth ranks larger features first, allowing smaller waterways to appear on zoom.
            rank = record.record.as_dict().get("scalerank", 6)
            ends = list(shape.parts[1:]) + [len(shape.points)]
            paths = []
            for start, end in zip(shape.parts, ends):
                points = [f"{(lon - 73) * 14:.3f},{(54 - lat) * 17:.3f}" for lon, lat in shape.points[start:end]]
                paths.append("M" + " ".join(points) + ("Z" if kind == "lake" else ""))
            a, b, c, d = shape.bbox
            vectors.append((kind, rank, [(a - 73) * 14, (54 - d) * 17, (c - 73) * 14, (54 - b) * 17], "".join(paths)))
    return vectors


def mercator_y(latitude):
    return 0.5 - np.arcsinh(np.tan(np.radians(latitude))) / (2 * math.pi)


def load_height(bounds, samples, zoom, cache):
    """Reproject the 512-pixel source tiles onto a longitude/latitude grid."""
    west, south, east, north = bounds
    tile_count = 2 ** zoom
    width, height = (east - west) * samples, (north - south) * samples
    cols = ((west + (np.arange(width) + 0.5) / samples + 180) / 360) * tile_count * 512 - 0.5
    rows = mercator_y(north - (np.arange(height) + 0.5) / samples) * tile_count * 512 - 0.5
    start_x, start_y = int(cols[0] // 512), int(rows[0] // 512)
    end_x, end_y = int(math.ceil(cols[-1] + 1) // 512), int(math.ceil(rows[-1] + 1) // 512)
    tiles = [(x, y) for y in range(start_y, end_y + 1) for x in range(start_x, end_x + 1)]
    mosaic = np.empty(((end_y - start_y + 1) * 512, (end_x - start_x + 1) * 512), dtype=np.int16)

    def fetch(tile):
        x, y = tile
        file = download(f"{MAPZEN}/{zoom}/{x}/{y}.tif", cache, f"{zoom}-{x}-{y}.tif")
        with Image.open(file) as source:
            pixels = np.asarray(source)
            if pixels.shape != (512, 512):
                raise ValueError(f"Unexpected source tile size: {file}")
            row, col = (y-start_y)*512, (x-start_x)*512
            mosaic[row:row+512, col:col+512] = np.clip(pixels, -11000, 8900)

    with ThreadPoolExecutor(max_workers=20) as pool:
        for index, _ in enumerate(pool.map(fetch, tiles), start=1):
            if index % 100 == 0 or index == len(tiles):
                print(f"Elevation level {zoom}: {index}/{len(tiles)} source tiles", flush=True)

    x = cols - start_x*512
    y = rows - start_y*512
    x0, y0 = x.astype(np.int32), y.astype(np.int32)
    tx, ty = (x-x0).astype(np.float32), (y-y0).astype(np.float32)
    result = np.empty((height, width), dtype=np.int16)
    for start in range(0, height, 64):
        end = start + 64
        r = y0[start:end, None]
        a = mosaic[r, x0]*(1-tx) + mosaic[r, x0+1]*tx
        b = mosaic[r+1, x0]*(1-tx) + mosaic[r+1, x0+1]*tx
        fraction = ty[start:end, None]
        result[start:end] = np.rint(a*(1-fraction) + b*fraction)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "shanhe-atlas-elevation")
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "data" / "terrain")
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    land = areas("land", args.cache)
    lakes = areas("lakes", args.cache)
    overview = load_height((WEST, SOUTH, EAST, NORTH), 30, 5, args.cache)
    save_grid(args.output / "overview.hgt.gz", overview, WEST, NORTH, 30, land, lakes)
    (args.output / "water.json").write_text(json.dumps(water_vectors(args.cache), separators=(",", ":")), encoding="utf-8")
    height = load_height((69, 14, 141, 56), 120, 7, args.cache)
    for lat in range(15, 55, 5):
        for lon in range(70, 140, 5):
            y, x = (56 - lat - 5) * 120, (lon - 69) * 120
            detail = height[y-2:y+602, x-2:x+602]
            save_grid(args.output / f"{lon}-{lat}.hgt.gz", detail, lon - 2 / 120, lat + 5 + 2 / 120, 120, land, lakes)
    print(f"Wrote {sum(file.stat().st_size for file in args.output.iterdir()):,} bytes of elevation and water data")


if __name__ == "__main__":
    main()
