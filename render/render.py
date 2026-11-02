"""Blender (5.2) renders of build/iPhone_Duo.glb.

    blender -b -P render/render.py -- <shot> [samples]

shots: rear_iso, front_iso, hinge_detail, ortho_front, ortho_rear, ortho_side, ortho_bottom
After import, world = CAD frame in metres (the importer leaves its Y-up fix on the root):
the phone lies flat, outer display facing +Z, top edge at Y=0, hinge at X=0.
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector, Euler, Matrix, Quaternion

ROOT = Path(__file__).resolve().parent.parent
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SHOT = args[0] if args else "rear_iso"
SAMPLES = int(args[1]) if len(args) > 1 else 256
SCALE = float(args[2]) if len(args) > 2 else 1.0        # resolution scale for quick tests
KEY = 6.0
OUT = ROOT / "renders"
OUT.mkdir(exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT / "build" / "iPhone_Duo.glb"))
root = bpy.data.objects["iPhone_Duo_folded"]
objs = {o.name: o for o in bpy.data.objects if o.type == "MESH"}


# ------------------------------------------------------------------ materials

def principled(name, color, metallic=0.0, rough=0.4, transmission=0.0, ior=1.5, coat=0.0,
               emission=None, aniso=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    b.inputs["Transmission Weight"].default_value = transmission
    b.inputs["IOR"].default_value = ior
    b.inputs["Coat Weight"].default_value = coat
    if aniso:
        b.inputs["Anisotropic"].default_value = aniso
    if emission:
        b.inputs["Emission Color"].default_value = (*emission[0], 1)
        b.inputs["Emission Strength"].default_value = emission[1]
    return m


MAT = {
    "alu": principled("alu", (0.42, 0.50, 0.62), metallic=1.0, rough=0.26, aniso=0.3),
    "alu_dark": principled("alu_dark", (0.34, 0.40, 0.50), metallic=1.0, rough=0.32),
    "band": principled("band", (0.025, 0.03, 0.045), rough=0.35),
    "back": principled("back", (0.13, 0.17, 0.25), rough=0.36, coat=0.2),
    "front_glass": principled("front_glass", (1, 1, 1), rough=0.0, transmission=1.0, ior=1.52),
    "ink": principled("ink", (0.004, 0.004, 0.005), rough=0.35),
    "display": principled("display", (0.006, 0.006, 0.008), rough=0.25),
    "front_cam": principled("front_cam", (0.02, 0.025, 0.04), metallic=0.3, rough=0.1),
    "ring": principled("ring", (0.50, 0.58, 0.70), metallic=1.0, rough=0.12),
    "lens": principled("lens", (0.008, 0.008, 0.012), rough=0.08, coat=1.0),
    "cam_glass": principled("cam_glass", (0.95, 0.97, 1.0), rough=0.0, transmission=1.0, ior=1.77),
    "flash": principled("flash", (0.95, 0.93, 0.82), rough=0.6),
    "screw": principled("screw", (0.35, 0.35, 0.37), metallic=1.0, rough=0.35),
    "black": principled("black", (0.01, 0.01, 0.01), rough=0.5),
    "sapphire": principled("sapphire", (0.10, 0.11, 0.12), rough=0.04, coat=1.0),
}
ASSIGN = {
    "A_frame": "alu", "B_frame": "alu", "B_side_button": "alu", "B_volume_down": "alu",
    "B_volume_up": "alu", "hinge_barrel": "alu_dark", "antenna_splits": "band",
    "B_back_glass": "back", "A_cover_glass": "front_glass", "A_display_active_area": "display",
    "A_front_camera": "front_cam", "B_camera_rings": "ring", "B_camera_lenses": "lens",
    "B_camera_cover_glass": "cam_glass", "B_flash": "flash", "A_screws": "screw",
    "B_screws": "screw", "A_usbc_tongue": "black", "B_camera_control": "sapphire",
}
for name, o in objs.items():
    o.data.materials.clear()
    o.data.materials.append(MAT[ASSIGN[name]])

# The frame fills the volume under the cover glass; paint that floor black like printed ink
# and drop it 10 um so it never coincides with the glass underside.
fr = objs["A_frame"]
fr.data.materials.append(MAT["ink"])
floor_y = -0.0050
moved = set()
for p in fr.data.polygons:
    if abs(p.center.y - floor_y) < 2e-6 and p.normal.y < -0.99:
        p.material_index = 1
        moved.update(p.vertices)
for i in moved:
    fr.data.vertices[i].co.y += 1e-5
for n in ("A_display_active_area", "A_front_camera"):
    for v in objs[n].data.vertices:
        v.co.y += 1e-5

# ------------------------------------------------------------------ world + lights

scn = bpy.context.scene
scn.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "METAL"
prefs.get_devices()
for d in prefs.devices:
    d.use = True
scn.cycles.device = "GPU"
scn.cycles.samples = SAMPLES
scn.cycles.use_denoising = True
scn.view_settings.view_transform = "AgX"
scn.view_settings.look = "AgX - Medium High Contrast"

world = bpy.data.worlds.new("w")
scn.world = world
world.use_nodes = True
nt = world.node_tree
nt.nodes.clear()
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(str(Path(bpy.utils.resource_path("LOCAL")) / "datafiles/studiolights/world/interior.exr"))
bg_light = nt.nodes.new("ShaderNodeBackground")
bg_light.inputs["Strength"].default_value = 0.35
bg_cam = nt.nodes.new("ShaderNodeBackground")
bg_cam.inputs["Color"].default_value = (0.012, 0.012, 0.014, 1)
lp = nt.nodes.new("ShaderNodeLightPath")
mix = nt.nodes.new("ShaderNodeMixShader")
outn = nt.nodes.new("ShaderNodeOutputWorld")
nt.links.new(env.outputs["Color"], bg_light.inputs["Color"])
nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
nt.links.new(bg_light.outputs["Background"], mix.inputs[1])
nt.links.new(bg_cam.outputs["Background"], mix.inputs[2])
nt.links.new(mix.outputs["Shader"], outn.inputs["Surface"])


def area(name, loc, target, size, energy, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, "AREA")
    l.size = size
    l.energy = energy
    l.color = color
    o = bpy.data.objects.new(name, l)
    scn.collection.objects.link(o)
    o.location = loc
    d = Vector(target) - Vector(loc)
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return o


def camera(loc, target, lens=85, ortho=None, up=(0, 0, 1)):
    c = bpy.data.cameras.new("cam")
    o = bpy.data.objects.new("cam", c)
    scn.collection.objects.link(o)
    o.location = loc
    if ortho:
        c.type = "ORTHO"
        c.ortho_scale = ortho
    else:
        c.lens = lens
    f = (Vector(target) - Vector(loc)).normalized()
    z = -f
    x = Vector(up).cross(z).normalized()
    y = z.cross(x)
    o.rotation_euler = Matrix((x, y, z)).transposed().to_euler()
    c.clip_start = 0.001
    c.clip_end = 10
    scn.camera = o
    return o


C = Vector((0.04205, -0.0589, 0.0))      # middle of the folded phone, world = CAD frame
Q_IMPORT = root.rotation_quaternion.copy()


def pose(rx_deg=0.0):
    """Turn the phone about X through its middle and put that middle at the origin."""
    q = Quaternion((1, 0, 0), math.radians(rx_deg))
    root.rotation_mode = "QUATERNION"
    root.rotation_quaternion = q @ Q_IMPORT
    root.location = -(q.to_matrix() @ C)
    bpy.context.view_layer.update()


def studio(key_from, target=(0, 0, 0)):
    k = Vector(key_from)
    area("key", tuple(k * 0.6), target, 0.35, KEY)
    area("rim", (-k.x * 0.5, -k.y * 0.5, abs(k.z) * 0.6 + 0.15), target, 0.25, KEY * 0.6)
    area("fill", (k.y * 0.5, -k.x * 0.5, 0.05), target, 0.6, KEY * 0.25)


res = {"x": 1600, "y": 2000}
if SHOT == "rear_iso":
    pose(180)                           # back facing up, top edge toward -Y
    tgt = (0.000, -0.0125, 0.003)
    camera((0.170, -0.225, 0.130), tgt, lens=66)
    area("strip", (-0.05, 0.10, 0.25), tgt, 0.5, KEY * 0.4).data.shape = "RECTANGLE"
    studio((0.4, -0.3, 0.5), tgt)
    res = {"x": 2000, "y": 1600}
elif SHOT == "front_iso":
    pose(0)                             # outer display up, bottom edge toward -Y
    tgt = (-0.0035, -0.002, 0.0)
    camera((0.180, -0.240, 0.160), tgt, lens=66)
    studio((0.3, -0.4, 0.5), tgt)
    res = {"x": 2000, "y": 1600}
elif SHOT == "hinge_detail":
    pose(0)
    tgt = (-0.022, -0.050, 0.0)
    camera((-0.120, -0.150, 0.070), tgt, lens=100)
    studio((-0.2, -0.4, 0.3), tgt)
    res = {"x": 2000, "y": 1600}
else:
    scn.render.film_transparent = True
    bg_cam.inputs["Color"].default_value = (1, 1, 1, 1)
    o = 0.13
    pose(0)                             # phone middle at the origin, CAD axes
    if SHOT == "ortho_front":
        camera((0, 0, 1.0), (0, 0, 0), ortho=o, up=(0, 1, 0))
        studio((0.2, 0.3, 0.5))
    elif SHOT == "ortho_rear":
        camera((0, 0, -1.0), (0, 0, 0), ortho=o, up=(0, 1, 0))
        studio((-0.2, 0.3, -0.5))
    elif SHOT == "ortho_side":
        camera((1.0, 0, 0), (0, 0, 0), ortho=o, up=(0, 1, 0))
        studio((0.5, 0.3, 0.2))
    elif SHOT == "ortho_bottom":
        camera((0, -1.0, 0), (0, 0, 0), ortho=o, up=(0, 0, 1))
        studio((0.2, -0.5, 0.3))
    res = {"x": 2600, "y": 2600}

scn.render.resolution_x = int(res["x"] * SCALE)
scn.render.resolution_y = int(res["y"] * SCALE)
scn.render.filepath = str(OUT / f"{SHOT}.png")
bpy.ops.render.render(write_still=True)
print("WROTE", scn.render.filepath)
