"""Build the Three Kingdoms 262 (Wei/Shu Han/Wu) atlas from CCTS ad0262 and CHGIS V6."""

import argparse
from collections import defaultdict
from pathlib import Path
from tempfile import gettempdir

import cv2
import numpy as np
from shapely import STRtree, coverage_is_valid, coverage_simplify, node, polygonize, transform, union_all
from shapely.geometry import Point, box

from prepare_boundaries import save
from prepare_ming_1582 import snapshot
from prepare_qing_1820 import area_record, polygonal, polygons, xy
from prepare_song_1111 import load_ccts_rgba
from prepare_song_1208 import build_song_water, raster_geometry, route_colors
from prepare_terrain import load_height, save_grid
from song_1208_coast import _clean_land, coast_reference
from song_1208_reference import OVERVIEW_FRAME, _smooth_coverage_arcs, from_pixels, to_pixels, vectorize_coverage
from song_1208_topology import build_topology


ROOT = Path(__file__).resolve().parents[1]
YEAR = 262
GRID = (60, 10, 145, 55)
SANGUO_Z7 = (7, 96, 46, 16, 12)

STATES = {
    'wei': ('魏', '政权', '3–17', '#c9b76a', '州级'),
    'shu': ('蜀汉', '政权', '18–23', '#bf8b66', '州级'),
    'wu': ('吴', '政权', '24–32', '#7ba188', '州级'),
}

STATE_ANCHORS = {
    'wei': (115.6, 37.6),
    'shu': (104.2, 28.8),
    'wu': (115.5, 27.6),
}

STATE_NOTES = {
    'wei': '魏景元三年（262 年）疆域，都洛阳，辖司、豫、兖、青、徐、冀、并、幽、雍、凉、荆、扬十二州及西域长史府。',
    'shu': '蜀汉景耀五年（262 年）疆域，都成都，辖益州（含汉中、巴蜀与南中诸郡）。',
    'wu': '吴永安五年（262 年）疆域，都建业，辖扬、荆、交三州（广州于 264 年始复置）。',
}

# All 17 Three Kingdoms provinces with state key, display name, pages, and control points on ad0262.
PROVINCES = [
    ('wei', '司州', '5–6', [(112.4, 34.8)]),
    ('wei', '豫州', '7–8', [(114.6, 33.5)]),
    ('wei', '兖州', '7–8', [(115.6, 35.4)]),
    ('wei', '青州', '7–8', [(118.8, 36.7)]),
    ('wei', '徐州', '7–8', [(118.5, 34.4)]),
    ('wei', '冀州', '9–10', [(115.6, 37.8)]),
    ('wei', '并州', '9–10', [(112.5, 37.5)]),
    ('wei', '幽州', '11–12', [(117.5, 40.0), (125.8, 39.0)]),
    ('wei', '雍州', '13–14', [(108.9, 34.5)]),
    ('wei', '凉州', '15–16', [(102.6, 37.9)]),
    ('wei', '西域长史府', '17', [(88.0, 41.5), (78.0, 39.5)]),
    ('wei', '荆州', '13–14', [(112.3, 32.8)]),
    ('wei', '扬州', '7–8', [(116.8, 32.3)]),
    ('shu', '益州', '18–23', [(104.1, 30.6), (102.5, 25.5)]),
    ('wu', '扬州', '24–27', [(118.5, 29.5), (116.5, 27.5)]),
    ('wu', '荆州', '28–29', [(112.2, 28.5), (112.5, 25.5)]),
    ('wu', '交州', '30–32', [(110.5, 23.0), (105.8, 21.0), (109.8, 19.2)]),
]

