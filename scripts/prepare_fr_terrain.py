"""Build terrain for metropolitan France from Mapzen and Natural Earth."""
import argparse
import json
from pathlib import Path

from prepare_terrain import areas, load_height, save_grid, water_vectors


def project(lon, lat):
    return (lon + 6) * 49, (52 - lat) * 69


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--output", type=Path, default=Path("dist/data/fr/terrain"))
    args = parser.parse_args()
    bounds = (-6, 41, 10, 52)
    samples = 120
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    heights = load_height(bounds, samples, 7, args.cache)
    save_grid(args.output / "overview.hgt.gz", heights, bounds[0], bounds[3], samples,
              areas("land", args.cache, bounds), areas("lakes", args.cache, bounds))
    vectors = water_vectors(args.cache, bounds, project)
    (args.output / "water.json").write_text(json.dumps(vectors, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
