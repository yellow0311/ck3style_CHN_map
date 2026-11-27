"""Generate the French atlas from IGN, Insee, Eurostat, SNCF and transport data."""
import argparse
from collections import defaultdict
import csv
import gzip
from io import BytesIO, TextIOWrapper
import json
from pathlib import Path
import re
from zipfile import ZipFile

from openpyxl import load_workbook
from pyproj import Transformer
import shapefile
from shapely import make_valid
from shapely.geometry import Point, shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree

from fr_names import FrenchNames, key
from prepare_fr_terrain import project
from prepare_jp import packed_lines
from prepare_us_admin import dump, packed_polygon


REGION_CODES = {"01","02","03","04","06","11","24","27","28","32","44","52","53","75","76","84","93","94"}
OVERSEAS_CODES = {"01","02","03","04","06"}
AIRPORT_ISO = {"FR","GP","MQ","GF","RE","YT"}
RAIL_SOURCE = "https://ressources.data.sncf.com/explore/dataset/formes-des-lignes-du-rfn/"
SCHOOL_SOURCE = "https://data.enseignementsup-recherche.gouv.fr/explore/dataset/fr-esr-principaux-etablissements-enseignement-superieur/"
AIR_SOURCE = "https://airportmiles.com/sources"
AIRPORT_LOCAL = {
    "CDG":("巴黎戴高乐机场","Aéroport Paris-Charles de Gaulle"),
    "AJA":("阿雅克肖拿破仑·波拿巴机场","Aéroport Ajaccio-Napoléon-Bonaparte"),
    "BIQ":("比亚里茨巴斯克地区机场","Aéroport de Biarritz-Pays basque"),
    "CMF":("尚贝里萨瓦机场","Aéroport Chambéry-Savoie-Mont-Blanc"),
    "ORY":("巴黎奥利机场","Aéroport Paris-Orly"),
    "BVA":("巴黎博韦机场","Aéroport Paris-Beauvais"),
    "LYS":("里昂圣埃克絮佩里机场","Aéroport Lyon-Saint Exupéry"),
    "MRS":("马赛普罗旺斯机场","Aéroport Marseille-Provence"),
    "NCE":("尼斯蓝色海岸机场","Aéroport Nice-Côte d’Azur"),
    "TLS":("图卢兹布拉尼亚克机场","Aéroport Toulouse-Blagnac"),
    "NTE":("南特大西洋机场","Aéroport Nantes-Atlantique"),
    "BOD":("波尔多梅里尼亚克机场","Aéroport Bordeaux-Mérignac"),
    "BSL":("巴塞尔-米卢斯-弗赖堡欧洲机场","Aéroport de Bâle-Mulhouse-Fribourg"),
    "SXB":("斯特拉斯堡机场","Aéroport de Strasbourg"),
    "MLH":("巴塞尔-米卢斯-弗赖堡欧洲机场","Aéroport de Bâle-Mulhouse-Fribourg"),
    "CAY":("卡宴费利克斯·埃布埃机场","Aéroport de Cayenne-Félix Éboué"),
    "PTP":("瓜德罗普玛丽斯·孔代机场","Aéroport Guadeloupe Maryse Condé"),
    "FDF":("马提尼克艾梅·塞泽尔国际机场","Aéroport international Martinique Aimé Césaire"),
    "RUN":("留尼汪罗兰·加洛斯机场","Aéroport de La Réunion-Roland-Garros"),
    "DZA":("藻德济帕曼济国际机场","Aéroport de Dzaoudzi-Pamandzi")
}
MAIN_STATIONS = {
    "Paris Gare de Lyon":"巴黎里昂站","Paris-Lyon":"巴黎里昂站","Paris Montparnasse":"巴黎蒙帕纳斯站",
    "Paris-Nord":"巴黎北站","Paris-Est":"巴黎东站","Paris-Austerlitz":"巴黎奥斯特利茨站",
    "Paris-Saint-Lazare":"巴黎圣拉扎尔站","Lyon Part Dieu":"里昂帕尔迪厄站",
    "Marseille-Saint-Charles":"马赛圣夏尔站","Bordeaux Saint-Jean":"波尔多圣让站",
    "Lille Europe":"里尔欧洲站","Lille Flandres":"里尔弗兰德站"
}
LGV_NAMES = {
    "005000":("东部欧洲高速铁路","LGV Est européenne"),
    "014000":("莱茵-罗讷高速铁路","LGV Rhin-Rhône"),
    "226000":("北方高速铁路","LGV Nord"),
    "431000":("大西洋高速铁路","LGV Atlantique"),
    "752000":("东南方向高速铁路","Ligne à grande vitesse vers le sud-est")
}


