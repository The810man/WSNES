#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 The810man
"""Generate the WSNES THT prototype KiCad 9 project (libraries + schematic) from design.py.

Usage: python3 gen_project.py <project_dir>
"""
import copy, math, os, sys, uuid, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sexp
from sexp import Q, find, find1, dump, parse
import design as D

PROJ = 'WSNES_Proto'
NS =uuid.UUID('6f1c1d55-2c1e-4c55-9a8e-5e5a0c0ffee0')
def U(*key):
    return Q(str(uuid.uuid5(NS, '/'.join(str(k) for k in key))))

ROOT = U('root-sheet')
STUB = 2.54
FONT = ['effects', ['font', ['size', 1.27, 1.27]]]
FONT_H = ['effects', ['font', ['size', 1.27, 1.27]], ['hide', 'yes']]

def snap(v, g=1.27):
    return round(round(v / g) * g, 4)

# ===================================================================== project symbol library
EDGE_SYM = 'SNES_Cart_Edge'
EDGE_FP = 'SNES_Cart_Edge_46P_P2.50mm'
# SNES cartridge slot signals (console pin numbering 1-62; standard carts use 5-27 / 36-58).
# (pin, name, electrical type) - grouped by function, left and right side of the symbol.
EDGE_LEFT = [(27, '+5V', 'power_out'), (58, '+5V', 'passive'), (5, 'GND', 'power_out'), (36, 'GND', 'passive'), None] + \
    [(p, 'A%d' % i, 'output') for i, p in enumerate([17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 37, 38, 39, 40])] + [None] + \
    [(41 + i, 'A%d' % (16 + i), 'output') for i in range(8)]
EDGE_RIGHT = [(p, 'D%d' % i, 'bidirectional') for i, p in enumerate([19, 20, 21, 22, 50, 51, 52, 53])] + [None] + \
    [(23, '~{RD}', 'output'), (54, '~{WR}', 'output'), (49, '~{ROMSEL}', 'output'), (26, '~{RESET}', 'bidirectional'),
     (18, '~{IRQ}', 'passive'), (57, 'SYSCLK', 'output'), None,
     (56, 'CIC_CLK', 'output'), (25, 'CIC_RST', 'output'), (55, 'CIC_DATA0', 'bidirectional'),
     (24, 'CIC_DATA1', 'bidirectional')]

