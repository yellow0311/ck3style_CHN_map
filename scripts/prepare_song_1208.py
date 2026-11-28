"""Build the 1208 atlas from volume 6, PDF page 61, and CHGIS V6."""

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from tempfile import gettempdir

import cv2
import numpy as np
from PIL import Image
from shapely import STRtree, difference, intersection, make_valid, transform, union_all
from shapely.geometry import Point, box
from shapely.ops import linemerge

from prepare_boundaries import save
from prepare_ming_1582 import snapshot
from prepare_qing_1820 import area_record, lines, polygonal, polygons, project_geom, ring_svg, table, xy
from prepare_terrain import load_height, save_grid, water_vectors
from prepare_yuan_1330 import conic_registration
from song_1208_coast import refine_coasts
from song_1208_reference import (
    SONG_FRAME, align_guangnan, load_ccts, reference_guangnan, reference_jin_prefectures,
    reference_song_routes, reference_states, vectorize_coverage,
)
from song_1208_topology import build_topology
from song_1208_routes import FRONTIER_SEEDS, JIN_ROUTES, ROUTE_ALIASES, SONG_ROUTES


ROOT = Path(__file__).resolve().parents[1]
YEAR = 1208
GRID = (45, 10, 150, 60)
ROUTES = {'song':SONG_ROUTES,'jin':JIN_ROUTES}
PREFECTURE_ROUTES = {key:{name:route for route,(_,members) in definitions.items() for name in members.split()}
                     for key,definitions in ROUTES.items()}
STATES = {
    'song': ('南宋','政权','59–71','#ce9167','路级'),
    'jin': ('金','政权','46–58','#7f9cac','路级'),
    'mongol': ('大蒙古国','政权','44–45','#a2a879','有记载的治所'),
    'xia': ('西夏','政权','36–37','#877cad','府州治所'),
    'liao': ('西辽','政权','73–74','#c5a363','有记载的治所'),
    'tibet': ('吐蕃等部','诸部概略范围','40–41','#bd858e','有记载的治所'),
    'dali': ('大理','政权','75–77','#7da58b','府郡治所'),
}
STATE_ANCHORS = {
    'song':(111.9,26.6),'jin':(119.4,43.1),'xia':(101.7,39.1),
    'liao':(68.9,43.4),'tibet':(88.8,32.3),'dali':(99.1,24.2),'mongol':(100.7,48.5),
}

# Positions are approximate historical-site locations, grouped by the
# atlas plate for the polity. Later local names are available for search.
PLATE_SEATS = {
    'mongol': [
        ('大斡耳朵','汗廷',109.060,47.181,['成吉思汗大斡耳朵','阔迭额阿剌勒','阿布拉嘎','阿夫拉嘎']),
        ('斡难河源大会地','建国大会地',108.917,48.833,['斡难河','鄂嫩河','幹难河']),
        ('土兀剌河黑林','行营',107.180,47.835,['土拉河黑林','昭莫多','哈剌屯']),
    ],
    'xia': [
        ('中兴府','府',106.249,38.473,['兴庆府','兴庆','银川']),
        ('西平府','府',106.184,37.981,['灵州','灵武']),
        ('西凉府','府',102.636,37.929,['凉州','武威']),
        ('甘州','州',100.450,38.929,['张掖']),('肃州','州',98.511,39.743,['酒泉']),
        ('瓜州','州',96.182,40.260,['锁阳城']),('沙州','州',94.649,40.136,['敦煌']),
        ('黑水镇燕军司','军司',101.143,41.760,['黑水城','亦集乃']),
    ],
    'dali': [
        ('羊苴咩城','都城',100.160,25.700,['大理古城','大理城']),
        ('善阐府','府',102.711,25.041,['昆明']),('威楚府','府',101.545,25.034,['楚雄']),
        ('统矢府','府',101.241,25.507,['姚安']),('谋统府','府',100.176,26.560,['鹤庆']),
        ('永昌府','府',99.166,25.113,['保山']),('腾冲府','府',98.496,25.023,['腾越']),
        ('建昌府','府',102.267,27.896,['西昌']),('会川府','府',102.243,26.660,['会理']),
        ('石城郡','郡',103.796,25.498,['曲靖']),('秀山郡','郡',102.754,24.112,['通海']),
        ('河阳郡','郡',102.912,24.674,['澄江']),('东川郡','郡',103.298,26.418,['会泽']),
    ],
    'liao': [
        ('虎思斡耳朵','都城',75.250,42.747,['八剌沙衮','巴拉萨衮']),
        ('阿力麻里','属部城邑',80.450,44.165,['阿力麻里古城','霍城']),
        ('叶密立','城邑',83.628,46.532,['也迷里','额敏']),
        ('海押立','属部城邑',80.240,45.655,['海剌力']),
        ('可失哈耳','属部城邑',75.989,39.472,['可失哈儿','喀什','喀什噶尔']),
        ('斡端','属部城邑',79.914,37.111,['于阗','和田']),
        ('寻思干','属部城邑',66.959,39.662,['撒马尔罕','撒马尔干']),
        ('蒲华','属部城邑',64.421,39.775,['不花剌','布哈拉']),
        ('讹答剌','属部城邑',68.303,42.852,['讹打剌','讹答罗']),
        ('忽毡','属部城邑',69.622,40.286,['苦盏']),
        ('别失八里','属部城邑',89.221,44.089,['北庭']),
        ('火州','属部城邑',89.533,42.852,['高昌','哈剌火州']),
    ],
    'tibet': [
        ('逻些','城邑',91.132,29.653,['拉萨','惹萨']),
        ('萨斯迦','地方中心',88.018,28.908,['萨迦']),
        ('托林','古格地方中心',79.803,31.476,['古格','托林寺','札达']),
        ('普兰','地方治所',81.177,30.296,['普兰城']),
        ('桑耶','寺院中心',91.503,29.326,['桑耶寺']),
        ('楚布','寺院中心',90.587,29.659,['楚布寺']),
        ('止贡','寺院中心',92.219,30.113,['止贡寺']),
    ],
}

