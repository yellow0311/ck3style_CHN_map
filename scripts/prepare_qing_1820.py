"""Convert the CHGIS V4 1820 MapInfo tables for a local historical preview.

Pass the directory with the extracted 1820 province/prefecture boundaries,
prefecture and county seats, and line and polygon river tables. Requires
pyogrio, shapely, numpy, pillow and the dependencies of prepare_terrain.
"""

import argparse
from collections import defaultdict
from pathlib import Path
from tempfile import gettempdir

from pyogrio.raw import read
from shapely import get_parts, make_valid, transform, union_all, from_wkb
from shapely.geometry import MultiPolygon
from shapely.ops import linemerge, polylabel

from prepare_boundaries import encode_ring, save
from prepare_terrain import EAST, NORTH, SOUTH, WEST, load_height, save_grid


ROOT = Path(__file__).resolve().parents[1]
PAGE = {
    '直隶':'7–9', '盛京':'10–11', '吉林':'12–13', '黑龙江':'14–15', '江苏':'16–17',
    '安徽':'18–19', '山西':'20–21', '山东':'22–23', '河南':'24–25', '陕西':'26–27',
    '甘肃':'28–30', '浙江':'31–32', '江西':'33–34', '湖北':'35–36', '湖南':'37–38',
    '四川':'39–41', '福建':'42–43', '广东':'44–45', '广西':'46–47', '云南':'48–49',
    '贵州':'50–51', '新疆':'52–54', '乌里雅苏台':'55–56', '内蒙古':'57–58', '青海':'59–60',
    '西藏':'61–63',
}
REGIONAL_TYPES = {
    '新疆':'边疆辖区', '乌里雅苏台':'将军辖区', '盛京':'将军辖区', '吉林':'将军辖区',
    '黑龙江':'将军辖区', '内蒙古':'盟旗地区', '青海':'边疆辖区', '西藏':'边疆辖区',
    '中俄尼布楚条约待议地区':'条约待议地区',
}
PALETTE = ['#a86d79','#779e9d','#c99861','#959666','#8788af','#8aab82','#be7861','#789aad']
MAJOR_RIVERS = {'黄河','长江','大江','黑龙江','松花江','辽河','鸭绿江','额尔齐斯河',
                '塔里木河','伊犁河','雅鲁藏布江','澜沧江','怒江','西江','淮河','汉水','汉江','赣江'}


def table(source, name):
    metadata, _, wkb, fields = read(source / (name + '.TAB'))
    geoms = from_wkb(wkb, on_invalid='ignore')
    return [(dict(zip(metadata['fields'], attrs)), geom)
            for attrs, geom in zip(zip(*fields), geoms, strict=True) if geom is not None]


def xy(lon, lat):
    return (lon-62)*14, (57-lat)*17


def polygons(geom):
    if geom.geom_type == 'Polygon':
        yield geom
    elif hasattr(geom, 'geoms'):
        for part in geom.geoms:
            yield from polygons(part)


def lines(geom):
    if geom.geom_type == 'LineString':
        yield geom
    elif hasattr(geom, 'geoms'):
        for part in geom.geoms:
            yield from lines(part)


def polygonal(geom):
    return MultiPolygon([p for p in polygons(make_valid(geom)) if p.area > 0])


def project_geom(geom):
    return transform(geom, xy, interleaved=False)


def encode_area(geom):
    rings = [ring for p in polygons(geom) for ring in (p.exterior,*p.interiors)]
    return '!'.join(encode_ring([(round(x*1000),round(y*1000)) for x,y in ring.coords[:-1]]) for ring in rings)


def area_record(ident, name, kind, geom, **fields):
    g = project_geom(polygonal(geom)).simplify(.025, preserve_topology=True)
    label = polylabel(max(polygons(g), key=lambda part:part.area), tolerance=.4)
    return {'id':ident, 'n':name, 'type':kind, 'x':round(label.x,3), 'y':round(label.y,3),
            'b':[round(v,3) for v in g.bounds], 'g':encode_area(g), **fields}