def build_edge_symbol():
    pins = []
    top = 2.54 * (len(EDGE_LEFT) // 2)
    for side, x, ang in ((EDGE_LEFT, -15.24, 0), (EDGE_RIGHT, 15.24, 180)):
        for i, e in enumerate(side):
            if e is None:
                continue
            num, name, typ = e
            pins.append(['pin', typ, 'line', ['at', x, round(top - 2.54 * i, 2), ang], ['length', 2.54],
                         ['name', Q(name), FONT], ['number', Q(str(num)), FONT]])
    bottom = round(top - 2.54 * (len(EDGE_LEFT) - 1), 2)
    return ['symbol', Q(EDGE_SYM), ['pin_names', ['offset', 1.016]], ['exclude_from_sim', 'no'],
            ['in_bom', 'no'], ['on_board', 'yes'],
            ['property', Q('Reference'), Q('P'), ['at', 0, top + 3.81, 0], FONT],
            ['property', Q('Value'), Q('SNES_Cart_Edge'), ['at', 0, bottom - 3.81, 0], FONT],
            ['property', Q('Footprint'), Q(PROJ + ':' + EDGE_FP), ['at', 0, 0, 0], FONT_H],
            ['property', Q('Datasheet'), Q(''), ['at', 0, 0, 0], FONT_H],
            ['property', Q('Description'), Q('SNES / Super Famicom cartridge edge, standard 46-contact section (pins 5-27, 36-58)'), ['at', 0, 0, 0], FONT_H],
            ['symbol', Q(EDGE_SYM + '_0_1'),
             ['rectangle', ['start', -12.7, top + 2.54], ['end', 12.7, bottom - 2.54],
              ['stroke', ['width', 0.254], ['type', 'default']], ['fill', ['type', 'background']]]],
            ['symbol', Q(EDGE_SYM + '_1_1')] + pins,
            ['embedded_fonts', 'no']]

# ===================================================================== project footprint library
# Edge tab geometry (origin = tab centre on the contact centre line, +y towards the inserted edge).
EDGE_PITCH = 2.5          # SNES slot contact pitch
EDGE_PAD = (1.8, 7.0)     # finger width x length
TAB_HALF = 30.0           # standard-cart tab is 60 mm wide (fits the slot's 46-contact section)
TAB_TOP = -6.5            # shoulder line (where the board body starts)
TAB_BOT = 4.6             # inserted edge
TAB_CHAMFER = 1.0

def build_edge_footprint():
    """Pins 36-58 on F.Cu (component side), 5-27 on B.Cu; pins 5/36 at +x when seen from the component side."""
    def font(sz=1.0): return ['effects', ['font', ['size', sz, sz], ['thickness', sz * 0.15]]]
    items = ['footprint', Q(EDGE_FP), ['version', 20241229], ['generator', Q('wsnes_gen')], ['generator_version', Q('9.0')],
             ['layer', Q('F.Cu')],
             ['descr', Q('SNES/SFC cartridge edge, 46 contacts (5-27 bottom, 36-58 top), 2.5 mm pitch, for 1.2 mm PCB with 45 deg bevel')],
             ['tags', Q('SNES cartridge edge connector gold fingers')],
             ['property', Q('Reference'), Q('REF**'), ['at', 0, TAB_TOP - 1.5, 0], ['layer', Q('F.SilkS')], font()],
             ['property', Q('Value'), Q(EDGE_FP), ['at', 0, TAB_BOT + 1.5, 0], ['layer', Q('F.Fab')], font()],
             ['property', Q('Footprint'), Q(''), ['at', 0, 0, 0], ['layer', Q('F.Fab')], ['hide', 'yes'], font()],
             ['property', Q('Datasheet'), Q(''), ['at', 0, 0, 0], ['layer', Q('F.Fab')], ['hide', 'yes'], font()],
             ['property', Q('Description'), Q(''), ['at', 0, 0, 0], ['layer', Q('F.Fab')], ['hide', 'yes'], font()],
             ['attr', 'smd']]
    def line(layer, a, b, w=0.1):
        return ['fp_line', ['start', a[0], a[1]], ['end', b[0], b[1]], ['stroke', ['width', w], ['type', 'solid']], ['layer', Q(layer)]]
    h, c = TAB_HALF, TAB_CHAMFER
    tab = [(-h, TAB_TOP), (-h, TAB_BOT - c), (-h + c, TAB_BOT), (h - c, TAB_BOT), (h, TAB_BOT - c), (h, TAB_TOP)]
    for a, b in zip(tab, tab[1:]):
        items.append(line('Edge.Cuts', a, b))
    items.append(['fp_rect', ['start', -h - 0.5, TAB_TOP - 0.5], ['end', h + 0.5, TAB_BOT + 0.5],
                  ['stroke', ['width', 0.05], ['type', 'solid']], ['fill', 'no'], ['layer', Q('F.CrtYd')]])
    items.append(['fp_text', 'user', Q('36'), ['at', 27.5, TAB_TOP + 1.2, 0], ['layer', Q('F.Fab')], font(0.8)])
    items.append(['fp_text', 'user', Q('58'), ['at', -27.5, TAB_TOP + 1.2, 0], ['layer', Q('F.Fab')], font(0.8)])
    for n in range(5, 28):           # bottom side
        x = round(27.5 - (n - 5) * EDGE_PITCH, 3)
        items.append(['pad', Q(str(n)), 'smd', 'rect', ['at', x, 0], ['size', EDGE_PAD[0], EDGE_PAD[1]],
                      ['layers', Q('B.Cu'), Q('B.Mask')]])
    for n in range(36, 59):          # component side
        x = round(27.5 - (n - 36) * EDGE_PITCH, 3)
        items.append(['pad', Q(str(n)), 'smd', 'rect', ['at', x, 0], ['size', EDGE_PAD[0], EDGE_PAD[1]],
                      ['layers', Q('F.Cu'), Q('F.Mask')]])
    items.append(['embedded_fonts', 'no'])
    return items

# ===================================================================== schematic
def lib_path(lib):
    return D.SYMDIR + lib + '.kicad_sym'

class Sch:
    def __init__(self):
        self.libsyms = {}
        self.items = []
        self.pwr_n = 0
        self.flag_n = 0

    def libsym(self, lib, name, projsyms):
        key = lib + ':' + name
        if key not in self.libsyms:
            if lib == PROJ:
                s = copy.deepcopy(projsyms[name])
            else:
                s = sexp.flatten(lib_path(lib), name)
            s[1] = Q(key)
            self.libsyms[key] = s
        return self.libsyms[key]

    def wire(self, a, b, key):
        self.items.append(['wire', ['pts', ['xy', a[0], a[1]], ['xy', b[0], b[1]]],
                           ['stroke', ['width', 0], ['type', 'default']], ['uuid', U('w', *key)]])

    def label(self, name, at, d, key):
        ang, just = {(-1, 0): (180, 'right'), (1, 0): (0, 'left'), (0, 1): (270, 'right'), (0, -1): (90, 'left')}[d]
        self.items.append(['label', Q(name), ['at', at[0], at[1], ang], ['fields_autoplaced', 'yes'],
                           ['effects', ['font', ['size', 1.27, 1.27]], ['justify', just, 'bottom']],
                           ['uuid', U('l', *key)]])

    def noconn(self, at, key):
        self.items.append(['no_connect', ['at', at[0], at[1]], ['uuid', U('nc', *key)]])

    def text(self, s, at, size=1.27, bold=False, key=None):
        eff = ['font', ['size', size, size]]
        if bold: eff += [['thickness', size / 5], ['bold', 'yes']]
        self.items.append(['text', Q(s), ['exclude_from_sim', 'no'], ['at', at[0], at[1], 0],
                           ['effects', eff, ['justify', 'left', 'top']], ['uuid', U('t', key or s[:40], at)]])

    def instance(self, lib_id, ref, value, fp, at, unit, rot, libsym, key, hide_ref=False, in_bom=True, dnp=False, extra_props=()):
        props = {str(p[1]): p for p in find(libsym, 'property')}
        def ppos(name, default):
            p = props.get(name)
            if p is None: return default
            a = find1(p, 'at')
            x, y = float(a[1]), float(a[2])
            r = math.radians(rot)
            xr, yr = x * math.cos(r) - y * math.sin(r), x * math.sin(r) + y * math.cos(r)
            return (snap(at[0] + xr, 0.01), snap(at[1] - yr, 0.01))
        def prop(name, val, hide=False):
            pos = ppos(name, at)
            return ['property', Q(name), Q(val), ['at', pos[0], pos[1], 0], FONT_H if hide else FONT]
        pins = sexp.pins_of(libsym)
        pinnums = sorted({p['number'] for p in pins if p['unit'] in (0, unit) and p['style'] in (0, 1)},
                         key=lambda s: (len(s), s))
        node = ['symbol', ['lib_id', Q(lib_id)], ['at', at[0], at[1], rot], ['unit', unit],
                ['exclude_from_sim', 'no'], ['in_bom', 'yes' if in_bom else 'no'], ['on_board', 'yes'],
                ['dnp', 'yes' if dnp else 'no'], ['fields_autoplaced', 'yes'], ['uuid', U('sym', *key)],
                prop('Reference', ref, hide_ref), prop('Value', value),
                prop('Footprint', fp, True), prop('Datasheet', str(props['Datasheet'][2]) if 'Datasheet' in props else '', True)]
        for k, v in extra_props:
            node.append(['property', Q(k), Q(v), ['at', at[0], at[1], 0], FONT_H])
        for n in pinnums:
            node.append(['pin', Q(n), ['uuid', U('pin', *key, n)]])
        node.append(['instances', ['project', Q(PROJ), ['path', Q('/' + ROOT), ['reference', Q(ref)], ['unit', unit]]]])
        self.items.append(node)

    def power(self, net, at, d, key):
        """Place a power symbol at `at`, oriented so its body points along direction d."""
        self.pwr_n += 1
        name = {'+5V': '+5V', '+3V3': '+3V3', 'GND': 'GND'}[net]
        ls = self.libsym('power', name, None)
        if net == 'GND':
            rot = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}[d]
        else:
            rot = {(0, -1): 0, (0, 1): 180, (-1, 0): 90, (1, 0): 270}[d]
        self.instance('power:' + name, '#PWR%03d' % self.pwr_n, net, '', at, 1, rot, ls, ('pwr',) + key,
                      hide_ref=True)

    def pwr_flag(self, net, at):
        self.flag_n += 1
        ls = self.libsym('power', 'PWR_FLAG', None)
        self.instance('power:PWR_FLAG', '#FLG%02d' % self.flag_n, 'PWR_FLAG', '', at, 1, 0, ls, ('flag', net), hide_ref=True)
        # flag pin is at (0,0): connect with a label of the net
        self.wire(at, (at[0], at[1] + STUB), ('flag', net))
        self.label(net, (at[0], at[1] + STUB), (0, 1), ('flag', net))


