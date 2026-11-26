"""Build the university atlas from published lists and documented campus additions."""

import argparse
import csv
import json
import re
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

import xlrd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dist" / "data"
LOGOS = "https://static-data.gaokao.cn/upload/logo/{}.jpg"
LOCATION_OVERRIDES = {
    "河北工业大学": "120000",
    "昆山杜克大学": "320500",
    "吉利学院": "510100",
    "西藏民族大学": "610400",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def canonical(name):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", name))


def taiwan_name(name):
    return canonical(name).split("財團法人")[-1].replace("台", "臺")


class TaiwanCrests(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = {}

    def handle_starttag(self, tag, attrs):
        if tag != "img":
            return
        attrs = dict(attrs)
        title = attrs.get("title", "")
        name = attrs.get("alt")
        url = attrs.get("data-src")
        if title.startswith("委員學校介紹（校徽）") and name and url and url.startswith("https://"):
            self.urls[taiwan_name(name)] = url


def locations():
    boundaries = load(DATA / "admin-boundaries.json")
    prefecture_parents = {row["p"] for row in boundaries["city"]}
    regions = [
        *boundaries["city"],
        *[row for row in boundaries["county"] if row["p"] in prefecture_parents],
        *load(DATA / "direct-counties.json"),
        *[row for row in boundaries["province"] if row["n"].endswith(("市", "特别行政区"))],
    ]
    return {(row["id"][:2], row["n"]): row["id"] for row in regions}


def school_tags(flags, authority, note, provincial):
    tags = [tag for field, tag in (
        ("is985", "985"), ("is211", "211"), ("isDoubleFirstClass", "firstClass"),
    ) if flags.get(field)]
    if "合作办学" in note:
        tags.append("coop")
    if authority == "教育部":
        tags.append("ministry")
    if provincial:
        tags.append("provincial")
    if flags.get("type") == "军队院校":
        tags.append("military")
    return tags


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", type=Path, help="directory with the published source files listed in README.md")
    parser.add_argument("--output", type=Path, default=DATA / "universities.json")
    args = parser.parse_args()
    overrides = load(ROOT / "scripts" / "university_additions.json")
    office = locations()
    region_ids = set(office.values()) | set(overrides["places"])
    flag_rows = [json.loads(line) for line in (args.sources / "universities.jsonl").read_text(encoding="utf8").splitlines()]
    flags_by_code = {row["code"]: row for row in flag_rows if row["code"]}
    eol = {
        canonical(row["name"]): row["id"]
        for row in load(args.sources / "eol-list.json")["data"].values()
    }
    ranking = {
        canonical(row["name_zh"]): row["logo_url"]
        for row in load(args.sources / "rank.json")
        if row["logo_url"]
    }
    numeric_aliases = {"华北电力大学": "华北电力大学（北京）"}

    def logo_for(name):
        key = canonical(name)
        logo_id = eol.get(key) or eol.get(canonical(numeric_aliases.get(name, name)))
        return ranking.get(key) or (LOGOS.format(logo_id) if logo_id else None)

    schools = {}

    def add(code, name, city, tags, logo=None, note=None):
        if code in schools:
            raise ValueError(f"Duplicate school code: {code}")
        if city not in region_ids:
            raise ValueError(f"{name}: unmapped city {city}")
        schools[code] = {
            "id": code, "name": name, "tags": tags,
            "placements": {city: [note] if note else []},
        }
        emblem = logo or logo_for(name)
        if emblem:
            schools[code]["logo"] = emblem

    sheet = xlrd.open_workbook(str(args.sources / "official.xls")).sheet_by_index(0)
    provincial = {
        school: [group["label"], group["source"]]
        for group in overrides["provincial"] for school in group["schools"]
    }
    bachelor_count = 0
    for i in range(sheet.nrows):
        _, name, value, authority, location, level, note = sheet.row_values(i)
        if level != "本科":
            continue
        code = str(int(value))
        city = LOCATION_OVERRIDES.get(name) or office.get((code[2:4], location))
        flags = flags_by_code.get(code, {})
        tags = school_tags(flags, authority, note, name in provincial)
        add(code, name, city, tags)
        if name in provincial:
            schools[code]["provincialSource"] = provincial[name]
        bachelor_count += 1
    if not provincial.keys() <= {school["name"] for school in schools.values()}:
        raise ValueError("Unrecognised school in the provincial programme list")

    military = [row for row in flag_rows if row["type"] == "军队院校" and row["level"] == "本科"]
    for row in military:
        tags = school_tags(row, row["authority"], "", False)
        city = office.get((row["provinceCode"], row["location"]))
        add("mil-" + str(row["id"]), row["name"], city, tags)

    for code, name, city, tags, logo, url in overrides["institutions"]:
        add(code, name, city, tags, logo, ["院校名录", url])

    crests = TaiwanCrests()
    crests.feed((args.sources / "tw-logos.html").read_text(encoding="utf-8"))
    tw = 0
    with (args.sources / "tw.csv").open(encoding="utf-8-sig", newline="") as file:
        for row in csv.reader(file):
            if not row or not row[0].isdigit() or "專科學校" in row[4] or row[4].endswith("專校"):
                continue
            place = next((id for id, data in overrides["places"].items() if data[0] == row[9]), None)
            add("tw-" + row[1], row[4], place, [], crests.urls.get(taiwan_name(row[4])),
                note=["院校", row[16]] if row[16].startswith(("http://", "https://")) else None)
            tw += 1

    by_name = {school["name"]: school for school in schools.values()}
    for name, city, label, source in overrides["campuses"]:
        if city not in region_ids:
            raise ValueError(f"{name}: unmapped campus {city}")
        campuses = by_name[name]["placements"].setdefault(city, [])
        campuses.append([label, source])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "schools": list(schools.values()), "places": overrides["places"],
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    placements = sum(len(school["placements"]) for school in schools.values())
    logos = sum("logo" in school for school in schools.values())
    print(f"{bachelor_count} MOE bachelor's institutions; {len(military)} military, {tw} Taiwan; "
          f"{len(schools)} distinct institutions, {placements} city placements, {logos} logos")


if __name__ == "__main__":
    main()
