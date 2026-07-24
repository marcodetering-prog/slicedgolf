"""SLICED GOLF — Rendert alle Panoramen der virtuellen Galerie.

Vier begehbare Räume, verbunden über Türen (Weltmodell in
js/galerie-pano.js — dort stehen auch Stationen, Werke und Türen):

  foyer       Eingangshalle: warme Wände, Eichenboden, Bank, Pendants,
              Portal nach draussen, Türen zu White Cube und Salon
  white-cube  Weisse Halle mit Tonnengewölbe-Lichtdecke (12 x 8 m),
              Türen zu Foyer und Garten
  salon       Klassischer Salon: Stuckrahmen, Vertäfelung, Kassettendecke,
              Kronleuchter, Westfenster, Tür zum Foyer
  garten      Skulpturengarten: Rasen, Hecken, Bäume, Nishita-Himmel,
              riesige aufgeschnittene Golfball-Skulptur, Portal zum
              White Cube

Jedes Werk bekommt eine lesbare Wandplakette (Titel + Opus-Zeile).

Aufruf:
  blender -b -P tools/render-gallery.py -- \
      [--theme foyer|white-cube|salon|garten|all] [--only N] [--preview]

Achsen: Blender x = -three-x (gespiegelt, wie die Original-Panoramen),
Blender y = three z (Nordwand bei y=-4), Blender z = Höhe. Bildmitte der
Equirect = -Y. Werke-/Textpositionen sind daher x-negiert zum Weltmodell.
"""

import math
import os
import sys

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART_DIR = '/tmp/sg-art'
OUT_DIR = os.path.join(ROOT, 'images', 'pano')

EYE = 1.55
HANG = 1.58

# Halle (White Cube & Salon): 12 x 8 m, Wände x=±6, y=±4
HALL_W, HALL_D, HALL_H = 12.0, 8.0, 3.5
# Foyer: 8 x 6 m, Wände x=±4, y=±3
FOY_W, FOY_D, FOY_H = 8.0, 6.0, 3.2
# Garten: 12 x 12 m Hecken
GAR = 12.0

# Stationen in three-Koordinaten (x wird beim Rendern gespiegelt)
HALL_ST = [(0.0, 2.4), (0.0, 0.0), (-2.4, -1.9), (2.4, -1.9),
           (2.4, 1.9), (-2.4, 1.9), (-4.1, 0.0)]
STATIONS = {
    'foyer': [(0.0, 1.2), (2.4, 0.0), (0.0, -1.2)],
    'white-cube': HALL_ST + [(4.3, -2.0), (4.3, 2.0)],
    'salon': HALL_ST + [(4.3, 0.0)],
    'garten': [(0.0, 4.2), (0.0, -0.5)],
}

# Wand: 'n'/'s' = Nord/Süd (y=-4/+4), 'e' = Ost (x=+6). 'along' in Blender-x.
WERKE = [
    dict(slug='blumenwiese', img='blumenwiese.jpg', wall='n', along=2.4,
         w=1.35, h=1.35, title='Blumenwiese',
         meta='Opus 21/99 · 100 × 100 cm · 2025'),
    dict(slug='rasta-mondrian', img='rasta-mondrian-auf-wolke-7.jpg', wall='n',
         along=-2.4, w=1.25, h=1.25, title='Rasta-Mondrian auf Wolke 7',
         meta='Opus 27/99 · 100 × 100 cm · 2024'),
    dict(slug='darkroom-beleuchter', img='darkroom-beleuchter.jpg', wall='s',
         along=-2.4, w=1.35, h=1.37, title='Darkroom Beleuchter',
         meta='Opus 13/99 · 100 × 70 cm · 2023'),
    dict(slug='fairway-spektrum', img='fairway-spektrum.jpg', wall='s',
         along=2.4, w=1.20, h=0.90, title='Fairway Spektrum',
         meta='Opus 16/99 · 100 × 75 cm · 2024'),
    dict(slug='stille-wasser', img='stille-wasser-crop.jpg', wall='e', along=0.0,
         w=1.0, h=0.65, title='Stille Wasser',
         meta='Opus 31/99 · 70 × 50 cm · 2025'),
]

# Fensteröffnungen Westwand Salon (y-Mitte, Breite, unten, oben)
WINDOWS = [(-1.5, 1.1, 0.85, 3.05), (1.5, 1.1, 0.85, 3.05)]

# Plakette neben dem Werk (lesbar aus ~2 m Betrachtungsdistanz)
PLAQ_W, PLAQ_H, PLAQ_Z = 0.44, 0.26, 1.30

DOOR_W, DOOR_H = 1.0, 2.2


# ── Materialien ──────────────────────────────────────────

