import * as THREE from 'three';

const FT = 0.3048;
const TYPE_ORDER = ['A320', 'A330', 'ATR72', 'DHC6', 'AS350'];
const ACCENTS = {
  A320: ['#b5172b', '#1f4f9c', '#0e7c66', '#6b2a8c', '#c25b12'],
  A330: ['#7a1730', '#123d7a', '#0b5c4d'],
  ATR72: ['#d99a00', '#1d6fb8', '#c62828', '#2e7d32'],
  DHC6: ['#e65100', '#1565c0', '#6a1b9a'],
  AS350: ['#d32f2f', '#f5a623', '#283593', '#00897b'],
};
const KIND_COLOR = { arr: 0xec7826, dep: 0x3987e5, miss: 0xe5534b, heli: 0x3fae6a };

function mulberry32(a) {
  return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
}
const pick = (rng, weights) => { let r = rng() * Object.values(weights).reduce((a, b) => a + b, 0); for (const [k, w] of Object.entries(weights)) { r -= w; if (r <= 0) return k; } return Object.keys(weights)[0]; };
const clamp01 = v => Math.min(Math.max(v, 0), 1);

function wingShape(pts, depth) {
  const s = new THREE.Shape(pts.map(([x, z]) => new THREE.Vector2(x, z)));
  const g = new THREE.ExtrudeGeometry(s, { depth, bevelEnabled: false });
  g.rotateX(Math.PI / 2);
  return g;
}
function finShape(pts, thick) {
  const s = new THREE.Shape(pts.map(([z, y]) => new THREE.Vector2(z, y)));
  const g = new THREE.ExtrudeGeometry(s, { depth: thick, bevelEnabled: false });
  g.translate(0, 0, -thick / 2);
  g.rotateY(-Math.PI / 2);
  return g;
}
const mirror = pts => pts.map(([x, z]) => [-x, z]).reverse();

