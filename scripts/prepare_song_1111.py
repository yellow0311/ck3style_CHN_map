"""Build the 1111 Northern Song & Liao atlas from CCTS ad1111 and CHGIS V6."""

import argparse
from collections import defaultdict
from pathlib import Path
from tempfile import gettempdir

import cv2
import numpy as np
from shapely import STRtree, difference, intersection, transform, union_all
from shapely.geometry import Point, box

from prepare_boundaries import save
from prepare_ming_1582 import snapshot
from prepare_qing_1820 import area_record, polygonal, polygons, xy
from prepare_song_1208 import build_song_water, raster_geometry, route_colors
from prepare_terrain import load_height, save_grid
from song_1111_routes import (
    LIAO_CONTROL_POINTS, LIAO_COUNTIES, LIAO_ROUTES, LIAO_SEATS,
    NSONG_CONTROL_POINTS, NSONG_ROUTES, PLATE_SEATS, ROUTE_ALIASES,
)
from song_1208_coast import _clean_land, coast_reference
from song_1208_reference import (
    OVERVIEW_FRAME, from_pixels, load_ccts, to_pixels, vectorize_coverage,
)
from song_1208_topology import build_topology


ROOT = Path(__file__).resolve().parents[1]
YEAR = 1111
GRID = (45, 10, 150, 62)
NSONG_FRAME = (7, 96, 44, 16, 14)

ROUTES = {'song': NSONG_ROUTES, 'liao': LIAO_ROUTES}
PREFECTURE_ROUTES = {
    key: {name: route for route, (_, members) in definitions.items() for name in members.split()}
    for key, definitions in ROUTES.items()
}

STATES = {
    'song': ('北宋', '政权', '18–33', '#7ea482', '路级'),
    'liao': ('辽', '政权', '5–13', '#c48f9a', '道级'),
    'xia': ('西夏', '政权', '36–37', '#8e82b0', '府州治所'),
    'dali': ('大理', '政权', '38–39', '#c9936d', '府郡治所'),
    'tibet': ('吐蕃诸部', '诸部概略范围', '40–41', '#c6b66f', '地方中心'),
    'huangtou': ('黄头回纥', '部族政权', '34–35', '#b4879f', '地方中心'),
    'xizhou': ('西州回鹘', '政权', '34–35', '#cf9c66', '城邑治所'),
    'karakhanid': ('黑汗', '政权', '34–35', '#87a88a', '重镇城邑'),
    'kyrgyz': ('黠戛斯', '部族政权', '3–4', '#c9be74', '汗廷与部族中心'),
}

STATE_ANCHORS = {
    'song': (113.2, 29.8),
    'liao': (117.5, 45.2),
    'xia': (103.8, 38.8),
    'dali': (100.8, 25.4),
    'tibet': (89.0, 32.5),
    'huangtou': (95.5, 38.0),
    'xizhou': (87.5, 42.3),
    'karakhanid': (75.5, 41.2),
    'kyrgyz': (98.0, 54.5),
}

STATE_NOTES = {
    'song': '疆界依政和元年（1111 年）全图，下分二十四路，府州与县治采用 1111 年有效记录。',
    'liao': '疆界依天庆元年（1111 年）全图，下分五道，府州与县治参照《辽史·地理志》及分图整理。',
    'xia': '疆界依 1111 年全图，标出兴庆府等主要府州与军司治所。',
    'dali': '疆界依 1111 年全图，按大理分图标出都城及主要府郡治所。',
    'tibet': '按全图描绘吐蕃诸部概略范围，标出主要城邑与寺院中心。',
    'huangtou': '按全图描绘黄头回纥（撒里畏吾儿）分布范围与地望。',
    'xizhou': '疆界依 1111 年全图，标出高昌、北庭、龟兹、焉耆等城邑。',
    'karakhanid': '疆界依 1111 年全图，标出八剌沙衮、疏勒、于阗、撒马尔罕等重镇。',
    'kyrgyz': '按全图描绘黠戛斯范围，标出叶尼塞河上游汗廷及主要部族中心。',
}