def read(path):
    return json.loads(path.read_bytes())


def compressed_features(path):
    with gzip.open(path,"rt",encoding="utf8") as source:
        return json.load(source)["features"]


def census_tables(cache):
    result = {}
    with ZipFile(cache/"population.zip") as archive:
        for tab in ("regions","departements","arrondissements","communes"):
            with archive.open(f"donnees_{tab}.csv") as table:
                result[tab] = list(csv.DictReader(TextIOWrapper(table,encoding="utf-8-sig"),delimiter=";"))
    return result


def regional_gdp(cache):
    book = load_workbook(cache/"gdp.xlsx",read_only=True,data_only=True)
    rows = book["PIB en valeur"].values
    labels = {}
    for row in rows:
        if row[0] and isinstance(row[-1],(int,float)):
            labels[key(row[0].replace("(y compris Saint-Martin)",""))] = (round(row[-1]/100,3),2024)
        if row[0] and row[0].strip()=="Mayotte":
            labels[key("Mayotte")] = (round(row[-2]/100,3),2023)
    book.close()
    return labels


def departmental_gdp(cache):
    dataset = read(cache/"nuts3.json")
    geo = dataset["dimension"]["geo"]["category"]
    values = dataset["value"]
    result = {}
    for code,label in geo["label"].items():
        if code.startswith("FR") and len(code)==5:
            value = values.get(str(geo["index"][code]))
            if value is not None:
                result[key(label)] = round(value/100,3)
    return result


def pack_area(geometry):
    return packed_polygon(make_valid(transform(project,geometry)))


def administrative(cache,names):
    tables = census_tables(cache)
    gdp_regions,gdp_depts = regional_gdp(cache),departmental_gdp(cache)
    populations = {row["REG"]:int(row["PMUN"]) for row in tables["regions"]}
    dep_pop = {row["DEP"]:int(row["PMUN"]) for row in tables["departements"]}
    populations["06"] = dep_pop["976"] = 323153
    regions,departments,arrondissements = [],[],[]
    statistics,geometries = {},{}
    for row in compressed_features(cache/"regions.gjson.gz"):
        code,name = row["properties"]["code"],row["properties"]["nom"]
        if code not in REGION_CODES:
            continue
        regions.append(dict(id=code,n=names.translate(name),original=name,nation=code,p=None,type="海外大区" if code in OVERSEAS_CODES else "大区",
                            **pack_area(shape(row["geometry"]))))
        gdp,year = gdp_regions[key(name)]
        statistics[code] = [gdp,round(populations[code]/10000,4),year,2026 if code=="06" else 2023]
    for row in compressed_features(cache/"depts.gjson.gz"):
        attrs = row["properties"]
        code,name,region = attrs["code"],attrs["nom"],attrs.get("region")
        if region not in REGION_CODES:
            continue
        gid = "D"+code
        geom = shape(row["geometry"])
        label = names.translate(name)+("省" if region not in OVERSEAS_CODES else "")
        departments.append(dict(id=gid,code=code,n=label,original=name,nation=region,p=region,type="海外省" if region in OVERSEAS_CODES else "省",**pack_area(geom)))
        geometries[gid] = geom
        statistics[gid] = [gdp_depts.get(key(name)),round(dep_pop[code]/10000,4),2023,2026 if code=="976" else 2023]

    commune_to_arr = {row["COM"]:row["DEP"]+row["CODARR"] for row in tables["communes"] if row["CODARR"]}
    members = defaultdict(list)
    for row in compressed_features(cache/"communes.gjson.gz"):
        code = row["properties"]["code"]
        target = commune_to_arr.get(code)
        if target:
            members[target].append(make_valid(shape(row["geometry"])))
    for row in tables["arrondissements"]:
        arr,dep,name = row["ARR"],row["DEP"],row["Arrondissement"]
        points = members[arr]
        if not points:
            continue
        geom = unary_union(points)
        gid = "AR"+arr
        province = row["REG"]
        arrondissements.append(dict(id=gid,code=arr,n=names.translate(name),original=name,nation=province,p="D"+dep,type="行政专区",**pack_area(geom)))
        geometries[gid] = geom
        statistics[gid] = [None,round(int(row["PMUN"])/10000,4),None,2023]
    assert len(regions)==18 and len(departments)==101 and len(arrondissements)>328
    return {"province":regions,"city":departments,"county":arrondissements},statistics,geometries


