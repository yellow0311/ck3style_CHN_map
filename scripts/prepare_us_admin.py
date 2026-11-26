"""Package U.S. Census-derived state and county boundaries and 2024 BEA data."""
import argparse
import csv
import io
import json
from pathlib import Path
from zipfile import ZipFile

from shapely import make_valid
from shapely.geometry import shape
from shapely.ops import transform

from us_geometry import project


STATES = {
    '01':'阿拉巴马州','02':'阿拉斯加州','04':'亚利桑那州','05':'阿肯色州','06':'加利福尼亚州',
    '08':'科罗拉多州','09':'康涅狄格州','10':'特拉华州','11':'哥伦比亚特区','12':'佛罗里达州',
    '13':'佐治亚州','15':'夏威夷州','16':'爱达荷州','17':'伊利诺伊州','18':'印第安纳州',
    '19':'艾奥瓦州','20':'堪萨斯州','21':'肯塔基州','22':'路易斯安那州','23':'缅因州',
    '24':'马里兰州','25':'马萨诸塞州','26':'密歇根州','27':'明尼苏达州','28':'密西西比州',
    '29':'密苏里州','30':'蒙大拿州','31':'内布拉斯加州','32':'内华达州','33':'新罕布什尔州',
    '34':'新泽西州','35':'新墨西哥州','36':'纽约州','37':'北卡罗来纳州','38':'北达科他州',
    '39':'俄亥俄州','40':'俄克拉何马州','41':'俄勒冈州','42':'宾夕法尼亚州','44':'罗得岛州',
    '45':'南卡罗来纳州','46':'南达科他州','47':'田纳西州','48':'得克萨斯州','49':'犹他州',
    '50':'佛蒙特州','51':'弗吉尼亚州','53':'华盛顿州','54':'西弗吉尼亚州','55':'威斯康星州','56':'怀俄明州',
}
LOCAL_NAMES = {
    '06037':'洛杉矶县','06059':'奥兰治县','06073':'圣迭戈县','06075':'旧金山市县','06085':'圣克拉拉县',
    '06067':'萨克拉门托县','17031':'库克县','36061':'纽约县（曼哈顿）','36047':'金斯县（布鲁克林）',
    '36081':'皇后县','36005':'布朗克斯县','36085':'里士满县（史泰登岛）','48201':'哈里斯县',
    '48113':'达拉斯县','53033':'金县','04013':'马里科帕县','12086':'迈阿密－戴德县',
    '25025':'萨福克县','25017':'米德尔塞克斯县','15003':'檀香山市县','02020':'安克雷奇市镇',
    '08031':'丹佛市县','11001':'哥伦比亚特区','42101':'费城县','32003':'克拉克县',
    '26163':'韦恩县','22071':'奥尔良堂区','13121':'富尔顿县','08014':'布鲁姆菲尔德市县',
}


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":")), encoding="utf-8")


def read_features(path):
    return json.loads(path.read_text(encoding="utf-8"))["features"]


def polygons(geom):
    if geom.geom_type == "Polygon":
        yield geom
    elif hasattr(geom, "geoms"):
        for part in geom.geoms:
            yield from polygons(part)


def projected(geojson):
    return make_valid(transform(project, shape(geojson)))


def packed_polygon(geometry):
    parts = sorted(polygons(geometry), key=lambda region: region.area, reverse=True)
    anchor = parts[0].representative_point()
    outlines = []
    for area in parts:
        for ring in [area.exterior, *area.interiors]:
            outlines.append("M" + " ".join(f"{x:.3f},{y:.3f}" for x, y in ring.coords) + "Z")
    return {
        "x":round(anchor.x, 3), "y":round(anchor.y, 3),
        "b":[round(value, 3) for value in geometry.bounds], "d":"".join(outlines)
    }


def load_boundaries(cache):
    states, counties = [], []
    for row in read_features(cache / "states-arc.json"):
        attrs = row["properties"]
        code = str(attrs.get("FIPS") or attrs.get("St_FIPS")).zfill(2)
        if code not in STATES:
            continue
        name = attrs.get("State_Name") or attrs.get("NAME")
        states.append(dict(id=code,n=STATES[code],en=name,nation=code,p=None,
                           type="联邦特区" if code=="11" else "州",**packed_polygon(projected(row["geometry"]))))
    for path in sorted(cache.glob("counties-*.json")):
        for row in read_features(path):
            attrs = row["properties"]
            code, state = attrs["FIPS"], attrs["St_FIPS"]
            if state not in STATES:
                continue
            name = attrs["County_Name"]
            unit = "堂区" if name.endswith("Parish") else "自治市镇" if name.endswith("Borough") else "县级辖区"
            counties.append(dict(id=code,n=LOCAL_NAMES.get(code,name),en=name,nation=state,p=state,type=unit,
                                 **packed_polygon(projected(row["geometry"]))))
    assert len(states)==51 and len(counties)>3100 and len(counties)==len({area["id"] for area in counties})
    return {"province":sorted(states,key=lambda row:row["id"]), "city":[], "county":sorted(counties,key=lambda row:row["id"])}


def bea_values(path, member_prefix, line, divisor):
    with ZipFile(path) as archive:
        name = next(item for item in archive.namelist() if item.startswith(member_prefix+"__ALL_AREAS"))
        with archive.open(name) as source:
            csv_rows = csv.DictReader(io.TextIOWrapper(source,encoding="cp1252"))
            values = {}
            for row in csv_rows:
                code = row["GeoFIPS"].strip().strip('"')
                if not (code.isdigit() and row["LineCode"] == line):
                    continue
                try:
                    values[code] = round(float(row["2024"])/divisor, 4)
                except ValueError:
                    continue
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--output", type=Path, default=Path("dist/data/us"))
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    bounds = load_boundaries(args.cache)
    gdp = bea_values(args.cache / "gdp.zip","CAGDP1","3",100_000)
    gdp.update(bea_values(args.cache / "state-gdp.zip","SAGDP2","1",100))
    population = bea_values(args.cache / "dep-pop.zip","CAINC1","2",10_000)
    stats = {}
    for region in bounds["province"] + bounds["county"]:
        key = region["id"]
        source_key = key+"000" if len(key)==2 else "11000" if key=="11001" else key
        stats[key] = [gdp.get(source_key),population.get(source_key)]
    assert all(stats[state["id"]][0] is not None for state in bounds["province"])
    dump(args.output / "admin-boundaries.json",bounds)
    dump(args.output / "statistics.json",stats)
    print(len(bounds["province"]),"states and DC",len(bounds["county"]),"counties and equivalents")
    print("Covered statistics:",*[sum(row[i] is not None for row in stats.values()) for i in range(2)])


if __name__ == "__main__":
    main()