# The CHGIS time series has limited coverage around the Jin capital and
# east of the passes. These points come from the named seats in the Jin
# plates and the county lists in Jin shi 24.
JIN_SEATS = [
    ('大兴府','府',116.340,39.880,'46–47',['中都','中都路','金中都']),
    ('通州','州',116.657,39.910,'46–47',[]),('蓟州','州',117.402,40.044,'46–47',[]),
    ('檀州','州',116.850,40.373,'46–47',[]),('涿州','州',115.976,39.483,'46–47',[]),
    ('易州','州',115.496,39.350,'46–47',[]),
    ('会宁府','府',126.951,45.529,'48–49',['上京','上京会宁府']),
    ('隆州','州',125.172,44.433,'48–49',['黄龙府','农安']),
    ('咸平府','府',124.069,42.561,'48–49',['开原老城']),
    ('辽阳府','府',123.173,41.273,'48–49',['东京','东京辽阳府']),
    ('沈州','州',123.429,41.803,'48–49',['沈阳']),
    ('澄州','州',122.755,40.846,'48–49',['海城']),
    ('贵德州','州',123.925,41.887,'48–49',['高尔山']),
    ('盖州','州',122.351,40.402,'48–49',[]),('复州','州',121.722,39.758,'48–49',[]),
    ('来远州','州',124.458,40.188,'48–49',['来远军','九连城']),
    ('婆速府路','路',124.349,40.105,'48–49',[]),
    ('胡里改路','路',129.559,46.325,'48–49',['依兰']),
    ('蒲与路','路',126.281,48.044,'48–49',['蒲峪路']),
    ('恤品路','路',131.954,43.789,'48–49',['速频路','率宾']),
    ('大定府','府',119.162,41.572,'50',['北京大定府','辽中京']),
    ('临潢府','府',119.369,43.959,'50',['辽上京']),
    ('锦州','州',121.127,41.109,'50',[]),('义州','州',121.239,41.535,'50',[]),
    ('兴中府','府',120.452,41.579,'50',['朝阳']),
    ('广宁府','府',121.798,41.585,'50',['北镇']),
]
JIN_COUNTIES = {
    '大兴府': [
        ('大兴县',116.354,39.883),('宛平县',116.321,39.884),('漷阴县',116.780,39.772),
        ('香河县',117.003,39.760),('昌平县',116.231,40.221),('良乡县',116.141,39.735),
        ('永清县',116.491,39.326),('武清县',116.946,39.510),('宝坻县',117.302,39.726),
    ],
    '通州': [('潞县',116.660,39.905),('三河县',117.076,39.983)],
    '蓟州': [('渔阳县',117.402,40.044),('玉田县',117.747,39.879),('遵化县',117.966,40.190),
             ('平谷县',117.120,40.140)],
    '檀州': [('密云县',116.847,40.373)],
    '涿州': [('范阳县',115.976,39.483),('固安县',116.297,39.438)],
    '易州': [('易县',115.496,39.350),('涞水县',115.714,39.393)],
    '会宁府': [('会宁县',126.951,45.529),('曲江县',126.828,45.727),('宜春县',125.993,45.613)],
    '隆州': [('利涉县',125.172,44.433)],
    '咸平府': [('平郭县',124.069,42.561)],
    '辽阳府': [('辽阳县',123.173,41.273)],
    '沈州': [('乐郊县',123.429,41.803),('辽滨县',122.933,42.167),('章义县',123.122,41.670)],
    '澄州': [('临溟县',122.755,40.846),('析木县',122.900,40.726)],
    '贵德州': [('贵德县',123.925,41.887),('奉集县',123.544,41.572)],
    '盖州': [('建安县',122.351,40.402),('汤池县',122.625,40.530),('熊岳县',122.139,40.178)],
    '复州': [('永康县',121.722,39.758),('化成县',121.718,39.100)],
    '大定府': [('大定县',119.162,41.572)],
    '临潢府': [('临潢县',119.369,43.959)],
    '锦州': [('永乐县',121.127,41.109)],
    '义州': [('弘政县',121.239,41.535)],
    '兴中府': [('兴中县',120.452,41.579)],
    '广宁府': [('广宁县',121.798,41.585),('闾阳县',121.721,41.465)],
}

