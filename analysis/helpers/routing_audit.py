#!/usr/bin/env python3
"""Routing audit per functional group: routed length vs. minimum spanning tree of the net's pads.

Usage: python3 analysis/helpers/routing_audit.py pcb/WSNES_Proto.kicad_pcb [analysis/<run>/pcb.json]

For every routed signal net it prints:
  * routed copper length and via count (from the board's segments / vias)
  * MST length over the net's pad centres (Euclidean): the shortest possible tree
  * detour factor = routed / MST (1.0 = straight lines; >2.5 = noticeable detour)
  * copper layers used
Nets are grouped by function (SNES bus, SRAM bus, ESP control, shift chain, SD, USB, ...).
Propagation delay is estimated at 6.7 ps/mm (FR4 stripline/microstrip average).
"""
import math
import re
import sys
from collections import defaultdict

sys.path.insert(0, '/home/rempel/.claude/plugins/cache/kicad-happy/kicad-happy/3.0.2/skills/kicad/scripts')
try:
    from kicad_core.sexp import parse_file, find_all, find_first
except ImportError:  # fall back to the project's own parser
    sys.path.insert(0, 'pcb/tools')
    raise

board = sys.argv[1]
doc = parse_file(board)
doc = doc[0] if isinstance(doc[0], list) and len(doc) == 1 else doc

pads = defaultdict(list)
for fp in find_all(doc, 'footprint'):
    ref = [q[2] for q in find_all(fp, 'property') if q[1] == 'Reference'][0]
    at = find_first(fp, 'at')
    fx, fy = float(at[1]), float(at[2])
    t = math.radians(float(at[3])) if len(at) > 3 and not isinstance(at[3], list) else 0.0
    for pad in find_all(fp, 'pad'):
        net = find_first(pad, 'net')
        if not net:
            continue
        pa = find_first(pad, 'at')
        lx, ly = float(pa[1]), float(pa[2])
        pads[net[-1]].append((ref + '.' + pad[1], fx + lx * math.cos(t) + ly * math.sin(t),
                              fy - lx * math.sin(t) + ly * math.cos(t)))
length = defaultdict(float)
layers = defaultdict(set)
for s in find_all(doc, 'segment'):
    n = find_first(s, 'net')[1]
    a, b = find_first(s, 'start'), find_first(s, 'end')
    length[n] += math.hypot(float(a[1]) - float(b[1]), float(a[2]) - float(b[2]))
    layers[n].add(find_first(s, 'layer')[1].replace('.Cu', ''))
vias = defaultdict(int)
for v in find_all(doc, 'via'):
    vias[find_first(v, 'net')[1]] += 1


def mst(points):
    if len(points) < 2:
        return 0.0
    pts = [(x, y) for _, x, y in points]
    used, total = {0}, 0.0
    best = {i: math.hypot(pts[i][0] - pts[0][0], pts[i][1] - pts[0][1]) for i in range(1, len(pts))}
    while best:
        i = min(best, key=best.get)
        total += best.pop(i)
        used.add(i)
        for j in best:
            best[j] = min(best[j], math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1]))
    return total


GROUPS = [
    ('SNES address (edge -> 541)', r'^/SNES_A\d+$'),
    ('SNES data (edge -> 245)', r'^/SNES_D\d$'),
    ('SNES control', r'^/SNES_(RD_N|WR_N|ROMSEL_N|RESET_N|A15)$|^/CIC_'),
    ('SRAM address SA', r'^/SA\d+$|^/SV_A\d+$|^/EA19'),
    ('SRAM data SD', r'^/SD\d$'),
    ('SRAM control', r'^/(SRAM_|SAVE_|DBUF|DB_ROM|ROM_SEL|ROMSEL|WE_GATE|ROM_WE|PWR_OK|DOUT_OE)'),
    ('ESP shift chain', r'^/(SR_|RB_Q7|RD_LOAD)'),
    ('ESP control', r'^/(BUS_ESP|ESP_(OE|WE)|MENU_WE|MBX|RESET_SENSE|SNES_5V|SNES_RST|RST_GATE|SAVE_EN|SAVE_M)'),
    ('microSD', r'^/SD_'),
    ('USB', r'^/USB_'),
]
seen = set()
rows = []
for gname, rx in GROUPS:
    nets = sorted((n for n in pads if re.search(rx, n) and n not in seen and length.get(n, 0) > 0),
                  key=lambda n: (len(n), n))
    if not nets:
        continue
    print('\n== %s (%d nets)' % (gname, len(nets)))
    print('   %-16s %7s %7s %6s %4s %5s  %s' % ('net', 'routed', 'MST', 'factor', 'vias', 'pads', 'layers'))
    for n in nets:
        seen.add(n)
        m = mst(pads[n])
        f = length[n] / m if m else 0
        flag = '  <-- detour' if f > 2.5 and length[n] > 20 else ''
        rows.append((gname, n, length[n], m, f, vias[n]))
        print('   %-16s %6.1fmm %6.1fmm %6.2f %4d %5d  %s%s' % (n.lstrip('/'), length[n], m, f, vias[n], len(pads[n]),
                                                            '+'.join(sorted(layers[n])), flag))
    ls = [length[n] for n in nets]
    print('   group: %.0f..%.0f mm, max delay %.2f ns' % (min(ls), max(ls), max(ls) * 0.0067))
print('\nworst detour factors (>20 mm routed):')
for r in sorted((r for r in rows if r[2] > 20), key=lambda r: -r[4])[:10]:
    print('   %-16s %-26s %6.1f mm vs MST %5.1f mm  x%.2f  %d vias' % (r[1].lstrip('/'), r[0], r[2], r[3], r[4], r[5]))
