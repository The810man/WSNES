#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 The810man
"""Generate the WSNES KiCad project (libraries + hierarchical schematic + net classes) from design.py.

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

# ===================================================================== schematic (hierarchical since v0.4)
# The root sheet holds the title, the overview notes and one sheet symbol per functional block (design.SHEETS).
# Parts are drawn with a short stub + label on every pin, no wires between parts:
#   - a net that only one sheet uses gets a local label  -> PCB net "/<Sheet>/<NET>"
#   - a net that crosses sheets gets a global label      -> PCB net "<NET>" (same name on every sheet)
#   - +5V / +3V3 / GND get power symbols
# Positions are computed by a simple column packer (pack()) from each symbol's real extents, so nothing in design.py
# has to carry schematic coordinates any more.
from collections import OrderedDict

def lib_path(lib):
    return D.SYMDIR + lib + '.kicad_sym'

POWER_NETS = ('+5V', '+3V3', 'GND')
PWR_TIP = 2.54                # GND / +5V / +3V3 graphics end 2.54 mm from the pin
CHAR_W = 1.27 * 0.92          # stroke-font advance per character at 1.27 mm text (a little generous)
PAPER = [('A4', 297.0, 210.0), ('A3', 420.0, 297.0), ('A2', 594.0, 420.0)]
X0, GAP = 17.78, 7.62
DIRS = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}   # pin angle -> outward direction (schematic y down)


def net_sheets():
    """net -> set of sheet keys that use it (power nets excluded)."""
    use = {}
    for p in D.parts:
        for net in p['conns'].values():
            if net and net not in POWER_NETS:
                use.setdefault(net, set()).add(p['sheet'])
    for net, key in D.pwr_flags.items():
        use.setdefault(net, set()).add(key)
    return use


class Project:
    """Shared state across all sheet files: symbol cache and the #PWR / #FLG counters (refs are project-wide)."""
    def __init__(self, projsyms):
        self.projsyms = projsyms
        self.cache = {}
        self.pwr_n = 0
        self.flag_n = 0
        self.global_nets = {n for n, sh in net_sheets().items() if len(sh) > 1}

    def libsym(self, lib, name):
        key = lib + ':' + name
        if key not in self.cache:
            s = copy.deepcopy(self.projsyms[name]) if lib == PROJ else sexp.flatten(lib_path(lib), name)
            s[1] = Q(key)
            self.cache[key] = s
        return key, self.cache[key]