def place_part(sch, p, projsyms, report):
    ls = sch.libsym(p['lib'], p['sym'], projsyms)
    lib_id = p['lib'] + ':' + p['sym']
    pins = [x for x in sexp.pins_of(ls) if x['style'] in (0, 1)]
    units = sorted({x['unit'] for x in pins if x['unit'] > 0}) or [1]
    if p['unit_pos']:
        placements = [(u, p['unit_pos'][u]) for u in units]
    else:
        assert len(units) == 1, (p['ref'], units)
        placements = [(units[0], p['pos'])]
    used = set()
    for unit, at in placements:
        at = (snap(at[0], 2.54), snap(at[1], 2.54))
        sch.instance(lib_id, p['ref'], p['value'], p['fp'], at, unit, 0, ls, (p['ref'], unit),
                     extra_props=tuple(x for x in (('Note', p.get('note', '')), ('MPN', p.get('mpn', '')),
                                                   ('Assembly', p.get('asm', ''))) if x[1]))
        seen = set()
        for pin in pins:
            if pin['unit'] not in (0, unit) or pin['number'] in seen:
                continue
            seen.add(pin['number'])
            num = pin['number']
            if num not in p['conns']:
                raise SystemExit('UNASSIGNED pin %s.%s (%s)' % (p['ref'], num, pin['name']))
            used.add(num)
            net = p['conns'][num]
            e = (snap(at[0] + pin['x'], 0.01), snap(at[1] - pin['y'], 0.01))
            d = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[int(pin['angle']) % 360]
            key = (p['ref'], num)
            report.append((p['ref'], num, pin['name'], net))
            if net is None:
                sch.noconn(e, key)
                continue
            s = (snap(e[0] + d[0] * STUB, 0.01), snap(e[1] + d[1] * STUB, 0.01))
            sch.wire(e, s, key)
            if net in ('+5V', '+3V3', 'GND'):
                sch.power(net, s, d, key)
            else:
                sch.label(net, s, d, key)
    extra = set(p['conns']) - used
    if extra:
        raise SystemExit('Connections to non-existent pins on %s: %s' % (p['ref'], sorted(extra)))


