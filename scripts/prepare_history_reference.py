"""Export modern China's land borders from Natural Earth countries (China POV)."""

import argparse
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import shapefile
from shapely import get_parts, line_merge, make_valid, set_precision, union_all
from shapely.geometry import shape

from prepare_boundaries import save


def polygon(feature):
    return set_precision(make_valid(shape(feature.__geo_interface__)), 0.000001)


def intersects_bounds(first, second):
    return first[0] <= second[2] and first[2] >= second[0] and first[1] <= second[3] and first[3] >= second[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='ne_10m_admin_0_countries_chn.zip')
    args = parser.parse_args()
    with ZipFile(args.source) as archive:
        buffers = {
            ext: BytesIO(archive.read(next(name for name in archive.namelist() if name.endswith('.'+ext))))
            for ext in ('shp','shx','dbf')
        }
    with shapefile.Reader(**buffers) as reader:
        countries = reader.shapeRecords(fields=['SOV_A3'])
    china = union_all([polygon(row.shape) for row in countries if row.record['SOV_A3'] == 'CH1'])
    shared_borders = [
        china.boundary.intersection(polygon(row.shape).boundary)
        for row in countries if row.record['SOV_A3'] != 'CH1' and intersects_bounds(china.bounds, row.shape.bbox)
    ]
    border = line_merge(union_all(shared_borders))
    lines = [[[round(x,5),round(y,5)] for x,y in part.coords]
             for part in get_parts(border) if part.geom_type == 'LineString']
    if not lines:
        raise ValueError('No land borders found in the supplied country data')
    output = Path(__file__).resolve().parents[1]/'dist/data/history/china-land-border.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    save(output, lines)


if __name__ == '__main__':
    main()
