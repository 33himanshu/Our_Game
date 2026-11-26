import bpy, sys, math, mathutils, bmesh
argv = sys.argv[sys.argv.index('--') + 1:]
XBOT, SHAPE, IMG, OUT, PREVIEW, HAIR = argv[:6]
DECIMATE = float(argv[6]) if len(argv) > 6 else 0.2
SOFT = argv[7] if len(argv) > 7 else None
NOHEAD = len(argv) > 8 and argv[8] == 'nohead'
WRAP = len(argv) > 9 and argv[9] == 'wrap'
XFER = len(argv) > 10 and argv[10] == 'xfer'
bpy.ops.wm.read_factory_settings(use_empty=True)
# 1. the game's skeleton: import the stand-in, keep only its armature
bpy.ops.import_scene.gltf(filepath=XBOT)
arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
SRC = None
for o in list(bpy.context.scene.objects):
    if o.type == 'MESH':
        if XFER and SRC is None and len(o.data.vertices) > 5000 and 'Joint' not in o.name and 'Joint' not in o.data.name:
            SRC = o; continue
        bpy.data.objects.remove(o, do_unlink=True)
if XFER and SRC is None:   # fall back: the biggest mesh
    pass
arm.animation_data_clear()
for pb in arm.pose.bones: pb.matrix_basis.identity()
for a in list(bpy.data.actions): bpy.data.actions.remove(a)
bpy.context.view_layer.update()
def bone_head(n): return arm.matrix_world @ arm.data.bones['mixamorig:' + n].head_local
def bone_tail(n): return arm.matrix_world @ arm.data.bones['mixamorig:' + n].tail_local
top = (arm.matrix_world @ arm.data.bones['mixamorig:HeadTop_End'].head_local).z
print('xbot top', round(top, 3), 'L shoulder', [round(c, 3) for c in bone_head('LeftArm')], 'L hand', [round(c, 3) for c in bone_head('LeftHand')])
# 2. the generated body
before = set(bpy.context.scene.objects)
bpy.ops.import_scene.gltf(filepath=SHAPE)
body = [o for o in bpy.context.scene.objects if o not in before and o.type == 'MESH'][0]
for o in [o for o in bpy.context.scene.objects if o not in before and o != body]:
    bpy.data.objects.remove(o, do_unlink=True)