def load_ccts_rgba(directory, frame=OVERVIEW_FRAME):
    zoom, west, north, width, height = frame
    images = np.zeros((height * 256, width * 256, 4), np.uint8)
    for x in range(west, west + width):
        for y in range(north, north + height):
            tile = directory / f'ccts-{zoom}-{x}-{y}.png'
            x0, y0 = (x - west) * 256, (y - north) * 256
            if tile.exists():
                from PIL import Image
                with Image.open(tile) as image:
                    rgba = image.convert('RGBA')
            elif zoom > 6:
                from PIL import Image
                fallback = 2 ** (zoom - 6)
                with Image.open(directory / f'ccts-6-{x // fallback}-{y // fallback}.png') as image:
                    side = 256 // fallback
                    ax, ay = x % fallback * side, y % fallback * side
                    rgba = image.convert('RGBA').crop((ax, ay, ax + side, ay + side)).resize(
                        (256, 256), Image.Resampling.NEAREST
                    )
            else:
                raise FileNotFoundError(f'Missing CCTS tile {tile.name}')
            images[y0:y0 + 256, x0:x0 + 256] = np.asarray(rgba)
    return images


def extract_1111_states_and_liao(ccts_dir):
    """Extract all 9 colored polities and 5 Liao circuits from CCTS ad1111 zoom 6."""
    rgba = load_ccts_rgba(ccts_dir, OVERVIEW_FRAME)
    r, g, b, a = rgba.transpose(2, 0, 1)
    land = a > 100
    orange = (r >= 145) & (g >= 90) & (g < 190) & (b <= 40) & land

    # Add the faint grey Kyrgyz / Liao-Shangjing boundary north of lat 50.2
    north_mask = np.zeros_like(land)
    x80, y59 = to_pixels([80], [59])[0]
    x123, y50 = to_pixels([123], [50.2])[0]
    north_mask[y59:y50, x80:x123] = True
    faint = north_mask & land & ((r < 228) | (g < 212) | (b < 175))
    combined = orange | faint

    closed = cv2.morphologyEx(combined.astype('uint8'), cv2.MORPH_CLOSE,
                              cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    strokes = cv2.dilate(closed, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    _, labels, stats, _ = cv2.connectedComponentsWithStats((land & (strokes == 0)).astype('uint8'), connectivity=4)

    # Identify every cell owner by control points
    cell_controls = {
        'song': list(NSONG_CONTROL_POINTS.values()),
        'liao_上京道': [(116.5, 45.2), (105.0, 47.0), (92.0, 49.0)],
        'liao_东京道': [(126.0, 46.0), (123.2, 41.3), (142.8, 51.0)],
        'liao_中京道': [(119.3, 41.6)],
        'liao_南京道': [(116.4, 39.9)],
        'liao_西京道': [(113.3, 40.5)],
        'xia': [(105.5, 38.5), (100.5, 39.0)],
        'dali': [(101.0, 25.0)],
        'tibet': [(88.0, 32.5), (96.0, 32.0)],
        'huangtou': [(95.5, 38.0)],
        'xizhou': [(89.0, 42.5), (84.0, 41.5)],
        'karakhanid': [(75.0, 42.0), (77.0, 39.0), (71.5, 41.5)],
        'kyrgyz': [(93.0, 54.5), (113.0, 54.5)],
    }
    group_names = list(cell_controls)
    lookup = np.zeros(len(stats), np.uint8)
    for idx, name in enumerate(group_names, 1):
        for lon, lat in cell_controls[name]:
            px, py = to_pixels([lon], [lat])[0]
            patch = labels[py - 4:py + 5, px - 4:px + 5].ravel()
            nz = patch[patch != 0]
            if len(nz):
                comp = int(np.bincount(nz).argmax())
                lookup[comp] = idx

    # Exclude Taiwan (lon > 119.7, lat < 25.8) which is uncolored on the 1111 plate
    tw_x, tw_y = to_pixels([119.7], [25.8])[0]
    taiwan_mask = np.zeros_like(land)
    taiwan_mask[tw_y:, tw_x:] = True
    valid_land = land & (~taiwan_mask)

    marked = lookup[labels]
    marked[taiwan_mask] = 0
    distance, nearest = cv2.distanceTransformWithLabels((marked == 0).astype('uint8'), cv2.DIST_L2, 5,
                                                        labelType=cv2.DIST_LABEL_PIXEL)
    owner = np.zeros(nearest.max() + 1, np.uint8)
    seeds = marked > 0
    owner[nearest[seeds]] = marked[seeds]
    coverage = np.where(valid_land & ((marked > 0) | ((labels == 0) & (distance < 15))), owner[nearest], 0)

    # First vectorize the 9 states cleanly (merging the 5 Liao circuits into 'liao')
    state_keys = list(STATES)
    state_map = np.zeros(len(group_names) + 1, np.uint8)
    for idx, name in enumerate(group_names, 1):
        st = 'liao' if name.startswith('liao_') else name
        state_map[idx] = state_keys.index(st) + 1
    state_cov = state_map[coverage]
    state_masks = [raster_geometry(state_cov == i) for i in range(1, len(state_keys) + 1)]
    states = {
        key: polygonal(transform(geom, from_pixels, interleaved=False))
        for key, geom in zip(state_keys, vectorize_coverage(state_masks, 1.15))
    }

    # Also vectorize the 5 Liao circuits cleanly
    liao_names = list(LIAO_ROUTES)
    liao_masks = [raster_geometry(coverage == (group_names.index('liao_' + n) + 1)) for n in liao_names]
    liao_guides = {
        name: polygonal(transform(geom, from_pixels, interleaved=False))
        for name, geom in zip(liao_names, vectorize_coverage(liao_masks, 1.15))
    }
    return states, liao_guides


def extract_nsong_route_guides(ccts_dir):
    """Extract Northern Song 24 route guides from CCTS ad1111 zoom 6 and zoom 7."""
    result = {}
    for frame, kernels, min_area in [(NSONG_FRAME, [7, 13, 21], 3000), (OVERVIEW_FRAME, [7, 15, 23], 500)]:
        ink, land = load_ccts(ccts_dir, frame)
        for kernel in kernels:
            closed = cv2.morphologyEx(ink.astype('uint8'), cv2.MORPH_CLOSE,
                                      cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel, kernel)))
            strokes = cv2.dilate(closed, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
            _, labels, stats, _ = cv2.connectedComponentsWithStats((land & (strokes == 0)).astype('uint8'), connectivity=4)
            owners = defaultdict(set)
            for name, (lon, lat) in NSONG_CONTROL_POINTS.items():
                px, py = to_pixels([lon], [lat], frame)[0]
                if not (0 <= py < labels.shape[0] and 0 <= px < labels.shape[1]):
                    continue
                patch = labels[max(0, py - 4):py + 5, max(0, px - 4):px + 5].ravel()
                nz = patch[patch != 0]
                if len(nz):
                    owners[int(np.bincount(nz).argmax())].add(name)
            for cell, names in owners.items():
                if len(names) != 1:
                    continue
                name = next(iter(names))
                if name in result:
                    continue
                left, top, width, height, area = stats[cell]
                if area < min_area:
                    continue
                core = labels[top:top + height, left:left + width] == cell
                geom = raster_geometry(core)
                result[name] = polygonal(transform(geom, lambda x, y: from_pixels(x + left, y + top, frame), interleaved=False))
    return result


def refine_1111_coasts(states, root, cache):
    """Apply detailed coastline to Song and Liao and remove spurious interior holes."""
    modern, shore = coast_reference(root, cache)
    old = union_all([states['song'], states['liao']])
    others = union_all([g for key, g in states.items() if key not in ('song', 'liao')])
    domain = old.buffer(.78).difference(others)
    coastal_band = shore.buffer(.86).intersection(box(107.65, 17.95, 124.2, 41.3)).intersection(domain)
    land = _clean_land(old.difference(coastal_band).union(modern.intersection(coastal_band)), min_area=.001)
    fragments = {'song': [], 'liao': []}
    for part in polygons(land.difference(old)):
        pt = part.representative_point()
        owner = min(fragments, key=lambda key: states[key].distance(pt))
        fragments[owner].append(part)
    output = {key: _clean_land(geom, min_area=.004) for key, geom in states.items()}
    for key in ('song', 'liao'):
        original = states[key]
        geom = union_all([original.intersection(land), *fragments[key]])
        output[key] = _clean_land(geom, min_area=.001)
    return output


def seat_record(ident, name, kind, key, point, parent=None, **details):
    x, y = xy(point.x, point.y)
    nation = 'song1111-p-' + key
    details.setdefault('sourcePage', STATES[key][2])
    return dict(id=ident, n=name, type=kind, seat=True, x=round(x, 3), y=round(y, 3),
                p=parent or nation, nation=nation, **details)


def build_routes(key, territory, prefectures, guides):
    routes = ROUTES[key]
    memberships = PREFECTURE_ROUTES[key]
    west, south, east, north = territory.bounds
    rate = 120 if key == 'song' else 60
    width, height = int(np.ceil((east - west) * rate)) + 1, int(np.ceil((north - south) * rate)) + 1
    shape = (height, width)

    def pixels(points):
        coords = np.asarray(points)
        return np.rint((coords - [west, south]) * rate).astype(np.int32)

    def paint(mask, geometry):
        for area in polygons(geometry):
            cv2.fillPoly(mask, [pixels(area.exterior.coords)], 255)
            for hole in area.interiors:
                cv2.fillPoly(mask, [pixels(hole.coords)], 0)

    known = {name: np.zeros(shape, np.uint8) for name in routes}
    mapped_areas = {name: np.zeros(shape, np.uint8) for name in routes}
    reference_areas = {name: np.zeros(shape, np.uint8) for name in routes}
    surveyed = defaultdict(list)

    for (state, name), (record, geometry) in prefectures.items():
        route = memberships.get(name) if state == key else None
        if not route:
            continue
        if geometry is not None:
            paint(mapped_areas[route], geometry)
            surveyed[route].append(geometry)
        else:
            point = [record['x'] / 14 + 62, 57 - record['y'] / 17]
            cv2.circle(known[route], tuple(pixels([point])[0]), 2, 255, -1)

    for name, geometry in guides.items():
        if name in reference_areas:
            paint(reference_areas[name], geometry.intersection(territory))

    ctrl = NSONG_CONTROL_POINTS if key == 'song' else LIAO_CONTROL_POINTS
    for name, pt in ctrl.items():
        if name in known:
            cv2.circle(known[name], tuple(pixels([pt])[0]), 2, 255, -1)

    exact = np.maximum.reduce(list(mapped_areas.values()))
    for name in routes:
        reference_areas[name][exact != 0] = 0

    mask = np.zeros(shape, np.uint8)
    paint(mask, territory)
    nearest = np.zeros(shape, np.uint8)
    best = np.full(shape, np.inf, np.float32)
    for index, name in enumerate(routes):
        seeds = cv2.bitwise_or(known[name], cv2.bitwise_or(mapped_areas[name], reference_areas[name]))
        if not seeds.any():
            raise ValueError(f'Missing geography for {name}')
        distance = cv2.distanceTransform(255 - seeds, cv2.DIST_L2, 5)
        wins = distance < best
        best[wins] = distance[wins]
        nearest[wins] = index

    raster = [raster_geometry((nearest == i) & (mask != 0)) for i in range(len(routes))]
    geometries = [
        polygonal(transform(geom, lambda x, y: (x / rate + west, y / rate + south), interleaved=False)
                  .intersection(territory))
        for geom in vectorize_coverage(raster, 1.4)
    ]

    missing = polygonal(territory.difference(union_all(geometries)))
    for part in polygons(missing):
        nearest_index = min(range(len(geometries)), key=lambda i: geometries[i].distance(part.representative_point()))
        geometries[nearest_index] = polygonal(geometries[nearest_index].union(part))

    # Preserve exact CHGIS 1111 vector prefecture boundaries for routes where available
    precision = .00001
    mapped = {
        name: polygonal(intersection(polygonal(union_all(parts, grid_size=precision)), territory, grid_size=precision))
        for name, parts in surveyed.items() if parts
    }
    if mapped:
        filled = polygonal(union_all(list(mapped.values()), grid_size=precision))
        geometries = [
            polygonal(union_all([polygonal(difference(geometry, filled, grid_size=precision)), mapped[name]],
                                grid_size=precision)) if name in mapped
            else polygonal(difference(geometry, filled, grid_size=precision))
            for name, geometry in zip(routes, geometries)
        ]

    colors = route_colors(geometries)
    output = {}
    nation = 'song1111-p-' + key
    tier_kind = '路' if key == 'song' else '道'
    for index, ((name, (pages, _)), geometry) in enumerate(zip(routes.items(), geometries)):
        ident = f'song1111-r-{key}-{index}'
        description = '路界结合 1111 年配准图与 CHGIS 府州边界复原。' if key == 'song' else '道界依辽天庆元年（1111 年）全图及五道分图复原。'
        info = area_record(ident, name, tier_kind, geometry, p=nation, nation=nation, sourcePage=pages,
                           aliases=ROUTE_ALIASES.get(name, []), color=colors[index], description=description)
        output[name] = info, geometry
    return output


def build_admin(land, chgis, route_guides):
    province, city, county = [], [], []
    eastern = {key: land[key] for key in ('song', 'liao')}
    joined_east = union_all(list(eastern.values()))
    groups = defaultdict(list)

    def listed_state(name):
        matches = [key for key in eastern if name in PREFECTURE_ROUTES[key]]
        return matches[0] if len(matches) == 1 else None

    for attrs, area in snapshot(chgis / 'dataverse-2966510.zip', YEAR):
        if attrs['TYPE_CH'] == '非政区国土':
            continue
        area = polygonal(area)
        key = listed_state(attrs['NAME_CH']) or max(eastern, key=lambda side: area.intersection(eastern[side]).area)
        clipped = polygonal(area.intersection(eastern[key]))
        if not clipped.is_empty:
            groups[key, attrs['NAME_CH']].append((attrs, clipped))

    city_shapes, city_keys, city_ids = [], [], []
    city_by_name = {}
    for (key, name), entries in groups.items():
        attrs = entries[0][0]
        geom = polygonal(union_all([shape for _, shape in entries], grid_size=.00001))
        ident = f'song1111-f-{attrs["SYS_ID"]}'
        nation = 'song1111-p-' + key
        record = area_record(ident, name, attrs['TYPE_CH'], geom, p=nation, nation=nation, sourcePage=STATES[key][2])
        city.append(record)
        city_shapes.append(geom)
        city_keys.append(key)
        city_ids.append(ident)
        city_by_name[key, name] = record, geom
    index = STRtree(city_shapes)

    def eastern_state(point):
        key = min(eastern, key=lambda side: eastern[side].distance(point))
        if eastern[key].distance(point) > .38:
            return None
        other = min(land, key=lambda side: land[side].distance(point))
        if other not in eastern and land[other].covers(point):
            return None
        return key

    for attrs, point in snapshot(chgis / 'dataverse-2970286.zip', YEAR):
        name = attrs['NAME_CH']
        key = listed_state(name) or eastern_state(point)
        if not key or not name:
            continue
        if (key, name) in city_by_name:
            record, geom = city_by_name[key, name]
            if geom is not None and geom.covers(point):
                record['x'], record['y'] = (round(value, 3) for value in xy(point.x, point.y))
        else:
            record = seat_record(f'song1111-f-p{attrs["SYS_ID"]}', name, attrs['TYPE_CH'], key, point)
            city.append(record)
            city_by_name[key, name] = record, None

    points = {key: [] for key in eastern}
    for record in city:
        key = record['nation'].split('-')[-1]
        point = Point(record['x'] / 14 + 62, 57 - record['y'] / 17)
        points[key].append((record, point))

    # Add curated Liao prefecture/zhou seats
    for i, (name, kind, lon, lat, pages, aliases) in enumerate(LIAO_SEATS):
        key = ('liao', name)
        if key in city_by_name:
            city_by_name[key][0].setdefault('aliases', aliases)
            continue
        record = seat_record(f'song1111-f-liao-{i}', name, kind, 'liao', Point(lon, lat), aliases=aliases,
                             sourcePage=pages, description='参照辽五道分图与《辽史·地理志》，点位为约略定位。')
        city.append(record)
        city_by_name[key] = record, None
        points['liao'].append((record, Point(lon, lat)))

    # Add CHGIS 1111 county seats for Northern Song and Liao
    for attrs, point in snapshot(chgis / 'county-points.zip', YEAR):
        name, kind = attrs['NAME_CH'], attrs['TYPE_CH']
        if not name or not kind or joined_east.distance(point) > .25:
            continue
        key = eastern_state(point)
        if not key:
            continue
        parents = [i for i in index.query(point, predicate='covered_by') if city_keys[i] == key]
        details = {}
        if parents:
            parent = city_ids[min(parents, key=lambda i: city_shapes[i].area)]
        else:
            closest, anchor = min(points[key], key=lambda entry: entry[1].distance(point))
            parent = closest['id'] if anchor.distance(point) < 1.2 else None
            if parent:
                details['description'] = '府州关联按治所位置推定。'
        county.append(seat_record(f'song1111-c-{attrs["SYS_ID"]}', name, kind, key, point, parent=parent, **details))

    # Supplement Liao county seats from Liao shi / Vol. 6 plates
    registered_liao = defaultdict(list)
    for record in county:
        if record['nation'] == 'song1111-p-liao':
            registered_liao[record['n']].append(record)
    for parent, places in LIAO_COUNTIES.items():
        if ('liao', parent) not in city_by_name:
            continue
        prefecture, _ = city_by_name['liao', parent]
        for offset, (name, lon, lat) in enumerate(places):
            x, y = xy(lon, lat)
            existing = next((r for r in registered_liao[name] if abs(r['x'] - x) < 3 and abs(r['y'] - y) < 3), None)
            if existing:
                existing.update(p=prefecture['id'], sourcePage=prefecture['sourcePage'])
                existing.pop('description', None)
                continue
            county.append(seat_record(f'{prefecture["id"]}-c{offset}', name, '县', 'liao', Point(lon, lat),
                                      parent=prefecture['id'], sourcePage=prefecture['sourcePage'],
                                      description='参照辽五道分图与《辽史·地理志》，点位为约略定位。'))

    # Add prefecture/city-level seats for the other 7 colored polities
    for key, places in PLATE_SEATS.items():
        for offset, (name, kind, lon, lat, aliases) in enumerate(places):
            city.append(seat_record(f'song1111-f-{key}-{offset}', name, kind, key, Point(lon, lat),
                                    aliases=aliases, description='参照图册及历史地名资料，点位为约略定位。'))

    # Build routes for Northern Song (24 routes) and Liao (5 circuits)
    route_records = {
        key: build_routes(key, territory, city_by_name, route_guides.get(key, {}))
        for key, territory in eastern.items()
    }

    final_prefectures = {}
    for (key, name), (record, geometry) in city_by_name.items():
        routes = route_records[key]
        route = PREFECTURE_ROUTES[key].get(name)
        if not route:
            point = Point(record['x'] / 14 + 62, 57 - record['y'] / 17)
            route = min(routes, key=lambda r: routes[r][1].distance(point))
            record['description'] = '所属路/道按图册地望及现有界线推定。'
        route_area, _ = routes[route]
        record['p'] = route_area['id']
        if geometry is not None:
            final_prefectures[record['id']] = geometry

    for record in county:
        if record['p'] != record['nation']:
            continue
        key = record['nation'].rsplit('-', 1)[1]
        point = Point(record['x'] / 14 + 62, 57 - record['y'] / 17)
        route, _ = min(route_records[key].values(), key=lambda r: r[1].distance(point))
        record['p'] = route['id']
        record['description'] = '所属路/道按地望推定，具体府州待核。'

    for key, (name, kind, pages, color, level) in STATES.items():
        ident = 'song1111-p-' + key
        item = area_record(ident, name, kind, land[key], nation=ident, color=color, sourcePage='3–4',
                           detailLevel=level, description=STATE_NOTES[key])
        point = Point(STATE_ANCHORS[key])
        if land[key].covers(point):
            item['x'], item['y'] = xy(point.x, point.y)
        if key == 'tibet':
            item['aliases'] = ['吐蕃', '吐蕃诸部']
        elif key == 'karakhanid':
            item['aliases'] = ['喀喇汗', '黑汗王朝']
        elif key == 'xizhou':
            item['aliases'] = ['高昌回鹘']
        elif key == 'huangtou':
            item['aliases'] = ['撒里畏吾儿']
        province.append(item)

    subdivisions = [entry for state in route_records.values() for entry in state.values()]
    route = [record for record, _ in subdivisions]
    outline, linework = build_topology(
        province, route, city,
        {'song1111-p-' + key: geometry for key, geometry in land.items()},
        {record['id']: geometry for record, geometry in subdivisions},
        final_prefectures,
    )
    return {'province': province, 'route': route, 'city': city, 'county': county, 'outline': outline, 'linework': linework}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ccts_tiles', type=Path, help='Directory containing CCTS ad1111 zoom 6/7 tiles')
    parser.add_argument('chgis', type=Path, help='Directory with CHGIS V6 archives')
    parser.add_argument('water_source', type=Path, help='CHGIS V4 water tables')
    parser.add_argument('--elevation-cache', type=Path, default=Path(gettempdir()) / 'shanhe-atlas-elevation')
    parser.add_argument('--vectors-only', action='store_true')
    args = parser.parse_args()
    output = ROOT / 'dist/data/song-1111'
    (output / 'terrain').mkdir(parents=True, exist_ok=True)

    print('Extracting 1111 polities and Liao circuits from CCTS ad1111', flush=True)
    land, liao_guides = extract_1111_states_and_liao(args.ccts_tiles)
    nsong_guides = extract_nsong_route_guides(args.ccts_tiles)
    print('Northern Song route guides extracted:', len(nsong_guides), flush=True)
    land = refine_1111_coasts(land, ROOT, args.elevation_cache)
    print('Refined coastlines and cleaned interior holes', flush=True)

    admin = build_admin(land, args.chgis, {'song': nsong_guides, 'liao': liao_guides})
    save(output / 'admin-boundaries.json', admin)

    water, lakes = build_song_water(args.water_source, args.elevation_cache)
    save(output / 'terrain/water.json', water)

    for state in admin['province']:
        counts = [sum(row['nation'] == state['id'] for row in admin[k]) for k in ('route', 'city', 'county')]
        print(state['n'], 'routes/cities/counties:', *counts, flush=True)

    if not args.vectors_only:
        areas = [(part.bounds, [list(r.coords) for r in (part.exterior, *part.interiors)])
                 for geom in land.values() for part in polygons(geom)]
        height = load_height(GRID, 30, 5, args.elevation_cache)
        save_grid(output / 'terrain/overview.hgt.gz', height.clip(min=0), GRID[0], GRID[3], 30, areas, lakes)


if __name__ == '__main__':
    main()