def universities(cache,admin,geometries,names):
    arr = [r["id"] for r in admin["county"]]
    deps = [r["id"] for r in admin["city"]]
    units = {r["id"]:r for r in admin["county"]+admin["city"]}
    arr_index = STRtree([geometries[k] for k in arr])
    dep_index = STRtree([geometries[k] for k in deps])
    schools = []
    for row in read(cache/"schools.json"):
        coord = row.get("coordonnees")
        label = row.get("uo_lib")
        if not coord or not label:
            continue
        point = Point(coord["lon"],coord["lat"])
        cells = arr_index.query(point,predicate="covered_by")
        if len(cells):
            id = arr[cells[0]]
        else:
            cells = dep_index.query(point,predicate="covered_by")
            if not len(cells):
                continue
            id = deps[cells[0]]
        sector = row.get("secteur_d_etablissement") or ""
        tags = ["public" if sector=="public" else "private"] if sector in ("public","privé","prive") else []
        kind = " ".join(str(row.get(field) or "") for field in ("types_d_etablissement","typologie_d_universites_et_assimiles","uo_lib"))
        if re.search(r"ingénieur|polytech|centrale|insa\b|imt\b",kind,re.I):
            tags.append("engineering")
        link = row.get("url") or SCHOOL_SOURCE
        if not re.match(r"^https?://",link):
            link = SCHOOL_SOURCE
        campus = row.get("com_nom") or units[id]["original"]
        campus_rows = [["院校",link],[names.translate(campus),"",campus]]
        schools.append(dict(id=row["etablissement_id_paysage"],name=names.university(label),original=label,
                            tags=tags,placements={id:campus_rows}))
    return {"schools":schools}


def railways(cache,names):
    station_labels = {key(label):translation for label,translation in MAIN_STATIONS.items()}
    network = defaultdict(list)
    for row in read(cache/"rail-lines.json"):
        if row["libelle"]=="Exploitée" and row.get("geo_shape"):
            network[row["code_ligne"]].append(transform(project,shape(row["geo_shape"]["geometry"])))
    high_speed = {row["code_ligne"] for row in read(cache/"rail-lgv.json") if row["catlig"]=="Ligne à grande vitesse"}
    by_line = defaultdict(list)
    stations = {}
    for row in read(cache/"stations.json"):
        code,coordinate = row["code_ligne"],row.get("geo_point_2d")
        if code not in network or not coordinate or (row["voyageurs"]!="O" and row["fret"]!="O"):
            continue
        id = row["code_uic"]
        name = row["libelle"].strip()
        if not id or not name:
            continue
        if id not in stations:
            x,y = project(coordinate["lon"],coordinate["lat"])
            known = station_labels.get(key(name))
            label = known or names.translate(name)+"站"
            stations[id] = dict(id=id,n=label,original=name,x=round(x,3),y=round(y,3),
                               passenger=row["voyageurs"]=="O",hub=bool(known),source=RAIL_SOURCE)
        if code in high_speed:
            stations[id]["hub"] = True
        by_line[code].append((row.get("pk") or "",id))
    lines = []
    for code,segments in sorted(network.items()):
        bounds,path = packed_lines(segments,.043)
        points = list(dict.fromkeys(i for _,i in sorted(by_line[code])))
        use_lgv = code in high_speed
        if use_lgv and code in LGV_NAMES:
            n,original = LGV_NAMES[code]
        elif len(points)>1:
            start,end = stations[points[0]],stations[points[-1]]
            n,original = start["n"].removesuffix("站")+"至"+end["n"].removesuffix("站")+"线",start["original"]+" – "+end["original"]
        elif points:
            n,original = stations[points[0]]["n"]+"联络线",stations[points[0]]["original"]+" · "+code
        else:
            n,original = code+" 号铁路","Ligne "+code
        lines.append(dict(id=code,n=n,original=original,kind="passenger" if use_lgv else "mixed",
                          b=bounds,d=path,stops=points,source=RAIL_SOURCE))
    return {"lines":lines,"stations":list(stations.values())}


