# Big-head cartoon character: the person's real 3D head (from the rigged photo model) on a clean, smooth cartoon body in their clothes' colours.
import bpy, sys, math, bmesh, mathutils
argv = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT, PREVIEW, WHO = argv[:4]
PAL = {
 'himanshu': dict(belt='#17171b', jacket='#3a3b45', shirt='#141416', trim='#e9e9ee', accent='#d8343a', trousers='#3f72ad', shoes='#9aa0aa', skin='#c08a6a', zip=True, patch=True),
 'aman':     dict(belt='#17181c', jacket='#4a4e5a', shirt='#23252b', trim='#8d929c', accent='#33363e', trousers='#4a4d57', shoes='#1d1e22', skin='#96644c', zip=True, patch=False),
 'charan':   dict(belt='#b9a7aa', jacket='#f0d9dc', shirt='#f7ecee', trim='#d9b9be', accent='#f0d9dc', trousers='#eeeeea', shoes='#c9ccd2', skin='#b8805f', zip=False, patch=False),
}[WHO]
BULK = {'himanshu': 1.0, 'aman': 1.28, 'charan': 1.08}[WHO]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
head = max((o for o in bpy.context.scene.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
bn = {b.name.replace('mixamorig:', '').replace('mixamorig', ''): b for b in arm.data.bones}
def J(n): return arm.matrix_world @ bn[n].head_local
def T(n): return arm.matrix_world @ bn[n].tail_local
print('bones', len(bn), 'head mesh verts', len(head.data.vertices), 'neck', [round(c, 3) for c in J('Neck')], 'L arm', [round(c, 3) for c in J('LeftArm')])
nz, hz = J('Neck').z, J('Head').z
# 1. the head: a clean smooth cartoon head, with the person's sharp photo face (and real hairline) on the front
import json, os
FACE = argv[4]; HM = json.load(open(os.path.join(FACE, WHO + '_head.json')))
for o in [o for o in bpy.context.scene.objects if o.type == 'MESH']: bpy.data.objects.remove(o, do_unlink=True)
HS = 2.0; Hh = 0.245 * HS; rz = Hh / 2; rx = min(rz * HM['aspect'], rz * 0.95); ry = rx * 0.98
hj = J('Head'); cx, cy, cz = 0.0, hj.y - 0.02, hj.z + 0.0 + rz
bmh = bmesh.new(); bmesh.ops.create_uvsphere(bmh, u_segments=40, v_segments=24, radius=1.0)
for v in bmh.verts:
    x, y, z = v.co; sq = 1.0 + 0.10 * max(0.0, -z)            # a slightly fuller jaw than a plain egg
    v.co = mathutils.Vector((cx + x * rx * sq, cy + y * ry, cz + z * rz))
uvl = bmh.loops.layers.uv.new('UVMap')
for f in bmh.faces:
    f.smooth = True; f.material_index = 0 if f.normal.y < 0.1 else 1
    for l in f.loops: l[uvl].uv = ((l.vert.co.x - cx) / (2 * rx * 1.1) + 0.5, (l.vert.co.z - cz) / (2 * rz) + 0.5)
hme = bpy.data.meshes.new('PhotoHead'); bmh.to_mesh(hme); bmh.free()
head = bpy.data.objects.new('PhotoHead', hme); bpy.context.scene.collection.objects.link(head)
mf = bpy.data.materials.new('face'); mf.use_nodes = True; bs = next(n for n in mf.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
ti = mf.node_tree.nodes.new('ShaderNodeTexImage'); ti.image = bpy.data.images.load(os.path.join(FACE, WHO + '_headtex.png')); ti.extension = 'EXTEND'
mf.node_tree.links.new(ti.outputs['Color'], bs.inputs['Base Color']); bs.inputs['Roughness'].default_value = 0.9; bs.inputs['Metallic'].default_value = 0.0
def rgb255(c): return tuple((v / 255.0) ** 2.2 for v in c) + (1.0,)
mh = bpy.data.materials.new('toon_hair'); mh.use_nodes = True; bh = next(n for n in mh.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'); bh.inputs['Base Color'].default_value = rgb255(HM['hair']); bh.inputs['Roughness'].default_value = 0.9; mh.diffuse_color = rgb255(HM['hair'])
hme.materials.append(mf); hme.materials.append(mh)
vg = head.vertex_groups.new(name=bn['Head'].name); vg.add(list(range(len(hme.vertices))), 1.0, 'REPLACE')
head.parent = arm; head.matrix_parent_inverse = arm.matrix_world.inverted(); mdh = head.modifiers.new('arm', 'ARMATURE'); mdh.object = arm
PAL['skin'] = '#%02x%02x%02x' % tuple(HM['skin'])
def onhead(uv):                                               # a photo point -> the same point on the head, in the game's axes
    x = cx + (uv[0] - 0.5) * 2 * rx * 1.1; z = cz + (0.5 - uv[1]) * 2 * rz
    y = cy - ry * max(0.0, 1 - ((x - cx) / rx) ** 2 - ((z - cz) / rz) ** 2) ** 0.5 - 0.006
    return [round(x, 4), round(z, 4), round(-y, 4)]
json.dump(dict(toon=True, photo=True, eyeA=onhead(HM['eyeA']), eyeB=onhead(HM['eyeB']), mouth=onhead(HM['mouth'])), open(OUT.replace('.glb', '_meta.json'), 'w'))
nz, hz = J('Neck').z, J('Head').z
print('photo head: radius x/y/z', round(rx, 3), round(ry, 3), round(rz, 3), 'centre z', round(cz, 3))
# 2. the cartoon body, built like a toy figure: separate smooth rounded parts, each locked to one bone (nothing can smear)
V = mathutils.Vector; k = BULK
MATS = ['jacket', 'shirt', 'trim', 'accent', 'trousers', 'shoes', 'skin', 'belt']
bm = bmesh.new(); lb = bm.verts.layers.int.new('bone'); BONES = []
def bidx(n):
    if n not in BONES: BONES.append(n)
    return BONES.index(n)
def tag(geom, bone, mat):
    for e in geom:
        if isinstance(e, bmesh.types.BMVert): e[lb] = bidx(bone)
    for f in {f for e in geom if isinstance(e, bmesh.types.BMVert) for f in e.link_faces}: f.material_index = MATS.index(mat); f.smooth = True
def ball(c, r, bone, mat, sc=(1, 1, 1)):
    g = bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=1.0)['verts']
    for v in g: v.co = V((v.co.x * r * sc[0], v.co.y * r * sc[1], v.co.z * r * sc[2])) + V(c)
    tag(g, bone, mat); return g
def limb(p0, p1, r0, r1, bone, mat, flat=1.0):
    p0, p1 = V(p0), V(p1); d = p1 - p0; L = d.length; q = V((0, 0, 1)).rotation_difference(d.normalized())
    g = bmesh.ops.create_cone(bm, cap_ends=False, segments=24, radius1=r0, radius2=r1, depth=L)['verts']
    for v in g: w = q @ v.co; v.co = V((w.x, w.y * flat, w.z)) + (p0 + p1) / 2
    tag(g, bone, mat); ball(p0, r0, bone, mat, (1, flat, 1)); ball(p1, r1, bone, mat, (1, flat, 1))
def box(c, sx, sy, sz, bone, mat):
    g = bmesh.ops.create_cube(bm, size=1.0)['verts']
    for v in g: v.co = V((v.co.x * sx, v.co.y * sy, v.co.z * sz)) + V(c)
    tag(g, bone, mat)
    for f in {f for v in g for f in v.link_faces}: f.smooth = False
H, S1, S2, NK, HD = J('Hips'), J('Spine1'), J('Spine2'), J('Neck'), J('Head')
FL = 0.74                                                    # the torso is flatter front to back than it is wide
ball(H + V((0, 0, -0.01)), 0.185 * k, 'Hips', 'trousers', (1, FL, 0.8)); ball(H + V((0, 0, 0.045)), 0.186 * k, 'Hips', 'belt', (1, FL, 0.2))
limb(H + V((0, 0, 0.03)), S1, 0.18 * k, 0.19 * k, 'Spine', 'jacket', FL)
chest_top = V((0, S2.y, NK.z - 0.085))
limb(S1 + V((0, 0, 0.01)), chest_top, 0.192 * k, 0.21 * k, 'Spine2', 'jacket', FL); ball(V((0, S2.y, NK.z - 0.035)), 0.088, 'Spine2', 'trim', (1, 1, 0.42))
limb(NK + V((0, 0, -0.04)), HD + V((0, 0, 0.06)), 0.058, 0.055, 'Neck', 'skin')
# front details sit just proud of the chest
for (za, zb, bone, r) in ((H.z + 0.06, S1.z, 'Spine', 0.185 * k), (S1.z + 0.01, chest_top.z + 0.02, 'Spine2', 0.2 * k)):
    yf = S1.y - r * FL - 0.004; zc = (za + zb) / 2; hgt = zb - za + 0.02
    box((0, yf, zc), 0.085, 0.03, hgt, bone, 'shirt')
    if PAL['zip']:
        for sx in (-1, 1): box((sx * 0.055, yf - 0.002, zc), 0.016, 0.03, hgt, bone, 'trim')
if WHO != 'charan': limb(V((-0.1 * k, H.y, H.z + 0.035)), V((0.1 * k, H.y, H.z + 0.035)), 0.118 * k, 0.118 * k, 'Spine', 'trim', 1.0) if False else None
for sd, sx in (('Left', 1), ('Right', -1)):
    A, F, W = J(sd + 'Arm'), J(sd + 'ForeArm'), J(sd + 'Hand')
    ball(A, 0.108 * (0.85 + 0.15 * k), sd + 'Arm', 'accent' if PAL['patch'] else 'jacket')
    limb(A, F, 0.09 * (0.85 + 0.15 * k), 0.08, sd + 'Arm', 'jacket'); limb(F, W, 0.08, 0.068, sd + 'ForeArm', 'jacket')
    ball(W, 0.072, sd + 'ForeArm', 'trim'); ball(W + (W - F).normalized() * 0.06, 0.06, sd + 'Hand', 'skin')
    U, K, AN, TB = J(sd + 'UpLeg'), J(sd + 'Leg'), J(sd + 'Foot'), J(sd + 'ToeBase')
    limb(U + V((0, 0, -0.01)), K, 0.112 * (0.8 + 0.2 * k), 0.094, sd + 'UpLeg', 'trousers'); limb(K, AN + V((0, 0, 0.04)), 0.092, 0.08, sd + 'Leg', 'trousers')
    ball(V((AN.x, (AN.y + TB.y) / 2 - 0.035, 0.066)), 1.0, sd + 'Foot', 'shoes', (0.088, 0.175, 0.066))
me = bpy.data.meshes.new('toon'); bm.to_mesh(me)
bones_of = [v[lb] for v in bm.verts]; bm.free()
body = bpy.data.objects.new('ToonBody', me); bpy.context.scene.collection.objects.link(body)
def hexrgb(h): return tuple(((int(h[i:i + 2], 16) / 255.0) ** 2.2) for i in (1, 3, 5)) + (1.0,)
for name in MATS:
    m = bpy.data.materials.new('toon_' + name); m.use_nodes = True; b_ = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b_.inputs['Base Color'].default_value = hexrgb(PAL[name]); b_.inputs['Roughness'].default_value = 0.9; b_.inputs['Metallic'].default_value = 0.0
    m.diffuse_color = hexrgb(PAL[name]); me.materials.append(m)
for i, bname in enumerate(BONES):
    vg = body.vertex_groups.new(name=bn[bname].name); vg.add([vi for vi, bi in enumerate(bones_of) if bi == i], 1.0, 'REPLACE')
body.parent = arm; body.matrix_parent_inverse = arm.matrix_world.inverted(); md = body.modifiers.new('arm', 'ARMATURE'); md.object = arm; bpy.context.view_layer.update()
print('toon body verts', len(me.vertices), 'parts on bones', len(BONES), 'verts without weights', sum(1 for v in me.vertices if not v.groups))
# 5. export
bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); head.select_set(True); arm.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_animations=False, export_skins=True, export_yup=True, export_image_format='JPEG', export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
print('exported', OUT)
# 6. preview with the big head
scn = bpy.context.scene; scn.render.engine = 'BLENDER_WORKBENCH'; scn.display.shading.light = 'STUDIO'; scn.display.shading.color_type = 'TEXTURE'; scn.display.shading.show_object_outline = True
scn.render.resolution_x, scn.render.resolution_y = 600, 760
scn.world = bpy.data.worlds.new('w')
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scn.collection.objects.link(cam); scn.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.3
for i, ang in enumerate((0, 35)):
    a = math.radians(ang); cam.location = (4 * math.sin(a), -4 * math.cos(a), 1.05); cam.rotation_euler = (math.radians(90), 0, a)
    scn.render.filepath = PREVIEW.replace('.png', f'_{i}.png'); bpy.ops.render.render(write_still=True)
print('previews written')