body.parent = None
body.matrix_world = mathutils.Matrix.Rotation(math.pi, 4, 'Z') @ body.matrix_world   # this model faces the other way
bpy.context.view_layer.objects.active = body; body.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bm = bmesh.new(); bm.from_mesh(body.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(body.data); bm.free(); body.data.update()
vs = [v.co for v in body.data.vertices]
zmin = min(v.z for v in vs); zmax = max(v.z for v in vs)
xmin = min(v.x for v in vs); xmax = max(v.x for v in vs)
ymid = (min(v.y for v in vs) + max(v.y for v in vs)) / 2
# scale so the body is as tall as the skeleton (feet on the floor, centred)
s = (top + 0.08) / (zmax - zmin)
_low = [v.co.x for v in body.data.vertices if (v.co.z - zmin) < 0.5 * (zmax - zmin)]; CX = (min(_low) + max(_low)) / 2   # centre on the legs and hips, not the fingertips
print('centre x from legs', round(CX, 4), 'vs arm span', round((xmin + xmax) / 2, 4))
for v in body.data.vertices:
    v.co = mathutils.Vector(((v.co.x - CX) * s, (v.co.y - ymid) * s, (v.co.z - zmin) * s))
body.data.update()
vs = [v.co for v in body.data.vertices]

# ---- colours: match the generated texture to the photo, then bake the real photo over everything the photo sees
if IMG != 'none':
    import numpy as np
    photo = bpy.data.images.load(IMG); PW, PH = photo.size
    pp = np.array(photo.pixels[:]).reshape(PH, PW, 4)
    al = pp[..., 3] > 0.5; ys_, xs_ = np.where(al); x0, x1, y0, y1 = xs_.min(), xs_.max(), ys_.min(), ys_.max()
    mat0 = body.material_slots[0].material; nt0 = mat0.node_tree
    bsdf0 = next(n for n in nt0.nodes if n.type == 'BSDF_PRINCIPLED'); tex0 = bsdf0.inputs['Base Color'].links[0].from_node
    while tex0.type != 'TEX_IMAGE': tex0 = tex0.inputs[0].links[0].from_node
    timg = tex0.image; TW, TH = timg.size; tp = np.array(timg.pixels[:]).reshape(TH, TW, 4)
    used = tp[..., :3].sum(2) > 0.02; ref = pp[al][:, :3]
    for ch in range(3):                                  # histogram match, per channel
        src = tp[..., ch][used]; order = np.argsort(src); q = np.linspace(0, 1, len(src)); refq = np.quantile(ref[:, ch], q)
        out = np.empty_like(src); out[order] = refq; tp[..., ch][used] = 0.7 * out + 0.3 * src
    timg.pixels.foreach_set(tp.ravel().astype(np.float32)); timg.update()
    me_ = body.data; co = np.array([v.co[:] for v in me_.vertices]); nr = np.array([v.normal[:] for v in me_.vertices])
    bx0, bx1, bz0, bz1 = co[:, 0].min(), co[:, 0].max(), co[:, 2].min(), co[:, 2].max()
    # horizontal fit from the legs and torso (fingertips are unreliable): match row extents of the mesh and the photo
    A_, B_ = [], []
    for fr in np.linspace(0.08, 0.62, 28):
        zc = bz0 + fr * (bz1 - bz0); sel_ = np.abs(co[:, 2] - zc) < 0.012 * (bz1 - bz0)
        row = al[int(y0 + fr * (y1 - y0))]; cols = np.where(row)[0]
        if sel_.sum() < 4 or len(cols) < 4: continue
        mx0, mx1 = co[sel_, 0].min(), co[sel_, 0].max()
        if (mx1 - mx0) > 0.75: continue                      # skip rows that include the arms
        A_ += [[mx0, 1], [mx1, 1]]; B_ += [cols.min(), cols.max()]
    ka, kb = np.linalg.lstsq(np.array(A_), np.array(B_), rcond=None)[0]
    print('photo fit: px = %.1f * x + %.1f  (bbox would give %.1f, %.1f)' % (ka, kb, (x1 - x0) / (bx1 - bx0), x0 - bx0 * (x1 - x0) / (bx1 - bx0)))
    pu = (ka * co[:, 0] + kb) / PW; pv = (y0 + (co[:, 2] - bz0) / (bz1 - bz0) * (y1 - y0)) / PH
    uvp = me_.uv_layers.new(name='PhotoUV')
    for poly in me_.polygons:
        for li in poly.loop_indices:
            vi = me_.loops[li].vertex_index; uvp.data[li].uv = (pu[vi], pv[vi])
    me_.uv_layers.active = me_.uv_layers[0]; me_.uv_layers[0].active_render = True
    xi = np.clip((pu * PW).astype(int), 0, PW - 1); yi = np.clip((pv * PH).astype(int), 0, PH - 1)
    mask = np.clip((-nr[:, 1] - 0.2) / 0.35, 0, 1) * al[yi, xi]
    headz = bz0 + 0.86 * (bz1 - bz0); hm = co[:, 2] > headz
    mask[hm] = (np.clip((-nr[:, 1] - 0.5) / 0.3, 0, 1) * al[yi, xi])[hm]      # on the head, only the part that squarely faces the camera
    if len(argv) > 12:                                                        # eye and mouth positions for the game's expressions
        import json as _j
        LM = _j.load(open(argv[11]))[argv[12]]; sc = PW / LM['size'][0]; meta = {}
        for nm_, key_ in (('eyeA', 'eye_a'), ('eyeB', 'eye_b'), ('mouth', 'mouth')):
            pxx, pyy = LM[key_][0] * sc, PH - LM[key_][1] * sc
            X = (pxx - kb) / ka; Z = bz0 + (pyy - y0) / (y1 - y0) * (bz1 - bz0)
            near = (np.abs(co[:, 0] - X) < 0.03) & (np.abs(co[:, 2] - Z) < 0.03)
            Y = co[near, 1].min() if near.any() else co[hm, 1].min()
            meta[nm_] = [round(float(X), 4), round(float(Z), 4), round(float(-Y), 4)]      # game axes: x, up, forward
        _j.dump(meta, open(OUT.replace('.glb', '_meta.json'), 'w')); print('face points', meta)
    ca = me_.color_attributes.new(name='PhotoMask', type='FLOAT_COLOR', domain='POINT'); ca.data.foreach_set('color', np.repeat(mask, 4).astype(np.float32))
    bimg = bpy.data.images.new('baked_color', TW, TH)
    bm_ = bpy.data.materials.new('bake'); bm_.use_nodes = True; nt = bm_.node_tree; nt.nodes.clear()
    u1 = nt.nodes.new('ShaderNodeUVMap'); u1.uv_map = me_.uv_layers[0].name; u2 = nt.nodes.new('ShaderNodeUVMap'); u2.uv_map = 'PhotoUV'
    t1 = nt.nodes.new('ShaderNodeTexImage'); t1.image = timg; t2 = nt.nodes.new('ShaderNodeTexImage'); t2.image = photo; t2.extension = 'EXTEND'
    nt.links.new(u1.outputs['UV'], t1.inputs['Vector']); nt.links.new(u2.outputs['UV'], t2.inputs['Vector'])
    vc = nt.nodes.new('ShaderNodeVertexColor'); vc.layer_name = 'PhotoMask'; sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(vc.outputs['Color'], sep.inputs['Color'])
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; nt.links.new(sep.outputs['Red'], mix.inputs['Factor']); nt.links.new(t1.outputs['Color'], mix.inputs[6]); nt.links.new(t2.outputs['Color'], mix.inputs[7])
    em = nt.nodes.new('ShaderNodeEmission'); nt.links.new(mix.outputs[2], em.inputs['Color']); on = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(em.outputs['Emission'], on.inputs['Surface'])
    tg = nt.nodes.new('ShaderNodeTexImage'); tg.image = bimg; nt.nodes.active = tg
    body.material_slots[0].material = bm_
    scn_ = bpy.context.scene; scn_.render.engine = 'CYCLES'; scn_.cycles.device = 'CPU'; scn_.cycles.samples = 1
    for o in bpy.data.objects: o.select_set(False)
    body.select_set(True); bpy.context.view_layer.objects.active = body
    bpy.ops.object.bake(type='EMIT', margin=6, use_clear=True)
    bimg.pack(); tex0.image = bimg; body.material_slots[0].material = mat0
    me_.uv_layers.remove(me_.uv_layers['PhotoUV']); me_.color_attributes.remove(me_.color_attributes['PhotoMask'])
    for n in list(nt0.nodes):                           # plain colour only: drop the generated gloss and bump maps
        if n.type in ('NORMAL_MAP',) : nt0.nodes.remove(n)
    for inp in ('Metallic', 'Roughness', 'Normal'):
        for l in list(bsdf0.inputs[inp].links): nt0.links.remove(l)
    bsdf0.inputs['Metallic'].default_value = 0.0; bsdf0.inputs['Roughness'].default_value = 0.85
    print('photo baked over the front; texture', TW, 'x', TH, 'photo-covered verts', int((mask > 0.5).sum()), 'of', len(mask))
arm_l = [v for v in vs if v.x > 0.45]; arm_r = [v for v in vs if v.x < -0.45]
print('body span', round(max(v.x for v in vs) - min(v.x for v in vs), 3), 'height', round(max(v.z for v in vs), 3),
      'arm centre z L/R', round(sum(v.z for v in arm_l) / max(1, len(arm_l)), 3), round(sum(v.z for v in arm_r) / max(1, len(arm_r)), 3),
      'depth centre', round(sum(v.y for v in vs) / len(vs), 3))
# fit the arm bones to the body's arms (height and reach), keep everything else
armz = (sum(v.z for v in arm_l) / max(1, len(arm_l)) + sum(v.z for v in arm_r) / max(1, len(arm_r))) / 2
reach = (max(v.x for v in vs) - min(v.x for v in vs)) / 2
if XFER:
    import mathutils as _mu
    shx = abs((arm.matrix_world @ arm.data.bones['mixamorig:LeftArm'].head_local).x)
    xz = (arm.matrix_world @ arm.data.bones['mixamorig:LeftArm'].head_local).z
    hx = abs((arm.matrix_world @ arm.data.bones['mixamorig:LeftHand'].head_local).x)
    our_reach = reach
    k = ((hx / 0.87) - shx) / max(1e-3, our_reach - shx)      # stand-in fingertip reach ~ hand joint / 0.87
    for v in body.data.vertices:
        ax = abs(v.co.x)
        if ax > shx * 0.7:
            t = min(1.0, (ax - shx * 0.7) / (shx * 0.6)); t = t * t * (3 - 2 * t)
            nx = shx + (ax - shx) * k if ax > shx else ax
            v.co.x = (1 if v.co.x > 0 else -1) * (ax + (nx - ax) * t)
            v.co.z = v.co.z + (xz - armz) * t
    body.data.update()
    print('arms warped to the stand-in line: reach factor', round(k, 3), 'z shift', round(xz - armz, 3))
else:
    bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    inv = arm.matrix_world.inverted()
    eb = arm.data.edit_bones
    hand_l = (arm.matrix_world @ eb['mixamorig:LeftHand'].head)
    sh_l = (arm.matrix_world @ eb['mixamorig:LeftArm'].head)
    print('xbot rest: L arm head', [round(c,3) for c in sh_l], 'L hand head', [round(c,3) for c in hand_l])
    f = (reach * 0.87) / abs(hand_l.x)
    for b in eb:
        n = b.name
        if not any(n.startswith('mixamorig:' + side) for side in ('Left', 'Right')): continue
        if not any(k in n for k in ('Arm', 'ForeArm', 'Hand')) or 'Shoulder' in n: continue
        for attr in ('head', 'tail'):
            w = arm.matrix_world @ getattr(b, attr)
            w = mathutils.Vector((w.x * f, w.y, w.z + (armz - sh_l.z)))
            setattr(b, attr, inv @ w)
    bpy.ops.object.mode_set(mode='OBJECT')
# 3. lighter mesh for the browser
bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); bpy.context.view_layer.objects.active = body
m = body.modifiers.new('dec', 'DECIMATE'); m.ratio = DECIMATE
bpy.ops.object.modifier_apply(modifier=m.name)
print('faces after decimate', len(body.data.polygons))
_v = body.data.vertices; FULLB = (min(v.co.x for v in _v), max(v.co.x for v in _v), min(v.co.z for v in _v), max(v.co.z for v in _v))   # bounds with head and hands, for the photo mapping
if NOHEAD:   # the game puts a clean photo head here; drop the photo-projected 3D head (above the head joint, head width)
    hz0 = (arm.matrix_world @ arm.data.bones['mixamorig:Head'].head_local).z
    bm = bmesh.new(); bm.from_mesh(body.data)
    gone = [v for v in bm.verts if v.co.z > hz0 - 0.02 and abs(v.co.x) < 0.16]
    bmesh.ops.delete(bm, geom=gone, context='VERTS'); bm.to_mesh(body.data); bm.free(); body.data.update()
    print('head removed: verts', len(gone))
    # hands too: the game fits gloves at the wrists
    wx = abs((arm.matrix_world @ arm.data.bones['mixamorig:LeftHand'].head_local).x) - 0.005
    bm = bmesh.new(); bm.from_mesh(body.data)
    gone = [v for v in bm.verts if abs(v.co.x) > wx]
    bmesh.ops.delete(bm, geom=gone, context='VERTS'); bm.to_mesh(body.data); bm.free(); body.data.update()
    print('hands removed: verts', len(gone), 'wrist x', round(wx, 3))
