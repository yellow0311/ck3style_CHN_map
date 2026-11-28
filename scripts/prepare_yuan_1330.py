"""Build the Yuan atlas from volume 7, PDF page 26, and CHGIS V6."""

import argparse
from collections import defaultdict
from pathlib import Path
from tempfile import gettempdir

import cv2
import numpy as np
from PIL import Image
from shapely import STRtree, make_valid, transform, union_all
from shapely.geometry import Point, Polygon, box, shape

from prepare_boundaries import save
from prepare_ming_1582 import snapshot, trace_curve
from prepare_qing_1820 import area_record, build_water, encode_area, polygonal, polygons, project_geom, xy
from prepare_terrain import load_height, save_grid, shape_reader, water_vectors


ROOT = Path(__file__).resolve().parents[1]
YEAR = 1330
GRID = (65, 10, 150, 75)
PROVINCES = {
    'zhongshu': ('中书省','中书省直辖地','7–10','#b78268'),
    'lingbei': ('岭北行省','行中书省','11–12','#85989f'),
    'liaoyang': ('辽阳行省','行中书省','13–14','#858e66'),
    'henan': ('河南江北行省','行中书省','15–16','#8e809d'),
    'shaanxi': ('陕西行省','行中书省','17–18','#c4a667'),
    'sichuan': ('四川行省','行中书省','19–20','#788e80'),
    'gansu': ('甘肃行省','行中书省','21','#b77975'),
    'western': ('哈密力、北庭、哈剌火州','西域辖地','22','#8b9e86'),
    'yunnan': ('云南行省','行中书省','23–26','#ad9473'),
    'jiangzhe': ('江浙行省','行中书省','27–29','#719aa7'),
    'jiangxi': ('江西行省','行中书省','30–31','#ba9271'),
    'huguang': ('湖广行省','行中书省','32–35','#7d9989'),
    'xuanzheng': ('宣政院辖地','宣政院辖地','36–37','#9c89a0'),
}

# The source polygons encode dates and names but omit their provincial parent.
# The groups below follow the provincial sheets and the Yuan geographical treatise.
GROUPS = {
    'zhongshu': {*range(220018,220437),221281},
    'henan': {97839,97849,97850,97887,97898,97914,97924,97926,97929,
              220442,220452,220456,220464,220470,220476,91109,91123,91108,91463,91193,91150},
    'shaanxi': {*range(220493,220576)},
    'gansu': {*range(220590,220638)},
    'sichuan': {*range(220651,220749)},
    'yunnan': {*range(220760,221022)},
    'huguang': {97866,97873,97882,97912,221035,221050,221073,221520,
                221162,221165,221167,221170,221172,221173,221181,221213,
                *range(93654,93682),*range(97301,97396),
                97700,97705,97708,97717,97723,*range(97815,97820)},
    'jiangzhe': {*range(90051,90581)},
    'jiangxi': {*range(97103,97280),*range(97722,97802)}-{97723},
}
PROVINCE_BY_ID = {ident:key for key,ids in GROUPS.items() for ident in ids}

# Additional locations on the smaller-scale provincial plates. Titles whose
# government seat remains uncertain stay out of the seat layer.
PLATE_SEATS = {
    'lingbei': [('和宁路','路',102.84,47.20)],
    'liaoyang': [('辽阳路','路',123.173,41.273),('广宁府路','路',121.794,41.596),
                 ('大宁路','路',119.162,41.572),('咸平府','府',124.111,42.786)],
    'western': [('哈密力','辖地',93.51,42.82),('北庭','辖地',89.22,44.09),
                ('哈剌火州','辖地',89.53,42.86)],
    'gansu': [('亦集乃路','路',101.14,41.76),('宁夏府路','路',106.24,38.48)],
    'xuanzheng': [('蔡巴万户','万户',91.21,29.63),('止贡万户','万户',92.21,30.09),
                  ('伯木古鲁万户','万户',91.79,29.30)],
}


