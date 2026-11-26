"""Build UK administrative boundaries and ONS local statistics."""
import argparse
import csv
from collections import defaultdict
import json
from pathlib import Path

from openpyxl import load_workbook
from shapely import make_valid, union_all
from shapely.geometry import shape
from shapely.ops import transform

from uk_geometry import project


NATIONS = {
    "E": ("E92000001", "英格兰", "England"),
    "S": ("S92000003", "苏格兰", "Scotland"),
    "W": ("W92000004", "威尔士", "Wales"),
    "N": ("N92000002", "北爱尔兰", "Northern Ireland"),
}
REGION_NAMES = ["东北英格兰", "西北英格兰", "约克郡与亨伯", "东米德兰兹", "西米德兰兹", "东英格兰", "伦敦", "东南英格兰", "西南英格兰"]
DISTRICT_NAMES = Path(__file__).with_name("uk_admin_names.csv")
TYPES = {
    "E06":"单一管理区","E07":"非都市区","E08":"都市区","E09":"伦敦自治市",
    "S12":"议会辖区","W06":"主要辖区","N09":"地方政府区",
}
PREVIOUS_CODES = {"E08000038":"E08000016","E08000039":"E08000019"}
ITL_NATIONS = {"E92000001":"TLB","S92000003":"TLM","W92000004":"TLL","N92000002":"TLN"}


def json_write(path, data):
    path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")


def polygons(geometry):
    if geometry.geom_type == "Polygon":
        yield geometry
    elif hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from polygons(part)


def feature(code, en, label, nation, parent, category, geometry):
    geometry = transform(project, geometry)
    areas = sorted(polygons(geometry), key=lambda polygon: polygon.area, reverse=True)
    if not areas:
        raise ValueError(f"Missing map geometry: {code}")
    anchor = areas[0].representative_point()
    paths = []
    for area in areas:
        for ring in [area.exterior,*area.interiors]:
            paths.append("M" + " ".join(f"{x:.3f},{y:.3f}" for x,y in ring.coords) + "Z")
    return {"id":code, "n":label, "en":en, "nation":nation, "p":parent, "type":category,
            "x":round(anchor.x,3), "y":round(anchor.y,3),
            "b":[round(v,3) for v in geometry.bounds], "d":"".join(paths)}


def load_boundaries(cache):
    with DISTRICT_NAMES.open(encoding="utf-8",newline="") as source:
        translations = {row["code"]:row["zh"] for row in csv.DictReader(source)}
    with (cache / "regions.csv").open(encoding="utf-8-sig",newline="") as source:
        lookup = {row["LAD25CD"]:(row["RGN25CD"],row["RGN25NM"]) for row in csv.DictReader(source)}
    features = json.loads((cache / "lad.geojson").read_text(encoding="utf-8"))["features"]
    district_codes = {item["properties"]["LAD25CD"] for item in features}
    if translations.keys() != district_codes:
        missing = sorted(district_codes - translations.keys())
        extra = sorted(translations.keys() - district_codes)
        raise ValueError(f"Update the district name table. Missing: {missing}. Extra: {extra}")
    districts = []
    nation_shapes, region_shapes = defaultdict(list), defaultdict(list)
    region_labels = {}
    for item in features:
        location = item["properties"]
        code, name = location["LAD25CD"],location["LAD25NM"]
        nation = NATIONS[code[0]][0]
        geometry = make_valid(shape(item["geometry"]))
        nation_shapes[nation].append(geometry)
        parent = lookup[code][0] if code.startswith("E") else nation
        if parent != nation:
            region_shapes[parent].append(geometry)
            region_labels[parent] = lookup[code][1]
        district = feature(code,name,translations[code],nation,parent,TYPES[code[:3]],geometry)
        if code in PREVIOUS_CODES:
            district["statCode"] = PREVIOUS_CODES[code]
        if code == "E09000001":
            district["type"] = "伦敦金融城"
        districts.append(district)
    regions = [feature(code,region_labels[code],REGION_NAMES[int(code[-1])-1],NATIONS["E"][0],
                       NATIONS["E"][0],"英格兰大区",union_all(parts)) for code,parts in sorted(region_shapes.items())]
    nations = [feature(code,en,label,code,None,"组成国",union_all(nation_shapes[code]))
               for code,label,en in NATIONS.values()]
    if (len(nations),len(regions),len(districts)) != (4,9,361):
        raise ValueError("The boundary dataset has unexpected coverage")
    return {"province":nations, "city":regions, "county":districts}


def load_statistics(cache, boundaries):
    workbook = load_workbook(cache / "gdp.xlsx",read_only=True,data_only=True)
    rows = list(workbook["Table 5"].values)
    year = rows[1].index("2024")
    gdp = {row[1]:row[year] for row in rows[2:] if isinstance(row[year],(int,float))}
    workbook.close()
    workbook = load_workbook(cache / "gdp-itl.xlsx",read_only=True,data_only=True)
    rows = list(workbook["Table 5"].values)
    year = rows[1].index("2024")
    itl_gdp = {row[1]:row[year] for row in rows[2:] if isinstance(row[year],(int,float))}
    workbook.close()
    workbook = load_workbook(cache / "pop.xlsx",read_only=True,data_only=True)
    people = {row[0]:row[3] for row in workbook["MYE2 - Persons"].values if isinstance(row[3],(int,float))}
    workbook.close()
    result = {}
    for group in ("county","city","province"):
        for area in boundaries[group]:
            code = area["id"]
            previous = area.get("statCode")
            itl = ITL_NATIONS.get(code)
            if group == "city":
                itl = "TL" + "CDEFGHIJK"[int(code[-1])-1]
            gross = itl_gdp.get(itl) if itl else gdp.get(code,gdp.get(previous))
            residents = people.get(code,people.get(previous))
            result[code] = [round(gross/100,2) if gross is not None else None,
                            round(residents/10000,4) if residents is not None else None]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--output", type=Path, default=Path("dist/data/uk"))
    args = parser.parse_args()
    boundaries = load_boundaries(args.cache)
    stats = load_statistics(args.cache,boundaries)
    args.output.mkdir(parents=True,exist_ok=True)
    json_write(args.output / "admin-boundaries.json",boundaries)
    json_write(args.output / "statistics.json",stats)
    print({key:len(value) for key,value in boundaries.items()})
    print("GDP and population",*[sum(value[i] is not None for value in stats.values()) for i in range(2)],"/",len(stats))


if __name__ == "__main__":
    main()