class Sheet:
    def __init__(self, proj, key, name, stem, title, sheet_uuid):
        self.proj, self.key, self.name, self.stem, self.title = proj, key, name, stem, title
        self.uuid = sheet_uuid                       # uuid of the sheet symbol on the root sheet (None for root)
        self.path = '/' + ROOT + ('/' + sheet_uuid if sheet_uuid else '')
        self.items = []
        self.used = OrderedDict()                    # lib symbols this file needs in its lib_symbols section
        self.paper = 'A3'

    def libsym(self, lib, name):
        key, s = self.proj.libsym(lib, name)
        self.used[key] = s
        return s

    # ---------------------------------------------------------------- primitives
    def wire(self, a, b, key):
        self.items.append(['wire', ['pts', ['xy', a[0], a[1]], ['xy', b[0], b[1]]],
                           ['stroke', ['width', 0], ['type', 'default']], ['uuid', U('w', *key)]])

    def label(self, name, at, d, key, shape='passive'):
        if name in self.proj.global_nets:
            ang, just = {(-1, 0): (180, 'right'), (1, 0): (0, 'left'), (0, 1): (270, 'right'), (0, -1): (90, 'left')}[d]
            self.items.append(['global_label', Q(name), ['shape', shape], ['at', at[0], at[1], ang],
                               ['fields_autoplaced', 'yes'],
                               ['effects', ['font', ['size', 1.27, 1.27]], ['justify', just]],
                               ['uuid', U('gl', *key)],
                               ['property', Q('Intersheetrefs'), Q('${INTERSHEET_REFS}'), ['at', at[0], at[1], 0],
                                ['effects', ['font', ['size', 1.27, 1.27]], ['justify', just], ['hide', 'yes']]]])
        else:
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
                           ['effects', eff, ['justify', 'left', 'top']], ['uuid', U('t', self.key, key or s[:40], at)]])

    def instance(self, lib_id, ref, value, fp, at, unit, rot, libsym, key, hide_ref=False, in_bom=True, dnp=False,
                 extra_props=(), datasheet='', value_at=None):
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
            eff = copy.deepcopy(FONT_H if hide else FONT)
            lp = props.get(name)
            just = find1(find1(lp, 'effects') or [], 'justify') if lp is not None else None
            if just and not hide and rot == 0:
                eff.append(just)      # keep the library's justification (e.g. left-justified SRAM values)
            return ['property', Q(name), Q(val), ['at', pos[0], pos[1], 0], eff]
        pins = sexp.pins_of(libsym)
        pinnums = sorted({p['number'] for p in pins if p['unit'] in (0, unit) and p['style'] in (0, 1)},
                         key=lambda s: (len(s), s))
        node = ['symbol', ['lib_id', Q(lib_id)], ['at', at[0], at[1], rot], ['unit', unit],
                ['exclude_from_sim', 'no'], ['in_bom', 'yes' if in_bom else 'no'], ['on_board', 'yes'],
                ['dnp', 'yes' if dnp else 'no'], ['fields_autoplaced', 'yes'], ['uuid', U('sym', *key)],
                prop('Reference', ref, hide_ref),
                prop('Value', value) if value_at is None else
                # KiCad turns field text together with the symbol: a 90/270 deg symbol needs a 90 deg field
                # to read horizontally
                ['property', Q('Value'), Q(value), ['at', value_at[0], value_at[1], 90 if rot in (90, 270) else 0],
                 ['effects', ['font', ['size', 1.27, 1.27]]] +
                 ([['justify', value_at[2]]] if value_at[2] != 'center' else [])],
                prop('Footprint', fp, True),
                prop('Datasheet', datasheet or (str(props['Datasheet'][2]) if 'Datasheet' in props else ''), True)]
        for k, v in extra_props:
            node.append(['property', Q(k), Q(v), ['at', at[0], at[1], 0], FONT_H])
        for n in pinnums:
            node.append(['pin', Q(n), ['uuid', U('pin', *key, n)]])
        node.append(['instances', ['project', Q(PROJ), ['path', Q(self.path), ['reference', Q(ref)], ['unit', unit]]]])
        self.items.append(node)

    def power(self, net, at, d, key):
        """Power symbol at `at`, its body pointing along direction d."""
        self.proj.pwr_n += 1
        ls = self.libsym('power', net)
        if net == 'GND':
            rot = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}[d]
        else:
            rot = {(0, -1): 0, (0, 1): 180, (-1, 0): 90, (1, 0): 270}[d]
        vat = None
        if d[1] == 0:      # horizontal pin: rotated symbol, so put its name after the tip, reading left-to-right
            just = 'left' if d[0] > 0 else 'right'
            if rot == 90:      # KiCad mirrors the justification of fields on 90 deg symbols
                just = {'left': 'right', 'right': 'left'}[just]
            vat = (round(at[0] + d[0] * (PWR_TIP + 0.6), 4), at[1], just)
        self.instance('power:' + net, '#PWR%03d' % self.proj.pwr_n, net, '', at, 1, rot, ls, ('pwr',) + key,
                      hide_ref=True, value_at=vat)

    def pwr_flag(self, net, at):
        self.proj.flag_n += 1
        ls = self.libsym('power', 'PWR_FLAG')
        self.instance('power:PWR_FLAG', '#FLG%02d' % self.proj.flag_n, 'PWR_FLAG', '', at, 1, 0, ls, ('flag', net),
                      hide_ref=True)
        self.wire(at, (at[0], at[1] + STUB), ('flag', net))
        self.label(net, (at[0], at[1] + STUB), (0, 1), ('flag', net))

    # ---------------------------------------------------------------- file
    def write(self, proj_dir, root_extra=()):
        tb = ['title_block', ['title', Q('WSNES Flashcart v0.4 - ' + (self.name.replace('_', ' ') if self.uuid else 'overview'))],
              ['date', Q(DATE)], ['rev', Q('0.4')], ['company', Q('WSNES project')],
              ['comment', 1, Q('ESP32-S3 + 512 KB ROM-SRAM + battery save RAM, LoROM')],
              ['comment', 2, Q('Generated by tools/gen_project.py from tools/design.py')],
              ['comment', 3, Q('(c) 2026 The810man - CC BY-NC-SA 4.0, non-commercial')]]
        node = ['kicad_sch', ['version', 20250114], ['generator', Q('eeschema')], ['generator_version', Q('9.0')],
                ['uuid', U('file', self.key) if self.uuid else ROOT], ['paper', Q(self.paper)], tb,
                ['lib_symbols'] + list(self.used.values())]
        node += self.items + list(root_extra)
        node += [['embedded_fonts', 'no']]
        fn = (PROJ if not self.uuid else self.stem) + '.kicad_sch'
        with open(os.path.join(proj_dir, fn), 'w', encoding='utf-8', newline='\n') as f:
            f.write(dump(node) + '\n')
        return fn