# 5. skin it to the skeleton (Blender's automatic weights)
bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active = arm
if XFER and SRC is not None:
    for g in SRC.vertex_groups: body.vertex_groups.new(name=g.name)
    dt = body.modifiers.new('xfer', 'DATA_TRANSFER'); dt.object = SRC
    dt.use_vert_data = True; dt.data_types_verts = {'VGROUP_WEIGHTS'}; dt.vert_mapping = 'POLYINTERP_NEAREST'
    dt.layers_vgroup_select_src = 'ALL'; dt.layers_vgroup_select_dst = 'NAME'
    bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); bpy.context.view_layer.objects.active = body
    bpy.ops.object.modifier_apply(modifier=dt.name)
    bpy.data.objects.remove(SRC, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type='ARMATURE_NAME')
    # parent_set may add empty groups; the copied weights are already there
    # a vertex on one side of the body never follows the other side's leg or arm
    for v in body.data.vertices:
        if abs(v.co.x) < 0.015: continue
        wrong = 'Right' if v.co.x > 0 else 'Left'
        for g in list(v.groups):
            if body.vertex_groups[g.group].name.startswith('mixamorig:' + wrong): body.vertex_groups[g.group].remove([v.index])
        if not v.groups:
            body.vertex_groups['mixamorig:Hips'].add([v.index], 1.0, 'REPLACE')
        tot = sum(g.weight for g in v.groups)
        if tot > 0:
            for g in v.groups: g.weight /= tot
    print('weights copied from the stand-in surface')