NOTES = [
    ((20.32, 20.32), 'WSNES cart v0.3 - mixed SMD/THT, standard SNES PCB shape (ESP32-S3 + 512 KB ROM-SRAM + battery-backed save RAM, LoROM)', 3.0, True),
    ((20.32, 345.44), 'Save RAM: AS6C1008 at LoROM $70-$7D/$F0-$FF:0000-7FFF, CR2032 backed, write-protected below 4.4 V', 2.0, True),
    ((360.68, 355.6),
     'SAVE RAM\n'
     'U17 decodes the LoROM save area: A22=A21=A20=1, A15=0, /ROMSEL=0 -> SAVE_SEL_N (only in SNES mode and when SAVE_EN=1).\n'
     'U19 masks A11-A14 with SAVE_M11..M14 (ESP GPIOs) so the RAM mirrors at the header size (2 KB: all 0, 8 KB: M11+M12, 32 KB: all 1).\n'
     'Some games check the mirroring (anti-copier), so set the masks from the ROM header before releasing reset.\n'
     'ESP access: BUS_ESP=1, address bit EA19 (U11 QD) = 1 selects the save chip, 0 the ROM chip (set masks to 1 for full access).\n'
     'Power fail: U20 drives CE2 low below ~4.4 V, R7 holds it low when the cart is off -> no garbage writes, data kept by BT1.\n'
     'Every SNES write to the save area pulses MBX_IRQ_N -> ESP knows the save is dirty and copies it to SD (.srm) on reset/game change.',
     1.5, False),
    ((20.32, 27.94), 'SNES edge + SuperCIC', 2.0, True),
    ((132.08, 27.94), 'SNES-side bus buffers (5 V, enabled when BUS_ESP = 0)', 2.0, True),
    ((233.68, 27.94), 'SRAM + bus-ownership glue', 2.0, True),
    ((335.28, 27.94), 'ESP-side serial address/data access (5 V HCT)', 2.0, True),
    ((424.18, 27.94), '5V->3V3 + reset + pull-ups', 2.0, True),
    ((518.16, 27.94), 'ESP32-S3-WROOM-1 (hand-soldered) + microSD + USB-C + 3V3 LDO', 2.0, True),
    ((20.32, 30.48 + 3.0), 'Assembly field: JLC = SMD assembled by JLCPCB, HAND = you solder it (U21 ESP module, U15 PIC, BT1, J3)', 1.5, False),
    ((20.32, 290.83), 'Power + decoupling (one 100 nF per IC, place at VCC pin)', 2.0, True),
    ((233.68, 280.0),
     'BUS OWNERSHIP (single GPIO BUS_ESP, pulled HIGH = ESP owns bus at power-up)\n'
     'BUS_ESP=0 (SNES plays): U2-U4 drive SA*, U5 passes data when ROM_SEL_N=0,\n'
     '   SRAM /CE=ROM_SEL_N, /OE=SNES /RD, /WE=SNES_WE_N (only if MENU_WE_N=0).\n'
     'BUS_ESP=1 (ESP loads): U9-U11 drive SA*, U12 drives SD* when DOUT_OE_N=0,\n'
     '   ROM /CE=EA19, save /CE1=NOT EA19, /OE=ESP_OE_N, /WE=ESP_WE_N. U13 reads SD* back via SPI MISO.\n'
     'LoROM decode: ROM_SEL_N = /ROMSEL OR NOT A15. SNES A16-A19 -> SRAM A15-A18.\n'
     'Writes: SNES_WE_N = /WR OR (SAVE_SEL_N AND (ROM_SEL_N OR MENU_WE_N)) -> save area always, ROM area only in menu mode.\n'
     'Reset: Q1 pulls SNES /RESET low (gate pulled up = SNES held in reset until ESP firmware releases it).\n'
     'Mailbox: with MENU_WE_N=0 the menu may write into SRAM; each write pulses MBX_IRQ_N to the ESP.',
     1.5, False),
    ((424.18, 280.0),
     'ESP32-S3 GPIO MAP (N16R8: GPIO35-37 are used by octal PSRAM - do not use!)\n'
     'GPIO4 BUS_ESP   GPIO5 ESP_WE_N   GPIO6 ESP_OE_N   GPIO7 DOUT_OE_N\n'
     'GPIO15 RD_LOAD_N  GPIO16 MENU_WE_N  GPIO17 SNES_RST_DRV (1 = hold SNES in reset)\n'
     'GPIO18 MBX_IRQ_N  GPIO8 RESET_SENSE_N  GPIO9 SNES_5V_SENSE\n'
     'SPI2 (IOMUX): GPIO10 SR_LATCH, GPIO11 SR_MOSI, GPIO12 SR_SCK, GPIO13 SR_MISO\n'
     'SD (SPI3): GPIO1 CS, GPIO2 SCK, GPIO42 MOSI, GPIO41 MISO, GPIO38 card detect (0 = card in)\n'
     'USB: GPIO19/20 native USB (flashing + serial), GPIO0 BOOT button, GPIO48 status LED\n'
     'Save RAM: GPIO21 SAVE_EN, GPIO14 M11, GPIO47 M12, GPIO39 M13, GPIO40 M14\n'
     'Shift order (MSB first, 32 bit): DATA[7:0], A[23:16] (bit19 = EA19 save select), A[15:8], A[7:0]\n'
     'Never drive 5 V-side outputs while SNES_5V_SENSE = 0 (USB-only power: only the ESP side is alive).',
     1.5, False),
]

