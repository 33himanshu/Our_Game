# Turns the downloaded domain model (FBX + large textures) into one small file the browser can load: Dome, Arms, Hands.
import bpy, sys, os, math
a = sys.argv[sys.argv.index('--') + 1:]; SRC, TEX, OUT, PREV = a[:4]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.fbx(filepath=SRC)
SET = {'Self_Embodiment_of_Perfection': ('SEoP', 1024, 'Dome', 0), 'Arms': ('Arm', 1024, 'Arms', 32000), 'Hands': ('Hand', 512, 'Hands', 9000)}
def img(name, size):
    p = os.path.join(TEX, name + '.tga.png')
    if not os.path.exists(p): return None
    im = bpy.data.images.load(p); im.scale(size, size); return im
keep = []
for o in [o for o in bpy.context.scene.objects if o.type == 'MESH']:
    m = o.material_slots[0].material; base, size, name, target = SET[m.name]; o.name = name; keep.append(o)
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); b = nt.nodes.new('ShaderNodeBsdfPrincipled'); nt.links.new(b.outputs['BSDF'], out.inputs['Surface'])
    b.inputs['Roughness'].default_value = 0.8; b.inputs['Metallic'].default_value = 0.0
    cm = img(base + '_CM', size)
    if cm: t = nt.nodes.new('ShaderNodeTexImage'); t.image = cm; nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    em = img(base + '_E', size)
    if em:
        t2 = nt.nodes.new('ShaderNodeTexImage'); t2.image = em
        for k in ('Emission Color', 'Emission'):
            if k in b.inputs: nt.links.new(t2.outputs['Color'], b.inputs[k]); break
        if 'Emission Strength' in b.inputs: b.inputs['Emission Strength'].default_value = 1.0
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    if name == 'Hands':                                    # the lone open hand in the middle becomes its own piece ("Palm"), centred, for the strikes
        import bmesh
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM'); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_mode(type='VERT'); bpy.ops.mesh.select_all(action='DESELECT'); bm = bmesh.from_edit_mesh(o.data)
        for v in bm.verts: v.select = v.co.x > -1.6
        bm.select_flush_mode(); bmesh.update_edit_mesh(o.data); bpy.ops.mesh.separate(type='SELECTED'); bpy.ops.object.mode_set(mode='OBJECT')
        palm = [x for x in bpy.context.selected_objects if x is not o][0]; palm.name = 'Palm'; keep.append(palm)
        vs = [v.co for v in palm.data.vertices]; c = sum(vs, type(vs[0])((0, 0, 0))) / len(vs)
        for v in palm.data.vertices: v.co -= c
        print('Palm verts', len(vs), 'size', [round(max(v[i] for v in vs) - min(v[i] for v in vs), 2) for i in range(3)])
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    if target and tris > target: md = o.modifiers.new('dec', 'DECIMATE'); md.ratio = target / tris; bpy.ops.object.modifier_apply(modifier=md.name)
    for p in o.data.polygons: p.use_smooth = True
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM'); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    print(name, 'tris', sum(len(p.vertices) - 2 for p in o.data.polygons), 'cm', bool(cm), 'em', bool(em))
for o in [o for o in bpy.context.scene.objects if o not in keep]: bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.object.select_all(action='DESELECT')
for o in keep: o.select_set(True)
kw = dict(filepath=OUT, export_format='GLB', use_selection=True, export_animations=False, export_yup=True, export_image_format='JPEG', export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
try: bpy.ops.export_scene.gltf(export_jpeg_quality=74, **kw)
except TypeError:
    try: bpy.ops.export_scene.gltf(export_image_quality=74, **kw)
    except TypeError: bpy.ops.export_scene.gltf(**kw)
print('exported', round(os.path.getsize(OUT) / 1e6, 2), 'MB')
scn = bpy.context.scene; scn.render.engine = 'BLENDER_WORKBENCH'; scn.display.shading.light = 'STUDIO'; scn.display.shading.color_type = 'TEXTURE'
scn.render.resolution_x, scn.render.resolution_y = 1000, 600; scn.world = bpy.data.worlds.new('w')
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scn.collection.objects.link(cam); scn.camera = cam; cam.data.lens = 22
for i, (loc, rot, hide) in enumerate([((0, -4.2, 1.4), (88, 0, 0), False), ((0, -11, 3), (80, 0, 0), True), ((0, 0, 14), (0, 0, 0), True)]):
    bpy.data.objects['Dome'].hide_render = hide
    cam.location = loc; cam.rotation_euler = tuple(math.radians(x) for x in rot); scn.render.filepath = PREV.replace('.png', f'_{i}.png'); bpy.ops.render.render(write_still=True)