function buildModel(type, accent) {
  const g = new THREE.Group();
  const body = new THREE.MeshStandardMaterial({ color: 0xf1f3f6, roughness: .45, metalness: .25 });
  const acc = new THREE.MeshStandardMaterial({ color: accent, roughness: .5, metalness: .2 });
  const dark = new THREE.MeshStandardMaterial({ color: 0x2a2f38, roughness: .6, metalness: .4 });
  const glass = new THREE.MeshStandardMaterial({ color: 0x0d1a2b, roughness: .2, metalness: .6 });
  const add = (geo, mat, x = 0, y = 0, z = 0) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); g.add(m); return m; };
  const gear = new THREE.Group(); g.add(gear); g.userData.gear = gear;
  const props = []; g.userData.props = props;
  const lights = { red: [], green: [], strobe: [] }; g.userData.lights = lights;
  const strut = (x, z, h, r = .35) => { const m = new THREE.Mesh(new THREE.CylinderGeometry(.18, .18, h, 6), dark); m.position.set(x, -h / 2, z); gear.add(m);
    const w = new THREE.Mesh(new THREE.CylinderGeometry(r * 1.6, r * 1.6, r * 1.2, 10).rotateZ(Math.PI / 2), dark); w.position.set(x, -h, z); gear.add(w); };

  if (type === 'A320' || type === 'A330') {
    const k = type === 'A330' ? 1.69 : 1, R = 1.98 * k, L = 37.6 * k;
    add(new THREE.CylinderGeometry(R, R, L * .62, 20).rotateX(Math.PI / 2), body, 0, 0, L * .05);
    add(new THREE.SphereGeometry(R, 20, 14, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(Math.PI / 2).scale(1, .95, 1.7), body, 0, -R * .05, L * .36);
    add(new THREE.CylinderGeometry(R * .32, R, L * .3, 18).rotateX(-Math.PI / 2), body, 0, R * .32, -L * .41).rotation.x = -0.08;
    add(new THREE.BoxGeometry(R * 1.25, R * .28, R * .45), glass, 0, R * .42, L * .43);
    const span = 35.8 * (type === 'A330' ? 1.68 : 1) / 2;
    const wingR = [[R * .8, L * .06], [span, -L * .19], [span, -L * .26], [R * .8, -L * .1]];
    add(wingShape(wingR, .45 * k), body, 0, -R * .45, 0);
    add(wingShape(mirror(wingR), .45 * k), body, 0, -R * .45, 0);
    for (const sx of [1, -1]) {
      add(new THREE.BoxGeometry(.25, 2.4 * k, 1.6 * k), acc, sx * span, -R * .45 + 1.1 * k, -L * .235);
      const ex = sx * span * .34;
      add(new THREE.CylinderGeometry(1.05 * k, .85 * k, 4.4 * k, 16).rotateX(Math.PI / 2), body, ex, -R * 1.05, L * .03);
      add(new THREE.CircleGeometry(.95 * k, 16), dark, ex, -R * 1.05, L * .03 + 2.21 * k);
      add(new THREE.BoxGeometry(.35, R * .5, 2.5 * k), body, ex, -R * .7, L * .0);
    }
    const hs = [[R * .3, -L * .38], [6.2 * k, -L * .47], [6.2 * k, -L * .5], [R * .3, -L * .46]];
    add(wingShape(hs, .3 * k), body, 0, R * .5, 0);
    add(wingShape(mirror(hs), .3 * k), body, 0, R * .5, 0);
    add(finShape([[-L * .34, R * .7], [-L * .45, R * .7], [-L * .5, R * 3.4], [-L * .45, R * 3.4]], .35 * k), acc);
    strut(0, L * .33, R * .9, .3 * k); strut(R * 1.2, -L * .04, R * 1.1, .42 * k); strut(-R * 1.2, -L * .04, R * 1.1, .42 * k);
    lights.red.push([-span, -R * .4, -L * .2]); lights.green.push([span, -R * .4, -L * .2]); lights.strobe.push([0, R * .3, -L * .55]);
  } else if (type === 'ATR72' || type === 'DHC6') {
    const otter = type === 'DHC6', R = otter ? .95 : 1.35, L = otter ? 15.8 : 27.2, span = (otter ? 19.8 : 27.1) / 2;
    if (otter) add(new THREE.BoxGeometry(R * 1.9, R * 2, L * .62), body, 0, 0, L * .02);
    else add(new THREE.CylinderGeometry(R, R, L * .62, 18).rotateX(Math.PI / 2), body, 0, 0, L * .04);
    add(new THREE.SphereGeometry(R, 16, 12, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(Math.PI / 2).scale(otter ? 1.1 : 1, 1, 1.6), body, 0, 0, L * .35);
    add(new THREE.CylinderGeometry(R * .3, R, L * .3, 14).rotateX(-Math.PI / 2), body, 0, R * .25, -L * .42);
    add(new THREE.BoxGeometry(R * 1.3, R * .35, R * .5), glass, 0, R * .5, L * .38);
    const chord = otter ? 2 : 2.4, wy = R * 1.05;
    const wingR = [[R * .5, L * .1], [span, L * .1 - .3], [span, L * .1 - chord * .75], [R * .5, L * .1 - chord]];
    add(wingShape(wingR, .32), body, 0, wy + .3, 0);
    add(wingShape(mirror(wingR), .32), body, 0, wy + .3, 0);
    for (const sx of [1, -1]) {
      const nx = sx * (otter ? 3.0 : 4.1);
      add(new THREE.CylinderGeometry(.62, .5, otter ? 3 : 4.6, 12).rotateX(Math.PI / 2), body, nx, wy - .25, L * .1 - .3);
      const hub = new THREE.Group(); hub.position.set(nx, wy - .25, L * .1 + (otter ? 1.3 : 2.1)); g.add(hub);
      const blades = otter ? 3 : 6;
      for (let b = 0; b < blades; b++) { const bl = new THREE.Mesh(new THREE.BoxGeometry(.18, otter ? 1.3 : 1.95, .05).translate(0, otter ? .65 : .97, 0), dark); bl.rotation.z = b / blades * Math.PI * 2; hub.add(bl); }
      hub.add(new THREE.Mesh(new THREE.ConeGeometry(.28, .6, 10).rotateX(Math.PI / 2), acc));
      props.push(hub);
    }
    if (otter) {
      const hs = [[R * .3, -L * .4], [3.2, -L * .41], [3.2, -L * .48], [R * .3, -L * .48]];
      add(wingShape(hs, .2), body, 0, R * .4, 0); add(wingShape(mirror(hs), .2), body, 0, R * .4, 0);
      add(finShape([[-L * .34, R * .7], [-L * .46, R * .7], [-L * .5, R * 3.2], [-L * .43, R * 3.2]], .25), acc);
      strut(0, L * .33, R * 1.1, .28); strut(R * 1.6, -L * .02, R * 1.25, .35); strut(-R * 1.6, -L * .02, R * 1.25, .35);
    } else {
      add(finShape([[-L * .32, R * .7], [-L * .44, R * .7], [-L * .5, R * 4.0], [-L * .44, R * 4.0]], .3), acc);
      const hs = [[0, -L * .45], [3.8, -L * .47], [3.8, -L * .52], [0, -L * .51]];
      add(wingShape(hs, .2), body, 0, R * 4.0 + .1, 0); add(wingShape(mirror(hs), .2), body, 0, R * 4.0 + .1, 0);
      strut(0, L * .3, R * .9, .25); strut(R * 1.1, -L * .02, R * .9, .35); strut(-R * 1.1, -L * .02, R * .9, .35);
    }
    lights.red.push([-span, wy + .2, L * .02]); lights.green.push([span, wy + .2, L * .02]); lights.strobe.push([0, R * 3.6, -L * .48]);
    g.userData.fixedGear = otter;
  } else {
    add(new THREE.SphereGeometry(1.3, 18, 14).scale(1, 1.05, 1.75), acc, 0, 0, .6);
    add(new THREE.SphereGeometry(1.0, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(Math.PI / 2).scale(1.05, .9, 1.1), glass, 0, .1, 1.9);
    add(new THREE.CylinderGeometry(.18, .38, 5.6, 8).rotateX(-Math.PI / 2), acc, 0, .35, -3.6);
    add(finShape([[-5.8, .3], [-6.6, .3], [-6.9, 1.9], [-6.3, 1.9]], .12), acc);
    add(new THREE.BoxGeometry(.1, 1.7, .25), dark, .3, .6, -6.4);
    for (const sx of [1, -1]) {
      add(new THREE.CylinderGeometry(.07, .07, 3.4, 6).rotateX(Math.PI / 2), dark, sx * .9, -1.55, .5);
      add(new THREE.BoxGeometry(.08, .55, .08), dark, sx * .85, -1.25, 1.4); add(new THREE.BoxGeometry(.08, .55, .08), dark, sx * .85, -1.25, -.4);
    }
    add(new THREE.CylinderGeometry(.18, .18, .6, 8), dark, 0, 1.55, .4);
    const rotor = new THREE.Group(); rotor.position.set(0, 1.9, .4); g.add(rotor);
    for (let b = 0; b < 3; b++) { const bl = new THREE.Mesh(new THREE.BoxGeometry(5.35, .06, .32).translate(2.67, 0, 0), dark); bl.rotation.y = b / 3 * Math.PI * 2; rotor.add(bl); }
    props.push(rotor); g.userData.rotorY = true;
    lights.red.push([0, -.3, 2.4]); lights.strobe.push([0, 2.0, -6.5]);
    g.userData.fixedGear = true;
  }
  return g;
}

export function shortName(p) {
  if (!p.ifr) { const m = p.name.match(/via ([^,]+)/); return 'VFR via ' + (m ? m[1] : 'the valley'); }
  if (p.kind === 'dep') return p.name.split(' (')[0];
  return p.name.split(',')[0].replace(' (AR)', '').replace(/ RWY \d\d/, '');
}

export function createFlightSim({ scene, camera, meta, demH, demMin, state, glowTex, groundY }) {
  const F = meta.flight, P = meta.profiles, TYPES = F.types;
  const procs = {};
  for (const [k, p] of Object.entries(F.procs)) {
    const pts = p.pts, cum = [0];
    for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    procs[k] = { ...p, cum };
  }
  const root = new THREE.Group(); scene.add(root);
  const lineGroup = new THREE.Group(); scene.add(lineGroup);
  const spriteMat = c => new THREE.SpriteMaterial({ map: glowTex, color: c, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });

  let flights = [], events = [], rwy = '02', weather = 'clear';
  const RW = { '02': [F.rw02, F.rw20], '20': [F.rw20, F.rw02] };

  function schedule() {
    const rng = mulberry32(20261030), out = [];
    let id = 1;
    for (let h = 0; h < 24; h++) {
      const n = Math.floor(P.air_mov[h]) + (rng() < P.air_mov[h] % 1 ? 1 : 0);
      const day = h >= 6 && h < 19;
      for (let k = 0; k < n; k++) {
        const shares = {};
        for (const t of TYPE_ORDER) shares[t] = day || TYPES[t].cls === 'narrow' || TYPES[t].cls === 'wide' ? TYPES[t].share : 0;
        if (!day) shares.A320 += .15;
        const type = pick(rng, shares);
        out.push({ id: id++, type, op: rng() < .5 ? 'arr' : 'dep', t: (h + rng()) * 3600, r1: rng(), r2: rng(), r3: rng(), accent: ACCENTS[type][Math.floor(rng() * ACCENTS[type].length)] });
      }
    }
    return out.sort((a, b) => a.t - b.t);
  }
  const BASE = schedule();

  function pickW(r, weights) { let s = Object.values(weights).reduce((a, b) => a + b, 0), x = r * s; for (const [k, w] of Object.entries(weights)) { x -= w; if (x <= 0) return k; } return Object.keys(weights)[0]; }
  const cls = t => { const c = TYPES[t].cls; return c === 'narrow' || c === 'wide' ? 'jet' : c === 'turboprop' ? 'tp' : c; };

  function build() {
    flights = []; events = [];
    let lastRunway = -1e9;
    const thrZ = F.thr[rwy];
    for (const b of BASE) {
      const T = TYPES[b.type], c = cls(b.type);
      const f = { ...b, label: T.label, cls: c, procs: [] };
      if (c === 'heli') {
        const lane = pickW(b.r1, F.mix.heli), p = procs['H_' + lane];
        const inbound = b.op === 'arr';
        let pts = p.pts.map(q => q.slice()); if (inbound) pts.reverse();
        const pad = F.pad;
        const sp = pts.map(q => Math.max(T.vclimb * clamp01(Math.hypot(q[0] - pad[0], q[1] - pad[1]) / 700), 6));
        timeline(f, pts, sp);
        const off = inbound ? b.t - f.times[f.times.length - 1] : b.t - f.times[0];
        shift(f, off);
        f.procs.push(p.name + (inbound ? ', inbound' : ', outbound'));
        f.ev = [{ t: b.t, kind: inbound ? 'land' : 'dep', text: `${inbound ? 'Helicopter landed' : 'Helicopter lifted off'} · ${lane.replace('_H', '').replace('_K', ' Kilo')} lane` }];
        flights.push(f); continue;
      }
      let slot = Math.max(b.t, lastRunway + 120); lastRunway = slot;
      const [A, B] = RW[rwy], ux = (B[0] - A[0]) / Math.hypot(B[0] - A[0], B[1] - A[1]), uy = (B[1] - A[1]) / Math.hypot(B[0] - A[0], B[1] - A[1]);
      if (b.op === 'arr') {
        const key = pickW(b.r1, F.mix[rwy][c + '_arr']), p = procs[key];
        f.ga = b.r3 < F.go_around[weather];
        const segs = [{ pts: p.pts, ph: 'app' }];
        f.procs.push(p.name);
        if (f.ga) {
          const m = procs[(p.ifr ? 'MA' : 'GA') + rwy];
          segs.push({ pts: m.pts, ph: 'miss' }); f.procs.push(m.name);
          if (p.ifr) { const re = procs[rwy === '02' ? 'Z02_DANFE' : 'R20_DANFE']; segs.push({ pts: re.pts, ph: 'app' }); f.procs.push('then ' + re.name); }
        }
        const roll = [];
        for (let k = 1; k <= 12; k++) { const s = T.roll * k / 12; roll.push([A[0] + ux * s, A[1] + uy * s, thrZ]); }
        segs.push({ pts: roll, ph: 'roll' });
        const pts = [], sp = [], ph = [];
        for (const sg of segs) for (const q of sg.pts) {
          if (pts.length && Math.hypot(q[0] - pts[pts.length - 1][0], q[1] - pts[pts.length - 1][1]) < 1) continue;
          pts.push(q); ph.push(sg.ph);
        }
        const nRoll = roll.length;
        for (let i = 0; i < pts.length; i++) {
          const agl = pts[i][2] - thrZ;
          if (ph[i] === 'roll') { const k = (i - (pts.length - nRoll) + 1) / nRoll; sp.push(T.vapp * (1 - k) + 7 * k); }
          else if (ph[i] === 'miss') sp.push(T.vapp + (T.vclimb - T.vapp) * clamp01(agl / 1200));
          else sp.push(T.vapp + (T.vinit - T.vapp) * clamp01((agl - 150) / 1500));
        }
        timeline(f, pts, sp);
        const thrIdx = []; for (let i = 1; i < pts.length; i++) if (ph[i] !== 'roll' && Math.hypot(pts[i][0] - A[0], pts[i][1] - A[1]) < 30 && pts[i][2] - thrZ < 40) thrIdx.push(i);
        const firstThr = thrIdx.length ? thrIdx[0] : pts.length - nRoll - 1;
        shift(f, slot - f.times[firstThr]);
        const land = f.times[pts.length - nRoll];
        f.ev = [];
        if (f.ga) {
          f.ev.push({ t: f.times[firstThr], kind: 'ga', text: `Go-around RWY ${rwy} · ${T.label.split(' /')[0]} · ${shortName(p)}` });
          lastRunway = Math.max(lastRunway, land);
        }
        f.ev.push({ t: land, kind: 'land', text: `Landed RWY ${rwy} · ${T.label.split(' /')[0]} · ${f.ga ? 'after a go-around' : shortName(p)}` });
      } else {
        const key = pickW(b.r1, F.mix[rwy][c + '_dep']), p = procs[key];
        f.procs.push(p.name);
        const cap = (p.ifr ? 15000 : 8500) * FT;
        const pts = p.pts.map((q, i) => [q[0], q[1], Math.min(thrZ + Math.max(p.cum[i] - T.rot, 0) * T.grad, cap)]);
        const sp = pts.map((q, i) => p.cum[i] < T.rot ? Math.max(T.vr * Math.sqrt(p.cum[i] / T.rot), 4) : T.vr + (T.vclimb - T.vr) * clamp01((q[2] - thrZ) / 1500));
        timeline(f, pts, sp);
        shift(f, slot - f.times[0]);
        const ri = p.cum.findIndex(d => d >= T.rot);
        f.ev = [{ t: f.times[Math.max(ri, 0)], kind: 'dep', text: `Took off RWY ${rwy} · ${T.label.split(' /')[0]} · ${shortName(p)}` }];
      }
      flights.push(f);
    }
    for (const f of flights) for (const e of f.ev) events.push({ ...e, f });
    events.sort((a, b) => a.t - b.t);
    flights.sort((a, b) => a.t0 - b.t0);
    drawProcedures();
  }

  function timeline(f, pts, sp) {
    const n = pts.length, P3 = new Float32Array(n * 3), T = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      P3[i * 3] = pts[i][0]; P3[i * 3 + 1] = pts[i][1]; P3[i * 3 + 2] = pts[i][2];
      if (i) { const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1], pts[i][2] - pts[i - 1][2]); T[i] = T[i - 1] + d / Math.max((sp[i] + sp[i - 1]) / 2, 2); }
    }
    f.pts = P3; f.times = T; f.t0 = T[0]; f.t1 = T[n - 1];
  }
  function shift(f, dt) { for (let i = 0; i < f.times.length; i++) f.times[i] += dt; f.t0 = f.times[0]; f.t1 = f.times[f.times.length - 1]; }

  function sample(f, t, out) {
    const T = f.times; let lo = 0, hi = T.length - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (T[m] <= t) lo = m; else hi = m; }
    const k = clamp01((t - T[lo]) / Math.max(T[hi] - T[lo], 1e-6)), a = lo * 3, b = hi * 3, p = f.pts;
    out.x = p[a] + (p[b] - p[a]) * k; out.y = p[a + 1] + (p[b + 1] - p[a + 1]) * k; out.z = p[a + 2] + (p[b + 2] - p[a + 2]) * k;
    const d = Math.hypot(p[b] - p[a], p[b + 1] - p[a + 1]);
    out.hx = d > .01 ? (p[b] - p[a]) / d : 0; out.hy = d > .01 ? (p[b + 1] - p[a + 1]) / d : 1;
    out.climb = (p[b + 2] - p[a + 2]) / Math.max(T[hi] - T[lo], 1e-6);
    out.speed = Math.hypot(p[b] - p[a], p[b + 1] - p[a + 1], p[b + 2] - p[a + 2]) / Math.max(T[hi] - T[lo], 1e-6);
    out.i = lo;
    return out;
  }

  const pools = {}, live = new Map();
  function acquire(f) {
    const pool = pools[f.type] || (pools[f.type] = []);
    let o = pool.pop();
    if (!o) {
      o = buildModel(f.type, f.accent);
      const L = o.userData.lights;
      o.userData.sprites = [
        ...L.red.map(p => { const s = new THREE.Sprite(spriteMat(0xff3b30)); s.position.set(...p); o.add(s); return s; }),
        ...L.green.map(p => { const s = new THREE.Sprite(spriteMat(0x34c759)); s.position.set(...p); o.add(s); return s; }),
        ...L.strobe.map(p => { const s = new THREE.Sprite(spriteMat(0xffffff)); s.position.set(...p); s.userData.strobe = true; o.add(s); return s; }),
      ];
      const halo = new THREE.Sprite(spriteMat(0xffd9a0)); halo.scale.set(70, 70, 1); o.add(halo); o.userData.halo = halo;
    }
    o.traverse(m => { if (m.material && m.material.color && m.material.metalness === .2 && m.material.roughness === .5) m.material.color.set(f.accent); });
    root.add(o); return o;
  }
  function release(f, o) { root.remove(o); (pools[f.type] || (pools[f.type] = [])).push(o); }

  const ringGeo = new THREE.RingGeometry(0.93, 1, 96); ringGeo.rotateX(-Math.PI / 2);
  const rings = [];
  for (let i = 0; i < 160; i++) {
    const r = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({ color: 0xec7826, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide }));
    r.visible = false; r.userData = { t: 1, life: 1, R: 1 }; root.add(r); rings.push(r);
  }
  let ringIdx = 0;

  const S = {};
  function lamaxBelow(f, z, x, y) {
    const T = TYPES[f.type], agl = Math.max(z - (demH(x, y) + demMin), 30), dep = f.op === 'dep';
    return (dep ? T.sel_dep : T.sel_app) - 9 - 22 * Math.log10(Math.max(agl, 60) / 300);
  }

  function update(dt, simT, realT) {
    const on = state.flights && state.on[1];
    const active = new Set();
    if (on) for (const f of flights) { if (f.t0 > simT) break; if (f.t1 >= simT) active.add(f); }
    for (const [f, o] of live) if (!active.has(f)) { release(f, o); live.delete(f); }
    const camPos = camera.position;
    for (const f of active) {
      let o = live.get(f);
      if (!o) { o = acquire(f); live.set(f, o); o.userData.ringT = Math.random() * .3; }
      sample(f, simT, S);
      const ground = demH(S.x, S.y), gy = groundY(S.x, S.y);
      const y = Math.max((S.z - demMin) * state.exag, gy + 2.5);
      o.position.set(S.x, y, -S.y);
      const ahead = new THREE.Vector3(S.x + S.hx * 50, y + (f.cls === 'heli' ? 0 : S.climb / Math.max(S.speed, 1) * 50 * state.exag), -(S.y + S.hy * 50));
      o.lookAt(ahead);
      if (f.cls === 'heli') o.rotateX(Math.min(S.speed / 55, 1) * .12);
      const agl = S.z - (ground + demMin);
      o.scale.setScalar(THREE.MathUtils.clamp(camPos.distanceTo(o.position) / 1100, 1, 14));
      const gearDown = o.userData.fixedGear || agl < (f.op === 'arr' ? 700 : 250);
      o.userData.gear.visible = gearDown;
      for (const pr of o.userData.props) o.userData.rotorY ? pr.rotation.y += dt * 40 : pr.rotation.z += dt * 55;
      for (const s of o.userData.sprites) {
        const k = THREE.MathUtils.clamp(camPos.distanceTo(o.position) / 260, 4, 60);
        s.scale.set(k, k, 1).divideScalar(o.scale.x);
        if (s.userData.strobe) s.material.opacity = (realT * 1.1 + f.id * .37) % 1 < .08 ? 1 : 0;
      }
      const cd = camPos.distanceTo(o.position);
      o.userData.halo.material.opacity = cd < 1500 ? .12 : .3 + (agl < 900 ? .25 : 0);
      o.userData.halo.scale.setScalar(THREE.MathUtils.clamp(cd / 14, 20, 420) / o.scale.x);
      o.userData.state = { ...S, agl };
      o.userData.ringT -= dt;
      if (o.userData.ringT <= 0 && agl < 2600) {
        o.userData.ringT = .32;
        const sel = f.op === 'dep' ? TYPES[f.type].sel_dep : TYPES[f.type].sel_app, R65 = 300 * Math.pow(10, (sel - 74) / 22), R = Math.sqrt(Math.max(R65 * R65 - agl * agl, 0));
        if (R > 60) {
          const r = rings[ringIdx = (ringIdx + 1) % rings.length];
          r.position.set(S.x, gy + 5, -S.y); r.material.color.set(f.ga && S.i > 0 ? 0xe5534b : f.op === 'dep' ? 0x3987e5 : 0xec7826);
          r.userData = { t: 0, life: 2.2, R }; r.visible = true;
        }
      }
    }
    for (const r of rings) if (r.visible) {
      const u = r.userData; u.t += dt / u.life;
      if (u.t >= 1 || !on) { r.visible = false; continue; }
      const s = u.R * (0.15 + 0.85 * Math.sqrt(u.t)); r.scale.set(s, 1, s); r.material.opacity = .5 * (1 - u.t);
    }
    return active;
  }

  function drawProcedures() {
    lineGroup.clear();
    const want = Object.entries(procs).filter(([k, p]) => p.rwy === rwy || p.kind === 'heli');
    for (const [k, p] of want) {
      const pts = p.pts.map(q => new THREE.Vector3(q[0], (q[2] - demMin) * state.exag, -q[1]));
      const geo = new THREE.BufferGeometry().setFromPoints(pts);
      const mat = p.ifr ? new THREE.LineBasicMaterial({ color: KIND_COLOR[p.kind], transparent: true, opacity: p.kind === 'miss' ? .55 : .5, depthWrite: false })
        : new THREE.LineDashedMaterial({ color: KIND_COLOR[p.kind], dashSize: 90, gapSize: 70, transparent: true, opacity: .55, depthWrite: false });
      const line = new THREE.Line(geo, mat);
      if (!p.ifr) line.computeLineDistances();
      line.userData.key = k; lineGroup.add(line);
    }
  }

  const v = new THREE.Vector3();
  function pickAt(cx, cy) {
    let best = null, bd = 30;
    for (const [f, o] of live) {
      v.copy(o.position).project(camera);
      if (v.z > 1) continue;
      const sx = (v.x + 1) / 2 * innerWidth, sy = (1 - v.y) / 2 * innerHeight, d = Math.hypot(sx - cx, sy - cy);
      if (d < bd) { bd = d; best = f; }
    }
    return best;
  }

  function info(f, simT) {
    const o = live.get(f), st = o ? o.userData.state : sample(f, Math.min(Math.max(simT, f.t0), f.t1), {});
    const thr = F.thr[rwy];
    let phase;
    if (simT < f.t0) phase = 'Scheduled';
    else if (simT > f.t1) phase = 'Completed';
    else if (f.cls === 'heli') phase = st.agl < 30 ? 'On the pad' : st.climb > 1 ? 'Climbing out' : st.climb < -1 ? 'Descending' : 'Cruising on lane';
    else if (f.op === 'dep') phase = st.z - thr < 5 ? 'Take-off roll' : 'Climbing out';
    else {
      const ga = f.ev.find(e => e.kind === 'ga');
      phase = st.z - thr < 3 ? 'Landing roll' : ga && simT > ga.t && simT < f.ev[f.ev.length - 1].t ? (st.climb > .5 ? 'Go-around, climbing' : 'Re-positioning after go-around') : st.z - thr < 300 ? 'Short final' : 'On approach';
    }
    return { phase, alt: st.z / FT, agl: st.agl ?? 0, kt: (st.speed || 0) * 1.944, vs: (st.climb || 0) / FT * 60, lamax: lamaxBelow(f, st.z, st.x, st.y), pos: st };
  }

  function counts(simT) {
    const c = { land: 0, dep: 0, ga: 0, heli: 0 };
    for (const e of events) { if (e.t > simT) break; if (e.f.cls === 'heli') c.heli++; else c[e.kind]++; }
    return c;
  }

  function setRunway(r) { rwy = r; build(); }
  function setWeather(w) { weather = w; build(); }
  build();

  return {
    update, pickAt, info, counts, setRunway, setWeather, drawProcedures, sample,
    get events() { return events; }, get flights() { return flights; }, get rwy() { return rwy; }, get weather() { return weather; },
    live, lineGroup, root,
  };
}
