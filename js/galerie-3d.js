/* SLICED GOLF — Virtuelle 3D-Galerie
   Street-View-Prinzip: Ziehen zum Umsehen, Bodenpunkte anklicken,
   um durch den Raum zu gehen. Werke anklicken für Details.
   Zwei Umgebungen: White Cube und Salon — jede als eigene Erfahrung.
   Three.js selbst gehostet — keine externen Abhängigkeiten. */

import * as THREE from 'three';
import { RoomEnvironment } from '/js/vendor/RoomEnvironment.js';

(function () {
  'use strict';

  var container = document.getElementById('galerie3d');
  if (!container) return;

  var REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── Werkdaten ─────────────────────────────────── */
  var WERKE = [
    { slug: 'blumenwiese', title: 'Blumenwiese',
      meta: 'Opus 21/99 · 100 × 100 cm · 2025',
      tex: '/images/artworks/blumenwiese.jpg', width: 1.35,
      wall: 'n', offset: -2.4, dark: false },
    { slug: 'rasta-mondrian-auf-wolke-7', title: 'Rasta-Mondrian auf Wolke 7',
      meta: 'Opus 27/99 · 100 × 100 cm · 2024',
      tex: '/images/artworks/rasta-mondrian-auf-wolke-7.jpg', width: 1.25,
      wall: 'n', offset: 2.4, dark: false },
    { slug: 'darkroom-beleuchter', title: 'Darkroom Beleuchter',
      meta: 'Opus 13/99 · 100 × 70 cm · 2023',
      tex: '/images/artworks/darkroom-beleuchter.jpg', width: 1.35,
      wall: 's', offset: 2.4, dark: true },
    { slug: 'fairway-spektrum', title: 'Fairway Spektrum',
      meta: 'Opus 16/99 · 100 × 75 cm · 2024',
      tex: '/images/artworks/fairway-spektrum-panel.jpg', width: 1.45,
      wall: 's', offset: -2.4, dark: true },
    { slug: 'stille-wasser', title: 'Stille Wasser',
      meta: 'Opus 31/99 · 70 × 50 cm · 2025',
      tex: '/images/artworks/stille-wasser-panel.jpg', width: 1.05,
      wall: 'w', offset: 0, dark: true }
  ];

  /* ── Grundgerüst ───────────────────────────────── */
  var W = 12, D = 8, H = 3.4;        // Raummasse in Metern
  var EYE = 1.55;                     // Augenhöhe
  var HANG = 1.58;                     // Bildmitte

  var scene = new THREE.Scene();

  var camera = new THREE.PerspectiveCamera(62, 1, 0.05, 60);
  camera.position.set(0, EYE, 2.6);

  var renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;
  container.appendChild(renderer.domElement);

  /* Image-based lighting für PBR-Materialien */
  var pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.55;

  /* ── Licht ─────────────────────────────────────── */
  var hemi = new THREE.HemisphereLight(0xffffff, 0xd8d4cd, 0.4);
  scene.add(hemi);

  /* Hauptlicht fällt durch das Oberlicht — wirft weiche Schatten */
  var sun = new THREE.DirectionalLight(0xffffff, 2.2);
  sun.position.set(0.6, H + 3.2, 1.2);
  sun.target.position.set(0, 0, 0);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.camera.left = -W / 2 - 1;
  sun.shadow.camera.right = W / 2 + 1;
  sun.shadow.camera.top = D / 2 + 1;
  sun.shadow.camera.bottom = -D / 2 - 1;
  sun.shadow.camera.near = 0.5;
  sun.shadow.camera.far = 12;
  sun.shadow.radius = 7;
  sun.shadow.bias = -0.0004;
  scene.add(sun);
  scene.add(sun.target);

  /* ── Prozedurale Texturen ──────────────────────── */

  /* Fugenloser Sichtbeton (White Cube) */
  function makeConcrete() {
    var c = document.createElement('canvas');
    c.width = 1024; c.height = 1024;
    var ctx = c.getContext('2d');
    ctx.fillStyle = '#e7e5e1';
    ctx.fillRect(0, 0, 1024, 1024);
    for (var i = 0; i < 5200; i++) {
      var x = Math.random() * 1024, y = Math.random() * 1024;
      var r = 18 + Math.random() * 60;
      var g = ctx.createRadialGradient(x, y, 0, x, y, r);
      var tone = 224 + Math.floor(Math.random() * 14) - 7;
      g.addColorStop(0, 'rgba(' + tone + ',' + (tone - 1) + ',' + (tone - 4) + ',0.05)');
      g.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = g;
      ctx.fillRect(x - r, y - r, r * 2, r * 2);
    }
    var tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(2.4, 1.6);
    return tex;
  }

  /* Fischgrät-Parkett (Salon) */
  function makeParquet() {
    var c = document.createElement('canvas');
    c.width = 1024; c.height = 1024;
    var ctx = c.getContext('2d');
    var tones = ['#a97c50', '#9a6f46', '#b1855a', '#8f6540', '#a5764b', '#b98a58'];
    ctx.fillStyle = tones[0];
    ctx.fillRect(0, 0, 1024, 1024);
    var pw = 256, ph = 60;
    for (var row = -3; row < 24; row++) {
      for (var col = -3; col < 10; col++) {
        var x = col * pw * 0.72, y = row * ph * 2;
        ctx.save();
        ctx.translate(x, y + (col % 2 ? ph : 0));
        ctx.rotate((col % 2 ? -1 : 1) * Math.PI / 4);
        var base = tones[Math.abs(row * 7 + col * 3) % tones.length];
        ctx.fillStyle = base;
        ctx.fillRect(0, 0, pw, ph);
        /* Maserung */
        ctx.globalAlpha = 0.18;
        for (var s = 0; s < 6; s++) {
          ctx.fillStyle = s % 2 ? '#6d4a2a' : '#c99b66';
          ctx.fillRect(0, (s + Math.random()) * ph / 6, pw, 1.6);
        }
        ctx.globalAlpha = 1;
        ctx.strokeStyle = 'rgba(50,28,12,0.5)';
        ctx.lineWidth = 2;
        ctx.strokeRect(0, 0, pw, ph);
        ctx.restore();
      }
    }
    var tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(6, 4);
    return tex;
  }

  /* Leuchtdecke im Raster (White Cube — Referenz: Lichtfeld-Decke) */
  function makeLightGrid() {
    var c = document.createElement('canvas');
    c.width = 1024; c.height = 512;
    var ctx = c.getContext('2d');
    ctx.fillStyle = '#fdfdfc';
    ctx.fillRect(0, 0, 1024, 512);
    ctx.strokeStyle = 'rgba(190,188,184,0.85)';
    ctx.lineWidth = 6;
    var cols = 8, rows = 4;
    for (var i = 0; i <= cols; i++) {
      ctx.beginPath(); ctx.moveTo(i * 1024 / cols, 0); ctx.lineTo(i * 1024 / cols, 512); ctx.stroke();
    }
    for (var j = 0; j <= rows; j++) {
      ctx.beginPath(); ctx.moveTo(0, j * 512 / rows); ctx.lineTo(1024, j * 512 / rows); ctx.stroke();
    }
    /* leichte Aufhellung zur Mitte jedes Feldes */
    for (var x = 0; x < cols; x++) {
      for (var y = 0; y < rows; y++) {
        var cx = (x + 0.5) * 1024 / cols, cy = (y + 0.5) * 512 / rows;
        var g = ctx.createRadialGradient(cx, cy, 4, cx, cy, 70);
        g.addColorStop(0, 'rgba(255,255,255,0.9)');
        g.addColorStop(1, 'rgba(255,255,255,0)');
        ctx.fillStyle = g;
        ctx.fillRect(cx - 70, cy - 70, 140, 140);
      }
    }
    var tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  }

  var concreteTex = makeConcrete();
  var parquetTex = makeParquet();
  var lightGridTex = makeLightGrid();

  /* ── Raum ──────────────────────────────────────── */
  var floorMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.42, metalness: 0.0 });
  var wallMat  = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.96 });
  var ceilMat  = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.95 });
  var skirtMat = new THREE.MeshStandardMaterial({ color: 0x0a0a0a, roughness: 0.8 });

  var floor = new THREE.Mesh(new THREE.PlaneGeometry(W, D), floorMat);
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  scene.add(floor);

  var ceil = new THREE.Mesh(new THREE.PlaneGeometry(W, D), ceilMat);
  ceil.rotation.x = Math.PI / 2;
  ceil.position.y = H;
  scene.add(ceil);

  function makeWall(w, h) {
    var m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), wallMat);
    m.receiveShadow = true;
    return m;
  }
  var wallN = makeWall(W, H); wallN.position.set(0, H / 2, -D / 2); scene.add(wallN);
  var wallS = makeWall(W, H); wallS.rotation.y = Math.PI; wallS.position.set(0, H / 2, D / 2); scene.add(wallS);
  var wallW = makeWall(D, H); wallW.rotation.y = Math.PI / 2; wallW.position.set(-W / 2, H / 2, 0); scene.add(wallW);
  var wallO = makeWall(D, H); wallO.rotation.y = -Math.PI / 2; wallO.position.set(W / 2, H / 2, 0); scene.add(wallO);

  /* Vier Wandseiten: [x, z, rotY, länge] */
  var SIDES = [[0, -D / 2, 0, W], [0, D / 2, Math.PI, W],
               [-W / 2, 0, Math.PI / 2, D], [W / 2, 0, -Math.PI / 2, D]];

  function inset(v, d) { return v === 0 ? 0 : (v > 0 ? v - d : v + d); }

  /* Sockel: White Cube = Schattenfuge, Salon = Holzsockel */
  var skirts = SIDES.map(function (s) {
    var skirt = new THREE.Mesh(new THREE.BoxGeometry(s[3], 0.06, 0.012), skirtMat);
    skirt.position.set(inset(s[0], 0.011), 0.03, inset(s[1], 0.011));
    skirt.rotation.y = s[2];
    scene.add(skirt);
    return skirt;
  });

  /* Salon: Lambris (Holztäfelung) und Karnies */
  var woodMat = new THREE.MeshStandardMaterial({ color: 0x5e3f28, roughness: 0.55 });
  var corniceMat = new THREE.MeshStandardMaterial({ color: 0x5a3a32, roughness: 0.7 });
  var salonParts = [];

  SIDES.forEach(function (s) {
    var wainscot = new THREE.Mesh(new THREE.BoxGeometry(s[3], 0.8, 0.03), woodMat);
    wainscot.position.set(inset(s[0], 0.026), 0.4, inset(s[1], 0.026));
    wainscot.rotation.y = s[2];
    wainscot.castShadow = true;
    scene.add(wainscot);
    salonParts.push(wainscot);

    var cornice = new THREE.Mesh(new THREE.BoxGeometry(s[3], 0.24, 0.06), corniceMat);
    cornice.position.set(inset(s[0], 0.041), H - 0.12, inset(s[1], 0.041));
    cornice.rotation.y = s[2];
    scene.add(cornice);
    salonParts.push(cornice);
  });

  /* Oberlicht / Leuchtdecke */
  var skylightMat = new THREE.MeshBasicMaterial({ map: lightGridTex, toneMapped: false });
  var skylight = new THREE.Mesh(new THREE.PlaneGeometry(7.2, 3.6), skylightMat);
  skylight.rotation.x = Math.PI / 2;
  skylight.position.y = H - 0.01;
  scene.add(skylight);

  /* ── Umgebungen ────────────────────────────────── */
  var discs = [];   // wird unten gefüllt

  var THEMES = {
    'white-cube': function () {
      scene.background = new THREE.Color(0xffffff);
      renderer.toneMappingExposure = 1.18;
      scene.environmentIntensity = 0.62;
      wallMat.color.set(0xfbfbfa);
      floorMat.map = concreteTex; floorMat.color.set(0xffffff);
      floorMat.roughness = 0.4; floorMat.needsUpdate = true;
      ceilMat.color.set(0xffffff);
      skirtMat.color.set(0x0a0a0a);
      skirts.forEach(function (s) { s.scale.y = 0.35; s.position.y = 0.0105; });
      salonParts.forEach(function (p) { p.visible = false; });
      skylightMat.map = lightGridTex; skylightMat.color.set(0xffffff); skylightMat.needsUpdate = true;
      hemi.color.set(0xffffff); hemi.groundColor.set(0xf0eeeb); hemi.intensity = 0.5;
      sun.color.set(0xffffff); sun.intensity = 2.0;
      sun.position.set(0.6, H + 3.2, 1.2);
      discs.forEach(function (d) { d.userData.ring.material.color.set(0x0a0a0a); });
    },
    'salon': function () {
      scene.background = new THREE.Color(0x2e211e);
      renderer.toneMappingExposure = 1.0;
      scene.environmentIntensity = 0.3;
      wallMat.color.set(0x6b7263);
      floorMat.map = parquetTex; floorMat.color.set(0xa8845c);
      floorMat.roughness = 0.34; floorMat.needsUpdate = true;
      ceilMat.color.set(0x4a3430);
      skirtMat.color.set(0x4f3520);
      skirts.forEach(function (s) { s.scale.y = 1; s.position.y = 0.03; });
      salonParts.forEach(function (p) { p.visible = true; });
      skylightMat.map = null; skylightMat.color.set(0xffe9c4); skylightMat.needsUpdate = true;
      hemi.color.set(0xffe9cf); hemi.groundColor.set(0x6a5236); hemi.intensity = 0.55;
      sun.color.set(0xffdba8); sun.intensity = 2.6;
      sun.position.set(2.4, H + 3.0, 2.0);
      discs.forEach(function (d) { d.userData.ring.material.color.set(0xfff2dc); });
    }
  };

  function applyTheme(name) {
    if (!THEMES[name]) name = 'white-cube';
    THEMES[name]();
    document.querySelectorAll('.g3d-themes .filter-btn').forEach(function (b) {
      b.classList.toggle('is-active', b.dataset.theme === name);
    });
  }

  document.querySelectorAll('.g3d-themes .filter-btn').forEach(function (btn) {
    btn.addEventListener('click', function () { applyTheme(btn.dataset.theme); });
  });

  /* ── Werke aufhängen ───────────────────────────── */
  var loader = new THREE.TextureLoader();
  var clickables = [];
  var pending = WERKE.length;
  var loadingEl = document.getElementById('g3d-loading');

  function wallTransform(wall, offset, depth) {
    switch (wall) {
      case 'n': return { x: offset, z: -D / 2 + depth, ry: 0 };
      case 's': return { x: offset, z: D / 2 - depth, ry: Math.PI };
      case 'w': return { x: -W / 2 + depth, z: offset, ry: Math.PI / 2 };
      default:  return { x: W / 2 - depth, z: offset, ry: -Math.PI / 2 };
    }
  }

  function hangArtwork(werk) {
    loader.load(werk.tex, function (tex) {
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
      var aspect = tex.image.height / tex.image.width;
      var w = werk.width, h = w * aspect, depth = 0.035;

      var edge = new THREE.MeshStandardMaterial({ color: werk.dark ? 0x111111 : 0xeceae6, roughness: 0.75 });
      var front = new THREE.MeshBasicMaterial({ map: tex, toneMapped: false });
      var back = new THREE.MeshStandardMaterial({ color: 0x222222 });
      var box = new THREE.Mesh(
        new THREE.BoxGeometry(w, h, depth),
        [edge, edge, edge, edge, front, back]
      );
      box.castShadow = true;

      var t = wallTransform(werk.wall, werk.offset, depth / 2 + 0.001);
      box.position.set(t.x, HANG, t.z);
      box.rotation.y = t.ry;
      scene.add(box);
      clickables.push({ mesh: box, werk: werk });

      /* Werklabel — Plakette rechts neben dem Werk */
      var label = makeLabel(werk.title, werk.meta.split(' · ')[0]);
      var lt = wallTransform(werk.wall, werk.offset, 0.004);
      var side = new THREE.Vector3(Math.cos(t.ry), 0, -Math.sin(t.ry));
      label.position.set(lt.x + side.x * (w / 2 + 0.22), Math.max(HANG - h / 2 + 0.06, 1.02), lt.z + side.z * (w / 2 + 0.22));
      label.rotation.y = t.ry;
      scene.add(label);

      if (--pending === 0 && loadingEl) loadingEl.classList.add('is-done');
    });
  }

  function makeLabel(title, opus) {
    var c = document.createElement('canvas');
    c.width = 512; c.height = 192;
    var ctx = c.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, c.width, c.height);
    ctx.fillStyle = '#0a0a0a';
    ctx.font = 'italic 300 40px "Cormorant Garamond", Georgia, serif';
    ctx.fillText(title, 32, 78, 448);
    ctx.fillStyle = '#888888';
    ctx.font = '300 26px Inter, sans-serif';
    ctx.fillText(opus, 32, 130, 448);
    var tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    return new THREE.Mesh(
      new THREE.PlaneGeometry(0.26, 0.0975),
      new THREE.MeshBasicMaterial({ map: tex, toneMapped: false })
    );
  }

  /* Ostwand: Wortmarke */
  (function eastWall() {
    var c = document.createElement('canvas');
    c.width = 1024; c.height = 512;
    var ctx = c.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, c.width, c.height);
    ctx.fillStyle = '#0a0a0a';
    ctx.font = '500 64px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('S L I C E D   G O L F', 512, 230);
    ctx.fillStyle = '#888888';
    ctx.font = 'italic 300 44px "Cormorant Garamond", Georgia, serif';
    ctx.fillText('Jeder Ball trägt eine Farbe in sich.', 512, 320);
    var tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    var mesh = new THREE.Mesh(
      new THREE.PlaneGeometry(3.0, 1.5),
      new THREE.MeshBasicMaterial({ map: tex, toneMapped: false })
    );
    mesh.position.set(W / 2 - 0.01, 1.7, 0);
    mesh.rotation.y = -Math.PI / 2;
    scene.add(mesh);
  })();

  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(function () { WERKE.forEach(hangArtwork); });
  } else {
    WERKE.forEach(hangArtwork);
  }

  /* ── Stationen (Street-View-Punkte) ────────────── */
  var STATIONS = [
    { x: 0,    z: 2.4,  look: { x: 0, z: -D / 2 } },
    { x: 0,    z: 0,    look: { x: 0, z: -D / 2 } },
    { x: -2.4, z: -1.9, werk: 'blumenwiese' },
    { x: 2.4,  z: -1.9, werk: 'rasta-mondrian-auf-wolke-7' },
    { x: 2.4,  z: 1.9,  werk: 'darkroom-beleuchter' },
    { x: -2.4, z: 1.9,  werk: 'fairway-spektrum' },
    { x: -4.1, z: 0,    werk: 'stille-wasser' }
  ];

  var discVisuals = [];
  STATIONS.forEach(function (st, i) {
    var ring = new THREE.Mesh(
      new THREE.RingGeometry(0.13, 0.19, 48),
      new THREE.MeshBasicMaterial({ color: 0x0a0a0a, transparent: true, opacity: 0.22 })
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.set(st.x, 0.012, st.z);
    scene.add(ring);
    discVisuals.push(ring);

    /* Unsichtbare volle Trefferfläche — auch die Ringmitte ist klickbar */
    var hit = new THREE.Mesh(
      new THREE.CircleGeometry(0.34, 24),
      new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false })
    );
    hit.rotation.x = -Math.PI / 2;
    hit.position.set(st.x, 0.013, st.z);
    hit.userData.station = i;
    hit.userData.ring = ring;
    scene.add(hit);
    discs.push(hit);
  });

  /* Umgebung initial anwenden (nach Disc-Erzeugung) */
  var themeParam = new URLSearchParams(window.location.search).get('raum');
  applyTheme(themeParam === 'salon' ? 'salon' : 'white-cube');

  /* ── Kamera-Steuerung ──────────────────────────── */
  /* Konvention: yaw 0 = Blick Richtung -z; dir = (sin yaw, 0, -cos yaw) */
  var yaw = Math.atan2(0 - camera.position.x, -(-D / 2 - camera.position.z));
  var pitch = 0;
  var targetYaw = yaw, targetPitch = pitch;

  var dragging = false, moved = 0, lastX = 0, lastY = 0;

  renderer.domElement.addEventListener('pointerdown', function (e) {
    dragging = true; moved = 0; lastX = e.clientX; lastY = e.clientY;
    try { renderer.domElement.setPointerCapture(e.pointerId); } catch (err) { /* synthetische Events */ }
  });
  renderer.domElement.addEventListener('pointermove', function (e) {
    if (!dragging) { updateHover(e); return; }
    var dx = e.clientX - lastX, dy = e.clientY - lastY;
    moved += Math.abs(dx) + Math.abs(dy);
    lastX = e.clientX; lastY = e.clientY;
    targetYaw -= dx * 0.0042;
    targetPitch = Math.max(-1.0, Math.min(1.0, targetPitch - dy * 0.0032));
  });
  renderer.domElement.addEventListener('pointerup', function (e) {
    dragging = false;
    if (moved < 8) handleTap(e);
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowLeft')  targetYaw += 0.35;
    if (e.key === 'ArrowRight') targetYaw -= 0.35;
  });

  /* ── Raycasting ────────────────────────────────── */
  var ray = new THREE.Raycaster();
  var pointer = new THREE.Vector2();

  function setPointer(e) {
    var r = renderer.domElement.getBoundingClientRect();
    pointer.x = ((e.clientX - r.left) / r.width) * 2 - 1;
    pointer.y = -((e.clientY - r.top) / r.height) * 2 + 1;
    ray.setFromCamera(pointer, camera);
  }

  function updateHover(e) {
    setPointer(e);
    var discHits = ray.intersectObjects(discs);
    var artHits = ray.intersectObjects(clickables.map(function (c) { return c.mesh; }));
    renderer.domElement.style.cursor = (discHits.length || artHits.length) ? 'pointer' : 'grab';
    discs.forEach(function (d) { d.userData.ring.material.opacity = 0.22; });
    if (discHits.length) discHits[0].object.userData.ring.material.opacity = 0.55;
  }

  function handleTap(e) {
    setPointer(e);
    var discHit = ray.intersectObjects(discs)[0];
    if (discHit) { goToStation(discHit.object.userData.station); return; }
    var artHit = ray.intersectObjects(clickables.map(function (c) { return c.mesh; }))[0];
    if (artHit) {
      var entry = clickables.find(function (c) { return c.mesh === artHit.object; });
      if (entry) showInfo(entry.werk);
    } else {
      hideInfo();
    }
  }

  /* ── Bewegung zwischen Stationen ───────────────── */
  var anim = null;

  function goToStation(i) {
    var st = STATIONS[i];
    var from = camera.position.clone();
    var to = new THREE.Vector3(st.x, EYE, st.z);

    var endYaw = targetYaw;
    if (st.werk) {
      var werk = WERKE.find(function (w) { return w.slug === st.werk; });
      var t = wallTransform(werk.wall, werk.offset, 0);
      endYaw = Math.atan2(t.x - st.x, -(t.z - st.z));
    } else if (st.look) {
      endYaw = Math.atan2(st.look.x - st.x, -(st.look.z - st.z));
    }
    var d = endYaw - targetYaw;
    while (d > Math.PI) d -= 2 * Math.PI;
    while (d < -Math.PI) d += 2 * Math.PI;
    endYaw = targetYaw + d;

    hideInfo();
    if (REDUCED) {
      camera.position.copy(to);
      targetYaw = endYaw; targetPitch = 0;
      if (st.werk) showInfoBySlug(st.werk);
      return;
    }
    anim = {
      from: from, to: to, t: 0,
      yawFrom: targetYaw, yawTo: endYaw,
      pitchFrom: targetPitch, pitchTo: 0,
      done: st.werk ? function () { showInfoBySlug(st.werk); } : null
    };
  }

  function easeInOut(t) { return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; }

  /* ── Info-Karte ────────────────────────────────── */
  var infoEl = document.getElementById('g3d-info');
  var infoTitle = document.getElementById('g3d-info-title');
  var infoMeta = document.getElementById('g3d-info-meta');
  var infoLink = document.getElementById('g3d-info-link');
  var infoClose = document.getElementById('g3d-info-close');

  function showInfo(werk) {
    if (!infoEl) return;
    infoTitle.textContent = werk.title;
    infoMeta.textContent = werk.meta.toUpperCase();
    infoLink.href = '/werke/' + werk.slug + '/';
    infoEl.classList.add('is-visible');
  }
  function showInfoBySlug(slug) {
    var werk = WERKE.find(function (w) { return w.slug === slug; });
    if (werk) showInfo(werk);
  }
  function hideInfo() {
    if (infoEl) infoEl.classList.remove('is-visible');
  }
  if (infoClose) infoClose.addEventListener('click', hideInfo);

  /* ── Render-Loop ───────────────────────────────── */
  function resize() {
    var w = container.clientWidth, h = container.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  }
  window.addEventListener('resize', resize);
  resize();

  var clock = new THREE.Clock();

  function frame() {
    requestAnimationFrame(frame);
    var rawDt = clock.getDelta();
    var dt = Math.min(rawDt, 0.05);

    if (anim) {
      anim.t += rawDt / 1.4;   // Echtzeit — bleibt auch bei gedrosseltem rAF korrekt
      var k = easeInOut(Math.min(anim.t, 1));
      camera.position.lerpVectors(anim.from, anim.to, k);
      targetYaw = anim.yawFrom + (anim.yawTo - anim.yawFrom) * k;
      yaw = targetYaw;
      targetPitch = anim.pitchFrom + (anim.pitchTo - anim.pitchFrom) * k;
      pitch = targetPitch;
      if (anim.t >= 1) {
        var cb = anim.done; anim = null;
        if (cb) cb();
      }
    } else {
      yaw += (targetYaw - yaw) * Math.min(1, dt * 10);
      pitch += (targetPitch - pitch) * Math.min(1, dt * 10);
    }

    var dirV = new THREE.Vector3(
      Math.sin(yaw) * Math.cos(pitch),
      Math.sin(pitch),
      -Math.cos(yaw) * Math.cos(pitch)
    );
    camera.lookAt(camera.position.clone().add(dirV));
    renderer.render(scene, camera);
  }
  frame();

  var hint = document.getElementById('g3d-hint');
  if (hint) setTimeout(function () { hint.classList.add('is-done'); }, 6000);

  /* Kleines API für Deep-Links und Tests */
  window.SG3D = {
    goTo: goToStation,
    theme: applyTheme,
    tap: handleTap,
    state: function () { return { pos: camera.position.toArray(), yaw: yaw, discs: discs.length, works: clickables.length }; },
    project: function (x, y, z) {
      var v = new THREE.Vector3(x, y, z).project(camera);
      var r = renderer.domElement.getBoundingClientRect();
      return { x: r.left + (v.x + 1) / 2 * r.width, y: r.top + (1 - v.y) / 2 * r.height, inFront: v.z < 1 };
    },
    cast: function (cx, cy) {
      setPointer({ clientX: cx, clientY: cy });
      return { discHits: ray.intersectObjects(discs).length, artHits: ray.intersectObjects(clickables.map(function (c) { return c.mesh; })).length };
    }
  };
})();
