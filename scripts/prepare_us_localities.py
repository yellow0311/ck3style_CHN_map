"""Add U.S. Census localities to an existing atlas using the 2025 Census files.

The cache contains county.zip, cousub.zip and place.zip (2025 1:500,000
cartographic boundaries), est.csv (SUB-EST2025), and hi-2020.zip (PL 94-171).
"""
import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import re
from zipfile import ZipFile

import shapefile
from shapely import STRtree, union_all

from prepare_us_admin import STATES, dump, packed_polygon, polygons, projected
from us_locality_names import UNIT, chinese_name, geonames_aliases, normalize


PLACE_TYPES = {'21': 3, '25': 0, '37': 3, '43': 1, '47': 2, '57': 5, '86': 8, '39': 7}
CONSOLIDATED = {'00', '53', 'CG', 'MG', 'UC', 'UG'}
SUFFIXES = ['市', '镇', '村', '自治市镇', '乡镇', '普查指定地区', '市县合并区', '镇级辖区', '保留地']
ADDED_COUNTIES = {
    '51530': '布埃纳维斯塔市', '51580': '科温顿市', '51595': '恩波里亚市',
    '51600': '费尔法克斯市', '51678': '列克星敦市', '51685': '马纳萨斯帕克市',
    '51720': '诺顿市',
}


def read_shapes(cache, filename):
    with shapefile.Reader(str(cache / filename), encodingErrors='replace') as reader:
        for item in reader.iterShapeRecords():
            row = item.record.as_dict()
            if row['STATEFP'] in STATES and item.shape.points:
                yield row, projected(item.shape.__geo_interface__)


def estimates(cache):
    whole, parts, divisions, county_pop = {}, defaultdict(dict), {}, {}
    with (cache / 'est.csv').open(encoding='cp1252', newline='') as source:
        for row in csv.DictReader(source):
            state, county = row['STATE'], row['COUNTY']
            if state not in STATES:
                continue
            pop = int(row['POPESTIMATE2025'])
            if row['SUMLEV'] == '162' and row['FUNCSTAT'] in 'ABF':
                whole[state + row['PLACE']] = pop
            elif row['SUMLEV'] == '157':
                parts[state + row['PLACE']][state + county] = pop
            elif row['SUMLEV'] == '061' and row['FUNCSTAT'] in 'AB' and row['PRIMGEO_FLAG'] == '1':
                divisions[state + county + row['COUSUB']] = pop
            elif row['SUMLEV'] == '050':
                county_pop[state + county] = int(row['POPESTIMATE2024'])
    return whole, parts, divisions, county_pop


