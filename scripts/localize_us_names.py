"""Apply curated and transliterated Chinese names to the generated US atlas data."""
import argparse
import json
from pathlib import Path


NAMES = Path(__file__).with_name("us_chinese_names.json")


def localize(directory):
    names = json.loads(NAMES.read_text(encoding="utf-8"))

    def read(filename):
        return json.loads((directory / filename).read_text(encoding="utf-8"))

    def save(filename, data):
        (directory / filename).write_text(
            json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )

    admin = read("admin-boundaries.json")
    for county in admin["city"] or admin["county"]:
        county["n"] = names["counties"].get(county["id"], county["n"])
    save("admin-boundaries.json", admin)

    colleges = read("universities.json")
    for school in colleges["schools"]:
        school["name"] = names["schools"][school["id"]]
        for district, locations in school["placements"].items():
            entries = []
            for label, url, *original in locations:
                if label == "院校":
                    entries.append([label, url])
                else:
                    source = original[0] if original else label
                    entries.append([names["campuses"][source], url, source])
            school["placements"][district] = entries
    save("universities.json", colleges)

    airports = read("airports.json")
    for airport in airports["airports"]:
        airport[1] = names["airports"][airport[0]]
    airports.setdefault("foreignEn", airports["foreign"])
    airports["foreign"] = {code: names["foreign_airports"][code] for code in airports["foreignEn"]}
    save("airports.json", airports)

    railway = read("railways.json")
    for group in ("lines", "stations"):
        for entry in railway[group]:
            source = entry.setdefault("en", entry["n"])
            entry["n"] = names["rail_" + group][source]
    save("railways.json", railway)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, default=Path("dist/data/us"))
    localize(parser.parse_args().directory)