def mat_principled(name, color, rough=0.6, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metallic
    return m


def mat_emission(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*color, 1.0)
    em.inputs['Strength'].default_value = strength
    nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    return m


def mat_noise(name, dark, light, scale, rough, bump=0.2):
    """Zweifarbige Noise-Textur (Parkett, Rasen, Hecke)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']
    tex = nt.nodes.new('ShaderNodeTexNoise')
    tex.inputs['Scale'].default_value = scale
    tex.inputs['Detail'].default_value = 5.0
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].color = (*light, 1)
    nt.links.new(tex.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    if bump:
        b = nt.nodes.new('ShaderNodeBump')
        b.inputs['Strength'].default_value = bump
        b.inputs['Distance'].default_value = 0.08
        nt.links.new(tex.outputs['Fac'], b.inputs['Height'])
        nt.links.new(b.outputs['Normal'], bsdf.inputs['Normal'])
    bsdf.inputs['Roughness'].default_value = rough
    return m


def mat_floor_dark():
    """Dunkles Parkett mit Maserung, seidenmatt."""
    m = mat_noise('Parkett', (0.035, 0.018, 0.010), (0.16, 0.09, 0.045), 3.0, 0.38, 0.25)
    nt = m.node_tree
    wave = nt.nodes.new('ShaderNodeTexWave')
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'X'
    wave.inputs['Scale'].default_value = 5.0
    wave.inputs['Distortion'].default_value = 2.5
    wave.inputs['Detail'].default_value = 3.0
    bsdf = nt.nodes['Principled BSDF']
    mix = nt.nodes['ShaderNodeMixRGB'] if nt.nodes.get('ShaderNodeMixRGB') else None
    # Maserung in die Basis-Färbung multiplizieren
    ramp2 = nt.nodes.new('ShaderNodeValToRGB')
    ramp2.color_ramp.elements[0].color = (0.5, 0.5, 0.5, 1)
    ramp2.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1)
    nt.links.new(wave.outputs['Color'], ramp2.inputs['Fac'])
    mult = nt.nodes.new('ShaderNodeMixRGB')
    mult.blend_type = 'MULTIPLY'
    mult.inputs[0].default_value = 0.45
    base = bsdf.inputs['Base Color'].links[0].from_socket
    nt.links.new(base, mult.inputs[1])
    nt.links.new(ramp2.outputs['Color'], mult.inputs[2])
    nt.links.new(mult.outputs['Color'], bsdf.inputs['Base Color'])
    return m


def mat_art(path):
    m = bpy.data.materials.new(os.path.basename(path))
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']
    img = nt.nodes.new('ShaderNodeTexImage')
    img.image = bpy.data.images.load(path)
    nt.links.new(img.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.5
    return m


# ── Geometrie-Helfer ─────────────────────────────────────

def box(name, loc, dims, mat):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.active_object
    o.name = name
    o.dimensions = dims
    bpy.ops.object.transform_apply(scale=True)
    if mat:
        o.data.materials.append(mat)
    return o


def wall_with_door(prefix, wall, along, wall_len, wall_h, wall_pos, T, mat,
                   frame_m, glow_m, glow_strength=1.5):
    """Wand mit Türöffnung. wall: 'n'/'s' (laengs x) oder 'w'/'e' (laengs y).
    wall_pos: fixe Achsposition der Wandmitte (y bzw. x)."""
    a0, a1 = along - DOOR_W / 2, along + DOOR_W / 2
    lo, hi = -wall_len / 2, wall_len / 2
    segs = [(lo, a0), (a1, hi)]
    for i, (a, b) in enumerate(segs):
        mid, ln = (a + b) / 2, b - a
        if ln <= 0.01:
            continue
        if wall in ('n', 's'):
            box(prefix + '-seg%d' % i, (mid, wall_pos, wall_h / 2), (ln, T, wall_h), mat)
        else:
            box(prefix + '-seg%d' % i, (wall_pos, mid, wall_h / 2), (T, ln, wall_h), mat)
    # Sturz über der Tür
    if wall in ('n', 's'):
        box(prefix + '-sturz', (along, wall_pos, (DOOR_H + wall_h) / 2),
            (DOOR_W, T, wall_h - DOOR_H), mat)
    else:
        box(prefix + '-sturz', (wall_pos, along, (DOOR_H + wall_h) / 2),
            (T, DOOR_W, wall_h - DOOR_H), mat)
    # Laibung (Zargen) + Licht dahinter
    fr = 0.06
    if wall in ('n', 's'):
        face = wall_pos + (T / 2 if wall == 'n' else -T / 2)
        box(prefix + '-zarge-l', (a0, face, DOOR_H / 2), (fr, 0.1, DOOR_H), frame_m)
        box(prefix + '-zarge-r', (a1, face, DOOR_H / 2), (fr, 0.1, DOOR_H), frame_m)
        box(prefix + '-zarge-o', (along, face, DOOR_H), (DOOR_W + fr, 0.1, fr), frame_m)
        depth = wall_pos + (0.55 if wall == 'n' else -0.55)
        glow = mat_emission(prefix + '-licht', glow_m, glow_strength)
        bpy.ops.mesh.primitive_plane_add(size=1, location=(along, depth, DOOR_H / 2),
                                         rotation=(math.pi / 2, 0, 0))
        p = bpy.context.active_object
        p.dimensions = (DOOR_W + 0.3, DOOR_H + 0.2, 1)
    else:
        face = wall_pos + (T / 2 if wall == 'w' else -T / 2)
        box(prefix + '-zarge-l', (face, a0, DOOR_H / 2), (0.1, fr, DOOR_H), frame_m)
        box(prefix + '-zarge-r', (face, a1, DOOR_H / 2), (0.1, fr, DOOR_H), frame_m)
        box(prefix + '-zarge-o', (face, along, DOOR_H), (0.1, DOOR_W + fr, fr), frame_m)
        depth = wall_pos + (0.55 if wall == 'w' else -0.55)
        glow = mat_emission(prefix + '-licht', glow_m, glow_strength)
        bpy.ops.mesh.primitive_plane_add(size=1, location=(depth, along, DOOR_H / 2),
                                         rotation=(math.pi / 2, 0, math.pi / 2))
        p = bpy.context.active_object
        p.dimensions = (DOOR_W + 0.3, DOOR_H + 0.2, 1)
    bpy.ops.object.transform_apply(scale=True)
    p.data.materials.append(glow)


def art_plane(name, img_path, wall, along, w, h):
    m = mat_art(img_path)
    bpy.ops.mesh.primitive_plane_add(size=1)
    o = bpy.context.active_object
    o.name = 'werk-' + name
    o.dimensions = (w, h, 1)
    D2 = HALL_D / 2
    if wall == 'n':
        o.location = (along, -D2 + 0.065, HANG)
        o.rotation_euler = (math.pi / 2, 0, math.pi)
    elif wall == 's':
        o.location = (along, D2 - 0.065, HANG)
        o.rotation_euler = (math.pi / 2, 0, 0)
    else:  # 'e'
        o.location = (HALL_W / 2 - 0.065, along, HANG)
        o.rotation_euler = (math.pi / 2, 0, -math.pi / 2)
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(m)
    return o


def load_font(path):
    try:
        return bpy.data.fonts.load(path)
    except Exception:  # noqa: BLE001
        return None


FONT_TITLE = None
FONT_META = None


def text_obj(body, loc, rot, size, mat, font=None, extrude=0.001):
    bpy.ops.object.text_add(location=loc, rotation=rot)
    t = bpy.context.active_object
    t.data.body = body
    t.data.align_x = 'CENTER'
    t.data.align_y = 'CENTER'
    t.data.size = size
    t.data.extrude = extrude
    if font:
        t.data.font = font
    t.data.materials.append(mat)
    return t


def add_label(wk, plaque_m, ink_m):
    """Lesbare Wandplakette rechts neben dem Werk (Betrachtersicht)."""
    wall, along, w = wk['wall'], wk['along'], wk['w']
    D2, W2 = HALL_D / 2, HALL_W / 2
    off = w / 2 + 0.10 + PLAQ_W / 2
    if wall == 'n':
        pos, dims, rot = (along - off, -D2 + 0.02, PLAQ_Z), (PLAQ_W, 0.015, PLAQ_H), (math.pi / 2, 0, math.pi)
        tpos = lambda dz: (pos[0], -D2 + 0.032, PLAQ_Z + dz)  # noqa: E731
    elif wall == 's':
        pos, dims, rot = (along + off, D2 - 0.02, PLAQ_Z), (PLAQ_W, 0.015, PLAQ_H), (math.pi / 2, 0, 0)
        tpos = lambda dz: (pos[0], D2 - 0.032, PLAQ_Z + dz)  # noqa: E731
    else:  # 'e'
        pos, dims, rot = (W2 - 0.02, along - off, PLAQ_Z), (0.015, PLAQ_W, PLAQ_H), (math.pi / 2, 0, -math.pi / 2)
        tpos = lambda dz: (W2 - 0.032, pos[1], PLAQ_Z + dz)  # noqa: E731
    box('plakette-' + wk['slug'], pos, dims, plaque_m)
    text_obj(wk['title'], tpos(0.045), rot, 0.042, ink_m, FONT_TITLE)
    text_obj(wk['meta'], tpos(-0.052), rot, 0.021, ink_m, FONT_META)


def add_werke(frame_m, plaque_m, ink_m):
    D2, W2 = HALL_D / 2, HALL_W / 2
    for wk in WERKE:
        wall, along, w, h = wk['wall'], wk['along'], wk['w'], wk['h']
        t = 0.05
        if wall in ('n', 's'):
            y = -D2 + t / 2 + 0.01 if wall == 'n' else D2 - t / 2 - 0.01
            box('rahmen-' + wk['slug'], (along, y, HANG), (w + 0.09, t, h + 0.09), frame_m)
        else:
            box('rahmen-' + wk['slug'], (W2 - t / 2 - 0.01, along, HANG), (t, w + 0.09, h + 0.09), frame_m)
        art_plane(wk['slug'], os.path.join(ART_DIR, wk['img']), wall, along, w, h)
        add_label(wk, plaque_m, ink_m)


def add_walltext(ink_m, x=-4.0, y=None, z=1.85, sub=1.58):
    rot = (math.pi / 2, 0, math.pi)
    if y is None:
        y = -HALL_D / 2 + 0.02
    text_obj('SLICED GOLF', (x, y, z), rot, 0.3, ink_m, FONT_META, 0.002)
    text_obj('Ralf Lehmann', (x, y, sub), rot, 0.13, ink_m, FONT_META, 0.002)


# ── White Cube ───────────────────────────────────────────

def build_white_cube():
    wall_m = mat_principled('WandWeiss', (0.93, 0.93, 0.92), 0.9)
    ceil_m = mat_principled('DeckeWeiss', (0.95, 0.95, 0.94), 0.9)
    mullion = mat_principled('Sprossen', (0.28, 0.28, 0.29), 0.5)
    floor_m = mat_principled('BodenWeiss', (0.62, 0.615, 0.60), 0.42)
    glow = mat_emission('Lichtdecke', (1.0, 1.0, 1.0), 1.4)
    frame_m = mat_principled('Rahmen', (0.07, 0.07, 0.07), 0.5)
    plaque_m = mat_principled('Plakette', (0.97, 0.97, 0.96), 0.6)
    ink_m = mat_principled('Schrift', (0.05, 0.05, 0.05), 0.6)

    W2, D2, H = HALL_W / 2, HALL_D / 2, HALL_H
    T = 0.12

    box('boden', (0, 0, -0.05), (HALL_W, HALL_D, 0.1), floor_m)
    for tag, loc, dims in (
            ('n', (0, -D2 - T / 2, H / 2), (HALL_W + 2 * T, T, H)),
            ('s', (0, D2 + T / 2, H / 2), (HALL_W + 2 * T, T, H)),
            ('e', (W2 + T / 2, 0, H / 2), (T, HALL_D, H))):
        box('wand-' + tag, loc, dims, wall_m)

    # Westwand: Tür zum Foyer (y=-2) und Tür zum Garten (y=+2)
    Tm = T / 2
    wall_with_door('tuer-foyer', 'w', -2.0, HALL_D, H, -W2 - Tm, T, wall_m,
                   mullion, (1.0, 0.95, 0.88), 1.6)
    wall_with_door('tuer-garten', 'w', 2.0, HALL_D, H, -W2 - Tm, T, wall_m,
                   mullion, (0.85, 0.95, 1.0), 2.5)
    # Wandstücke zwischen/um die Türen
    for i, (a, b) in enumerate([(-D2, -2.0 - DOOR_W / 2),
                                (-2.0 + DOOR_W / 2, 2.0 - DOOR_W / 2),
                                (2.0 + DOOR_W / 2, D2)]):
        if b - a > 0.01:
            box('wand-w-%d' % i, (-W2 - Tm, (a + b) / 2, H / 2), (T, b - a, H), wall_m)

    box('decke-n', (0, -3.62, H + 0.05), (HALL_W + 2 * T, 1.24, 0.1), ceil_m)
    box('decke-s', (0, 3.62, H + 0.05), (HALL_W + 2 * T, 1.24, 0.1), ceil_m)

    # Tonnengewölbe-Lichtdecke (Radius 7.8, Scheitel 4.0, Auflager 3.4)
    R, ZC, HALF = 7.8, -3.8, math.radians(22.6)
    N = 9
    for i in range(N):
        t = -HALF + (i + 0.5) * (2 * HALF / N)
        y, z = R * math.sin(t), ZC + R * math.cos(t)
        seg = box('lichtdecke', (0, y, z), (HALL_W + 2 * T, 0.75, 0.02), glow)
        seg.rotation_euler = (t, 0, 0)
    for i in range(N + 1):
        t = -HALF + i * (2 * HALF / N)
        y, z = R * math.sin(t), ZC + R * math.cos(t)
        bar = box('profil', (0, y, z - 0.012), (HALL_W + 2 * T, 0.055, 0.05), mullion)
        bar.rotation_euler = (t, 0, 0)
    for x in (-4.0, 0.0, 4.0):
        for i in range(N):
            t = -HALF + (i + 0.5) * (2 * HALF / N)
            y, z = R * math.sin(t), ZC + R * math.cos(t)
            arc = box('bogen', (x, y, z - 0.015), (0.055, 0.75, 0.035), mullion)
            arc.rotation_euler = (t, 0, 0)

    add_werke(frame_m, plaque_m, ink_m)
    add_walltext(ink_m)


def lights_white_cube():
    bpy.ops.object.light_add(type='AREA', location=(0, 0, 3.65))
    key = bpy.context.active_object
    key.data.energy = 480
    key.data.color = (1.0, 1.0, 1.0)
    key.data.size = 5.0
    for y in (-2.0, 2.0):
        bpy.ops.object.light_add(type='POINT', location=(0, y, 2.8))
        l = bpy.context.active_object
        l.data.energy = 130
        l.data.color = (1.0, 1.0, 1.0)
        l.data.shadow_soft_size = 0.2

    world = bpy.data.worlds.new('Welt')
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.9, 0.9, 0.9, 1)
    bg.inputs['Strength'].default_value = 0.3
    bpy.context.scene.world = world


# ── Salon ────────────────────────────────────────────────

def build_salon():
    sage = mat_principled('Salbeigruen', (0.283, 0.306, 0.235), 0.85)
    wainscot = mat_principled('Vertaefelung', (0.153, 0.176, 0.129), 0.7)
    cream = mat_principled('Stuck', (0.75, 0.71, 0.62), 0.55)
    wood = mat_principled('Dunkelholz', (0.075, 0.045, 0.026), 0.45)
    gold = mat_principled('Messing', (0.35, 0.24, 0.09), 0.35, 0.85)
    white = mat_principled('Decke', (0.82, 0.79, 0.72), 0.9)
    plaque_m = mat_principled('Plakette', (0.93, 0.92, 0.89), 0.6)
    ink_m = mat_principled('Schrift', (0.05, 0.045, 0.04), 0.6)
    sky = mat_emission('Himmel', (0.85, 0.92, 1.0), 3.5)
    flame = mat_emission('Kerze', (1.0, 0.72, 0.35), 9.0)
    floor_m = mat_floor_dark()
    frame_m = mat_principled('Rahmen', (0.16, 0.11, 0.05), 0.4, 0.3)

    W2, D2, H = HALL_W / 2, HALL_D / 2, HALL_H
    T = 0.12

    box('boden', (0, 0, -0.05), (HALL_W, HALL_D, 0.1), floor_m)
    box('decke', (0, 0, H + 0.05), (HALL_W + 2 * T, HALL_D + 2 * T, 0.1), white)

    box('wand-n', (0, -D2 - T / 2, H / 2), (HALL_W + 2 * T, T, H), sage)
    box('wand-s', (0, D2 + T / 2, H / 2), (HALL_W + 2 * T, T, H), sage)
    box('wand-e', (W2 + T / 2, 0, H / 2), (T, HALL_D, H), sage)

    # Westwand: zwei Fenster, dazwischen die Tür zum Foyer
    wb = WINDOWS[0][1]
    door_lo, door_hi = -DOOR_W / 2, DOOR_W / 2
    segs = [(-D2, WINDOWS[0][0] - wb / 2),
            (WINDOWS[0][0] + wb / 2, door_lo),
            (door_hi, WINDOWS[1][0] - wb / 2),
            (WINDOWS[1][0] + wb / 2, D2)]
    for i, (a, b) in enumerate(segs):
        if b - a > 0.01:
            box('west-seg%d' % i, (-W2 - T / 2, (a + b) / 2, H / 2), (T, b - a, H), sage)
    # Türsturz + Laibung + warmes Licht dahinter
    box('tuer-sturz', (-W2 - T / 2, 0, (DOOR_H + H) / 2), (T, DOOR_W, H - DOOR_H), sage)
    box('tuer-zarge-l', (-W2 + 0.01, door_lo, DOOR_H / 2), (0.06, 0.05, DOOR_H), wood)
    box('tuer-zarge-r', (-W2 + 0.01, door_hi, DOOR_H / 2), (0.06, 0.05, DOOR_H), wood)
    box('tuer-zarge-o', (-W2 + 0.01, 0, DOOR_H), (0.06, DOOR_W + 0.05, 0.05), wood)
    glow_door = mat_emission('tuer-licht', (1.0, 0.88, 0.68), 1.8)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-W2 - 0.55, 0, DOOR_H / 2),
                                     rotation=(math.pi / 2, 0, math.pi / 2))
    p = bpy.context.active_object
    p.dimensions = (DOOR_W + 0.3, DOOR_H + 0.2, 1)
    bpy.ops.object.transform_apply(scale=True)
    p.data.materials.append(glow_door)

    for yc, b, u, o in WINDOWS:
        box('sturz', (-W2 - T / 2, yc, (o + H) / 2), (T, b, H - o), sage)
        box('bruestung', (-W2 - T / 2, yc, u / 2), (T, b, u), sage)
        fr = 0.05
        box('f-rahmen-l', (-W2 + 0.01, yc - b / 2, (u + o) / 2), (0.06, fr, o - u), cream)
        box('f-rahmen-r', (-W2 + 0.01, yc + b / 2, (u + o) / 2), (0.06, fr, o - u), cream)
        box('f-rahmen-o', (-W2 + 0.01, yc, o), (0.06, b + fr, fr), cream)
        box('f-rahmen-u', (-W2 + 0.01, yc, u), (0.06, b + fr, fr), cream)
        box('f-sprosse-v', (-W2 + 0.005, yc, (u + o) / 2), (0.03, 0.025, o - u), cream)
        box('f-sprosse-h', (-W2 + 0.005, yc, (u + o) / 2), (0.03, b, 0.025), cream)
        box('fensterbank', (-W2 + 0.03, yc, u - 0.02), (0.14, b + 0.1, 0.04), cream)
        bpy.ops.mesh.primitive_plane_add(size=1, location=(-W2 - 0.35, yc, (u + o) / 2),
                                         rotation=(math.pi / 2, 0, math.pi / 2))
        p = bpy.context.active_object
        p.name = 'himmel'
        p.dimensions = (b + 0.4, o - u + 0.4, 1)
        bpy.ops.object.transform_apply(scale=True)
        p.data.materials.append(sky)

    for tag, (cx, cy, dx, dy) in {
        'n': (0, -D2 + 0.012, HALL_W, 0.024),
        's': (0, D2 - 0.012, HALL_W, 0.024),
        'e': (W2 - 0.012, 0, 0.024, HALL_D),
    }.items():
        box('vert-' + tag, (cx, cy, 0.475), (dx, dy, 0.95), wainscot)
        box('leiste-' + tag, (cx, cy, 0.96), (dx * 1.02 + 0.02, dy * 1.02 + 0.02, 0.035), wood)
        box('sockel-' + tag, (cx, cy, 0.06), (dx * 1.02 + 0.02, dy * 1.02 + 0.02, 0.12), wood)

    def panel(wall, center, pw, ph=1.8, pz=2.1):
        sw, sd = 0.045, 0.015
        if wall in ('n', 's'):
            y = -D2 + sd / 2 if wall == 'n' else D2 - sd / 2
            for (x, yy, z) in [(center, y, pz - ph / 2), (center, y, pz + ph / 2)]:
                box('stuck', (x, yy, z), (pw + sw, sd, sw), cream)
            for (x, yy, z) in [(center - pw / 2, y, pz), (center + pw / 2, y, pz)]:
                box('stuck', (x, yy, z), (sw, sd, ph), cream)
        else:
            x = W2 - sd / 2
            for (yy, z) in [(center, pz - ph / 2), (center, pz + ph / 2)]:
                box('stuck', (x, yy, z), (sd, pw + sw, sw), cream)
            for (yy, z) in [(center - pw / 2, pz), (center + pw / 2, pz)]:
                box('stuck', (x, yy, z), (sd, sw, ph), cream)

    for wall in ('n', 's'):
        for c in (-4.5, -1.5, 1.5, 4.5):
            panel(wall, c, 2.4)
    for c in (-2.6, 0.0, 2.6):
        panel('e', c, 2.0)

    for i in range(5):
        x = -W2 + i * (HALL_W / 4)
        box('balken-x', (x, 0, H - 0.075), (0.14, HALL_D, 0.15), cream)
    for j in range(4):
        y = -D2 + j * (HALL_D / 3)
        box('balken-y', (0, y, H - 0.075), (HALL_W, 0.14, 0.15), cream)

    box('kette', (0, 0, H - 0.5), (0.02, 0.02, 1.0), gold)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.42, minor_radius=0.03,
                                     location=(0, 0, H - 0.95))
    torus = bpy.context.active_object
    torus.name = 'leuchter-ring'
    torus.data.materials.append(gold)
    wax = mat_principled('Kerzenwachs', (0.9, 0.87, 0.8), 0.5)
    for k in range(6):
        a = k * math.pi / 3
        cx, cy = 0.42 * math.cos(a), 0.42 * math.sin(a)
        box('kerze', (cx, cy, H - 0.86), (0.035, 0.035, 0.16), wax)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.022, location=(cx, cy, H - 0.765))
        f = bpy.context.active_object
        f.name = 'flamme'
        f.data.materials.append(flame)

    add_werke(frame_m, plaque_m, ink_m)
    add_walltext(ink_m)


def lights_salon():
    def point(loc, energy, color):
        bpy.ops.object.light_add(type='POINT', location=loc)
        l = bpy.context.active_object
        l.data.energy = energy
        l.data.color = color
        l.data.shadow_soft_size = 0.15

    def area(loc, rot, energy, color, size):
        bpy.ops.object.light_add(type='AREA', location=loc, rotation=rot)
        l = bpy.context.active_object
        l.data.energy = energy
        l.data.color = color
        l.data.size = size

    point((0, 0, HALL_H - 1.0), 320, (1.0, 0.8, 0.58))
    point((0, -2.0, 2.9), 90, (1.0, 0.94, 0.85))
    point((0, 2.0, 2.9), 90, (1.0, 0.94, 0.85))
    for yc, *_ in WINDOWS:
        area((-HALL_W / 2 - 0.9, yc, 2.0), (0, -math.pi / 2, 0), 500, (0.88, 0.94, 1.0), 1.8)

    world = bpy.data.worlds.new('Welt')
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.32, 0.33, 0.35, 1)
    bg.inputs['Strength'].default_value = 0.35
    bpy.context.scene.world = world


# ── Foyer ────────────────────────────────────────────────

def build_foyer():
    wall_m = mat_principled('FoyerWand', (0.55, 0.53, 0.49), 0.85)
    ceil_m = mat_principled('FoyerDecke', (0.88, 0.86, 0.82), 0.9)
    floor_m = mat_noise('Eiche', (0.20, 0.13, 0.07), (0.38, 0.27, 0.16), 2.5, 0.45, 0.15)
    wood = mat_principled('FoyerHolz', (0.16, 0.10, 0.055), 0.4)
    ink_m = mat_principled('FoyerSchrift', (0.08, 0.075, 0.07), 0.6)
    glow_portal = mat_emission('PortalLicht', (0.9, 0.95, 1.0), 3.0)

    W2, D2, H = FOY_W / 2, FOY_D / 2, FOY_H
    T = 0.12

    box('boden', (0, 0, -0.05), (FOY_W, FOY_D, 0.1), floor_m)
    box('decke', (0, 0, H + 0.05), (FOY_W + 2 * T, FOY_D + 2 * T, 0.1), ceil_m)
    box('wand-e', (W2 + T / 2, 0, H / 2), (T, FOY_D, H), wall_m)

    # Nordwand: Tür zum Salon (x=0)
    wall_with_door('tuer-salon', 'n', 0.0, FOY_W, H, -D2 - T / 2, T, wall_m,
                   wood, (1.0, 0.88, 0.68), 1.6)
    # Westwand: Tür zum White Cube (y=0)
    wall_with_door('tuer-wc', 'w', 0.0, FOY_D, H, -W2 - T / 2, T, wall_m,
                   wood, (1.0, 1.0, 1.0), 1.6)

    # Südwand: Eingangsportal (verglast, helles Aussenlicht)
    box('wand-s-l', ((-W2 - 0.9) / 2 - 0.0, D2 + T / 2, H / 2), (W2 - 0.9 + W2 + T, T, H), wall_m)
    box('wand-s-r', ((W2 + 0.9) / 2 + 0.0, D2 + T / 2, H / 2), (W2 - 0.9 + T, T, H), wall_m)
    box('portal-sturz', (0, D2 + T / 2, (2.4 + H) / 2), (1.8, T, H - 2.4), wall_m)
    box('portal-rahmen-l', (-0.9, D2, 1.2), (0.08, 0.16, 2.4), wood)
    box('portal-rahmen-r', (0.9, D2, 1.2), (0.08, 0.16, 2.4), wood)
    box('portal-rahmen-o', (0, D2, 2.4), (1.88, 0.16, 0.08), wood)
    box('portal-mitte', (0, D2, 1.2), (0.05, 0.12, 2.4), wood)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, D2 + 0.3, 1.2),
                                     rotation=(math.pi / 2, 0, math.pi))
    p = bpy.context.active_object
    p.dimensions = (1.8, 2.4, 1)
    bpy.ops.object.transform_apply(scale=True)
    p.data.materials.append(glow_portal)

    # Wandschrift über der Salon-Tür (Nordwand)
    add_walltext(ink_m, x=0.0, y=-D2 + 0.02, z=2.75, sub=2.48)

    # Bank
    box('bank-sitz', (1.6, 1.6, 0.42), (1.6, 0.45, 0.08), wood)
    for dx in (-0.65, 0.65):
        for dy in (-0.15, 0.15):
            box('bank-bein', (1.6 + dx, 1.6 + dy, 0.19), (0.06, 0.06, 0.38), wood)

    # Pendelleuchten
    for x in (-1.5, 1.5):
        box('pendel-kabel', (x, 0.5, H - 0.35), (0.015, 0.015, 0.7), wood)
        bpy.ops.mesh.primitive_cone_add(radius1=0.22, radius2=0.05, depth=0.25,
                                        location=(x, 0.5, H - 0.78))
        shade = bpy.context.active_object
        shade.data.materials.append(wood)


def lights_foyer():
    def point(loc, energy, color, size=0.12):
        bpy.ops.object.light_add(type='POINT', location=loc)
        l = bpy.context.active_object
        l.data.energy = energy
        l.data.color = color
        l.data.shadow_soft_size = size

    point((-1.5, 0.5, FOY_H - 0.95), 130, (1.0, 0.86, 0.66))
    point((1.5, 0.5, FOY_H - 0.95), 130, (1.0, 0.86, 0.66))
    point((0, -1.5, 2.5), 60, (1.0, 0.94, 0.85))

    world = bpy.data.worlds.new('Welt')
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.4, 0.4, 0.42, 1)
    bg.inputs['Strength'].default_value = 0.4
    bpy.context.scene.world = world


# ── Garten ───────────────────────────────────────────────

def build_garten():
    grass = mat_noise('Rasen', (0.02, 0.05, 0.012), (0.10, 0.20, 0.05), 4.0, 1.0, 0.35)
    hedge = mat_noise('Hecke', (0.012, 0.045, 0.012), (0.05, 0.13, 0.035), 6.0, 1.0, 0.6)
    leaf = mat_noise('Laub', (0.02, 0.07, 0.02), (0.09, 0.22, 0.06), 3.0, 1.0, 0.4)
    trunk_m = mat_principled('Stamm', (0.10, 0.06, 0.035), 0.9)
    stone = mat_principled('Stein', (0.55, 0.54, 0.50), 0.85)
    white = mat_principled('Sockel', (0.92, 0.92, 0.90), 0.6)
    shell = mat_principled('BallSchale', (0.96, 0.96, 0.95), 0.35)
    core1 = mat_principled('KernRot', (0.60, 0.15, 0.18), 0.5)
    core2 = mat_principled('KernBlau', (0.15, 0.25, 0.60), 0.5)
    core3 = mat_principled('KernGelb', (0.75, 0.50, 0.05), 0.5)
    glow_exit = mat_emission('PortalWeiss', (1.0, 1.0, 1.0), 2.2)

    G2 = GAR / 2

    box('rasen', (0, 0, -0.06), (GAR + 4, GAR + 4, 0.12), grass)

    # Hecken (ragen über das Sichtfeld hinaus)
    for tag, loc, dims in (
            ('n', (0, -G2 - 0.3, 1.1), (GAR + 2, 0.6, 2.2)),
            ('s', (0, G2 + 0.3, 1.1), (GAR + 2, 0.6, 2.2)),
            ('w', (-G2 - 0.3, 0, 1.1), (0.6, GAR + 2, 2.2)),
            ('e', (G2 + 0.3, 0, 1.1), (0.6, GAR + 2, 2.2))):
        box('hecke-' + tag, loc, dims, hedge)

    # Ausgang zum White Cube (Blender y=+G2, helles Portal in der Hecke)
    box('portal-l', (-0.75, G2 + 0.28, 1.15), (0.16, 0.66, 2.3), white)
    box('portal-r', (0.75, G2 + 0.28, 1.15), (0.16, 0.66, 2.3), white)
    box('portal-o', (0, G2 + 0.28, 2.34), (1.66, 0.66, 0.16), white)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, G2 + 0.7, 1.15),
                                     rotation=(math.pi / 2, 0, math.pi))
    p = bpy.context.active_object
    p.dimensions = (1.34, 2.3, 1)
    bpy.ops.object.transform_apply(scale=True)
    p.data.materials.append(glow_exit)

    # Steinweg vom Portal zur Skulptur
    for i in range(6):
        box('weg', (0, 4.6 - i * 1.35, 0.015), (0.9, 0.7, 0.03), stone)

    # Skulptur: riesiger aufgeschnittener Golfball auf Sockel
    box('sockel', (0, -3, 0.5), (0.55, 0.55, 1.0), white)
    layers = [(shell, 0.45, 0.04), (core1, 0.385, 0.09),
              (core2, 0.31, 0.14), (core3, 0.20, 0.19)]
    for mat, r, cut in layers:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=48, ring_count=32,
                                             location=(0, -3, 1.55))
        ball = bpy.context.active_object
        ball.data.materials.append(mat)
        bpy.ops.object.shade_smooth()
        # Schnittfläche zeigt auf den Weg (Blickrichtung vom Portal, +y)
        box('schnitt', (0, -3 + cut + 1.0, 1.55), (2.0, 2.0, 2.0), None)
        cutter = bpy.context.active_object
        mod = ball.modifiers.new('schnitt', 'BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = cutter
        bpy.context.view_layer.objects.active = ball
        bpy.ops.object.modifier_apply(modifier='schnitt')
        bpy.data.objects.remove(cutter)

    # Bäume
    for tx, ty in ((-4.0, 2.0), (4.0, -1.5), (3.5, 3.5)):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.11, depth=1.9, location=(tx, ty, 0.95))
        trunk = bpy.context.active_object
        trunk.data.materials.append(trunk_m)
        for (dx, dy, dz, r) in ((0, 0, 2.4, 1.05), (0.5, 0.3, 2.0, 0.65), (-0.4, -0.3, 2.1, 0.6)):
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r,
                                                  location=(tx + dx, ty + dy, dz))
            crown = bpy.context.active_object
            crown.data.materials.append(leaf)
            bpy.ops.object.shade_smooth()

    # Steinbank
    box('steinbank', (2.6, 1.5, 0.22), (1.4, 0.45, 0.44), stone)

    # Himmel (Nishita) + Sonne
    world = bpy.data.worlds.new('Himmel')
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes['Background']
    sky = nt.nodes.new('ShaderNodeTexSky')
    sky.sky_type = 'MULTIPLE_SCATTERING'   # Blender 5.0 (ehemals Nishita)
    sky.sun_elevation = math.radians(38)
    sky.sun_rotation = math.radians(65)
    sky.altitude = 0.2
    nt.links.new(sky.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 0.5
    bpy.context.scene.world = world

    bpy.ops.object.light_add(type='SUN', rotation=(math.radians(52), 0, math.radians(65)))
    sun = bpy.context.active_object
    sun.data.energy = 1.5
    sun.data.angle = 0.02


def lights_garten():
    pass  # Sonne und Himmel werden in build_garten gesetzt


# ── Kamera & Render ──────────────────────────────────────

def make_camera():
    bpy.ops.object.camera_add()
    cam = bpy.context.active_object
    cam.data.type = 'PANO'
    # Blender 5.0: panorama_type liegt im Core; aeltere Versionen unter .cycles
    if hasattr(cam.data, 'panorama_type'):
        cam.data.panorama_type = 'EQUIRECTANGULAR'
    else:
        cam.data.cycles.panorama_type = 'EQUIRECTANGULAR'
    cam.rotation_euler = (math.pi / 2, 0, math.pi)   # Bildmitte = -Y (Nord)
    bpy.context.scene.camera = cam
    return cam


def configure(scene, width, height, samples):
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL'
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = 'GPU'
        print('Cycles-Geraet: METAL GPU')
    except Exception as exc:  # noqa: BLE001
        print('GPU nicht verfuegbar, CPU-Fallback:', exc)
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.image_settings.file_format = 'JPEG'
    scene.render.image_settings.quality = 90
    try:
        scene.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass


THEMES = {
    'foyer': (build_foyer, lights_foyer),
    'white-cube': (build_white_cube, lights_white_cube),
    'salon': (build_salon, lights_salon),
    'garten': (build_garten, lights_garten),
}


def main():
    global FONT_TITLE, FONT_META
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    preview = '--preview' in argv
    only = int(argv[argv.index('--only') + 1]) if '--only' in argv else None
    theme = argv[argv.index('--theme') + 1] if '--theme' in argv else 'all'
    names = list(THEMES) if theme == 'all' else [theme]

    for name in names:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        # Fonts erst nach dem Factory-Reset laden — sonst haengen sie an
        # entfernten Datenbloecken.
        FONT_TITLE = load_font('/System/Library/Fonts/Supplemental/Georgia Italic.ttf')
        FONT_META = load_font('/System/Library/Fonts/Helvetica.ttc')
        scene = bpy.context.scene
        build, lights = THEMES[name]
        build()
        lights()
        cam = make_camera()
        stations = STATIONS[name]

        if preview:
            configure(scene, 2048, 1024, 64)
            i = only if only is not None else 0
            scene.render.filepath = '/tmp/%s-preview.jpg' % name
            cam.location = (-stations[i][0], stations[i][1], EYE)   # x gespiegelt
            bpy.ops.render.render(write_still=True)
            print('PREVIEW:', scene.render.filepath)
            continue

        configure(scene, 4096, 2048, 256)
        todo = range(len(stations)) if only is None else [only]
        for i in todo:
            cam.location = (-stations[i][0], stations[i][1], EYE)   # x gespiegelt
            scene.render.filepath = os.path.join(OUT_DIR, '%s-st%d.jpg' % (name, i))
            bpy.ops.render.render(write_still=True)
            print('FERTIG:', scene.render.filepath)


main()