def conic_registration(top, bottom, parallels):
    origins = {lon:(x,y) for lon,x,y in top}
    direction, offsets = [], []
    for lon,x,y in bottom:
        a,b = origins[lon]
        dx,dy = x-a,y-b
        direction.append((dy,-dx))
        offsets.append(dy*x-dx*y)
    apex_x,apex_y = np.linalg.lstsq(direction,offsets,rcond=None)[0]
    lon,x,y = np.array(top+bottom).T
    angle = np.arctan2(x-apex_x,y-apex_y)
    angular_scale,center = np.linalg.lstsq(np.column_stack((angle,np.ones_like(angle))),lon,rcond=None)[0]
    lat,x,y = np.array(parallels).T
    distance = np.hypot(x-apex_x,y-apex_y)
    latitude_scale,offset = np.linalg.lstsq(
        np.column_stack((np.log(np.tan(np.pi/4+np.radians(lat)/2)),np.ones_like(lat))),
        np.log(distance),rcond=None)[0]

    def project(px,py):
        x,y = px-apex_x,py-apex_y
        longitude = center+angular_scale*np.arctan2(x,y)
        latitude = np.degrees(2*np.arctan(np.exp((np.log(np.hypot(x,y))-offset)/latitude_scale))-np.pi/2)
        return longitude,latitude

    return project


