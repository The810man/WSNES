#!/usr/bin/env python3
"""Write the "cheap prototype" assembly variant: same board, same gerbers, fewer JLC fees.

Usage (from pcb/):  python3 tools/export_cheap.py .

Reads the schematic (parts, fields) and the routed board (positions), like export_bom.py, and writes
  production/jlc-cheap/WSNES_BOM_JLC_cheap.csv   upload to JLC as the BOM
  production/jlc-cheap/WSNES_CPL_JLC_cheap.csv   upload to JLC as the CPL
  production/jlc-cheap/WSNES_SelfBuy.csv         everything you buy and solder yourself

Compared with production/jlc/ this variant
  - leaves off the parts that are out of stock (U1, U13) and the optional ones (SW1, SW2, U23),
  - swaps the green and blue LEDs for the red JLC basic LED (same 0603 footprint, no feeder fee).
Every part JLC still places sits on the same pads as before, so the gerbers do not change.

Prices and stock: LCSC / jlcsearch, checked 2026-11-17. Update PRICES when you order.
"""
import csv
import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from export_bom import PROJ, board_positions, natkey, ranges, schematic_parts  # noqa: E402

BOARDS = 2   # boards JLC assembles (JLC's minimum PCBA quantity); self-buy quantities are for this many

# Parts JLC leaves off in this variant: ref -> (required?, reason)
DNP = {
    'U1': (True, 'out of stock at LCSC and JLC on 2026-11-17'),
    'U13': (True, 'out of stock at LCSC and JLC on 2026-11-17'),
    'SW1': (False, 'BOOT is only a fallback: esptool puts the S3 into download mode over native USB'),
    'SW2': (False, 'RESET: unplugging the cart or USB resets the ESP too'),
    'U23': (False, 'USB ESD diode: D+/D- run as copper past it, so USB works without it'),
}
OPTIONAL_HAND = {'J3'}   # hand-soldered parts you can skip (ICSP header)
# Same-footprint swaps to JLC basic parts: ref -> (value, manufacturer, MPN, LCSC)
SWAP = {
    'D3': ('LED red (CIC OK)', 'KENTO', 'KT-0603R', 'C2286'),   # was green KT-0603G (extended)
    'D7': ('LED red (ESP)', 'KENTO', 'KT-0603R', 'C2286'),      # was blue KT-0603B (extended)
}
# JLC basic parts (no feeder fee), from jlcsearch 2026-11-17. Everything else JLC places is extended.
BASIC = {'C12891', 'C14663', 'C15849', 'C15850', 'C45783', 'C191023', 'C2286', 'C8545',
         'C22775', 'C25804', 'C21190', 'C25803', 'C23186'}
EXTENDED_FEE = 3.0   # USD per extended part type (JLC economic PCBA)

# LCSC part -> (unit price USD at the order quantity, minimum order qty, LCSC stock, where / notes)
PRICES = {
    'C2913202': (5.40, 1, 9691, 'LCSC'),
    'C1350086': (5.80, 1, 0, 'order MPN AS6C4008-55SIN from Mouser / DigiKey (price is the LCSC list price)'),
    'C547409': (0.164, 5, 0, 'order MPN 74HCT165PW,118 (Nexperia) from Mouser / DigiKey (price is the LCSC list price). '
                             'Must be HCT, because CP and /PL come from the ESP at 3.3 V'),
    'C9785': (2.07, 1, 42, 'LCSC. Flash the SuperCIC key firmware before soldering (needs a PIC programmer, '
                           'e.g. a PICkit), or fit J3 and flash it in place'),
    'C2979167': (0.40, 5, 2030, 'LCSC. Holder only: add one CR2032 cell per board (any shop)'),
    'C2935976': (0.076, 10, 650, 'LCSC. Only needed to flash the PIC in place'),
    'C221896': (0.59, 1, 626, 'LCSC'),
    'C7519': (0.16, 5, 38345, 'LCSC'),
}


