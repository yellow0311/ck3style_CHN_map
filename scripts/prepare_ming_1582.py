"""Build the local Ming atlas from CHGIS V6 and the supplied historical atlas.

The inputs directory contains the UTF-8 WGS84 CHGIS prefecture polygon and
county point zip files, the Historical Map Project checkout, and PNG renders
of PDF pages 63 and 73. The water network uses the CHGIS V4 river and lake
tables prepared for the Qing preview.
"""

import argparse
import json
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from tempfile import gettempdir
from zipfile import ZipFile

import cv2
import numpy as np
import shapefile
from PIL import Image
from shapely import STRtree, make_valid, transform, union_all
from shapely.geometry import LineString, Point, Polygon, box, shape

from prepare_boundaries import save
from prepare_qing_1820 import area_record, build_water, encode_area, polygonal, polygons, project_geom, xy
from prepare_terrain import EAST, NORTH, SOUTH, WEST, load_height, save_grid


ROOT = Path(__file__).resolve().parents[1]
YEAR = 1582
PROVINCES = {
    'jingshi': ('京师（北直隶）','北直隶','44–46','#c59169'),
    'nanjing': ('南京（南直隶）','南直隶','47–49','#c68172'),
    'shandong': ('山东','承宣布政使司','50–51','#889cad'),
    'shanxi': ('山西','承宣布政使司','54–56','#a99b69'),
    'henan': ('河南','承宣布政使司','57–58','#9c879e'),
    'shaanxi': ('陕西','承宣布政使司','59–61','#8eaa86'),
    'sichuan': ('四川','承宣布政使司','62–63','#be8870'),
    'jiangxi': ('江西','承宣布政使司','64–65','#9ba989'),
    'huguang': ('湖广','承宣布政使司','66–67','#c9ac70'),
    'zhejiang': ('浙江','承宣布政使司','68–69','#91a189'),
    'fujian': ('福建','承宣布政使司','70–71','#a58ba5'),
    'guangdong': ('广东','承宣布政使司','72–73','#8da1ad'),
    'guangxi': ('广西','承宣布政使司','74–75','#a79972'),
    'yunnan': ('云南','承宣布政使司','76–79','#9f8b9f'),
    'guizhou': ('贵州','承宣布政使司','80–81','#809e9c'),
    'liaodong': ('辽东都司','都指挥使司','52–53','#bd8d66'),
    'west': ('乌思藏、朵甘','西部边地','85–86','#ad977b'),
    'northeast': ('东北女真诸部','边疆地区','42–43、82–83','#aa8e59'),
}


def snapshot(archive_path, year=YEAR):
    with ZipFile(archive_path) as archive:
        buffers = {ext: BytesIO(archive.read(next(n for n in archive.namelist() if n.endswith('.'+ext))))
                   for ext in ('shp','shx','dbf')}
    with shapefile.Reader(**buffers) as reader:
        for row in reader.iterShapeRecords():
            if row.record['BEG_YR'] <= year <= row.record['END_YR']:
                yield row.record.as_dict(), shape(row.shape.__geo_interface__)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def name_index(source, level):
    index = defaultdict(list)
    for key in PROVINCES:
        units = source/'units/administrative'/f'{key}.json'
        places = source/'places'/f'{key}.json'
        if not units.exists() or not places.exists():
            continue
        seats = {p['id']:Point(p['longitude'],p['latitude']) for p in read_json(places)
                 if p.get('longitude') is not None and p.get('latitude') is not None}
        for unit in read_json(units):
            place = seats.get(unit.get('seatPlaceId'))
            if place is not None and (level is None or unit['level'] in level):
                index[unit['name']].append((key,place))
    return index