STATE_NOTES = {
    'song': '疆界依嘉定元年全图。府州、县治采用 1208 年有效记录。',
    'jin': '疆界依泰和八年全图。分图按大定二十九年绘制，府州、县治以 1208 年记录校核。',
    'mongol': '按 1208 年全图勾勒蒙古诸部统一后的范围。大斡耳朵为早期汗廷，其他点位标示史载营地和大会地点。',
    'xia': '疆界依 1208 年全图。较早的西夏分图供核对治所位置。',
    'liao': '疆界依 1208 年全图。部分治所为西辽属部或附庸城邑。',
    'tibet': '按全图描绘吐蕃诸部大致分布。地图标出有记载的地方治所与寺院中心。',
    'dali': '疆界依 1208 年全图，府、郡和都城按大理分图标出。',
}


PLATE_SCALE = 2.4


def plate_pixels(points):
    return np.rint(np.asarray(points)*PLATE_SCALE).astype(np.int32)


def plate_kernel(width):
    size = round(width*PLATE_SCALE)//2*2+1
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(size,size))


def plate_masks(page):
    image = Image.open(page).transpose(Image.Transpose.ROTATE_90).convert('RGB').resize((3000,2119))
    rgb = cv2.medianBlur(np.asarray(image),9)
    light,a,b = cv2.cvtColor(rgb,cv2.COLOR_RGB2LAB).transpose(2,0,1)
    frame = np.zeros(light.shape,np.uint8)
    cv2.fillPoly(frame,[plate_pixels([(94,65),(1171,66),(1171,612),(1035,612),(1035,807),
                                     (352,807),(352,626),(93,626)])],255)
    yellow = (b >= 143)&(a < 125)&(light > 182)
    specifications = {
        'song': ((b>=136)&(a>=125)&(a<=146)&(light>=172),
                 [(618,495),(875,487),(910,490),(948,570),(925,704),(759,777),(626,730),(622,613)],17),
        'jin': (yellow,[(682,343),(800,70),(985,65),(1083,68),(1143,200),(984,398),(940,431),
                        (883,505),(822,548),(678,527),(625,486),(711,440)],13),
        'mongol': ((a<=118)&(b>=128)&(b<=143)&(light>=181),
                   [(365,249),(390,168),(463,133),(492,86),(526,71),(621,73),(714,100),
                    (827,96),(883,213),(850,305),(787,363),(721,386),(666,367),(608,381),
                    (546,363),(480,309),(422,274)],13),
        'xia': ((b<=126)&(a>=124)&(a<=140)&(light>=177),
                [(493,402),(550,342),(615,337),(736,339),(747,410),(731,473),(638,501),(570,444)],15),
        'liao': (yellow,[(94,212),(298,198),(403,235),(531,277),(574,336),(538,401),(479,464),
                         (320,489),(186,449),(95,368)],11),
        'tibet': ((b<=131)&(a>=132)&(light>=184),
                  [(216,425),(329,454),(477,407),(559,396),(606,416),(660,478),(652,587),
                   (615,644),(550,663),(505,655),(369,645),(248,569)],13),
        'dali': ((b>=135)&(a<=120)&(light>=178),
                 [(501,610),(536,598),(620,593),(650,618),(697,696),(712,762),(673,783),(534,785),(494,693)],13),
    }
    for key,(pixels,area,close) in specifications.items():
        window = np.zeros(light.shape,np.uint8)
        cv2.fillPoly(window,[plate_pixels(area)],255)
        mask = (pixels.astype('uint8')*255)&window&frame
        closed = cv2.morphologyEx(mask,cv2.MORPH_CLOSE,plate_kernel(close))
        contours,_ = cv2.findContours(closed,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        component = max(contours,key=cv2.contourArea)
        filled = np.zeros_like(closed)
        cv2.drawContours(filled,[component],-1,255,-1)
        for extra in contours:
            if extra is component or cv2.contourArea(extra) <= 9*PLATE_SCALE**2:
                continue
            x,y,w,h = cv2.boundingRect(extra)
            if cv2.pointPolygonTest(component,(x+w/2,y+h/2),True) > -13*PLATE_SCALE:
                cv2.drawContours(filled,[extra],-1,255,-1)
        yield key,filled


def raster_geometry(mask):
    rectangles = []
    for y,row in enumerate(mask):
        changes = np.flatnonzero(np.diff(row.astype(np.int8),prepend=0,append=0))
        rectangles.extend(box(start,y,end,y+1) for start,end in zip(changes[::2],changes[1::2]))
    return union_all(rectangles)


def build_territories(page):
    masks = dict(plate_masks(page))
    distances = np.stack([cv2.distanceTransform(255-masks[k],cv2.DIST_L2,5) for k in STATES])
    nearest = np.argmin(distances,axis=0)
    combined = np.maximum.reduce(list(masks.values()))
    # Close gaps at the centerline of the atlas's purple border stroke.
    fill = cv2.morphologyEx(combined,cv2.MORPH_CLOSE,plate_kernel(11))
    _,components,stats,_ = cv2.connectedComponentsWithStats(255-fill,connectivity=8)
    small_holes = np.flatnonzero((stats[:,4] < 330*PLATE_SCALE**2)&
                                 (stats[:,0] > 90*PLATE_SCALE)&(stats[:,1] > 70*PLATE_SCALE))
    # The overprinted place names in western Sichuan interrupt the fill
    # along the border stroke on this plate.
    sx,sy = plate_pixels([643,570])
    sichuan_gap = components[sy,sx]
    if sichuan_gap and stats[sichuan_gap,cv2.CC_STAT_AREA] < 1900*PLATE_SCALE**2:
        small_holes = np.append(small_holes,sichuan_gap)
    fill[np.isin(components,small_holes)] = 255
    coverage = [raster_geometry((nearest==index)&(fill!=0)) for index in range(len(STATES))]
    registered = conic_registration(
        [(60,197.5,65),(70,311.7,65),(80,415.8,65),(90,516.7,65),(100,615.4,66),
         (110,702.1,66),(120,801.7,65),(130,905,65),(140,1015.4,65),(150,1133.3,65)],
        [(90,418,806),(100,594.2,806),(110,764.2,806),(120,942.9,806)],
        [(50,95,96.5),(40,95,291),(30,95,481),(50,1168,96),(40,1168,290),(30,1168,481)])
    def project_plate(x,y):
        return registered(x/PLATE_SCALE,y/PLATE_SCALE)
    return {key:polygonal(transform(geom,project_plate,interleaved=False))
            for key,geom in zip(STATES,vectorize_coverage(coverage,1.4))}


def seat_record(ident,name,kind,key,point,parent=None,**details):
    x,y = xy(point.x,point.y)
    nation = 'song1208-p-'+key
    details.setdefault('sourcePage',STATES[key][2])
    return dict(id=ident,n=name,type=kind,seat=True,x=round(x,3),y=round(y,3),
                p=parent or nation,nation=nation,**details)


def route_colors(geometries):
    # Ink, earth and mineral tones from the Ming and Qing plate palettes.
    palette = ['#c59169','#8eaa86','#889cad','#c9ac70','#a58ba5','#809e9c','#c68172',
               '#a79972','#8788af','#aec0c5','#b78489','#ad977b','#9ba989','#888aa0',
               '#a6a66f','#ba8c78']
    rgb = np.array([[[int(color[i:i+2],16) for i in (1,3,5)] for color in palette]],dtype=np.uint8)
    lab = cv2.cvtColor(rgb,cv2.COLOR_RGB2LAB)[0].astype(float)
    distances = np.linalg.norm(lab[:,None]-lab,axis=2)
    neighbors = [{j for j,b in enumerate(geometries) if j!=i and a.distance(b)<.002}
                 for i,a in enumerate(geometries)]
    colors,used = {},Counter()
    remaining = set(range(len(geometries)))
    while remaining:
        index = max(remaining,key=lambda i:(sum(j in colors for j in neighbors[i]),len(neighbors[i]),-i))
        adjacent = [colors[j] for j in neighbors[index] if j in colors]
        def score(candidate):
            contrast = min((distances[candidate,other] for other in adjacent),default=75)
            return min(contrast,53)-14*used[candidate]
        color = max(range(len(palette)),key=score)
        colors[index] = color
        used[color] += 1
        remaining.remove(index)
    return [palette[colors[i]] for i in range(len(geometries))]


def build_routes(key,territory,prefectures,guides,detail_routes,guangnan):
    routes = ROUTES[key]
    memberships = PREFECTURE_ROUTES[key]
    west,south,east,north = territory.bounds
    rate = 130
    width,height = int(np.ceil((east-west)*rate))+1,int(np.ceil((north-south)*rate))+1
    shape = (height,width)

    def pixels(points):
        coords = np.asarray(points)
        return np.rint((coords-[west,south])*rate).astype(np.int32)

    def paint(mask,geometry):
        for area in polygons(geometry):
            cv2.fillPoly(mask,[pixels(area.exterior.coords)],255)
            for hole in area.interiors:
                cv2.fillPoly(mask,[pixels(hole.coords)],0)

    known = {name:np.zeros(shape,np.uint8) for name in routes}
    mapped_areas = {name:np.zeros(shape,np.uint8) for name in routes}
    reference_areas = {name:np.zeros(shape,np.uint8) for name in routes}
    surveyed = defaultdict(list)
    for (state,name),(record,geometry) in prefectures.items():
        route = memberships.get(name) if state == key else None
        if not route:
            continue
        if geometry is not None:
            paint(mapped_areas[route],geometry)
            surveyed[route].append(geometry)
        else:
            point = [record['x']/14+62,57-record['y']/17]
            cv2.circle(known[route],tuple(pixels([point])[0]),2,255,-1)
    for name,geometry in guides.items():
        paint(reference_areas[name],geometry.intersection(territory))
    if detail_routes:
        resolved = np.maximum.reduce([reference_areas[name] for name in detail_routes])
        for name in routes:
            mapped_areas[name][resolved!=0] = 0
            if name not in detail_routes:
                reference_areas[name][resolved!=0] = 0
    # Use known prefectural polygons where the registered linework is
    # incomplete and where Jin's supporting 1200 geography disagrees.
    exact = np.maximum.reduce(list(mapped_areas.values()))
    for name in routes:
        reference_areas[name][exact!=0] = 0
    for name,points in FRONTIER_SEEDS.items():
        if name in known:
            for point in pixels(points):
                cv2.circle(known[name],tuple(point),2,255,-1)

    mask = np.zeros(shape,np.uint8)
    paint(mask,territory)
    nearest = np.zeros(shape,np.uint8)
    best = np.full(shape,np.inf,np.float32)
    for index,name in enumerate(routes):
        seeds = cv2.bitwise_or(known[name],cv2.bitwise_or(mapped_areas[name],reference_areas[name]))
        if not seeds.any():
            raise ValueError(f'Missing geography for {name}')
        distance = cv2.distanceTransform(255-seeds,cv2.DIST_L2,5)
        wins = distance < best
        best[wins] = distance[wins]
        nearest[wins] = index
    raster = [raster_geometry((nearest==i)&(mask!=0)) for i in range(len(routes))]
    geometries = [polygonal(transform(geom,lambda x,y:(x/rate+west,y/rate+south),interleaved=False)
                            .intersection(territory)) for geom in vectorize_coverage(raster,1.55)]
    # The historic national outline is more detailed than the raster cells.
    # Attach the thin remainder along its edge to the adjoining route.
    missing = polygonal(territory.difference(union_all(geometries)))
    for part in polygons(missing):
        nearest_index = min(range(len(geometries)),key=lambda i:geometries[i].distance(part.representative_point()))
        geometries[nearest_index] = polygonal(geometries[nearest_index].union(part))
    # Preserve original CHGIS 1208 vector boundaries for BOTH Song and Jin
    # wherever prefectural polygons are available, and Hartwell 1200 vectors
    # for Jin gaps. The high-res smoothed raster partition fills only the
    # remaining unmapped areas.
    precision = .00001
    mapped = {name:polygonal(intersection(polygonal(union_all(parts,grid_size=precision)),territory,grid_size=precision))
              for name,parts in surveyed.items() if parts}
    filled = polygonal(union_all(list(mapped.values()),grid_size=precision)) if mapped else polygonal(box(0,0,0,0))
    if key == 'jin' and guides:
        for name in routes:
            if name in guides:
                supplement = polygonal(intersection(guides[name],territory,grid_size=precision))
                supplement = polygonal(difference(supplement,filled,grid_size=precision))
                if not supplement.is_empty:
                    mapped[name] = polygonal(union_all([mapped[name],supplement],grid_size=precision)) if name in mapped else supplement
                    filled = polygonal(union_all([filled,supplement],grid_size=precision))
    if not filled.is_empty:
        geometries = [polygonal(union_all([polygonal(difference(geometry,filled,grid_size=precision)),mapped[name]],
                                         grid_size=precision)) if name in mapped
                      else polygonal(difference(geometry,filled,grid_size=precision))
                      for name,geometry in zip(routes,geometries)]
    if key=='song' and guangnan:
        names = list(routes)
        west,east = names.index('广南西路'),names.index('广南东路')
        geometries[west],geometries[east] = align_guangnan(geometries[west],geometries[east],guangnan)
    colors = route_colors(geometries)
    output = {}
    nation = 'song1208-p-'+key
    for index,((name,(pages,_)),geometry) in enumerate(zip(routes.items(),geometries)):
        ident = f'song1208-r-{key}-{index}'
        description = '路界结合配准图、府州边界和治所复原，史料不足之处为概略线。'
        if name == '临潢府路':
            description += '此处按《金代行政区划史》的泰和八年条目单列。《金史·地理志》将临潢府列于北京路。'
        info = area_record(ident,name,'路',geometry,p=nation,nation=nation,sourcePage=pages,
                           aliases=ROUTE_ALIASES.get(name,[]),color=colors[index],description=description)
        output[name] = info,geometry
    return output


def build_admin(land, source, route_guides, jin_prefectures, detail_routes, guangnan=None):
    province,city,county = [],[],[]
    eastern = {key:land[key] for key in ('song','jin')}
    joined_east = union_all(list(eastern.values()))
    groups = defaultdict(list)
    def listed_state(name):
        matches = [key for key in eastern if name in PREFECTURE_ROUTES[key]]
        return matches[0] if len(matches) == 1 else None

    rows = snapshot(source/'dataverse-2966510.zip',YEAR)
    for attrs,area in rows:
        if attrs['TYPE_CH'] == '非政区国土':
            continue
        area = polygonal(area)
        key = listed_state(attrs['NAME_CH']) or max(eastern,key=lambda side:area.intersection(eastern[side]).area)
        clipped = polygonal(area.intersection(eastern[key]))
        if not clipped.is_empty:
            groups[key,attrs['NAME_CH']].append((attrs,clipped))

    city_shapes,city_keys,city_ids = [],[],[]
    city_by_name = {}
    for (key,name),entries in groups.items():
        attrs = entries[0][0]
        geom = polygonal(union_all([shape for _,shape in entries],grid_size=.00001))
        ident = f'song1208-f-{attrs["SYS_ID"]}'
        nation = 'song1208-p-'+key
        record = area_record(ident,name,attrs['TYPE_CH'],geom,p=nation,nation=nation,sourcePage=STATES[key][2])
        city.append(record)
        city_shapes.append(geom)
        city_keys.append(key)
        city_ids.append(ident)
        city_by_name[key,name] = record,geom
    index = STRtree(city_shapes)

    def eastern_state(point):
        key = min(eastern,key=lambda side:eastern[side].distance(point))
        if eastern[key].distance(point) > .38:
            return None
        other = min(land,key=lambda side:land[side].distance(point))
        if other not in eastern and land[other].covers(point):
            return None
        return key

    for attrs,point in snapshot(source/'dataverse-2970286.zip',YEAR):
        name = attrs['NAME_CH']
        key = listed_state(name) or eastern_state(point)
        if not key or not name:
            continue
        if (key,name) in city_by_name:
            record,geom = city_by_name[key,name]
            if geom is not None and geom.covers(point):
                record['x'],record['y'] = (round(value,3) for value in xy(point.x,point.y))
        else:
            record = seat_record(f'song1208-f-p{attrs["SYS_ID"]}',name,attrs['TYPE_CH'],key,point)
            city.append(record)
            city_by_name[key,name] = record,None
    points = {key:[] for key in eastern}
    for record in city:
        key = record['nation'].split('-')[-1]
        point = Point(record['x']/14+62,57-record['y']/17)
        points[key].append((record,point))
    for i,(name,kind,lon,lat,pages,aliases) in enumerate(JIN_SEATS):
        key = ('jin',name)
        if key in city_by_name:
            city_by_name[key][0].setdefault('aliases',aliases)
            continue
        record = seat_record(f'song1208-f-jin-{i}',name,kind,'jin',Point(lon,lat),aliases=aliases,
                             sourcePage=pages,description='参照金代分图与《金史·地理志》，点位为约略定位。')
        city.append(record)
        city_by_name[key] = record,None
        points['jin'].append((record,Point(lon,lat)))
    for attrs,point in snapshot(source/'county-points.zip',YEAR):
        name,kind = attrs['NAME_CH'],attrs['TYPE_CH']
        if not name or not kind or joined_east.distance(point) > .25:
            continue
        key = eastern_state(point)
        if not key:
            continue
        parents = [i for i in index.query(point,predicate='covered_by') if city_keys[i] == key]
        details = {}
        if parents:
            parent = city_ids[min(parents,key=lambda i:city_shapes[i].area)]
        else:
            closest,anchor = min(points[key],key=lambda entry:entry[1].distance(point))
            parent = closest['id'] if anchor.distance(point) < 1.0 else None
            if parent:
                details['description'] = '府州关联按治所位置推定。'
        county.append(seat_record(f'song1208-c-{attrs["SYS_ID"]}',name,kind,key,point,parent=parent,**details))

    registered = defaultdict(list)
    for record in county:
        if record['nation'] == 'song1208-p-jin':
            registered[record['n']].append(record)
    for parent,places in JIN_COUNTIES.items():
        prefecture,_ = city_by_name['jin',parent]
        for offset,(name,lon,lat) in enumerate(places):
            x,y = xy(lon,lat)
            existing = next((r for r in registered[name] if abs(r['x']-x) < 3 and abs(r['y']-y) < 3),None)
            if existing:
                existing.update(p=prefecture['id'],sourcePage=prefecture['sourcePage'])
                existing.pop('description',None)
                continue
            county.append(seat_record(f'{prefecture["id"]}-c{offset}',name,'县','jin',Point(lon,lat),
                                      parent=prefecture['id'],sourcePage=prefecture['sourcePage'],
                                      description='参照金代分图与《金史·地理志》，点位为约略定位。'))

    for key,places in PLATE_SEATS.items():
        for offset,(name,kind,lon,lat,aliases) in enumerate(places):
            city.append(seat_record(f'song1208-f-{key}-{offset}',name,kind,key,Point(lon,lat),
                                    aliases=aliases,description='参照图册及历史地名资料，点位为约略定位。'))
    route_records = {key:build_routes(key,territory,city_by_name,route_guides.get(key,{}),
                                    detail_routes if key=='song' else (),guangnan)
                     for key,territory in eastern.items()}
    jin_precincts = union_all([geometry for (key,_),(record,geometry) in city_by_name.items()
                              if key=='jin' and geometry is not None])
    final_prefectures = {}
    for (key,name),(record,geometry) in city_by_name.items():
        routes = route_records[key]
        route = PREFECTURE_ROUTES[key].get(name)
        if not route:
            point = Point(record['x']/14+62,57-record['y']/17)
            route = min(routes,key=lambda r:routes[r][1].distance(point))
            record['description'] = '所属路按图册地望及现有路界推定。'
        route_area,route_shape = routes[route]
        record['p'] = route_area['id']
        if geometry is None and key == 'jin' and name in jin_prefectures:
            point = Point(record['x']/14+62,57-record['y']/17)
            candidate = polygonal(jin_prefectures[name].intersection(route_shape).difference(jin_precincts))
            if candidate.area >= .006 and candidate.distance(point) < .23:
                geometry = candidate
                record['description'] = '治所及隶属按 1208 年口径展示，辖界参考 Hartwell 1200 年府州范围。'
        if geometry is not None:
            final_prefectures[record['id']] = geometry
    for record in county:
        if record['p'] != record['nation']:
            continue
        key = record['nation'].rsplit('-',1)[1]
        point = Point(record['x']/14+62,57-record['y']/17)
        route,_ = min(route_records[key].values(),key=lambda r:r[1].distance(point))
        record['p'] = route['id']
        record['description'] = '所属路按地望推定，具体府州待核。'
    for key,(name,kind,pages,color,level) in STATES.items():
        ident = 'song1208-p-'+key
        item = area_record(ident,name,kind,land[key],nation=ident,color=color,sourcePage='44–45',
                           detailLevel=level,description=STATE_NOTES[key])
        point = Point(STATE_ANCHORS[key])
        if land[key].covers(point):
            item['x'],item['y'] = xy(point.x,point.y)
        if key == 'tibet':
            item['aliases'] = ['吐蕃','吐蕃诸部']
        if key == 'mongol':
            item['aliases'] = ['蒙古','蒙古国']
        province.append(item)
    subdivisions = [entry for state in route_records.values() for entry in state.values()]
    route = [record for record,_ in subdivisions]
    outline,linework = build_topology(province,route,city,
        {'song1208-p-'+key:geometry for key,geometry in land.items()},
        {record['id']:geometry for record,geometry in subdivisions},final_prefectures)
    return {'province':province,'route':route,'city':city,'county':county,'outline':outline,'linework':linework}


SONG_TRUNK_RIVERS = {
    '黄河','长江','大江','金沙江','通天河','本鲁乌苏河(通天河)','淮河','淮水',
    '汉水','汉江','湘江','赣江','西江','郁江','黔江','浔江','黑龙江',
    '黑龙江(萨哈连乌拉河)','松花江','嫩江','辽河','西辽河','鸭绿江','乌苏哩江',
    '乌苏里江','精奇哩江','雅鲁藏布江','澜沧江','怒江','塔里木河','伊犁河',
    '额尔齐斯河','运河','克鲁伦河(胪胊河)','鄂尔坤河','色楞格河','斡难河',
    '土拉河','土兀剌河','贝克穆河',
}
SONG_PRIMARY_TRIBUTARIES = {
    '嘉陵江','岷江','雅龙江','大渡河','乌江','沅江','资水','澧水','渭河','渭水',
    '汾河','洛河','洛水','泾水','泾河','沁水','沁河','漳河','滹沱河','白河',
    '永定河','滦河','大凌河','闽江','钱塘江','浙江','瓯江','韩江','北江','东江',
    '桂江','柳江','叶尔羌河','和阗河','阿克苏河','弱水','疏勒河','洮河','湟水',
    '大通河','颖河','颍水','涡河','泗水','大清河','兴衮河','拉楚河','喀尔古讷河',
    '纽勒们河',
}


def build_song_water(source, elevation_cache):
    """Build a hierarchically filtered water network for 1208 terrain readability."""
    water, lakes = [], []
    for _, geom in table(source, 'Layer1820_River_Pgn'):
        for part in polygons(make_valid(geom)):
            if part.area < .0015:
                continue
            lakes.append((part.bounds, [list(r.coords) for r in (part.exterior, *part.interiors)]))
            layer = project_geom(part).simplify(.035, preserve_topology=True)
            g = ''.join(ring_svg(r.coords, True) for r in (layer.exterior, *layer.interiors))
            water.append(['lake', max(1, 6 - int(layer.area ** .28 * 2)), [round(v, 2) for v in layer.bounds], g])
    named = defaultdict(list)
    unnamed = []
    for attrs, geom in table(source, 'River_Line_Layer1820'):
        name = attrs['Character_name'].strip()
        if name:
            named[name].extend(lines(geom))
        else:
            unnamed.extend(lines(geom))
    for name, group in named.items():
        merged = [project_geom(line).simplify(.04) for line in lines(linemerge(group))]
        total_len = sum(g.length for g in merged)
        is_trunk = name in SONG_TRUNK_RIVERS
        is_primary = name in SONG_PRIMARY_TRIBUTARIES
        if not is_trunk and not is_primary and total_len < 32:
            continue
        for geom in merged:
            if is_trunk:
                if geom.length < 4:
                    continue
                rank = 1
            elif is_primary or total_len >= 65:
                if geom.length < 10:
                    continue
                rank = 3
            else:
                if geom.length < 16:
                    continue
                rank = 6
            water.append(['river', rank, [round(v, 2) for v in geom.bounds], ring_svg(geom.coords)])
    for line in lines(linemerge(unnamed)):
        geom = project_geom(line).simplify(.045)
        if geom.length >= 42:
            water.append(['river', 3 if geom.length >= 75 else 6,
                          [round(v, 2) for v in geom.bounds], ring_svg(geom.coords)])
    supplement = water_vectors(elevation_cache, (45, 22, 121, 60), xy)
    water.extend(row for row in supplement
                 if (row[0] == 'lake' or row[1] <= 4)
                 and (row[2][2] < xy(88, 0)[0] or row[2][3] < xy(0, 45)[1]))
    return water, lakes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('page',type=Path,help='Portrait PNG render of PDF page 61')
    parser.add_argument('chgis',type=Path,help='Directory with CHGIS V6 archives used for Yuan')
    parser.add_argument('water_source',type=Path,help='CHGIS V4 water tables')
    parser.add_argument('--ccts-tiles',type=Path,help='Directory containing the CCTS ad1208 zoom 6 reference tiles')
    parser.add_argument('--jin-reference',type=Path,help='Hartwell 1200 Jin prefecture GeoJSON in WGS84')
    parser.add_argument('--elevation-cache',type=Path,default=Path(gettempdir())/'shanhe-atlas-elevation')
    parser.add_argument('--vectors-only',action='store_true')
    args = parser.parse_args()
    output = ROOT/'dist/data/song-1208'
    (output/'terrain').mkdir(parents=True,exist_ok=True)
    land = build_territories(args.page)
    print('Reading the historical atlas boundary plate',flush=True)
    route_guides = {}
    jin_prefectures = {}
    detail_routes = {}
    guangnan = None
    if args.ccts_tiles:
        ink,reference_land = load_ccts(args.ccts_tiles)
        land = reference_states(ink,reference_land,STATE_ANCHORS,land,raster_geometry)
        route_guides['song'] = reference_song_routes(ink,reference_land,raster_geometry)
        if any(args.ccts_tiles.glob('ccts-7-*.png')):
            ink,reference_land = load_ccts(args.ccts_tiles,SONG_FRAME)
            detail_routes = reference_song_routes(ink,reference_land,raster_geometry,SONG_FRAME)
            route_guides['song'].update(detail_routes)
            print('Higher resolution Song route outlines:',len(detail_routes),flush=True)
        if any(args.ccts_tiles.glob('ccts-9-*.png')):
            guangnan = reference_guangnan(args.ccts_tiles,raster_geometry)
        print('Registered 1208 territories and Song route reference',flush=True)
    if args.jin_reference:
        route_guides['jin'],jin_prefectures = reference_jin_prefectures(args.jin_reference,PREFECTURE_ROUTES['jin'])
    land = refine_coasts(land,ROOT,args.elevation_cache)
    print('Refined coastlines and islands',flush=True)
    admin = build_admin(land,args.chgis,route_guides,jin_prefectures,detail_routes,guangnan)
    save(output/'admin-boundaries.json',admin)
    water,lakes = build_song_water(args.water_source,args.elevation_cache)
    save(output/'terrain/water.json',water)
    for state in admin['province']:
        counts = [sum(row['nation']==state['id'] for row in admin[k]) for k in ('city','county')]
        print(state['n'],*counts,flush=True)
    if not args.vectors_only:
        areas = [(part.bounds,[list(r.coords) for r in (part.exterior,*part.interiors)])
                 for geom in land.values() for part in polygons(geom)]
        height = load_height(GRID,30,5,args.elevation_cache)
        save_grid(output/'terrain/overview.hgt.gz',height.clip(min=0),GRID[0],GRID[3],30,areas,lakes)


if __name__ == '__main__':
    main()
