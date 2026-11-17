# review_render.py: the gate's renders.  For each fixture id: loads <id>/<id>.glb and writes PNG cells to
# lighting/_rv/<id>/ : four orthographic views of the sheet's subject (front, side, back, top; lamp off), and for
# every object a three-quarter view lamp off (flat daylight) and lamp on (dusk, the lit material glowing, a real
# light at stats.json's light_at / light_dir in the suggested colour, a wall / deck / ceiling behind it to catch it).
# review_compose.py then puts them beside the sheet.
#   blender -b --factory-startup -t 4 --python review_render.py -- [id ...]
import bpy, sys, os, math, json
from mathutils import Vector, Euler, Matrix
A = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
HERE = os.path.dirname(os.path.abspath(__file__)); FAM = os.path.abspath(os.path.join(HERE, ".."))
IDS = ["wellglass", "tube_light", "flood", "obstruction_light", "helideck_lights", "escape_route", "beacon", "work_light"]
SET = {"helideck_lights", "escape_route", "work_light"}        # sheets that show the whole set side by side
PRIMARY = dict(wellglass="wellglass", tube_light="tube_light_ceiling", flood="flood_head", obstruction_light="obstruction_light", beacon="beacon_pole")
CW, CH = 720, 600


def setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.render.engine = "BLENDER_EEVEE"
    try: sc.eevee.taa_render_samples = 32
    except Exception as e: print(e)
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun); sun.data.angle = math.radians(40)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    sc.render.image_settings.file_format = "PNG"; sc.render.film_transparent = False
    return sc, w.node_tree.nodes["Background"], sun, cam


def bounds(objs):
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])


def shoot(sc, cam, sun, path, az, el, ortho, mn, mx, cw=CW, ch=CH, fit=1.16, lens=60, dist=2.2):
    size = mx - mn; ctr = (mn + mx) / 2; diag = max(size.length, 0.05); azr, elr = math.radians(az), math.radians(el)
    d = Vector((math.sin(azr) * math.cos(elr), -math.cos(azr) * math.cos(elr), math.sin(elr)))
    sc.render.resolution_x, sc.render.resolution_y = cw, ch
    if ortho:
        if abs(el) > 89: w_, h_ = size.x, size.y
        else: w_, h_ = abs(math.cos(azr)) * size.x + abs(math.sin(azr)) * size.y, size.z
        cam.data.type = "ORTHO"; cam.data.ortho_scale = max(w_ * fit, h_ * fit * cw / ch, 0.05); cam.location = ctr + d * (diag * 2 + 1)
    else:
        cam.data.type = "PERSP"; cam.data.lens = lens; cam.location = ctr + d * (diag * dist + 0.05)
    cam.data.clip_start = 0.01; cam.data.clip_end = diag * 8 + 20
    cam.rotation_euler = Euler((0, 0, 0)) if el > 89 else (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
    ld = (d + Vector((0, 0, 0.8)) + d.cross(Vector((0, 0, 1))) * 0.5) if abs(el) < 89 else Vector((0.3, -0.4, 1))
    sun.rotation_euler = (-ld).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)


def plane(name, c, n, s, col=(0.33, 0.35, 0.36)):
    bpy.ops.mesh.primitive_plane_add(size=s, location=c); o = bpy.context.object; o.name = name
    o.rotation_euler = Vector(n).to_track_quat("Z", "Y").to_euler()
    m = bpy.data.materials.new(name); m.use_nodes = True; bs = m.node_tree.nodes["Principled BSDF"]
    bs.inputs["Base Color"].default_value = (*col, 1); bs.inputs["Roughness"].default_value = 0.7; o.data.materials.append(m)
    return o


