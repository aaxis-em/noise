"""
Screening-level environmental noise model for Kathmandu + Lalitpur.

Inputs  : OpenStreetMap extracts in ../raw (Overpass JSON) + Terrarium DEM tiles.
Outputs : ../web/data/*  (binary grids + JSON consumed by the Three.js viewer)

Sources modelled
  road      line sources per OSM highway class, Kathmandu-calibrated emission at 10 m
  aircraft  TIA runway 02/20 approach / departure tracks, fleet mix, NPD-style SEL decay
  activity  bus parks, marketplaces, industrial + commercial land use, busy junctions

Propagation: energy summation of 1/r^2 point kernels (=> 1/r for lines) with an
urban excess-attenuation term (building screening + ground), done via FFT convolution.
This is a modelled estimate for exploration, not a substitute for measurements.
"""
import json, math, os, struct, glob
import numpy as np
from scipy.signal import fftconvolve
from PIL import Image
from matplotlib.path import Path

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "raw")
OUT = os.path.join(HERE, "..", "web", "data")
os.makedirs(OUT, exist_ok=True)

S, W, N, E = 27.635, 85.265, 27.765, 85.405
LAT0, LON0 = (S + N) / 2, (W + E) / 2
KX = 111320.0 * math.cos(math.radians(LAT0))
KY = 110574.0
RES = 20.0  # metres per cell


def xy(lat, lon):
    return (lon - LON0) * KX, (lat - LAT0) * KY


X0, Y0 = xy(S, W)
X1, Y1 = xy(N, E)
NX = int(math.ceil((X1 - X0) / RES))
NY = int(math.ceil((Y1 - Y0) / RES))
print("grid", NX, NY)


def cell(x, y):
    return (x - X0) / RES, (y - Y0) / RES


def load(name):
    with open(os.path.join(RAW, name)) as f:
        return json.load(f)["elements"]


def db(e):
    return 10 * np.log10(np.maximum(e, 1e-30))


def en(l):
    return 10 ** (np.asarray(l) / 10.0)


# ---------------------------------------------------------------- kernel
# Energy kernel for a point source: 1/r^2 * exp(-r/lambda). Integrated along a
# line this gives the 1/r (3 dB per doubling) law plus urban excess attenuation.
EXCESS_DB_PER_M = 0.016  # soft ground + air absorption + scattering
SCREEN_DB = 9.0          # first-row building screening: receivers behind the street wall
KR = 1800.0
kr = int(KR / RES)
ky_, kx_ = np.mgrid[-kr:kr + 1, -kr:kr + 1]
r = np.hypot(kx_, ky_) * RES
R_MIN = 6.0
K = 1.0 / np.maximum(r, R_MIN) ** 2 * 10 ** (-(EXCESS_DB_PER_M * r + SCREEN_DB * (1 - np.exp(-np.maximum(r - 12, 0) / 30))) / 10)
K[r > KR] = 0


def propagate(src):
    return np.maximum(fftconvolve(src, K, mode="same"), 0)


# calibration: straight infinite-ish line rasterised at unit energy/m.
# Choose C so that the level 10 m off the line == emission level LE.
_t = np.zeros((401, 401))
_t[200, :] = RES  # metres of line in each cell
_p = fftconvolve(_t, K, mode="same")
_ref = (_p[200, 200] * 0.5 + _p[201, 200] * 0.5)  # ~10 m from the line centre
LINE_CAL = 1.0 / _ref
print("line calibration", LINE_CAL)
# point calibration: level at 10 m from a point source == L10
_t[:] = 0
_t[200, 200] = 1
_p = fftconvolve(_t, K, mode="same")
PT_CAL = 1.0 / (0.5 * (_p[200, 200] + _p[200, 201]))

# ---------------------------------------------------------------- roads
# LAeq,day emission 10 m from the kerb, dB(A). Anchored to Kathmandu surveys:
# Ring Road junctions all > 70 dB(A); Kupondole ~79, New Road ~80 dB(A) at peak.
EMIS = {
    "trunk": 76.0, "trunk_link": 71, "motorway": 76, "motorway_link": 71,
    "primary": 75.0, "primary_link": 70, "secondary": 72.0, "secondary_link": 68,
    "tertiary": 68.5, "tertiary_link": 65, "unclassified": 61.5,
    "residential": 55.5, "living_street": 52, "service": 49,
}
roads = load("roads.json")
road_src = np.zeros((NY, NX))
road_out = []  # for the viewer
named = {}


def raster_line(arr, pts, w):
    """deposit w * length (energy) into cells along polyline pts (cell coords)."""
    for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
        L = math.hypot(bx - ax, by - ay)
        n = max(1, int(L * 2))
        seg = L * RES / n
        for i in range(n):
            t = (i + 0.5) / n
            cx, cy = int(ax + (bx - ax) * t), int(ay + (by - ay) * t)
            if 0 <= cx < NX and 0 <= cy < NY:
                arr[cy, cx] += w * seg


