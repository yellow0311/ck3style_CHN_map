"""Make the 1208 fill polygons and their visible hierarchy use one line network."""

from shapely import STRtree, difference, intersection, line_merge, make_valid, set_precision, union_all
from shapely.algorithms.polylabel import polylabel
from shapely.geometry import Point

from prepare_boundaries import encode_ring
from prepare_qing_1820 import encode_area, lines, polygonal, polygons, project_geom


# This is the same millesimal coordinate grid used by the browser encoding.
GRID_SIZE = .001


def project_partitions(geometries):
    return {ident: polygonal(set_precision(make_valid(project_geom(geometry)), GRID_SIZE))
            for ident,geometry in geometries.items()}


def _pick_owner(part, ids, geoms, tree):
    """Pick the adjacent child sharing the longest border, falling back to nearest."""
    candidates = tree.query(part.buffer(0.05))
    best_id, best_shared = None, 0.0
    for idx in candidates:
        shared = part.boundary.intersection(geoms[idx].boundary).length
        if shared > best_shared:
            best_shared = shared
            best_id = ids[idx]
    if best_id is not None:
        return best_id
    return ids[tree.nearest(part.representative_point())]


def partition(parent,candidates,complete,unmapped_seats=()):
    """Clip child polygons to their parent and resolve competing areas once."""
    available = parent
    children = {}
    for ident,geometry in candidates.items():
        child = polygonal(intersection(geometry,available,grid_size=GRID_SIZE))
        if child.is_empty:
            continue
        # Return micro-slivers to available so they can be cleanly merged.
        kept = [p for p in polygons(child) if p.area >= 0.05]
        if not kept:
            continue
        child = polygonal(union_all(kept,grid_size=GRID_SIZE))
        children[ident] = child
        available = polygonal(difference(available,child,grid_size=GRID_SIZE))
    if not available.is_empty and children:
        ids = list(children)
        geoms = list(children.values())
        nearest = STRtree(geoms)
        patches = {ident:[] for ident in ids}
        for part in polygons(available):
            if complete:
                absorb = True
            else:
                has_unmapped = any(part.buffer(0.8).covers(seat) for seat in unmapped_seats)
                is_sliver = part.area < 28.0 or (part.area < 140.0 and part.area / max(part.length, 1e-6) < 2.2)
                absorb = (not has_unmapped) and is_sliver
            if absorb:
                patches[_pick_owner(part, ids, geoms, nearest)].append(part)
        children = {ident:polygonal(union_all([geometry,*patches[ident]],grid_size=GRID_SIZE))
                    if patches[ident] else geometry for ident,geometry in children.items()}
    return children


def update_polygon(record,geometry):
    record['b'] = [round(value,3) for value in geometry.bounds]
    record['g'] = encode_area(geometry)
    if not record.get('seat') and not geometry.covers(Point(record['x'],record['y'])):
        center = polylabel(max(polygons(geometry),key=lambda part:part.area),tolerance=.4)
        record['x'],record['y'] = round(center.x,3),round(center.y,3)


def encode_internal_edges(parent,children):
    edges = union_all([geometry.boundary for geometry in children.values()],grid_size=GRID_SIZE)
    # Remove rounding remnants along a higher-level line before painting
    # the lower-level network. The clearance is below the displayed stroke.
    internal = line_merge(difference(edges,parent.boundary.buffer(.025),grid_size=GRID_SIZE))
    return '!'.join(encode_ring([(round(x*1000),round(y*1000)) for x,y in edge.coords])
                    for edge in lines(internal) if edge.length >= 0.18)


def _absorb_enclaves(parent, zones, max_area=120.0):
    """Merge spurious inland route enclaves completely enclosed by a single neighbor."""
    ids = list(zones)
    if len(ids) < 2:
        return zones
    parent_edge = parent.boundary.buffer(0.05)
    changed = True
    while changed:
        changed = False
        geoms = [zones[i] for i in ids]
        tree = STRtree(geoms)
        moves = []
        for idx, ident in enumerate(ids):
            parts = list(polygons(zones[ident]))
            if len(parts) <= 1:
                continue
            largest = max(p.area for p in parts)
            for part in parts:
                if part.area >= largest or part.area > max_area:
                    continue
                if part.boundary.intersects(parent_edge):
                    continue
                nbrs = [j for j in tree.query(part.buffer(0.05)) if j != idx]
                best_j, best_len = None, 0.0
                for j in nbrs:
                    shared = part.boundary.intersection(geoms[j].boundary).length
                    if shared > best_len:
                        best_len = shared
                        best_j = j
                if best_j is not None and best_len >= part.boundary.length * 0.9:
                    moves.append((ident, ids[best_j], part))
        if moves:
            changed = True
            for src, dst, part in moves:
                zones[src] = polygonal(difference(zones[src], part, grid_size=GRID_SIZE))
                zones[dst] = polygonal(union_all([zones[dst], part], grid_size=GRID_SIZE))
    return zones


def build_topology(provinces,routes,prefectures,state_shapes,route_shapes,prefecture_shapes):
    states = project_partitions(state_shapes)
    outline = polygonal(union_all(list(states.values()),grid_size=GRID_SIZE))
    states = partition(outline,states,complete=True)
    subregions = project_partitions(route_shapes)
    prefecture_polygons = project_partitions(prefecture_shapes)
    linework = {'state':encode_internal_edges(outline,states),'route':{},'prefecture':{}}
    for state in provinces:
        state_id = state['id']
        parent = states[state_id]
        update_polygon(state,parent)
        subdivisions = {r['id']:subregions[r['id']] for r in routes if r['p']==state_id}
        if not subdivisions:
            continue
        zones = _absorb_enclaves(parent, partition(parent,subdivisions,complete=True))
        linework['route'][state_id] = encode_internal_edges(parent,zones)
        for route in routes:
            route_id = route['id']
            if route_id not in zones:
                continue
            route_shape = zones[route_id]
            update_polygon(route,route_shape)
            route_prefs = [p for p in prefectures if p['p']==route_id]
            records = [p for p in route_prefs if p['id'] in prefecture_polygons]
            if not records:
                continue
            unmapped_seats = [Point(p['x'],p['y']) for p in route_prefs if p['id'] not in prefecture_polygons]
            children = partition(route_shape,{p['id']:prefecture_polygons[p['id']] for p in records},
                                 complete=(len(unmapped_seats)==0), unmapped_seats=unmapped_seats)
            linework['prefecture'][route_id] = encode_internal_edges(route_shape,children)
            for record in records:
                if record['id'] in children:
                    update_polygon(record,children[record['id']])
                else:
                    record.pop('b',None)
                    record.pop('g',None)
                    record['seat'] = True
    return encode_area(outline),linework
