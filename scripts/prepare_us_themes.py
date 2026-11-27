"""Package U.S. parks, highways, Amtrak services, airports and degree-granting colleges."""
import argparse
from collections import defaultdict
import csv
from io import BytesIO, TextIOWrapper
import json
from pathlib import Path
import re
from zipfile import ZipFile

import shapefile
from shapely import line_merge, simplify
from shapely.geometry import MultiLineString, Point, shape
from shapely.strtree import STRtree

from prepare_us_admin import STATES, dump, packed_polygon, projected, read_features
from us_geometry import project


PARKS = {
    "ACAD":"阿卡迪亚","ARCH":"拱门","BADL":"恶地","BIBE":"大弯","BISC":"比斯坎",
    "BLCA":"甘尼森黑峡谷","BRCA":"布莱斯峡谷","CANY":"峡谷地","CARE":"圆顶礁","CAVE":"卡尔斯巴德洞窟",
    "CHIS":"海峡群岛","CONG":"康加里","CRLA":"火山口湖","CUVA":"凯霍加谷","DENA":"迪纳利",
    "DEVA":"死亡谷","DRTO":"干龟岛","EVER":"大沼泽地","GAAR":"北极之门","GLAC":"冰川",
    "GLBA":"冰川湾","GRBA":"大盆地","GRCA":"大峡谷","GRSA":"大沙丘","GRSM":"大烟山",
    "GRTE":"大提顿","GUMO":"瓜达卢佩山","HALE":"哈莱阿卡拉","HAVO":"夏威夷火山","HOSP":"温泉",
    "INDU":"印第安纳沙丘","ISRO":"皇家岛","JEFF":"门户拱门","JOTR":"约书亚树","KATM":"卡特迈",
    "KEFJ":"基奈峡湾","KICA":"国王峡谷","KOVA":"科伯克谷","LACL":"克拉克湖","LAVO":"拉森火山",
    "MACA":"猛犸洞","MEVE":"梅萨维德","MORA":"雷尼尔山","NERI":"新河峡谷","NOCA":"北喀斯喀特",
    "OLYM":"奥林匹克","PEFO":"石化森林","PINN":"尖峰","REDW":"红木","ROMO":"落基山",
    "SAGU":"萨瓜罗","SEQU":"巨杉","SHEN":"谢南多厄","THRO":"西奥多·罗斯福","VOYA":"航海家",
    "WHSA":"白沙","WICA":"风洞","WRST":"兰格尔－圣伊莱亚斯","YELL":"黄石","YOSE":"优胜美地","ZION":"锡安",
}
SCHOOLS = {
    "Harvard University":"哈佛大学","Yale University":"耶鲁大学","Princeton University":"普林斯顿大学",
    "Massachusetts Institute of Technology":"麻省理工学院","Stanford University":"斯坦福大学",
    "California Institute of Technology":"加州理工学院","University of Pennsylvania":"宾夕法尼亚大学",
    "Columbia University in the City of New York":"哥伦比亚大学","Cornell University":"康奈尔大学",
    "Brown University":"布朗大学","Dartmouth College":"达特茅斯学院","Duke University":"杜克大学",
    "Johns Hopkins University":"约翰斯·霍普金斯大学","University of Chicago":"芝加哥大学",
    "University of California-Berkeley":"加州大学伯克利分校","University of California-Los Angeles":"加州大学洛杉矶分校",
    "University of California-San Diego":"加州大学圣迭戈分校","University of Michigan-Ann Arbor":"密歇根大学安娜堡分校",
    "University of Washington-Seattle Campus":"华盛顿大学西雅图校区","Howard University":"霍华德大学",
    "University of Hawaii at Manoa":"夏威夷大学马诺阿分校","University of Alaska Fairbanks":"阿拉斯加大学费尔班克斯分校",
}
AIRPORTS = {
    "ATL":"亚特兰大哈茨菲尔德－杰克逊国际机场","LAX":"洛杉矶国际机场","ORD":"芝加哥奥黑尔国际机场",
    "JFK":"纽约约翰·肯尼迪国际机场","DFW":"达拉斯－沃思堡国际机场","LGA":"纽约拉瓜迪亚机场",
    "SFO":"旧金山国际机场","DEN":"丹佛国际机场","SEA":"西雅图－塔科马国际机场",
    "LAS":"拉斯维加斯哈里·里德国际机场","MIA":"迈阿密国际机场","BOS":"波士顿洛根国际机场",
    "HNL":"檀香山丹尼尔·井上国际机场","ANC":"安克雷奇泰德·史蒂文斯国际机场","IAD":"华盛顿杜勒斯国际机场",
    "DCA":"华盛顿里根国家机场","IAH":"休斯敦乔治·布什洲际机场","EWR":"纽瓦克自由国际机场",
}
RAIL_NAMES = {
    "Acela":"阿西乐快线","California Zephyr":"加州和风号","Coast Starlight":"海岸星光号","Empire Builder":"帝国建设者号",
    "Northeast Regional":"东北区域列车","Southwest Chief":"西南酋长号","Texas Eagle":"得州鹰号",
    "City of New Orleans":"新奥尔良城号","Lake Shore Limited":"湖岸特快","Crescent":"新月号",
    "Pacific Surfliner":"太平洋冲浪者号","Capitol Corridor":"首府走廊","Empire Service":"帝国服务号",
}


