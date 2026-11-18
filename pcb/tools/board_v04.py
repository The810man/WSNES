#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 The810man
"""One-shot v0.4 board update: rip-up, re-link to the hierarchical schematic, two-sided placement, power fan-out.

Run with KiCad's own Python (needs pcbnew), from pcb/:
    kicad-cli sch export netlist --format kicadsexpr -o /tmp/p.net WSNES_Proto.kicad_sch
    "C:/Program Files/KiCad/10.0/bin/python.exe" tools/board_v04.py WSNES_Proto.kicad_pcb /tmp/p.net WSNES_Proto.kicad_pcb

What it does, in order:
  1. removes every track, arc and via (the board gets re-routed by hand; zones and rule areas stay)
  2. applies the schematic netlist: footprint -> symbol path (/sheet/symbol), sheet name/file, value + fields,
     pad nets (hierarchical net names). Adds footprints that are new in the schematic (R28/R29).
  3. marks In1 (GND) and In2 (+5V/+3V3) as power-plane layers, so the router and freerouting keep signals off them
  4. moves the BACK set (see BACK_*) to B.Cu and resolves courtyard overlaps with a small spiral search
  5. fans out every SMD pad on GND/+5V/+3V3 with a short stub + via into the matching plane region
  6. puts every 100 nF decoupling cap on B.Cu right under its IC and ties it to the IC's supply via
Anything it cannot place cleanly is left alone and listed at the end (KiCad shows it as ratsnest).

Run it once. It is not idempotent (it rips up routing). The result is checked with
    kicad-cli pcb drc --refill-zones --save-board --schematic-parity WSNES_Proto.kicad_pcb
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew as P                      # noqa: E402
from sexp import parse, find, find1     # noqa: E402

FPLIB = 'C:/Program Files/KiCad/10.0/share/kicad/footprints'
MM = 1e6
def nm(v): return int(round(v * MM))
def mm(v): return v / MM
def V(x, y): return P.VECTOR2I(nm(x), nm(y))

PLANE_NETS = {'GND': 'GND_PLANE', '+5V': '+5V_PLANE', '+3V3': '+3V3_PLANE'}
VIA_D, VIA_DRILL = 0.6, 0.3            # Power net class via
STUB_W = 0.4

# ---------------------------------------------------------------- what goes to the back
# Decoupling caps are placed separately (under their IC). C19 (VSAVE, no plane) stays on top next to U16.
BACK_IC = ['U2']                      # A0-A7 buffer: all 8 inputs come from the B.Cu fingers 10-17
# R17-R22 (microSD pull-ups) stay on top: on the back they would sit on the B.Silkscreen logo.
BACK_PASSIVE = ['R1', 'R3', 'R6', 'R7', 'R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15', 'R16',
                'R25', 'R26', 'R28', 'R29', 'C22']
NEW_FP_NEAR = {'R28': ('U21', '20'), 'R29': ('U21', '18')}     # new parts: start next to this pad
# A decoupling cap whose supply has no plane (C18 on VSAVE for U16) stays on top next to its IC.

# In2 split (v0.4). v0.3 split +3V3 / +5V along y = 113.6, right through both SRAMs, so U1 VCC, D1, D4 and U20
# had no +5V plane under them. +3V3 now keeps the USB / LDO / microSD band and the ESP column, +5V reaches up
# under the SRAMs. 0.6 mm between the two outlines. (x, y) in mm, board coordinates.
PLANE_3V3 = [(91.5, 86.8), (203.7, 86.8), (203.7, 113.3), (171.0, 113.3), (171.0, 101.0), (128.0, 101.0),
             (128.0, 105.5), (91.5, 105.5)]
PLANE_5V = [(91.5, 106.1), (128.6, 106.1), (128.6, 101.6), (170.4, 101.6), (170.4, 113.9), (203.7, 113.9),
            (203.7, 128.3), (196.3, 128.3), (196.3, 130.1), (199.3, 130.1), (199.3, 136.4), (203.7, 136.4),
            (203.7, 167.2), (97.5, 167.2), (97.5, 144.7), (100.8, 144.7), (100.8, 138.2), (103.8, 138.2),
            (103.8, 136.4), (91.5, 136.4)]


def clearance(netname):
    base = netname.rsplit('/', 1)[-1]
    if base in ('SR_SCK', 'SR_LATCH', 'SR_SCK_ESP', 'SR_LATCH_ESP', 'SD_SCK', 'CIC_CLK'):
        return 0.25
    return 0.2


# ===================================================================== netlist
def read_netlist(path):
    root = parse(open(path, encoding='utf-8').read())
    comps, pinnet = {}, {}
    for c in find(find1(root, 'components'), 'comp'):
        ref = str(find1(c, 'ref')[1])
        sp = find1(c, 'sheetpath')
        props = {}
        for pp in find(c, 'property'):
            v = find1(pp, 'value')
            props[str(find1(pp, 'name')[1])] = str(v[1]) if v else ''
        ds = find1(c, 'datasheet')
        comps[ref] = dict(value=str(find1(c, 'value')[1]), fp=str(find1(c, 'footprint')[1]),
                          datasheet=str(ds[1]) if ds else '',
                          path=str(find1(sp, 'tstamps')[1]) + str(find1(c, 'tstamps')[1]),
                          sheetname=str(find1(sp, 'names')[1]), sheetfile=props.get('Sheetfile', ''),
                          props=props)
    for n in find(find1(root, 'nets'), 'net'):
        name = str(find1(n, 'name')[1])
        for node in find(n, 'node'):
            pinnet[(str(find1(node, 'ref')[1]), str(find1(node, 'pin')[1]))] = name
    return comps, pinnet


# ===================================================================== geometry model
class Model:
    """Axis-aligned copper model: pads (AABB), vias (circles), tracks (segments). All parts sit at 0/90/180/270 deg,
    so AABBs are exact for rect pads and conservative for round/roundrect ones."""
    def __init__(self, board):
        self.b = board
        self.pads = []      # (x0, y0, x1, y1, layers, net, smd, pad)
        self.vias = []      # (x, y, r, net)
        self.segs = []      # (x0, y0, x1, y1, w, layer, net)
        self.court = {'F': [], 'B': []}   # (x0, y0, x1, y1, ref)
        self.outline = P.SHAPE_POLY_SET()
        board.GetBoardPolygonOutlines(self.outline, True)
        self.planes = {}
        self.no_via, self.no_fp = [], []
        for z in board.Zones():
            if z.GetIsRuleArea():
                if z.GetDoNotAllowVias(): self.no_via.append(z)
                if z.GetDoNotAllowFootprints(): self.no_fp.append(z)
            elif z.GetZoneName() in PLANE_NETS.values():
                self.planes[z.GetZoneName()] = z
        for fp in board.GetFootprints():
            for z in fp.Zones():
                if z.GetIsRuleArea():
                    if z.GetDoNotAllowVias(): self.no_via.append(z)
                    if z.GetDoNotAllowFootprints(): self.no_fp.append(z)
        self.rebuild()

    def rebuild(self):
        self.pads, self.court = [], {'F': [], 'B': []}
        for fp in self.b.GetFootprints():
            self.add_fp(fp)
        self.add_art()

    def add_fp(self, fp):
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            layers = set()
            if pad.IsOnLayer(P.F_Cu): layers.add('F')
            if pad.IsOnLayer(P.B_Cu): layers.add('B')
            smd = pad.GetAttribute() in (P.PAD_ATTRIB_SMD, P.PAD_ATTRIB_CONN)
            if not smd: layers |= {'F', 'B', 'I'}
            if not layers: continue
            self.pads.append((mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom()),
                              layers, pad.GetNetname(), smd, pad))
        side = 'B' if fp.IsFlipped() else 'F'
        cb = courtyard_bbox(fp)
        if cb: self.court[side].append(cb + (fp.GetReference(),))

    def add_art(self):
        """Board artwork on the silkscreens is a keep-out for parts on that side."""
        for d in self.b.GetDrawings():
            for lay, side in ((P.B_SilkS, 'B'), (P.F_SilkS, 'F')):
                if d.GetLayer() == lay:
                    bb = d.GetBoundingBox()
                    self.court[side].append((mm(bb.GetLeft()) - 0.3, mm(bb.GetTop()) - 0.3, mm(bb.GetRight()) + 0.3,
                                             mm(bb.GetBottom()) + 0.3, '#art'))

    def remove_fp(self, fp):
        ref = fp.GetReference()
        self.pads = [p for p in self.pads if p[7].GetParentFootprint().GetReference() != ref]
        for s in 'FB':
            self.court[s] = [c for c in self.court[s] if c[4] != ref]

    # ---------------------------------------------------------------- distance helpers
    @staticmethod
    def d_pt_box(x, y, b):
        dx = max(b[0] - x, 0, x - b[2]); dy = max(b[1] - y, 0, y - b[3])
        return math.hypot(dx, dy)

    @staticmethod
    def d_pt_seg(x, y, s):
        ax, ay, bx, by = s[0], s[1], s[2], s[3]
        vx, vy = bx - ax, by - ay
        L = vx * vx + vy * vy
        t = 0 if L == 0 else max(0, min(1, ((x - ax) * vx + (y - ay) * vy) / L))
        return math.hypot(x - ax - t * vx, y - ay - t * vy)

    def inside_board(self, x, y, margin):
        for k in range(8):
            a = k * math.pi / 4
            if not self.outline.Contains(V(x + margin * math.cos(a), y + margin * math.sin(a))):
                return False
        return self.outline.Contains(V(x, y))

    def in_zone(self, z, x, y, margin=0.0):
        pts = [(x, y)] + [(x + margin * math.cos(k * math.pi / 4), y + margin * math.sin(k * math.pi / 4))
                          for k in range(8)] if margin else [(x, y)]
        return all(z.Outline().Contains(V(px, py)) for px, py in pts)

    # ---------------------------------------------------------------- checks
    def via_ok(self, x, y, net, ignore_pad=None):
        r = VIA_D / 2
        if not self.inside_board(x, y, r + 0.35):
            return False
        ring = [(x, y)] + [(x + (r + 0.1) * math.cos(k * math.pi / 4), y + (r + 0.1) * math.sin(k * math.pi / 4))
                           for k in range(8)]
        if any(z.Outline().Contains(V(px, py)) for z in self.no_via for px, py in ring):
            return False
        plane = self.planes.get(PLANE_NETS.get(net))
        if plane is None or not self.in_zone(plane, x, y, r + 0.45):
            return False
        cl_me = clearance(net)
        for p in self.pads:
            if p[7] is ignore_pad: continue
            d = self.d_pt_box(x, y, p)
            if p[5] == net:
                if p[6] and d < r + 0.1: return False          # no via-in-pad, even on the same net
                if not p[6] and d < r + 0.25: return False      # keep hole-to-hole distance to THT pads
                continue
            if d < r + max(cl_me, clearance(p[5])) + 0.02: return False
        for (vx, vy, vr, vn) in self.vias:
            if math.hypot(vx - x, vy - y) < r + vr + (0.25 if vn == net else max(cl_me, clearance(vn))) + 0.05:
                return False
        for s in self.segs:
            if s[6] == net: continue
            if self.d_pt_seg(x, y, s) < r + s[4] / 2 + max(cl_me, clearance(s[6])) + 0.02: return False
        return True

    def seg_ok(self, ax, ay, bx, by, w, layer, net, own_pad=None):
        n = max(2, int(math.hypot(bx - ax, by - ay) / 0.05))
        cl_me = clearance(net)
        pts = [(ax + (bx - ax) * i / n, ay + (by - ay) * i / n) for i in range(n + 1)]
        for p in self.pads:
            if layer not in p[4] or p[7] is own_pad or p[5] == net: continue
            need = w / 2 + max(cl_me, clearance(p[5])) + 0.02
            if any(self.d_pt_box(x, y, p) < need for x, y in pts): return False
        for (vx, vy, vr, vn) in self.vias:
            if vn == net: continue
            need = vr + w / 2 + max(cl_me, clearance(vn)) + 0.02
            if self.d_pt_seg(vx, vy, (ax, ay, bx, by)) < need: return False
        for s in self.segs:
            if s[5] != layer or s[6] == net: continue
            need = w / 2 + s[4] / 2 + max(cl_me, clearance(s[6])) + 0.02
            if any(self.d_pt_seg(x, y, s) < need for x, y in pts[::4] + [pts[-1]]): return False
        if not all(self.inside_board(x, y, w / 2 + 0.3) for x, y in (pts[0], pts[-1])): return False
        return True

    def fp_ok(self, fp, side, ignore_ref):
        cb = courtyard_bbox(fp)
        if cb is None: return True
        if not all(self.inside_board(x, y, 0.2) for x, y in ((cb[0], cb[1]), (cb[2], cb[1]), (cb[0], cb[3]), (cb[2], cb[3]))):
            return False
        for c in self.court[side]:
            if c[4] == ignore_ref: continue
            if cb[0] < c[2] and c[0] < cb[2] and cb[1] < c[3] and c[1] < cb[3]: return False
        for z in self.no_fp:
            if any(z.Outline().Contains(V(x, y)) for x, y in ((cb[0], cb[1]), (cb[2], cb[1]), (cb[0], cb[3]), (cb[2], cb[3]))):
                return False
        mine = [pad for pad in fp.Pads()]
        lay = side
        for pad in mine:
            bb = pad.GetBoundingBox()
            box = (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom()))
            net = pad.GetNetname()
            for p in self.pads:
                if p[7].GetParentFootprint().GetReference() == ignore_ref or lay not in p[4]: continue
                gap = max(p[0] - box[2], box[0] - p[2], p[1] - box[3], box[1] - p[3])
                if gap < max(clearance(net), clearance(p[5])) + 0.05: return False
            for (vx, vy, vr, vn) in self.vias:
                if vn == net: continue
                if self.d_pt_box(vx, vy, box) < vr + max(clearance(net), clearance(vn)) + 0.05: return False
        return True


def courtyard_bbox(fp):
    fp.BuildCourtyardCaches()
    poly = fp.GetCourtyard(P.B_CrtYd if fp.IsFlipped() else P.F_CrtYd)
    if poly.OutlineCount() == 0:
        return None
    bb = poly.BBox()
    return (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom()))


# ===================================================================== board edits
def add_via(board, model, x, y, net):
    v = P.PCB_VIA(board)
    v.SetPosition(V(x, y))
    v.SetWidth(nm(VIA_D))
    v.SetDrill(nm(VIA_DRILL))
    v.SetLayerPair(P.F_Cu, P.B_Cu)
    v.SetNet(board.FindNet(net))
    board.Add(v)
    model.vias.append((x, y, VIA_D / 2, net))


def add_seg(board, model, ax, ay, bx, by, w, layer, net):
    if math.hypot(bx - ax, by - ay) < 1e-3:
        return
    t = P.PCB_TRACK(board)
    t.SetStart(V(ax, ay)); t.SetEnd(V(bx, by)); t.SetWidth(nm(w))
    t.SetLayer(P.F_Cu if layer == 'F' else P.B_Cu)
    t.SetNet(board.FindNet(net))
    board.Add(t)
    model.segs.append((ax, ay, bx, by, w, layer, net))


def pad_info(pad):
    bb = pad.GetBoundingBox()
    c = pad.GetPosition()
    w, h = mm(bb.GetWidth()), mm(bb.GetHeight())
    layer = 'F' if pad.IsOnLayer(P.F_Cu) else 'B'
    return mm(c.x), mm(c.y), w, h, layer


def fanout(board, model, pad, prefer=None, max_reuse=1.6):
    """Stub + via from an SMD power pad into its plane. Returns the via position or None."""
    net = pad.GetNetname()
    cx, cy, w, h, layer = pad_info(pad)
    tw = STUB_W if min(w, h) >= 0.6 else 0.3     # 0.3 mm into 0.4 mm TSSOP pads keeps 0.3 mm to the neighbours
    fp = pad.GetParentFootprint()
    fc = fp.GetPosition()
    fx, fy = mm(fc.x), mm(fc.y)
    # 1) reuse a same-net via close by
    best = None
    for (vx, vy, vr, vn) in model.vias:
        if vn != net: continue
        d = math.hypot(vx - cx, vy - cy)
        if d <= max_reuse + max(w, h) / 2 and model.seg_ok(cx, cy, vx, vy, tw, layer, net, own_pad=pad):
            if best is None or d < best[0]:
                best = (d, vx, vy)
    if best:
        add_seg(board, model, cx, cy, best[1], best[2], tw, layer, net)
        return best[1], best[2]
    # 2) new via. Directions: along the pad's long axis towards the part body first, then away, then sideways.
    long_x = w >= h
    ax_ = (1, 0) if long_x else (0, 1)
    toward = (fx - cx) * ax_[0] + (fy - cy) * ax_[1]
    nin = (ax_[0] * (1 if toward >= 0 else -1), ax_[1] * (1 if toward >= 0 else -1)) if abs(toward) > 0.05 else None
    perp = (ax_[1], ax_[0])
    dirs = []
    if prefer: dirs.append(prefer)
    if nin: dirs += [nin, (-nin[0], -nin[1])]
    else: dirs += [ax_, (-ax_[0], -ax_[1])]
    dirs += [perp, (-perp[0], -perp[1])]
    diag = [(a * 0.7071, b * 0.7071) for a in (1, -1) for b in (1, -1)]
    dirs += diag
    cands = []
    for rank, d in enumerate(dirs):
        half = abs(d[0]) * w / 2 + abs(d[1]) * h / 2
        for k in range(18):
            dist = half + VIA_D / 2 + 0.25 + k * 0.25
            cands.append((dist + rank * 0.35, cx + d[0] * dist, cy + d[1] * dist))
    cands.sort()
    for _cost, vx, vy in cands:
        vx, vy = round(vx, 3), round(vy, 3)
        if model.via_ok(vx, vy, net, ignore_pad=pad) and model.seg_ok(cx, cy, vx, vy, tw, layer, net, own_pad=pad):
            add_via(board, model, vx, vy, net)
            add_seg(board, model, cx, cy, vx, vy, tw, layer, net)
            return vx, vy
    return None


def flip_to_back(fp):
    if not fp.IsFlipped():
        fp.Flip(fp.GetPosition(), P.FLIP_DIRECTION_LEFT_RIGHT)


def spiral_place(model, fp, x0, y0, rots=(None,), rmax=9.0):
    """Move fp to the nearest free spot around (x0, y0) on its current side."""
    side = 'B' if fp.IsFlipped() else 'F'
    ref = fp.GetReference()
    model.remove_fp(fp)
    for r10 in range(0, int(rmax * 4) + 1):
        r = r10 * 0.25
        n = 1 if r == 0 else max(8, int(2 * math.pi * r / 0.35))
        for k in range(n):
            a = 2 * math.pi * k / n
            for rot in rots:
                if rot is not None: fp.SetOrientationDegrees(rot)
                fp.SetPosition(V(round(x0 + r * math.cos(a), 3), round(y0 + r * math.sin(a), 3)))
                if model.fp_ok(fp, side, ref):
                    model.add_fp(fp)
                    return True
    fp.SetPosition(V(x0, y0))
    model.add_fp(fp)
    return False


# ===================================================================== main
TAB = chr(9)


def strip_routing(src, dst):
    """Copy the board without its top-level segment / arc / via nodes. Done on the text: removing tracks through
    the KiCad 10 Python API breaks SWIG's type casting for everything fetched afterwards."""
    out, skip, n = [], False, 0
    for line in open(src, encoding='utf-8'):
        s = line.rstrip(chr(13) + chr(10))
        if not skip and s in (TAB + '(segment', TAB + '(arc', TAB + '(via'):
            skip, n = True, n + 1
            continue
        if skip:
            if s == TAB + ')':
                skip = False
            continue
        out.append(line)
    open(dst, 'w', encoding='utf-8', newline='').write(''.join(out))
    return n


