"""Registered boundary references for the 1208 coverage reconstruction."""

import json
from collections import defaultdict

import cv2
import numpy as np
from PIL import Image
from shapely import coverage_is_valid, coverage_simplify, difference, intersection, make_valid, transform, union_all
from shapely.geometry import MultiPolygon, Polygon, shape

from prepare_qing_1820 import polygonal, polygons


SONG_CONTROL_POINTS = {
    '两浙西路':(119.92,30.64),'两浙东路':(120.56,29.55),
    '淮南东路':(119.42,33.32),'淮南西路':(117.03,31.78),
    '江南东路':(118.63,30.98),'江南西路':(115.42,28.6),
    '荆湖北路':(112.16,30.52),'荆湖南路':(112.8,27.9),
    '京西南路':(111.87,32.16),'福建路':(118,26.21),
    '成都府路':(103.87,30.65),'潼川府路':(105.07,30.8),
    '利州东路':(106.9,32.91),'利州西路':(105.35,33.95),
    '夔州路':(108.72,30.95),'广南东路':(113.6,23.22),'广南西路':(109.66,24.52),
}
OVERVIEW_FRAME = (6,42,18,16,11)
SONG_FRAME = (7,99,50,10,8)
GUANGNAN_FRAME = (9,411,216,8,10)


def to_pixels(lon,lat,frame=OVERVIEW_FRAME):
    zoom,west,north,*_ = frame
    world = 2**zoom*256
    x = (np.asarray(lon)+180)/360*world-west*256
    y = (.5-np.arcsinh(np.tan(np.radians(lat)))/(2*np.pi))*world-north*256
    return np.column_stack((x,y)).round().astype(np.int32)


def from_pixels(x,y,frame=OVERVIEW_FRAME):
    zoom,west,north,*_ = frame
    world = 2**zoom*256
    lon = (x+west*256)/world*360-180
    lat = np.degrees(np.arctan(np.sinh(np.pi*(1-2*(y+north*256)/world))))
    return lon,lat


def load_ccts(directory,frame=OVERVIEW_FRAME):
    zoom,west,north,width,height = frame
    images = np.zeros((height*256,width*256,4),np.uint8)
    for x in range(west,west+width):
        for y in range(north,north+height):
            tile = directory/f'ccts-{zoom}-{x}-{y}.png'
            x0,y0 = (x-west)*256,(y-north)*256
            if tile.exists():
                with Image.open(tile) as image:
                    rgba = image.convert('RGBA')
            elif zoom>6:
                fallback = 2**(zoom-6)
                with Image.open(directory/f'ccts-6-{x//fallback}-{y//fallback}.png') as image:
                    side = 256//fallback
                    ax,ay = x%fallback*side,y%fallback*side
                    rgba = image.convert('RGBA').crop((ax,ay,ax+side,ay+side)).resize((256,256),Image.Resampling.NEAREST)
            else:
                raise FileNotFoundError(f'Missing CCTS reference tile {tile.name}')
            images[y0:y0+256,x0:x0+256] = np.asarray(rgba)
    red,green,blue,alpha = images.transpose(2,0,1)
    return (red>=145)&(green>=90)&(green<190)&(blue<=40)&(alpha>100),alpha>100


def component_guides(ink,land,kernel,controls,frame=OVERVIEW_FRAME,strict=True):
    closed = cv2.morphologyEx(ink.astype('uint8'),cv2.MORPH_CLOSE,
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(kernel,kernel)))
    strokes = cv2.dilate(closed,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3)))
    _,labels,stats,_ = cv2.connectedComponentsWithStats((land&(strokes==0)).astype('uint8'),connectivity=4)
    owners = defaultdict(set)
    for name,points in controls.items():
        for lon,lat in points:
            x,y = to_pixels([lon],[lat],frame)[0]
            radius = 3 if strict else 15
            pixels = labels[y-radius:y+radius+1,x-radius:x+radius+1].ravel()
            if not pixels.any():
                if strict:
                    raise ValueError(f'Missing reference close to {name} at {(lon,lat)}')
                continue
            component = int(np.bincount(pixels[pixels!=0]).argmax())
            owners[component].add(name)
    if strict and any(len(names)>1 for names in owners.values()):
        raise ValueError('A reference cell joins two administrative regions')
    known = {cell:next(iter(names)) for cell,names in owners.items() if len(names)==1}
    return labels,stats,known


def polygon_mask(geometry,mask,value):
    for part in sorted(polygons(geometry),key=lambda area:area.area,reverse=True):
        ring = np.asarray(part.exterior.coords)
        cv2.fillPoly(mask,[to_pixels(ring[:,0],ring[:,1])],value)
        for interior in part.interiors:
            ring = np.asarray(interior.coords)
            cv2.fillPoly(mask,[to_pixels(ring[:,0],ring[:,1])],0)


