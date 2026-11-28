"""Apply the atlas's detailed coast reference to the 1208 land coverage."""

import json

from shapely import make_valid, union_all
from shapely.geometry import Polygon, box, shape

from prepare_qing_1820 import polygonal, polygons
from prepare_terrain import shape_reader


def decode_rings(encoded, unproject):
    rings = []
    for path in encoded.split('!'):
        x = y = value = shift = 0
        coordinate = []
        ring = []
        for character in path:
            chunk = ord(character)-63
            value |= (chunk & 31) << shift
            if chunk >= 32:
                shift += 5
                continue
            coordinate.append(-(value//2)-1 if value & 1 else value//2)
            value = shift = 0
            if len(coordinate) == 2:
                x += coordinate[0]
                y += coordinate[1]
                ring.append(unproject(x/1000,y/1000))
                coordinate.clear()
        if len(ring) >= 3:
            poly = make_valid(Polygon(ring))
            if not poly.is_empty and poly.area > 0:
                rings.append((poly.area, ring, poly))
    # Reconstruct exterior rings and interior holes using even-odd containment.
    rings.sort(key=lambda item: item[0], reverse=True)
    nodes = []
    for area, coords, poly in rings:
        pt = poly.representative_point()
        parent = None
        for idx in range(len(nodes)-1, -1, -1):
            if nodes[idx]['poly'].covers(pt):
                parent = idx
                break
        depth = 0 if parent is None else nodes[parent]['depth']+1
        nodes.append({'coords': coords, 'poly': poly, 'parent': parent, 'depth': depth, 'holes': []})
        if depth % 2 == 1:
            nodes[parent]['holes'].append(coords)
    for node in nodes:
        if node['depth'] % 2 == 0:
            poly = make_valid(Polygon(node['coords'], node['holes']))
            if not poly.is_empty and poly.area > 0:
                yield poly


def _clean_land(geometry, min_area=.0012, max_hole_area=.5):
    """Drop micro-islets and fill spurious interior holes (river mouths, seam gaps, raster noise)."""
    kept = []
    for p in polygons(geometry):
        if p.area < min_area:
            continue
        holes = [r for r in p.interiors if Polygon(r).area >= max_hole_area]
        kept.append(Polygon(p.exterior, holes))
    if not kept:
        return polygonal(geometry)
    return polygonal(union_all(kept))


def coast_reference(root,cache):
    data = root/'dist/data'
    overview = json.loads((data/'china-boundaries/overview.json').read_text(encoding='utf-8'))
    modern_ids = {'210000','120000','130000','370000','320000','310000','330000','350000','440000',
                  '450000','460000','810000','820000'}
    modern = _clean_land(union_all([
        part for ident,outline,*_ in overview['provinces'] if ident in modern_ids
        for part in decode_rings(outline, lambda x,y:(73+x/14,54-y/17))
    ]))
    domain = box(105,17.5,145,59)
    natural_land = union_all([make_valid(shape(row.__geo_interface__)).intersection(domain)
                              for row in shape_reader('land',cache).iterShapes()
                              if row.bbox[0] < 145 and row.bbox[2] > 105 and row.bbox[1] < 59 and row.bbox[3] > 17.5])
    # This intersection screens out inland provincial borders. Subsequent
    # edits use the project's coast geometry, including small islands.
    coastal_domain = box(107.5,18,124.2,41.3)
    shore = modern.boundary.intersection(natural_land.boundary.buffer(.37)).intersection(coastal_domain)
    return modern,shore


def refine_coasts(states,root,cache):
    modern,shore = coast_reference(root,cache)
    old = union_all([states['song'],states['jin']])
    # Change geometry only in the coastal strip. Leave the ancient Yellow
    # River and the plotted land boundary independent of today's state lines.
    # The neighboring Dali and other jurisdictions must keep their coverage.
    others = union_all([g for key,g in states.items() if key not in ('song','jin')])
    domain = old.buffer(.78).difference(others)
    coastal_band = shore.buffer(.86).intersection(box(107.65,17.95,124.2,41.3)).intersection(domain)
    land = _clean_land(old.difference(coastal_band).union(modern.intersection(coastal_band)), min_area=.001)
    fragments = {'song':[], 'jin':[]}
    for part in polygons(land.difference(old)):
        point = part.representative_point()
        owner = min(fragments,key=lambda key:states[key].distance(point))
        fragments[owner].append(part)
    output = {key: _clean_land(geom, min_area=.004) for key, geom in states.items()}
    for key in ('song','jin'):
        original = states[key]
        geom = union_all([original.intersection(land),*fragments[key]])
        output[key] = _clean_land(geom, min_area=.001)
    return output