def build_admin(source):
    province, city, county = [], [], []
    top, primary, precincts = {}, {}, defaultdict(list)
    county_rows = table(source,'PII_Point_1820_County')
    source_prefs = table(source,'PII_Boun_1820_Pref')
    shapes = []
    for attrs, area in table(source,'PII_Boun_1820_Prov'):
        name = attrs['NAME_CH'].strip()
        geom = polygonal(area)
        ident = 'qing-p-'+str(attrs['SYS_ID'])
        top[name] = (ident, geom)
        shapes.append(geom)
    for name, (ident, geom) in top.items():
        used = {r['color'] for r in province if geom.intersects(top[r['n']][1])}
        color = next((c for c in PALETTE if c not in used), PALETTE[len(province)%len(PALETTE)])
        kind = REGIONAL_TYPES.get(name, '行省' if name in PAGE else '海疆地名')
        if kind in {'条约待议地区','海疆地名'}:
            color = '#a69a83'
        province.append(area_record(ident,name,kind,geom,nation=ident,color=color,sourcePage=PAGE.get(name,'3–4')))

    for attrs, geom in source_prefs:
        name, parent = attrs['NAME_CH'].strip(), attrs['LEV1_CH'].strip()
        if name == '徐州府':
            # 江苏分图和八个县级治所一致。V4 府界属性误挂安徽。
            parent = '江苏'
        if not name or parent not in top or name == parent:
            continue
        if name == '太仓州':
            kind = '直隶州'
        elif name.endswith('副都统辖区'):
            kind = '副都统辖区'
        else:
            kind = attrs['TYPE_CH'].strip() or '辖区'
        precincts[parent].append((attrs['SYS_ID'],name,kind,polygonal(geom)))

    # Match the missing Chahar subdivision to the residual already delineated by
    # the parent and neighbouring jurisdictions. No new county boundaries.
    parent = '内蒙古'
    neighbouring = union_all([g for _,_,_,g in precincts[parent]],grid_size=.00001)
    residual = top[parent][1].difference(neighbouring,grid_size=.00001)
    seats = [point for r,point in county_rows if r['LEV2_CH'] == '察哈尔']
    parts = [part for part in polygons(residual) if part.area > .1 and any(part.covers(seat) for seat in seats)]
    if parts:
        precincts[parent].append(('chahar','察哈尔','旗辖区',union_all(parts)))

    for parent, areas in precincts.items():
        by_name = defaultdict(list)
        for key, name, kind, geom in areas:
            by_name[name].append((key,kind,geom))
        nation = top[parent][0]
        for name, entries in by_name.items():
            key,kind,_ = entries[0]
            geom = union_all([shape for _,_,shape in entries],grid_size=.00001)
            ident = nation+'-f-'+str(key)
            primary[parent,name] = ident
            city.append(area_record(ident,name,kind,geom,p=nation,nation=nation,sourcePage=PAGE[parent]))

    for attrs, point in county_rows:
        name = attrs['NAME_CH'].strip()
        parent, sub = (attrs[key].strip() for key in ('LEV1_CH','LEV2_CH'))
        kind = attrs['TYPE_CH'].strip() or '县级政区'
        if kind in {'牧厂','军镇'}:
            continue
        canonical = sub+'辖区' if sub.endswith('副都统') else '喀喇乌苏' if sub == '库尔喀喇乌苏' else sub
        nation = top[parent][0]
        linked = primary.get((parent,canonical))
        x,y = xy(point.x,point.y)
        item = {'id':'qing-c-'+str(attrs['SYS_ID']), 'n':name, 'type':kind, 'p':linked or nation,
                'nation':nation, 'x':round(x,3), 'y':round(y,3), 'seat':True,'sourcePage':PAGE[parent]}
        if sub and not linked:
            item['description'] = '图册所载下辖关系 · '+sub
            item['aliases'] = [sub+name]
        county.append(item)
    # The capital inset labels Daxing and Wanping in the same city.
    wanping = next(r for r in county if r['n'] == '宛平县')
    x,y = xy(116.413,39.939)
    county.append({**wanping,'id':'qing-c-daxing','n':'大兴县','x':round(x,3),'y':round(y,3),
                   'description':'京师附郭县，县署位于今大兴胡同一带，位置为约略定位。',
                   'source':'https://www.beijing.gov.cn/hudong/gfxwjzj/qjzjxx/202504/P020250417415998607329.pdf'})

    outline = project_geom(union_all(shapes,grid_size=.00001)).simplify(.025,preserve_topology=True)
    return {'province':province,'city':city,'county':county,'outline':encode_area(outline)}, shapes


def ring_svg(coords, close=False):
    vertices = ' '.join(f'{x:.2f},{y:.2f}' for x,y in coords)
    return 'M'+vertices+('Z' if close else '')


def build_water(source):
    water, lakes = [], []
    for _, geom in table(source,'Layer1820_River_Pgn'):
        for part in polygons(make_valid(geom)):
            if part.area < .00008:
                continue
            lakes.append((part.bounds,[list(r.coords) for r in (part.exterior,*part.interiors)]))
            layer = project_geom(part).simplify(.035,preserve_topology=True)
            g = ''.join(ring_svg(r.coords, True) for r in (layer.exterior,*layer.interiors))
            water.append(['lake',max(1,7-int(layer.area**.28*2)),[round(v,2) for v in layer.bounds],g])
    named = defaultdict(list)
    for attrs, geom in table(source,'River_Line_Layer1820'):
        named[attrs['Character_name'].strip()].extend(lines(geom))
    for name, group in named.items():
        for line in lines(linemerge(group)) if name else group:
            geom = project_geom(line).simplify(.045)
            rank = 1 if name in MAJOR_RIVERS else 3 if geom.length >= 34 else 5 if geom.length >= 11 else 8
            water.append(['river',rank,[round(v,2) for v in geom.bounds],ring_svg(geom.coords)])
    return water, lakes

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path,help='Extracted 1820 CHGIS V4 MapInfo tables')
    parser.add_argument('--output',type=Path,default=ROOT/'dist/data/qing-1820')
    parser.add_argument('--elevation-cache',type=Path,default=Path(gettempdir())/'shanhe-atlas-elevation')
    parser.add_argument('--vectors-only',action='store_true')
    args = parser.parse_args()
    args.output.joinpath('terrain').mkdir(parents=True,exist_ok=True)
    admin, land = build_admin(args.source)
    save(args.output/'admin-boundaries.json',admin)
    water, lakes = build_water(args.source)
    save(args.output/'terrain/water.json',water)
    print({k:len(admin[k]) for k in ('province','city','county')},'water',len(water),flush=True)
    if not args.vectors_only:
        args.elevation_cache.mkdir(parents=True,exist_ok=True)
        areas = [(part.bounds,[list(r.coords) for r in (part.exterior,*part.interiors)])
                 for geom in land for part in polygons(geom)]
        height = load_height((WEST,SOUTH,EAST,NORTH),30,5,args.elevation_cache)
        # Land in the historical shoreline can be below the coast in modern data.
        save_grid(args.output/'terrain/overview.hgt.gz',height.clip(min=0),WEST,NORTH,30,areas,lakes)


if __name__ == '__main__':
    main()
