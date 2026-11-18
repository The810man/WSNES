#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 The810man
"""Compare a KiCad netlist export against tools/intended_pins.json (written by gen_project.py)."""
import json, re, sys, collections
net_file, intended_file = sys.argv[1], sys.argv[2]
s = open(net_file).read()
actual = {}
nets = collections.defaultdict(set)
# whitespace-tolerant: KiCad 9 writes each node on one line, KiCad 10 pretty-prints them
for m in re.finditer(r'\(net\s+\(code\s+"\d+"\)\s+\(name\s+"([^"]*)"\)(.*?)(?=\(net\s+\(code|\Z)', s, re.S):
    # hierarchical schematic: sheet-local nets are "/<Sheet>/<NET>", global ones "<NET>"; compare the bare name
    # (gen_project.py only makes a net local when all its pins are on one sheet, so bare names stay unique)
    name = m.group(1).rsplit('/', 1)[-1]
    for ref, pin in re.findall(r'\(node\s+\(ref\s+"([^"]+)"\)\s+\(pin\s+"([^"]+)"\)', m.group(2)):
        actual[(ref, pin)] = name
        nets[name].add((ref, pin))
errors = 0
intended = json.load(open(intended_file))
want_nets = collections.defaultdict(set)
for ref, pin, pname, net in intended:
    a = actual.get((ref, pin))
    if net is None:
        if a is not None and not a.startswith('unconnected-'):
            print('NC pin connected: %s.%s (%s) -> %s' % (ref, pin, pname, a)); errors += 1
        continue
    want_nets[net].add((ref, pin))
    if a != net:
        print('MISMATCH %s.%s (%s): want %s got %s' % (ref, pin, pname, net, a)); errors += 1
# single-node nets = dangling label (typo) -> report
for n, nodes in want_nets.items():
    if len(nodes) < 2:
        print('SINGLE-NODE NET %s: %s' % (n, sorted(nodes))); errors += 1
print('pins checked: %d, nets: %d, errors: %d' % (len(intended), len(want_nets), errors))
sys.exit(1 if errors else 0)
