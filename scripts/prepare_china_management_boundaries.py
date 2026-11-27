"""Build the administrative-management view of Jagdaqi and Songling."""
import argparse
from pathlib import Path

from shapely import set_precision, union_all
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import polylabel

from prepare_boundaries import OUTPUT
from refine_china_boundaries import decode_ring, from_rings, pack, polygons, read, save


def unpack(encoded):
    return set_precision(from_rings(decode_ring(ring) for ring in encoded.split('!')), .001)


def is_seam(area):
    return area.area <= .65 and area.area/area.length <= .065


def clean_owner_outline(area, seam_zone):
    parts = []
    for part in polygons(set_precision(area, .001)):
        if is_seam(part) and seam_zone.covers(part):
            continue
        holes = []
        for ring in part.interiors:
            gap = Polygon(ring)
            if not (is_seam(gap) and seam_zone.covers(gap)):
                holes.append(ring)
        parts.append(Polygon(part.exterior, holes))
    return MultiPolygon(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=OUTPUT)
    root = parser.parse_args().data
    data = read(root/'admin-boundaries.json')
    base = {region['id']: region['g'] for tier in data.values() for region in tier}
    folder = root/'china-boundaries'
    detailed = {code:g for code,g,_ in read(folder/'overview.json')['provinces']}
    for province in ('150000', '230000'):
        detailed.update({code:g for code,g,_ in read(folder/(province+'.json'))})

    asset = folder/'managed-districts.json'
    previous = read(asset)
    districts = previous if isinstance(previous, list) else previous['districts']
    songling = next(region for region in districts if region['id'] == '232762')
    jagdaqi = unpack(detailed.get('232718',base['232718']))
    songling_area = unpack(songling['g']).difference(jagdaqi)
    administered = {'232718':jagdaqi,'232762':songling_area}
    shared_area = union_all(list(administered.values()))

    results = {}
    oroqen = []
    for scale, encoded in [('base',base),('detail',{**base,**detailed})]:
        # Transfer the same area at each tier. The two districts share the same
        # geometry at both scales, so zooming never flips their affiliation.
        areas = dict(administered)
        owners = ('230000','232700')
        joined = {code:unpack(encoded[code]).union(shared_area) for code in owners}
        seams = []
        for outline in joined.values():
            for part in polygons(outline):
                for ring in part.interiors:
                    gap = Polygon(ring)
                    # Matching boundaries from separate sources can leave thin,
                    # enclosed strips where the new outline joins the old one.
                    if is_seam(gap) and shared_area.intersects(gap):
                        seams.append(gap)
        transferred = shared_area.union(union_all(seams))
        seam_zone = transferred.buffer(.35)
        fragments = []
        for code in ('150000','150700','150723','232721'):
            remaining = []
            for part in polygons(unpack(encoded[code]).difference(transferred)):
                # Near the transfer, nonmatching boundaries also leave detached
                # slivers that would still get stroked in the old jurisdiction.
                if is_seam(part) and seam_zone.covers(part):
                    fragments.append(part)
                else:
                    remaining.append(part)
            areas[code] = union_all(remaining)
        transferred = transferred.union(union_all(fragments))
        for code in owners:
            # Check the final snapped rings too. Subpixel holes can still pick up
            # a full-width border stroke even when the fill appears continuous.
            areas[code] = clean_owner_outline(joined[code].union(transferred), seam_zone)
        oroqen.append(areas['150723'])
        results[scale] = [[code,*pack(area)] for code,area in sorted(areas.items())]

    common_oroqen = oroqen[0].intersection(oroqen[1])
    anchor = polylabel(max(polygons(common_oroqen),key=lambda part:part.area),tolerance=.1)
    save(asset, {'districts':districts,'administered':list(administered),'boundaries':results,
                 'labelAnchors':{'150723':[round(anchor.x,3),round(anchor.y,3)]}})


if __name__ == '__main__':
    main()