else:
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
# keep the torso off the arm bones (heat weights bleed across the armpit), then renormalise
armg = set() if XFER else {g.index for g in body.vertex_groups if any(k in g.name for k in ('Arm', 'Hand')) and 'Shoulder' not in g.name}
shx = abs((arm.matrix_world @ arm.data.bones['mixamorig:LeftArm'].head_local).x)
for v in body.data.vertices:
    if abs(v.co.x) < shx + 0.02:
        for g in [g for g in v.groups if g.group in armg]: body.vertex_groups[g.group].remove([v.index])
    tot = sum(g.weight for g in v.groups)
    if tot > 0:
        for g in v.groups: g.weight /= tot
bpy.context.view_layer.objects.active = body
bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=0.5, repeat=2)
bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
bpy.ops.object.mode_set(mode='OBJECT')
# the head is rigid: everything above the head joint follows the head bone only (no smearing between head and neck)
hz = (arm.matrix_world @ arm.data.bones['mixamorig:Head'].head_local).z
nz = (arm.matrix_world @ arm.data.bones['mixamorig:Neck'].head_local).z
hg = body.vertex_groups.get('mixamorig:Head') or body.vertex_groups.new(name='mixamorig:Head')
ng = body.vertex_groups.get('mixamorig:Neck') or body.vertex_groups.new(name='mixamorig:Neck')
for v in body.data.vertices:
    if v.co.z >= hz + 0.01 and abs(v.co.x) < 0.16:
        for g in list(v.groups):
            if g.group != hg.index: body.vertex_groups[g.group].remove([v.index])
        hg.add([v.index], 1.0, 'REPLACE')
    elif v.co.z >= nz and abs(v.co.x) < 0.12:
        t = (v.co.z - nz) / max(1e-4, hz + 0.01 - nz)
        for g in list(v.groups):
            if g.group not in (hg.index, ng.index): body.vertex_groups[g.group].remove([v.index])
        hg.add([v.index], t, 'REPLACE'); ng.add([v.index], 1 - t, 'REPLACE')
