"""Prepare boundaries for towns and streets directly administered by four prefecture-level cities."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import osmium
from shapely import from_wkb, make_valid, to_geojson
from shapely.ops import unary_union

from prepare_boundaries import OUTPUT, convert


# The municipal directories determine names and membership, including the three
# offices listed for Danzhou. Development zones are separate from that directory.
CITIES = {
    "441900": {
        "name": "东莞市", "region": "guangdong", "label": "镇街级",
        "source": "https://www.dg.gov.cn/zjdz/dzgk/xzqh/",
        "units": """东城街道 南城街道 万江街道 莞城街道 石碣镇 石龙镇 茶山镇 石排镇 企石镇 横沥镇
            桥头镇 谢岗镇 东坑镇 常平镇 寮步镇 樟木头镇 大朗镇 黄江镇 清溪镇 塘厦镇 凤岗镇 大岭山镇
            长安镇 虎门镇 厚街镇 沙田镇 道滘镇 洪梅镇 麻涌镇 望牛墩镇 中堂镇 高埗镇""".split(),
    },
    "442000": {
        "name": "中山市", "region": "guangdong", "label": "镇街级",
        "source": "https://www.zs.gov.cn/zjzs/zsgk/content/post_1669002.html",
        "units": """石岐街道 东区街道 中山港街道 西区街道 南区街道 五桂山街道 民众街道 南朗街道
            小榄镇 黄圃镇 东凤镇 古镇镇 沙溪镇 坦洲镇 港口镇 三角镇 横栏镇 南头镇 阜沙镇 三乡镇
            板芙镇 大涌镇 神湾镇""".split(),
    },
    "460400": {
        "name": "儋州市", "region": "hainan", "label": "乡镇级",
        "source": "https://www.danzhou.gov.cn/danzhou/zjdz/202403/t20240313_3617228.html",
        "units": """那大镇 和庆镇 南丰镇 大成镇 雅星镇 兰洋镇 光村镇 木棠镇 海头镇 峨蔓镇 王五镇
            白马井镇 中和镇 排浦镇 东成镇 新州镇 新英湾办事处 干冲办事处 三都办事处""".split(),
        "aliases": {"新英湾办事处": "新英湾区", "干冲办事处": "干冲区", "三都办事处": "三都区"},
    },
    "620200": {
        "name": "嘉峪关市", "region": "gansu", "label": "镇街级",
        "source": "https://www.jyg.gov.cn/zjjyg/",
        "units": "雄关街道 钢城街道 新城镇 文殊镇 峪泉镇".split(),
    },
}


def read_areas(source, names):
    def polygon_parts(geometry):
        if geometry.geom_type == "Polygon":
            yield geometry
        elif geometry.geom_type in {"MultiPolygon", "GeometryCollection"}:
            for part in geometry.geoms:
                yield from polygon_parts(part)

    named_areas = defaultdict(list)
    factory = osmium.geom.WKBFactory()
    processor = osmium.FileProcessor(source).with_areas(osmium.filter.TagFilter(("boundary", "administrative")))
    processor.with_filter(osmium.filter.EntityFilter(osmium.osm.AREA))
    for area in processor:
        if area.from_way():
            continue
        tags = area.tags
        matches = names.intersection(tags.get(key) for key in ("name", "name:zh", "name:zh-Hans", "official_name"))
        if not matches or not tags.get("admin_level"):
            continue
        shape = make_valid(from_wkb(bytes.fromhex(factory.create_multipolygon(area))))
        shape = unary_union(list(polygon_parts(shape)))
        if not shape.is_empty:
            for match in matches:
                named_areas[match].append((area.orig_id(), tags.get("admin_level"), shape))
    return named_areas


def prepare_city(code, city, names):
    parents = [shape for _, level, shape in names[city["name"]] if level in {"5", "6"}]
    if len(parents) != 1:
        raise ValueError(f'{city["name"]}: expected one municipal boundary, found {len(parents)}')
    parent = parents[0]
    units = []
    missing = []
    for name in city["units"]:
        candidates = names[name] or names[city.get("aliases", {}).get(name, name)]
        matches = [(relation, shape) for relation, level, shape in candidates if level in {"7", "8", "9"}
                   and parent.intersection(shape).area >= shape.area * .9]
        key = f"{code}:{name}"
        if not matches:
            units.append({"id": key, "n": name})
            missing.append(name)
            continue
        if len(matches) != 1:
            raise ValueError(f'{city["name"]} {name}: conflicting boundaries {[relation for relation, _ in matches]}')
        relation, shape = matches[0]
        center = shape.representative_point()
        feature = {"properties": {"name": name, "adcode": key, "center": [center.x, center.y]},
                   "geometry": json.loads(to_geojson(shape))}
        unit = convert(feature)
        unit.pop("p")
        unit["osm"] = relation
        units.append(unit)
    count = len(units) - len(missing)
    print(f'{city["name"]}: {count}/{len(units)} boundaries' + (f'; missing {", ".join(missing)}' if missing else ''))
    return {"label": city["label"], "sources": [[f'{city["name"]} · 镇街名录', city["source"]]], "units": units}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extracts", type=Path, help="directory with guangdong.osm.pbf, hainan.osm.pbf and gansu.osm.pbf")
    parser.add_argument("--output", type=Path, default=OUTPUT / "townships.json")
    args = parser.parse_args()
    result = {}
    for region in ("guangdong", "hainan", "gansu"):
        cities = {code: city for code, city in CITIES.items() if city["region"] == region}
        names = {name for city in cities.values() for name in [city["name"], *city["units"]]}
        for city in cities.values():
            names.update(city.get("aliases", {}).values())
        areas = read_areas(args.extracts / f"{region}.osm.pbf", names)
        for code, city in cities.items():
            result[code] = prepare_city(code, city, areas)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
