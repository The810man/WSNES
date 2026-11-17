#!/usr/bin/env python3
"""Measure zone-fill copper inside the SNES contact tab (gold-finger area).

Usage: python3 analysis/helpers/tab_copper.py pcb/WSNES_Proto.kicad_pcb

Reads the filled zone polygons stored in the board (refill zones first) and
reports, per copper layer:
  * copper area inside the tab (x 120..180, y 153.5..164.6)
  * whether pour copper sits in the gaps between adjacent fingers (y = 160)
  * whether pour copper reaches the bevelled tip strip (y = 164.0)
Tab geometry comes from P1's Edge.Cuts lines (tab bottom edge y = 164.6).
"""
import re
import sys

TAB = (120.0, 153.5, 180.0, 164.6)
FINGER_PITCH = 2.5
FINGER_CENTRE_X = 150.0


def tokenize(text):
    return re.findall(r'"(?:[^"\\]|\\.)*"|\(|\)|[^\s()]+', text)


def parse(tokens):
    stack, cur = [], []
    for t in tokens:
        if t == "(":
            stack.append(cur)
            cur = []
        elif t == ")":
            done, cur = cur, stack.pop()
            cur.append(done)
        else:
            cur.append(t.strip('"'))
    return cur[0]


def walk(node, key):
    if isinstance(node, list):
        if node and node[0] == key:
            yield node
        for child in node:
            yield from walk(child, key)


def first(node, key):
    return next((c for c in node if isinstance(c, list) and c and c[0] == key), None)


def clip(poly, x0, y0, x1, y1):
    def edge(poly, inside, cross):
        out = []
        for i in range(len(poly)):
            a, b = poly[i - 1], poly[i]
            if inside(b):
                if not inside(a):
                    out.append(cross(a, b))
                out.append(b)
            elif inside(a):
                out.append(cross(a, b))
        return out

    def at_x(x):
        return lambda a, b: (x, a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]))

    def at_y(y):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]), y)

    for inside, cross in ((lambda p: p[0] >= x0, at_x(x0)), (lambda p: p[0] <= x1, at_x(x1)),
                          (lambda p: p[1] >= y0, at_y(y0)), (lambda p: p[1] <= y1, at_y(y1))):
        if not poly:
            break
        poly = edge(poly, inside, cross)
    return poly


def area(p):
    return abs(sum(p[i - 1][0] * p[i][1] - p[i][0] * p[i - 1][1] for i in range(len(p)))) / 2 if len(p) > 2 else 0.0


def contains(pt, poly):
    x, y = pt
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def main(path):
    board = parse(tokenize(open(path, encoding="utf-8").read()))
    layers = {}
    for zone in walk(board, "zone"):
        for fp in walk(zone, "filled_polygon"):
            layer = first(fp, "layer")[1]
            pts = [(float(p[1]), float(p[2])) for p in first(fp, "pts")[1:] if p[0] == "xy"]
            layers.setdefault(layer, []).append(pts)
    gaps = [FINGER_CENTRE_X + FINGER_PITCH / 2 + FINGER_PITCH * k for k in range(-12, 11)]
    for layer in ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu"):
        polys = layers.get(layer, [])
        tab = sum(area(clip(p, *TAB)) for p in polys)
        tip = sum(area(clip(p, TAB[0], TAB[3] - 1.0, TAB[2], TAB[3])) for p in polys)
        between = sum(any(contains((g, 160.0), p) for p in polys) for g in gaps)
        at_tip = sum(any(contains((g, 164.0), p) for p in polys) for g in gaps)
        print(f"{layer:7} tab copper {tab:6.1f} mm2 | within 1 mm of tip {tip:5.1f} mm2 | "
              f"pour between fingers {between}/{len(gaps)} gaps | pour at y=164.0 {at_tip}/{len(gaps)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "pcb/WSNES_Proto.kicad_pcb")
