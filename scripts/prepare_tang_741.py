"""Build the Tang 741 (Kaiyuan 29) atlas from CCTS ad0741 and CHGIS V6."""

import argparse
from collections import defaultdict
from pathlib import Path
from tempfile import gettempdir

import cv2
import numpy as np
from shapely import STRtree, difference, intersection, set_precision, transform, union_all
from shapely.geometry import LineString, Point, Polygon, box

from prepare_boundaries import save
from prepare_ming_1582 import snapshot
from prepare_qing_1820 import area_record, encode_area, polygonal, polygons, project_geom, xy
from prepare_song_1111 import load_ccts_rgba
from prepare_song_1208 import build_song_water, raster_geometry
from prepare_terrain import load_height, save_grid
from song_1208_coast import _clean_land, coast_reference
from song_1208_reference import OVERVIEW_FRAME, from_pixels, load_ccts, to_pixels, vectorize_coverage
from song_1208_topology import GRID_SIZE, _absorb_enclaves, partition, update_polygon
from tang_741_data import (
    CIRCUIT_ANCHORS, CIRCUIT_CONTROL_POINTS, CIRCUIT_NOTES,
    EXTRA_COUNTIES, EXTRA_PREFECTURES, TANG_CIRCUITS,
)


ROOT = Path(__file__).resolve().parents[1]
YEAR = 741
GRID = (45, 10, 150, 62)
TANG_FRAME = (7, 96, 44, 16, 14)

PREFECTURE_CIRCUITS = {
    name: key
    for key, (_, _, _, _, members) in TANG_CIRCUITS.items()
    for name in members.split()
}


