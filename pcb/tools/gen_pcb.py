#!/usr/bin/env python3
"""Build WSNES_Proto.kicad_pcb: standard SNES PCB outline, 4 layers, placed footprints, nets, planes.

Usage: python3 gen_pcb.py <project_dir>
Requires KiCad 9 python (pcbnew) and kicad-cli. Routing is NOT done here.
WARNING: rebuilds the board from scratch - do not run once you have started routing.
Also writes: freerouting/WSNES_Proto.dsn and production/jlc/ (BOM + CPL for the JLC-assembled parts).
"""
import csv, math, os, re, subprocess, sys
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_project as G
import design as D

PROJ = 'WSNES_Proto'
FPDIR = '/usr/share/kicad/footprints/'
MM = pcbnew.FromMM
def V(x, y): return pcbnew.VECTOR2I(MM(x), MM(y))

# ------------------------------------------------------------------ board frame (standard SNES cartridge PCB shape)
CX, PY = 150.0, 160.0               # tab centre / finger centre line (edge footprint origin)
SY = PY + G.TAB_TOP                 # shoulder = bottom edge of the board body
def R(dx, dy): return (round(CX + dx, 3), round(SY + dy, 3))
# body 112.2 x 66.7 mm above the shoulder; corner steps + side notches locate the board in the shell
OUTLINE = [R(-30, 0), R(-52.55, 0), R(-52.55, -8.85), R(-49.25, -8.85), R(-49.25, -15.35), R(-46.25, -15.35),
           R(-46.25, -17.1), R(-58.5, -17.1), R(-58.5, -55.95), R(-48.9, -55.95), R(-48.9, -62.7), R(-46.65, -62.7),
           R(-46.65, -66.7), R(46.75, -66.7), R(46.75, -62.7), R(49.0, -62.7), R(49.0, -55.95), R(53.7, -55.95),
           R(53.7, -25.2), R(46.3, -25.2), R(46.3, -23.45), R(49.3, -23.45), R(49.3, -17.1), R(53.7, -17.1),
           R(53.7, 0), R(30, 0)]              # the tab itself is drawn by the edge footprint
Y_TOP = SY - 66.7
POUR = OUTLINE[1:-1] + [R(53.7, -0.8), R(-52.55, -0.8)]
POUR = [(x, min(y, SY - 0.8)) for x, y in POUR]
# In2 is split: +3V3 in the top band (ESP, SD, LDO), +5V below (logic, SRAMs, PIC)
SPLIT_Y = SY - 39.8
THREE_V3 = [R(-58.5, -66.7), R(53.7, -66.7), R(53.7, -40.2), R(-58.5, -40.2)]
FIVE_V = [R(-58.5, -39.5), R(53.7, -39.5), R(53.7, -25.2), R(46.3, -25.2), R(46.3, -23.45), R(49.3, -23.45),
          R(49.3, -17.1), R(53.7, -17.1), R(53.7, -0.8), R(-52.55, -0.8), R(-52.55, -8.85), R(-49.25, -8.85),
          R(-49.25, -15.35), R(-46.25, -15.35), R(-46.25, -17.1), R(-58.5, -17.1)]

# ------------------------------------------------------------------ hand placement of the big parts: ref -> (x, y, rot)
PLACE = {
    'P1': (CX, PY, 0),
    # top edge: microSD + USB-C open towards the top, ESP antenna at the top edge
    'J2': (113.0, Y_TOP + 8.95, 180), 'J5': (154.0, Y_TOP + 4.2, 180), 'U21': (186.0, Y_TOP + 12.8, 0),
    'BT1': (94.7, 117.4, 0),
    # memories
    'U1': (133.0, 113.8, 90), 'U16': (156.5, 113.8, 90),
    # row A: ESP-side shift registers, level shifter, mux
    'U9': (126.5, 126.2, 0), 'U10': (136.5, 126.2, 0), 'U11': (146.5, 126.2, 0), 'U12': (156.5, 126.2, 0),
    'U13': (166.5, 126.2, 0), 'U14': (176.5, 126.2, 0), 'U8': (186.5, 126.2, 0),
    # row B: glue + save logic
    'U6': (126.5, 135.6, 0), 'U7': (136.5, 135.6, 0), 'U18': (146.5, 135.6, 0), 'U19': (156.5, 135.6, 0),
    # bottom row next to the fingers
    'U15': (104.5, 151.0, 90), 'J3': (106.0, 139.6, 90),
    'U5': (137.0, 147.6, 90), 'U17': (146.5, 147.6, 90), 'U2': (155.5, 147.6, 90), 'U4': (164.5, 147.6, 90),
    'U3': (173.5, 147.6, 90),
}
EDGE_PARTS = ('J2', 'J5', 'U21')   # allowed to reach the board edge / overhang it