# ===================================================================== geometry for the packer
def _text_box(x, y, s, eff_node, horizontal=True):
    w = len(s) * CHAR_W
    just = []
    for c in (eff_node or []):
        if isinstance(c, list) and c and c[0] == 'justify':
            just = [str(j) for j in c[1:]]
    if 'left' in just:   x0, x1 = x, x + w
    elif 'right' in just: x0, x1 = x - w, x
    else:                x0, x1 = x - w / 2, x + w / 2
    return (x0, y - 1.0, x1, y + 1.0)


def unit_extents(sheet, libsym, unit, conns, value, ref):
    """Bounding box (schematic coords relative to the anchor, y down) of one unit incl. stubs, labels and fields."""
    xs, ys = [], []
    def add(x, y): xs.append(x); ys.append(y)
    for u in find(libsym, 'symbol'):
        m = __import__('re').match(r'.*_(\d+)_(\d+)$', str(u[1]))
        un, st = int(m.group(1)), int(m.group(2))
        if un not in (0, unit) or st not in (0, 1):
            continue
        for g in u:
            if not isinstance(g, list): continue
            if g[0] == 'rectangle':
                for k in ('start', 'end'):
                    a = find1(g, k); add(float(a[1]), -float(a[2]))
            elif g[0] in ('polyline', 'bezier'):
                for xy in find(find1(g, 'pts'), 'xy'):
                    add(float(xy[1]), -float(xy[2]))
            elif g[0] == 'circle':
                c = find1(g, 'center'); r = float(find1(g, 'radius')[1])
                add(float(c[1]) - r, -float(c[2]) - r); add(float(c[1]) + r, -float(c[2]) + r)
            elif g[0] == 'arc':
                for k in ('start', 'mid', 'end'):
                    a = find1(g, k); add(float(a[1]), -float(a[2]))
    for pin in sexp.pins_of(libsym):
        if pin['unit'] not in (0, unit) or pin['style'] not in (0, 1):
            continue
        ex, ey = pin['x'], -pin['y']
        d = DIRS[int(pin['angle']) % 360]
        add(ex, ey)
        add(ex - d[0] * pin['length'], ey - d[1] * pin['length'])
        net = conns.get(pin['number'], 'X')
        if net is None:
            continue
        sx, sy = ex + d[0] * STUB, ey + d[1] * STUB
        if net in POWER_NETS and d[1] == 0:
            along, side = PWR_TIP + 0.6 + len(net) * CHAR_W, 1.4
        elif net in POWER_NETS:
            along, side = 5.6, 2.6
        elif net in sheet.proj.global_nets:
            along, side = len(net) * CHAR_W + 3.6, 1.4
        else:
            along, side = len(net) * CHAR_W + 0.8, 1.8
        if d[1] == 0:
            add(sx + d[0] * along, sy - side); add(sx + d[0] * along, sy + side)
        else:
            add(sx - side, sy + d[1] * along); add(sx + side, sy + d[1] * along)
    boxes = {}
    for p in find(libsym, 'property'):
        name = str(p[1])
        if name in ('Reference', 'Value'):
            a = find1(p, 'at')
            boxes[name] = _text_box(float(a[1]), -float(a[2]), ref if name == 'Reference' else value, find1(p, 'effects'))
    r, v = boxes.get('Reference'), boxes.get('Value')
    value_at = None
    if r and v and r[0] < v[2] and v[0] < r[2] and r[1] < v[3] and v[1] < r[3]:
        # long value runs into the reference (e.g. the SRAMs): put it centred under everything else
        cx, by = (min(xs) + max(xs)) / 2, max(ys) + 2.0
        value_at = (cx, by, 'center')
        v = (cx - len(value) * CHAR_W / 2, by - 1.0, cx + len(value) * CHAR_W / 2, by + 1.0)
    for b in (r, v):
        if b:
            add(b[0], b[1]); add(b[2], b[3])
    return (min(xs), min(ys), max(xs), max(ys)), value_at


