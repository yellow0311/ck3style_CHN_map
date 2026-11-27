"""Build detailed China boundaries for existing atlas codes from local vector sources."""
import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path

import numpy as np
from shapely import STRtree, get_num_coordinates, make_valid, set_precision, union_all
from shapely.geometry import Polygon, shape
from shapely import transform

from prepare_boundaries import OUTPUT, encode_ring


HK_DISTRICT_CODES = {
    'A':'810001','B':'810002','C':'810003','D':'810004','E':'810005','F':'810006',
    'G':'810007','H':'810008','J':'810009','K':'810010','L':'810011','M':'810012',
    'N':'810013','P':'810014','Q':'810015','R':'810016','S':'810017','T':'810018',
}

# Use a common snapshot for enclaves and the jurisdictions they border. These
# codes match the atlas, but some outlines differ materially from its older data.
MATCHED_SNAPSHOT = {
    '140302', '140303', '220402', '220403', '220422', '230306', '513425', '650106',
    '654002', '659002', '659003', '659006', '659007', '659010', '659011', '659012',
}

SOURCE_CODE_ALIASES = {'513402':'513425'}  # Huili city, retaining the atlas's existing record ID.

# Tianjin's enclosed Tangshan areas are grouped under district codes in the
# boundary snapshot. Use their common city in the map to avoid a district label.
CONTEXT_PARENT_CODES = {'120000': {'130202':'130200', '130207':'130200'}}


def gcj_delta(lon, lat):
    x, y = lon - 105, lat - 35
    common = (20 * np.sin(6 * x * np.pi) + 20 * np.sin(2 * x * np.pi)) * 2 / 3
    dx = (300 + x + 2 * y + .1 * x*x + .1 * x*y + .1 * np.sqrt(abs(x)) + common
          + (20 * np.sin(x*np.pi) + 40 * np.sin(x*np.pi/3)) * 2/3
          + (150 * np.sin(x*np.pi/12) + 300 * np.sin(x*np.pi/30)) * 2/3)
    dy = (-100 + 2*x + 3*y + .2*y*y + .1*x*y + .2*np.sqrt(abs(x)) + common
          + (20 * np.sin(y*np.pi) + 40 * np.sin(y*np.pi/3)) * 2/3
          + (160 * np.sin(y*np.pi/12) + 320 * np.sin(y*np.pi/30)) * 2/3)
    radians = lat*np.pi/180
    eccentricity = .006693421622965943
    factor = 1 - eccentricity * np.sin(radians)**2
    return (dx * 180 * np.sqrt(factor) / (6378245 * np.cos(radians) * np.pi),
            dy * 180 * factor**1.5 / (6378245 * (1-eccentricity) * np.pi))


def xy(lon,lat):
    return (lon-73)*14,(54-lat)*17


def project_gcj_ring(text):
    lon,lat = np.fromstring(text.replace(',',' '),sep=' ').reshape((-1,2)).T
    west, south = lon, lat
    for _ in range(2):
        dx, dy = gcj_delta(west, south)
        west, south = lon-dx, lat-dy
    return np.column_stack(xy(west,south))


def polygons(geom):
    if geom.geom_type == 'Polygon' and not geom.is_empty:
        yield geom
    elif hasattr(geom,'geoms'):
        for part in geom.geoms:
            yield from polygons(part)


def clean(geom):
    if not geom.is_valid:
        geom = make_valid(geom)
    return geom if geom.geom_type in ('Polygon','MultiPolygon') else union_all(list(polygons(geom)))


def decode_ring(value):
    current = [0, 0]
    vertices = []
    axis, shift, delta = 0, 0, 0
    for ch in value:
        digit = ord(ch)-63
        delta |= (digit & 31) << shift
        if digit >= 32:
            shift += 5
            continue
        current[axis] += -(delta+1)//2 if delta & 1 else delta//2
        if axis == 1:
            vertices.append(tuple(c/1000 for c in current))
        axis, shift, delta = 1-axis, 0, 0
    return vertices