def lines(geojson):
    if geojson["type"] == "LineString":
        yield geojson["coordinates"]
    elif geojson["type"] == "MultiLineString":
        yield from geojson["coordinates"]


def pack_lines(segments, tolerance):
    geometry = simplify(line_merge(MultiLineString(segments)),tolerance,preserve_topology=False)
    if geometry.is_empty:
        return [], "", geometry
    parts = [geometry] if geometry.geom_type == "LineString" else list(geometry.geoms)
    d = "".join("M" + " ".join(f"{x:.3f},{y:.3f}" for x,y in part.coords) for part in parts)
    return list(geometry.bounds), d, geometry


def park_records(cache):
    data = read_features(cache / "parks.json")
    extra = cache / "parks-neri.json"
    if extra.exists():
        data += read_features(extra)
    results = {}
    for feature in data:
        props = feature["properties"]
        code = props["UNIT_CODE"]
        if code not in PARKS:
            continue
        area = projected(feature["geometry"]).simplify(.05,preserve_topology=True)
        results[code] = dict(id=code,n=PARKS[code]+"国家公园",en=props["UNIT_NAME"],
                             states=props.get("STATE"),**packed_polygon(area))
    return list(results.values())


def roads(cache):
    parts = defaultdict(list)
    if (cache / "highways" / "complete").exists():
        attribution = "bts"
        for file in sorted((cache / "highways").glob("*.json")):
            for record in read_features(file):
                values = record["properties"]
                if str(values["STFIPS"]).zfill(2) not in STATES or not re.fullmatch(r"\d+[A-Z]?",str(values["SIGNN1"])):
                    continue
                key = (values["SIGNT1"],str(values["SIGNN1"]))
                parts[key].extend([list(map(lambda p:project(*p[:2]),line)) for line in lines(record["geometry"]) if len(line)>1])
    else:
        attribution = "natural-earth"
        with ZipFile(cache / "ne-roads.zip") as archive:
            streams = {ext:BytesIO(archive.read(f"ne_10m_roads.{ext}")) for ext in ("shp","shx","dbf")}
            reader = shapefile.Reader(**streams,encoding="utf-8")
            for entry in reader.iterShapeRecords():
                attrs = entry.record.as_dict()
                prefix, road = attrs["prefix"],attrs["name"]
                if attrs["sov_a3"] != "USA" or prefix not in {"I","US"} or not re.fullmatch(r"\d+",road):
                    continue
                parts[(prefix,road)].extend([[project(*p[:2]) for p in line]
                                            for line in lines(entry.shape.__geo_interface__) if len(line)>1])
    result = []
    for (prefix,number),segments in sorted(parts.items(),key=lambda item:(item[0][0]=="I",int(re.match(r"\d+",item[0][1])[0]))):
        if not segments:
            continue
        b,d,_ = pack_lines(segments,.055)
        if not d:
            continue
        ref = ("I-" if prefix=="I" else "US-")+number
        result.append([ref,ref+(" 州际公路" if prefix=="I" else " 美国国道"),"expressway" if prefix=="I" else "national",b,d])
    return {"roads":result,"source":attribution}


def railways(cache):
    stations = {}
    for item in read_features(cache / "scheduled-stops.json"):
        attrs = item["properties"]
        if attrs["StnType"] != "TRAIN" or not item.get("geometry"):
            continue
        lon,lat = item["geometry"]["coordinates"][:2]
        if not (-125 <= lon <= -65 and 24 <= lat <= 50) or attrs["State"] in {"BC","ON","QC"}:
            continue
        code = attrs["Code"]
        x,y = project(lon,lat)
        stations[code] = dict(id=code,n=attrs["StationName"],x=x,y=y,hub=code in {"NYP","WAS","CHI","LAX","BOS","PHL","SEA"},
                              passenger=True,source="https://www.amtrak.com/train-stations")
    results = []
    used = set()
    for entry in read_features(cache / "scheduled-rail.json"):
        attrs = entry["properties"]
        name = attrs.get("name")
        segments = [[project(*p[:2]) for p in line] for line in lines(entry["geometry"]) if len(line)>1]
        if not name or not segments:
            continue
        b,d,path = pack_lines(segments,.025)
        if not d:
            continue
        stops = sorted(((path.project(Point(s["x"],s["y"])),code) for code,s in stations.items()
                        if path.distance(Point(s["x"],s["y"])) <= .23))
        ids = [code for _,code in stops]
        used.update(ids)
        url = (attrs.get("ROUTE_URL") or "https://www.amtrak.com/train-routes").replace("http://","https://")
        if not url.startswith("https://www.amtrak.com/"):
            url = "https://www.amtrak.com/train-routes"
        results.append(dict(id=attrs["OBJECTID"],n=RAIL_NAMES.get(name,name),en=name,kind="passenger" if name=="Acela" else "mixed",
                            b=b,d=d,stops=ids,source=url))
    return {"lines":results,"stations":[s for code,s in stations.items() if code in used]}