ROW_W = 110.0           # small parts (2-pin R/C/LED, PWR_FLAG) are first lined up in rows of at most this width
def rows(jobs):
    """Group runs of small jobs into rows. Returns blocks: (bbox, [(job, dx, dy), ...]), bbox origin (0, 0)."""
    small = lambda bb: bb[2] - bb[0] <= 22 and bb[3] - bb[1] <= 40
    blocks, cur = [], None
    def flush():
        if cur:
            blocks.append(((0.0, 0.0, cur['w'], cur['h']), cur['items']))
    for j in jobs:
        bb = j[2]
        if not small(bb):
            flush(); cur = None
            blocks.append((bb, [(j, 0.0, 0.0)]))
            continue
        if cur is None or cur['w'] + (bb[2] - bb[0]) > ROW_W:
            flush(); cur = {'w': 0.0, 'h': 0.0, 'items': []}
        ox = math.ceil((cur['w'] + (GAP / 2 if cur['items'] else 0) - bb[0]) / 2.54) * 2.54
        oy = math.ceil(-bb[1] / 2.54) * 2.54
        cur['items'].append((j, ox, oy))
        cur['w'] = ox + bb[2]
        cur['h'] = max(cur['h'], oy + bb[3])
    flush()
    return blocks


def pack(boxes, y0, ymax):
    """Column packer. boxes: list of (bbox). Returns anchors and the used width/height."""
    anchors, x, y, colw, right, bottom = [], X0, y0, 0.0, X0, y0
    for (x0, y0b, x1, y1) in boxes:
        w, h = x1 - x0, y1 - y0b
        if y > y0 and y + h > ymax:
            x += colw + GAP; y = y0; colw = 0.0
        ax = math.ceil((x - x0) / 2.54) * 2.54
        ay = math.ceil((y - y0b) / 2.54) * 2.54
        anchors.append((round(ax, 4), round(ay, 4)))
        y = ay + y1 + GAP * 0.6
        colw = max(colw, ax + x1 - x)
        right, bottom = max(right, ax + x1), max(bottom, ay + y1)
    return anchors, right, bottom


# ===================================================================== drawing a part
def part_units(sheet, p):
    ls = sheet.libsym(p['lib'], p['sym'])
    pins = [x for x in sexp.pins_of(ls) if x['style'] in (0, 1)]
    units = sorted({x['unit'] for x in pins if x['unit'] > 0}) or [1]
    return ls, pins, units


def draw_unit(sheet, p, ls, pins, unit, at, report, used, value_at=None):
    lib_id = p['lib'] + ':' + p['sym']
    sheet.instance(lib_id, p['ref'], p['value'], p['fp'], at, unit, 0, ls, (p['ref'], unit),
                   extra_props=tuple(x for x in (('Note', p.get('note', '')), ('MPN', p.get('mpn', '')),
                                                 ('Manufacturer', p.get('mfr', '')), ('LCSC', p.get('lcsc', '')),
                                                 ('Assembly', p.get('asm', ''))) if x[1]),
                   datasheet=p.get('datasheet', ''), value_at=value_at)
    seen, drawn = set(), set()
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
        d = DIRS[int(pin['angle']) % 360]
        key = (p['ref'], num)
        report.append((p['ref'], num, pin['name'], net))
        if (e, net) in drawn:          # stacked pins (e.g. USB-C VBUS / GND): one stub + label is enough
            continue
        drawn.add((e, net))
        if net is None:
            sheet.noconn(e, key)
            continue
        s = (snap(e[0] + d[0] * STUB, 0.01), snap(e[1] + d[1] * STUB, 0.01))
        sheet.wire(e, s, key)
        if net in POWER_NETS:
            sheet.power(net, s, d, key)
        else:
            shape = {'input': 'input', 'output': 'output', 'bidirectional': 'bidirectional',
                     'tri_state': 'tri_state'}.get(pin['type'], 'passive')
            sheet.label(net, s, d, key, shape)


