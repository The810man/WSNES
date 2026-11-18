#!/usr/bin/env python3
"""Write the production files from the schematic (parts, fields) and the routed board (positions).

Usage (from pcb/):  python3 tools/export_bom.py .

Writes
  production/jlc/WSNES_BOM_JLC.csv   parts JLC assembles (Assembly = JLC), grouped by value/footprint/LCSC
  production/jlc/WSNES_CPL_JLC.csv   their placement, taken from the board
  production/WSNES_Proto_BOM.csv     every part, with manufacturer, MPN, LCSC number and sourcing notes

Unlike gen_pcb.py this never touches the board, so it is safe to run after routing.
"""
import csv
import math
import os
import re
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import find, find1, parse  # noqa: E402

PROJ = 'WSNES_Proto'
# Sourcing notes (checked 2026-11-17, re-checked 2026-11-18). Update when stock changes.
NOTES = {
    'C2953576': 'replaces the out-of-stock AS6C4008-55SIN (C1350086). Same 450-mil SOIC-32 land pattern, JEDEC pinout, '
                '4.5-5.5 V, 55 ns. Only 5 in stock at LCSC on 2026-11-18: order early, or buy and hand-solder it',
    'C10910': 'replaces the out-of-stock 74AHCT245PW,118 (C173388); same TSSOP-20 pinout',
    'C3304572': 'replaces the out-of-stock 74HCT165PW,118 (C547409); same TSSOP-16 pinout. '
                'Must stay HCT (CP and /PL are 3.3 V signals)',
    'C1350086': 'not stocked at LCSC on 2026-11-17: JLC parts pre-order / Global Sourcing, or hand-solder (SOP-32)',
    'C1351203': 'not stocked at LCSC on 2026-11-17: JLC parts pre-order / Global Sourcing, or hand-solder (SOP-32). '
                'Keep a 2.7-5.5 V part: it runs from VSAVE behind the BAT54C',
    'C2953613': 'replaces the out-of-stock AS6C1008-55SIN (C1351203); same pinout and 450-mil SOP-32. '
                'Rated 4.5-5.5 V but VSAVE is ~0.35 V below +5V (BAT54C), so it is only in spec with >= 4.9 V from the console. '
                'Data retention from 2.0 V (CR2032 is fine). Prefer the AS6C1008 (2.7-5.5 V) when stocked',
    'C547409': 'not stocked at LCSC on 2026-11-17: JLC parts pre-order / Global Sourcing, or hand-solder (TSSOP-16). '
               'Must stay HCT (CP and /PL are 3.3 V signals)',
    'C221896': 'replaces the out-of-stock PTS810SJM (1.6 N); same footprint, 2.6 N',
    'C2674471': 'AHCT instead of HCT: faster /ROMSEL -> SRAM /CE path (FastROM)',
    'C2979167': 'holder only; add one CR2032 cell',
    'C2935976': 'optional, only for flashing the PIC in circuit',
}


def natkey(ref):
    m = re.match(r'([A-Za-z]+)(\d+)', ref)
    return (m.group(1), int(m.group(2))) if m else (ref, 0)


def ranges(refs):
    """['C3','C4','C5','C9'] -> 'C3-C5,C9' (same style as the existing full BOM)."""
    refs = sorted(refs, key=natkey)
    out, run = [], []
    for r in refs:
        if run and natkey(r)[0] == natkey(run[-1])[0] and natkey(r)[1] == natkey(run[-1])[1] + 1:
            run.append(r)
        else:
            if run:
                out.append(run)
            run = [r]
    if run:
        out.append(run)
    return ','.join(g[0] if len(g) == 1 else (','.join(g) if len(g) == 2 else '%s-%s' % (g[0], g[-1])) for g in out)


