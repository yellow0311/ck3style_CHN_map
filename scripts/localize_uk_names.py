"""Apply the atlas's Chinese names to generated UK railway, road and university data."""
import argparse
import json
from pathlib import Path


NAMES = Path(__file__).with_name("uk_chinese_names.json")


def localize(data_dir):
    names = json.loads(NAMES.read_text(encoding="utf-8"))
    files = {
        filename: json.loads((data_dir / filename).read_text(encoding="utf-8"))
        for filename in ("railways.json", "roads.json", "universities.json")
    }
    for group in ("lines", "stations"):
        for record in files["railways.json"][group]:
            english = record.setdefault("en", record["n"])
            record["n"] = names["rail_" + group][english]

    for road in files["roads.json"]["roads"]:
        ref, title, kind = road[:3]
        if len(road) == 5:
            road.append(title)
        road[1] = ref + (" 高速公路" if kind == "expressway" else " 号公路")

    for institution in files["universities.json"]["schools"]:
        english = institution.setdefault("en", institution["name"])
        institution["name"] = names["schools"][english]
        institution.pop("abbr", None)
        for district, locations in institution["placements"].items():
            localized = []
            for label, url, *original in locations:
                text = original[0] if original else label
                translated = names["campuses"][text]
                localized.append([translated, url, text] if translated != text else [translated, url])
            institution["placements"][district] = localized

    for filename, data in files.items():
        (data_dir / filename).write_text(
            json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, default=Path("dist/data/uk"))
    args = parser.parse_args()
    localize(args.directory)