# ===================================================================== notes
DATE = '2026-11-18'
SHEET_NOTES = {
    'root': [
        ('WSNES cart v0.4 - mixed SMD/THT, standard SNES PCB shape (ESP32-S3 + 512 KB ROM-SRAM + battery-backed save RAM, LoROM)', 3.0, True),
        ('Assembly field: JLC = SMD assembled by JLCPCB, HAND = hand-soldered (U21 ESP module, U15 PIC, BT1, J3)', 1.5, False),
        ('SIGNAL FLOW\n'
         'SNES edge (Edge_CIC) -> SNES_A* / SNES_D* / SNES_RD_N / SNES_WR_N -> SNES_Buffers (U2-U5) -> SA* / SD* -> ROM SRAM U1 and Save RAM U16\n'
         'ESP32 -> SPI (SR_SCK / SR_MOSI / SR_LATCH via 33R) -> ESP_Serial (U9-U12 595 drive SA* / SD*, U13 165 reads SD* back -> SR_MISO)\n'
         'BUS_ESP (one GPIO, pulled high) selects the owner: 0 = SNES plays (U2-U5 on), 1 = ESP loads (U9-U12 on). ROM_Glue muxes /CE /OE /WE.\n'
         'Level_Reset shifts 5 V status lines down to 3.3 V for the ESP and holds the SNES in reset until the firmware releases it.\n'
         'Net names: labels that cross sheets are GLOBAL labels (same net name everywhere); sheet-internal nets are local (/Sheet/NET).\n'
         'Every IC has its 100 nF decoupling cap on its own sheet.', 1.5, False),
    ],
    'rom': [
        ('BUS OWNERSHIP (single GPIO BUS_ESP, pulled HIGH = ESP owns bus at power-up)\n'
         'BUS_ESP=0 (SNES plays): U2-U4 drive SA*, U5 passes data when ROM_SEL_N=0,\n'
         '   SRAM /CE=ROM_SEL_N, /OE=SNES /RD, /WE=SNES_WE_N (only if MENU_WE_N=0).\n'
         'BUS_ESP=1 (ESP loads): U9-U11 drive SA*, U12 drives SD* when DOUT_OE_N=0,\n'
         '   ROM /CE=EA19, save /CE1=NOT EA19, /OE=ESP_OE_N, /WE=ESP_WE_N. U13 reads SD* back via SPI MISO.\n'
         'LoROM decode: ROM_SEL_N = /ROMSEL OR NOT A15. SNES A16-A19 -> SRAM A15-A18.\n'
         'Writes: SNES_WE_N = /WR OR (SAVE_SEL_N AND (ROM_SEL_N OR MENU_WE_N)) -> save area always, ROM area only in menu mode.\n'
         'U8 is AHCT: it sits in the /ROMSEL -> SRAM /CE path and saves ~24 ns against an HCT157 (FastROM).', 1.5, False),
    ],
    'level': [
        ('Reset: Q1 pulls SNES /RESET low (gate pulled up = SNES held in reset until the ESP firmware releases it).\n'
         'Mailbox: with MENU_WE_N=0 the menu may write into SRAM; each write pulses MBX_IRQ_N to the ESP.\n'
         'CD74HC4050 runs from 3V3; its inputs are 5 V tolerant.', 1.5, False),
    ],
    'esp': [
        ('ESP32-S3 GPIO MAP (N16R8: GPIO35-37 are used by octal PSRAM - do not use!)\n'
         'GPIO4 BUS_ESP   GPIO5 ESP_WE_N   GPIO6 ESP_OE_N   GPIO7 DOUT_OE_N\n'
         'GPIO15 RD_LOAD_N  GPIO16 MENU_WE_N  GPIO17 SNES_RST_DRV (1 = hold SNES in reset)\n'
         'GPIO18 MBX_IRQ_N  GPIO8 RESET_SENSE_N  GPIO9 SNES_5V_SENSE\n'
         'SPI2 (IOMUX): GPIO10 SR_LATCH, GPIO11 SR_MOSI, GPIO12 SR_SCK, GPIO13 SR_MISO (latch + clock via 33R R29/R28)\n'
         'SD (SPI3): GPIO1 CS, GPIO2 SCK, GPIO42 MOSI, GPIO41 MISO, GPIO38 card detect (0 = card in)\n'
         'USB: GPIO19/20 native USB (flashing + serial), GPIO0 BOOT button, GPIO48 status LED\n'
         'Save RAM: GPIO21 SAVE_EN, GPIO14 M11, GPIO47 M12, GPIO39 M13, GPIO40 M14\n'
         'Shift order (MSB first, 32 bit): DATA[7:0], A[23:16] (bit19 = EA19 save select), A[15:8], A[7:0]\n'
         'Never drive 5 V-side outputs while SNES_5V_SENSE = 0 (USB-only power: only the ESP side is alive).', 1.5, False),
    ],
    'serial': [
        ('32-bit chain U9 -> U10 -> U11 -> U12 (MSB first). U11 QD = EA19 (1 = save chip). R8 keeps EA19 low while the 595s are off.\n'
         'U13 (74HCT165) loads SD* on RD_LOAD_N and shifts it out on SR_SCK -> RB_Q7 -> U14 -> SR_MISO. CP and /PL are 3.3 V: keep it HCT.', 1.5, False),
    ],
    'power': [
        ('SNES +5V and USB VBUS meet at ESP_5V through D1 / D6 (Schottky OR). U22 makes +3V3 for the ESP, the SD card and U14.\n'
         'U23 USBLC6 protects D+, D- and VBUS at the connector.', 1.5, False),
    ],
    'save': [
        ('Save RAM: CY62128E at LoROM $70-$7D/$F0-$FF:0000-7FFF, CR2032 backed, write-protected below 4.4 V', 2.0, True),
        ('U17 decodes the LoROM save area: A22=A21=A20=1, A15=0, /ROMSEL=0 -> SAVE_SEL_N (only in SNES mode and when SAVE_EN=1).\n'
         'U19 masks A11-A14 with SAVE_M11..M14 (ESP GPIOs) so the RAM mirrors at the header size (2 KB: all 0, 8 KB: M11+M12, 32 KB: all 1).\n'
         'Some games check the mirroring (anti-copier), so set the masks from the ROM header before releasing reset.\n'
         'ESP access: BUS_ESP=1, address bit EA19 (U11 QD) = 1 selects the save chip, 0 the ROM chip (set masks to 1 for full access).\n'
         'Power fail: U20 drives CE2 low below ~4.4 V, R7 holds it low when the cart is off -> no garbage writes, data kept by BT1.\n'
         'Every SNES write to the save area pulses MBX_IRQ_N -> ESP knows the save is dirty and copies it to SD (.srm) on reset/game change.',
         1.5, False),
    ],
}