def from_rings(rings):
    parts = sorted((clean(Polygon(ring)) for ring in rings if len(ring) >= 3),
                   key=lambda part: part.area,reverse=True)
    if not parts:
        return Polygon()
    # Nested rings describe holes. Adjoining parts dissolve to a common exterior.
    shells, holes = [], []
    for part in parts:
        if part.is_empty:
            continue
        if any(shell.contains(part) for shell in shells):
            holes.append(part)
        else:
            shells.append(part)
    geom = union_all(shells)
    return geom.difference(union_all(holes)) if holes else geom


def project(geometry):
    return transform(shape(geometry),xy,interleaved=False)


def overlap(first,second):
    common = first.intersection(second).area
    return common/(first.area+second.area-common)


def osm_fallback(source,missing,previous,province_codes):
    by_name = defaultdict(list)
    values = {}
    for code,region in missing.items():
        by_name[region['n']].append(code)
    with source.open(encoding='utf-8') as stream:
        for line in stream:
            _,level,_ = line.split(',',2)
            if level not in ('"4"','"5"','"6"','"7"'):
                continue
            _,_,name,original,ref,geometry = json.loads(line)
            candidates = set(by_name.get(name,[])) | set(by_name.get(original,[]))
            if ref in missing:
                candidates.add(ref)
            if not candidates:
                continue
            boundary = clean(project(geometry))
            for code in candidates:
                old = previous[code]
                if get_num_coordinates(boundary) <= get_num_coordinates(old):
                    continue
                score = overlap(boundary,old)
                threshold = .965 if code in province_codes else .74
                if score >= threshold and score > values.get(code,(0,))[0]:
                    values[code] = (score,boundary)
    return {code:boundary for code,(_,boundary) in values.items()}


def pack(geometry):
    snapped = set_precision(clean(geometry),.001,mode='valid_output')
    rings = []
    for part in polygons(snapped):
        for ring in (part.exterior,*part.interiors):
            rings.append(encode_ring([(round(x*1000),round(y*1000)) for x,y in ring.coords[:-1]]))
    if rings:
        return ['!'.join(rings),[round(a,3) for a in snapped.bounds]]


def enclosed_jurisdictions(admin, geometries):
    """Identify named districts visible inside holes of another map focus."""
    counties = [r for r in admin['county'] if r['id'] in geometries]
    by_id = {r['id']:r for regions in admin.values() for r in regions}
    province_codes = {r['id'] for r in admin['province']}
    county_shapes = [geometries[r['id']] for r in counties]
    tree = STRtree(county_shapes)
    contexts = defaultdict(lambda: defaultdict(list))

    for tier in ('province', 'city', 'county'):
        for host in admin[tier]:
            code = host['id']
            if code not in geometries:
                continue
            scope = by_id.get(host['p'], host) if tier == 'county' else host
            for part in polygons(geometries[code]):
                for ring in part.interiors:
                    gap = Polygon(ring)
                    if gap.area < .025:
                        continue
                    hits = []
                    for i in tree.query(gap,predicate='intersects'):
                        region = counties[i]
                        if (region['id'] == code or region['p'] == scope['id'] or
                                (scope['id'] in province_codes and region['id'][:2] == code[:2])):
                            continue
                        meet = gap.intersection(county_shapes[i])
                        if meet.area >= max(.015, gap.area * .045):
                            hits.append((region['id'],meet))
                    if not hits or union_all([g for _,g in hits]).area < gap.area*.84:
                        continue
                    # When one jurisdiction accounts for almost the entire hole,
                    # share that edge to avoid pixel cracks from source rounding.
                    for region,piece in hits:
                        display_code = CONTEXT_PARENT_CODES.get(scope['id'],{}).get(region,region)
                        contexts[scope['id']][display_code].append(gap if piece.area >= gap.area*.94 else piece)

    result = {}
    for scope,targets in sorted(contexts.items()):
        entries = []
        for code,parts in sorted(targets.items()):
            area = union_all(parts)
            packed = pack(area)
            if packed:
                point = max(polygons(area),key=lambda shape:shape.area).representative_point()
                entries.append([code,*packed,round(point.x,3),round(point.y,3)])
        if entries:
            result[scope] = entries
    return result


