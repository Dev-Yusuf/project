"""Build compact SVG geometry from pinned geoBoundaries / GRID3 (CC BY 4.0).

Usage: python scripts/build_kogi_map.py PATH_TO_ADM1_GEOJSON PATH_TO_ADM2_GEOJSON
Source download URLs and attribution: docs/KOGI_MAP.md.
No network access or third-party geometry libraries are required.
"""
import json
import math
import re
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EAST = {'Ankpa', 'Bassa', 'Dekina', 'Ibaji', 'Idah', 'Igalamela-Odolu', 'Ofu', 'Olamaboro', 'Omala'}
NAMES = EAST | {'Adavi', 'Ajaokuta', 'Okehi', 'Okene', 'Ogori/Magongo', 'Ijumu', 'Kabba/Bunu', 'Kogi', 'Lokoja', 'Mopa-Muro', 'Yagba East', 'Yagba West'}


def rings(geometry):
    if geometry['type'] == 'Polygon':
        return geometry['coordinates']
    if geometry['type'] == 'MultiPolygon':
        return [ring for polygon in geometry['coordinates'] for ring in polygon]
    raise ValueError('Expected polygon geometry.')


def centroid(ring):
    area = cx = cy = 0
    for a, b in zip(ring, ring[1:] + ring[:1]):
        cross = a[0] * b[1] - b[0] * a[1]
        area += cross
        cx += (a[0] + b[0]) * cross
        cy += (a[1] + b[1]) * cross
    return (cx / (3 * area), cy / (3 * area)) if area else ring[0][:2]


def build(adm1, adm2):
    state = next(f for f in adm1['features'] if f['properties']['shapeName'] == 'Kogi')
    selected = []
    for feature in adm2['features']:
        name = feature['properties']['shapeName']
        outer = max(rings(feature['geometry']), key=len)
        x, y = centroid(outer)
        if name in NAMES and 5 < x < 8 and 6.4 < y < 9:
            selected.append(feature)
    assert len(selected) == 21 and {f['properties']['shapeName'] for f in selected} == NAMES
    points = [p for ring in rings(state['geometry']) for p in ring]
    points += [p for f in selected for ring in rings(f['geometry']) for p in ring]
    minx, maxx = min(p[0] for p in points), max(p[0] for p in points)
    miny, maxy = min(p[1] for p in points), max(p[1] for p in points)
    cosine = math.cos(math.radians((miny + maxy) / 2))
    scale = min(600 / ((maxx - minx) * cosine), 540 / (maxy - miny))
    offset_x = (680 - (maxx - minx) * cosine * scale) / 2
    offset_y = (620 - (maxy - miny) * scale) / 2
    def project(p):
        return [round(offset_x + (p[0] - minx) * cosine * scale, 2), round(offset_y + (maxy - p[1]) * scale, 2)]
    def path(geometry):
        return ''.join('M' + 'L'.join(f'{x:g},{y:g}' for x,y in map(project, ring)) + 'Z' for ring in rings(geometry))
    features = []
    for feature in sorted(selected, key=lambda f: f['properties']['shapeName']):
        name = feature['properties']['shapeName']
        outer = max(rings(feature['geometry']), key=len)
        x, y = project(centroid(outer))
        features.append({'id': re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-'), 'name': name,
                         'east': name in EAST, 'path': path(feature['geometry']),
                         'label_x': x, 'label_y': y, 'source_id': feature['properties']['shapeID']})
    return {'viewbox': '0 0 680 620', 'source': 'GRID3 / geoBoundaries', 'license': 'CC BY 4.0',
            'boundary_year': 2022, 'state_path': path(state['geometry']), 'lgas': features}


def labeled_svg(data, viewbox='0 0 680 620'):
    """Static version of the About map: same geometry and palette, no hit targets."""
    context, east, labels = [], [], []
    for lga in data['lgas']:
        path = f'<path d="{lga["path"]}" fill-rule="evenodd"/>'
        (east if lga['east'] else context).append(path)
        if lga['east']:
            x, y = lga['label_x'], lga['label_y']
            name = escape(lga['name'])
            if lga['id'] == 'igalamela-odolu':
                name = f'<tspan x="{x}" dy="-5">Igalamela</tspan><tspan x="{x}" dy="16">Odolu</tspan>'
            labels.append(f'<text x="{x}" y="{y}">{name}</text>')
    districts = ('<g fill="#859279" font-family="monospace" font-size="10" letter-spacing="1.3" text-anchor="middle">'
                 '<text x="235" y="235">KOGI WEST</text><text x="320" y="370" transform="rotate(-36 320 370)">KOGI CENTRAL</text></g>') if viewbox == '0 0 680 620' else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}">'
            '<title>Kogi State local government areas</title>'
            '<desc>Kogi East is highlighted, with labels for Ankpa, Bassa, Dekina, Ibaji, Idah, Igalamela-Odolu, Ofu, Olamaboro and Omala. Administrative boundaries are not language boundaries.</desc>'
            '<metadata>GRID3 / geoBoundaries, 2022. CC BY 4.0. Adapted to rounded SVG coordinates; static companion to the About-page explorer.</metadata>'
            '<g stroke="#f7f9f2" stroke-width="1.6" stroke-linejoin="round">'
            f'<g fill="#e5eade">{"".join(context)}</g>'
            f'<g fill="#c5d9ac">{"".join(east)}</g></g>'
            '<g fill="#31533b" font-family="Arial,sans-serif" font-size="15" font-weight="500" text-anchor="middle" dominant-baseline="middle" paint-order="stroke" stroke="#f6f9ef" stroke-width="3" stroke-linejoin="round">'
            f'{"".join(labels)}</g>{districts}</svg>')


if __name__ == '__main__':
    result = build(*(json.loads(Path(p).read_text(encoding='utf-8')) for p in sys.argv[1:3]))
    target = ROOT / 'main' / 'data' / 'kogi_boundaries.json'
    target.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    outline = result['state_path']
    lgas = ''.join(f'<path d="{lga["path"]}"/>' for lga in result['lgas'])
    east = ''.join(f'<path d="{lga["path"]}"/>' for lga in result['lgas'] if lga['east'])
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{result["viewbox"]}">'
           '<title>Sketch of Kogi State</title>'
           '<metadata>GRID3 / geoBoundaries, 2022. CC BY 4.0. Adapted to SVG and rounded projected coordinates.</metadata>'
           f'<g fill="#dae5cb" fill-opacity=".45" stroke="none">{east}</g>'
           f'<g id="sketch-lines" fill="none" stroke="#7e9676" stroke-width=".8" stroke-linejoin="round">{lgas}</g>'
           '<use href="#sketch-lines" transform="translate(.9 -1.2)" opacity=".24"/>'
           f'<path d="{outline}" fill="none" stroke="#56744f" stroke-width="1.6" stroke-linejoin="round"/>'
           '<circle cx="381.61" cy="452.36" r="10" fill="none" stroke="#a48b4f" stroke-width="1"/>'
           '<circle cx="381.61" cy="452.36" r="3.8" fill="#a48b4f"/>'
           '</svg>')
    (ROOT / 'static' / 'images' / 'kogi-sketch.svg').write_text(svg, encoding='utf-8')
    for filename, viewbox in [('kogi-labeled.svg', '0 0 680 620'), ('kogi-labeled-east.svg', '320 185 350 410')]:
        (ROOT / 'static' / 'images' / filename).write_text(labeled_svg(result, viewbox), encoding='utf-8')
    print(f'Built {len(result["lgas"])} LGAs; {target.stat().st_size:,} bytes.')
