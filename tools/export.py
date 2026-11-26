import conv, numpy as np, json
B = conv.bake; O = conv.OUT.index
def cut(c, a=None, b=None):
    a = 0 if a is None else int(round(a * c['fps'])); b = c['n'] if b is None else int(round(b * c['fps'])) + 1
    return dict(fps=c['fps'], n=b - a, q=c['q'][a:b], h=c['h'][a:b], p=c['p'][a:b])
def hold(c, t): k = min(c['n'] - 1, int(round(t * c['fps']))); return dict(fps=c['fps'], n=2, q=c['q'][[k, k]], h=c['h'][[k, k]], p=c['p'][[k, k]])
def cat(a, b):
    q = b['q'].copy()
    for i in range(q.shape[1]):
        if np.dot(q[0, i], a['q'][-1, i]) < 0: q[:, i] = -q[:, i]
    return dict(fps=a['fps'], n=a['n'] + b['n'], q=np.concatenate([a['q'], q]), h=np.concatenate([a['h'], b['h']]), p=np.concatenate([a['p'], b['p']]))
def strike(c, hand): z = c['p'][:, O(hand), 2] - c['p'][:, O('Hips'), 2]; return float(np.argmax(z)) / c['fps']
enter = B(1, 'Punch_Enter'); C = {}
C['stance'] = hold(enter, 9); C['enter'] = enter
C['jab'] = B(1, 'Punch_Jab'); C['jab']['strike'] = strike(C['jab'], 'LeftHand')
C['cross'] = B(1, 'Punch_Cross'); C['cross']['strike'] = strike(C['cross'], 'RightHand')
C['hook'] = cat(B(2, 'Melee_Hook'), B(2, 'Melee_Hook_Rec')); C['hook']['strike'] = strike(C['hook'], 'RightHand')
C['hitc'] = B(1, 'Hit_Chest'); C['hith'] = B(1, 'Hit_Head')
C['kd'] = B(2, 'Hit_Knockback'); C['getup'] = B(2, 'LayToIdle')
C['crouch'] = B(1, 'Crouch_Idle_Loop'); C['crouch']['loop'] = True
C['walk'] = B(1, 'Walk_Loop'); C['walk']['loop'] = True
C['jump'] = B(1, 'Jump_Loop'); C['jump']['loop'] = True
C['castin'] = B(1, 'Spell_Simple_Enter'); C['cast'] = B(1, 'Spell_Simple_Idle_Loop'); C['cast']['loop'] = True
C['slam'] = B(1, 'Sword_Attack'); C['dance'] = B(1, 'Dance_Loop'); C['dance']['loop'] = True
C['fold'] = B(2, 'Idle_FoldArms_Loop'); C['fold']['loop'] = True
C['block'] = hold(B(2, 'Sword_Block'), 0.45); C['slide'] = B(2, 'Slide_Start'); C['idle'] = B(1, 'Idle_Loop'); C['idle']['loop'] = True
for k, c in C.items():
    if 'strike' in c: print(k, 'strike %.2f of %.2f' % (c['strike'], (c['n'] - 1) / c['fps']))
    print(k, c['n'], 'hips y %.2f..%.2f z %.2f..%.2f' % (c['h'][:, 1].min(), c['h'][:, 1].max(), c['h'][:, 2].min(), c['h'][:, 2].max()))
conv.sheet({k: C[k] for k in ['stance', 'hook', 'block', 'kd', 'getup']}, 'sheet3.png')
out = {k: {**{x: y for x, y in c.items() if x not in 'qhp'}, 'q': np.round(c['q'], 4).reshape(-1).tolist(), 'h': np.round(c['h'], 3).reshape(-1).tolist()} for k, c in C.items()}
js = 'window.ANIM = ' + json.dumps({'bones': conv.OUT, 'clips': out}, separators=(',', ':')) + ';\n'
open('../anim.js', 'w').write(js); print('anim.js %d KB' % (len(js) // 1024))