def green_outline(image, footprint, minimum):
    red,green,blue = np.asarray(image,dtype=np.int16).transpose(2,0,1)
    ink = ((green-red > 12)&(green-blue > 13)&(red >= 120)&(green >= 160)).astype(np.uint8)*255
    frame = np.zeros_like(ink)
    cv2.fillPoly(frame,[np.asarray(footprint,dtype=np.int32)],255)
    ink = cv2.bitwise_and(ink,frame)
    joined = cv2.morphologyEx(ink,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(9,9)))
    contours,_ = cv2.findContours(cv2.medianBlur(joined,5),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    return [Polygon(cv2.approxPolyDP(part,1.05,True).reshape(-1,2))
            for part in contours if cv2.contourArea(part) >= minimum]


def atlas_outline(pdf_page, elevation_cache):
    scan = Image.open(pdf_page).transpose(Image.Transpose.ROTATE_90).convert('RGB').resize((3000,2120))
    main = scan.resize((1250,883))
    register = conic_registration(
        [(60,183,76),(70,297,76),(80,402,76),(90,503,76),(100,603,76),
         (110,698,77),(120,798,77),(130,900,77),(140,1011,77),(150,1129,78)],
        [(100,584,817),(110,754,817),(120,931,816)],
        [(50,80,109),(40,80,300),(30,80,492),(50,1163,110),(40,1163,304),(30,1163,495)])
    footprint = [(80,76),(1162,77),(1162,624),(1026,624),(1026,816),
                 (463,816),(463,676),(302,676),(302,576),(229,499),(80,499)]
    mainland = union_all([transform(p,register,interleaved=False) for p in green_outline(main,footprint,54)])

    inset = scan.crop((155,1182,737,1637))
    inset_register = conic_registration(
        [(80,181,24),(90,240,24),(100,302,24),(110,360,24),(120,423,24)],
        [(80,97,417),(90,198,417),(100,300,417),(110,399,417),(120,501,417)],
        [(70,35,27),(60,35,224),(55,35,324)])
    inset_frame = [(35,26),(394,26),(559,218),(559,417),(252,417),
                   (252,340),(35,340)]
    inset_land = union_all([transform(p,inset_register,interleaved=False)
                            for p in green_outline(inset,inset_frame,125)])
    # Where the two atlas frames overlap, retain the main plate's southern
    # exterior and the northern inset's coast rather than either frame edge.
    north = inset_land.intersection(box(65,53,150,75))
    coast = []
    for row in shape_reader('land',elevation_cache).iterShapeRecords():
        a,b,c,d = row.shape.bbox
        if c > 65 and a < 150 and d > 56 and b < 75:
            coast.append(make_valid(shape(row.shape.__geo_interface__)))
    land_above_frame = union_all(coast).intersection(box(65,56.5,150,75))
    outline = mainland.difference(box(65,56.5,150,75)).union(
        mainland.union(north).intersection(land_above_frame)).union(north.intersection(box(65,53,150,56.5)))
    return polygonal(outline.buffer(.026).buffer(-.026))


# Geographic guide lines for the parts with no CHGIS polygons. The shared
# boundaries within the CHGIS coverage are taken from the 1330 time slice.
GUIDES = {
    'western': [(89.3,46),(92.8,46.2),(94.4,44.2),(95.1,42.8),(94.4,41.9),
                (92.7,41.7),(92,40.4),(90.3,40.1),(87.5,39.1),(85,41),(85,44.3)],
    'gansu': [(90,45.3),(94,44.6),(96.2,43.4),(100.3,42.5),(103.7,42.3),
              (105.6,42.6),(107.6,41.5),(108.1,40.2),(106.9,38.1),(105.7,36.3),
              (103.6,35.1),(102.2,35.6),(99,37.1),(94,38.2),(89,39)],
    'xuanzheng': [(65,45),(89,45),(90,40.3),(94,39),(99,37.3),(102.8,35.4),
                  (104.1,33.6),(103.7,31.4),(102.1,28.8),(100.5,27.2),(98.2,27.1),
                  (95.5,27.6),(65,22)],
    'liaoyang': [(120.3,75),(119.4,62),(120.1,56),(119.5,52.7),(119.7,50.3),
                 (117.9,47.7),(118.6,45.9),(119.5,45),(118.5,43.2),(117.8,42.1),
                 (118.8,40.4),(120.9,38),(150,34),(150,75)],
    'zhongshu': [(106.9,42.1),(109.6,42.5),(112.2,43.6),(114.9,44.5),(117.9,45.1),
                 (119.1,43.5),(118.6,41.2),(119.5,39.7),(123,38.9),(126,33),(106,34)],
    'lingbei': [(65,75),(121,75),(119.4,62),(120.1,56),(119.5,52.7),(119.7,50.3),
                (117.9,47.7),(118.6,45.9),(119.5,45),(115.4,44.2),(111.8,42.7),
                (108.2,41.7),(105.9,42.3),(103,42.2),(97,43.15),(95,44.3),(65,47)],
    'yunnan': [(92,28.6),(98.8,27.1),(101.8,28),(104.3,27.9),(105.1,26.5),
               (105.8,25.5),(106.2,23.7),(103.9,22.1),(104,17),(93,16)],
}


def province_shapes(outline, divisions):
    province = {key:union_all([geom for _,geom in divisions[key]],grid_size=.00001) for key in PROVINCES}
    unassigned = outline.difference(union_all(list(province.values()),grid_size=.00001),grid_size=.00001)
    for key,points in GUIDES.items():
        mask = make_valid(Polygon(trace_curve(points+[points[0]])))
        province[key] = province[key].union(unassigned.intersection(mask),grid_size=.00001)
        unassigned = unassigned.difference(mask,grid_size=.00001)
    for part in polygons(unassigned):
        if part.area < .000015:
            continue
        # Attach thin scan/CHGIS differences to the bordering administrative area.
        neighbor = min(province,key=lambda key:(round(province[key].distance(part),4),
                                               -province[key].boundary.intersection(part.boundary).length))
        province[neighbor] = province[neighbor].union(part,grid_size=.00001)
    return {key:polygonal(geom) for key,geom in province.items()}


def build_admin(source, outline):
    divisions = defaultdict(list)
    rows = [(attrs,polygonal(geom)) for attrs,geom in snapshot(source/'dataverse-2966510.zip',YEAR)
            if attrs['TYPE_CH'] != '非政区国土']
    for attrs,geom in rows:
        key = PROVINCE_BY_ID[attrs['SYS_ID']]
        divisions[key].append((attrs,geom))
    land = province_shapes(outline,divisions)
    province,city,county = [],[],[]
    cities = []
    by_id = {}
    for key,(name,kind,pages,color) in PROVINCES.items():
        ident = 'yuan-p-'+key
        fields = {'color':color,'nation':ident,'sourcePage':pages}
        if key in GUIDES:
            fields['description'] = '图册所示概略范围。地方辖界按现有资料展示。'
        record = area_record(ident,name,kind,land[key],**fields)
        if key == 'zhongshu':
            record['x'],record['y'] = xy(112.1,39.3)
        province.append(record)
        labels = defaultdict(list)
        for attrs,geom in divisions[key]:
            labels[attrs['NAME_CH']].append((attrs,geom))
        for name,group in labels.items():
            attrs = group[0][0]
            geom = polygonal(union_all([g for _,g in group],grid_size=.00001))
            city_id = f'yuan-f-{attrs["SYS_ID"]}'
            item = area_record(city_id,name,'路' if name.endswith('路') else attrs['TYPE_CH'],geom,
                               p=ident,nation=ident,sourcePage=pages)
            city.append(item)
            cities.append(geom)
            by_id[city_id] = key
    province_ids = {r['id'] for r in province}
    city_index = STRtree(cities)
    original_cities = city[:]
    used = set()

    def seat(ident,name,kind,point,key=None,city_level=False,parent=None,description=None):
        ident = f'yuan-{"f" if city_level else "c"}-{ident}'
        if ident in used:
            return
        if not key:
            key = min(land,key=lambda k:land[k].distance(point))
        province_id = 'yuan-p-'+key
        if province_id not in province_ids or (parent is None and land[key].distance(point) > .4):
            return
        if not city_level and not parent:
            indexes = city_index.query(point,predicate='covered_by')
            candidates = [i for i in indexes if by_id[original_cities[i]['id']] == key]
            if candidates:
                parent = original_cities[min(candidates,key=lambda i:cities[i].area)]['id']
        x,y = xy(point.x,point.y)
        record = dict(id=ident,n=name,type=kind,seat=True,x=round(x,3),y=round(y,3),
                      p=parent or province_id,nation=province_id,sourcePage=PROVINCES[key][2])
        if description:
            record['description'] = description
        (city if city_level else county).append(record)
        used.add(ident)

    city_names = {r['n'] for r in city}
    for attrs,point in snapshot(source/'dataverse-2970286.zip',YEAR):
        name = attrs['NAME_CH']
        if name and name not in city_names:
            seat('point-'+str(attrs['SYS_ID']),name,attrs['TYPE_CH'],point,city_level=True)
    for key,places in PLATE_SEATS.items():
        for index,(name,kind,lon,lat) in enumerate(places):
            if not any(r['n'] == name for r in city):
                seat(f'{key}-{index}',name,kind,Point(lon,lat),key,city_level=True)
    for attrs,point in snapshot(source/'county-points.zip',YEAR):
        name = attrs['NAME_CH']
        if name and attrs['TYPE_CH']:
            seat(attrs['SYS_ID'],name,attrs['TYPE_CH'],point)
    city_by_name = {r['n']:r['id'] for r in city}
    for ident,name,lon in [('daxing','大兴县',116.425),('wanping','宛平县',116.363)]:
        if not any(r['n'] == name and r['nation'] == 'yuan-p-zhongshu' for r in county):
            seat(ident,name,'县',Point(lon,39.92),'zhongshu',parent=city_by_name['大都路'],
                 description='大都城内治所，位置为约略定位。')
    for name,kind,lon,lat,parent in [
        ('辽阳县','县',123.173,41.273,'辽阳路'),('盖州','州',122.35,40.402,'辽阳路'),
        ('大定县','县',119.162,41.572,'大宁路'),('兴中州','州',120.451,41.574,'大宁路')
    ]:
        if not any(r['n'] == name and r['nation'] == 'yuan-p-liaoyang' for r in county):
            seat(name,name,kind,Point(lon,lat),'liaoyang',parent=city_by_name[parent],
                 description='参照辽阳行省分图与《元史·地理志》，位置为约略定位。')
    seat('penghu','澎湖寨巡检司','巡检司',Point(119.576,23.566),'jiangzhe',parent=city_by_name['泉州路'],
         description='沿用江浙行省分图的岛上标注。巡检司设立年代有异说，点位为约略定位。')
    projected = project_geom(union_all(list(land.values()),grid_size=.00001)).simplify(.025,preserve_topology=True)
    return {'province':province,'city':city,'county':county,'outline':encode_area(projected)},land


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path,help='Directory with yuan-026.png and CHGIS V6 archives')
    parser.add_argument('water_source',type=Path,help='CHGIS V4 river and lake tables prepared for Qing')
    parser.add_argument('--elevation-cache',type=Path,default=Path(gettempdir())/'shanhe-atlas-elevation')
    parser.add_argument('--vectors-only',action='store_true')
    args = parser.parse_args()
    output = ROOT/'dist/data/yuan-1330'
    (output/'terrain').mkdir(parents=True,exist_ok=True)
    admin,land = build_admin(args.source,atlas_outline(args.source/'yuan-026.png',args.elevation_cache))
    save(output/'admin-boundaries.json',admin)
    water,lakes = build_water(args.water_source)
    water.extend(row for row in water_vectors(args.elevation_cache,(75,55,150,75),xy) if row[2][1] < xy(0,57)[1])
    save(output/'terrain/water.json',water)
    print({k:len(admin[k]) for k in ('province','city','county')},flush=True)
    if not args.vectors_only:
        areas = [(part.bounds,[list(r.coords) for r in (part.exterior,*part.interiors)])
                 for geom in land.values() for part in polygons(geom)]
        height = load_height(GRID,30,5,args.elevation_cache)
        save_grid(output/'terrain/overview.hgt.gz',height.clip(min=0),GRID[0],GRID[3],30,areas,lakes)


if __name__ == '__main__':
    main()