def _chaikin_open(pts, passes):
    pts = list(pts)
    for _ in range(passes):
        if len(pts) < 3:
            break
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            out.append((0.75*a[0]+0.25*b[0], 0.75*a[1]+0.25*b[1]))
            out.append((0.25*a[0]+0.75*b[0], 0.25*a[1]+0.75*b[1]))
        out.append(pts[-1])
        pts = out
    return pts


def _chaikin_closed(pts, passes):
    pts = list(pts[:-1])
    for _ in range(passes):
        if len(pts) < 3:
            break
        out = []
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i+1)%n]
            out.append((0.75*a[0]+0.25*b[0], 0.75*a[1]+0.25*b[1]))
            out.append((0.25*a[0]+0.75*b[0], 0.25*a[1]+0.75*b[1]))
        pts = out
    return pts + [pts[0]]


def _smooth_coverage_arcs(parts, passes):
    adjacent = defaultdict(set)
    for group in parts:
        for exterior, holes in group:
            for ring in [exterior, *holes]:
                for a, b in zip(ring, ring[1:]):
                    if a != b:
                        adjacent[a].add(b)
                        adjacent[b].add(a)
    junctions = {pt for pt, nbrs in adjacent.items() if len(nbrs) != 2}
    arc_cache = {}

    def smooth_arc(arc):
        key = tuple(arc)
        rev = tuple(reversed(arc))
        if key in arc_cache:
            return arc_cache[key]
        if rev in arc_cache:
            return list(reversed(arc_cache[rev]))
        if key <= rev:
            res = _chaikin_open(arc, passes)
            arc_cache[key] = res
            return res
        res = _chaikin_open(list(rev), passes)
        arc_cache[rev] = res
        return list(reversed(res))

    def smooth_ring(ring, allow_closed=True):
        pts = list(ring[:-1])
        j_indices = [i for i, pt in enumerate(pts) if pt in junctions]
        if not j_indices:
            return _chaikin_closed(ring, passes) if (allow_closed and len(pts) >= 5) else list(ring)
        first = j_indices[0]
        ordered = pts[first:] + pts[:first] + [pts[first]]
        result = []
        start = 0
        for i in range(1, len(ordered)):
            if ordered[i] in junctions:
                arc = ordered[start:i+1]
                seg = smooth_arc(arc) if len(arc) >= 4 else list(arc)
                if result:
                    result.extend(seg[1:])
                else:
                    result.extend(seg)
                start = i
        if result[0] != result[-1]:
            result.append(result[0])
        return result

    return [MultiPolygon([
        Polygon(
            smooth_ring(outer, allow_closed=Polygon(outer).area >= 25),
            [smooth_ring(ring, allow_closed=Polygon(ring).area >= 25) for ring in holes]
        )
        for outer, holes in group
    ]) for group in parts]


def vectorize_coverage(coverage, tolerance):
    """Smooth pixel-grid boundaries via topology-preserving shared-arc Chaikin subdivision."""
    simplified = coverage_simplify(coverage, tolerance * 0.65)
    parts = [[(list(p.exterior.coords), [list(r.coords) for r in p.interiors])
              for p in polygons(geometry)] for geometry in simplified]
    for passes in (2, 1):
        try:
            refined = _smooth_coverage_arcs(parts, passes)
            if all(geometry.is_valid for geometry in refined) and coverage_is_valid(refined):
                return coverage_simplify(refined, tolerance * 0.14)
        except Exception:
            continue
    return simplified


def reference_states(ink,land,anchors,approximate,raster_geometry):
    controls = {key:[point] for key,point in anchors.items() if key!='song'}
    controls['song'] = list(SONG_CONTROL_POINTS.values())
    labels,stats,known = component_guides(ink,land,7,controls)
    names = list(anchors)
    source_class = {key:index+1 for index,key in enumerate(names)}
    coarse = np.zeros(labels.shape,np.uint8)
    for key,shape in approximate.items():
        polygon_mask(shape,coarse,source_class[key])
    lookup = np.zeros(len(stats),np.uint8)
    for index,name in known.items():
        lookup[index] = source_class[name]
    counts = np.bincount((labels*(len(names)+1)+coarse).ravel(),
                         minlength=len(stats)*(len(names)+1)).reshape(-1,len(names)+1)
    for index,values in enumerate(counts[1:],1):
        if lookup[index] or stats[index,cv2.CC_STAT_AREA] < 2:
            continue
        owner = 1+int(np.argmax(values[1:]))
        if values[owner] >= .20*stats[index,cv2.CC_STAT_AREA]:
            lookup[index] = owner
    marked = lookup[labels]
    # Allocate the shared stroke once, to the nearer group. Clip to the
    # actual drawn outline and exclude components unrelated to the seven states.
    distance,nearest = cv2.distanceTransformWithLabels((marked==0).astype('uint8'),cv2.DIST_L2,5,
                                                       labelType=cv2.DIST_LABEL_PIXEL)
    owner = np.zeros(nearest.max()+1,np.uint8)
    seeds = marked>0
    owner[nearest[seeds]] = marked[seeds]
    coverage = np.where(land & ((marked>0)|((labels==0)&(distance<13))),owner[nearest],0)
    masks = [raster_geometry(coverage==source_class[key]) for key in names]
    return {key:polygonal(transform(geometry,from_pixels,interleaved=False))
            for key,geometry in zip(names,vectorize_coverage(masks,1.2))}


