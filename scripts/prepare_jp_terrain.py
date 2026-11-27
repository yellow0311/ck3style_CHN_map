"""Build the Japanese elevation grid and water layer from Mapzen and Natural Earth."""
import argparse
import json
from pathlib import Path

from prepare_terrain import areas, load_height, save_grid, water_vectors


def project(lon, lat):
    return (lon - 122) * 30, (46 - lat) * 38


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--output", type=Path, default=Path("dist/data/jp/terrain"))
    args = parser.parse_args()
    bounds = (122, 20, 155, 46)
    samples = 60
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    height = load_height(bounds, samples, 6, args.cache)
    land = areas("land", args.cache, bounds)
    lakes = areas("lakes", args.cache, bounds)
    save_grid(args.output / "overview.hgt.gz", height, bounds[0], bounds[3], samples, land, lakes)
    water = water_vectors(args.cache, bounds, project)
    (args.output / "water.json").write_text(json.dumps(water, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