# small parts: auto-placed next to an anchor pad (ref, pad); decoupling caps anchor at their IC's VCC pin
ANCHOR = {
    'C25': ('U21', '2'), 'C22': ('U21', '3'), 'R25': ('U21', '3'), 'SW2': ('U21', '3'),
    'R26': ('U21', '27'), 'SW1': ('U21', '27'), 'R27': ('U21', '25'), 'D7': ('U21', '25'),
    'C26': ('J2', '4'), 'R18': ('J2', '7'), 'R19': ('J2', '3'), 'R20': ('J2', '8'), 'R21': ('J2', '1'),
    'R22': ('J2', '10'), 'R17': ('J2', '2'),
    'R23': ('J5', 'A5'), 'R24': ('J5', 'B5'), 'D6': ('J5', 'A4'), 'U22': ('J5', 'A4'), 'C23': ('J5', 'A4'),
    'C24': ('J5', 'A4'), 'C1': ('J5', 'A4'), 'D1': ('J5', 'A4'),
    'R10': ('U21', '4'), 'R11': ('U21', '5'), 'R12': ('U21', '6'), 'R13': ('U21', '7'), 'R14': ('U21', '8'),
    'R15': ('U21', '9'), 'R16': ('U21', '10'), 'R1': ('U21', '10'),
    'Q1': ('P1', '26'), 'C2': ('P1', '58'), 'R5': ('P1', '58'), 'D2': ('P1', '58'),
    'R2': ('U15', '4'), 'R4': ('U15', '3'), 'D3': ('U15', '3'),
    'R3': ('U14', '9'), 'R8': ('U6', '12'),
    'U20': ('U16', '30'), 'R6': ('U16', '30'), 'R7': ('U16', '30'), 'D4': ('U16', '32'), 'R9': ('U16', '32'),
}
SILK = [('WSNES v0.3', 150.0, 118.0, 2.0), ('ESP32-S3 + 512KB ROM + battery save', 150.0, 121.5, 1.2),
        ('1.2mm 4-layer ENIG, 45deg bevel', 150.0, 124.0, 1.0)]

STACKUP = """\t\t(stackup
\t\t\t(layer "F.SilkS" (type "Top Silk Screen"))
\t\t\t(layer "F.Paste" (type "Top Solder Paste"))
\t\t\t(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
\t\t\t(layer "F.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "dielectric 1" (type "prepreg") (thickness 0.21) (material "FR4") (epsilon_r 4.4) (loss_tangent 0.02))
\t\t\t(layer "In1.Cu" (type "copper") (thickness 0.0152))
\t\t\t(layer "dielectric 2" (type "core") (thickness 0.65) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))
\t\t\t(layer "In2.Cu" (type "copper") (thickness 0.0152))
\t\t\t(layer "dielectric 3" (type "prepreg") (thickness 0.21) (material "FR4") (epsilon_r 4.4) (loss_tangent 0.02))
\t\t\t(layer "B.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
\t\t\t(layer "B.Paste" (type "Bottom Solder Paste"))
\t\t\t(layer "B.SilkS" (type "Bottom Silk Screen"))
\t\t\t(copper_finish "ENIG")
\t\t\t(dielectric_constraints no)
\t\t\t(edge_connector bevelled)
\t\t)
"""


def add_stackup(pcb_path):
    """1.2 mm 4-layer board, ENIG, bevelled edge connector (pcbnew python has no stackup API)."""
    s = open(pcb_path, encoding='utf-8').read()
    if '(stackup' in s:
        return
    i = s.index('(setup')
    j = s.index('\n', i) + 1
    s = s[:j] + STACKUP + s[j:]
    s = s.replace('(thickness 1.6)', '(thickness 1.2)', 1)
    open(pcb_path, 'w', encoding='utf-8').write(s)