def notes_height(notes):
    return sum((s.count('\n') + 1) * size * 1.7 + 2.0 for s, size, _b in notes)


def draw_sheet(sheet, refs, report):
    """Lay out and draw every part (all units) of one sheet plus its PWR_FLAGs and notes."""
    byref = {p['ref']: p for p in D.parts}
    jobs = []                                     # (kind, payload, bbox)
    for ref in refs:
        p = byref[ref]
        ls, pins, units = part_units(sheet, p)
        for u in units:
            bb, vat = unit_extents(sheet, ls, u, p['conns'], p['value'], ref)
            jobs.append(('unit', (p, ls, pins, u, vat), bb))
    for net, key in D.pwr_flags.items():
        if key == sheet.key:
            jobs.append(('flag', net, (-6.0, -6.0, 6.0, STUB + len(net) * CHAR_W + 1.0)))
    title = [(sheet.title, 2.5, True)] + SHEET_NOTES.get(sheet.key, [])
    y0 = 15.24 + notes_height(title) + 2.54
    blocks = rows(jobs)
    for name, w, h in PAPER:
        ymax = h - 42.0
        anchors, right, bottom = pack([b[0] for b in blocks], y0, ymax)
        if right <= w - 15 and bottom <= ymax:
            break
    sheet.paper = name
    used = {}
    placed = [(job, (round(a[0] + dx, 4), round(a[1] + dy, 4))) for (bb, items), a in zip(blocks, anchors)
              for job, dx, dy in items]
    for (kind, payload, _bb), at in placed:
        if kind == 'unit':
            p, ls, pins, u, vat = payload
            if vat:
                vat = (round(at[0] + vat[0], 2), round(at[1] + vat[1], 2), vat[2])
            draw_unit(sheet, p, ls, pins, u, at, report, used.setdefault(p['ref'], set()), vat)
        else:
            sheet.pwr_flag(payload, at)
    for ref in refs:
        extra = set(byref[ref]['conns']) - used.get(ref, set())
        if extra:
            raise SystemExit('Connections to non-existent pins on %s: %s' % (ref, sorted(extra)))
    y = 15.24
    for s, size, bold in title:
        sheet.text(s, (X0, y), size, bold)
        y += (s.count('\n') + 1) * size * 1.7 + 2.0


# ===================================================================== project file
def netclass(name, clearance, track, via_d, via_drill, priority, color='rgba(0, 0, 0, 0.000)', dp=(0.2, 0.25)):
    return {'name': name, 'clearance': clearance, 'track_width': track, 'via_diameter': via_d,
            'via_drill': via_drill, 'microvia_diameter': 0.3, 'microvia_drill': 0.1,
            'diff_pair_width': dp[0], 'diff_pair_gap': dp[1], 'diff_pair_via_gap': 0.25,
            'wire_width': 6, 'bus_width': 12, 'line_style': 0, 'priority': priority, 'tuning_profile': '',
            'pcb_color': color, 'schematic_color': 'rgba(0, 0, 0, 0.000)'}

