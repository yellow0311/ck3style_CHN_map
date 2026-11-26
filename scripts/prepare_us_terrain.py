"""Build the U.S. elevation grid from Mapzen and Natural Earth."""
import argparse
import json
from pathlib import Path

from prepare_terrain import areas, load_height, save_grid, water_vectors
from us_geometry import project


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--output", type=Path, default=Path("dist/data/us/terrain"))
    args = parser.parse_args()
    bounds = (-188, 17, -64, 72)
    samples = 30
    args.output.mkdir(parents=True, exist_ok=True)
    heights = load_height(bounds, samples, 5, args.cache)
    land = areas("land", args.cache, bounds)
    lakes = areas("lakes", args.cache, bounds)
    save_grid(args.output / "overview.hgt.gz", heights, bounds[0], bounds[3], samples, land, lakes)
    (args.output / "water.json").write_text(json.dumps(water_vectors(args.cache,bounds,project),
        separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