print('head joint z', round(hz, 3), 'neck z', round(nz, 3))
unweighted = sum(1 for v in body.data.vertices if not v.groups)
print('vertices', len(body.data.vertices), 'without weights', unweighted)
# 5b. clean-up pass: even out the lumpy generated surface below the neck, and calm the speckled clothes texture (the face keeps full detail)
import numpy as _np
bm = bmesh.new(); bm.from_mesh(body.data)
low = [v for v in bm.verts if v.co.z < nz - 0.01 and not v.is_boundary]
for _ in range(5): bmesh.ops.smooth_vert(bm, verts=low, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
bm.to_mesh(body.data); bm.free(); body.data.update()
for pl in body.data.polygons: pl.use_smooth = True
print('smoothed verts below the neck', len(low))
if IMG != 'none':
    TW, TH = bimg.size; tp = _np.array(bimg.pixels[:], dtype=_np.float32).reshape(TH, TW, 4)
    uvl = body.data.uv_layers.active.data; head = _np.zeros((TH, TW), bool)
    for pl in body.data.polygons:                      # texels that belong to the head and neck keep their detail
        if min(body.data.vertices[i].co.z for i in pl.vertices) < nz - 0.02: continue
        uv = _np.array([[uvl[li].uv[0] * TW, uvl[li].uv[1] * TH] for li in pl.loop_indices])
        x0, y0 = _np.floor(uv.min(0)).astype(int) - 2; x1, y1 = _np.ceil(uv.max(0)).astype(int) + 2
        head[max(0, y0):min(TH, y1 + 1), max(0, x0):min(TW, x1 + 1)] = True
    used = (tp[..., :3].sum(2) > 0.02).astype(_np.float32)
    def box(a, r):
        c = _np.cumsum(_np.cumsum(_np.pad(a, ((r + 1, r), (r + 1, r))), 0), 1); n = 2 * r + 1
        return c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]
    den = _np.maximum(box(used, 4), 1e-3)
    for ch in range(3):
        bl = box(tp[..., ch] * used, 4) / den
        body_px = (~head) & (used > 0)
        v = 0.3 * tp[..., ch] + 0.7 * bl                # mostly the local average: flat, clean cloth colours
        v = _np.clip((v - 0.5) * 1.08 + 0.5 + 0.035, 0, 1) # a touch more contrast and light
        tp[..., ch] = _np.where(body_px, v, tp[..., ch])
    bimg.pixels.foreach_set(tp.ravel()); bimg.update(); bimg.pack()
    print('texture calmed: body texels', int(((~head) & (used > 0)).sum()), 'head texels kept', int((head & (used > 0)).sum()))
# 6. export for the game
bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); arm.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_animations=False, export_skins=True, export_yup=True, export_image_format='JPEG', export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6, export_draco_color_quantization=10)
print('exported', OUT)
# 7. check render: front and three-quarter, flat light
scn = bpy.context.scene
scn.render.engine = 'BLENDER_WORKBENCH'; scn.display.shading.light = 'FLAT'; scn.display.shading.color_type = 'TEXTURE'
scn.render.resolution_x, scn.render.resolution_y = 600, 700
w = bpy.data.worlds.new('w'); scn.world = w
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scn.collection.objects.link(cam); scn.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.2
for i, ang in enumerate((0, 35)):
    a = math.radians(ang); cam.location = (4 * math.sin(a), -4 * math.cos(a), 0.95); cam.rotation_euler = (math.radians(90), 0, a)
    scn.render.filepath = PREVIEW.replace('.png', f'_{i}.png'); bpy.ops.render.render(write_still=True)
print('previews written')
