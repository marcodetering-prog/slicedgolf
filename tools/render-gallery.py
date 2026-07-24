"""SLICED GOLF — Rendert alle Panoramen der virtuellen Galerie.

Zwei Szenen mit identischem Grundriss (Weltmodell in js/galerie-pano.js):

  white-cube-*  Weisse Galerie: Foyer, Haupthalle mit Tonnengewölbe-
                Lichtdecke, Kabinett — verbunden über drei Türen
  salon-*       Klassischer Salon: Foyer, Halle mit Stuckrahmen,
                Vertäfelung, Kassettendecke, Kronleuchter und
                Oberlicht, Kabinett — gleicher Grundriss
  garten        Geteilter Skulpturengarten (Rasen, Hecken, Bäume,
                Himmel, aufgeschnittene Golfball-Skulptur), Portal
                zurück in die Halle der jeweiligen Szene

Jedes Werk bekommt eine lesbare Wandplakette (Titel + Opus-Zeile).

Aufruf:
  blender -b -P tools/render-gallery.py -- \
      [--theme white-cube-halle|salon-halle|...|all] [--only N] [--preview]

Achsen: Blender x = -three-x (gespiegelt, wie die Original-Panoramen),
Blender y = three z (Nordwand bei y=-D/2), Blender z = Höhe. Bildmitte
der Equirect = -Y. Werkspositionen sind daher x-negiert zum Weltmodell.
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

HALL_W, HALL_D, HALL_H = 12.0, 8.0, 3.5   # Haupthalle
KAB_W, KAB_D, KAB_H = 8.0, 6.0, 3.2       # Kabinett
FOY_W, FOY_D, FOY_H = 8.0, 6.0, 3.2       # Foyer
GAR = 12.0                                # Garten (Hecken)

DOOR_W, DOOR_H = 1.0, 2.2
PLAQ_W, PLAQ_H, PLAQ_Z = 0.44, 0.26, 1.30

# Stationen in three-Koordinaten (x wird beim Rendern gespiegelt)
HALL_ST = [(0.0, 2.4), (0.0, 0.0), (-2.4, -1.9), (2.4, -1.9),
           (2.4, 1.9), (-2.4, 1.9), (-4.1, 0.0),
           (4.3, -2.0), (4.3, 0.0), (4.3, 2.0)]
FOY_ST = [(0.0, 1.2), (2.4, 0.0)]
KAB_ST = [(0.0, 1.0), (-1.8, -0.8), (2.6, 0.0)]
GAR_ST = [(0.0, 4.2), (0.0, -0.5)]

# Werke der Halle: Wand 'n'/'s'/'e', 'along' in Blender-x
HALL_WERKE = [
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

# Werke des Kabinetts
KAB_WERKE = [
    dict(slug='great-balls-of-fire', img='great-balls-of-fire.jpg', wall='n',
         along=0.0, w=0.6, h=0.8, title='Great Balls of Fire',
         meta='Opus 18/99 · 80 × 60 cm · 2024'),
    dict(slug='ballhaelften-1', img='makro-ballhaelften-01.jpg', wall='e',
         along=0.0, w=0.9, h=0.675, title='Ballhälften I', meta='Makrofotografie'),
    dict(slug='ballhaelften-2', img='makro-ballhaelften-02.jpg', wall='s',
         along=1.5, w=0.9, h=0.675, title='Ballhälften II', meta='Makrofotografie'),
    dict(slug='ballhaelften-3', img='makro-ballhaelften-03.jpg', wall='s',
         along=-1.5, w=0.9, h=0.675, title='Ballhälften III', meta='Makrofotografie'),
]


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
    """Zweifarbige Noise-Textur (Böden, Rasen, Hecke)."""
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
    bsdf = nt.nodes['Principled BSDF']
    wave = nt.nodes.new('ShaderNodeTexWave')
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'X'
    wave.inputs['Scale'].default_value = 5.0
    wave.inputs['Distortion'].default_value = 2.5
    wave.inputs['Detail'].default_value = 3.0
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


def wall_x(name, y_center, room_w, room_h, T, mat, openings=()):
    """Wand entlang x (Nord/Süd) mit Rechteck-Öffnungen
    [(mitte, breite, unten, oben)]."""
    box(name, (0, y_center, room_h / 2), (room_w + 2 * T, T, room_h), mat)
    if not openings:
        return
    bpy.context.view_layer.objects.active = bpy.data.objects[name]
    wall = bpy.data.objects[name]
    for i, (mitte, breite, unten, oben) in enumerate(openings):
        h = oben - unten
        cutter = box(name + '-cut%d' % i, (mitte, y_center, unten + h / 2),
                     (breite, T * 3, h), None)
        mod = wall.modifiers.new('cut%d' % i, 'BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = cutter
        bpy.context.view_layer.objects.active = wall
        bpy.ops.object.modifier_apply(modifier='cut%d' % i)
        bpy.data.objects.remove(cutter)


def wall_y(name, x_center, room_d, room_h, T, mat, openings=()):
    """Wand entlang y (West/Ost) mit Rechteck-Öffnungen."""
    box(name, (x_center, 0, room_h / 2), (T, room_d, room_h), mat)
    if not openings:
        return
    wall = bpy.data.objects[name]
    for i, (mitte, breite, unten, oben) in enumerate(openings):
        h = oben - unten
        cutter = box(name + '-cut%d' % i, (x_center, mitte, unten + h / 2),
                     (T * 3, breite, h), None)
        mod = wall.modifiers.new('cut%d' % i, 'BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = cutter
        bpy.context.view_layer.objects.active = wall
        bpy.ops.object.modifier_apply(modifier='cut%d' % i)
        bpy.data.objects.remove(cutter)


def door_frame(prefix, wall, along, room_w, room_d, frame_m, glow_color,
               glow_strength, glow_dist=0.45):
    """Zargen + Lichtquelle hinter einer Öffnung (Öffnung via wall_x/wall_y)."""
    fr = 0.06
    if wall == 'n':
        face = -room_d / 2 - 0.01
        box(prefix + '-l', (along - DOOR_W / 2, face, DOOR_H / 2), (fr, 0.08, DOOR_H), frame_m)
        box(prefix + '-r', (along + DOOR_W / 2, face, DOOR_H / 2), (fr, 0.08, DOOR_H), frame_m)
        box(prefix + '-o', (along, face, DOOR_H), (DOOR_W + fr, 0.08, fr), frame_m)
        glow = mat_emission(prefix + '-licht', glow_color, glow_strength)
        bpy.ops.mesh.primitive_plane_add(size=1, location=(along, -room_d / 2 - glow_dist, DOOR_H / 2),
                                         rotation=(math.pi / 2, 0, 0))
    else:  # 'w'
        face = -room_w / 2 - 0.01
        box(prefix + '-l', (face, along - DOOR_W / 2, DOOR_H / 2), (0.08, fr, DOOR_H), frame_m)
        box(prefix + '-r', (face, along + DOOR_W / 2, DOOR_H / 2), (0.08, fr, DOOR_H), frame_m)
        box(prefix + '-o', (face, along, DOOR_H), (0.08, DOOR_W + fr, fr), frame_m)
        glow = mat_emission(prefix + '-licht', glow_color, glow_strength)
        bpy.ops.mesh.primitive_plane_add(size=1, location=(-room_w / 2 - glow_dist, along, DOOR_H / 2),
                                         rotation=(math.pi / 2, 0, math.pi / 2))
    p = bpy.context.active_object
    p.dimensions = (DOOR_W + 0.3, DOOR_H + 0.2, 1)
    bpy.ops.object.transform_apply(scale=True)
    p.data.materials.append(glow)


def art_plane(name, img_path, wall, along, w, h, room_w, room_d):
    m = mat_art(img_path)
    bpy.ops.mesh.primitive_plane_add(size=1)
    o = bpy.context.active_object
    o.name = 'werk-' + name
    o.dimensions = (w, h, 1)
    D2, W2 = room_d / 2, room_w / 2
    if wall == 'n':
        o.location = (along, -D2 + 0.065, HANG)
        o.rotation_euler = (math.pi / 2, 0, math.pi)
    elif wall == 's':
        o.location = (along, D2 - 0.065, HANG)
        o.rotation_euler = (math.pi / 2, 0, 0)
    else:  # 'e'
        o.location = (W2 - 0.065, along, HANG)
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


def add_label(wk, room_w, room_d, plaque_m, ink_m):
    """Lesbare Wandplakette rechts neben dem Werk (Betrachtersicht)."""
    wall, along, w = wk['wall'], wk['along'], wk['w']
    D2, W2 = room_d / 2, room_w / 2
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


def add_werke(werke, room_w, room_d, frame_m, plaque_m, ink_m):
    D2, W2 = room_d / 2, room_w / 2
    for wk in werke:
        wall, along, w, h = wk['wall'], wk['along'], wk['w'], wk['h']
        t = 0.05
        if wall in ('n', 's'):
            y = -D2 + t / 2 + 0.01 if wall == 'n' else D2 - t / 2 - 0.01
            box('rahmen-' + wk['slug'], (along, y, HANG), (w + 0.09, t, h + 0.09), frame_m)
        else:
            box('rahmen-' + wk['slug'], (W2 - t / 2 - 0.01, along, HANG), (t, w + 0.09, h + 0.09), frame_m)
        art_plane(wk['slug'], os.path.join(ART_DIR, wk['img']), wall, along, w, h,
                  room_w, room_d)
        add_label(wk, room_w, room_d, plaque_m, ink_m)


def add_walltext(ink_m, x, y, z=1.85, sub=1.58):
    rot = (math.pi / 2, 0, math.pi)
    text_obj('SLICED GOLF', (x, y, z), rot, 0.3, ink_m, FONT_META, 0.002)
    text_obj('Ralf Lehmann', (x, y, sub), rot, 0.13, ink_m, FONT_META, 0.002)


def point_light(loc, energy, color, size=0.15):
    bpy.ops.object.light_add(type='POINT', location=loc)
    l = bpy.context.active_object
    l.data.energy = energy
    l.data.color = color
    l.data.shadow_soft_size = size


def area_light(loc, rot, energy, color, size):
    bpy.ops.object.light_add(type='AREA', location=loc, rotation=rot)
    l = bpy.context.active_object
    l.data.energy = energy
    l.data.color = color
    l.data.size = size


def grey_world(strength, color=(0.35, 0.35, 0.38)):
    world = bpy.data.worlds.new('Welt')
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (*color, 1)
    bg.inputs['Strength'].default_value = strength
    bpy.context.scene.world = world


# ── White Cube: Halle ────────────────────────────────────

def build_wc_halle():
    wall_m = mat_principled('wand', (0.93, 0.93, 0.92), 0.9)
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
    wall_x('wand-n', -D2 - T / 2, HALL_W, H, T, wall_m)
    wall_x('wand-s', D2 + T / 2, HALL_W, H, T, wall_m)
    wall_y('wand-e', W2 + T / 2, HALL_D, H, T, wall_m)

    # Westwand: Türen zu Foyer (-2), Garten (0), Kabinett (+2)
    wall_y('wand-w', -W2 - T / 2, HALL_D, H, T, wall_m,
           openings=[(-2.0, DOOR_W, 0, DOOR_H), (0.0, DOOR_W, 0, DOOR_H),
                     (2.0, DOOR_W, 0, DOOR_H)])
    door_frame('tuer-foyer', 'w', -2.0, HALL_W, HALL_D, mullion, (1.0, 0.95, 0.88), 1.6)
    door_frame('tuer-garten', 'w', 0.0, HALL_W, HALL_D, mullion, (0.85, 0.95, 1.0), 2.5)
    door_frame('tuer-kabinett', 'w', 2.0, HALL_W, HALL_D, mullion, (1.0, 0.95, 0.88), 1.6)

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

    add_werke(HALL_WERKE, HALL_W, HALL_D, frame_m, plaque_m, ink_m)
    add_walltext(ink_m, -4.0, -D2 + 0.02)


def lights_wc_halle():
    area_light((0, 0, 3.65), (0, 0, 0), 480, (1.0, 1.0, 1.0), 5.0)
    point_light((0, -2.0, 2.8), 130, (1.0, 1.0, 1.0), 0.2)
    point_light((0, 2.0, 2.8), 130, (1.0, 1.0, 1.0), 0.2)
    grey_world(0.3, (0.9, 0.9, 0.9))


# ── Salon: Halle ─────────────────────────────────────────

def build_salon_halle():
    sage = mat_principled('wand', (0.283, 0.306, 0.235), 0.85)
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

    # Nordwand mit Oberlicht über der Mitte (x=0, z 2.4–3.2)
    wall_x('wand-n', -D2 - T / 2, HALL_W, H, T, sage,
           openings=[(0.0, 1.6, 2.4, 3.2)])
    box('ol-rahmen-l', (-0.8, -D2 - 0.01, 2.8), (0.06, 0.1, 0.8), cream)
    box('ol-rahmen-r', (0.8, -D2 - 0.01, 2.8), (0.06, 0.1, 0.8), cream)
    box('ol-rahmen-o', (0, -D2 - 0.01, 3.2), (1.66, 0.1, 0.06), cream)
    box('ol-rahmen-u', (0, -D2 - 0.01, 2.4), (1.66, 0.1, 0.06), cream)
    box('ol-sprosse', (0, -D2 - 0.005, 2.8), (0.03, 0.05, 0.8), cream)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -D2 - 0.4, 2.8),
                                     rotation=(math.pi / 2, 0, 0))
    p = bpy.context.active_object
    p.dimensions = (2.0, 1.2, 1)
    bpy.ops.object.transform_apply(scale=True)
    p.data.materials.append(sky)

    wall_x('wand-s', D2 + T / 2, HALL_W, H, T, sage)
    wall_y('wand-e', W2 + T / 2, HALL_D, H, T, sage)

    # Westwand: Türen zu Foyer (-2), Garten (0), Kabinett (+2)
    wall_y('wand-w', -W2 - T / 2, HALL_D, H, T, sage,
           openings=[(-2.0, DOOR_W, 0, DOOR_H), (0.0, DOOR_W, 0, DOOR_H),
                     (2.0, DOOR_W, 0, DOOR_H)])
    door_frame('tuer-foyer', 'w', -2.0, HALL_W, HALL_D, wood, (1.0, 0.88, 0.68), 1.8)
    door_frame('tuer-garten', 'w', 0.0, HALL_W, HALL_D, wood, (0.85, 0.95, 1.0), 2.5)
    door_frame('tuer-kabinett', 'w', 2.0, HALL_W, HALL_D, wood, (1.0, 0.88, 0.68), 1.8)

    # Vertäfelung, Stuhlleiste, Sockel — an N, S, E
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

    for c in (-4.2, -2.0, 2.0, 4.2):     # Nord: Oberlicht bleibt frei
        panel('n', c, 2.0)
    for c in (-4.5, -1.5, 1.5, 4.5):
        panel('s', c, 2.4)
    for c in (-2.6, 0.0, 2.6):
        panel('e', c, 2.0)

    # Kassettendecke
    for i in range(5):
        x = -W2 + i * (HALL_W / 4)
        box('balken-x', (x, 0, H - 0.075), (0.14, HALL_D, 0.15), cream)
    for j in range(4):
        y = -D2 + j * (HALL_D / 3)
        box('balken-y', (0, y, H - 0.075), (HALL_W, 0.14, 0.15), cream)

    # Kronleuchter
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

    add_werke(HALL_WERKE, HALL_W, HALL_D, frame_m, plaque_m, ink_m)
    add_walltext(ink_m, -4.0, -D2 + 0.02)


def lights_salon_halle():
    point_light((0, 0, HALL_H - 1.0), 320, (1.0, 0.8, 0.58))
    point_light((0, -2.0, 2.9), 90, (1.0, 0.94, 0.85))
    point_light((0, 2.0, 2.9), 90, (1.0, 0.94, 0.85))
    area_light((0, -HALL_D / 2 - 0.9, 2.8), (math.pi / 2, 0, math.pi), 350,
               (0.88, 0.94, 1.0), 1.5)
    grey_world(0.35, (0.32, 0.33, 0.35))


# ── Foyer & Kabinett (pro Szene gestylt) ─────────────────

def build_foyer(style):
    wall_m = mat_principled('wand', style['wall'], 0.85)
    ceil_m = mat_principled('FoyerDecke', style['ceil'], 0.9)
    wood = mat_principled('FoyerHolz', (0.16, 0.10, 0.055), 0.4)
    ink_m = mat_principled('FoyerSchrift', style['ink'], 0.6)
    floor_m = style['floor']()
    glow_portal = mat_emission('PortalLicht', (0.9, 0.95, 1.0), 3.0)

    W2, D2, H = FOY_W / 2, FOY_D / 2, FOY_H
    T = 0.12

    box('boden', (0, 0, -0.05), (FOY_W, FOY_D, 0.1), floor_m)
    box('decke', (0, 0, H + 0.05), (FOY_W + 2 * T, FOY_D + 2 * T, 0.1), ceil_m)
    wall_x('wand-n', -D2 - T / 2, FOY_W, H, T, wall_m)
    wall_y('wand-e', W2 + T / 2, FOY_D, H, T, wall_m)

    # Westwand: Tür zur Halle (y=0)
    wall_y('wand-w', -W2 - T / 2, FOY_D, H, T, wall_m,
           openings=[(0.0, DOOR_W, 0, DOOR_H)])
    door_frame('tuer-halle', 'w', 0.0, FOY_W, FOY_D, wood, style['doorglow'], 1.8)

    # Südwand: Eingangsportal (verglast, helles Aussenlicht)
    wall_x('wand-s', D2 + T / 2, FOY_W, H, T, wall_m,
           openings=[(0.0, 1.8, 0, 2.4)])
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

    # Wandschrift Nordwand
    add_walltext(ink_m, 0.0, -D2 + 0.02, z=1.9, sub=1.62)

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


def lights_foyer(style):
    point_light((-1.5, 0.5, FOY_H - 0.95), 130, (1.0, 0.86, 0.66), 0.12)
    point_light((1.5, 0.5, FOY_H - 0.95), 130, (1.0, 0.86, 0.66), 0.12)
    point_light((0, -1.5, 2.5), 60, (1.0, 0.94, 0.85))
    grey_world(0.4, style['world'])


def build_kabinett(style):
    wall_m = mat_principled('wand', style['wall'], 0.85)
    ceil_m = mat_principled('KabDecke', style['ceil'], 0.9)
    frame_m = mat_principled('Rahmen', style['frame'], 0.45)
    plaque_m = mat_principled('Plakette', style['plaque'], 0.6)
    ink_m = mat_principled('Schrift', style['ink'], 0.6)
    wood = mat_principled('KabHolz', (0.16, 0.10, 0.055), 0.4)
    floor_m = style['floor']()

    W2, D2, H = KAB_W / 2, KAB_D / 2, KAB_H
    T = 0.12

    box('boden', (0, 0, -0.05), (KAB_W, KAB_D, 0.1), floor_m)
    box('decke', (0, 0, H + 0.05), (KAB_W + 2 * T, KAB_D + 2 * T, 0.1), ceil_m)
    wall_x('wand-n', -D2 - T / 2, KAB_W, H, T, wall_m)
    wall_x('wand-s', D2 + T / 2, KAB_W, H, T, wall_m)
    wall_y('wand-e', W2 + T / 2, KAB_D, H, T, wall_m)

    # Westwand: Tür zurück zur Halle (y=0)
    wall_y('wand-w', -W2 - T / 2, KAB_D, H, T, wall_m,
           openings=[(0.0, DOOR_W, 0, DOOR_H)])
    door_frame('tuer-halle', 'w', 0.0, KAB_W, KAB_D, wood, style['doorglow'], 1.8)

    add_werke(KAB_WERKE, KAB_W, KAB_D, frame_m, plaque_m, ink_m)


def lights_kabinett(style):
    point_light((0, 0, KAB_H - 0.5), 220, style['light'], 0.2)
    point_light((0, -1.5, 2.4), 70, (1.0, 0.95, 0.88))
    grey_world(0.4, style['world'])


# ── Garten (geteilt) ─────────────────────────────────────

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

    for tag, loc, dims in (
            ('n', (0, -G2 - 0.3, 1.1), (GAR + 2, 0.6, 2.2)),
            ('s', (0, G2 + 0.3, 1.1), (GAR + 2, 0.6, 2.2)),
            ('w', (-G2 - 0.3, 0, 1.1), (0.6, GAR + 2, 2.2)),
            ('e', (G2 + 0.3, 0, 1.1), (0.6, GAR + 2, 2.2))):
        box('hecke-' + tag, loc, dims, hedge)

    # Ausgang zurück in die Halle (helles Portal in der Heckenwand)
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

    # Himmel + Sonne
    world = bpy.data.worlds.new('Himmel')
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes['Background']
    sky = nt.nodes.new('ShaderNodeTexSky')
    sky.sky_type = 'MULTIPLE_SCATTERING'
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


# ── Stile, Kamera & Render ───────────────────────────────

STYLE_WC = {
    'wall': (0.93, 0.93, 0.92), 'ceil': (0.95, 0.95, 0.94),
    'frame': (0.07, 0.07, 0.07), 'plaque': (0.97, 0.97, 0.96),
    'ink': (0.05, 0.05, 0.05), 'floor': lambda: mat_principled('BodenWeiss', (0.62, 0.615, 0.60), 0.42),
    'doorglow': (1.0, 0.95, 0.88), 'light': (1.0, 1.0, 1.0),
    'world': (0.9, 0.9, 0.9),
}

STYLE_SALON = {
    'wall': (0.283, 0.306, 0.235), 'ceil': (0.82, 0.79, 0.72),
    'frame': (0.16, 0.11, 0.05), 'plaque': (0.93, 0.92, 0.89),
    'ink': (0.05, 0.045, 0.04), 'floor': mat_floor_dark,
    'doorglow': (1.0, 0.88, 0.68), 'light': (1.0, 0.86, 0.66),
    'world': (0.32, 0.33, 0.35),
}

THEMES = {
    'white-cube-foyer':    (lambda: build_foyer(STYLE_WC),
                            lambda: lights_foyer(STYLE_WC), FOY_ST),
    'white-cube-halle':    (build_wc_halle, lights_wc_halle, HALL_ST),
    'white-cube-kabinett': (lambda: build_kabinett(STYLE_WC),
                            lambda: lights_kabinett(STYLE_WC), KAB_ST),
    'salon-foyer':         (lambda: build_foyer(STYLE_SALON),
                            lambda: lights_foyer(STYLE_SALON), FOY_ST),
    'salon-halle':         (build_salon_halle, lights_salon_halle, HALL_ST),
    'salon-kabinett':      (lambda: build_kabinett(STYLE_SALON),
                            lambda: lights_kabinett(STYLE_SALON), KAB_ST),
    'garten':              (build_garten, lights_garten, GAR_ST),
}


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
        build, lights, stations = THEMES[name]
        build()
        lights()
        cam = make_camera()

        if preview:
            configure(scene, 2048, 1024, 64)
            i = only if only is not None else 0
            scene.render.filepath = '/tmp/%s-preview.jpg' % name
            cam.location = (-stations[i][0], stations[i][1], EYE)   # x gespiegelt
            bpy.ops.render.render(write_still=True)
            print('PREVIEW:', scene.render.filepath)
            continue

        configure(scene, 4096, 2048, 192)
        todo = range(len(stations)) if only is None else [only]
        for i in todo:
            cam.location = (-stations[i][0], stations[i][1], EYE)   # x gespiegelt
            scene.render.filepath = os.path.join(OUT_DIR, '%s-st%d.jpg' % (name, i))
            bpy.ops.render.render(write_still=True)
            print('FERTIG:', scene.render.filepath)


main()