def netclass(name, clearance, track, via_d, via_drill, priority):
    return {'name': name, 'clearance': clearance, 'track_width': track, 'via_diameter': via_d,
            'via_drill': via_drill, 'microvia_diameter': 0.3, 'microvia_drill': 0.1,
            'diff_pair_width': 0.2, 'diff_pair_gap': 0.25, 'diff_pair_via_gap': 0.25,
            'wire_width': 6, 'bus_width': 12, 'line_style': 0, 'priority': priority,
            'pcb_color': 'rgba(0, 0, 0, 0.000)', 'schematic_color': 'rgba(0, 0, 0, 0.000)'}

def make_project(proj_dir):
    """Minimal project file: JLCPCB-friendly rules + a Power net class. KiCad fills in the rest."""
    pro = {
        'meta': {'filename': PROJ + '.kicad_pro', 'version': 3},
        'board': {'design_settings': {
            'rules': {'min_clearance': 0.15, 'min_track_width': 0.15, 'min_via_diameter': 0.45,
                      'min_through_hole_diameter': 0.2, 'min_via_annular_width': 0.1,
                      'min_hole_to_hole': 0.25, 'min_hole_clearance': 0.2,
                      'min_copper_edge_clearance': 0.3, 'min_connection': 0.15,
                      'min_text_height': 0.8, 'min_text_thickness': 0.08, 'min_silk_clearance': 0.0},
            'track_widths': [0.0, 0.2, 0.3, 0.4, 0.6],
            'via_dimensions': [{'diameter': 0.0, 'drill': 0.0}, {'diameter': 0.5, 'drill': 0.25},
                               {'diameter': 0.7, 'drill': 0.35}]}},
        'net_settings': {
            'classes': [netclass('Default', 0.15, 0.2, 0.5, 0.25, 2147483647),
                        netclass('Power', 0.2, 0.4, 0.7, 0.35, 0)],
            'meta': {'version': 4},
            'netclass_assignments': None,
            'netclass_patterns': [{'netclass': 'Power', 'pattern': p}
                                  for p in ('+5V', '+3V3', 'GND', '/ESP_5V', '/VBUS', '/VSAVE')]},
        'schematic': {}, 'erc': {}, 'libraries': {}, 'pcbnew': {}, 'sheets': [], 'text_variables': {},
    }
    json.dump(pro, open(os.path.join(proj_dir, PROJ + '.kicad_pro'), 'w'), indent=2)

