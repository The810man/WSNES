"""Minimal KiCad S-expression parser/writer + symbol library helpers."""
import re

class Q(str):
    """Quoted string atom."""
    pass

_tok = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)

def parse(text):
    stack = [[]]
    pos = 0
    n = len(text)
    while pos < n:
        m = _tok.match(text, pos)
        if not m:
            if text[pos:].strip() == '':
                break
            raise ValueError('parse error at %d: %r' % (pos, text[pos:pos+40]))
        pos = m.end()
        if m.group(1):
            stack.append([])
        elif m.group(2):
            node = stack.pop()
            stack[-1].append(node)
        elif m.group(3) is not None:
            stack[-1].append(Q(m.group(3).replace('\\"', '"').replace('\\\\', '\\')))
        else:
            stack[-1].append(m.group(4))
    return stack[0][0] if len(stack[0]) == 1 else stack[0]

def _atom(a):
    if isinstance(a, Q):
        return '"' + a.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'
    if isinstance(a, float):
        s = ('%.4f' % a).rstrip('0').rstrip('.')
        return '0' if s in ('-0', '') else s
    return str(a)

def dump(node, ind=0):
    if not isinstance(node, list):
        return _atom(node)
    simple = all(not isinstance(c, list) for c in node)
    if simple or (len(node) <= 4 and all(not isinstance(c, list) or all(not isinstance(cc, list) for cc in c) for c in node) and len(str(node)) < 90):
        return '(' + ' '.join(dump(c, 0) for c in node) + ')'
    out = '(' + ' '.join(_atom(c) for c in node if not isinstance(c, list))
    for c in node:
        if isinstance(c, list):
            out += '\n' + '\t' * (ind + 1) + dump(c, ind + 1)
    return out + '\n' + '\t' * ind + ')'

def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]

def find1(node, key):
    r = find(node, key)
    return r[0] if r else None

_libcache = {}
def load_lib(path):
    if path not in _libcache:
        root = parse(open(path, encoding='utf-8').read())
        _libcache[path] = {str(c[1]): c for c in find(root, 'symbol')}
    return _libcache[path]

def flatten(path, name):
    """Return a flattened copy of library symbol `name` (resolving extends)."""
    import copy
    lib = load_lib(path)
    node = copy.deepcopy(lib[name])
    ext = find1(node, 'extends')
    if not ext:
        return node
    parent = flatten(path, str(ext[1]))
    pname = str(parent[1])
    out = ['symbol', Q(name)]
    child_props = {str(p[1]): p for p in find(node, 'property')}
    for c in parent[2:]:
        if not isinstance(c, list):
            continue
        if c[0] == 'property':
            k = str(c[1])
            out.append(child_props.pop(k) if k in child_props else c)
        elif c[0] == 'symbol':
            u = copy.deepcopy(c)
            u[1] = Q(str(u[1]).replace(pname + '_', name + '_', 1))
            out.append(u)
        else:
            out.append(c)
    # extra child props not in parent
    idx = max(i for i, c in enumerate(out) if isinstance(c, list) and c[0] == 'property') + 1
    for p in child_props.values():
        out.insert(idx, p); idx += 1
    return out

def pins_of(sym):
    """Yield dicts: unit, style, number, name, type, x, y, angle, length, hidden."""
    nm = str(sym[1])
    res = []
    for u in find(sym, 'symbol'):
        m = re.match(r'.*_(\d+)_(\d+)$', str(u[1]))
        unit, style = int(m.group(1)), int(m.group(2))
        for p in find(u, 'pin'):
            at = find1(p, 'at'); ln = find1(p, 'length')
            hidden = 'hide' in p or any(isinstance(c, list) and c[0] == 'hide' and c[1] == 'yes' for c in p)
            res.append(dict(unit=unit, style=style, type=str(p[1]), number=str(find1(p, 'number')[1]),
                            name=str(find1(p, 'name')[1]), x=float(at[1]), y=float(at[2]),
                            angle=float(at[3]) if len(at) > 3 else 0.0, length=float(ln[1]), hidden=hidden))
    return res