def do(fid):
    sc, bg, sun, cam = setup()
    st = json.load(open(os.path.join(FAM, fid, "stats.json")))
    bpy.ops.import_scene.gltf(filepath=os.path.join(FAM, fid, fid + ".glb"))
    objs = {o.name: o for o in sc.objects if o.type == "MESH"}
    out = os.path.join(FAM, "_rv", fid); os.makedirs(out, exist_ok=True)
    lit = {}
    for m in bpy.data.materials:
        if "__lit" in m.name and m.use_nodes:
            bs = m.node_tree.nodes.get("Principled BSDF")
            if bs: lit[m.name] = (bs, bs.inputs["Emission Strength"].default_value)

    def lamps(on):
        for bs, s in lit.values(): bs.inputs["Emission Strength"].default_value = s if on else 0.0

    def day():
        sc.view_settings.view_transform = "Standard"; sc.view_settings.exposure = 0; bg.inputs[0].default_value = (0.42, 0.42, 0.43, 1); bg.inputs[1].default_value = 1.0; sun.data.energy = 1.5; sun.hide_render = False; lamps(False)

    def dusk():
        sc.view_settings.view_transform = "AgX"; sc.view_settings.exposure = -3.6; bg.inputs[0].default_value = (0.10, 0.14, 0.24, 1); bg.inputs[1].default_value = 5.0; sun.data.energy = 3.0; lamps(True)

    def show(names):
        for n, o in objs.items(): o.hide_render = n not in names

    # orthographic views of the sheet's subject
    day()
    if fid in SET:
        for n, o in objs.items(): o.location = Vector(o.location) + Vector(st["layout"][n])
        sub = list(objs)
    else: sub = [PRIMARY[fid]]
    show(sub); mn, mx = bounds([objs[n] for n in sub])
    if fid == "beacon": objs["beacon_lens"].location = st["items"]["beacon_pole"]["lens_at"]; objs["beacon_lens"].hide_render = False
    for tag, az, el in (("front", 0, 0), ("side", -90, 0), ("back", 180, 0), ("top", 0, 90)):
        shoot(sc, cam, sun, os.path.join(out, f"_{tag}.png"), az, el, True, mn, mx)
    for o in objs.values(): o.location = (0, 0, 0)
    def seat(n, on):            # the beacon's dome is its own object: show it in its seat
        if fid == "beacon" and n != "beacon_lens":
            lens = objs["beacon_lens"]; lens.location = st["items"][n]["lens_at"] if on else (0, 0, 0); lens.hide_render = not on
    # three-quarter, off and on, per object
    for n, o in objs.items():
        it = st["items"][n]; mount = it.get("mount", ""); show([n]); mn, mx = bounds([o]); size = mx - mn; big = max(size.length, 0.3)
        el = -14 if mount == "ceiling" else 16
        az = 145 if n in ("flood_rail",) else -35
        seat(n, True); day(); shoot(sc, cam, sun, os.path.join(out, f"{n}_off.png"), az, el, False, mn, mx)
        dusk(); extra = []
        ctr = (mn + mx) / 2
        if mount == "wall": extra.append(plane("wall", (ctr.x, 0.002, ctr.z), (0, -1, 0), big * 6))
        elif mount == "ceiling": extra.append(plane("ceil", (ctr.x, ctr.y, 0.002), (0, 0, -1), big * 6)); extra.append(plane("wall", (ctr.x, 0.6, ctr.z), (0, -1, 0), big * 6))
        elif mount == "rail": extra.append(plane("deck", (ctr.x, ctr.y, -1.1), (0, 0, 1), big * 8))
        else: extra.append(plane("deck", (ctr.x, ctr.y, mn.z - 0.001), (0, 0, 1), big * 8))
        if mount not in ("wall", "ceiling") and az < 90: extra.append(plane("wall", (ctr.x, mx.y + big * 0.8, ctr.z), (0, -1, 0), big * 8))
        sg = it.get("suggested", {}); col = sg.get("rgb", (1, 1, 1))
        for L in (it.get("lights") or [dict(at=it.get("light_at"), dir=it.get("light_dir"))]):
            if not L.get("at"): continue
            spot = L.get("dir") is not None and sg.get("spot_deg")
            ld = bpy.data.lights.new("l", "SPOT" if spot else "POINT"); lo = bpy.data.objects.new("l", ld); sc.collection.objects.link(lo); extra.append(lo)
            lo.location = L["at"]; ld.color = col; ld.energy = 800 * (sg.get("power", 1) ** 0.5) * big * big * (3 if spot else 1); ld.shadow_soft_size = 0.03
            if spot:
                ld.spot_size = math.radians(min(sg["spot_deg"], 170)); ld.spot_blend = 0.5
                lo.rotation_euler = Vector(L["dir"]).to_track_quat("-Z", "Y").to_euler()
        shoot(sc, cam, sun, os.path.join(out, f"{n}_on.png"), az, el, False, mn, mx)
        seat(n, False)
        for e in extra: bpy.data.objects.remove(e)
    print("rendered", fid)


for fid in (A or IDS): do(fid)
