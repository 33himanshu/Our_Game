# Turns the downloaded shrine (FBX + large textures) into one small file the browser can load.
import bpy, sys, os, math, mathutils
a = sys.argv[sys.argv.index('--') + 1:]; SRC, TEX, OUT, PREV = a[:4]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
SET = {'Extra_Stuff_Material': ('ExtraStuff', 512), 'Bull_Skull_Material': ('Bull_Skull', 512), 'Mouths_Material': ('Mouth', 512), 'Human_Skull_Material': ('Human_Skull', 256), 'Shrine_Material': ('Shrine', 1024)}
def img(name, size, srgb=True):
    p = os.path.join(TEX, name + '.tga.png')
    if not os.path.exists(p): return None
    im = bpy.data.images.load(p); im.scale(size, size); im.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'; return im
done = {}
for o in meshes:
    for slot in o.material_slots:
        m = slot.material
        if not m or m.name in done or m.name not in SET: continue
        base, size = SET[m.name]; m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial'); b = nt.nodes.new('ShaderNodeBsdfPrincipled'); nt.links.new(b.outputs['BSDF'], out.inputs['Surface'])
        b.inputs['Roughness'].default_value = 0.85; b.inputs['Metallic'].default_value = 0.0
        cm = img(base + '_CM', size)
        if cm: t = nt.nodes.new('ShaderNodeTexImage'); t.image = cm; nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
        em = img(base + '_E', size)
        if em:
            t2 = nt.nodes.new('ShaderNodeTexImage'); t2.image = em
            for k in ('Emission Color', 'Emission'):
                if k in b.inputs: nt.links.new(t2.outputs['Color'], b.inputs[k]); break
            if 'Emission Strength' in b.inputs: b.inputs['Emission Strength'].default_value = 2.0
        done[m.name] = (bool(cm), bool(em))
print('materials', done)
# lighter geometry: the two heavy parts carry most of the triangles
for o in meshes:
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    if tris > 12000:
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        md = o.modifiers.new('dec', 'DECIMATE'); md.ratio = 15000 / tris; bpy.ops.object.modifier_apply(modifier=md.name)
    for p in o.data.polygons: p.use_smooth = True
# one object, standing on the floor, about 3.6 m tall
bpy.ops.object.select_all(action='DESELECT')
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]; bpy.ops.object.join(); S = bpy.context.view_layer.objects.active
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM'); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
vs = [S.matrix_world @ v.co for v in S.data.vertices]; z0, z1 = min(v.z for v in vs), max(v.z for v in vs); cx = (min(v.x for v in vs) + max(v.x for v in vs)) / 2; cy = (min(v.y for v in vs) + max(v.y for v in vs)) / 2
k = 3.6 / (z1 - z0)
for v in S.data.vertices: v.co = mathutils.Vector(((v.co.x - cx) * k, (v.co.y - cy) * k, (v.co.z - z0) * k))
S.data.update(); vs = [v.co for v in S.data.vertices]
print('tris', sum(len(p.vertices) - 2 for p in S.data.polygons), 'size x/y/z', round(max(v.x for v in vs) - min(v.x for v in vs), 2), round(max(v.y for v in vs) - min(v.y for v in vs), 2), round(max(v.z for v in vs), 2))
for o in [o for o in bpy.context.scene.objects if o is not S]: bpy.data.objects.remove(o, do_unlink=True)
S.name = 'Shrine'; bpy.ops.object.select_all(action='DESELECT'); S.select_set(True)
kw = dict(filepath=OUT, export_format='GLB', use_selection=True, export_animations=False, export_yup=True, export_image_format='JPEG', export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
try: bpy.ops.export_scene.gltf(export_jpeg_quality=72, **kw)
except TypeError:
    try: bpy.ops.export_scene.gltf(export_image_quality=72, **kw)
    except TypeError: bpy.ops.export_scene.gltf(**kw)
print('exported', OUT, round(os.path.getsize(OUT) / 1e6, 2), 'MB')
scn = bpy.context.scene; scn.render.engine = 'BLENDER_WORKBENCH'; scn.display.shading.light = 'STUDIO'; scn.display.shading.color_type = 'TEXTURE'
scn.render.resolution_x, scn.render.resolution_y = 700, 700; scn.world = bpy.data.worlds.new('w')
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scn.collection.objects.link(cam); scn.camera = cam; cam.data.type = 'ORTHO'; cam.data.ortho_scale = 6.2
for i, ang in enumerate((0, 90, 180, 270)):
    r = math.radians(ang); cam.location = (8 * math.sin(r), -8 * math.cos(r), 2.0); cam.rotation_euler = (math.radians(86), 0, r)
    scn.render.filepath = PREV.replace('.png', f'_{i}.png'); bpy.ops.render.render(write_still=True)
print('previews written')
