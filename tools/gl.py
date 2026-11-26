import json, struct, numpy as np
CT = {5126: ('f4', 4), 5123: ('u2', 2), 5121: ('u1', 1), 5125: ('u4', 4), 5122: ('i2', 2), 5120: ('i1', 1)}
NC = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16, 'VEC2': 2}
def qmat(q):
    x, y, z, w = q; return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)], [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)], [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
def matq(m):
    t = np.trace(m)
    if t > 0: s = np.sqrt(t + 1) * 2; q = [(m[2,1]-m[1,2])/s, (m[0,2]-m[2,0])/s, (m[1,0]-m[0,1])/s, s/4]
    elif m[0,0] > m[1,1] and m[0,0] > m[2,2]: s = np.sqrt(1+m[0,0]-m[1,1]-m[2,2])*2; q = [s/4, (m[0,1]+m[1,0])/s, (m[0,2]+m[2,0])/s, (m[2,1]-m[1,2])/s]
    elif m[1,1] > m[2,2]: s = np.sqrt(1+m[1,1]-m[0,0]-m[2,2])*2; q = [(m[0,1]+m[1,0])/s, s/4, (m[1,2]+m[2,1])/s, (m[0,2]-m[2,0])/s]
    else: s = np.sqrt(1+m[2,2]-m[0,0]-m[1,1])*2; q = [(m[0,2]+m[2,0])/s, (m[1,2]+m[2,1])/s, s/4, (m[1,0]-m[0,1])/s]
    q = np.array(q); return q / np.linalg.norm(q)
def slerp(a, b, w):
    d = float(np.dot(a, b))
    if d < 0: b = -b; d = -d
    if d > 0.9995: q = a + (b - a) * w
    else: th = np.arccos(d); q = (np.sin((1-w)*th) * a + np.sin(w*th) * b) / np.sin(th)
    return q / np.linalg.norm(q)
class G:
    def __init__(s, path):
        b = open(path, 'rb').read(); n = struct.unpack('<I', b[12:16])[0]; s.j = json.loads(b[20:20+n]); s.bin = b[20+n+8:]
        s.nodes = s.j['nodes']; s.name = {nd.get('name'): i for i, nd in enumerate(s.nodes)}; s.parent = {}
        for i, nd in enumerate(s.nodes):
            for c in nd.get('children', []): s.parent[c] = i
        s.anims = {a.get('name'): a for a in s.j.get('animations', [])}; s._cache = {}
    def acc(s, i):
        if i in s._cache: return s._cache[i]
        a = s.j['accessors'][i]; bv = s.j['bufferViews'][a['bufferView']]; dt, sz = CT[a['componentType']]; nc = NC[a['type']]
        off = bv.get('byteOffset', 0) + a.get('byteOffset', 0); st = bv.get('byteStride', 0)
        assert not st or st == sz * nc, 'stride'
        arr = np.frombuffer(s.bin, dtype='<' + dt, count=a['count'] * nc, offset=off).reshape(a['count'], nc).astype(np.float64)
        if a.get('normalized'): arr = arr / {'i2': 32767., 'u2': 65535., 'i1': 127., 'u1': 255.}[dt]
        s._cache[i] = arr; return arr
    def rest(s):
        T = {}
        for i, nd in enumerate(s.nodes):
            if 'matrix' in nd:
                m = np.array(nd['matrix']).reshape(4, 4).T; t = m[:3, 3]; sc = np.linalg.norm(m[:3, :3], axis=0); q = matq(m[:3, :3] / sc)
            else: t = np.array(nd.get('translation', [0, 0, 0.])); q = np.array(nd.get('rotation', [0, 0, 0, 1.])); sc = np.array(nd.get('scale', [1, 1, 1.]))
            T[i] = [np.array(t, float), np.array(q, float), np.array(sc, float)]
        return T
    def dur(s, name): return max(s.acc(sm['input']).max() for sm in s.anims[name]['samplers'])
    def sample(s, name, t):
        T = s.rest()
        if name is None: return T
        a = s.anims[name]
        for ch in a['channels']:
            sm = a['samplers'][ch['sampler']]; node = ch['target'].get('node'); path = ch['target']['path']
            if node is None or path == 'weights': continue
            ti = s.acc(sm['input'])[:, 0]; out = s.acc(sm['output']); interp = sm.get('interpolation', 'LINEAR')
            if interp == 'CUBICSPLINE': out = out.reshape(len(ti), 3, -1)[:, 1]
            k = int(np.clip(np.searchsorted(ti, t, 'right') - 1, 0, len(ti) - 1)); k2 = min(k + 1, len(ti) - 1)
            w = 0 if (k2 == k or interp == 'STEP') else float(np.clip((t - ti[k]) / (ti[k2] - ti[k]), 0, 1))
            idx = {'translation': 0, 'rotation': 1, 'scale': 2}[path]
            T[node][idx] = slerp(out[k], out[k2], w) if path == 'rotation' else out[k] * (1 - w) + out[k2] * w
        return T
    def world(s, T):
        W = {}
        def go(i):
            if i in W: return W[i]
            t, q, sc = T[i]; m = np.eye(4); m[:3, :3] = qmat(q) * sc; m[:3, 3] = t
            if i in s.parent: m = go(s.parent[i]) @ m
            W[i] = m; return m
        for i in range(len(s.nodes)): go(i)
        return W
def rot(m): r = m[:3, :3] / np.linalg.norm(m[:3, :3], axis=0); return r