T0 = __import__('time').time()
def tick(msg):
    print('[%6.1fs] %s' % (__import__('time').time() - T0, msg), flush=True)


def main(src, netfile, dst):
    log = []
    # 1. rip-up
    tmp = dst + '.stripped.kicad_pcb'
    n_tr = strip_routing(src, tmp)
    log.append('removed %d tracks/arcs/vias' % n_tr)
    tick('stripped')
    board = P.LoadBoard(tmp)
    os.remove(tmp)
    tick('loaded')
    comps, pinnet = read_netlist(netfile)

    # 2. netlist
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    for ref in sorted(set(comps) - set(fps)):
        lib, name = comps[ref]['fp'].split(':')
        fp = P.FootprintLoad(FPLIB + '/' + lib + '.pretty', name)
        fp.SetFPID(P.LIB_ID(lib, name))           # FootprintLoad leaves the library nickname empty
        fp.SetReference(ref)
        board.Add(fp)
        fps[ref] = fp
        fp.Reference().SetVisible(False)          # like every other passive on this board
        if ref in NEW_FP_NEAR:
            o, pin = NEW_FP_NEAR[ref]
            pp = next(p for p in fps[o].Pads() if p.GetNumber() == pin).GetPosition()
            fp.SetPosition(pp)
        log.append('added footprint %s (%s)' % (ref, comps[ref]['fp']))
    extra = sorted(set(fps) - set(comps))
    if extra:
        raise SystemExit('footprints without symbol: %s' % extra)

    def getnet(name):
        ni = board.FindNet(name)
        if ni is None:
            ni = P.NETINFO_ITEM(board, name)
            board.Add(ni)
        return ni

    for ref, fp in fps.items():
        c = comps[ref]
        fp.SetPath(P.KIID_PATH(c['path']))
        fp.SetSheetname(c['sheetname'])
        fp.SetSheetfile(c['sheetfile'])
        fp.SetValue(c['value'])
        if c['datasheet'] and fp.GetField('Datasheet') is not None:
            fp.GetField('Datasheet').SetText(c['datasheet'])
        for k in ('MPN', 'Manufacturer', 'LCSC', 'Assembly', 'Note'):
            if c['props'].get(k):
                f = fp.GetField(k)
                if f is not None:
                    f.SetText(c['props'][k])
                else:
                    fp.SetField(k, c['props'][k])
        for pad in fp.Pads():
            num = pad.GetNumber()
            net = pinnet.get((ref, num))
            if net:
                pad.SetNet(getnet(net))
            else:
                pad.SetNetCode(0)
    board.BuildConnectivity()

    # 3. plane layers + In2 split
    board.SetLayerType(P.In1_Cu, P.LT_POWER)
    board.SetLayerType(P.In2_Cu, P.LT_POWER)
    for z in board.Zones():
        pts = {'+3V3_PLANE': PLANE_3V3, '+5V_PLANE': PLANE_5V}.get(z.GetZoneName())
        if pts and not z.GetIsRuleArea():
            o = z.Outline()
            o.RemoveAllContours()
            o.NewOutline()
            for x, y in pts:
                o.Append(nm(x), nm(y))
            log.append('reshaped %s' % z.GetZoneName())
    # back silkscreen still said v0.3
    for d in board.GetDrawings():
        if d.GetClass() == 'PCB_TEXT' and d.GetText() == 'WSNES v0.3':
            d.SetText('WSNES v0.4')

    tick('netlist applied')
    model = Model(board)
    tick('model built')

    # 4. back side: IC(s) in place, passives in place then de-overlapped
    for ref in BACK_IC + BACK_PASSIVE:
        fp = fps[ref]
        p = fp.GetPosition()
        model.remove_fp(fp)
        flip_to_back(fp)
        fp.SetPosition(p)
        model.add_fp(fp)
    for ref in BACK_IC + BACK_PASSIVE:
        fp = fps[ref]
        p = fp.GetPosition()
        rot = fp.GetOrientationDegrees()
        if not spiral_place(model, fp, mm(p.x), mm(p.y), rots=(rot, (rot + 90) % 360)):
            log.append('NO free spot on B for %s, left overlapping at %.2f %.2f' % (ref, mm(p.x), mm(p.y)))

    tick('back side placed')
    decaps = {}
    for ref, c in comps.items():
        note = c['props'].get('Note', '')
        supply = pinnet.get((ref, '1'), '')
        if note.startswith('decouples ') and supply in PLANE_NETS:
            decaps[ref] = note.split()[1]
    # take the decaps out of the model while the ICs fan out (they move afterwards)
    for ref in decaps:
        model.remove_fp(fps[ref])

    # 5. fan-out of every SMD power pad except the decaps
    skipped = []
    p1 = fps['P1']
    for pad in p1.Pads():                         # edge fingers: straight up into the board, wide stub, 2 vias
        net = pad.GetNetname()
        if net not in PLANE_NETS: continue
        cx, cy, w, h, layer = pad_info(pad)
        top = cy - h / 2
        ok = 0
        for dx in (-0.5, 0.5):
            vx, vy = round(cx + dx, 3), round(top - 1.6, 3)
            if any(abs(x - vx) < 0.01 and abs(y - vy) < 0.01 and n == net for x, y, r, n in model.vias):
                ok += 1                           # the finger on the other side (same net) already put it here
            elif model.via_ok(vx, vy, net, ignore_pad=pad):
                add_via(board, model, vx, vy, net); ok += 1
        if ok:
            add_seg(board, model, cx, cy, cx, top - 1.6, 0.8, layer, net)
            if ok == 2:
                add_seg(board, model, cx - 0.5, top - 1.6, cx + 0.5, top - 1.6, 0.6, layer, net)
        else:
            skipped.append('P1.%s' % pad.GetNumber())
    for ref in sorted(fps):
        if ref in decaps or ref == 'P1': continue
        fp = fps[ref]
        for pad in fp.Pads():
            net = pad.GetNetname()
            if net not in PLANE_NETS: continue
            if pad.GetAttribute() not in (P.PAD_ATTRIB_SMD,): continue
            if ref == 'U21' and pad.GetNumber() == '41':
                continue                          # ESP centre pad: optional for hand soldering, pins 1/40 are GND
            if fanout(board, model, pad) is None:
                skipped.append('%s.%s (%s)' % (ref, pad.GetNumber(), net))

    tick('fan-out done')
    # 6. decoupling caps under their IC, pad 1 tied to the IC supply via on B.Cu
    for cref in sorted(decaps, key=lambda r: int(r[1:])):
        cap, ic = fps[cref], fps[decaps[cref]]
        supply = next(p.GetNetname() for p in cap.Pads() if p.GetNumber() == '1')
        vpad = next((p for p in ic.Pads() if p.GetNetname() == supply), None)
        placed = False
        if vpad is not None:
            vx, vy, w, h, _l = pad_info(vpad)
            near = [(x, y) for (x, y, r, n) in model.vias if n == supply and math.hypot(x - vx, y - vy) < 3.0]
            if near:
                ax, ay = min(near, key=lambda q: math.hypot(q[0] - vx, q[1] - vy))
                flip_to_back(cap)
                for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    rot = 0 if d[1] == 0 else 90
                    for extra_d in (0.0, 0.25, 0.5, 0.75, 1.0):
                        cx, cy = ax + d[0] * (1.75 + extra_d), ay + d[1] * (1.75 + extra_d)
                        for r in (rot, rot + 180):
                            cap.SetOrientationDegrees(r % 360)
                            cap.SetPosition(V(cx, cy))
                            p1_ = next(p for p in cap.Pads() if p.GetNumber() == '1').GetPosition()
                            if math.hypot(mm(p1_.x) - ax, mm(p1_.y) - ay) > 1.3: continue
                            if model.fp_ok(cap, 'B', cref):
                                placed = True
                                break
                        if placed: break
                    if placed: break
        if not placed:
            # fall back: free spot on B as close to the IC supply pin as possible
            flip_to_back(cap)
            tx, ty = (vx, vy) if vpad is not None else (mm(ic.GetPosition().x), mm(ic.GetPosition().y))
            placed = spiral_place(model, cap, tx, ty, rots=(0, 90))
            if not placed:
                log.append('NO free spot on B for %s' % cref)
        else:
            model.add_fp(cap)
        for pad in cap.Pads():
            if pad.GetNetname() in PLANE_NETS and fanout(board, model, pad, max_reuse=1.9) is None:
                skipped.append('%s.%s (%s)' % (cref, pad.GetNumber(), pad.GetNetname()))

    tick('decaps done')
    board.BuildConnectivity()
    # SaveBoard() also writes <name>.kicad_pro from the board's settings. The board was loaded from a temp copy
    # without its project, so those are KiCad defaults: keep the real project file.
    pro = os.path.splitext(dst)[0] + '.kicad_pro'
    keep = open(pro, 'rb').read() if os.path.exists(pro) else None
    P.SaveBoard(dst, board)
    if keep is not None:
        open(pro, 'wb').write(keep)
    tick('saved')
    vias = sum(1 for t in board.GetTracks() if t.GetClass() == 'PCB_VIA')
    log.append('fan-out: %d vias, %d stubs' % (vias, sum(1 for t in board.GetTracks()) - vias))
    log.append('back side: ' + ', '.join(sorted((r for r, f in fps.items() if f.IsFlipped()),
                                                 key=lambda r: (r[0], int(r[1:])))))
    log.append('not fanned out (route these by hand): ' + (', '.join(skipped) if skipped else 'none'))
    print('\n'.join(log))


if __name__ == '__main__':
    main(*sys.argv[1:4])
