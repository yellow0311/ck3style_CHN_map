"""Join UK university and OfS registers to campus points and local authorities."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from openpyxl import load_workbook
from shapely import make_valid
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

RUSSELL = {
    "University of Birmingham","University of Bristol","University of Cambridge","Cardiff University","Durham University",
    "University of Edinburgh","University of Exeter","University of Glasgow","Imperial College London","King's College London",
    "University of Leeds","University of Liverpool","London School of Economics and Political Science","University of Manchester",
    "Newcastle University","University of Nottingham","University of Oxford","Queen Mary University of London",
    "Queen's University Belfast","University of Sheffield","University of Southampton","University College London",
    "University of Warwick","University of York",
}
POSTCODE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s+\d[A-Z]{2}\b",re.I)
REGISTER = "https://www.officeforstudents.org.uk/for-providers/registering-with-the-ofs/guide-to-the-ofs-register/"
NAME_ALIASES = {
    "londonschoolofeconomics":"londonschoolofeconomicsandpoliticalscience",
    "bruneluniversitylondon":"bruneluniversityoflondon",
    "bruneluniversity":"bruneluniversityoflondon",
}
VERIFIED_CAMPUSES = {
    "londonschoolofeconomicsandpoliticalscience":[
        ("E09000033","Houghton Street","https://www.lse.ac.uk/lse-information/contact-us"),
    ],
    "instituteofcancerresearch":[
        ("E09000020","Chelsea","https://www.icr.ac.uk/contact-us"),
        ("E09000029","Sutton","https://www.icr.ac.uk/contact-us"),
    ],
}


def normalized(value):
    value = re.sub(r"^the\s+|\s+(?:limited|ltd)\.?$", "", value.casefold().strip()).replace("&","and")
    key = "".join(c for c in unicodedata.normalize("NFKD",value) if c.isalnum())
    return NAME_ALIASES.get(key,key)


def json_read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def wiki_providers(path):
    doc = BeautifulSoup(path.read_bytes(),"lxml")
    result = {}
    for table in doc.select("table.wikitable"):
        headers = [h.get_text(" ",strip=True) for h in table.select("tr:first-child th")]
        if "Arms" not in headers or "University" not in headers:
            continue
        for row in table.select("tr")[1:]:
            cells = row.find_all(["th","td"],recursive=False)
            if len(cells) < 3:
                continue
            school = cells[1].select_one('a[href*="/wiki/"]')
            if not school:
                continue
            name = school.get_text(" ",strip=True)
            image = cells[0].select_one('img[src*="/wikipedia/commons/"]')
            logo = ""
            if image:
                logo = "https:"+image["src"].split("?")[0] if image["src"].startswith("//") else image["src"].split("?")[0]
            location = cells[2].find("a") if "City" in headers else None
            result[normalized(name)] = dict(name=name, wiki=school["href"], logo=logo,
                                            city=location.get_text(" ",strip=True) if location else "",
                                            power="", postcode="", aliases=[name])
    return result


def providers(cache):
    wiki = wiki_providers(cache / "wikipedia-uk-universities.html")
    institutions = {}
    workbook = load_workbook(cache / "ofs.xlsx",read_only=True,data_only=True)
    matched = set()
    for row in workbook["Register"].iter_rows(min_row=4,values_only=True):
        legal,_,trading,ident,address,_,website = row[:7]
        power = str(row[13]).strip()
        if not ident or not power.startswith(("Research","Taught","Bachelor")):
            continue
        alternatives = [legal]+[v for v in str(trading or "").splitlines() if v and v.strip() != "Not applicable"]
        keys = [normalized(v) for v in alternatives]
        match = next((key for key in keys if key in wiki),None)
        if match:
            matched.update(keys)
        base = wiki.get(match,dict(name=alternatives[-1],wiki="",logo="",city=""))
        postcode = POSTCODE.search(str(address))
        institutions[str(ident)] = dict(base,power=power,postcode=postcode[0].upper() if postcode else "",
                                       website=website if isinstance(website,str) and website.startswith("https://") else "",
                                       aliases=list(dict.fromkeys([*alternatives,base["name"]])))
    workbook.close()
    for key, entry in wiki.items():
        if key not in matched and key not in {"universityofgibraltar","universityofwales"}:
            institutions[key] = dict(entry,website="")
    return institutions


def geocodes(cache, institutions):
    target = cache / "provider-postcodes.json"
    results = json_read(target) if target.is_file() else {}
    missing = sorted({r["postcode"] for r in institutions.values() if r["postcode"]} - results.keys())
    for start in range(0,len(missing),80):
        batch = missing[start:start+80]
        body = json.dumps({"postcodes":batch}).encode("utf-8")
        request = Request("https://api.postcodes.io/postcodes",data=body,headers={"Content-Type":"application/json"})
        with urlopen(request,timeout=24) as response:
            pairs = json.load(response)["result"]
        for pair in pairs:
            match = pair["result"]
            results[pair["query"]] = match["codes"]["admin_district"] if match else None
    target.write_text(json.dumps(results),encoding="utf-8")
    return results


def assign_locations(cache, schools):
    features = json_read(cache / "lad.geojson")["features"]
    areas = [(f["properties"]["LAD25CD"], f["properties"]["LAD25NM"], make_valid(shape(f["geometry"]))) for f in features]
    index = STRtree([item[2] for item in areas])
    known_ids = {row[0] for row in areas}
    district_names = {normalized(row[1]):row[0] for row in areas}
    district_names.update({"dundee":"S12000042","edinburgh":"S12000036","glasgow":"S12000049",
                           "aberystwyth":"W06000008","stirling":"S12000030","standrews":"S12000047",
                           "bangor":"W06000002","stokeontrent":"E06000021","chichester":"E07000225"})
    aliases, websites = defaultdict(set), defaultdict(set)
    by_location = defaultdict(dict)
    for key,school in schools.items():
        for name in school["aliases"]:
            if len(normalized(name)) > 4:
                aliases[normalized(name)].add(key)
        if school["website"]:
            websites[urlsplit(school["website"]).netloc.removeprefix("www.")].add(key)
    for site in json_read(cache / "university-osm.json"):
        operator = normalized(site.get("operator",""))
        name = normalized(site.get("name",""))
        url = site.get("website") or site.get("contact:website") or ""
        host = urlsplit(url).netloc.removeprefix("www.")
        candidates = aliases.get(operator) or aliases.get(name) or websites.get(host)
        if not candidates and "campus" in name:
            # Only accept a longer campus name if it clearly names its provider.
            candidates = next((aliases[prefix] for prefix in sorted(aliases,key=len,reverse=True)
                               if len(prefix)>10 and name.startswith(prefix)), None)
        if not candidates or len(candidates) != 1:
            continue
        school = next(iter(candidates))
        point = Point(site["lon"],site["lat"])
        hits = index.query(point,predicate="covered_by")
        if not len(hits):
            continue
        district = areas[hits[0]][0]
        label = site.get("name") or schools[school]["name"]
        placements = by_location[school].setdefault(district,{})
        placements[label] = "https://www.openstreetmap.org/"+site["osm"]
    postcode = geocodes(cache,schools)
    for key,school in schools.items():
        matches = by_location[key]
        for code,label,url in VERIFIED_CAMPUSES.get(normalized(school["name"]),[]):
            matches.setdefault(code,{})[label] = url
        if matches:
            continue
        code = postcode.get(school["postcode"]) or district_names.get(normalized(school["city"]))
        if code in known_ids:
            matches[code] = {"登记所在地":REGISTER if school["power"] else school["wiki"]}
    return by_location


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache",type=Path)
    parser.add_argument("--output",type=Path,default=Path("dist/data/uk/universities.json"))
    args=parser.parse_args()
    schools=providers(args.cache)
    locations=assign_locations(args.cache,schools)
    russell={normalized(name) for name in RUSSELL}
    result=[]
    missing=[]
    for ident,school in schools.items():
        if not locations[ident]:
            missing.append(school["name"])
            continue
        name=school["name"]
        tags=[]
        if any(normalized(alias) in russell for alias in school["aliases"]): tags.append("russell")
        if school["power"]=="Research": tags.append("research")
        if re.search(r"conservatoire|conservatory|school of|college of (?:art|music|dance)|creative arts",name,re.I):
            tags.append("specialist")
        places={}
        for code,sites in locations[ident].items():
            source=school["website"] or school["wiki"] or REGISTER
            places[code]=[["院校",source],*sorted(sites.items())]
        abbr="".join(word[0] for word in re.findall(r"[A-Za-z]+",name)
                     if word.casefold() not in {"university","of","the","and"})[:3] or name[:2]
        result.append(dict(id=ident,name=name,abbr=abbr,tags=tags,placements=places,logo=school["logo"]))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({"schools":sorted(result,key=lambda row:row["name"].casefold())},
                                     ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print(len(result),"mapped institutions",sum("russell" in row["tags"] for row in result),"Russell Group",
          sum(len(row["placements"]) for row in result),"placements")
    print(len(missing),"unplaced:",missing)


if __name__=="__main__":
    main()