# Routing classes (v0.4). The colours tint the ratsnest (View > Net colour mode "ratsnest"), so a line shows at a
# glance what it is: red = power (pre-routed into the planes), purple = USB pair, orange = clocks,
# blue = address bus, green = data bus, white/grey = everything else.
# JLC 4-layer limits for reference: 0.09 mm track/space, 0.15 mm drill. These classes stay well above them.
NETCLASSES = [
    (netclass('Default', 0.15, 0.2, 0.5, 0.25, 2147483647), []),
    (netclass('Power', 0.2, 0.5, 0.6, 0.3, 0, 'rgba(235, 64, 52, 0.900)'),
     ['+5V', '+3V3', 'GND', '*ESP_5V', '*VBUS', '*VSAVE', '*VBAT', '*VBAT_R']),
    (netclass('USB', 0.2, 0.3, 0.5, 0.25, 1, 'rgba(186, 85, 211, 0.900)', dp=(0.3, 0.2)),
     ['USB_DP', 'USB_DN']),
    (netclass('Clock', 0.25, 0.2, 0.5, 0.25, 2, 'rgba(255, 165, 0, 0.900)'),
     ['SR_SCK', '*SR_SCK_ESP', 'SR_LATCH', '*SR_LATCH_ESP', '*SD_SCK', 'CIC_CLK', '*CIC_CLK']),
    (netclass('AddrBus', 0.15, 0.2, 0.5, 0.25, 3, 'rgba(66, 135, 245, 0.900)'),
     ['SA?', 'SA??', 'SNES_A?', 'SNES_A??', '*SV_A??', 'EA19', 'EA19_N']),
    (netclass('DataBus', 0.15, 0.2, 0.5, 0.25, 4, 'rgba(60, 200, 90, 0.900)'),
     ['SD?', 'SNES_D?']),
]