def colleges(cache, counties):
    boundary_rows = [row for file in cache.glob("counties-*.json") for row in read_features(file)
                     if row["properties"]["FIPS"] in counties]
    spatial = STRtree([shape(row["geometry"]) for row in boundary_rows])
    result = []
    with ZipFile(cache / "universities.zip") as archive, archive.open("HD2024.csv") as raw:
        for row in csv.DictReader(TextIOWrapper(raw,encoding="utf-8-sig",errors="replace")):
            if row["ICLEVEL"] != "1" or row["DEGGRANT"] != "1" or row.get("CYACTIVE") not in {"1","A"}:
                continue
            if str(row["FIPS"]).zfill(2) not in STATES:
                continue
            county = row["COUNTYCD"].strip().zfill(5)
            if county not in counties:
                try:
                    point = Point(float(row["LONGITUD"]),float(row["LATITUDE"]))
                except ValueError:
                    continue
                hits = spatial.query(point,predicate="covered_by")
                if not len(hits):
                    continue
                county = boundary_rows[hits[0]]["properties"]["FIPS"]
            english = row["INSTNM"]
            tags = []
            if row["CONTROL"]=="1": tags.append("public")
            if row["CONTROL"]=="2": tags.append("nonprofit")
            if row["HBCU"]=="1": tags.append("hbcu")
            if row["TRIBAL"]=="1": tags.append("tribal")
            if row["LANDGRNT"]=="1": tags.append("landgrant")
            link = row["WEBADDR"].strip()
            if link and "://" not in link: link = "https://"+link
            if not re.match(r"https?://",link): link = "https://nces.ed.gov/collegenavigator/?id="+row["UNITID"]
            abbr = "".join(word[0] for word in re.findall(r"[A-Za-z]+",english) if word.lower() not in {"of","the","at","and"})[:3]
            result.append(dict(id=row["UNITID"],name=SCHOOLS.get(english,english),en=english,abbr=abbr,tags=tags,
                               placements={county:[["院校",link],[row["CITY"],""]]}))
    return {"schools":result}


def airports(source):
    locations = json.loads((source/"airports.json").read_text(encoding="utf8"))
    traffic = json.loads((source/"airportmiles-routes.json").read_text(encoding="utf8"))
    keys = {row["iata"]:row for row in locations["airports"]}
    domestic = {k for k,v in keys.items() if v["country"]=="US"}
    names = lambda code:AIRPORTS.get(code,keys[code]["name"])
    ranks = {"large":"hub","medium":"major","small":"regional"}
    sources = "https://airportmiles.com/sources"
    routes = defaultdict(set)
    foreign = {}
    for row in traffic["routes"]:
        a,b = row["from"],row["to"]
        if row.get("passengersSource") != "t100" or not row.get("passengers"):
            continue
        for origin,target in ((a,b),(b,a)):
            if origin in domestic and target in keys:
                routes[origin].add(target)
                if target not in domestic: foreign[target] = names(target)
    return {"date":traffic["generated"],"routes":{k:sorted(v) for k,v in routes.items()},
            "airports":[[code,names(code),ranks.get(keys[code]["size"],""),keys[code]["longitude"],keys[code]["latitude"],None,keys[code]["name"]]
                        for code in sorted(domestic)],"foreign":foreign,"sources":{k:sources for k in routes}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache",type=Path)
    parser.add_argument("aviation_cache",type=Path)
    parser.add_argument("--output",type=Path,default=Path("dist/data/us"))
    args=parser.parse_args()
    admin = json.loads((args.output/"admin-boundaries.json").read_text(encoding="utf-8"))
    counties = {row["id"] for row in admin["city"] or admin["county"]}
    data={"parks":park_records(args.cache),"roads":roads(args.cache),"railways":railways(args.cache),
          "universities":colleges(args.cache,counties),"airports":airports(args.aviation_cache)}
    assert data["parks"] and data["roads"]["roads"] and data["railways"]["lines"] and data["universities"]["schools"] and data["airports"]["routes"]
    for name,source in data.items():
        dump(args.output / (name+".json"),source)
        print(name,len(source) if isinstance(source,list) else {key:len(value) for key,value in source.items() if isinstance(value,(list,dict))})


if __name__=="__main__":
    main()