def reference_song_routes(ink,land,raster_geometry,frame=OVERVIEW_FRAME):
    points = {name:[point] for name,point in SONG_CONTROL_POINTS.items()}
    overview = frame == OVERVIEW_FRAME
    result = {}
    for kernel in ([23] if overview else [7,15,23]):
        labels,stats,known = component_guides(ink,land,kernel,points,frame,strict=overview)
        for cell,name in known.items():
            left,top,width,height,area = stats[cell]
            if name in result or (not overview and area < 3500):
                continue
            core = labels[top:top+height,left:left+width]==cell
            geometry = raster_geometry(core)
            result[name] = polygonal(transform(geometry,lambda x,y:from_pixels(x+left,y+top,frame),interleaved=False))
    return result


def reference_guangnan(directory,raster_geometry):
    ink,land = load_ccts(directory,GUANGNAN_FRAME)
    names = ['广南西路','广南东路']
    controls = {name:[SONG_CONTROL_POINTS[name]] for name in names}
    for kernel in (3,7,13,23,35):
        labels,_,known = component_guides(ink,land,kernel,controls,GUANGNAN_FRAME,strict=False)
        if len(known)==2:
            break
    else:
        raise ValueError('The detailed Guangnan plate did not separate the two circuits')
    lookup = np.zeros(labels.max()+1,np.uint8)
    for cell,name in known.items():
        lookup[cell] = names.index(name)+1
    marked = lookup[labels]
    distance,nearest = cv2.distanceTransformWithLabels((marked==0).astype('uint8'),cv2.DIST_L2,5,
                                                       labelType=cv2.DIST_LABEL_PIXEL)
    colors = np.zeros(nearest.max()+1,np.uint8)
    colors[nearest[marked>0]] = marked[marked>0]
    # Recover the center of the actual boundary ink as shared vertices.
    # Other circuits and gaps away from the ink remain in the base map.
    coverage = np.where(land & ((marked>0)|((labels==0)&(distance<(kernel+4)))),colors[nearest],0)
    shapes = vectorize_coverage([raster_geometry(coverage==i) for i in (1,2)],1.1)
    return {name:polygonal(transform(geometry,lambda x,y:from_pixels(x,y,GUANGNAN_FRAME),interleaved=False))
            for name,geometry in zip(names,shapes)}


def align_guangnan(west,east,reference):
    """Replace the internal Guangnan line without moving the pair's perimeter."""
    precision=.00001
    extent=polygonal(union_all([west,east],grid_size=precision))
    detailed_west=polygonal(intersection(extent,reference['广南西路'],grid_size=precision))
    detailed_east=polygonal(intersection(extent,reference['广南东路'],grid_size=precision))
    western=polygonal(union_all([detailed_west,polygonal(difference(west,detailed_east,grid_size=precision))],grid_size=precision))
    eastern=polygonal(difference(extent,western,grid_size=precision))
    return western,eastern


# The Hartwell release indexes the sheet in traditional characters; a few
# features use variant spellings or Latin transliterations.
_TRADITIONAL = str.maketrans('臨慶義廣寧錦興來遼陽瀋蓋復開鳳順涼鎮隴綏間獻凊滄濬衛嵐絳澤懷華會積蘭鞏歸壽許鈞陳鄭穎陜單鄧環涇濰濱濟萊東邳兗與雲內撫應蔚德薊涿灤豐淨',
                           '临庆义广宁锦兴来辽阳沈盖复开凤顺凉镇陇绥间献清沧浚卫岚绛泽怀华会积兰巩归寿许钧陈郑颍陕单邓环泾潍滨济莱东邳兖与云内抚应蔚德蓟涿滦丰净')
_HARTWELL_ALIASES = {'Ao Zhou':'隩州','德兴州':'德兴府','乌古迪烈部':'临潢府','烏古迪烈部':'临潢府'}


def reference_jin_prefectures(source,memberships):
    by_prefecture = defaultdict(list)
    by_route = defaultdict(list)
    data = json.loads(source.read_text(encoding='utf-8'))
    for feature in data['features']:
        original = feature['properties']['name']
        name = _HARTWELL_ALIASES.get(original,original.translate(_TRADITIONAL))
        route = memberships.get(name)
        if route:
            geometry = make_valid(shape(feature['geometry']))
            by_prefecture[name].append(geometry)
            by_route[route].append(geometry)
    return tuple({name:polygonal(union_all(parts)) for name,parts in groups.items()}
                 for groups in (by_route,by_prefecture))