def extract_tang_circuits(ccts_dir):
    """Extract the 15 Tang circuits, Western Regions, and Northeast Jimi frontier from CCTS ad0741."""
    # Extract Tang core land (excluding Tujue, Tubo, Nanzhao, Taiwan) from zoom 6
    rgba = load_ccts_rgba(ccts_dir, OVERVIEW_FRAME)
    r, g, b, a = rgba.transpose(2, 0, 1)
    land = a > 100
    orange = (r >= 145) & (g >= 90) & (g < 190) & (b <= 40) & land
    # Close the open Gobi desert gap between Hexi/Longyou and Guannei so Tujue (Mongolia)
    # stays cleanly separated from Tang's Longyou / Western Regions.
    barrier = orange.astype('uint8').copy()
    cv2.polylines(barrier, [to_pixels([97.5, 102.0, 107.0], [42.5, 41.8, 41.4])], False, 1, 5)

    closed = cv2.morphologyEx(barrier, cv2.MORPH_CLOSE,
                              cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    strokes = cv2.dilate(closed, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    _, labels, stats, _ = cv2.connectedComponentsWithStats((land & (strokes == 0)).astype('uint8'), connectivity=4)

    # Identify Tang empire cells (all 15 circuits; exclude Tujue, Tubo, Nanzhao, Taiwan)
    tang_comps = set()
    cell_owner = {}
    for key, (lon, lat) in CIRCUIT_CONTROL_POINTS.items():
        px, py = to_pixels([lon], [lat])[0]
        patch = labels[py - 4:py + 5, px - 4:px + 5].ravel()
        nz = patch[patch != 0]
        if len(nz):
            comp = int(np.bincount(nz).argmax())
            tang_comps.add(comp)
            cell_owner.setdefault(comp, []).append(key)

    # Exclude Taiwan (lon > 119.7, lat < 25.8)
    tw_x, tw_y = to_pixels([119.7], [25.8])[0]
    tw_mask = np.zeros_like(land)
    tw_mask[tw_y:, tw_x:] = True

    tang_mask = np.isin(labels, list(tang_comps)) & (~tw_mask)
    distance, nearest = cv2.distanceTransformWithLabels((~tang_mask).astype('uint8'), cv2.DIST_L2, 5,
                                                        labelType=cv2.DIST_LABEL_PIXEL)
    # Dilate tang_mask into its own orange stroke only (within 10px of tang_mask)
    empire_px = land & (~tw_mask) & (tang_mask | ((labels == 0) & (distance < 10)))

    # Vectorize the whole Tang empire smoothly
    empire_geom = polygonal(transform(
        vectorize_coverage([raster_geometry(empire_px)], 1.15)[0], from_pixels, interleaved=False
    ))

    # Extract individual circuit guides cleanly from OVERVIEW_FRAME (zoom 6) in one
    # consistent labeling pass so thick double-lined capital circuit borders (e.g. Jingji)
    # stay solid and no neighboring circuit (e.g. Hedong) can leak into a hollow border.
    exclude_pts = {'_tujue': (100.0, 48.0), '_tubo': (88.0, 32.0), '_nanzhao': (100.5, 25.0)}
    all_pts = {**CIRCUIT_CONTROL_POINTS, **exclude_pts}
    erode_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    guides = {}
    ink, fland = load_ccts(ccts_dir, OVERVIEW_FRAME)
    bar = ink.astype('uint8').copy()
    cv2.polylines(bar, [to_pixels([97.5, 102.0, 107.0], [42.5, 41.8, 41.4], OVERVIEW_FRAME)], False, 1, 5)
    for kernel in (7, 13, 19):
        cl = cv2.morphologyEx(bar, cv2.MORPH_CLOSE,
                              cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel, kernel)))
        st_dil = cv2.dilate(cl, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
        _, lab, st, _ = cv2.connectedComponentsWithStats((fland & (st_dil == 0)).astype('uint8'), connectivity=4)
        owners = defaultdict(set)
        for key, (lon, lat) in all_pts.items():
            px, py = to_pixels([lon], [lat], OVERVIEW_FRAME)[0]
            if not (0 <= py < lab.shape[0] and 0 <= px < lab.shape[1]):
                continue
            patch = lab[max(0, py - 3):py + 4, max(0, px - 3):px + 4].ravel()
            nz = patch[patch != 0]
            if len(nz):
                owners[int(np.bincount(nz).argmax())].add(key)
        for cell, keys in owners.items():
            if len(keys) != 1:
                continue
            key = next(iter(keys))
            if key.startswith('_') or key in guides:
                continue
            left, top, width, height, area = st[cell]
            if area < 500:
                continue
            core = cv2.erode((lab[top:top + height, left:left + width] == cell).astype('uint8'), erode_k) > 0
            if not core.any():
                continue
            geom = raster_geometry(core)
            guides[key] = polygonal(transform(geom, lambda x, y: from_pixels(x + left, y + top, OVERVIEW_FRAME), interleaved=False))

    return empire_geom, guides


def refine_tang_coast(empire, root, cache):
    modern, shore = coast_reference(root, cache)
    domain = empire.buffer(.78)
    coastal_band = shore.buffer(.86).intersection(box(107.65, 17.95, 124.2, 41.3)).intersection(domain)
    land = _clean_land(empire.difference(coastal_band).union(modern.intersection(coastal_band)), min_area=.001)
    return land


def _smooth_open_line(pts, passes=2):
    pts = list(pts)
    for _ in range(passes):
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            out.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            out.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        out.append(pts[-1])
        pts = out
    return pts


def split_anxi_beiting(circuits):
    """Split Anxi (south of Tianshan) and Beiting (north of Tianshan) from Longyou proper.

    Follows the actual Tianshan mountain crest (Chatkal / Kyrgyz / Terskey / Kokshaal /
    Khan Tengri / Narat / Borohoro / Bogda Shan) between Beiting and Anxi, and follows
    Tan Qixiang Vol. 5 (CCTS ad0741) curved grey prefecture boundaries between Anxi,
    Beiting, and Longyou (Xizhou / Yizhou).
    """
    longyou = circuits['longyou']
    # Tianshan crest from western Chatkal/Fergana ridge (64E) to Bogda Shan west of Turpan (87.4E)
    tianshan_ridge = _smooth_open_line([
        (64.0, 41.1), (66.5, 41.3), (68.2, 41.6), (69.8, 41.9), (71.2, 42.1),
        (72.6, 41.8), (74.0, 41.6), (75.4, 41.5), (76.8, 41.7), (78.2, 41.9),
        (79.6, 42.1), (80.5, 42.3), (81.8, 42.6), (83.0, 42.9), (84.2, 43.1),
        (85.5, 43.2), (86.6, 43.0), (87.4, 42.8),
    ], passes=2)
    # Beiting vs Longyou (northern rim of Xizhou/Turpan then curving north between Tingzhou and Yizhou)
    beiting_east = _smooth_open_line([
        (87.4, 42.8), (88.3, 43.0), (89.4, 43.3), (90.5, 43.4), (91.3, 43.3),
        (91.5, 43.9), (91.3, 44.5), (91.5, 45.2), (91.9, 46.2),
    ], passes=2)
    # Anxi vs Longyou (Vol. 5 ad0741 curved desert border west of Turpan & Lop Nur down to Altun Shan)
    anxi_east = _smooth_open_line([
        (87.4, 42.8), (88.0, 42.2), (88.4, 41.5), (87.8, 40.8), (86.9, 40.0),
        (86.1, 39.2), (85.4, 38.4), (85.1, 37.6), (85.4, 36.8), (86.0, 36.0),
        (86.5, 34.5),
    ], passes=2)

    tianshan_north = Polygon(tianshan_ridge + beiting_east[1:] + [(92.0, 52.0), (60.0, 52.0), (60.0, 41.1)])
    tianshan_south = Polygon(tianshan_ridge + anxi_east[1:] + [(86.5, 33.5), (60.0, 33.5), (60.0, 41.1)])

    beiting = polygonal(intersection(longyou, tianshan_north, grid_size=.00001))
    anxi = polygonal(intersection(longyou, tianshan_south, grid_size=.00001))
    rem = polygonal(difference(longyou, polygonal(union_all([beiting, anxi], grid_size=.00001)), grid_size=.00001))
    circuits['beiting'] = beiting
    circuits['anxi'] = anxi
    circuits['longyou'] = rem
    return circuits


def build_circuits(empire, guides, chgis_prefs):
    """Partition the Tang empire into 15 circuits, preserving CHGIS 741 vector boundaries."""
    keys = list(CIRCUIT_CONTROL_POINTS)
    west, south, east, north = empire.bounds
    rate = 75
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

    mapped_areas = {k: np.zeros(shape, np.uint8) for k in keys}
    ref_areas = {k: np.zeros(shape, np.uint8) for k in keys}
    known = {k: np.zeros(shape, np.uint8) for k in keys}
    surveyed = defaultdict(list)

    for name, geom in chgis_prefs.items():
        k = PREFECTURE_CIRCUITS.get(name)
        if k in mapped_areas:
            paint(mapped_areas[k], geom)
            surveyed[k].append(geom)

    for k, geom in guides.items():
        if k in ref_areas:
            paint(ref_areas[k], geom.intersection(empire))

    for k, pt in CIRCUIT_CONTROL_POINTS.items():
        cv2.circle(known[k], tuple(pixels([pt])[0]), 2, 255, -1)

    exact = np.maximum.reduce(list(mapped_areas.values()))
    for k in keys:
        ref_areas[k][exact != 0] = 0

    mask = np.zeros(shape, np.uint8)
    paint(mask, empire)
    nearest = np.zeros(shape, np.uint8)
    best = np.full(shape, np.inf, np.float32)
    for idx, k in enumerate(keys):
        seeds = cv2.bitwise_or(known[k], cv2.bitwise_or(mapped_areas[k], ref_areas[k]))
        dist = cv2.distanceTransform(255 - seeds, cv2.DIST_L2, 5)
        wins = dist < best
        best[wins] = dist[wins]
        nearest[wins] = idx

    raster = [raster_geometry((nearest == i) & (mask != 0)) for i in range(len(keys))]
    geoms = [
        polygonal(transform(g, lambda x, y: (x / rate + west, y / rate + south), interleaved=False).intersection(empire))
        for g in vectorize_coverage(raster, 2.4)
    ]

    missing = polygonal(empire.difference(union_all(geoms)))
    for part in polygons(missing):
        idx = min(range(len(geoms)), key=lambda i: geoms[i].distance(part.representative_point()))
        geoms[idx] = polygonal(geoms[idx].union(part))

    # Preserve exact CHGIS 741 vector prefecture boundaries where available
    precision = .00001
    mapped = {
        k: polygonal(intersection(polygonal(union_all(parts, grid_size=precision)), empire, grid_size=precision))
        for k, parts in surveyed.items() if parts
    }
    if mapped:
        filled = polygonal(union_all(list(mapped.values()), grid_size=precision))
        geoms = [
            polygonal(union_all([polygonal(difference(g, filled, grid_size=precision)), mapped[k]],
                                grid_size=precision)) if k in mapped
            else polygonal(difference(g, filled, grid_size=precision))
            for k, g in zip(keys, geoms)
        ]

    circuits = dict(zip(keys, geoms))
    return split_anxi_beiting(circuits)


def seat_record(ident, name, kind, key, point, parent=None, **details):
    x, y = xy(point.x, point.y)
    nation = 'tang741-p-' + key
    details.setdefault('sourcePage', TANG_CIRCUITS[key][2])
    return dict(id=ident, n=name, type=kind, seat=True, x=round(x, 3), y=round(y, 3),
                p=parent or nation, nation=nation, **details)


def build_admin(empire, guides, chgis):
    # 1. Load CHGIS 741 prefecture polygons clipped to Tang empire
    groups = defaultdict(list)
    for attrs, area in snapshot(chgis / 'dataverse-2966510.zip', YEAR):
        if attrs['TYPE_CH'] == '非政区国土':
            continue
        clipped = polygonal(polygonal(area).intersection(empire))
        if not clipped.is_empty:
            groups[attrs['NAME_CH']].append((attrs, clipped))

    chgis_prefs = {
        name: polygonal(union_all([g for _, g in entries], grid_size=.00001))
        for name, entries in groups.items()
    }
    chgis_attrs = {name: entries[0][0] for name, entries in groups.items()}

    # 2. Partition Tang empire into 17 top-level circuits (15 circuits + Xiyu + Northeast Jimi)
    circuits = build_circuits(empire, guides, chgis_prefs)

    # Project and cleanly partition top-level circuits on GRID_SIZE with enclave cleanup
    proj_circuits = {
        'tang741-p-' + k: polygonal(set_precision(project_geom(g), GRID_SIZE))
        for k, g in circuits.items()
    }
    proj_outline = polygonal(union_all(list(proj_circuits.values()), grid_size=GRID_SIZE))
    proj_circuits = _absorb_enclaves(proj_outline, partition(proj_outline, proj_circuits, complete=True))

    # Build circuit records
    province = []
    for k, (name, kind, pages, color, _) in TANG_CIRCUITS.items():
        ident = 'tang741-p-' + k
        geom = proj_circuits[ident]
        rec = {'id': ident, 'n': name, 'type': kind, 'nation': ident, 'color': color,
               'sourcePage': pages, 'description': CIRCUIT_NOTES[k]}
        ax, ay = xy(*CIRCUIT_ANCHORS[k])
        rec['x'], rec['y'] = round(ax, 3), round(ay, 3)
        update_polygon(rec, geom)
        province.append(rec)

    # 3. Assign prefectures (polygons + seats) to circuits
    city = []
    city_by_name = {}
    city_shapes_geo, city_ids = [], []

    def circuit_for(name, geom_or_pt):
        if name in PREFECTURE_CIRCUITS:
            return PREFECTURE_CIRCUITS[name]
        return min(circuits, key=lambda k: circuits[k].distance(geom_or_pt))

    for name, geom in chgis_prefs.items():
        attrs = chgis_attrs[name]
        k = circuit_for(name, geom)
        ident = f'tang741-f-{attrs["SYS_ID"]}'
        nation = 'tang741-p-' + k
        rec = area_record(ident, name, attrs['TYPE_CH'], geom, p=nation, nation=nation, sourcePage=TANG_CIRCUITS[k][2])
        city.append(rec)
        city_by_name[name] = rec, geom
        city_shapes_geo.append(geom)
        city_ids.append(ident)

    # Add CHGIS 741 prefecture seat points
    for attrs, pt in snapshot(chgis / 'dataverse-2970286.zip', YEAR):
        name = attrs['NAME_CH']
        if not name or empire.distance(pt) > .35:
            continue
        if name in city_by_name:
            rec, geom = city_by_name[name]
            if geom is not None and geom.covers(pt):
                rec['x'], rec['y'] = (round(v, 3) for v in xy(pt.x, pt.y))
        else:
            k = circuit_for(name, pt)
            rec = seat_record(f'tang741-f-p{attrs["SYS_ID"]}', name, attrs['TYPE_CH'] or '州', k, pt)
            city.append(rec)
            city_by_name[name] = rec, None

    # Add curated Western Regions / Northeast Jimi / Annan prefectures
    for i, (k, name, kind, lon, lat, pages, aliases) in enumerate(EXTRA_PREFECTURES):
        if name in city_by_name:
            city_by_name[name][0].setdefault('aliases', aliases)
            continue
        pt = Point(lon, lat)
        rec = seat_record(f'tang741-f-ex-{i}', name, kind, k, pt, aliases=aliases,
                          sourcePage=pages, description='参照《中国历史地图集》第五册及《旧唐书·地理志》，点位为约略定位。')
        city.append(rec)
        city_by_name[name] = rec, None

    # Partition prefecture polygons cleanly inside each circuit (absorbing coastal shift slivers)
    for rec in province:
        cid = rec['id']
        parent = proj_circuits[cid]
        c_prefs = [p for p in city if p['p'] == cid]
        mapped_prefs = [p for p in c_prefs if p['n'] in chgis_prefs]
        if not mapped_prefs:
            continue
        unmapped_seats = [Point(p['x'], p['y']) for p in c_prefs if p['n'] not in chgis_prefs]
        cands = {p['id']: polygonal(set_precision(project_geom(chgis_prefs[p['n']]), GRID_SIZE)) for p in mapped_prefs}
        children = partition(parent, cands, complete=(len(unmapped_seats) == 0), unmapped_seats=unmapped_seats)
        for p in mapped_prefs:
            if p['id'] in children:
                update_polygon(p, children[p['id']])
            else:
                p.pop('b', None)
                p.pop('g', None)
                p['seat'] = True

    # 4. Assign CHGIS 741 county seats (1,492 counties!)
    pref_tree = STRtree(city_shapes_geo)
    all_pref_pts = [(r, Point(r['x'] / 14 + 62, 57 - r['y'] / 17)) for r in city]
    county = []
    for attrs, pt in snapshot(chgis / 'county-points.zip', YEAR):
        name, kind = attrs['NAME_CH'], attrs['TYPE_CH']
        if not name or not kind or empire.distance(pt) > .28:
            continue
        hits = list(pref_tree.query(pt, predicate='covered_by'))
        details = {}
        if hits:
            parent_id = city_ids[min(hits, key=lambda i: city_shapes_geo[i].area)]
            parent_rec = next(r for r in city if r['id'] == parent_id)
            k = parent_rec['nation'].split('-')[-1]
        else:
            closest, anchor = min(all_pref_pts, key=lambda entry: entry[1].distance(pt))
            if anchor.distance(pt) < 1.3:
                parent_id = closest['id']
                k = closest['nation'].split('-')[-1]
                details['description'] = '府州关联按治所位置推定。'
            else:
                k = min(circuits, key=lambda ck: circuits[ck].distance(pt))
                parent_id = 'tang741-p-' + k
                details['description'] = '所属道按地望推定。'
        county.append(seat_record(f'tang741-c-{attrs["SYS_ID"]}', name, kind, k, pt, parent=parent_id, **details))

    # Add curated frontier counties (Xiyu, Yingzhou, Annan)
    existing_counties = {(r['n'], r['p']) for r in county}
    for pname, places in EXTRA_COUNTIES.items():
        if pname not in city_by_name:
            continue
        prec, _ = city_by_name[pname]
        k = prec['nation'].split('-')[-1]
        for offset, (cname, lon, lat) in enumerate(places):
            if (cname, prec['id']) in existing_counties:
                continue
            county.append(seat_record(f'{prec["id"]}-c{offset}', cname, '县', k, Point(lon, lat),
                                      parent=prec['id'], sourcePage=prec['sourcePage'],
                                      description='参照《中国历史地图集》第五册及《旧唐书·地理志》，点位为约略定位。'))

    return {'province': province, 'city': city, 'county': county, 'outline': encode_area(proj_outline)}, circuits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ccts_tiles', type=Path, help='Directory containing CCTS ad0741 zoom 6/7 tiles')
    parser.add_argument('chgis', type=Path, help='Directory with CHGIS V6 archives')
    parser.add_argument('water_source', type=Path, help='CHGIS V4 water tables')
    parser.add_argument('--elevation-cache', type=Path, default=Path(gettempdir()) / 'shanhe-atlas-elevation')
    parser.add_argument('--vectors-only', action='store_true')
    args = parser.parse_args()
    output = ROOT / 'dist/data/tang-741'
    (output / 'terrain').mkdir(parents=True, exist_ok=True)

    print('Extracting Tang 741 circuits from CCTS ad0741', flush=True)
    empire, guides = extract_tang_circuits(args.ccts_tiles)
    print('Tang circuit guides extracted:', len(guides), flush=True)
    empire = refine_tang_coast(empire, ROOT, args.elevation_cache)
    print('Refined Tang coastlines and cleaned interior holes', flush=True)

    admin, circuits = build_admin(empire, guides, args.chgis)
    save(output / 'admin-boundaries.json', admin)

    water, lakes = build_song_water(args.water_source, args.elevation_cache)
    save(output / 'terrain/water.json', water)

    print(f"Tang 741 totals: circuits={len(admin['province'])}, prefectures={len(admin['city'])}, counties={len(admin['county'])}", flush=True)
    for rec in admin['province']:
        c_cnt = sum(r['nation'] == rec['id'] for r in admin['city'])
        x_cnt = sum(r['nation'] == rec['id'] for r in admin['county'])
        print(f"  {rec['n']:10s}: prefs={c_cnt:3d}, counties={x_cnt:3d}" + (' [frontier]' if rec.get('frontier') else ''), flush=True)

    if not args.vectors_only:
        areas = [(part.bounds, [list(r.coords) for r in (part.exterior, *part.interiors)])
                 for geom in circuits.values() for part in polygons(geom)]
        height = load_height(GRID, 30, 5, args.elevation_cache)
        save_grid(output / 'terrain/overview.hgt.gz', height.clip(min=0), GRID[0], GRID[3], 30, areas, lakes)


if __name__ == '__main__':
    main()