def export_netlist(proj_dir):
    out = os.path.join(proj_dir, PROJ + '.net')
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', out,
                    os.path.join(proj_dir, PROJ + '.kicad_sch')], check=True, capture_output=True)
    s = open(out, encoding='utf-8').read()
    comps = {}
    for m in re.finditer(r'\(comp \(ref "([^"]+)"\)(.*?)\(tstamps "([^"]+)"\)\)', s, re.S):
        body = m.group(2)
        val = re.search(r'\(value "([^"]*)"\)', body).group(1)
        fp = re.search(r'\(footprint "([^"]*)"\)', body).group(1)
        comps[m.group(1)] = dict(value=val, fp=fp, tstamp=m.group(3).split()[0])
    nets = {}
    for m in re.finditer(r'\(net \(code "\d+"\) \(name "([^"]*)"\)(.*?)(?=\(net \(code|\Z)', s, re.S):
        for ref, pin in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2)):
            nets[(ref, pin)] = m.group(1)
    return comps, nets


def load_fp(proj_dir, fpid):
    lib, name = fpid.split(':')
    path = os.path.join(proj_dir, 'lib', lib + '.pretty') if lib == PROJ else FPDIR + lib + '.pretty'
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit('footprint not found: ' + fpid)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def segs(board, pts, layer=pcbnew.Edge_Cuts, w=0.1):
    for a, b in zip(pts, pts[1:]):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(*a)); s.SetEnd(V(*b)); s.SetLayer(layer); s.SetWidth(MM(w))
        board.Add(s)


def zone(board, pts, layer, net, name='', priority=0):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    ol = z.Outline()
    ol.NewOutline()
    for p in pts:
        ol.Append(MM(p[0]), MM(p[1]))
    z.SetNet(net)
    z.SetLocalClearance(MM(0.25))
    z.SetMinThickness(MM(0.2))
    z.SetThermalReliefGap(MM(0.3))
    z.SetThermalReliefSpokeWidth(MM(0.4))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetAssignedPriority(priority)
    if name:
        z.SetZoneName(name)
    board.Add(z)
    return z


def text(board, s, x, y, size=1.2, layer=pcbnew.F_SilkS):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s); t.SetPosition(V(x, y)); t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size))); t.SetTextThickness(MM(size * 0.15))
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    board.Add(t)


# ------------------------------------------------------------------ geometry helpers for the auto-placer
def in_poly(x, y, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside

def rect_in_board(r, poly, margin=0.3):
    x0, y0, x1, y1 = r[0] - margin, r[1] - margin, r[2] + margin, r[3] + margin
    if not all(in_poly(x, y, poly) for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))):
        return False
    return not any(x0 < px < x1 and y0 < py < y1 for px, py in poly)

def overlap(a, b, m=0.15):
    return a[0] - m < b[2] and b[0] - m < a[2] and a[1] - m < b[3] and b[1] - m < a[3]

def crtyd(fp):
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    if cy.OutlineCount() == 0:
        bb = fp.GetBoundingBox(False)
    else:
        bb = cy.BBox()
    return (pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()))

def fab_box(fp):
    xs, ys = [], []
    for g in fp.GraphicalItems():
        if g.GetLayer() == pcbnew.F_Fab and g.GetClass() == 'PCB_SHAPE':
            bb = g.GetBoundingBox()
            xs += [pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetRight())]
            ys += [pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetBottom())]
    return (min(xs), min(ys), max(xs), max(ys))


