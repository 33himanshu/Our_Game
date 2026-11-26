import gl, numpy as np, json, sys
from PIL import Image, ImageDraw
OUT = ['Hips','Spine','Spine1','Spine2','Neck','Head','LeftShoulder','LeftArm','LeftForeArm','LeftHand','RightShoulder','RightArm','RightForeArm','RightHand','LeftUpLeg','LeftLeg','LeftFoot','LeftToeBase','RightUpLeg','RightLeg','RightFoot','RightToeBase']
M1 = ['DEF-hips','DEF-spine.001','DEF-spine.002','DEF-spine.003','DEF-neck','DEF-head','DEF-shoulder.L','DEF-upper_arm.L','DEF-forearm.L','DEF-hand.L','DEF-shoulder.R','DEF-upper_arm.R','DEF-forearm.R','DEF-hand.R','DEF-thigh.L','DEF-shin.L','DEF-foot.L','DEF-toe.L','DEF-thigh.R','DEF-shin.R','DEF-foot.R','DEF-toe.R']
M2 = ['pelvis','spine_01','spine_02','spine_03','neck_01','Head','clavicle_l','upperarm_l','lowerarm_l','hand_l','clavicle_r','upperarm_r','lowerarm_r','hand_r','thigh_l','calf_l','foot_l','ball_l','thigh_r','calf_r','foot_r','ball_r']
P1 = 'dl/ual1/Animation Library[Standard]/Godot/AnimationLibrary_Godot_Standard.glb'
P2 = 'dl/ual2/Universal Animation Library 2 [Standard]/Unreal-Godot/UAL2_Standard.glb'
SRC = {1: (gl.G(P1), M1), 2: (gl.G(P2), M2)}
LEG = (1.04 - 0.084) / (0.917 - 0.104)          # our skeleton's hip-to-ankle height over the pack's
def bake(pack, name, fps=30):
    U, M = SRC[pack]; idx = [U.name[n] for n in M]; root = U.name['root']
    W0 = U.world(U.sample('A_TPose', 0)); R0 = [gl.rot(W0[i]) for i in idx]; h0 = W0[idx[0]][:3, 3] - W0[root][:3, 3]
    d = float(U.dur(name)); n = max(2, int(round(d * fps)) + 1); Q = []; H = []; P = []
    for k in range(n):
        W = U.world(U.sample(name, d * k / (n - 1))); rw = W[root]
        Rr = gl.rot(W0[root]) @ gl.rot(rw).T   # take the root bone's own motion out, keep world axes
        Q.append([gl.matq(Rr @ gl.rot(W[i]) @ R0[j].T) for j, i in enumerate(idx)])
        H.append((Rr @ (W[idx[0]][:3, 3] - rw[:3, 3]) - h0) * LEG)
        P.append([Rr @ (W[i][:3, 3] - rw[:3, 3]) for i in idx])
    Q = np.array(Q)
    for b in range(Q.shape[1]):                 # keep each bone's quaternions on one side, so blending never takes the long way
        for k in range(1, n):
            if np.dot(Q[k, b], Q[k - 1, b]) < 0: Q[k, b] = -Q[k, b]
    return dict(fps=fps, n=n, q=Q, h=np.array(H), p=np.array(P))
def sheet(clips, path, cols=7):
    im = Image.new('RGB', (cols * 150 + 150, len(clips) * 190), 'white'); d = ImageDraw.Draw(im); B = OUT.index
    seg = [('Hips','Spine2'),('Spine2','Neck'),('Neck','Head'),('Spine2','LeftArm'),('LeftArm','LeftForeArm'),('LeftForeArm','LeftHand'),('Spine2','RightArm'),('RightArm','RightForeArm'),('RightForeArm','RightHand'),('Hips','LeftUpLeg'),('LeftUpLeg','LeftLeg'),('LeftLeg','LeftFoot'),('LeftFoot','LeftToeBase'),('Hips','RightUpLeg'),('RightUpLeg','RightLeg'),('RightLeg','RightFoot'),('RightFoot','RightToeBase')]
    for r, (nm, c) in enumerate(clips.items()):
        d.text((4, r * 190 + 90), '%s  %.2fs' % (nm, (c['n'] - 1) / c['fps']), fill='black')
        for ci, fi in enumerate(np.linspace(0, c['n'] - 1, cols).astype(int)):
            P = c['p'][fi]; ox, oy = 150 + ci * 150 + 60, r * 190 + 180
            d.line([ox - 60, oy, ox + 80, oy], fill=(200, 200, 200))
            for a, b in seg:
                col = (220, 40, 40) if 'Left' in a + b else (40, 60, 200) if 'Right' in a + b else (0, 0, 0)
                d.line([ox + P[B(a)][2] * 85, oy - P[B(a)][1] * 85, ox + P[B(b)][2] * 85, oy - P[B(b)][1] * 85], fill=col, width=3)
            hx, hy = ox + P[B('Head')][2] * 85, oy - P[B('Head')][1] * 85; d.ellipse([hx - 8, hy - 18, hx + 8, hy - 2], outline='black', width=2)
    im.save(path)
if __name__ == '__main__':
    A = {n: bake(1, n) for n in ['Punch_Enter','Punch_Jab','Punch_Cross','Hit_Chest','Hit_Head','Death01','Crouch_Idle_Loop','Walk_Loop','Jog_Fwd_Loop','Jump_Loop','Idle_Loop','Spell_Simple_Enter','Spell_Simple_Idle_Loop','Spell_Simple_Shoot','Dance_Loop','Sword_Attack','Roll']}
    sheet(A, 'sheet1.png')
    Bc = {n: bake(2, n) for n in ['Hit_Knockback','LayToIdle','Melee_Hook','Melee_Hook_Rec','Idle_Shield_Loop','Sword_Block','Slide_Start','Slide_Loop','OverhandThrow','Yes','Idle_FoldArms_Loop','Idle_No_Loop','Shield_OneShot','Idle_Shield_Break','NinjaJump_Start','Zombie_Scratch']}
    sheet(Bc, 'sheet2.png'); print('ok')