def roads(cache):
    lambert = Transformer.from_crs(2154,4326,always_xy=True)
    def projected(x,y,z=None):
        return project(*lambert.transform(x,y))
    groups = defaultdict(list)
    with ZipFile(cache/"roads.zip") as archive:
        shp = next(n for n in archive.namelist() if n.endswith(".shp"))
        reader = shapefile.Reader(shp=BytesIO(archive.read(shp)),dbf=BytesIO(archive.read(shp[:-4]+".dbf")),encoding="latin1")
        for row in reader.iterShapeRecords():
            ref = re.fullmatch(r"(973|976)?([AN])0*(\d{1,4})([A-Z]?)",row.record["route"])
            if ref is None or not row.shape.points:
                continue
            territory,kind,number,suffix = ref.groups()
            id = (territory+"-" if territory else "")+kind+str(int(number))+suffix
            groups[id].append(transform(projected,shape(row.shape.__geo_interface__)))
    result = []
    for id,segments in sorted(groups.items()):
        b,d = packed_lines(segments,.072)
        ref = id.split("-")[-1]
        express = ref.startswith("A")
        zh = ref+(" 高速公路" if express else " 国道")
        original = ("Autoroute " if express else "Route nationale ")+ref
        if id.startswith("973-"):
            zh = "法属圭亚那 "+zh
            original = "Guyane · "+original
        if id.startswith("976-"):
            zh = "马约特 "+zh
            original = "Mayotte · "+original
        result.append([id,zh,"expressway" if express else "national",b,d,original])
    return {"roads":result,"source":"rrn"}


def airport_names(code,label,names):
    if code in AIRPORT_LOCAL:
        return AIRPORT_LOCAL[code]
    base = re.sub(r"\s*(?:International\s+)?(?:Airport|Airfield|Aerodrome).*$","",label,flags=re.I).strip()
    return names.translate(base)+"机场","Aéroport de "+base


def airports(source,atlas,names):
    catalog = {row["iata"]:row for row in read(source/"airports.json")["airports"]}
    local = {id for id,row in catalog.items() if row["country"] in AIRPORT_ISO}
    route_data = read(source/"airportmiles-routes.json")
    connections = defaultdict(set)
    for row in route_data["routes"]:
        a,b = row["from"],row["to"]
        if a in catalog and b in catalog and row.get("passengers"):
            if a in local:
                connections[a].add(b)
            if b in local:
                connections[b].add(a)
    names_by_code = {}
    for country in ("us","uk","jp",""):
        data = read(atlas/country/"airports.json")
        labels = {**data["foreign"],**{row[0]:row[1] for row in data["airports"]}}
        names_by_code.update({code:label for code,label in labels.items() if re.search(r"[\u3400-\u9fff]",label) and not re.search(r"[A-Za-z]",label)})
    external = sorted(set().union(*connections.values()) - local)
    classes = {"large":"hub","medium":"major","small":"regional"}
    result = []
    for code in sorted(local):
        row = catalog[code]
        zh,original = airport_names(code,row["name"],names)
        result.append([code,zh,classes.get(row["size"],"unknown"),row["longitude"],row["latitude"],None,original])
    # The published route counts use actual passenger traffic, with statistical periods varying by source.
    return dict(date=route_data["generated"],airports=result,
                routes={code:sorted(other) for code,other in connections.items()},
                foreign={c:names_by_code.get(c) or airport_names(c,catalog[c]["name"],names)[0] for c in external},
                foreignEn={c:catalog[c]["name"] for c in external},sources={c:AIR_SOURCE for c in connections})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache",type=Path)
    parser.add_argument("aviation_cache",type=Path)
    parser.add_argument("--output",type=Path,default=Path("dist/data/fr"))
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    names = FrenchNames(args.cache/"names.zip")
    admin,metrics,geometry = administrative(args.cache,names)
    layers = {"admin-boundaries":admin,"statistics":metrics,"universities":universities(args.cache,admin,geometry,names),
              "railways":railways(args.cache,names),"roads":roads(args.cache),"airports":airports(args.aviation_cache,args.output.parent,names)}
    for file,data in layers.items():
        dump(args.output/(file+".json"),data)
        print(file,{key:len(value) for key,value in data.items() if isinstance(value,(dict,list))} if file!="statistics" else len(data))


if __name__=="__main__":
    main()