CLS = {k: i for i, k in enumerate(["trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "service"])}


def cls_of(h):
    h = h.replace("_link", "").replace("motorway", "trunk").replace("living_street", "residential")
    return CLS.get(h, 6)


for w in roads:
    t = w["tags"]
    h = t["highway"]
    LE = EMIS.get(h, 54)
    try:
        lanes = float(str(t.get("lanes", "")).split(";")[0])
        if h in ("trunk", "primary", "secondary") and lanes > 2:
            LE += 10 * math.log10(lanes / 2) * 0.7
    except ValueError:
        pass
    if t.get("surface") in ("unpaved", "dirt", "gravel", "ground"):
        LE += 1.0  # rough surface, potholes, horn use
    if t.get("oneway") == "yes" and h.split("_")[0] in ("trunk", "primary", "secondary"):
        LE -= 3  # dual carriageway mapped as two one-way ways: each carries ~half the flow
    elif t.get("oneway") == "yes":
        LE -= 1
    g = w["geometry"]
    pts_xy = [xy(p["lat"], p["lon"]) for p in g]
    pts = [cell(*p) for p in pts_xy]
    raster_line(road_src, pts, en(LE) * LINE_CAL)
    length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts_xy[:-1], pts_xy[1:]))
    road_out.append((cls_of(h), pts_xy, LE))
    nm = t.get("name:en") or t.get("name")
    if nm and h in ("trunk", "primary", "secondary", "tertiary"):
        d = named.setdefault(nm, {"len": 0, "LE": 0, "pts": [], "cls": h})
        d["len"] += length
        d["LE"] = max(d["LE"], LE)
        d["pts"].append(pts_xy[len(pts_xy) // 2])

# junction hotspots: horn use, idling and acceleration at signalised / major nodes
node_count = {}
for w in roads:
    if w["tags"]["highway"] in ("trunk", "primary", "secondary"):
        for nid in (w.get("nodes") or []):
            node_count[nid] = node_count.get(nid, 0) + 1
feat = load("feat.json")

# ---------------------------------------------------------------- activity
act_src = np.zeros((NY, NX))
pois = []  # sensitive receptors + sources for viewer


def centroid(e):
    if "lat" in e:
        return e["lat"], e["lon"]
    if "center" in e:
        return e["center"]["lat"], e["center"]["lon"]
    if "geometry" in e and e["geometry"]:
        g = [p for p in e["geometry"] if p]
        return sum(p["lat"] for p in g) / len(g), sum(p["lon"] for p in g) / len(g)
    if "bounds" in e:
        b = e["bounds"]
        return (b["minlat"] + b["maxlat"]) / 2, (b["minlon"] + b["maxlon"]) / 2
    return None


def poly_fill(arr, e, w_per_m2):
    g = e.get("geometry") or []
    if len(g) < 3:
        return
    P = np.array([cell(*xy(p["lat"], p["lon"])) for p in g])
    x0, y0 = np.floor(P.min(0)).astype(int)
    x1, y1 = np.ceil(P.max(0)).astype(int)
    x0, y0 = max(x0, 0), max(y0, 0)
    x1, y1 = min(x1, NX - 1), min(y1, NY - 1)
    if x1 <= x0 or y1 <= y0:
        return
    gy, gx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
    m = Path(P).contains_points(np.c_[gx.ravel() + 0.5, gy.ravel() + 0.5]).reshape(gx.shape)
    arr[y0:y1 + 1, x0:x1 + 1][m] += w_per_m2 * RES * RES


def point_src(arr, lat, lon, L10):
    cx, cy = cell(*xy(lat, lon))
    cx, cy = int(cx), int(cy)
    if 0 <= cx < NX and 0 <= cy < NY:
        arr[cy, cx] += en(L10) * PT_CAL


# area emission expressed as level at 10 m from a 100 m^2 patch (dB per area)
AREA_L = {"industrial": 64, "commercial": 60, "retail": 60}
for e in feat:
    t = e.get("tags", {})
    c = centroid(e)
    if not c:
        continue
    lat, lon = c
    am = t.get("amenity") or ("hospital" if t.get("healthcare") == "hospital" else None)
    lu = t.get("landuse")
    if lu in AREA_L and e["type"] == "way":
        poly_fill(act_src, e, en(AREA_L[lu]) * PT_CAL / 100.0)
    if am == "bus_station":
        point_src(act_src, lat, lon, 76)  # diesel idling, conductors calling routes, horns
        pois.append(("bus", lat, lon, t.get("name:en") or t.get("name") or "Bus park"))
    elif am == "marketplace":
        point_src(act_src, lat, lon, 72)
        pois.append(("market", lat, lon, t.get("name:en") or t.get("name") or "Market"))
    elif am in ("hospital",):
        pois.append(("hospital", lat, lon, t.get("name:en") or t.get("name") or "Hospital"))
    elif am in ("school", "college", "university", "kindergarten"):
        nm = t.get("name:en") or t.get("name")
        if nm:
            pois.append(("school", lat, lon, nm))
    elif t.get("highway") == "traffic_signals":
        point_src(act_src, lat, lon, 74)
    elif t.get("place") in ("suburb", "neighbourhood", "quarter", "town", "city"):
        nm = t.get("name:en") or t.get("name")
        if nm:
            pois.append(("place", lat, lon, nm))
    elif t.get("leisure") == "stadium":
        point_src(act_src, lat, lon, 66)

# major junction hotspots (3+ major ways meet): idling, acceleration, horn use
ends = {}
for w in roads:
    if w["tags"]["highway"] not in ("trunk", "primary", "secondary"):
        continue
    for p in (w["geometry"][0], w["geometry"][-1]):
        k = (round(p["lat"], 4), round(p["lon"], 4))
        ends[k] = ends.get(k, 0) + 1
jn = 0
for (la, lo), c in ends.items():
    if c >= 3:
        point_src(act_src, la, lo, 68 + min(c - 3, 3))
        jn += 1
print("junction hotspots", jn)

# street commerce + nightlife from OSM shops / venues
night_src = np.zeros((NY, NX))
NIGHT_L = {"bar": 66, "pub": 66, "nightclub": 76, "restaurant": 54, "cafe": 50, "fast_food": 52}
nshop = 0
for e in load("shops.json"):
    t = e.get("tags", {})
    c = centroid(e)
    if not c:
        continue
    am = t.get("amenity")
    if am in NIGHT_L:
        point_src(night_src, c[0], c[1], NIGHT_L[am])
    elif "shop" in t:
        point_src(act_src, c[0], c[1], 58)  # shopfront speakers, hawkers, crowds
        nshop += 1
print("shops", nshop)

# ---------------------------------------------------------------- propagate
print("propagating road...")
road_e = propagate(road_src)
print("propagating activity...")
act_e = propagate(act_src)
night_e = propagate(night_src)

L_road = db(road_e)           # LAeq day-average hour
L_act = db(act_e)
L_night = db(night_e)

# ---------------------------------------------------------------- terrain
dem_files = glob.glob(os.path.join(RAW, "dem", "13_*.png"))
Z = 13
tiles = {}
for f in dem_files:
    _, x, y = os.path.basename(f)[:-4].split("_")
    im = np.asarray(Image.open(f).convert("RGB")).astype(np.float64)
    tiles[(int(x), int(y))] = im[..., 0] * 256 + im[..., 1] + im[..., 2] / 256 - 32768


def elev(lat, lon):
    n = 2 ** Z
    fx = (lon + 180) / 360 * n
    fy = (1 - np.arcsinh(np.tan(np.radians(lat))) / math.pi) / 2 * n
    tx, ty = np.floor(fx).astype(int), np.floor(fy).astype(int)
    px = np.clip(((fx - tx) * 256).astype(int), 0, 255)
    py = np.clip(((fy - ty) * 256).astype(int), 0, 255)
    out = np.full(np.shape(lat), 1330.0)
    for (x, y), im in tiles.items():
        m = (tx == x) & (ty == y)
        out[m] = im[py[m], px[m]]
    return out


DEM_RES = 40.0
dnx, dny = int(NX * RES / DEM_RES) + 1, int(NY * RES / DEM_RES) + 1
dy_, dx_ = np.mgrid[0:dny, 0:dnx]
dlon = LON0 + (X0 + dx_ * DEM_RES) / KX
dlat = LAT0 + (Y0 + dy_ * DEM_RES) / KY
H = elev(dlat, dlon) if tiles else np.full((dny, dnx), 1330.0)
print("terrain", H.min(), H.max(), H.shape)
HMIN = float(H.min())

# ---------------------------------------------------------------- aircraft
rw = [e for e in feat if e.get("tags", {}).get("aeroway") == "runway"]
rw = max(rw, key=lambda e: len(e["geometry"]))
g = rw["geometry"]
A = np.array(xy(g[0]["lat"], g[0]["lon"]))
B = np.array(xy(g[-1]["lat"], g[-1]["lon"]))
if A[1] > B[1]:
    A, B = B, A  # A = south threshold (RWY 02), B = north threshold (RWY 20)
U = (B - A) / np.linalg.norm(B - A)
RWLEN = float(np.linalg.norm(B - A))
hdg = (math.degrees(math.atan2(U[0], U[1])) + 360) % 360
print("runway length %.0f m, heading %.1f" % (RWLEN, hdg))

gy, gx = np.mgrid[0:NY, 0:NX]
PX = X0 + (gx + 0.5) * RES
PY = Y0 + (gy + 0.5) * RES

import flightpaths as fp


def elev_xy(x, y):
    return float(elev(np.atleast_1d(LAT0 + y / KY), np.atleast_1d(LON0 + x / KX))[0])


geom = fp.Geometry(xy, elev_xy)
MOV_PER_HOUR = 25.0
RWY02_SHARE = 0.75
ARES = 40.0
anx, any_ = int(math.ceil(NX * RES / ARES)), int(math.ceil(NY * RES / ARES))
GX = (X0 + (np.arange(anx) + 0.5) * ARES)[None, :].repeat(any_, 0).astype(np.float32)
GY = (Y0 + (np.arange(any_) + 0.5) * ARES)[:, None].repeat(anx, 1).astype(np.float32)
GZ = (H[:any_, :anx] if H.shape[0] >= any_ and H.shape[1] >= anx else np.full(GX.shape, 1330.0)).astype(np.float32)
SEL_CAL = 1.0 / (1.887 * 300.0 ** -2.2)


def unit_field(pts, roll=None):
    P = [tuple(p) for p in pts]
    if roll:
        a, b = roll
        z = P[-1][2]
        for k in range(1, 15):
            t = k / 15 * 0.6
            P.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, z))
    P = np.array(P, np.float32)
    seg = np.r_[0, np.hypot(np.diff(P[:, 0]), np.diff(P[:, 1]))]
    ds = (seg + np.r_[seg[1:], 0]) / 2
    keep = np.hypot(P[:, 0], P[:, 1]) < 32000
    E = np.zeros(GX.shape, np.float32)
    for (x, y, z), d in zip(P[keep], ds[keep]):
        hz = np.hypot(GX - x, GY - y)
        dz = z - GZ
        r = np.maximum(np.hypot(hz, dz), 60)
        ang = np.degrees(np.arctan2(np.maximum(dz, 0), hz + 1))
        att = np.where(ang < 30, (30 - ang) / 30 * 7.0, 0)
        E += d * r ** -3.2 * 10 ** (-att / 10)
    return E * SEL_CAL


cache = {}
procs = fp.build_all(geom)


def field(key, typ=None):
    k = (key, typ)
    if k not in cache:
        if typ and key in fp.DEPARTURES:
            p = geom.departure(key, fp.TYPES[typ]["grad"], fp.TYPES[typ]["rot"])
        elif typ and key in fp.VFR and fp.VFR[key][2] == "dep":
            p = geom.vfr(key, fp.TYPES[typ]["grad"], fp.TYPES[typ]["rot"])
        else:
            p = procs[key]
        cache[k] = unit_field(p["pts"], p.get("roll"))
    return cache[k]


def air_energy(rwy):
    E = np.zeros(GX.shape, np.float32)
    mix = fp.MIX[rwy]
    for t, T in fp.TYPES.items():
        n = MOV_PER_HOUR * T["share"] / 2
        ea, ed = 10 ** (T["sel_app"] / 10), 10 ** (T["sel_dep"] / 10)
        c = fp.class_key(t)
        if c == "heli":
            for lane, w in fp.MIX["heli"].items():
                E += 2 * n * w * ed * field("H_" + lane)
            continue
        for route, w in mix[c + "_arr"].items():
            E += n * w * ea * field(route)
            ga = "MA" + rwy if procs[route]["ifr"] else "GA" + rwy
            E += n * w * fp.GO_AROUND["clear"] * ed * field(ga)
        for route, w in mix[c + "_dep"].items():
            E += n * w * ed * field(route, t)
    E /= 3600.0
    from scipy.ndimage import zoom
    up = zoom(10 * np.log10(np.maximum(E, 1e-12)), (NY / any_, NX / anx), order=1)
    return en(up[:NY, :NX])


print("aircraft noise on published procedures...")
air02_e, air20_e = air_energy("02"), air_energy("20")
print("aircraft fields", len(cache))
air_e = RWY02_SHARE * air02_e + (1 - RWY02_SHARE) * air20_e
L_air = db(air_e)
L_air02, L_air20 = db(air02_e), db(air20_e)


def proc_out(p):
    return {"name": p["name"], "rwy": p["rwy"], "kind": p["kind"], "ifr": p["ifr"],
            "pts": [[round(x), round(y), round(z)] for x, y, z in p["pts"]],
            "roll": [[round(v) for v in a] for a in p["roll"]] if p.get("roll") else None}


flight_meta = {
    "procs": {k: proc_out(p) for k, p in procs.items()},
    "types": fp.TYPES, "mix": fp.MIX, "go_around": fp.GO_AROUND, "rwy02_share": RWY02_SHARE,
    "thr": geom.thr, "pad": [round(v) for v in geom.pad],
    "rw02": [round(v) for v in geom.p["RW02"]], "rw20": [round(v) for v in geom.p["RW20"]],
    "source": "CAAN AIP Nepal VNKT AD 2 (AMDT 03/2022): RNP AR coding tables, AD 2.23 valley passes, heli-lanes",
    "approx": ["BHARATPUR_PASS", "KAKANI_PASS"],
}

# ---------------------------------------------------------------- diurnal profiles
# dB offset from the daytime-average hour, per clock hour 0..23 (Nepal Time)
ROAD_H = [-10, -12, -13, -13, -11, -6.5, -3, -0.8, 0.6, 1.6, 1.6, 1.0, 0.6, 0.4, 0.4, 0.6, 1.1, 1.7, 1.6, 0.4, -1.6, -3.6, -5.5, -7.8]
AIR_MOV = [1, 0.5, 0.5, 0.5, 1, 5, 26, 33, 30, 27, 25, 24, 23, 23, 24, 25, 26, 26, 24, 21, 16, 10, 7, 3]  # movements/h
ACT_H = [-14, -15, -15, -15, -13, -8, -4, -1.5, 0, 1, 1.2, 1.2, 1, 1, 1, 1, 1.2, 1.4, 1, -1, -3, -6, -9, -12]
NIGHT_H = [-1, -4, -9, -14, -18, -20, -20, -18, -14, -10, -8, -7, -6, -6, -6, -6, -5, -4, -2, 0, 1, 1.5, 1.5, 1]
BG_DAY, BG_NIGHT = 46.0, 38.0  # residual urban hum (dogs, generators, distant traffic)
BG_H = [BG_NIGHT + (BG_DAY - BG_NIGHT) * max(0, min(1, (h - 5) / 3 if h < 12 else (23 - h) / 3)) for h in range(24)]


def hour_level(h, road=1, air=1, act=1, night=1, bg=1):
    e = en(BG_H[h]) if bg else 1e-3
    if road:
        e = e + en(L_road + ROAD_H[h])
    if air:
        e = e + en(L_air + 10 * math.log10(AIR_MOV[h] / MOV_PER_HOUR))
    if act:
        e = e + en(L_act + ACT_H[h])
    if night:
        e = e + en(L_night + NIGHT_H[h])
    return e


def lden_lnight(**kw):
    hrs = [hour_level(h, **kw) for h in range(24)]
    day = sum(hrs[h] for h in range(7, 19)) / 12
    eve = sum(hrs[h] for h in range(19, 23)) / 4
    nig = sum(hrs[h] for h in list(range(23, 24)) + list(range(0, 7))) / 8
    lden = db((12 * day + 4 * eve * 10 ** 0.5 + 8 * nig * 10) / 24)
    return lden, db(nig), db(day)


Lden, Lnight, Lday = lden_lnight()
Lden_air, Lnight_air, _ = lden_lnight(road=0, act=0, night=0, bg=0)
Lden_road, Lnight_road, _ = lden_lnight(air=0, act=0, night=0, bg=0)
print("Lden range", Lden.min(), Lden.max())

# ---------------------------------------------------------------- buildings
print("buildings...")
bpath = os.path.join(RAW, "bbb.json")
if not os.path.exists(bpath) or os.path.getsize(bpath) < 1e6:
    bpath = os.path.join(RAW, "bcenter.json")
bld = load(bpath)
bx, by, bw, bd, blv = [], [], [], [], []
for e in bld:
    t = e.get("tags", {})
    if "bounds" in e:
        b = e["bounds"]
        x0_, y0_ = xy(b["minlat"], b["minlon"])
        x1_, y1_ = xy(b["maxlat"], b["maxlon"])
        cx_, cy_ = (x0_ + x1_) / 2, (y0_ + y1_) / 2
        w_, d_ = (x1_ - x0_) * 0.82, (y1_ - y0_) * 0.82
    else:
        c = centroid(e)
        if not c:
            continue
        cx_, cy_ = xy(*c)
        w_ = d_ = 9
    lv = None
    try:
        lv = float(str(t.get("building:levels", "")).split(";")[0])
    except ValueError:
        pass
    if not lv:
        try:
            lv = float(str(t.get("height", "")).replace("m", "")) / 3.0
        except ValueError:
            lv = None
    if not lv:
        hsh = (e["id"] * 2654435761) & 0xFFFF
        lv = 2 + (hsh % 4) if t.get("building") not in ("school", "commercial", "apartments", "hospital") else 4 + hsh % 3
    bx.append(cx_); by.append(cy_)
    bw.append(min(max(w_, 3), 60)); bd.append(min(max(d_, 3), 60)); blv.append(min(max(lv, 1), 25))
bx, by, bw, bd, blv = map(np.array, (bx, by, bw, bd, blv))
inside = (bx > X0) & (bx < X1) & (by > Y0) & (by < Y1)
bx, by, bw, bd, blv = bx[inside], by[inside], bw[inside], bd[inside], blv[inside]
bi = np.clip(((bx - X0) / RES).astype(int), 0, NX - 1)
bj = np.clip(((by - Y0) / RES).astype(int), 0, NY - 1)
b_lden = Lden[bj, bi]
b_lnight = Lnight[bj, bi]
print("buildings", len(bx))

# building density per cell -> used by viewer for shading
dens = np.zeros((NY, NX))
np.add.at(dens, (bj, bi), bw * bd)
dens = np.clip(dens / (RES * RES), 0, 1)

# ---------------------------------------------------------------- municipalities
adm = load("adm.json")


def rel_polys(rel):
    """stitch outer ways of a multipolygon relation into rings (x,y)."""
    ways = [m["geometry"] for m in rel.get("members", []) if m.get("type") == "way" and m.get("role") in ("outer", "") and m.get("geometry")]
    ways = [[(p["lat"], p["lon"]) for p in w] for w in ways]
    rings = []
    while ways:
        ring = ways.pop(0)
        changed = True
        while changed and ring[0] != ring[-1]:
            changed = False
            for i, w in enumerate(ways):
                if w[0] == ring[-1]:
                    ring += w[1:]
                elif w[-1] == ring[-1]:
                    ring += w[::-1][1:]
                elif w[-1] == ring[0]:
                    ring = w[:-1] + ring
                elif w[0] == ring[0]:
                    ring = w[::-1][:-1] + ring
                else:
                    continue
                ways.pop(i)
                changed = True
                break
        rings.append([xy(*p) for p in ring])
    return rings


MUNI = {}
for rel in adm:
    t = rel.get("tags", {})
    nm = t.get("name:en") or t.get("name")
    MUNI.setdefault(nm, []).extend(rel_polys(rel))
print("municipalities", list(MUNI))


def in_muni(name, x, y):
    m = np.zeros(len(x), bool)
    for ring in MUNI.get(name, []):
        if len(ring) > 3:
            m |= Path(np.array(ring)).contains_points(np.c_[x, y])
    return m


def muni_key(nm):
    n = (nm or "").lower()
    if "kathmandu" in n or "काठमाडौँ" in n:
        return "Kathmandu"
    if "lalitpur" in n or "ललितपुर" in n:
        return "Lalitpur"
    if "kirtipur" in n or "कीर्तिपुर" in n:
        return "Kirtipur"
    if "madhyapur" in n or "मध्यपुर" in n:
        return "Madhyapur Thimi"
    return nm


groups = {}
for nm in MUNI:
    groups.setdefault(muni_key(nm), []).append(nm)

bmuni = np.full(len(bx), "", dtype=object)
for key, names in groups.items():
    m = np.zeros(len(bx), bool)
    for nm in names:
        m |= in_muni(nm, bx, by)
    bmuni[m] = key

BANDS = [0, 45, 50, 55, 60, 65, 70, 75, 200]


def exposure(mask):
    out = {"buildings": int(mask.sum())}
    out["lden_hist"] = [int(((b_lden >= lo) & (b_lden < hi) & mask).sum()) for lo, hi in zip(BANDS[:-1], BANDS[1:])]
    out["lnight_hist"] = [int(((b_lnight >= lo) & (b_lnight < hi) & mask).sum()) for lo, hi in zip(BANDS[:-1], BANDS[1:])]
    n = max(mask.sum(), 1)
    out["pct_lden_55"] = float(((b_lden >= 55) & mask).sum() / n * 100)
    out["pct_lden_65"] = float(((b_lden >= 65) & mask).sum() / n * 100)
    out["pct_lnight_50"] = float(((b_lnight >= 50) & mask).sum() / n * 100)
    out["pct_who_road"] = float(((Lden_road[bj, bi] >= 53) & mask).sum() / n * 100)
    out["pct_who_air"] = float(((Lden_air[bj, bi] >= 45) & mask).sum() / n * 100)
    out["median_lden"] = float(np.median(b_lden[mask])) if mask.any() else 0
    return out


stats = {"All study area": exposure(np.ones(len(bx), bool))}
for key in ("Kathmandu", "Lalitpur", "Kirtipur", "Madhyapur Thimi"):
    m = bmuni == key
    if m.any():
        stats[key] = exposure(m)

# dominant source share per building
e_r = en(Lden_road[bj, bi]); e_a = en(Lden_air[bj, bi])
dominant_air = int((e_a > e_r).sum())

# ---------------------------------------------------------------- receptors
def sample(lat, lon, grid):
    x, y = xy(lat, lon)
    i, j = int((x - X0) / RES), int((y - Y0) / RES)
    if 0 <= i < NX and 0 <= j < NY:
        return float(grid[j, i])
    return None


receptors = []
for kind, lat, lon, nm in pois:
    if kind not in ("hospital", "school"):
        continue
    ld = sample(lat, lon, Lday)
    if ld is None:
        continue
    x, y = xy(lat, lon)
    receptors.append({"k": kind, "n": nm, "x": round(x, 1), "y": round(y, 1),
                      "lday": round(ld, 1), "lnight": round(sample(lat, lon, Lnight), 1),
                      "air": round(sample(lat, lon, Lden_air), 1), "road": round(sample(lat, lon, Lden_road), 1)})
# dedupe by name
seen = {}
for r in receptors:
    if r["n"] not in seen or seen[r["n"]]["lday"] < r["lday"]:
        seen[r["n"]] = r
receptors = sorted(seen.values(), key=lambda r: -r["lday"])

places = []
for kind, lat, lon, nm in pois:
    if kind in ("place", "bus", "market"):
        x, y = xy(lat, lon)
        places.append({"k": kind, "n": nm, "x": round(x, 1), "y": round(y, 1),
                       "lden": round(sample(lat, lon, Lden) or 0, 1)})

# named corridors ranked
corr = []
for nm, d in named.items():
    if d["len"] < 600:
        continue
    lv = [sample(LAT0 + p[1] / KY, LON0 + p[0] / KX, Lday) for p in d["pts"]]
    lv = [v for v in lv if v]
    if not lv:
        continue
    p = d["pts"][len(d["pts"]) // 2]
    corr.append({"n": nm, "len": round(d["len"]), "lday": round(float(np.percentile(lv, 75)), 1),
                 "x": round(p[0], 1), "y": round(p[1], 1), "cls": d["cls"]})
corr.sort(key=lambda c: (-c["lday"], -c["len"]))

# reference measurements from published surveys (for a sanity check in the viewer)
REFS = [
    {"n": "New Road (commercial survey, 2025)", "lat": 27.7041, "lon": 85.3110, "measured": 79.6,
     "note": "Highest of the surveyed commercial sites, daytime LAeq", "src": "https://www.nepjol.info/index.php/arj/article/download/87534/66358/251419"},
    {"n": "Kupondole (NHRC, office hours)", "lat": 27.6864, "lon": 85.3168, "measured": 79.0,
     "note": "High-traffic site, office-hours LAeq", "src": "https://opac.nhrc.gov.np/vufind/Record/oai:103.69.126.140:123456789-151/Details"},
    {"n": "Kalanki Chowk (Ring Road)", "lat": 27.6934, "lon": 85.2810, "measured": 70.0,
     "note": "Reported above 70 dB(A) day and night (DoEnv survey, lower bound)", "src": "https://thehimalayantimes.com/kathmandu/noise-pollution-alarming-in-kathmandu/"},
    {"n": "Koteshwor (Ring Road junction)", "lat": 27.6788, "lon": 85.3494, "measured": 70.0,
     "note": "All 20 Ring Road junctions surveyed exceeded 70 dB(A) Leq (lower bound)", "src": "https://i-scholar.in/index.php/CURS/article/view/215209"},
]
for r in REFS:
    x, y = xy(r["lat"], r["lon"])
    # nearest-road peak within 40 m (meters are placed at the kerb)
    i, j = int((x - X0) / RES), int((y - Y0) / RES)
    sl = (slice(max(j - 1, 0), j + 2), slice(max(i - 1, 0), i + 2))
    h10 = 10  # surveys were taken in the late-morning peak
    win_all = db(en(L_road[sl] + ROAD_H[h10]) + en(L_act[sl] + ACT_H[h10]) + en(L_night[sl] + NIGHT_H[h10])
                 + en(L_air[sl] + 10 * math.log10(AIR_MOV[h10] / MOV_PER_HOUR)) + en(BG_H[h10]))
    r["modelled"] = round(float(win_all.max()), 1)
    r["x"], r["y"] = round(x, 1), round(y, 1)

# hourly building-facade statistics (for the 24 h strip in the viewer)
hourly = []
for h in range(24):
    lv = db(hour_level(h))[bj, bi]
    hourly.append([round(float(np.median(lv)), 1), round(float(np.percentile(lv, 90)), 1),
                   round(float((lv >= 65).mean() * 100), 1)])

# airport footprint: contour areas and buildings inside aircraft-only Lden bands
air_b = Lden_air[bj, bi]
airport = {"bands": [], "movements_day": float(sum(AIR_MOV))}
for th in (45, 50, 55, 60, 65, 70):
    airport["bands"].append({"lden": th, "km2": round(float((Lden_air >= th).sum() * RES * RES / 1e6), 1),
                             "buildings": int((air_b >= th).sum())})
airport["night_bands"] = [{"lnight": th, "buildings": int((Lnight_air[bj, bi] >= th).sum())} for th in (40, 45, 50, 55)]

# ---------------------------------------------------------------- write outputs
def q(a):  # dB -> uint8, 0.5 dB steps
    return np.clip(np.round(a * 2), 0, 255).astype(np.uint8)


rgba = np.stack([q(L_road), q(L_air02), q(L_act), q(L_night)], -1)
rgba.tofile(os.path.join(OUT, "grid.bin"))
q(L_air20).tofile(os.path.join(OUT, "air20.bin"))
np.round(H - HMIN).clip(0, 65535).astype(np.uint16).tofile(os.path.join(OUT, "dem.bin"))

# buildings: int16 x,y (0.5 m), uint8 w,d (0.5 m), uint8 levels, uint8 muni code
codes = {"": 0, "Kathmandu": 1, "Lalitpur": 2, "Kirtipur": 3, "Madhyapur Thimi": 4}
b = np.zeros(len(bx), dtype=[("x", "<i2"), ("y", "<i2"), ("w", "u1"), ("d", "u1"), ("l", "u1"), ("m", "u1")])
b["x"] = np.clip(np.round(bx * 2), -32767, 32767)
b["y"] = np.clip(np.round(by * 2), -32767, 32767)
b["w"] = np.clip(np.round(bw * 4), 1, 255)
b["d"] = np.clip(np.round(bd * 4), 1, 255)
b["l"] = np.round(blv)
b["m"] = [codes.get(m, 0) for m in bmuni]
b.tofile(os.path.join(OUT, "buildings.bin"))

# roads: per way [cls(u8), n(u16), then n*(i16 x, i16 y) at 1 m]
with open(os.path.join(OUT, "roads.bin"), "wb") as f:
    for c, pts, LE in road_out:
        f.write(struct.pack("<BBH", c, int(round(LE)), len(pts)))
        for x, y in pts:
            f.write(struct.pack("<hh", int(round(x)), int(round(y))))

# misc vectors: runway, rivers, parks, municipal boundaries
vec = {"rivers": [], "green": [], "muni": [], "aerodrome": []}
for e in feat:
    t = e.get("tags", {})
    gm = e.get("geometry")
    if not gm or e["type"] != "way":
        continue
    pts = [[round(v, 1) for v in xy(p["lat"], p["lon"])] for p in gm if p]
    if t.get("waterway") == "river":
        vec["rivers"].append(pts)
    elif t.get("leisure") in ("park", "golf_course") or t.get("landuse") in ("forest", "grass", "recreation_ground"):
        vec["green"].append(pts)
    elif t.get("aeroway") == "aerodrome":
        vec["aerodrome"].append(pts)
for key, names in groups.items():
    if key in ("Kathmandu", "Lalitpur"):
        for nm in names:
            for ring in MUNI[nm]:
                vec["muni"].append({"n": key, "p": [[round(a, 1), round(b_, 1)] for a, b_ in ring[::2]]})

meta = {
    "grid": {"nx": NX, "ny": NY, "res": RES, "x0": X0, "y0": Y0},
    "dem": {"nx": dnx, "ny": dny, "res": DEM_RES, "min": HMIN, "max": float(H.max())},
    "origin": {"lat": LAT0, "lon": LON0, "kx": KX, "ky": KY},
    "bbox": [S, W, N, E],
    "runway": {"a": A.round(1).tolist(), "b": B.round(1).tolist(), "len": RWLEN, "hdg": hdg, "rwy02_share": RWY02_SHARE},
    "flight": flight_meta,
    "profiles": {"night": NIGHT_H, "road": ROAD_H, "air_mov": AIR_MOV, "act": ACT_H, "bg": BG_H, "mov_ref": MOV_PER_HOUR},
    "stats": stats, "bands": BANDS, "hourly": hourly, "airport": airport, "dominant_air_buildings": dominant_air,
    "receptors": receptors[:400], "receptor_counts": {
        "school": sum(1 for r in receptors if r["k"] == "school"),
        "hospital": sum(1 for r in receptors if r["k"] == "hospital"),
        "school_over_50": sum(1 for r in receptors if r["k"] == "school" and r["lday"] > 50),
        "hospital_over_50": sum(1 for r in receptors if r["k"] == "hospital" and r["lday"] > 50),
        "school_over_65": sum(1 for r in receptors if r["k"] == "school" and r["lday"] > 65),
        "hospital_over_65": sum(1 for r in receptors if r["k"] == "hospital" and r["lday"] > 65),
    },
    "places": places, "corridors": corr[:40], "refs": REFS,
    "model": {"excess_db_per_m": EXCESS_DB_PER_M, "emission": EMIS, "kernel_m": KR},
    "counts": {"roads": len(road_out), "buildings": int(len(bx)), "osm_timestamp": "2026-10-20"},
    "vec": vec,
}
with open(os.path.join(OUT, "meta.json"), "w") as f:
    json.dump(meta, f, separators=(",", ":"), ensure_ascii=False)

for f in sorted(os.listdir(OUT)):
    print(f, os.path.getsize(os.path.join(OUT, f)))
for k, v in stats.items():
    print(k, v["buildings"], "Lden>=55 %.1f%%  >=65 %.1f%%  Lnight>=50 %.1f%%  median %.1f" % (v["pct_lden_55"], v["pct_lden_65"], v["pct_lnight_50"], v["median_lden"]))
print("refs", [(r["n"], r["measured"], r["modelled"]) for r in REFS])
print("top corridors", [(c["n"], c["lday"]) for c in corr[:10]])
print("receptors", meta["receptor_counts"])
