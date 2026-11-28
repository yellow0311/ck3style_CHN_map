"""Build the Sui 612 (Daye 8) commandery-and-county atlas from CCTS ad0612 and CHGIS V6."""

import argparse
from collections import defaultdict
from pathlib import Path
from tempfile import gettempdir

import cv2
import numpy as np
from shapely import STRtree, set_precision, transform, union_all
from shapely.geometry import Point, box

from prepare_boundaries import save
from prepare_ming_1582 import snapshot
from prepare_qing_1820 import encode_area, polygonal, polygons, project_geom, xy
from prepare_song_1111 import load_ccts_rgba
from prepare_song_1208 import build_song_water, raster_geometry, route_colors
from prepare_terrain import load_height, save_grid
from song_1208_coast import _clean_land, coast_reference
from song_1208_reference import from_pixels, to_pixels, vectorize_coverage
from song_1208_topology import GRID_SIZE, _absorb_enclaves, partition, update_polygon


ROOT = Path(__file__).resolve().parents[1]
YEAR = 612
GRID = (60, 10, 145, 55)
# Zoom 7 cols 93..111, rows 46..58 (covers 81.5E..135E, 16N..46N; falls back to zoom 6 where needed)
SUI_FRAME = (7, 93, 46, 19, 12)

# Duplicate or non-commandery CHGIS 612 seat names to skip so canonical Sui commanderies own their cells.
SKIP_SEATS = {'应州', '宜阳郡', '万州', '南宁州', '渠滥川', '越析州', '宁州'}

# Curated Sui 612 commanderies missing from CHGIS 612 point table (Vol. 5 Daye 8 plates & Sui shu 29-31).
EXTRA_COMMANDERIES = [
    ('伊吾郡', '郡', 93.515, 42.826, ['伊州', '哈密']),
    ('鄯善郡', '郡', 89.800, 39.200, ['罗布泊', '若羌']),
    ('且末郡', '郡', 85.530, 38.140, []),
    ('西海郡', '郡', 100.850, 36.950, ['伏俟城', '青海湖']),
    ('河源郡', '郡', 99.600, 35.600, ['赤水城']),
    ('五原郡', '郡', 108.180, 40.980, ['五原']),
    ('榆林郡', '郡', 110.950, 40.280, ['胜州']),
    ('定襄郡', '郡', 111.880, 40.650, ['大利城']),
    ('柳城郡', '郡', 120.452, 41.579, ['营州', '朝阳']),
    ('辽西郡', '郡', 121.860, 41.590, ['汝罗']),
    ('渔阳郡', '郡', 117.660, 40.000, ['无终', '蓟县']),
    ('安乐郡', '郡', 116.850, 40.373, ['燕乐', '密云']),
    ('下邳郡', '郡', 118.180, 33.800, ['宿迁']),
    ('江夏郡', '郡', 114.300, 30.550, ['武昌']),
    ('泸川郡', '郡', 105.420, 28.880, ['泸州']),
    ('会宁郡', '郡', 104.850, 36.370, ['靖远']),
    ('明阳郡', '郡', 107.830, 27.860, []),
    ('北地郡', '郡', 108.100, 35.340, ['定安', '宁县']),
    ('淮安郡', '郡', 113.340, 32.780, ['比阳']),
    ('汲郡', '郡', 114.830, 35.390, ['卫县']),
    ('汉阳郡', '郡', 105.200, 34.050, ['上邽']),
    ('信安郡', '郡', 112.460, 23.050, ['高要', '肇庆']),
    ('东郡', '郡', 114.950, 35.480, ['白马', '滑县']),
    ('东平郡', '郡', 116.120, 35.880, ['郓城', '东平']),
    ('僚', '羁縻区', 105.420, 28.190, ['西南僚人']),
    ('交趾郡', '郡', 105.834, 21.028, ['宋平', '河内']),
    ('九真郡', '郡', 105.780, 19.810, ['清化']),
    ('日南郡', '郡', 105.680, 18.670, ['荣市']),
    ('珠崖郡', '郡', 110.350, 19.950, ['义伦', '琼山']),
    ('儋耳郡', '郡', 109.170, 19.520, ['义伦', '儋州']),
]