def main(proj_dir):
    comps, pinnet = export_netlist(proj_dir)
    pcb_path = os.path.join(proj_dir, PROJ + '.kicad_pcb')
    G.make_project(proj_dir)
    board = pcbnew.NewBoard(pcb_path)
    board.SetCopperLayerCount(4)
    board.GetDesignSettings().SetBoardThickness(MM(1.2))

    netobj = {}
    for name in sorted(set(pinnet.values())):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netobj[name] = ni

    info = {p['ref']: p for p in D.parts}
    fps = {}
    for ref, c in comps.items():
        fp = load_fp(proj_dir, c['fp'])
        fp.SetReference(ref); fp.SetValue(c['value'])
        fp.SetPath(pcbnew.KIID_PATH('/' + c['tstamp']))
        fp.SetSheetfile(PROJ + '.kicad_sch'); fp.SetSheetname('/')
        for pad in fp.Pads():
            n = pinnet.get((ref, pad.GetNumber()))
            if n is not None:
                pad.SetNet(netobj[n])
        fps[ref] = fp
        board.Add(fp)

    def put(ref, x, y, rot):
        fps[ref].SetOrientationDegrees(rot)
        fps[ref].SetPosition(V(x, y))

    # ---- big parts
    occupied = []
    for ref, (x, y, rot) in PLACE.items():
        put(ref, x, y, rot)
        if ref == 'P1':
            continue
        if ref == 'U21':   # T-shaped courtyard: antenna keep-out (wide) + module body (narrow)
            ux, uy = pcbnew.ToMM(fps[ref].GetPosition().x), pcbnew.ToMM(fps[ref].GetPosition().y)
            occupied.append(('U21', (ux - 24.0, uy - 27.75, ux + 24.0, uy - 6.75)))
            occupied.append(('U21', (ux - 9.74, uy - 6.75, ux + 9.74, uy + 13.45)))
        else:
            occupied.append((ref, crtyd(fps[ref])))
    # finger area below the shoulder
    occupied.append(('TAB', (CX - 31, SY - 0.4, CX + 31, PY + 6)))

    # ---- small parts: spiral search around the anchor pad
    cap_for = {p['ref']: p['note'].split()[1] for p in D.parts if p.get('note', '').startswith('decouples ')}
    def anchor_of(ref):
        if ref in cap_for:
            ic = fps[cap_for[ref]]
            pads = [p for p in ic.Pads() if p.GetNetname() in ('+5V', '+3V3', '/VSAVE')]
            return pads[0].GetPosition()
        aref, apad = ANCHOR[ref]
        return [p for p in fps[aref].Pads() if p.GetNumber() == apad][0].GetPosition()
    order = list(cap_for) + [r for r in ANCHOR]
    missing = [r for r in fps if r not in PLACE and r not in order]
    if missing:
        raise SystemExit('no placement rule for: %s' % missing)
    poly = OUTLINE
    unplaced = []
    for ref in order:
        fp = fps[ref]
        a = anchor_of(ref)
        ax, ay = pcbnew.ToMM(a.x), pcbnew.ToMM(a.y)
        shapes = []
        for rot in (0, 90):
            fp.SetOrientationDegrees(rot); fp.SetPosition(V(0, 0))
            shapes.append((rot, crtyd(fp)))
        done = False
        r = 0.0
        while r < 40 and not done:
            n = max(1, int(2 * math.pi * r / 0.5))
            for k in range(n):
                t = 2 * math.pi * k / n
                x, y = round(ax + r * math.cos(t), 2), round(ay + r * math.sin(t), 2)
                for rot, s in shapes:
                    box = (s[0] + x, s[1] + y, s[2] + x, s[3] + y)
                    if not rect_in_board(box, poly):
                        continue
                    if any(overlap(box, o) for _, o in occupied):
                        continue
                    put(ref, x, y, rot)
                    occupied.append((ref, box))
                    done = True
                    break
                if done:
                    break
            r += 0.5
        if not done:
            unplaced.append(ref)

    # ---- reference texts: only on parts you solder yourself (JLC does not need silkscreen refs)
    for ref, fp in fps.items():
        rr = fp.Reference()
        rr.SetTextSize(pcbnew.VECTOR2I(MM(0.9), MM(0.9))); rr.SetTextThickness(MM(0.15))
        rr.SetPosition(fp.GetPosition()); rr.SetTextAngleDegrees(0)
        rr.SetVisible(info.get(ref, {}).get('asm') == 'HAND')
        pads = [q.GetPosition() for q in fp.Pads()]
        cx = sum(pcbnew.ToMM(q.x) for q in pads) / len(pads); cy = sum(pcbnew.ToMM(q.y) for q in pads) / len(pads)
        if ref == 'J3':
            cy -= 2.2
        if ref in ('BT1', 'U15', 'J3'):
            rr.SetPosition(V(cx, cy))

    # ---- outline, planes, silk
    segs(board, OUTLINE)
    gnd, v5, v33 = netobj['GND'], netobj['+5V'], netobj['+3V3']
    zone(board, POUR, pcbnew.In1_Cu, gnd, 'GND_PLANE')
    zone(board, FIVE_V, pcbnew.In2_Cu, v5, '+5V_PLANE')
    zone(board, THREE_V3, pcbnew.In2_Cu, v33, '+3V3_PLANE')
    outer = [zone(board, POUR, pcbnew.F_Cu, gnd, 'GND_F'), zone(board, POUR, pcbnew.B_Cu, gnd, 'GND_B')]
    for s_, x, y, size in SILK:
        text(board, s_, x, y, size, pcbnew.B_SilkS)
    # USB-C GND pins are too narrow for thermal spokes -> solid connection
    for pad in fps['J5'].Pads():
        if pad.GetNetname() == 'GND':
            pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    # keep pours away from the USB-C locating pegs (NPTH)
    for pad in fps['J5'].Pads():
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            px, py = pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)
            k = pcbnew.ZONE(board)
            k.SetIsRuleArea(True); k.SetDoNotAllowCopperPour(True)
            k.SetDoNotAllowTracks(False); k.SetDoNotAllowVias(False); k.SetDoNotAllowPads(False); k.SetDoNotAllowFootprints(False)
            k.SetLayerSet(pcbnew.LSET.AllCuMask())
            ol = k.Outline(); ol.NewOutline()
            for dx, dy in ((-0.9, -0.9), (0.9, -0.9), (0.9, 0.9), (-0.9, 0.9)):
                ol.Append(MM(px + dx), MM(py + dy))
            board.Add(k)

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(pcb_path, board)
    add_stackup(pcb_path)

    # ---- freerouting input: inner planes only (outer GND pours would block every route; KiCad re-pours them)
    os.makedirs(os.path.join(proj_dir, 'freerouting'), exist_ok=True)
    for z in outer:
        board.Remove(z)
    pcbnew.ExportSpecctraDSN(board, os.path.join(proj_dir, 'freerouting', PROJ + '.dsn'))

    # ---- JLC assembly files (only asm == 'JLC')
    jdir = os.path.join(proj_dir, 'production', 'jlc'); os.makedirs(jdir, exist_ok=True)
    groups = {}
    for ref, fp in fps.items():
        p = info.get(ref, {})
        if p.get('asm') != 'JLC':
            continue
        key = (comps[ref]['value'], comps[ref]['fp'].split(':')[1], p.get('mpn', ''))
        groups.setdefault(key, []).append(ref)
    with open(os.path.join(jdir, 'WSNES_BOM_JLC.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Comment', 'Designator', 'Footprint', 'MPN', 'LCSC Part #'])
        for (val, fpn, mpn), refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
            w.writerow([val, ','.join(sorted(refs, key=lambda r: (re.sub(r'\d', '', r), int(re.sub(r'\D', '', r) or 0)))), fpn, mpn, ''])
    with open(os.path.join(jdir, 'WSNES_CPL_JLC.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        for ref, fp in sorted(fps.items()):
            if info.get(ref, {}).get('asm') != 'JLC':
                continue
            pos = fp.GetPosition()
            w.writerow([ref, '%.3fmm' % pcbnew.ToMM(pos.x), '%.3fmm' % -pcbnew.ToMM(pos.y),
                        'Top' if fp.GetLayer() == pcbnew.F_Cu else 'Bottom', '%.0f' % (fp.GetOrientationDegrees() % 360)])

    # ---- sanity: overlaps + outline (big parts), unplaced small parts
    probs = ['could not place ' + r for r in unplaced]
    boxes = dict()
    for ref, b in occupied:
        boxes.setdefault(ref, []).append(b)
    refs = [r for r in boxes if r not in ('ANT', 'TAB')]
    for i, a in enumerate(refs):
        for b in refs[i + 1:]:
            if any(overlap(x, y, 0) for x in boxes[a] for y in boxes[b]):
                probs.append('courtyard overlap %s / %s' % (a, b))
        if a not in EDGE_PARTS and not all(rect_in_board(bx, OUTLINE, 0) for bx in boxes[a]):
            probs.append('%s outside the outline' % a)
    for ref in EDGE_PARTS:
        for pad in fps[ref].Pads():
            p = pad.GetPosition()
            if not in_poly(pcbnew.ToMM(p.x), pcbnew.ToMM(p.y), OUTLINE):
                probs.append('%s pad %s outside the board' % (ref, pad.GetNumber()))
    for p in probs:
        print('PLACEMENT:', p)
    xs = [x for x, _ in OUTLINE]
    print('board %.1f x %.1f mm (+ %.1f mm tab), footprints: %d, nets: %d, placement problems: %d'
          % (max(xs) - min(xs), SY - Y_TOP, PY + G.TAB_BOT - SY, len(fps), len(netobj), len(probs)))


if __name__ == '__main__':
    main(os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..')))