def main(proj_dir):
    parts = schematic_parts(os.path.join(proj_dir, PROJ + '.kicad_sch'))
    pos = board_positions(os.path.join(proj_dir, PROJ + '.kicad_pcb'))
    for ref in list(DNP) + list(SWAP):
        if ref not in parts:
            raise SystemExit('variant names a part the schematic does not have: %s' % ref)
    for ref, (val, man, mpn, lcsc) in SWAP.items():
        parts[ref] = dict(parts[ref], Value=val, Manufacturer=man, MPN=mpn, LCSC=lcsc)
    fpname = lambda p: p.get('Footprint', '').split(':')[-1]

    jlc = [r for r, p in parts.items() if p.get('Assembly') == 'JLC' and r not in DNP]
    groups = OrderedDict()
    for r in sorted(jlc, key=natkey):
        p = parts[r]
        groups.setdefault((p['LCSC'], fpname(p)), []).append(r)

    out = os.path.join(proj_dir, 'production', 'jlc-cheap')
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'WSNES_BOM_JLC_cheap.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Comment', 'Designator', 'Footprint', 'Manufacturer', 'MPN', 'LCSC Part #'])
        for (lcsc, fp), refs in sorted(groups.items(), key=lambda kv: natkey(kv[1][0])):
            p = parts[refs[0]]
            vals = {parts[r]['Value'] for r in refs}
            w.writerow([p['Value'] if len(vals) == 1 else p['MPN'], ','.join(refs), fp,
                        p.get('Manufacturer', ''), p.get('MPN', ''), lcsc])
    with open(os.path.join(out, 'WSNES_CPL_JLC_cheap.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        for r in sorted(jlc):
            x, y, rot, layer = pos[r]
            w.writerow([r, '%.3fmm' % x, '%.3fmm' % -y, layer, '%g' % rot])

    # self-buy: the hand-soldered parts plus everything this variant leaves off
    own = [r for r, p in parts.items() if p.get('Assembly') == 'HAND' or r in DNP]
    buy = OrderedDict()
    for r in sorted(own, key=natkey):
        p = parts[r]
        buy.setdefault(p.get('LCSC', ''), []).append(r)
    totals = {True: 0.0, False: 0.0}
    with open(os.path.join(out, 'WSNES_SelfBuy.csv'), 'w', newline='') as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator='\n')
        w.writerow(['Refs', 'Part', 'MPN', 'Manufacturer', 'LCSC', 'Need', 'Per board', 'Order qty (%d boards)' % BOARDS,
                    'Unit USD', 'Line USD', 'LCSC stock', 'Where / notes'])
        for lcsc, refs in buy.items():
            p = parts[refs[0]]
            required = DNP[refs[0]][0] if refs[0] in DNP else refs[0] not in OPTIONAL_HAND
            price, moq, stock, where = PRICES[lcsc]
            qty = max(len(refs) * BOARDS, moq)
            totals[required] += qty * price
            reason = ''.join(DNP[r][1] + '. ' for r in refs if r in DNP)
            name = ' / '.join(OrderedDict.fromkeys(parts[r]['Value'] for r in refs))
            w.writerow([ranges(refs), name, p.get('MPN', ''), p.get('Manufacturer', ''), lcsc,
                        'required' if required else 'optional', len(refs), qty, '%.2f' % price,
                        '%.2f' % (qty * price), stock, reason + where])
        w.writerow(['BT1', 'CR2032 cell', 'CR2032', '', '', 'required', 1, BOARDS, '', '', '',
                    'any shop; keeps the saves while the cart is unplugged'])

    ext = sorted({lcsc for lcsc, _ in groups} - BASIC)
    print('cheap variant: JLC BOM lines %d (%d parts), extended types %d (~%.0f USD feeder fees), '
          'self-buy %d lines: required ~%.2f USD, optional ~%.2f USD (LCSC prices, plus shipping and CR2032 cells)'
          % (len(groups), len(jlc), len(ext), len(ext) * EXTENDED_FEE, len(buy), totals[True], totals[False]))


if __name__ == '__main__':
    main(os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..')))
