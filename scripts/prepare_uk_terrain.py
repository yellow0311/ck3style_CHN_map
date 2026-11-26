"""Build the UK elevation grid and rivers and lakes."""
import argparse
import json
from pathlib import Path

from prepare_terrain import areas, load_height, save_grid, water_vectors
from uk_geometry import project


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--output", type=Path, default=Path("dist/data/uk/terrain"))
    args = parser.parse_args()
    bounds = (-9, 49, 3, 62)
    samples = 120
    args.output.mkdir(parents=True, exist_ok=True)
    args.cache.mkdir(parents=True, exist_ok=True)
    land = areas("land", args.cache, bounds)
    lakes = areas("lakes", args.cache, bounds)
    heights = load_height(bounds, samples, 7, args.cache)
    save_grid(args.output / "overview.hgt.gz", heights, bounds[0], bounds[3], samples, land, lakes)
    vectors = water_vectors(args.cache, bounds, project)
    (args.output / "water.json").write_text(json.dumps(vectors, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