# Secondary seeds for commanderies split across the Yangtze River by the blue water barrier.
SECONDARY_SEEDS = {
    '江夏郡': [(114.47, 29.86)],
    '南郡': [(111.61, 30.17)],
}

# External polities to exclude cleanly from Sui territory.
EXCLUDE_POINTS = [
    (102.0, 45.0),  # 东突厥
    (88.0, 44.0),   # 西突厥
    (91.0, 31.0),   # 吐蕃
    (100.0, 23.5),  # 云南南端外部
    (123.5, 41.5),  # 高句丽
    (121.0, 23.8),  # 流求（台湾）
]


def extract_sui_commanderies(ccts_dir, seats):
    """Extract all Sui 612 commanderies from CCTS ad0612 zoom 7 with orange+blue barriers."""
    rgba = load_ccts_rgba(ccts_dir, SUI_FRAME)
    r, g, b, a = rgba.transpose(2, 0, 1)
    land = a > 100
    orange = (r >= 145) & (g >= 90) & (g < 190) & (b <= 40) & land
    blue = (b.astype(int) - r.astype(int) > 15) & (b > 170) & land

    closed = cv2.morphologyEx((orange | blue).astype('uint8'), cv2.MORPH_CLOSE,
                              cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    strokes = cv2.dilate(closed, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    _, labels, stats, _ = cv2.connectedComponentsWithStats((land & (strokes == 0)).astype('uint8'), connectivity=4)

    # Identify excluded external cells
    excluded = set()
    for lon, lat in EXCLUDE_POINTS:
        px, py = to_pixels([lon], [lat], SUI_FRAME)[0]
        if 0 <= py < labels.shape[0] and 0 <= px < labels.shape[1]:
            patch = labels[max(0, py - 4):py + 5, max(0, px - 4):px + 5].ravel()
            nz = patch[patch != 0]
            if len(nz):
                excluded.add(int(np.bincount(nz).argmax()))

    # Exclude Taiwan explicitly
    tw_x, tw_y = to_pixels([119.7], [25.8], SUI_FRAME)[0]
    tw_mask = np.zeros_like(land)
    tw_mask[tw_y:, tw_x:] = True

    # Map each commandery seat to its connected component cell
    cell_to_seat = {}
    seat_cells = []
    for seat in seats:
        px, py = to_pixels([seat['lon']], [seat['lat']], SUI_FRAME)[0]
        if not (0 <= py < labels.shape[0] and 0 <= px < labels.shape[1]):
            continue
        patch = labels[max(0, py - 4):py + 5, max(0, px - 4):px + 5].ravel()
        nz = patch[patch != 0]
        if not len(nz):
            continue
        comp = int(np.bincount(nz).argmax())
        if comp in excluded or comp in cell_to_seat:
            continue
        if stats[comp, cv2.CC_STAT_AREA] > 280000:
            continue
        cell_to_seat[comp] = len(seat_cells) + 1
        seat_cells.append(seat)
        for slon, slat in SECONDARY_SEEDS.get(seat['n'], ()):
            spx, spy = to_pixels([slon], [slat], SUI_FRAME)[0]
            if 0 <= spy < labels.shape[0] and 0 <= spx < labels.shape[1]:
                spatch = labels[max(0, spy - 4):spy + 5, max(0, spx - 4):spx + 5].ravel()
                snz = spatch[spatch != 0]
                if len(snz):
                    scomp = int(np.bincount(snz).argmax())
                    if scomp not in excluded and scomp not in cell_to_seat:
                        cell_to_seat[scomp] = len(seat_cells)

    lookup = np.zeros(len(stats), np.uint16)
    for comp, idx in cell_to_seat.items():
        lookup[comp] = idx

    marked = lookup[labels]
    marked[tw_mask] = 0
    # Split orange borders & river strokes cleanly down their exact centerlines
    distance, nearest = cv2.distanceTransformWithLabels((marked == 0).astype('uint8'), cv2.DIST_L2, 5,
                                                        labelType=cv2.DIST_LABEL_PIXEL)
    owner = np.zeros(nearest.max() + 1, np.uint16)
    seeds = marked > 0
    owner[nearest[seeds]] = marked[seeds]
    coverage = np.where(land & (~tw_mask) & ((marked > 0) | ((labels == 0) & (distance < 16))), owner[nearest], 0)

    masks = [raster_geometry(coverage == i) for i in range(1, len(seat_cells) + 1)]
    smoothed = vectorize_coverage(masks, 1.35)
    result = {}
    for seat, geom in zip(seat_cells, smoothed):
        poly = polygonal(transform(geom, lambda x, y: from_pixels(x, y, SUI_FRAME), interleaved=False))
        if not poly.is_empty:
            result[seat['id']] = (seat, poly)
    return result


def refine_sui_coasts(commanderies, root, cache):
    """Apply detailed coastline to coastal Sui commanderies and clean interior holes."""
    modern, shore = coast_reference(root, cache)
    old = polygonal(union_all([g for _, g in commanderies.values()]))
    domain = old.buffer(.78)
    coastal_band = shore.buffer(.86).intersection(box(107.65, 17.95, 124.2, 41.3)).intersection(domain)
    land = _clean_land(old.difference(coastal_band).union(modern.intersection(coastal_band)), min_area=.001)

    ids = list(commanderies)
    geoms = [commanderies[i][1] for i in ids]
    tree = STRtree(geoms)
    extras = defaultdict(list)
    for part in polygons(land.difference(old)):
        pt = part.representative_point()
        owner = ids[tree.nearest(pt)]
        extras[owner].append(part)

    output = {}
    for ident, (seat, geom) in commanderies.items():
        parts = [geom.intersection(land), *extras[ident]]
        cleaned = _clean_land(union_all(parts), min_area=.001)
        if not cleaned.is_empty:
            output[ident] = (seat, cleaned)
    return output


def build_admin(ccts_dir, chgis, elevation_cache):
    # 1. Gather all unique Sui 612 commandery seats (CHGIS 612 + curated border commanderies)
    seats = []
    seen_names = set()
    for attrs, pt in snapshot(chgis / 'dataverse-2970286.zip', YEAR):
        name = attrs['NAME_CH'].strip()
        if not name or name in SKIP_SEATS or name in seen_names:
            continue
        seen_names.add(name)
        seats.append({
            'id': f'sui612-j-{attrs["SYS_ID"]}',
            'n': name,
            'type': attrs['TYPE_CH'].strip() or '郡',
            'lon': pt.x,
            'lat': pt.y,
            'aliases': [],
        })
    for idx, (name, kind, lon, lat, aliases) in enumerate(EXTRA_COMMANDERIES):
        if name in seen_names:
            for s in seats:
                if s['n'] == name:
                    s['aliases'] = aliases
            continue
        seen_names.add(name)
        seats.append({
            'id': f'sui612-j-ex-{idx}',
            'n': name,
            'type': kind,
            'lon': lon,
            'lat': lat,
            'aliases': aliases,
        })

    # 2. Extract exact commandery polygons from CCTS ad0612 zoom 7 & refine coasts
    raw_cmds = extract_sui_commanderies(ccts_dir, seats)
    print(f'Extracted {len(raw_cmds)} Sui commandery polygons from CCTS ad0612', flush=True)
    cmds = refine_sui_coasts(raw_cmds, ROOT, elevation_cache)

    # 3. Project & enforce watertight shared-edge topology + enclave cleanup
    proj_cmds = {
        ident: polygonal(set_precision(project_geom(geom), GRID_SIZE))
        for ident, (_, geom) in cmds.items()
    }
    proj_outline = polygonal(union_all(list(proj_cmds.values()), grid_size=GRID_SIZE))
    proj_cmds = _absorb_enclaves(proj_outline, partition(proj_outline, proj_cmds, complete=True))

    # 4. Graph-color all commanderies so no two adjacent commanderies share a color
    cmd_ids = list(proj_cmds)
    colors = route_colors([proj_cmds[i] for i in cmd_ids])

    province = []
    geo_geoms = []
    for ident, color in zip(cmd_ids, colors):
        seat, geo_geom = cmds[ident]
        geom = proj_cmds[ident]
        sx, sy = xy(seat['lon'], seat['lat'])
        rec = {
            'id': ident,
            'n': seat['n'],
            'type': seat['type'],
            'nation': ident,
            'color': color,
            'sourcePage': '3–30',
            'x': round(sx, 3),
            'y': round(sy, 3),
            'description': '大业八年（612 年）隋朝郡级辖区，界线依《中国历史地图集》第五册配准复原。',
        }
        if seat['aliases']:
            rec['aliases'] = seat['aliases']
        update_polygon(rec, geom)
        province.append(rec)
        geo_geoms.append((ident, geo_geom))

    # 5. Assign CHGIS 612 county seats (1,070 counties) to their containing commandery
    empire_geo = polygonal(union_all([g for _, g in geo_geoms]))
    cmd_tree = STRtree([g for _, g in geo_geoms])
    county = []
    for attrs, pt in snapshot(chgis / 'county-points.zip', YEAR):
        name, kind = attrs['NAME_CH'].strip(), attrs['TYPE_CH'].strip() or '县'
        if not name or empire_geo.distance(pt) > .25:
            continue
        hits = list(cmd_tree.query(pt, predicate='covered_by'))
        if hits:
            parent_id = geo_geoms[min(hits, key=lambda i: geo_geoms[i][1].area)][0]
        else:
            parent_id = geo_geoms[cmd_tree.nearest(pt)][0]
        cx, cy = xy(pt.x, pt.y)
        county.append({
            'id': f'sui612-c-{attrs["SYS_ID"]}',
            'n': name,
            'type': kind,
            'seat': True,
            'x': round(cx, 3),
            'y': round(cy, 3),
            'p': parent_id,
            'nation': parent_id,
            'sourcePage': '3–30',
        })

    return {'province': province, 'city': [], 'county': county, 'outline': encode_area(proj_outline)}, [g for _, g in geo_geoms]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ccts_tiles', type=Path, help='Directory containing CCTS ad0612 zoom 6/7 tiles')
    parser.add_argument('chgis', type=Path, help='Directory with CHGIS V6 archives')
    parser.add_argument('water_source', type=Path, help='CHGIS V4 water tables')
    parser.add_argument('--elevation-cache', type=Path, default=Path(gettempdir()) / 'shanhe-atlas-elevation')
    parser.add_argument('--vectors-only', action='store_true')
    args = parser.parse_args()
    output = ROOT / 'dist/data/sui-612'
    (output / 'terrain').mkdir(parents=True, exist_ok=True)

    admin, land_geoms = build_admin(args.ccts_tiles, args.chgis, args.elevation_cache)
    save(output / 'admin-boundaries.json', admin)

    water, lakes = build_song_water(args.water_source, args.elevation_cache)
    save(output / 'terrain/water.json', water)

    print(f"Sui 612 totals: commanderies={len(admin['province'])}, counties={len(admin['county'])}", flush=True)

    if not args.vectors_only:
        areas = [(part.bounds, [list(r.coords) for r in (part.exterior, *part.interiors)])
                 for geom in land_geoms for part in polygons(geom)]
        height = load_height(GRID, 30, 5, args.elevation_cache)
        save_grid(output / 'terrain/overview.hgt.gz', height.clip(min=0), GRID[0], GRID[3], 30, areas, lakes)


if __name__ == '__main__':
    main()