def schematic_parts(path, parts=None):
    """All symbols of the (hierarchical) schematic: the root file plus every sub-sheet it references."""
    root = parse(open(path, encoding='utf-8').read())
    parts = OrderedDict() if parts is None else parts
    for sh in find(root, 'sheet'):
        sub = next(str(p[2]) for p in find(sh, 'property') if str(p[1]) == 'Sheetfile')
        schematic_parts(os.path.join(os.path.dirname(path), sub), parts)
    for s in find(root, 'symbol'):
        if not find1(s, 'lib_id'):
            continue
        props = {str(p[1]): str(p[2]) for p in find(s, 'property')}
        ref = props.get('Reference', '')
        if not ref or ref.startswith('#'):
            continue
        parts.setdefault(ref, props)     # multi-unit symbols: first unit wins (same fields)
    return parts


def board_positions(path):
    root = parse(open(path, encoding='utf-8').read())
    pos = {}
    for fp in find(root, 'footprint'):
        ref = next((str(p[2]) for p in find(fp, 'property') if str(p[1]) == 'Reference'), None)
        at = find1(fp, 'at')
        rot = float(at[3]) if len(at) > 3 else 0.0
        layer = str(find1(fp, 'layer')[1])
        pos[ref] = (float(at[1]), float(at[2]), rot % 360, 'Top' if layer == 'F.Cu' else 'Bottom')
    return pos


def main(proj_dir):
    parts = schematic_parts(os.path.join(proj_dir, PROJ + '.kicad_sch'))
    pos = board_positions(os.path.join(proj_dir, PROJ + '.kicad_pcb'))
    missing = sorted(set(parts) ^ set(pos), key=natkey)
    if missing:
        raise SystemExit('schematic and board disagree on: %s' % missing)
    fpname = lambda p: p.get('Footprint', '').split(':')[-1]

    jlc = [r for r, p in parts.items() if p.get('Assembly') == 'JLC']
    nolcsc = [r for r in jlc if not parts[r].get('LCSC')]
    if nolcsc:
        raise SystemExit('JLC parts without an LCSC number: %s' % nolcsc)

    groups = OrderedDict()
    for r in sorted(jlc, key=natkey):
        p = parts[r]
        groups.setdefault((p['Value'], fpname(p), p.get('LCSC', '')), []).append(r)
    jdir = os.path.join(proj_dir, 'production', 'jlc')
    os.makedirs(jdir, exist_ok=True)
    with open(os.path.join(jdir, 'WSNES_BOM_JLC.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Comment', 'Designator', 'Footprint', 'Manufacturer', 'MPN', 'LCSC Part #'])
        for (val, fp, lcsc), refs in sorted(groups.items(), key=lambda kv: natkey(kv[1][0])):
            p = parts[refs[0]]
            w.writerow([val, ','.join(refs), fp, p.get('Manufacturer', ''), p.get('MPN', ''), lcsc])
    with open(os.path.join(jdir, 'WSNES_CPL_JLC.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        for r in sorted(jlc):
            x, y, rot, layer = pos[r]
            w.writerow([r, '%.3fmm' % x, '%.3fmm' % -y, layer, '%g' % rot])

    full = OrderedDict()
    for r in sorted(parts, key=natkey):
        p = parts[r]
        full.setdefault((p['Value'], p.get('Footprint', ''), p.get('MPN', ''), p.get('Assembly', '')), []).append(r)
    with open(os.path.join(proj_dir, 'production', PROJ + '_BOM.csv'), 'w', newline='') as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator='\n')
        w.writerow(['Refs', 'Value', 'Footprint', 'Manufacturer', 'MPN', 'LCSC', 'Assembly', 'Qty', 'Notes'])
        for (val, fp, mpn, asm), refs in sorted(full.items(), key=lambda kv: natkey(kv[1][0])):
            p = parts[refs[0]]
            lcsc = p.get('LCSC', '')
            w.writerow([ranges(refs), val, fp, p.get('Manufacturer', ''), mpn, lcsc, asm, len(refs), NOTES.get(lcsc, '')])
    print('JLC BOM lines: %d (%d parts), CPL rows: %d, full BOM lines: %d (%d parts)'
          % (len(groups), len(jlc), len(jlc), len(full), len(parts)))


if __name__ == '__main__':
    main(os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..')))
