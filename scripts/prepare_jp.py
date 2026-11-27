"""Package the Japanese boundaries, statistics, university, railway, road and airport layers."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
from zipfile import ZipFile

from openpyxl import load_workbook
from shapely import make_valid
from shapely.geometry import Point, shape
from shapely.ops import linemerge, transform, unary_union
from shapely.strtree import STRtree

from jp_names import chinese
from prepare_jp_terrain import project
from prepare_us_admin import dump, packed_polygon

RAIL_SOURCE = "https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N02-2025.html"
SCHOOL_SOURCE = "https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-P29-v2_0.html"
AIR_SOURCE = "https://airportmiles.com/sources"
INTERNATIONAL_SOURCE = "https://www.mlit.go.jp/koku/content/002028814.xlsx"
INTERNATIONAL_CITIES = dict(item.split(":") for item in (
    "アトランタ:亚特兰大 アブダビ:阿布扎比 アムステルダム:阿姆斯特丹 イスタンブール:伊斯坦布尔 ウィーン:维也纳"
    " ウランバートル:乌兰巴托 オークランド:奥克兰 カイロ:开罗 カトマンズ:加德满都 カルガリー:卡尔加里"
    " クアラルンプール:吉隆坡 クラーク:克拉克 グアム:关岛 ケアンズ:凯恩斯 コペンハーゲン:哥本哈根"
    " コロンボ:科伦坡 コロール:科罗尔 サイパン:塞班岛 サンディエゴ:圣迭戈 サンフランシスコ:旧金山"
    " シアトル:西雅图 シカゴ:芝加哥 シドニー:悉尼 シンガポール:新加坡 ジャカルタ:雅加达"
    " ストックホルム:斯德哥尔摩 セブ:宿务 ソウル:首尔 タシケント:塔什干 ダッカ:达卡"
    " ダナン:岘港 ダラス:达拉斯 チェンマイ:清迈 チューリッヒ:苏黎世 テルアビブ:特拉维夫"
    " デトロイト:底特律 デリー:德里 デンバー:丹佛 デンパサール:登巴萨 トロント:多伦多"
    " ドバイ:迪拜 ドーハ:多哈 ナンディ:楠迪 ニューアーク:纽瓦克 ニューヨーク:纽约"
    " ハノイ:河内 ハルビン:哈尔滨 バンクーバー:温哥华 バンコク:曼谷 バンダルスリブガワン:斯里巴加湾市"
    " パペーテ:帕皮提 パリ:巴黎 パース:珀斯 ヒューストン:休斯敦 フランクフルト:法兰克福"
    " ブリスベン:布里斯班 ブリュッセル:布鲁塞尔 ヘルシンキ:赫尔辛基 ベンガルール:班加罗尔 ホノルル:檀香山"
    " ホーチミン:胡志明市 ボストン:波士顿 ポートモレスビー:莫尔兹比港 マカオ:澳门 マドリッド:马德里"
    " マニラ:马尼拉 ミネアポリス:明尼阿波利斯 ミュンヘン:慕尼黑 ミラノ:米兰 ムンバイ:孟买"
    " メキシコシティ:墨西哥城 メルボルン:墨尔本 モントリオール:蒙特利尔 ロサンゼルス:洛杉矶"
    " ロンドン:伦敦 ローマ:罗马 ワシントンD.C.:华盛顿特区 ワルシャワ:华沙"
    " 深セン:深圳 台北:台北 台中:台中 済州:济州 大邱:大邱 清州:清州".split()
))
AIRPORT_NAMES = dict(item.split(":") for item in (
    "AGJ:粟国 AKJ:旭川 AOJ:青森 ASJ:奄美 AXJ:天草 AXT:秋田 CTS:新千歳 FKS:福島 FSZ:静岡"
    " FUJ:福江 FUK:福岡 GAJ:山形 HAC:八丈島 HIJ:広島 HKD:函館 HNA:花巻 HND:東京国際"
    " HSG:佐賀 IBR:茨城 IKI:壱岐 ISG:新石垣 ITM:大阪国際 IWJ:石見 IWK:岩国錦帯橋 IZO:出雲"
    " KCZ:高知 KIJ:新潟 KIX:関西国際 KKJ:北九州 KKX:喜界 KMI:宮崎 KMJ:熊本 KMQ:小松"
    " KOJ:鹿児島 KTD:北大東 KUH:釧路 KUM:屋久島 MBE:紋別 MMB:女満別 MMD:南大東"
    " MMJ:松本 MMY:宮古 MSJ:三沢 MYE:三宅島 MYJ:松山 NGO:中部国際 NGS:長崎 NKM:名古屋"
    " NRT:成田国際 NTQ:能登 OBO:帯広 OGN:与那国 OIM:大島 OIR:奥尻 OIT:大分 OKA:那覇"
    " OKD:札幌丘珠 OKE:沖永良部 OKI:隠岐 OKJ:岡山 ONJ:大館能代 RIS:利尻 RNJ:与論 SDJ:仙台"
    " SDS:佐渡 SHB:中標津 SHI:下地島 SHM:南紀白浜 SYO:庄内 TAK:高松 TJH:但馬 TKN:徳之島"
    " TKS:徳島 TNE:種子島 TOY:富山 TRA:多良間 TSJ:対馬 TTJ:鳥取 UBJ:山口宇部 UEO:久米島"
    " UKB:神戸 WKJ:稚内 YGJ:米子".split()
))
AIRPORT_CHINESE = {
    "HND":"东京羽田国际机场", "ITM":"大阪伊丹国际机场", "FSZ":"富士山静冈机场", "NGO":"中部国际机场",
    "OKA":"那霸机场", "IBR":"茨城机场", "NKM":"名古屋小牧机场", "NRT":"东京成田国际机场", "KIX":"关西国际机场",
    "FUK":"福冈机场", "TOY":"富山机场", "CTS":"新千岁机场", "KIJ":"新潟机场", "MYJ":"松山机场"
}


def read(path):
    return json.loads(path.read_bytes())


def read_zip_features(path, suffix):
    with ZipFile(path) as archive:
        member = next(name for name in archive.namelist() if name.endswith(suffix))
        return json.loads(archive.read(member))["features"]


def workbook_rows(path):
    book = load_workbook(path,read_only=True,data_only=True)
    try:
        yield from book.active.values
    finally:
        book.close()


def regions_and_statistics(cache):
    people = {row[1][:5]:round(row[4]/10_000,4) for row in workbook_rows(cache/"population.xlsx")
              if re.match(r"^\d{5}_",str(row[1])) and isinstance(row[4],int)}
    gdp = {row[1]:round(row[15]/100,2) for row in workbook_rows(cache/"gdp.xlsx")
           if row[1] and isinstance(row[15],(int,float))}
    provinces, municipalities = [], []
    municipal_geometries = {}
    by_province = defaultdict(list)
    statistics = {}
    for row in read(cache/"muni.geojson")["features"]:
        names = row["properties"]
        code, original = names["code5"], names["name"]
        # Use the 2025 census roster to define the mapped municipality coverage.
        if code not in people:
            continue
        nation = code[:2]+"000"
        geography = make_valid(shape(row["geometry"]))
        packed = packed_polygon(transform(project,geography))
        kind = "特别区" if original.endswith("区") else {"市":"市","町":"町","村":"村"}.get(original[-1],"市区町村")
        municipalities.append(dict(id=code,n=chinese(original),original=original,type=kind,nation=nation,p=nation,**packed))
        municipal_geometries[code] = geography
        by_province[nation].append(geography)
        statistics[code] = [gdp.get(original),people[code]]
    for row in read(cache/"prefs.geojson")["features"]:
        code, original = (row["properties"][key] for key in ("code5","name"))
        geography = transform(project,unary_union(by_province[code]))
        packed = packed_polygon(geography)
        provinces.append(dict(id=code,n=chinese(original),original=original,type=chinese(original[-1]),nation=code,p=None,**packed))
        statistics[code] = [gdp[original],people[code]]
    assert len(provinces)==47 and len(municipalities)==1741
    return {"province":provinces,"city":[],"county":municipalities},statistics,municipal_geometries


def line_parts(geometry):
    if geometry.geom_type == "LineString":
        yield geometry
    elif hasattr(geometry,"geoms"):
        for component in geometry.geoms:
            yield from line_parts(component)


def packed_lines(geometries, tolerance):
    connected = unary_union(geometries)
    merged = linemerge(connected) if connected.geom_type == "MultiLineString" else connected
    reduced = merged.simplify(tolerance)
    path = "".join("M"+" ".join(f"{x:.3f},{y:.3f}" for x,y in line.coords) for line in line_parts(reduced))
    return [round(n,3) for n in reduced.bounds],path


def railways(cache):
    main = defaultdict(list)
    stops = defaultdict(list)
    stations = {}
    def key(row):
        info = row["properties"]
        return info["N02_002"],info["N02_004"],info["N02_003"]

    for row in read_zip_features(cache/"rail.zip","RailroadSection.geojson"):
        main[key(row)].append(transform(project,shape(row["geometry"])))
    for row in read_zip_features(cache/"rail.zip","Station.geojson"):
        info = row["properties"]
        original = info["N02_005"]
        ident = info["N02_005g"]
        if ident not in stations:
            geometry = transform(project,shape(row["geometry"]))
            point = geometry.interpolate(.5,normalized=True)
            stations[ident] = dict(id=ident,n=chinese(original)+"站",original=original+"駅",x=round(point.x,3),y=round(point.y,3),
                                   passenger=True,hub=False,source=RAIL_SOURCE)
        group = key(row)
        if group[0]=="1":
            stations[ident]["hub"] = True
        stops[group].append(ident)
    names = Counter(label for _,_,label in main)
    lines = []
    used = set()
    for i,((code,operator,label),geometry) in enumerate(sorted(main.items()),1):
        bounds,path = packed_lines(geometry,.037)
        ids = list(dict.fromkeys(stops.get((code,operator,label),[])))
        used.update(ids)
        original = f"{label}（{operator}）" if names[label]>1 else label
        name = f"{chinese(label)}（{chinese(operator)}）" if names[label]>1 else chinese(label)
        lines.append(dict(id=i,n=name,original=original,kind="passenger" if code=="1" else "mixed",b=bounds,d=path,stops=ids,source=RAIL_SOURCE))
    return {"lines":lines,"stations":[station for ident,station in stations.items() if ident in used]}


def schools(cache, admin, municipal_geometries):
    placements = defaultdict(list)
    regions = {row["id"]:row for row in admin["county"]}
    codes = list(municipal_geometries)
    tree = STRtree(list(municipal_geometries.values()))
    for row in read_zip_features(cache/"schools.zip",".geojson"):
        info = row["properties"]
        ident = info["P29_002"] or ""
        if not ident.startswith("F1"):
            continue
        muni = info["P29_001"]
        if muni not in regions:
            point = shape(row["geometry"])
            if not isinstance(point,Point):
                continue
            hits = tree.query(point,predicate="covered_by")
            if not len(hits):
                continue
            muni = codes[hits[0]]
        placements[ident].append((muni,info["P29_004"].strip()))
    result = []
    labels = {"1":"national","2":"public","3":"private"}
    for ident,campuses in placements.items():
        base = min((name for _,name in campuses),key=len)
        institution = {"id":ident,"name":chinese(base),"original":base,"tags":[labels[ident[4]]],"placements":{}}
        for muni,location in campuses:
            entries = institution["placements"].setdefault(muni,[["院校名录",SCHOOL_SOURCE]])
            region = regions[muni]
            name = [chinese(location),"",location] if location!=base else [region["n"],"",region["original"]]
            if name not in entries:
                entries.append(name)
        result.append(institution)
    return {"schools":result}


def roads(cache):
    highway_sections = defaultdict(list)
    for row in read_zip_features(cache/"expressways.zip","HighwaySection.geojson"):
        info = row["properties"]
        original = info["N06_007"]
        if original and info["N06_002"] <= 2020 < info["N06_003"]:
            highway_sections[original].append(transform(project,shape(row["geometry"])))
    result = []
    for index,(name,geometry) in enumerate(sorted(highway_sections.items()),1):
        bounds,path = packed_lines(geometry,.065)
        result.append([f"JP-E-{index}",chinese(name),"expressway",bounds,path,name])
    # Numbered national routes are taken from complete OSM relation responses.
    relation_ids = read(cache/"road-relations.json")
    for ref in sorted(relation_ids,key=int):
        response = cache/f"route-{ref}.json"
        if not response.exists():
            continue
        elements = read(response)["elements"]
        nodes = {row["id"]:project(row["lon"],row["lat"]) for row in elements if row["type"]=="node"}
        relation = next(row for row in elements if str(row["id"])==relation_ids[ref] and row["type"]=="relation")
        members = {row["ref"] for row in relation["members"] if row["type"]=="way"}
        geometry = [shape({"type":"LineString","coordinates":[nodes[node] for node in row["nodes"]]})
                    for row in elements if row["type"]=="way" and row["id"] in members
                    and len(row["nodes"])>1 and all(node in nodes for node in row["nodes"])]
        if geometry:
            bounds,path = packed_lines(geometry,.059)
            result.append(["R"+ref,f"{ref} 号国道","national",bounds,path,f"国道{ref}号"])
    assert any(row[2]=="national" for row in result)
    return {"roads":result,"source":"mlit-osm"}


def airports(cache,source):
    catalog = {a["iata"]:a for a in read(source/"airports.json")["airports"]}
    local = {code for code,row in catalog.items() if row["country"]=="JP"}
    assert local <= AIRPORT_NAMES.keys(), local-AIRPORT_NAMES.keys()
    flight_data = read(source/"airportmiles-routes.json")
    locations, routes = [], defaultdict(set)
    for route in flight_data["routes"]:
        a,b = route["from"],route["to"]
        if a in local and b in local and route["passengersSource"]=="mlitRoutes" and route.get("passengers"):
            routes[a].add(b)
            routes[b].add(a)

    airport_codes = {name:code for code,name in AIRPORT_NAMES.items()}
    airport_codes.update({"羽田":"HND","成田":"NRT","関西":"KIX","中部":"NGO","石垣":"ISG"})
    international = [(airport_codes[row[0]],row[3]) for row in workbook_rows(cache/"international.xlsx")
                     if isinstance(row[6],(float,int)) and not isinstance(row[6],bool) and row[6]>0]
    cities = {city:index for index,city in enumerate(sorted({city for _,city in international}),1)}
    overseas, originals = {}, {}
    for airport,city in international:
        code = f"city-{cities[city]:03}"
        routes[airport].add(code)
        overseas[code] = INTERNATIONAL_CITIES.get(city) or chinese(city)
        originals[code] = city

    ranks = {"large":"hub","medium":"major","small":"regional"}
    for code in sorted(local):
        row = catalog[code]
        original = AIRPORT_NAMES[code]+"空港"
        label = AIRPORT_CHINESE.get(code,chinese(AIRPORT_NAMES[code])+"机场")
        locations.append([code,label,ranks.get(row["size"],"unknown"),row["longitude"],row["latitude"],None,original])
    international_origins = {airport for airport,_ in international}
    return {"date":"2026-10-25","routes":{key:sorted(value) for key,value in routes.items()},
            "airports":locations,"foreign":overseas,"foreignEn":originals,
            "sources":{code:INTERNATIONAL_SOURCE if code in international_origins else AIR_SOURCE for code in routes}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache",type=Path)
    parser.add_argument("aviation_cache",type=Path)
    parser.add_argument("--output",type=Path,default=Path("dist/data/jp"))
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    admin, stats, geo = regions_and_statistics(args.cache)
    products = {"admin-boundaries":admin,"statistics":stats,"railways":railways(args.cache),
                "universities":schools(args.cache,admin,geo),"roads":roads(args.cache),
                "airports":airports(args.cache,args.aviation_cache)}
    for name,data in products.items():
        dump(args.output/(name+".json"),data)
        print(name,{key:len(value) for key,value in data.items() if isinstance(value,(dict,list))} if name!="statistics" else len(data))


if __name__=="__main__":
    main()