# Curated border/frontier commanderies supplementing CHGIS 262 point table.
EXTRA_COMMANDERIES = [
    ('wei', '幽州', '辽东郡', '郡', 123.173, 41.273, ['襄平', '辽阳']),
    ('wei', '幽州', '玄菟郡', '郡', 123.925, 41.887, ['高句丽县']),
    ('wei', '幽州', '乐浪郡', '郡', 125.750, 39.010, ['朝鲜县', '平壤']),
    ('wei', '幽州', '带方郡', '郡', 125.850, 38.050, []),
    ('wei', '幽州', '昌黎郡', '郡', 121.239, 41.535, []),
    ('wei', '幽州', '辽西郡', '郡', 118.860, 39.880, ['阳乐']),
    ('wei', '幽州', '右北平郡', '郡', 117.750, 40.000, ['土垠']),
    ('wei', '幽州', '渔阳郡', '郡', 116.850, 40.373, []),
    ('wei', '西域长史府', '海头', '治所', 89.920, 40.520, ['楼兰', '西域长史府治']),
    ('wei', '西域长史府', '高昌', '城邑', 89.533, 42.852, ['戊己校尉']),
    ('wei', '西域长史府', '伊吾', '城邑', 93.515, 42.826, ['哈密']),
    ('wei', '西域长史府', '龟兹', '城邑', 82.960, 41.720, ['库车']),
    ('wei', '西域长史府', '焉耆', '城邑', 86.570, 42.060, []),
    ('wei', '西域长史府', '疏勒', '城邑', 75.989, 39.472, ['喀什']),
    ('wei', '西域长史府', '于阗', '城邑', 79.914, 37.111, ['和田']),
    ('wu', '交州', '交趾郡', '郡', 105.834, 21.028, ['龙编', '河内']),
    ('wu', '交州', '九真郡', '郡', 105.780, 19.810, ['胥浦']),
    ('wu', '交州', '日南郡', '郡', 107.180, 16.750, ['西卷']),
    ('wu', '交州', '珠崖郡', '郡', 110.350, 19.950, ['徐闻']),
    ('wu', '交州', '郁林郡', '郡', 109.600, 23.100, ['布山']),
]


def smooth_raster_coverage(label_grid, count, tolerance):
    """Rebuild a noded polygonal coverage from a label grid and smooth all shared arcs."""
    raw = [raster_geometry(label_grid == i) for i in range(1, count + 1)]
    boundaries = [g.boundary for g in raw if not g.is_empty]
    if not boundaries:
        return raw
    noded = node(union_all(boundaries))
    lines = list(noded.geoms) if hasattr(noded, 'geoms') else [noded]
    faces = list(polygonize(lines).geoms)
    buckets = defaultdict(list)
    h, w = label_grid.shape
    for face in faces:
        pt = face.representative_point()
        ix, iy = int(pt.x), int(pt.y)
        if 0 <= iy < h and 0 <= ix < w:
            owner = int(label_grid[iy, ix])
            if owner > 0:
                buckets[owner].append(face)
    rebuilt = [polygonal(union_all(buckets[i])) if buckets[i] else raw[i - 1] for i in range(1, count + 1)]
    if not coverage_is_valid(rebuilt):
        return vectorize_coverage(rebuilt, tolerance)
    simplified = coverage_simplify(rebuilt, tolerance)
    parts = [[(list(p.exterior.coords), [list(r.coords) for r in p.interiors])
              for p in polygons(g)] for g in simplified]
    for passes in (2, 1):
        try:
            refined = _smooth_coverage_arcs(parts, passes)
            if all(g.is_valid for g in refined) and coverage_is_valid(refined):
                return coverage_simplify(refined, tolerance * 0.15)
        except Exception:
            continue
    return simplified