def area_contours(image, bounds, min_area):
    r,g,b = np.asarray(image.convert('RGB'),dtype=np.int16).transpose(2,0,1)
    mask = ((r-b > 29)&(g-b > 18)&(r >= 195)&(g >= 173)&(b < 227)).astype(np.uint8)
    x,y,right,bottom = bounds
    mask[:y] = mask[bottom:] = 0
    mask[:,:x] = mask[:,right:] = 0
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(13,13))
    joined = cv2.morphologyEx(mask*255,cv2.MORPH_CLOSE,kernel)
    closed = (cv2.GaussianBlur(joined,(9,9),1.8) >= 118).astype(np.uint8)
    contours,_ = cv2.findContours(closed,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    return [Polygon(cv2.approxPolyDP(part,1.35,True).reshape(-1,2))
            for part in contours if cv2.contourArea(part) >= min_area]


def trace_curve(points):
    # Round the digitized joins within the width of the atlas's printed stroke.
    for _ in range(2):
        rounded = [points[0]]
        for (x1,y1),(x2,y2) in zip(points,points[1:]):
            rounded.extend(((.8*x1+.2*x2,.8*y1+.2*y2),(.2*x1+.8*x2,.2*y1+.8*y2)))
        rounded.append(points[-1])
        points = rounded
    return points


def liaodong_area(image):
    scan = Image.open(image).resize((820,1160))
    pieces = area_contours(scan,(59,200,748,950),1000)
    area = max(pieces,key=lambda p:p.area)
    # Follow the purple boundary beneath the diagonal yellow hatch marks.
    wall = trace_curve([(55,661),(68,658),(81,656),(94,651),(110,645),(127,638),
                        (143,631),(152,622),(156,611),(156,598),(160,586),
                        (169,579),(181,577),(195,575),(208,570),(219,563),
                        (229,553),(234,541),(237,526),(244,510),(250,498),
                        (251,484),(248,470),(246,455),(243,441),(245,430),
                        (253,424),(267,420),(280,417),(293,414),(302,406),
                        (308,395),(317,390),(332,391),(348,389),(361,391)])
    strip = LineString(wall).buffer(32).intersection(box(59,360,350,668))
    inland = Polygon(wall+[(361,710),(55,710)])
    area = area.difference(strip).union(inland.intersection(strip))
    area = max(polygons(area),key=lambda p:p.area)
    # Reference intersections along 120°, 122°, 124° E and 39°, 41°, 43° N.
    controls = [(120,43,120,213),(122,43,360,212),(124,43,598,210),
                (120,41,115,539),(122,41,361,537),(124,41,607,535),
                (120,39,110,864),(122,39,361,862),(124,39,615,860)]
    design = lambda x,y: np.array([np.ones_like(x),x,y,x*y]).T
    lon,lat,h,v = np.array(controls,dtype=float).T
    params = np.linalg.lstsq(design(h,v),np.stack([lon,lat],axis=1),rcond=None)[0]
    return polygonal(transform(area,lambda x,y:(design(x,y)@params).T,interleaved=False))


def overview_projection():
    # Conic registration from the printed meridians and parallels on the
    # 1415×1000 overview, independent of later administrative boundaries.
    top = [(60,207,79),(70,337,79),(80,459,79),(90,574,80),(100,682,81),
           (110,790,81),(120,902,82),(130,1019,83),(140,1143,84),(150,1277,85)]
    bottom = [(90,459,922),(100,658,922),(110,850,924),(120,1052,925)]
    north_edge = {lon:(x,y) for lon,x,y in top}
    matrix,offsets = [],[]
    for lon,x,y in bottom:
        start_x,start_y = north_edge[lon]
        dx,dy = x-start_x,y-start_y
        matrix.append((dy,-dx))
        offsets.append(dy*x-dx*y)
    apex_x,apex_y = np.linalg.lstsq(matrix,offsets,rcond=None)[0]
    lon,x,y = np.array(top+bottom).T
    angle = np.arctan2(x-apex_x,y-apex_y)
    angular_scale,central_longitude = np.linalg.lstsq(np.stack([angle,np.ones_like(angle)],axis=1),lon,rcond=None)[0]
    parallels = [(50,95,115),(40,94,335),(30,94,550),(50,1314,119),(40,1316,336),(30,1318,552)]
    lat,x,y = np.array(parallels).T
    distance = np.hypot(x-apex_x,y-apex_y)
    latitude_scale,latitude_offset = np.linalg.lstsq(
        np.stack([np.log(np.tan(np.pi/4+np.radians(lat)/2)),np.ones_like(lat)],axis=1),np.log(distance),rcond=None)[0]

    def reproject(px,py):
        x,y = px-apex_x,py-apex_y
        angle = np.arctan2(x,y)
        power = (np.log(np.hypot(x,y))-latitude_offset)/latitude_scale
        return central_longitude+angular_scale*angle,np.degrees(2*np.arctan(np.exp(power))-np.pi/2)
    return reproject


def frontier_areas(overview, civil):
    scan = Image.open(overview).convert('RGB').transpose(Image.Transpose.ROTATE_90).resize((1415,1000))
    project = overview_projection()
    northeast = max(area_contours(scan,(898,78,1265,460),1000),key=lambda p:p.area)
    # Follow the 1582 plate's purple stroke around the exposed western edge.
    # Close the eastern side inside the adjoining civil polygons so their
    # shared frontier is cut from the same vertices at both levels.
    western_edge = trace_curve([
        (699,510),(685,517),(677,523),(665,526),(653,530),(631,532),
        (615,533),(598,534),(582,532),(563,527),(548,523),(533,515),
        (524,519),(514,527),(506,532),(500,539),(493,536),(485,530),
        (478,522),(465,525),(452,528),(437,525),(423,524),(410,528),
        (397,531),(388,524),(377,520),(366,517),(354,524),(343,521),
        (334,518),(329,526),(324,530),(316,529),(307,528),(302,518),
        (300,510),(291,505),(283,500),(278,492),(270,483),(261,478),
        (254,474),(250,470),(254,466),(264,461),(274,464),(282,472),
        (288,480),(282,484),(273,484),(269,490),(271,500),(268,509),
        (268,519),(271,529),(276,539),(282,546),(282,555),(288,562),
        (289,568),(284,573),(294,576),(306,583),(312,591),(319,598),
        (326,608),(334,619),(343,623),(356,625),(365,629),(374,638),
        (380,647),(386,657),(400,666),(412,677),(425,686),(436,690),
        (433,702),(438,710),(449,712),(461,709),(475,710),(490,714),
        (507,716),(523,719),(543,718),(559,717),(573,712),(584,703),
        (596,700),(606,704),(615,710),(622,707),(626,715),(625,725),
        (623,733),(619,740),(616,747),(613,753),(614,759),(619,762)
    ])
    west = Polygon(western_edge+[(631,762),(647,748),(681,730),(706,701),
                                 (744,680),(775,635),(770,594),(749,570),
                                 (709,569),(695,559),(694,542),(699,525)])
    def cut(area):
        registered = make_valid(transform(area,project,interleaved=False))
        return polygonal(registered.difference(civil,grid_size=.00001))
    # The atlas shows open water in the gulf and no colored area in the
    # southern Liao valley. The overview's color mask picks up the paper tint.
    valley_edge = trace_curve([(123.7,41.72),(123.1,41.72),(122.94,41.73),
                               (122.89,41.75),(122.86,41.79),(122.83,41.84),
                               (122.76,41.88),(122.67,41.89),(119,41.89)])
    bohai_and_lower_liao = Polygon([(119,38.5),(123.7,38.5)]+valley_edge)
    return polygonal(cut(northeast).difference(bohai_and_lower_liao)),cut(west)


def build_admin(source, overview, liaodong):
    aliases = name_index(source/'historical-map-project/data',None)
    seat_aliases = name_index(source/'historical-map-project/data',{'county','county-level','prefecture','zhou'})
    prefectures = [(r,polygonal(g)) for r,g in snapshot(source/'dataverse-2966510.zip')
                   if r['NAME_CH'] and r['NAME_CH'] != '台湾' and not g.is_empty]
    assigned = defaultdict(list)
    remaining = []
    for row,geom in prefectures:
        name = row['NAME_CH']
        candidates = aliases.get(name,[])
        if name.endswith('卫') and geom.centroid.x < 105 and geom.centroid.y >= 33:
            assigned['shaanxi'].append((row,geom))
        elif name == '万全都司':
            assigned['jingshi'].append((row,geom))
        elif name in {'播州宣慰司','永宁宣慰司','四川行都司','松潘卫','天全六番招讨司'}:
            assigned['sichuan'].append((row,geom))
        elif candidates:
            key,_ = min(candidates,key=lambda c:geom.distance(c[1])+geom.centroid.distance(c[1])*.03)
            assigned[key].append((row,geom))
        else:
            remaining.append((row,geom))
    cores = {key:union_all([g for _,g in items],grid_size=.00001) for key,items in assigned.items()}
    if set(PROVINCES) - set(cores) != {'liaodong','west','northeast'}:
        raise ValueError('Could not identify all two capitals and thirteen provinces')
    for row,geom in remaining:
        key = min(cores,key=lambda k:cores[k].distance(geom.representative_point()))
        assigned[key].append((row,geom))

    land = {k:polygonal(union_all([g for _,g in rows],grid_size=.00001)) for k,rows in assigned.items()}
    civil = union_all(list(land.values()),grid_size=.00001)
    # Tie the continuous coastal corridor on the full plate to the two
    # registered boundaries. Keep its width from the detailed Liaodong plate.
    pass_corridor = Polygon(trace_curve([
        (119.36,40.182),(119.43,40.195),(119.49,40.214),(119.54,40.235),
        (119.60,40.251),(119.66,40.266),(119.73,40.272),(119.79,40.268),
        (119.77,40.211),(119.71,40.207),(119.64,40.199),(119.58,40.187),
        (119.51,40.166),(119.44,40.148),(119.37,40.125)
    ]))
    liaodong_land = liaodong_area(liaodong).union(pass_corridor,grid_size=.00001)
    land['liaodong'] = polygonal(liaodong_land.difference(civil,grid_size=.00001))
    land['northeast'],land['west'] = frontier_areas(overview,union_all([civil,land['liaodong']],grid_size=.00001))
    province,city,county = [],[],[]
    for key,(name,kind,page,color) in PROVINCES.items():
        ident = 'ming-p-'+key
        record = area_record(ident,name,kind,land[key],nation=ident,color=color,sourcePage=page)
        if key == 'northeast':
            record.update(frontier=True,description='图册所示东北女真诸部活动和羁縻地区的概略范围。辽东都司辖界另绘。')
        if key == 'west':
            record['description'] = '参照万历十年全图与都司分图概略描绘；西部边地的分界口径各异。'
        if key == 'liaodong':
            record['description'] = '山东二（辽东都司）分图所示辖区。卫、所按治所位置显示。'
        province.append(record)

    city_areas = []
    for key,items in assigned.items():
        group = defaultdict(list)
        for row,geom in items:
            group[row['NAME_CH'],row['TYPE_CH']].append((row,geom))
        for (name,kind),rows in group.items():
            row = rows[0][0]
            geom = polygonal(union_all([g for _,g in rows],grid_size=.00001))
            nation = 'ming-p-'+key
            ident = f'ming-f-{key}-{row["SYS_ID"]}'
            city.append(area_record(ident,name,kind or '辖区',geom,p=nation,nation=nation,sourcePage=PROVINCES[key][2]))
            city_areas.append((key,ident,geom))
    city_index = STRtree([g for _,_,g in city_areas])
    province_shapes = list(land.items())
    used = set()

    def add_seat(ident,name,kind,point,key=None,description=None):
        ident = 'ming-c-'+str(ident)
        if ident in used:
            return
        valid = [city_areas[index] for index in city_index.query(point,predicate='covered_by')]
        if key:
            valid = [item for item in valid if item[0] == key]
        seat_parent = min(valid,key=lambda item:item[2].area,default=None)
        if seat_parent:
            key,parent,_ = seat_parent
        else:
            key = key or min(province_shapes,key=lambda item:item[1].distance(point))[0]
            parent = 'ming-p-'+key
        if land[key].distance(point) > .45:
            return
        x,y = xy(point.x,point.y)
        row = dict(id=ident,n=name,type=kind,p=parent,nation='ming-p-'+key,seat=True,
                   x=round(x,3),y=round(y,3),sourcePage=PROVINCES[key][2])
        if description:
            row['description'] = description
        county.append(row)
        used.add(ident)

    for row,point in snapshot(source/'county-points.zip'):
        name = row['NAME_CH']
        if row['TYPE_CH'] in {'','侯国'} or not name or civil.distance(point) > .22:
            continue
        indexed = sorted(seat_aliases.get(name,[]),key=lambda item:point.distance(item[1]))
        key = indexed[0][0] if indexed and indexed[0][1].distance(point) < .09 else None
        add_seat(row['SYS_ID'],name,row['TYPE_CH'],point,key)

    # Supply the military seats whose positions are shown on the atlas's
    # Liaodong sheet. Leave the intervening satellite districts undivided.
    liaodong_units = read_json(source/'historical-map-project/data/units/military/liaodong.json')
    liaison_places = {p['id']:p for p in read_json(source/'historical-map-project/data/places/liaodong.json')}
    for entry in liaodong_units:
        place = liaison_places.get(entry.get('seatPlaceId'))
        if place and entry['name'].endswith(('卫','所')) and None not in (place.get('longitude'),place.get('latitude')):
            add_seat(entry['id'],entry['name'],'卫' if entry['name'].endswith('卫') else '千户所',
                     Point(place['longitude'],place['latitude']),'liaodong')
    for name,lon,lat in [('大兴县',116.414,39.939),('宛平县',116.383,39.933)]:
        if not any(r['n'] == name and r['nation'] == 'ming-p-jingshi' for r in county):
            add_seat('capital-'+name,name,'县',Point(lon,lat),'jingshi','京师城内的治所，位置为约略定位。')
    outline = project_geom(union_all(list(land.values()),grid_size=.00001)).simplify(.025,preserve_topology=True)
    return {'province':province,'city':city,'county':county,'outline':encode_area(outline)},land


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('water_source',type=Path,help='Extracted CHGIS V4 river tables')
    parser.add_argument('--elevation-cache',type=Path,default=Path(gettempdir())/'shanhe-atlas-elevation')
    parser.add_argument('--vectors-only',action='store_true')
    args = parser.parse_args()
    output = ROOT/'dist/data/ming-1582'
    (output/'terrain').mkdir(parents=True,exist_ok=True)
    admin,land = build_admin(args.source,args.source/'sheet-063.png',args.source/'region-073.png')
    save(output/'admin-boundaries.json',admin)
    water,lakes = build_water(args.water_source)
    save(output/'terrain/water.json',water)
    print({k:len(admin[k]) for k in ('province','city','county')},flush=True)
    if not args.vectors_only:
        areas = [(poly.bounds,[list(r.coords) for r in (poly.exterior,*poly.interiors)])
                 for geom in land.values() for poly in polygons(geom)]
        height = load_height((WEST,SOUTH,EAST,NORTH),30,5,args.elevation_cache)
        save_grid(output/'terrain/overview.hgt.gz',height.clip(min=0),WEST,NORTH,30,areas,lakes)


if __name__ == '__main__':
    main()
