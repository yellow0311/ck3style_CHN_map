"""Build airport and nonstop destination data from saved public source pages."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup


REGIONS = {"CN", "HK", "MO", "TW"}
# 达州河市机场已随达州金垭机场（DZH）启用而关闭。
# https://www.caac.gov.cn/PHONE/GLJ_PHONE/XNGLJ/XN_XXGK/XNYSSC/202301/t20230116_216897.html
CLOSED = {"DAX"}
LOCAL_NAMES = {
    "CYI": "嘉义机场", "HUN": "花莲机场", "KHH": "高雄国际机场", "KNH": "金门尚义机场",
    "KYD": "兰屿机场", "LZN": "马祖南竿机场", "MFK": "马祖北竿机场", "MZG": "澎湖机场",
    "RMQ": "台中清泉岗机场", "TNN": "台南机场", "TPE": "桃园国际机场",
    "TSA": "台北松山机场", "TTT": "台东丰年机场",
}
GRADE = re.compile(r"\b[1-4][A-F]\b")
EXCLUDE = re.compile(r"\b(?:via|begins?|starts?|ends?|terminated|suspended|resumes?)\b", re.I)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def soup_from(path):
    return BeautifulSoup(path.read_bytes(), "lxml")


def normalize(text):
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in text if char.isalnum())


def airport_grades(path):
    grades = {}
    for table in soup_from(path).select("table.wikitable"):
        headings = [th.get_text(" ", strip=True) for th in table.select("tr:first-child th")]
        if not {"ICAO", "IATA", "指标"}.issubset(headings):
            continue
        for row in table.select("tr")[1:]:
            cells = row.find_all("td", recursive=False)
            if len(cells) < 6:
                continue
            code = cells[2].get_text(strip=True)
            if not re.fullmatch(r"[A-Z]{3}", code):
                continue
            match = GRADE.search(cells[4].get_text(" ", strip=True))
            name = cells[0].find("a")
            grades[code] = (name.get_text(strip=True) if name else "", match[0] if match else "")
    return grades


def airport_index(records):
    aliases = defaultdict(set)
    for code, airport in records.items():
        for text in {airport["name"], airport.get("served_city"), airport.get("municipality"), code}:
            if text:
                aliases[normalize(text)].add(code)
        name = re.sub(r"\b(?:International|Airport)\b", "", airport["name"], flags=re.I)
        aliases[normalize(name)].add(code)
    return {name: next(iter(codes)) for name, codes in aliases.items() if len(codes) == 1}


def public_destinations(path, index):
    for table in soup_from(path).select("table.wikitable"):
        heading = table.find_previous(["h2", "h3", "h4"])
        if heading and re.search("cargo|freight|former|previous", heading.get_text(" ", strip=True), re.I):
            continue
        cols = [th.get_text(" ", strip=True).lower() for th in table.select("tr:first-child th")]
        if not any(col.startswith("destination") for col in cols):
            continue
        for row in table.select("tr")[1:]:
            cells = row.find_all(["th", "td"], recursive=False)
            if len(cells) != 2 or "cargo" in cells[0].get_text(" ", strip=True).lower():
                continue
            cell = cells[1]
            for element in cell.select("sup, s, del"):
                element.decompose()
            for br in cell.find_all("br"):
                br.replace_with(";")
            for link in cell.select("a[href]"):
                url = urlsplit(link["href"])
                if not url.path.startswith("/wiki/"):
                    continue
                title = unquote(url.path.rsplit("/", 1)[-1])
                name = link.get_text(" ", strip=True)
                code = index.get(normalize(title)) or index.get(normalize(name))
                if code:
                    link.replace_with(f" @{code}@ ")
            for part in re.split(r"[,;]", cell.get_text(" ", strip=True)):
                if not EXCLUDE.search(part):
                    yield from re.findall(r"@([A-Z]{3})@", part)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--date", required=True, help="ISO date when the destination pages were saved")
    parser.add_argument("--output", type=Path, default=Path("dist/data/airports.json"))
    args = parser.parse_args()
    database = read_json(args.cache / "airports.json")
    records = {airport["iata"]: airport for airport in database["airports"] if airport["iata"] not in CLOSED}
    local = {code: a for code, a in records.items() if a["country"] in REGIONS}
    grades = airport_grades(args.cache / "airport-grades.html")
    pages = args.cache / "airport-pages"
    urls = read_json(pages / "urls.json")
    index = airport_index(records)
    points, routes, sources, foreign = [], {}, {}, {}
    for code, airport in sorted(local.items()):
        name, grade = grades.get(code, ("", ""))
        points.append([code, name or LOCAL_NAMES.get(code, airport["name"]), grade, airport["longitude"], airport["latitude"]])
        page = pages / f"{code}.html"
        if not page.is_file():
            continue
        destinations = sorted(set(public_destinations(page, index)) - {code})
        if destinations:
            routes[code] = destinations
            sources[code] = urls[code]
            foreign.update({dest: records[dest]["name"] for dest in destinations if dest not in local})
    result = {
        "date": args.date, "airportDate": database["generated"], "airports": points,
        "routes": routes, "foreign": foreign, "sources": sources,
    }
    if "PEK" not in routes or len(routes["PEK"]) < 20:
        raise SystemExit("Incomplete sample: the PEK airport page did not yield its main routes")
    args.output.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(len(points), Counter(row[2] or "unverified" for row in points))
    print(len(routes), "airports with destinations", sum(map(len,routes.values())), "airport pairs")


if __name__ == "__main__":
    main()