def extract_states_and_provinces(ccts_dir):
    """Extract the 3 kingdoms and 17 provinces from CCTS ad0262 zoom 6."""
    rgba = load_ccts_rgba(ccts_dir, OVERVIEW_FRAME)
    r, g, b, a = rgba.transpose(2, 0, 1)
    land = a > 100
    orange = (r >= 145) & (g >= 90) & (g < 190) & (b <= 40) & land
    # Include blue Yangtze River so Wei Yangzhou and Wu Yangzhou separate cleanly
    blue = (b.astype(int) - r.astype(int) > 15) & (b > 170) & land
    # Only apply blue barrier in the lower Yangtze box (114E..122E, 29N..33N)
    x1, y1 = to_pixels([114.0], [33.0])[0]
    x2, y2 = to_pixels([122.0], [29.0])[0]
    yangtze_mask = np.zeros_like(land)
    yangtze_mask[y1:y2, x1:x2] = True
    barrier = orange | (blue & yangtze_mask)

    closed = cv2.morphologyEx(barrier.astype('uint8'), cv2.MORPH_CLOSE,
                              cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    strokes = cv2.dilate(closed, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    _, labels, stats, _ = cv2.connectedComponentsWithStats((land & (strokes == 0)).astype('uint8'), connectivity=4)

    # Exclude Taiwan (夷洲)
    tw_x, tw_y = to_pixels([119.7], [25.8])[0]
    tw_mask = np.zeros_like(land)
    tw_mask[tw_y:, tw_x:] = True

    lookup = np.zeros(len(stats), np.uint8)
    for idx, (state_key, prov_name, _, pts) in enumerate(PROVINCES, 1):
        for lon, lat in pts:
            px, py = to_pixels([lon], [lat])[0]
            patch = labels[py - 4:py + 5, px - 4:px + 5].ravel()
            nz = patch[patch != 0]
            if len(nz):
                comp = int(np.bincount(nz).argmax())
                lookup[comp] = idx

    marked = lookup[labels]
    marked[tw_mask] = 0
    distance, nearest = cv2.distanceTransformWithLabels((marked == 0).astype('uint8'), cv2.DIST_L2, 5,
                                                        labelType=cv2.DIST_LABEL_PIXEL)
    owner = np.zeros(nearest.max() + 1, np.uint8)
    seeds = marked > 0
    owner[nearest[seeds]] = marked[seeds]
    coverage = np.where(land & (~tw_mask) & ((marked > 0) | ((labels == 0) & (distance < 14))), owner[nearest], 0)

    # Vectorize the 17 provinces cleanly together with noded Chaikin smoothing
    smoothed_provs = smooth_raster_coverage(coverage, len(PROVINCES), tolerance=1.9)
    prov_geoms = {
        (state_key, prov_name): polygonal(transform(geom, from_pixels, interleaved=False))
        for (state_key, prov_name, _, _), geom in zip(PROVINCES, smoothed_provs)
    }

    # Build the 3 state geometries as exact unions of their provinces
    states = {}
    for sk in STATES:
        parts = [g for (k, _), g in prov_geoms.items() if k == sk]
        states[sk] = polygonal(union_all(parts))
    return states, prov_geoms


def refine_sanguo_coasts(states, root, cache):
    modern, shore = coast_reference(root, cache)
    old = polygonal(union_all(list(states.values())))
    domain = old.buffer(.78)
    coastal_band = shore.buffer(.86).intersection(box(107.65, 17.95, 124.2, 41.3)).intersection(domain)
    land = _clean_land(old.difference(coastal_band).union(modern.intersection(coastal_band)), min_area=.001)
    fragments = {k: [] for k in states}
    for part in polygons(land.difference(old)):
        pt = part.representative_point()
        owner = min(states, key=lambda k: states[k].distance(pt))
        fragments[owner].append(part)
    output = {}
    for k, orig in states.items():
        geom = union_all([orig.intersection(land), *fragments[k]])
        output[k] = _clean_land(geom, min_area=.001)
    return output


def extract_commandery_polygons(ccts_dir, seats, empire):
    """Extract commandery polygons from CCTS ad0262 zoom 7 using orange+grey+blue lines."""
    rgba = load_ccts_rgba(ccts_dir, SANGUO_Z7)
    r, g, b, a = rgba.transpose(2, 0, 1)
    land = a > 100
    orange = (r >= 145) & (g >= 90) & (g < 190) & (b <= 40) & land
    # Grey commandery borders inside provinces
    grey = (r >= 115) & (r <= 215) & (np.abs(r.astype(int) - g.astype(int)) < 16) & (np.abs(g.astype(int) - b.astype(int)) < 16) & land
    blue = (b.astype(int) - r.astype(int) > 15) & (b > 170) & land
    barrier = orange | grey | blue

    closed = cv2.morphologyEx(barrier.astype('uint8'), cv2.MORPH_CLOSE,
                              cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    strokes = cv2.dilate(closed, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    _, labels, stats, _ = cv2.connectedComponentsWithStats((land & (strokes == 0)).astype('uint8'), connectivity=4)

    cell_to_seat = {}
    matched = []
    for seat in seats:
        px, py = to_pixels([seat['lon']], [seat['lat']], SANGUO_Z7)[0]
        if not (0 <= py < labels.shape[0] and 0 <= px < labels.shape[1]):
            continue
        patch = labels[max(0, py - 4):py + 5, max(0, px - 4):px + 5].ravel()
        nz = patch[patch != 0]
        if not len(nz):
            continue
        comp = int(np.bincount(nz).argmax())
        if comp in cell_to_seat or stats[comp, cv2.CC_STAT_AREA] > 260000:
            continue
        cell_to_seat[comp] = len(matched) + 1
        matched.append(seat)

    lookup = np.zeros(len(stats), np.uint16)
    for comp, idx in cell_to_seat.items():
        lookup[comp] = idx
    marked = lookup[labels]
    distance, nearest = cv2.distanceTransformWithLabels((marked == 0).astype('uint8'), cv2.DIST_L2, 5,
                                                        labelType=cv2.DIST_LABEL_PIXEL)
    owner = np.zeros(nearest.max() + 1, np.uint16)
    seeds = marked > 0
    owner[nearest[seeds]] = marked[seeds]
    coverage = np.where(land & ((marked > 0) | ((labels == 0) & (distance < 14))), owner[nearest], 0)

    smoothed = smooth_raster_coverage(coverage, len(matched), tolerance=2.4)
    polys = {}
    for seat, geom in zip(matched, smoothed):
        poly = polygonal(transform(geom, lambda x, y: from_pixels(x, y, SANGUO_Z7), interleaved=False).intersection(empire))
        if not poly.is_empty and poly.area > .005:
            polys[seat['id']] = poly
    return polys


def build_admin(ccts_dir, chgis, elevation_cache):
    states, prov_geoms = extract_states_and_provinces(ccts_dir)
    states = refine_sanguo_coasts(states, ROOT, elevation_cache)
    empire = polygonal(union_all(list(states.values())))

    # Clip/re-attach coastal fragments to provinces cleanly
    route_shapes = {}
    route_records = []
    route_id_by_key = {}
    for sk in STATES:
        s_provs = [(p_name, pages, prov_geoms[sk, p_name]) for k, p_name, pages, _ in PROVINCES if k == sk]
        geoms = [polygonal(g.intersection(states[sk])) for _, _, g in s_provs]
        # Attach coastal refinement fragments to nearest province of same state
        missing = polygonal(states[sk].difference(union_all(geoms)))
        for part in polygons(missing):
            idx = min(range(len(geoms)), key=lambda i: geoms[i].distance(part.representative_point()))
            geoms[idx] = polygonal(geoms[idx].union(part))
        colors = route_colors(geoms)
        nation = 'sanguo262-p-' + sk
        for idx, ((p_name, pages, _), geom, color) in enumerate(zip(s_provs, geoms, colors)):
            rid = f'sanguo262-r-{sk}-{idx}'
            rec = area_record(rid, p_name, '州' if p_name != '西域长史府' else '都护辖区', geom,
                              p=nation, nation=nation, sourcePage=pages, color=color,
                              description='州界依《中国历史地图集》第三册 262 年配准图复原。')
            route_records.append(rec)
            route_shapes[rid] = geom
            route_id_by_key[sk, p_name] = rid

    # Gather all commandery seats (CHGIS 262 + curated frontier commanderies)
    seats = []
    seen = set()
    for attrs, pt in snapshot(chgis / 'dataverse-2970286.zip', YEAR):
        name = attrs['NAME_CH'].strip()
        if not name or empire.distance(pt) > .35:
            continue
        sk = min(states, key=lambda k: states[k].distance(pt))
        if (sk, name) in seen:
            continue
        seen.add((sk, name))
        # Find parent province inside state
        cands = [(rid, route_shapes[rid]) for (k, _), rid in route_id_by_key.items() if k == sk]
        rid = min(cands, key=lambda item: item[1].distance(pt))[0]
        seats.append({
            'id': f'sanguo262-f-{attrs["SYS_ID"]}',
            'n': name, 'type': attrs['TYPE_CH'].strip() or '郡',
            'sk': sk, 'rid': rid, 'lon': pt.x, 'lat': pt.y, 'aliases': [],
        })
    for i, (sk, p_name, name, kind, lon, lat, aliases) in enumerate(EXTRA_COMMANDERIES):
        if (sk, name) in seen:
            for s in seats:
                if (s['sk'], s['n']) == (sk, name):
                    s['aliases'] = aliases
            continue
        seen.add((sk, name))
        rid = route_id_by_key[sk, p_name]
        seats.append({
            'id': f'sanguo262-f-ex-{i}',
            'n': name, 'type': kind,
            'sk': sk, 'rid': rid, 'lon': lon, 'lat': lat, 'aliases': aliases,
        })

    # Extract commandery polygons from zoom 7 + prefer CHGIS 262 vector polygons where available
    cmd_polys = extract_commandery_polygons(ccts_dir, seats, empire)
    chgis_polys = {}
    for attrs, area in snapshot(chgis / 'dataverse-2966510.zip', YEAR):
        if attrs['TYPE_CH'] == '非政区国土':
            continue
        chgis_polys.setdefault(attrs['NAME_CH'].strip(), []).append(polygonal(area))
    for s in seats:
        if s['n'] in chgis_polys:
            geom = polygonal(union_all(chgis_polys[s['n']], grid_size=.00001).intersection(route_shapes[s['rid']]))
            if not geom.is_empty and geom.area > .01:
                cmd_polys[s['id']] = geom

    city = []
    final_prefectures = {}
    for s in seats:
        nation = 'sanguo262-p-' + s['sk']
        sx, sy = xy(s['lon'], s['lat'])
        # Offset capital commandery label slightly so it doesn't collide with capital star
        if s['n'] == '河南尹':
            sx, sy = xy(112.45, 34.95)
        elif s['n'] == '蜀郡':
            sx, sy = xy(103.85, 31.02)
        elif s['n'] == '丹阳郡':
            sx, sy = xy(119.05, 31.55)
        rec = {
            'id': s['id'], 'n': s['n'], 'type': s['type'], 'p': s['rid'], 'nation': nation,
            'x': round(sx, 3), 'y': round(sy, 3), 'sourcePage': STATES[s['sk']][2],
        }
        if s['aliases']:
            rec['aliases'] = s['aliases']
        if s['id'] in cmd_polys:
            final_prefectures[s['id']] = cmd_polys[s['id']]
        else:
            rec['seat'] = True
        city.append(rec)

    # Assign CHGIS 262 county seats (1,022 counties)
    pref_ids = list(final_prefectures)
    pref_geoms = [final_prefectures[i] for i in pref_ids]
    pref_tree = STRtree(pref_geoms)
    seat_pts = [(s, Point(s['lon'], s['lat'])) for s in seats]
    county = []
    for attrs, pt in snapshot(chgis / 'county-points.zip', YEAR):
        name, kind = attrs['NAME_CH'].strip(), attrs['TYPE_CH'].strip() or '县'
        if not name or empire.distance(pt) > .28:
            continue
        sk = min(states, key=lambda k: states[k].distance(pt))
        hits = [i for i in pref_tree.query(pt, predicate='covered_by') if pref_ids[i] in final_prefectures]
        same_state_hits = [i for i in hits if next(c['nation'] for c in city if c['id'] == pref_ids[i]) == 'sanguo262-p-' + sk]
        if same_state_hits:
            pid = pref_ids[min(same_state_hits, key=lambda i: pref_geoms[i].area)]
        else:
            cands = [(s, sp) for s, sp in seat_pts if s['sk'] == sk]
            closest, _ = min(cands, key=lambda item: item[1].distance(pt))
            pid = closest['id']
        cx, cy = xy(pt.x, pt.y)
        county.append({
            'id': f'sanguo262-c-{attrs["SYS_ID"]}', 'n': name, 'type': kind, 'seat': True,
            'x': round(cx, 3), 'y': round(cy, 3), 'p': pid, 'nation': 'sanguo262-p-' + sk,
            'sourcePage': STATES[sk][2],
        })

    # Build top-level kingdom records
    province = []
    for sk, (name, kind, pages, color, level) in STATES.items():
        ident = 'sanguo262-p-' + sk
        item = area_record(ident, name, kind, states[sk], nation=ident, color=color, sourcePage='3–4',
                           detailLevel=level, description=STATE_NOTES[sk])
        pt = Point(STATE_ANCHORS[sk])
        if states[sk].covers(pt):
            item['x'], item['y'] = xy(pt.x, pt.y)
        if sk == 'shu':
            item['aliases'] = ['汉', '季汉', '蜀']
        elif sk == 'wei':
            item['aliases'] = ['曹魏']
        elif sk == 'wu':
            item['aliases'] = ['孙吴', '东吴']
        province.append(item)

    outline, linework = build_topology(
        province, route_records, city,
        {'sanguo262-p-' + k: g for k, g in states.items()},
        route_shapes, final_prefectures,
    )
    return {'province': province, 'route': route_records, 'city': city, 'county': county,
            'outline': outline, 'linework': linework}, states


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ccts_tiles', type=Path, help='Directory containing CCTS ad0262 zoom 6/7 tiles')
    parser.add_argument('chgis', type=Path, help='Directory with CHGIS V6 archives')
    parser.add_argument('water_source', type=Path, help='CHGIS V4 water tables')
    parser.add_argument('--elevation-cache', type=Path, default=Path(gettempdir()) / 'shanhe-atlas-elevation')
    parser.add_argument('--vectors-only', action='store_true')
    args = parser.parse_args()
    output = ROOT / 'dist/data/sanguo-262'
    (output / 'terrain').mkdir(parents=True, exist_ok=True)

    admin, states = build_admin(args.ccts_tiles, args.chgis, args.elevation_cache)
    save(output / 'admin-boundaries.json', admin)

    water, lakes = build_song_water(args.water_source, args.elevation_cache)
    save(output / 'terrain/water.json', water)

    for st in admin['province']:
        counts = [sum(r['nation'] == st['id'] for r in admin[k]) for k in ('route', 'city', 'county')]
        polys = sum(r['nation'] == st['id'] and 'g' in r for r in admin['city'])
        print(f"{st['n']:4s}: provinces={counts[0]:2d}, commanderies={counts[1]:3d} (polys={polys:3d}), counties={counts[2]:4d}", flush=True)

    if not args.vectors_only:
        areas = [(part.bounds, [list(r.coords) for r in (part.exterior, *part.interiors)])
                 for geom in states.values() for part in polygons(geom)]
        height = load_height(GRID, 30, 5, args.elevation_cache)
        save_grid(output / 'terrain/overview.hgt.gz', height.clip(min=0), GRID[0], GRID[3], 30, areas, lakes)


if __name__ == '__main__':
    main()