def read(path):
    return json.loads(path.read_bytes())


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('areacity_csv',type=Path)
    parser.add_argument('hong_kong',type=Path,help='HAD 18 district GeoJSON')
    parser.add_argument('--macao',type=Path,help='GeoJSON with the existing numeric codes in properties.id')
    parser.add_argument('--osm-areas',type=Path,help='Optional OSM boundary records as ID, admin level, names, code and geometry')
    parser.add_argument('--data',type=Path,default=OUTPUT)
    args = parser.parse_args()
    admin = read(args.data/'admin-boundaries.json')
    extras_path = args.data/'direct-counties.json'
    if extras_path.exists():
        existing = {r['id'] for r in admin['county']}
        admin['county'].extend(r for r in read(extras_path) if r.get('g') and r['id'] not in existing)
    current = {r['id']:r for regions in admin.values() for r in regions}
    previous = {code:from_rings(decode_ring(ring) for ring in row.get('gDetail',row['g']).split('!'))
                for code,row in current.items()}
    csv.field_size_limit(50_000_000)
    detailed = {}
    rejected = []
    with args.areacity_csv.open(encoding='utf-8-sig',newline='') as source:
        for row in csv.DictReader(source):
            code = SOURCE_CODE_ALIASES.get(row['id'], row['id'].ljust(6,'0'))
            if row['id'] == '81':
                hong_kong_land = from_rings(project_gcj_ring(ring) for ring in row['polygon'].split(';'))
            if (code in detailed or code not in current or row['polygon'] in ('','EMPTY') or
                    row['id'].startswith(('81','82'))):
                continue
            geometry = from_rings(project_gcj_ring(ring) for ring in row['polygon'].split(';'))
            old = previous[code]
            if old.is_empty or geometry.is_empty:
                continue
            similarity = overlap(geometry,old)
            tolerance = .93 if code == '460000' else .965 if len(row['id']) == 2 else .84
            same_snapshot = code in MATCHED_SNAPSHOT and row['name'] == current[code]['n']
            if not same_snapshot and (similarity < tolerance or get_num_coordinates(geometry) <= get_num_coordinates(old)):
                rejected.append((code,round(similarity,3),get_num_coordinates(old),get_num_coordinates(geometry)))
                continue
            detailed[code] = geometry

    # District boundaries extend offshore. Keep their internal divisions and clip
    # the water portions against the coastline used for the main map.
    hong_kong = {HK_DISTRICT_CODES[f['properties']['地區號碼']]:clean(project(f['geometry']).intersection(hong_kong_land))
                 for f in read(args.hong_kong)['features']}
    assert len(hong_kong) == 18
    detailed.update(hong_kong)
    detailed['810000'] = clean(union_all(list(hong_kong.values())))
    if args.macao:
        detailed.update({str(f['properties']['id']):clean(project(f['geometry']))
                         for f in read(args.macao)['features']})
    else:
        detailed['820000'] = clean(union_all([geom for code,geom in previous.items()
                                              if code.startswith('82') and code != '820000']))

    province_codes = {r['id'] for r in admin['province']}
    if args.osm_areas:
        fallback = osm_fallback(args.osm_areas,{code:region for code,region in current.items() if code not in detailed},
                                previous,province_codes)
        detailed.update(fallback)
        print('OSM fallback records:',len(fallback))

    output = args.data/'china-boundaries'
    output.mkdir(exist_ok=True)
    provinces = {r['id']:detailed.get(r['id'],previous[r['id']]) for r in admin['province']}
    national = clean(union_all(list(provinces.values())))
    bundles = defaultdict(list)
    for code,geom in sorted(detailed.items()):
        if code in provinces:
            continue
        entry = pack(geom)
        if entry:
            bundles[code[:2]+'0000'].append([code,*entry])
    for code,bundle in bundles.items():
        save(output/(code+'.json'),bundle)
    context = {'base':enclosed_jurisdictions(admin,previous),
               'detail':enclosed_jurisdictions(admin,{**previous,**detailed})}
    save(output/'enclaves.json',context)
    save(output/'overview.json',{'provinces':[[code,*pack(geom)] for code,geom in provinces.items()],
                                 'outline':pack(national)[0],'bundles':sorted(bundles)})
    for key,regions in admin.items():
        print(key,sum(r['id'] in detailed for r in regions),'/',len(regions))
    print('Focus views with enclosed jurisdictions:',len(context['base']),len(context['detail']))
    print('Fallback records:',len(rejected), rejected[:25])


if __name__ == '__main__':
    main()
