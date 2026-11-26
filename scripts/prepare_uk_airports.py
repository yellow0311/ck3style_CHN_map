"""Build UK airport markers and observed scheduled routes from CAA annual CSVs."""
import argparse
import csv
from collections import defaultdict
import json
from pathlib import Path


CAA_URL = "https://www.caa.co.uk/data-and-analysis/uk-aviation-market/airports/uk-airport-data/uk-airport-data-2025/annual-2025/"
ALIASES = {
    "GATWICK":"LGW","HEATHROW":"LHR","LONDON CITY":"LCY","LUTON":"LTN","SOUTHEND":"SEN","STANSTED":"STN",
    "ABERDEEN":"ABZ","BARRA":"BRR","BELFAST CITY (GEORGE BEST)":"BHD","BELFAST INTERNATIONAL":"BFS",
    "BENBECULA":"BEB","BIRMINGHAM":"BHX","BOURNEMOUTH":"BOH","BRISTOL":"BRS","CAMPBELTOWN":"CAL",
    "CARDIFF WALES":"CWL","CITY OF DERRY (EGLINTON)":"LDY","DUNDEE":"DND","EAST MIDLANDS INTERNATIONAL":"EMA",
    "EDINBURGH":"EDI","EXETER":"EXT","GLASGOW":"GLA","HUMBERSIDE":"HUY","INVERNESS":"INV","ISLAY":"ILY",
    "ISLES OF SCILLY (ST.MARYS)":"ISC","KIRKWALL":"KOI","LANDS END (ST JUST)":"LEQ","LEEDS BRADFORD":"LBA",
    "LERWICK (TINGWALL)":"LWK","LIVERPOOL (JOHN LENNON)":"LPL","MANCHESTER":"MAN","NEWCASTLE":"NCL",
    "NEWQUAY":"NQY","NORWICH":"NWI","PRESTWICK":"PIK","SOUTHAMPTON":"SOU","STORNOWAY":"SYY",
    "SUMBURGH":"LSI","TEESSIDE INTERNATIONAL AIRPORT":"MME","TIREE":"TRE","WICK JOHN O GROATS":"WIC",
    "ALDERNEY":"ACI","GUERNSEY":"GCI","ISLE OF MAN":"IOM","JERSEY":"JER",
}
NAMES = Path(__file__).with_name("uk_airport_names.json")


def csv_rows(path):
    with path.open(encoding="utf-8-sig",newline="") as source:
        yield from csv.DictReader(source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    parser.add_argument("airports", type=Path, help="AirportMiles CC0 airport file")
    parser.add_argument("--output", type=Path, default=Path("dist/data/uk/airports.json"))
    args = parser.parse_args()
    source = json.loads(args.airports.read_text(encoding="utf-8"))
    names = json.loads(NAMES.read_text(encoding="utf-8"))
    database = {a["iata"]:a for a in source["airports"]}
    local = {code:a for code,a in database.items() if a["country"] == "GB"}
    pax = {ALIASES[row["rpt_apt_name"]]:int(row["term_pax_tp"] or 0)
           for row in csv_rows(args.cache / "caa09.csv") if row["rpt_apt_name"] in ALIASES}
    routes = defaultdict(set)
    outside = {}
    for row in csv_rows(args.cache / "caa122.csv"):
        if int(row["total_pax_shd_tp"] or 0) <= 0:
            continue
        a,b = (ALIASES.get(row[key]) for key in ("apt1_apt_name","apt2_apt_name"))
        for origin,target in ((a,b),(b,a)):
            if origin in local and target:
                routes[origin].add(target)
                if target not in local:
                    outside[target] = database[target]["name"]
    for row in csv_rows(args.cache / "caa121.csv"):
        if int(row["ty_s_pax"] or 0) <= 0:
            continue
        code = ALIASES.get(row["uk_apt"])
        if code not in local:
            continue
        name = row["foreign_apt"].strip()
        if not name or name.startswith("TOTAL"):
            continue
        key = f'{name} · {row["foreign_country"].strip()}'
        outside[key] = key
        routes[code].add(key)
    points = []
    for code,airport in sorted(local.items()):
        passengers = pax.get(code)
        category = "" if passengers is None else "hub" if passengers >= 10_000_000 else "major" if passengers >= 1_000_000 else "regional"
        points.append([code,names["iata"][code],category,airport["longitude"],airport["latitude"],passengers,airport["name"]])
    data = {"date":"2025","airportDate":source["generated"],"airports":points,
            "routes":{code:sorted(destinations) for code,destinations in sorted(routes.items())},
            "foreign":{code:names["iata"].get(code) or names["foreign"][code] for code in outside},
            "foreignEn":outside,"sources":{code:CAA_URL for code in routes}}
    if len(routes["LHR"]) < 100 or "BFS" not in routes["STN"]:
        raise ValueError("Expected scheduled airport pairs are missing")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print(len(points),"airports",len(routes),"CAA route origins",sum(map(len,routes.values())),"observed airport pairs")


if __name__ == "__main__":
    main()
