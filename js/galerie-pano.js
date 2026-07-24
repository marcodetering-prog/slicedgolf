/* SLICED GOLF — Fotorealistische Panorama-Galerie
   Street-View-Prinzip mit vorgerenderten 360°-Panoramen (Blender/Cycles,
   tools/render-gallery.py). Zwei Szenen — White Cube und Salon — mit je
   demselben Grundriss: Foyer → Halle → Kabinett, dazu ein geteilter
   Skulpturengarten. Ziehen zum Umsehen, Punkte anklicken zum Gehen,
   Werke anklicken für Details, Türen (gefüllte Punkte) führen in
   andere Räume.

   Panorama-Dateien: /images/pano/<szene>-<raum>-st<n>.jpg, der Garten
   liegt als geteilter Satz unter /images/pano/garten-st<n>.jpg. */

import * as THREE from 'three';

(function () {
  'use strict';

  var container = document.getElementById('galerie3d');
  if (!container) return;

  var REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var EYE = 1.55, HANG = 1.58;

  var SCENES = {
    'white-cube': { label: 'White Cube' },
    'salon': { label: 'Salon' }
  };

  /* Die Sammlung — hängt in der Halle (12 x 8 m) */
  var HALL_WERKE = [
    { slug: 'blumenwiese', title: 'Blumenwiese',
      meta: 'Opus 21/99 · 100 × 100 cm · 2025', x: -2.4, z: -4, w: 1.35, h: 1.35,
      desc: 'Mehrere hundert Ballhälften auf weissem Panel, ohne Raster nach Farbfamilien. Zufällig verteilt, in der Summe ein Feld.' },
    { slug: 'rasta-mondrian-auf-wolke-7', title: 'Rasta-Mondrian auf Wolke 7',
      meta: 'Opus 27/99 · 100 × 100 cm · 2024', x: 2.4, z: -4, w: 1.25, h: 1.25,
      desc: 'Eine Verbeugung vor Mondrian, übersetzt in das Material des Spiels. Farbfelder aus Ballhälften, gefasst in ein schwarzes Raster.' },
    { slug: 'darkroom-beleuchter', title: 'Darkroom Beleuchter',
      meta: 'Opus 13/99 · 100 × 70 cm · 2023', x: 2.4, z: 4, w: 1.35, h: 1.37,
      desc: 'Auf schwarzem Brett verdichten sich kühle Blau- und Violetttöne zu einem Leuchten, das erst im Halbdunkel seine volle Wirkung entfaltet.' },
    { slug: 'fairway-spektrum', title: 'Fairway Spektrum',
      meta: 'Opus 16/99 · 100 × 75 cm · 2024', x: -2.4, z: 4, w: 1.45, h: 0.9,
      desc: 'Ein breites Farbspektrum über die ganze Tafel gezogen — von kühlem Grün bis zu warmem Ocker.' },
    { slug: 'stille-wasser', title: 'Stille Wasser',
      meta: 'Opus 31/99 · 70 × 50 cm · 2025', x: -6, z: 0, w: 1.05, h: 0.66,
      desc: 'Lakeballs, dem Wasser entnommen und zu einer Komposition aus Grün- und Graunuancen geordnet. Zurückhaltend, fast monochrom.' }
  ];

  /* Das Kabinett (8 x 6 m): ein weiteres Werk plus Makrofotografien */
  var KABINETT_WERKE = [
    { slug: 'great-balls-of-fire', title: 'Great Balls of Fire',
      meta: 'Opus 18/99 · 80 × 60 cm · 2024', x: 0, z: -3, w: 0.6, h: 0.8,
      desc: 'Achtzehn Lagen Rot, gefunden in den Kernen ausgemusterter Turnierbälle. Die Komposition folgt keiner Vorzeichnung — die Farbe bestimmt ihren Platz selbst.' },
    { slug: 'ballhaelften-1', title: 'Ballhälften I',
      meta: 'Makrofotografie', x: -4, z: 0, w: 0.9, h: 0.68,
      desc: 'Schicht für Schicht: Das Makro legt den Aufbau der Bälle offen — Kern, Schichten, Lack.' },
    { slug: 'ballhaelften-2', title: 'Ballhälften II',
      meta: 'Makrofotografie', x: -1.5, z: 3, w: 0.9, h: 0.68,
      desc: 'Schicht für Schicht: Das Makro legt den Aufbau der Bälle offen — Kern, Schichten, Lack.' },
    { slug: 'ballhaelften-3', title: 'Ballhälften III',
      meta: 'Makrofotografie', x: 1.5, z: 3, w: 0.9, h: 0.68,
      desc: 'Schicht für Schicht: Das Makro legt den Aufbau der Bälle offen — Kern, Schichten, Lack.' }
  ];

  var HALL_ST = [
    { x: 0,    z: 2.4 },
    { x: 0,    z: 0 },
    { x: -2.4, z: -1.9, werk: 'blumenwiese' },
    { x: 2.4,  z: -1.9, werk: 'rasta-mondrian-auf-wolke-7' },
    { x: 2.4,  z: 1.9,  werk: 'darkroom-beleuchter' },
    { x: -2.4, z: 1.9,  werk: 'fairway-spektrum' },
    { x: -4.1, z: 0,    werk: 'stille-wasser' },
    { x: 4.3,  z: -2.0 },   // Tür Foyer
    { x: 4.3,  z: 0 },      // Tür Garten
    { x: 4.3,  z: 2.0 }     // Tür Kabinett
  ];

  /* Grundriss — gilt für beide Szenen; der Garten ist geteilt. */
  var LAYOUT = {
    'foyer': {
      face: { x: 0, z: -3 },
      stations: [
        { x: 0,   z: 1.2 },
        { x: 2.4, z: 0 }
      ],
      werke: [],
      doors: [
        { x: 4, z: 0, to: ['halle', 7] }
      ]
    },
    'halle': {
      face: { x: 0, z: -4 },
      stations: HALL_ST,
      werke: HALL_WERKE,
      doors: [
        { x: 6, z: -2, to: ['foyer', 1] },
        { x: 6, z: 0,  to: ['garten', 0] },
        { x: 6, z: 2,  to: ['kabinett', 2] }
      ]
    },
    'kabinett': {
      face: { x: 0, z: -3 },
      stations: [
        { x: 0,    z: 1.0 },
        { x: -1.8, z: -0.8, werk: 'great-balls-of-fire' },
        { x: 2.6,  z: 0 }
      ],
      werke: KABINETT_WERKE,
      doors: [
        { x: 4, z: 0, to: ['halle', 9] }
      ]
    },
    'garten': {
      face: { x: 0, z: -3 },
      stations: [
        { x: 0, z: 4.2 },
        { x: 0, z: -0.5 }
      ],
      werke: [],
      doors: [
        { x: 0, z: 6, to: ['halle', 8] }
      ]
    }
  };

  /* Panorama-Ausrichtung: Bildmitte schaut nach Norden (three -z).
     PANO_OFFSET korrigiert die Texture-Drehung der Kugel. */
  var PANO_OFFSET = -Math.PI / 2;

  var requested = new URLSearchParams(window.location.search).get('raum');
  var scene = SCENES[requested] ? requested : 'white-cube';
  var room = 'foyer';
  var station = 0;

  function panoUrl(sc, rm, st) {
    var prefix = rm === 'garten' ? 'garten' : sc + '-' + rm;
    return '/images/pano/' + prefix + '-st' + st + '.jpg';
  }

  /* ── Szene ─────────────────────────────────────── */
  var scene3d = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(72, 1, 0.05, 200);
  camera.position.set(0, 0, 0);

  var renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  var loader = new THREE.TextureLoader();
  var loadingEl = document.getElementById('g3d-loading');

  function makeSphere() {
    var geo = new THREE.SphereGeometry(60, 72, 36);
    geo.scale(-1, 1, 1);
    geo.rotateY(PANO_OFFSET);
    var m = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, toneMapped: false });
    var mesh = new THREE.Mesh(geo, m);
    mesh.renderOrder = -1;               // Panorama immer zuerst zeichnen
    mesh.visible = false;
    scene3d.add(mesh);
    return mesh;
  }
  var sphereA = makeSphere();
  var sphereB = makeSphere();
  var active = sphereA;

  var texCache = {};
  function loadPano(sc, rm, st, cb) {
    var key = sc + rm + st;
    if (texCache[key]) { cb(texCache[key]); return; }
    loader.load(panoUrl(sc, rm, st), function (tex) {
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
      texCache[key] = tex;
      cb(tex);
    });
  }

  /* ── Hotspots (Ringe am Boden, Türen, Klickflächen für Werke) ── */
  var hotspotScene = new THREE.Scene();
  var hotspotGroup = new THREE.Group();
  hotspotScene.add(hotspotGroup);

  function dirFromStation(st, wx, wy, wz) {
    /* Richtung vom Auge (Station) zu Weltpunkt, auf Kugelradius projiziert */
    var v = new THREE.Vector3(wx - st.x, wy - EYE, wz - st.z);
    return v.normalize();
  }

  function upFacing(pos) {
    return pos.clone().add(new THREE.Vector3(0, 1, 0));
  }

  function rebuildHotspots() {
    while (hotspotGroup.children.length) hotspotGroup.remove(hotspotGroup.children[0]);
    var R = LAYOUT[room];
    var st = R.stations[station];
    var ringColor = scene === 'salon' ? 0xfff2dc : 0x0a0a0a;

    function addGroundMarker(pos, k, userData, isDoor) {
      var ring = new THREE.Mesh(
        new THREE.RingGeometry(0.30 * k, 0.42 * k, 40),
        new THREE.MeshBasicMaterial({
          color: ringColor, transparent: true, opacity: isDoor ? 0.55 : 0.35,
          side: THREE.DoubleSide, depthTest: false
        })
      );
      ring.position.copy(pos);
      ring.lookAt(upFacing(pos));
      ring.renderOrder = 2;
      hotspotGroup.add(ring);
      if (isDoor) {   // Türen: gefüllte Mitte als Unterscheidung
        var dot = new THREE.Mesh(
          new THREE.CircleGeometry(0.14 * k, 24),
          new THREE.MeshBasicMaterial({
            color: ringColor, transparent: true, opacity: 0.55,
            side: THREE.DoubleSide, depthTest: false
          })
        );
        dot.position.copy(pos);
        dot.lookAt(upFacing(pos));
        dot.renderOrder = 2;
        hotspotGroup.add(dot);
      }
      /* unsichtbare grosszügige Trefferfläche */
      var hit = new THREE.Mesh(
        new THREE.CircleGeometry(0.9 * k, 20),
        new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthTest: false })
      );
      hit.position.copy(pos);
      hit.lookAt(upFacing(pos));
      hit.renderOrder = 2;
      for (var key in userData) hit.userData[key] = userData[key];
      hit.userData.ring = ring;
      hotspotGroup.add(hit);
    }

    R.stations.forEach(function (other, i) {
      if (i === station) return;
      var dist = Math.hypot(other.x - st.x, other.z - st.z);
      if (dist > 6.5) return;                       // nur nahe Punkte zeigen
      var dir = dirFromStation(st, other.x, 0, other.z);
      var pos = dir.clone().multiplyScalar(24);
      var k = 24 / Math.max(dist, 1.2);           // näher = grösser, wie Street View
      addGroundMarker(pos, k, { station: i }, false);
    });

    R.doors.forEach(function (door) {
      var dist = Math.hypot(door.x - st.x, door.z - st.z);
      var dir = dirFromStation(st, door.x, 0, door.z);
      var pos = dir.clone().multiplyScalar(24);
      var k = 24 / Math.max(dist, 1.2);
      addGroundMarker(pos, k, { door: door.to }, true);
    });

    R.werke.forEach(function (wk) {
      var dir = dirFromStation(st, wk.x, HANG, wk.z);
      var pos = dir.clone().multiplyScalar(23);
      var dist = Math.hypot(wk.x - st.x, wk.z - st.z);
      var scale = 23 / Math.max(dist, 0.8);
      var zone = new THREE.Mesh(
        new THREE.PlaneGeometry(wk.w * scale, wk.h * scale),
        new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, side: THREE.DoubleSide, depthTest: false })
      );
      zone.position.copy(pos);
      zone.lookAt(0, 0, 0);
      zone.renderOrder = 2;
      zone.userData.werk = wk;
      hotspotGroup.add(zone);
    });
  }

  /* ── Kamerasteuerung ───────────────────────────── */
  var yaw = 0, pitch = 0, targetYaw = 0, targetPitch = 0;

  function faceWorldPoint(wx, wz) {
    var st = LAYOUT[room].stations[station];
    targetYaw = Math.atan2(wx - st.x, -(wz - st.z));
    var d = targetYaw - yaw;
    while (d > Math.PI) { targetYaw -= 2 * Math.PI; d = targetYaw - yaw; }
    while (d < -Math.PI) { targetYaw += 2 * Math.PI; d = targetYaw - yaw; }
    targetPitch = 0;
  }

  var dragging = false, moved = 0, lastX = 0, lastY = 0;
  renderer.domElement.addEventListener('pointerdown', function (e) {
    dragging = true; moved = 0; lastX = e.clientX; lastY = e.clientY;
    try { renderer.domElement.setPointerCapture(e.pointerId); } catch (err) {}
  });
  renderer.domElement.addEventListener('pointermove', function (e) {
    if (!dragging) { updateHover(e); return; }
    var dx = e.clientX - lastX, dy = e.clientY - lastY;
    moved += Math.abs(dx) + Math.abs(dy);
    lastX = e.clientX; lastY = e.clientY;
    targetYaw -= dx * 0.0038;
    /* Nur seitliches Umsehen — vertikale Achse bleibt fixiert */
  });
  renderer.domElement.addEventListener('pointerup', function (e) {
    dragging = false;
    if (moved < 8) handleTap(e);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowLeft') targetYaw += 0.35;
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
    var hits = ray.intersectObjects(hotspotGroup.children);
    renderer.domElement.style.cursor = hits.length ? 'pointer' : 'grab';
    hotspotGroup.children.forEach(function (h) {
      if (h.userData.ring) h.userData.ring.material.opacity = 0.35;
    });
    var hit = hits.find(function (h) { return h.object.userData.ring; });
    if (hit) hit.object.userData.ring.material.opacity = 0.7;
  }

  function handleTap(e) {
    setPointer(e);
    var hits = ray.intersectObjects(hotspotGroup.children);
    var doorHit = hits.find(function (h) { return h.object.userData.door; });
    if (doorHit) { goDoor(doorHit.object.userData.door); return; }
    var stHit = hits.find(function (h) { return h.object.userData.station !== undefined; });
    if (stHit) { goToStation(stHit.object.userData.station); return; }
    var artHit = hits.find(function (h) { return h.object.userData.werk; });
    if (artHit) { showInfo(artHit.object.userData.werk); return; }
    hideInfo();
  }

  /* ── Stations-, Raum- & Szenenwechsel (Überblendung) ── */
  var fading = null;

  function showStation(sc, rm, st, instant, faceWerk) {
    loadPano(sc, rm, st, function (tex) {
      var incoming = (active === sphereA) ? sphereB : sphereA;
      incoming.material.map = tex;
      incoming.material.needsUpdate = true;
      incoming.visible = true;
      scene = sc;
      room = rm;
      station = st;
      rebuildHotspots();
      if (faceWerk) {
        var wk = LAYOUT[rm].werke.find(function (w) { return w.slug === faceWerk; });
        if (wk) faceWorldPoint(wk.x, wk.z);
      }
      if (instant || REDUCED) {
        incoming.material.opacity = 1;
        active.visible = false;
        active.material.opacity = 0;
        active = incoming;
        if (loadingEl) loadingEl.classList.add('is-done');
        if (faceWerk) showInfoBySlug(faceWerk);
      } else {
        fading = { from: active, to: incoming, t: 0, werk: faceWerk };
        active = incoming;
      }
      preloadNeighbours();
    });
  }

  function goToStation(i) {
    hideInfo();
    var st = LAYOUT[room].stations[i];
    showStation(scene, room, i, false, st.werk);
  }

  function goDoor(to) {
    hideInfo();
    faceWorldPoint(0, 0);          // Blick ins Zentrum des neuen Raums
    showStation(scene, to[0], to[1], false, null);
  }

  /* Szenenwechsel: gleicher Raum, gleiche Station, andere Welt */
  function applyScene(name) {
    if (!SCENES[name] || name === scene) return;
    hideInfo();
    if (room === 'garten') {       // Garten ist geteilt — kein Neuladen nötig
      scene = name;
      syncSceneButtons();
      rebuildHotspots();
      return;
    }
    showStation(name, room, station, false, null);
    syncSceneButtons();
  }

  function preloadNeighbours() {
    LAYOUT[room].stations.forEach(function (s, i) {
      if (i !== station) loadPano(scene, room, i, function () {});
    });
    LAYOUT[room].doors.forEach(function (door) {
      loadPano(scene, door.to[0], door.to[1], function () {});
    });
  }

  /* ── Szenen-Schalter (oben rechts) ─────────────── */
  function syncSceneButtons() {
    document.querySelectorAll('.g3d-themes .filter-btn').forEach(function (b) {
      b.classList.toggle('is-active', b.dataset.scene === scene);
    });
  }
  document.querySelectorAll('.g3d-themes .filter-btn').forEach(function (btn) {
    btn.addEventListener('click', function () { applyScene(btn.dataset.scene); });
  });

  /* ── Info-Karte ────────────────────────────────── */
  var infoEl = document.getElementById('g3d-info');
  var infoTitle = document.getElementById('g3d-info-title');
  var infoMeta = document.getElementById('g3d-info-meta');
  var infoClose = document.getElementById('g3d-info-close');

  var infoDesc = document.getElementById('g3d-info-desc');
  var infoWerkField = document.getElementById('g3d-anfrage-werk');
  var infoForm = document.getElementById('g3d-anfrage');
  var infoFormToggle = document.getElementById('g3d-anfrage-toggle');

  function showInfo(werk) {
    if (!infoEl) return;
    infoTitle.textContent = werk.title;
    infoMeta.textContent = werk.meta.toUpperCase();
    if (infoDesc) infoDesc.textContent = werk.desc || '';
    if (infoWerkField) infoWerkField.value = werk.meta.split(' · ')[0] + ' — ' + werk.title;
    if (infoForm) infoForm.classList.remove('is-open');
    infoEl.classList.add('is-visible');
  }
  if (infoFormToggle && infoForm) {
    infoFormToggle.addEventListener('click', function () {
      infoForm.classList.toggle('is-open');
    });
  }
  function showInfoBySlug(slug) {
    var wk = LAYOUT[room].werke.find(function (w) { return w.slug === slug; });
    if (wk) showInfo(wk);
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

    if (fading) {
      fading.t += rawDt / 0.5;
      var k = Math.min(fading.t, 1);
      fading.to.material.opacity = k;
      fading.from.material.opacity = 1 - k;
      if (fading.t >= 1) {
        fading.from.visible = false;
        var wk = fading.werk;
        fading = null;
        if (loadingEl) loadingEl.classList.add('is-done');
        if (wk) showInfoBySlug(wk);
      }
    }

    yaw += (targetYaw - yaw) * Math.min(1, dt * 9);
    pitch += (targetPitch - pitch) * Math.min(1, dt * 9);

    var dirV = new THREE.Vector3(
      Math.sin(yaw) * Math.cos(pitch),
      Math.sin(pitch),
      -Math.cos(yaw) * Math.cos(pitch)
    );
    camera.lookAt(dirV);
    renderer.autoClear = true;
    renderer.render(scene3d, camera);
    renderer.autoClear = false;
    renderer.clearDepth();
    renderer.render(hotspotScene, camera);   // Punkte immer über dem Panorama
  }
  frame();

  /* Start: Foyer der gewählten Szene (?raum=white-cube|salon) */
  faceWorldPoint(LAYOUT[room].face.x, LAYOUT[room].face.z);
  yaw = targetYaw; pitch = 0;
  syncSceneButtons();
  showStation(scene, room, station, true, null);

  var hint = document.getElementById('g3d-hint');
  if (hint) setTimeout(function () { hint.classList.add('is-done'); }, 6000);

  /* ── Panels (Werke, Künstler, Golf Pro, Kontakt) ── */
  function closePanels() {
    document.querySelectorAll('.g3d-panel.is-open').forEach(function (pnl) {
      pnl.classList.remove('is-open');
    });
  }
  document.querySelectorAll('[data-panel]').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      var overlay = document.querySelector('.nav-overlay');
      if (overlay) {
        overlay.classList.remove('is-open');
        overlay.setAttribute('aria-hidden', 'true');
        document.documentElement.style.overflow = '';
      }
      closePanels();
      hideInfo();
      var pnl = document.getElementById('panel-' + btn.dataset.panel);
      if (pnl) pnl.classList.add('is-open');
    });
  });
  document.querySelectorAll('.g3d-panel-close').forEach(function (btn) {
    btn.addEventListener('click', closePanels);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { closePanels(); hideInfo(); }
  });
  /* Werk-Liste: die Sammlung hängt in der Halle */
  document.querySelectorAll('[data-goto]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      closePanels();
      if (room !== 'halle') { room = 'halle'; }
      goToStation(parseInt(btn.dataset.goto, 10));
    });
  });
  /* Bestätigung bzw. Fehlermeldung nach Formularversand */
  var params = new URLSearchParams(window.location.search);
  if (hint && params.get('gesendet') === '1') {
    hint.textContent = 'Nachricht gesendet. Ralf Lehmann meldet sich persönlich.';
    hint.classList.remove('is-done');
    setTimeout(function () { hint.classList.add('is-done'); }, 7000);
  } else if (hint && params.get('fehler') === '1') {
    hint.textContent = 'Senden fehlgeschlagen. Bitte erneut versuchen oder per E-Mail an kontakt@slicedgolf.ch.';
    hint.classList.remove('is-done');
    setTimeout(function () { hint.classList.add('is-done'); }, 7000);
  }

  /* API für Tests und Deep-Links */
  window.SG3D = {
    goTo: goToStation,
    scene: applyScene,
    door: goDoor,
    tap: handleTap,
    state: function () {
      return { scene: scene, room: room, station: station, yaw: yaw,
               hotspots: hotspotGroup.children.length };
    },
    project: function (x, y, z) {
      var st = LAYOUT[room].stations[station];
      var v = new THREE.Vector3(x - st.x, y - EYE, z - st.z).normalize()
        .multiplyScalar(20).project(camera);
      var r = renderer.domElement.getBoundingClientRect();
      return { x: r.left + (v.x + 1) / 2 * r.width,
               y: r.top + (1 - v.y) / 2 * r.height, inFront: v.z < 1 };
    }
  };
})();