def hawaii_counts(cache):
    with ZipFile(cache / 'hi-2020.zip') as archive:
        geography = {}
        for line in archive.read('higeo2020.pl').splitlines():
            fields = line.split(b'|')
            if fields[2] == b'160':
                geography[fields[7]] = fields[9].decode('ascii')
        counts = {}
        for line in archive.read('hi000012020.pl').splitlines():
            fields = line.split(b'|', 6)
            if fields[4] in geography:
                counts[geography[fields[4]]] = int(fields[5])
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cache', type=Path)
    parser.add_argument('geonames', type=Path, help='US.zip from GeoNames')
    parser.add_argument('--output', type=Path, default=Path('dist/data/us'))
    args = parser.parse_args()
    read = lambda path: json.loads(path.read_text(encoding='utf-8'))
    admin_path = args.output / 'admin-boundaries.json'
    stats_path = args.output / 'statistics.json'
    admin = read(admin_path)
    stats = read(stats_path)
    counties = {row['id']: row for row in admin['city'] or admin['county']}
    names = read(Path(__file__).with_name('us_chinese_names.json'))
    known = {normalize(name): UNIT.sub('', label) for name, label in names['campuses'].items()}
    aliases = geonames_aliases(args.geonames)
    whole, parts, divisions, county_pop = estimates(args.cache)
    hawaii = hawaii_counts(args.cache)

    county_shapes, county_base = {}, {}
    for row, geom in read_shapes(args.cache, 'county.zip'):
        code, state = row['GEOID'], row['STATEFP']
        admin_type = '独立市' if row['NAMELSAD'].endswith(' city') else '县及同级辖区'
        entry = dict(id=code, n=ADDED_COUNTIES.get(code, row['NAME']), en=row['NAMELSAD'],
                     nation=state, p=state, type=admin_type)
        entry.update(counties.get(code, {}))
        entry.pop('aliases', None)
        entry.update(packed_polygon(geom.simplify(.025)))
        if admin_type == '独立市':
            entry['type'] = admin_type
        if code not in stats:
            stats[code] = [None, county_pop[code] / 10000 if code in county_pop else None]
        if code in ADDED_COUNTIES:
            entry['censusPop'] = True
        counties[code] = entry
        county_shapes[code] = geom
        county_base[code] = normalize(row['NAME'])
    assert len(county_shapes) == len(counties) == 3144 and all(code in county_shapes for code in counties)
    hawaii_counties = [code for code in county_shapes if code.startswith('15')]
    county_index = STRtree([county_shapes[code] for code in hawaii_counties])
    index, geometry = [], defaultdict(dict)
    summary = Counter()
    primary_places = defaultdict(dict)

    def add(row, geom, parent, kind, population, total=None, year=2025):
        polygon = union_all(list(polygons(geom)))
        if polygon.is_empty or polygon.area < .0000001:
            summary['empty part'] += 1
            if population:
                print('County part without a usable boundary:', row['GEOID'], parent, population)
            return
        identifier = ('M' if kind == 4 or 'COUSUBFP' in row else 'P') + row['GEOID']
        if total is not None:
            identifier += '-' + parent
        label = chinese_name(row['NAME'], row['STUSPS'], aliases, known, SUFFIXES[kind])
        original = row['NAMELSAD']
        if kind == 5:
            original = row['NAME'] + ' (CDP)'
        packed = packed_polygon(polygon.simplify(.012))
        index.append([identifier, parent, label, original, row['GEOID'], kind, packed['x'], packed['y'], population, total, year, packed['b']])
        geometry[parent[:2]][identifier] = packed['d']
        summary[SUFFIXES[kind]] += 1

    for row, geom in read_shapes(args.cache, 'place.zip'):
        code = row['GEOID']
        kind = PLACE_TYPES.get(row['LSAD'], 6 if row['LSAD'] in CONSOLIDATED else 0)
        if row['STATEFP'] == '15' and kind == 5:
            hits = {hawaii_counties[i]: geom.intersection(county_shapes[hawaii_counties[i]]).area
                    for i in county_index.query(geom)}
            if hits:
                add(row, geom, max(hits, key=hits.get), kind, hawaii.get(code), year=2020)
            continue
        if code not in whole or row['STATEFP'] == '11':
            continue
        parents = {parent: pop for parent, pop in parts[code].items() if parent in county_shapes}
        if not parents:
            summary['no county match'] += 1
            continue
        for parent, pop in parents.items():
            county = county_shapes[parent]
            folded_name = normalize(row['NAME'])
            if len(parents) == 1 and ((county_base[parent] == folded_name and geom.intersection(county).area >= .98 * county.area)
                                     or counties[parent]['type'] == '独立市'):
                counties[parent]['aliases'] = [row['NAME'], row['NAMELSAD'], code,
                    chinese_name(row['NAME'], row['STUSPS'], aliases, known, SUFFIXES[kind])]
                primary_places[parent][folded_name] = geom
                summary['county-level city'] += 1
                continue
            extent = geom if len(parents) == 1 else geom.intersection(county)
            add(row, extent, parent, kind, pop, whole[code] if len(parents) > 1 else None)
            primary_places[parent][folded_name] = extent

    for row, geom in read_shapes(args.cache, 'cousub.zip'):
        if row['GEOID'] not in divisions:
            continue
        county = row['STATEFP'] + row['COUNTYFP']
        other = primary_places[county].get(normalize(row['NAME']))
        if other is not None and geom.intersection(other).area >= .98 * max(geom.area, other.area):
            continue
        kind = PLACE_TYPES.get(row['LSAD'], 4)
        add(row, geom, county, kind, divisions[row['GEOID']])

    assert len(index) == len({row[0] for row in index})
    assert all(re.search(r'[\u3400-\u9fff]', row[2]) for row in index)
    assert len(geometry) == 50
    folder = args.output / 'localities'
    folder.mkdir(exist_ok=True)
    dump(folder / 'index.json', sorted(index, key=lambda row: (row[1], row[0])))
    for state, paths in sorted(geometry.items()):
        dump(folder / (state + '.json'), paths)
    admin['city'] = [counties[code] for code in sorted(counties)]
    admin['county'] = []
    dump(admin_path, admin)
    dump(stats_path, stats)
    print(len(index), 'locality records across', len(geometry), 'states;', dict(summary))
    print(len({row[4] for row in index}), 'distinct localities;', sum(row[8] is None for row in index), 'missing population values')


if __name__ == '__main__':
    main()
