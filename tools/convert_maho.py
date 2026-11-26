# Turns the rigged giant (.blend with packed textures) into one small file the browser can load: skinned Body + static Wheel.
import bpy, sys, os, bmesh, mathutils
OUT = sys.argv[sys.argv.index('--') + 1]
arm = bpy.data.objects['Armature']; body = bpy.data.objects['Plane.008']; wheel = bpy.data.objects['Roundcube']
def first_img(m, prefer):
    for n in prefer:
        im = bpy.data.images.get(n)
        if im and im.size[0] > 0: return im
    return None
def simple(m, im, size, alpha=False):
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); b = nt.nodes.new('ShaderNodeBsdfPrincipled'); nt.links.new(b.outputs['BSDF'], out.inputs['Surface'])
    b.inputs['Roughness'].default_value = 0.7; b.inputs['Metallic'].default_value = 0.0
    if im:
        if im.size[0] > size: im.scale(size, int(size * im.size[1] / im.size[0]))
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = im; nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
        if alpha: nt.links.new(t.outputs['Alpha'], b.inputs['Alpha']); m.blend_method = 'CLIP'
    m.use_backface_culling = False
# drop the inverted-hull outline faces
for o in (body, wheel):
    idx = [i for i, s in enumerate(o.material_slots) if s.material and s.material.name == 'Outline']
    if idx:
        bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in idx], context='FACES'); bm.to_mesh(o.data); bm.free()
for s in body.material_slots:
    m = s.material
    if m.name == 'Body': simple(m, first_img(m, ['Mahoraga Color', 'DefaultMaterial_Base_color.png']), 1024)
    elif m.name == 'Feather': simple(m, first_img(m, ['feather (2).png.001']), 256, alpha=True)
# the wheel: bake its modifiers into plain geometry, origin at its centre
dg = bpy.context.evaluated_depsgraph_get(); ev = wheel.evaluated_get(dg); me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
W = bpy.data.objects.new('Wheel', me); bpy.context.scene.collection.objects.link(W); W.matrix_world = wheel.matrix_world.copy()
bpy.ops.object.select_all(action='DESELECT'); W.select_set(True); bpy.context.view_layer.objects.active = W; bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
idx = [i for i, s in enumerate(W.material_slots) if s.material and s.material.name == 'Outline']
if idx:
    bm = bmesh.new(); bm.from_mesh(W.data); bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in idx], context='FACES'); bm.to_mesh(W.data); bm.free()
vs = [v.co.copy() for v in W.data.vertices]; c = sum(vs, mathutils.Vector()) / len(vs)
for v in W.data.vertices: v.co -= c
W.location = c
for s in W.material_slots:
    if s.material and s.material.name == 'The Great Wheel': simple(s.material, first_img(s.material, ['The Great Wheel_Base_color.png']), 512)
print('Wheel tris', sum(len(p.vertices) - 2 for p in W.data.polygons), 'centre', [round(x, 2) for x in c], 'size', [round(max(v[i] for v in vs) - min(v[i] for v in vs), 2) for i in range(3)])
bpy.data.objects.remove(wheel, do_unlink=True)
body.name = 'Body'; print('Body tris', sum(len(p.vertices) - 2 for p in body.data.polygons))
bpy.ops.object.select_all(action='DESELECT')
for o in (arm, body, W): o.hide_set(False); o.select_set(True)
kw = dict(filepath=OUT, export_format='GLB', use_selection=True, export_animations=False, export_yup=True, export_image_format='JPEG', export_skins=True, export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
try: bpy.ops.export_scene.gltf(export_jpeg_quality=78, **kw)
except TypeError: bpy.ops.export_scene.gltf(**kw)
print('exported', round(os.path.getsize(OUT) / 1e6, 2), 'MB')