def make_project(proj_dir, sheets):
    """Create or update WSNES_Proto.kicad_pro. Only the keys below are managed here; everything else in an existing
    project file (zone defaults, ERC pin map, plot settings, ...) is kept as it is."""
    fn = os.path.join(proj_dir, PROJ + '.kicad_pro')
    pro = json.load(open(fn, encoding='utf-8')) if os.path.exists(fn) else {
        'meta': {'filename': PROJ + '.kicad_pro', 'version': 3}, 'board': {'design_settings': {}},
        'net_settings': {'meta': {'version': 4}}, 'schematic': {}, 'erc': {}, 'libraries': {}, 'pcbnew': {},
        'text_variables': {}}
    ds = pro.setdefault('board', {}).setdefault('design_settings', {})
    ds.setdefault('rules', {}).update({
        'min_clearance': 0.15, 'min_track_width': 0.15, 'min_via_diameter': 0.45,
        'min_through_hole_diameter': 0.2, 'min_via_annular_width': 0.1,
        'min_hole_to_hole': 0.25, 'min_hole_clearance': 0.2,
        'min_copper_edge_clearance': 0.3, 'min_connection': 0.15,
        'min_text_height': 0.8, 'min_text_thickness': 0.08, 'min_silk_clearance': 0.0})
    # Track width / via presets: [0] = "use net class". Cycle with W / Shift+W and the via size list.
    ds['track_widths'] = [0.0, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.8]
    ds['via_dimensions'] = [{'diameter': 0.0, 'drill': 0.0}, {'diameter': 0.45, 'drill': 0.2},
                            {'diameter': 0.5, 'drill': 0.25}, {'diameter': 0.6, 'drill': 0.3},
                            {'diameter': 0.8, 'drill': 0.4}]
    ds['diff_pair_dimensions'] = [{'gap': 0.0, 'via_gap': 0.0, 'width': 0.0},
                                  {'gap': 0.2, 'via_gap': 0.25, 'width': 0.3}]
    ns = pro.setdefault('net_settings', {})
    ns['classes'] = [c for c, _ in NETCLASSES]
    ns['netclass_patterns'] = [{'netclass': c['name'], 'pattern': pat} for c, pats in NETCLASSES for pat in pats]
    ns.setdefault('netclass_assignments', {})
    ns.setdefault('net_colors', {})
    pro['sheets'] = [[ROOT, 'Root']] + [[sh.uuid, sh.name] for sh in sheets]
    with open(fn, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(pro, f, indent=2)
        f.write('\n')


# ===================================================================== main
def main(proj_dir):
    libdir = os.path.join(proj_dir, 'lib')
    os.makedirs(os.path.join(libdir, PROJ + '.pretty'), exist_ok=True)
    edge = build_edge_symbol()
    with open(os.path.join(libdir, PROJ + '.kicad_sym'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(dump(['kicad_symbol_lib', ['version', 20241209], ['generator', Q('wsnes_gen')],
                      ['generator_version', Q('9.0')], edge]) + '\n')
    stale = os.path.join(libdir, PROJ + '.pretty', 'ESP32-S3-DevKitC-1_Socket.kicad_mod')
    if os.path.exists(stale):
        os.remove(stale)
    with open(os.path.join(libdir, PROJ + '.pretty', EDGE_FP + '.kicad_mod'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(dump(build_edge_footprint()) + '\n')
    with open(os.path.join(proj_dir, 'sym-lib-table'), 'w') as f:
        f.write('(sym_lib_table\n\t(version 7)\n\t(lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/lib/%s.kicad_sym")(options "")(descr "WSNES project symbols"))\n)\n' % (PROJ, PROJ))
    with open(os.path.join(proj_dir, 'fp-lib-table'), 'w') as f:
        f.write('(fp_lib_table\n\t(version 7)\n\t(lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/lib/%s.pretty")(options "")(descr "WSNES project footprints"))\n)\n' % (PROJ, PROJ))

    proj = Project({EDGE_SYM: edge})
    report = []
    sheets = []
    for key, name, stem, title, refs in D.SHEETS:
        sh = Sheet(proj, key, name, stem, title, str(uuid.uuid5(NS, 'sheet/' + key)))
        draw_sheet(sh, refs, report)
        sh.write(proj_dir)
        sheets.append(sh)

    # root: title + overview notes + one sheet symbol per block (3 columns)
    root = Sheet(proj, 'root', 'Root', PROJ, 'overview', None)
    y = 15.24
    for s, size, bold in SHEET_NOTES['root']:
        root.text(s, (X0, y), size, bold)
        y += (s.count('\n') + 1) * size * 1.7 + 2.0
    y0 = math.ceil((y + 10) / 2.54) * 2.54
    W, H, DX, DY = 109.22, 30.48, 129.54, 48.26
    extra = []
    for i, sh in enumerate(sheets):
        x, yy = 25.4 + (i % 3) * DX, y0 + (i // 3) * DY
        extra.append(['sheet', ['at', x, yy], ['size', W, H], ['exclude_from_sim', 'no'], ['in_bom', 'yes'],
                      ['on_board', 'yes'], ['dnp', 'no'], ['fields_autoplaced', 'yes'],
                      ['stroke', ['width', 0.1524], ['type', 'solid']], ['fill', ['color', 0, 0, 0, 0.0]],
                      ['uuid', Q(sh.uuid)],
                      ['property', Q('Sheetname'), Q(sh.name), ['at', x, round(yy - 0.7116, 4), 0],
                       ['effects', ['font', ['size', 1.524, 1.524], ['bold', 'yes']], ['justify', 'left', 'bottom']]],
                      ['property', Q('Sheetfile'), Q(sh.stem + '.kicad_sch'), ['at', x, round(yy + H + 0.5884, 4), 0],
                       ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left', 'top']]],
                      ['instances', ['project', Q(PROJ), ['path', Q('/' + ROOT), ['page', Q(str(i + 2))]]]]])
        refs = next(s for s in D.SHEETS if s[0] == sh.key)[4]
        ics = [r for r in refs if not r.startswith(('C', 'R'))]
        body = sh.title + '\n\n' + ', '.join(ics) + '\n+ %d R/C' % (len(refs) - len(ics))
        root.text(body, (x + 2.54, yy + 2.54), 1.27, False, key='sheetbody/' + sh.key)
    root.paper = 'A3'
    extra.append(['sheet_instances', ['path', Q('/'), ['page', Q('1')]]])
    root.items = root.items + extra[:-1]
    root.write(proj_dir, root_extra=extra[-1:])

    make_project(proj_dir, sheets)
    with open(os.path.join(proj_dir, 'tools', 'intended_pins.json'), 'w') as f:
        json.dump(report, f, indent=0)
    print('parts:', len(D.parts), 'pins:', len(report), 'lib symbols:', len(proj.cache),
          'sheets:', ', '.join('%s(%s)' % (s.stem, s.paper) for s in sheets),
          'global nets:', len(proj.global_nets))

if __name__ == '__main__':
    main(os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..')))