def main(proj_dir):
    libdir = os.path.join(proj_dir, 'lib')
    os.makedirs(os.path.join(libdir, PROJ + '.pretty'), exist_ok=True)
    edge = build_edge_symbol()
    projsyms = {EDGE_SYM: edge}
    with open(os.path.join(libdir, PROJ + '.kicad_sym'), 'w') as f:
        f.write(dump(['kicad_symbol_lib', ['version', 20241209], ['generator', Q('wsnes_gen')],
                      ['generator_version', Q('9.0')], edge]) + '\n')
    stale = os.path.join(libdir, PROJ + '.pretty', 'ESP32-S3-DevKitC-1_Socket.kicad_mod')
    if os.path.exists(stale):
        os.remove(stale)
    with open(os.path.join(libdir, PROJ + '.pretty', EDGE_FP + '.kicad_mod'), 'w') as f:
        f.write(dump(build_edge_footprint()) + '\n')
    with open(os.path.join(proj_dir, 'sym-lib-table'), 'w') as f:
        f.write('(sym_lib_table\n\t(version 7)\n\t(lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/lib/%s.kicad_sym")(options "")(descr "WSNES project symbols"))\n)\n' % (PROJ, PROJ))
    with open(os.path.join(proj_dir, 'fp-lib-table'), 'w') as f:
        f.write('(fp_lib_table\n\t(version 7)\n\t(lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/lib/%s.pretty")(options "")(descr "WSNES project footprints"))\n)\n' % (PROJ, PROJ))

    sch = Sch()
    report = []
    for p in D.parts:
        place_part(sch, p, projsyms, report)
    for net, at in D.pwr_flags.items():
        sch.pwr_flag(net, at)
    for at, s, size, bold in NOTES:
        sch.text(s, at, size, bold)

    root = ['kicad_sch', ['version', 20250114], ['generator', Q('eeschema')], ['generator_version', Q('9.0')],
            ['uuid', ROOT], ['paper', Q('A1')],
            ['title_block', ['title', Q('WSNES Flashcart - Cart v0.3 (mixed SMD/THT)')], ['date', Q('2026-11-16')],
             ['rev', Q('0.3')], ['company', Q('WSNES project')],
             ['comment', 1, Q('ESP32-S3-WROOM-1 + 512 KB ROM-SRAM + battery save RAM, LoROM, 5 V core, standard SNES PCB outline')],
             ['comment', 2, Q('Generated: tools/gen_project.py + tools/design.py')],
             ['comment', 3, Q('Copyright 2026 The810man - CC BY-NC-SA 4.0, no commercial use without permission')]],
            ['lib_symbols'] + list(sch.libsyms.values())]
    root += sch.items
    root += [['sheet_instances', ['path', Q('/'), ['page', Q('1')]]], ['embedded_fonts', 'no']]
    with open(os.path.join(proj_dir, PROJ + '.kicad_sch'), 'w') as f:
        f.write(dump(root) + '\n')

    make_project(proj_dir)
    with open(os.path.join(proj_dir, 'tools', 'intended_pins.json'), 'w') as f:
        json.dump(report, f, indent=0)
    print('parts:', len(D.parts), 'pins:', len(report), 'lib symbols:', len(sch.libsyms))

if __name__ == '__main__':
    main(os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..')))
