"""Tribhuvan International (VNKT) flight paths from CAAN AIP Nepal, VNKT AD 2 (AMDT 03/2022).

IFR tracks follow the RNP AR approach, missed approach and departure coding tables
(AD 2-49 to 2-58), with RF legs flown as arcs about their published centres.
Domestic VFR tracks use the valley entry/exit passes of AD 2.23 and the VFR holding
points of AD 2-73/74. Helicopters follow the heli-lanes of AD 2-77/79.
"""
import glob
import math
import os
import re

FT = 0.3048
NM = 1852.0
HERE = os.path.dirname(os.path.abspath(__file__))
AIP_GLOB = os.path.join(HERE, "..", "raw", "aip", "*.txt")


def _dms(d, m, s):
    return float(d) + float(m) / 60 + float(s) / 3600


def load_waypoints():
    wp = {}
    pat = re.compile(r"^\s*([A-Z]{5}|KT\d{3}|KTC\d{2}|RW\d{2})\s+(ICAO|ADHP)\s+(\d+)°(\d+)'([\d.]+)\"N\s+(\d+)°(\d+)'([\d.]+)\"E")
    heli = re.compile(r"^\s*\d+\s+(.+?)\s+N\s?(\d+)\s?:(\d+)['’](\d+(?:\.\d+)?)[\"”]?\s+E\s?0?(\d+):(\d+)['’](\d+(?:\.\d+)?)")
    for path in glob.glob(AIP_GLOB):
        for line in open(path, encoding="utf-8", errors="ignore"):
            m = pat.match(line)
            if m:
                wp[m.group(1)] = (_dms(*m.group(3, 4, 5)), _dms(*m.group(6, 7, 8)))
                continue
            m = heli.match(line)
            if m:
                wp["H:" + re.sub(r"\s+", " ", m.group(1)).strip()] = (_dms(*m.group(2, 3, 4)), _dms(*m.group(5, 6, 7)))
    wp["KTM"] = (_dms(27, 40, 25), _dms(85, 20, 55))
    wp["LTH"] = (_dms(27, 36, 45), _dms(85, 19, 24))
    return wp


# Leg = (fix, "IF"|"TF"|"RF", turn, centre, altitude constraint)
ARRIVALS = {
    "Z02_RATAN": ("RNP Z RWY 02 (AR) via RATAN", "02", [
        ("RATAN", "IF", None, None, "+10500"), ("GURAS", "TF", None, None, None), ("KT532", "TF", None, None, None),
        ("KT530", "RF", "L", "KTC21", "@8700")]),
    "Z02_DANFE": ("RNP Z RWY 02 (AR) via DANFE", "02", [
        ("DANFE", "IF", None, None, "+10500"), ("KT540", "TF", None, None, None), ("KT538", "RF", "L", "KTC31", None),
        ("KT536", "TF", None, None, "+10500"), ("KT534", "TF", None, None, None), ("KT532", "RF", "L", "KTC21", None),
        ("KT530", "RF", "L", "KTC21", "@8700")]),
    "Y02_IGRIS": ("RNP Y RWY 02 (AR) via IGRIS", "02", [
        ("IGRIS", "IF", None, None, "+11800"), ("SARMA", "TF", None, None, "+7900"), ("KT554", "RF", "R", "KTC33", None),
        ("KT552", "TF", None, None, None), ("KT550", "RF", "L", "KTC32", "@7500")]),
    "Y02_DARKE": ("RNP Y RWY 02 (AR) via DARKE", "02", [
        ("DARKE", "IF", None, None, "+10500"), ("BELOM", "TF", None, None, None), ("KT566", "RF", "R", "KTC34", None),
        ("KT564", "TF", None, None, "+7900"), ("KT562", "RF", "L", "KTC35", None), ("KT560", "RF", "L", "KTC35", None),
        ("KT550", "TF", None, None, "@7500")]),
    "VOR02": ("VOR/DME RWY 02 via RATAN, KTM R202", "02", [
        ("RATAN", "IF", None, None, "+10500"), ("GURAS", "TF", None, None, "@9500")]),
    "R20_RATAN": ("RNP RWY 20 (AR) via RATAN", "20", [
        ("RATAN", "IF", None, None, "+10500"), ("KT450", "TF", None, None, None), ("KT448", "RF", "L", "KTC43", None),
        ("KT446", "TF", None, None, None), ("KT444", "RF", "R", "KTC42", None), ("KT442", "TF", None, None, "+8800"),
        ("BIRUP", "RF", "R", "KTC41", None), ("KT424", "TF", None, None, "+7900"), ("KT422", "RF", "L", "KTC38", None),
        ("KT421", "TF", None, None, None), ("KT419", "RF", "L", "KTC37", "@7400")]),
    "R20_DANFE": ("RNP RWY 20 (AR) via DANFE", "20", [
        ("DANFE", "IF", None, None, "+10500"), ("KT540", "TF", None, None, None), ("KT538", "RF", "L", "KTC31", None),
        ("KT536", "TF", None, None, "+10500"), ("KT452", "TF", None, None, None), ("KT444", "RF", "L", "KTC44", None),
        ("KT442", "TF", None, None, "+8800"), ("BIRUP", "RF", "R", "KTC41", None), ("KT424", "TF", None, None, "+7900"),
        ("KT422", "RF", "L", "KTC38", None), ("KT421", "TF", None, None, None), ("KT419", "RF", "L", "KTC37", "@7400")]),
    "R20_IGRIS": ("RNP RWY 20 (AR) via IGRIS", "20", [
        ("IGRIS", "IF", None, None, "+11800"), ("SARMA", "TF", None, None, None), ("KT430", "RF", "R", "KTC40", None),
        ("KT428", "TF", None, None, None), ("KT564", "RF", "L", "KTC39", None), ("KT426", "RF", "L", "KTC38", None),
        ("KT424", "RF", "L", "KTC38", "+7900"), ("KT422", "RF", "L", "KTC38", None), ("KT421", "TF", None, None, None),
        ("KT419", "RF", "L", "KTC37", "@7400")]),
    "R20_DARKE": ("RNP RWY 20 (AR) via DARKE", "20", [
        ("DARKE", "IF", None, None, "+10500"), ("BELOM", "TF", None, None, None), ("KT566", "RF", "R", "KTC34", None),
        ("KT564", "TF", None, None, None), ("KT426", "RF", "L", "KTC38", None), ("KT424", "RF", "L", "KTC38", "+7900"),
        ("KT422", "RF", "L", "KTC38", None), ("KT421", "TF", None, None, None), ("KT419", "RF", "L", "KTC37", "@7400")]),
}
FINALS = {
    "Z02": [("KT528", "TF", None, None, None), ("DOVAM", "RF", "R", "KTC22", None), ("KT524", "TF", None, None, None),
            ("KT522", "RF", "R", "KTC23", None), ("KT520", "RF", "L", "KTC24", None), ("RW02", "TF", None, None, "THR")],
    "Y02": [("KT546", "RF", "L", "KTC32", None), ("RW02", "TF", None, None, "THR")],
    "VOR02": [("RW02", "TF", None, None, "THR")],
    "R20": [("KT418", "RF", "L", "KTC37", None), ("KT416", "TF", None, None, None), ("KT414", "RF", "L", "KTC36", None),
            ("RW20", "TF", None, None, "THR")],
}
MISSED = {
    "02": ("RNP missed approach RWY 02, right turn to DARKE then DANFE hold", [
        ("RW02", "IF", None, None, None), ("KT590", "TF", None, None, None), ("KT592", "RF", "R", "KTC01", None),
        ("KT812", "RF", "R", "KTC47", None), ("KT814", "TF", None, None, "+7500"), ("KT914", "TF", None, None, "+8500"),
        ("DARKE", "TF", None, None, None), ("KT890", "RF", "L", "KTC02", "+10000"), ("KT892", "TF", None, None, None),
        ("KT894", "RF", "L", "KTC29", None), ("KT896", "TF", None, None, None), ("KT898", "RF", "L", "KTC30", None),
        ("DANFE", "TF", None, None, "@10500")]),
    "20": ("RNP missed approach RWY 20, right turn to DARKE then DANFE hold", [
        ("RW20", "IF", None, None, None), ("KT491", "TF", None, None, None), ("KT493", "RF", "R", "KTC78", None),
        ("KT494", "TF", None, None, None), ("KT910", "RF", "R", "KTC66", None), ("KT912", "RF", "R", "KTC74", "+7500"),
        ("KT916", "TF", None, None, "+8500"), ("KT918", "RF", "L", "KTC73", None), ("DARKE", "TF", None, None, None),
        ("KT890", "RF", "L", "KTC02", "+10000"), ("KT892", "TF", None, None, None), ("KT894", "RF", "L", "KTC29", None),
        ("KT896", "TF", None, None, None), ("KT898", "RF", "L", "KTC30", None), ("DANFE", "TF", None, None, "@10500")]),
}
DEPARTURES = {
    "DARKE1F": ("DARKE 1F (RWY 02), west to India and the Gulf", "02", [
        ("RW02", "IF", None, None, None), ("KT414", "TF", None, None, None), ("KT802", "RF", "R", "KTC36", None),
        ("KT804", "TF", None, None, None), ("KT806", "RF", "R", "KTC45", None), ("KT808", "RF", "R", "KTC45", None),
        ("KT810", "RF", "R", "KTC46", None), ("KT812", "RF", "R", "KTC46", None), ("KT814", "TF", None, None, "+7500"),
        ("KT914", "TF", None, None, None), ("DARKE", "TF", None, None, None), ("KT840", "RF", "L", "KTC75", None),
        ("KT845", "TF", None, None, None)]),
    "IGRIS1C": ("IGRIS 1C (RWY 02), east", "02", [
        ("RW02", "IF", None, None, None), ("KT414", "TF", None, None, None), ("KT802", "RF", "R", "KTC36", None),
        ("KT804", "TF", None, None, None), ("KT806", "RF", "R", "KTC45", None), ("KT808", "RF", "R", "KTC45", None),
        ("KT810", "RF", "R", "KTC46", None), ("KT830", "TF", None, None, "+7500"), ("KT832", "RF", "R", "KTC71", None),
        ("KT834", "TF", None, None, None), ("KT822", "RF", "L", "KTC72", None), ("IGRIS", "TF", None, None, None),
        ("KT940", "TF", None, None, None), ("KT942", "RF", "R", "KTC49", None), ("KT944", "TF", None, None, None)]),
    "IGRIS1D": ("IGRIS 1D (RWY 02), east", "02", [
        ("RW02", "IF", None, None, None), ("KT414", "TF", None, None, None), ("KT802", "RF", "R", "KTC36", None),
        ("KT804", "TF", None, None, None), ("KT806", "RF", "R", "KTC45", None), ("KT820", "TF", None, None, None),
        ("KT822", "RF", "L", "KTC48", None), ("IGRIS", "TF", None, None, None), ("KT940", "TF", None, None, None),
        ("KT942", "RF", "R", "KTC49", None), ("KT944", "TF", None, None, None)]),
    "DARKE1G": ("DARKE 1G (RWY 20), west", "20", [
        ("RW20", "IF", None, None, None), ("KT901", "TF", None, None, None), ("KT903", "RF", "R", "KTC50", None),
        ("KT905", "RF", "R", "KTC51", None), ("KT906", "TF", None, None, None), ("KT908", "RF", "R", "KTC66", "+7500"),
        ("KT911", "RF", "R", "KTC52", None), ("KT915", "TF", None, None, None), ("KT918", "RF", "L", "KTC73", None),
        ("DARKE", "TF", None, None, None), ("KT840", "RF", "L", "KTC75", None), ("KT845", "TF", None, None, None)]),
    "DARKE1H": ("DARKE 1H (RWY 20), west, early turn", "20", [
        ("RW20", "IF", None, None, None), ("KT901", "TF", None, None, None), ("KT903", "RF", "R", "KTC50", None),
        ("KT915", "TF", None, None, None), ("KT918", "RF", "L", "KTC73", None), ("DARKE", "TF", None, None, None),
        ("KT840", "RF", "L", "KTC75", None), ("KT845", "TF", None, None, None)]),
    "IGRIS1E": ("IGRIS 1E (RWY 20), east", "20", [
        ("RW20", "IF", None, None, None), ("KT901", "TF", None, None, None), ("KT903", "RF", "R", "KTC50", None),
        ("KT905", "RF", "R", "KTC51", None), ("KT906", "TF", None, None, None), ("KT908", "RF", "R", "KTC66", "+7500"),
        ("KT920", "TF", None, None, None), ("KT922", "RF", "L", "KTC67", None), ("IGRIS", "TF", None, None, None),
        ("KT940", "TF", None, None, None), ("KT942", "RF", "R", "KTC49", None), ("KT944", "TF", None, None, None)]),
}

# Valley passes from AD 2.23 that have no published coordinates are placed on the obvious gap.
APPROX_PASSES = {
    "BHARATPUR_PASS": ("KTM", 235, 9.0),
    "KAKANI_PASS": ("KTM", 318, 9.5),
}
VFR_HOLDS = {
    "KIRTI": ("KTM", 275, 4), "SOYAM": ("KTM", 304, 4), "THECHO": ("KTM", 201, 4), "NALIN": ("KTM", 103, 6.5),
    "BHAKTA": ("KTM", 90, 4), "CHANG": ("KTM", 60, 5), "SURYA": ("KTM", 108, 4),
    "NAUBI": ("KTM", 255, 11), "BANEP": ("KTM", 110, 10), "NAKOT": ("KTM", 95, 14),
}
VFR = {
    "VFR02_W": ("Domestic VFR from the west via Bharatpur pass, final over Thecho", "02", "arr",
                [("BHARATPUR_PASS", 8500), ("THECHO", 5700), ("RW02", "THR")]),
    "VFR02_E": ("Domestic VFR from the east via Banepa, base over Suryabinayak", "02", "arr",
                [("BANEP", 8000), ("SURYA", 6000), ("F02_2NM", 5000), ("RW02", "THR")]),
    "VFRD02_W": ("Domestic VFR departure RWY 02, left turn out via Kakani pass", "02", "dep",
                 [("RW02", 0), ("RW20", 0), ("N02_1NM", 5600), ("SOYAM", 7000), ("KAKANI_PASS", 8500)]),
    "VFRD02_E": ("Domestic VFR departure RWY 02, right turn out via Nagarkot pass", "02", "dep",
                 [("RW02", 0), ("RW20", 0), ("N02_1NM", 5600), ("CHANG", 7000), ("H:Nagarkot Pass", 8500), ("NAKOT", 9500)]),
    "VFR20_W": ("Domestic VFR from the west via Kakani pass, final over Gokarna", "20", "arr",
                [("KAKANI_PASS", 8500), ("SOYAM", 6500), ("F20_3NM", 5400), ("RW20", "THR")]),
    "VFR20_E": ("Domestic VFR from the east via Nagarkot pass", "20", "arr",
                [("NAKOT", 9000), ("H:Nagarkot Pass", 8000), ("CHANG", 6200), ("F20_2NM", 5100), ("RW20", "THR")]),
    "VFRD20_W": ("Domestic VFR departure RWY 20, out via Bharatpur pass", "20", "dep",
                 [("RW20", 0), ("RW02", 0), ("S20_1NM", 5400), ("KIRTI", 6500), ("BHARATPUR_PASS", 8500)]),
    "VFRD20_E": ("Domestic VFR departure RWY 20, out via Banepa", "20", "dep",
                 [("RW20", 0), ("RW02", 0), ("S20_1NM", 5400), ("NALIN", 6500), ("BANEP", 8000)]),
}
HELI_LANES = {
    "GOKARNA": ("Gokarna lane to Sundarijal pass (Langtang, Helambu)", 7500,
                ["Gothatar Junction", "Gokarna Bagmati Bridge", "Gokarna", "Sundarijal", "Sundarijal Pass"]),
    "TOKHA": ("Tokha lane to Tokha pass (Gosaikunda, Rasuwa)", 6500,
              ["Gothatar Junction", "Gokarna Bagmati Bridge", "South of Kapan Gumba", "Tokha", "Tokha Pass"]),
    "MAIJU": ("Maiju lane (north-west)", 5500, ["Gothatar Junction", "Narayan Gopal Chowk", "Gongabu", "Maiju Pass", "Chaturali"]),
    "SITAPAILA": ("Sitapaila lane (west, Dhading)", 5500,
                  ["Gothatar Junction", "Narayan Gopal Chowk", "Gongabu", "Machha Pokhari Chowk", "Swayambhu", "Sitapaila",
                   "Sitapaila Pass", "Jeewanpur"]),
    "THANKOT": ("Thankot Bravo lane (west, Pokhara)", 5500,
                ["Gothatar Junction", "Chabahil Bridge", "Bagmati/Dhobikhola JNC", "Balkhu Bridge", "North Kirtipur",
                 "Thankot (Nagdhunga) Pass", "Naubishe"]),
    "THANKOT_K": ("Thankot Kilo lane (west, Pokhara)", 5500,
                  ["Manahara/Hanumante JNC", "Bagmati/Dhobikhola JNC", "Balkhu Bridge", "North Kirtipur",
                   "Thankot (Nagdhunga) Pass", "Naubishe"]),
    "BAGMATI": ("Bagmati Kilo lane (south, Khokana pass)", 5500,
                ["Manahara/Hanumante JNC", "Bagmati/Dhobikhola JNC", "Balkhu Bridge", "Khokana Pass"]),
    "NALA": ("Bhakta lane out via Nala pass (Everest, Solu)", 6000, ["Duwakot", "Kaushal", "Bhakta North (Nala) Pass", "Tanchok"]),
    "SANGA": ("Bhakta lane in via Sanga pass", 6000, ["Bode", "Sallaghari", "Bhakta South (Sanga) Pass", "Banepa"]),
    "KARTIKE": ("Changu lane out via Kartike pass (Everest, Rolwaling)", 6500,
                ["Kageshori Manahara", "Indrayani", "Shankhu", "Kartike Pass", "Baluwapati"]),
    "NAGARKOT_H": ("Changu lane in via Nagarkot pass", 6500,
                   ["Mulpani", "Changunarayan", "Chhyabasti", "Nagarkot Pass", "Nayagaun"]),
}


class Geometry:
    def __init__(self, xy, elev_fn):
        self.xy = xy
        self.elev = elev_fn
        self.wp = load_waypoints()
        self.p = {k: xy(*v) for k, v in self.wp.items()}
        ktm = self.p["KTM"]
        for name, (_, radial, dist) in {**APPROX_PASSES, **VFR_HOLDS}.items():
            a = math.radians(radial)
            self.p[name] = (ktm[0] + math.sin(a) * dist * NM, ktm[1] + math.cos(a) * dist * NM)
        a, b = self.p["RW02"], self.p["RW20"]
        self.rwlen = math.dist(a, b)
        u = ((b[0] - a[0]) / self.rwlen, (b[1] - a[1]) / self.rwlen)
        self.u = u
        self.p["F02_2NM"] = (a[0] - u[0] * 2 * NM, a[1] - u[1] * 2 * NM)
        self.p["F20_2NM"] = (b[0] + u[0] * 2 * NM, b[1] + u[1] * 2 * NM)
        self.p["F20_3NM"] = (b[0] + u[0] * 3 * NM, b[1] + u[1] * 3 * NM)
        self.p["N02_1NM"] = (b[0] + u[0] * 1 * NM, b[1] + u[1] * 1 * NM)
        self.p["S20_1NM"] = (a[0] - u[0] * 1 * NM, a[1] - u[1] * 1 * NM)
        self.thr = {"02": 4370 * FT, "20": 4445 * FT}
        self.pad = self.p["H:East Helipad"]

    def fix(self, name):
        return self.p[name if name in self.p else "H:" + name]

    def legs(self, legs, step=120.0):
        pts, marks = [], {}
        for i, (fx, kind, turn, ctr, alt) in enumerate(legs):
            P = self.fix(fx)
            if not pts:
                pts.append(P)
            elif kind == "RF":
                C = self.fix(ctr)
                S = pts[-1]
                a0 = math.atan2(S[1] - C[1], S[0] - C[0])
                a1 = math.atan2(P[1] - C[1], P[0] - C[0])
                r = (math.dist(S, C) + math.dist(P, C)) / 2
                if turn == "R":
                    while a1 > a0:
                        a1 -= 2 * math.pi
                else:
                    while a1 < a0:
                        a1 += 2 * math.pi
                n = max(2, int(abs(a1 - a0) * r / step))
                for k in range(1, n + 1):
                    t = a0 + (a1 - a0) * k / n
                    pts.append((C[0] + r * math.cos(t), C[1] + r * math.sin(t)))
                pts[-1] = P
            else:
                S = pts[-1]
                n = max(1, int(math.dist(S, P) / step))
                for k in range(1, n + 1):
                    pts.append((S[0] + (P[0] - S[0]) * k / n, S[1] + (P[1] - S[1]) * k / n))
            if alt:
                marks[len(pts) - 1] = alt
        return pts, marks

    @staticmethod
    def cum(pts):
        d = [0.0]
        for a, b in zip(pts[:-1], pts[1:]):
            d.append(d[-1] + math.dist(a, b))
        return d

    def arrival(self, key):
        name, rwy, legs = ARRIVALS[key]
        fin = "VOR02" if key == "VOR02" else key[:3]
        pts, marks = self.legs(legs + FINALS[fin])
        d = self.cum(pts)
        thr = self.thr[rwy] + 15
        known = []
        for i, a in sorted(marks.items()):
            if a == "THR":
                known.append((d[i], thr))
            else:
                known.append((d[i], float(a[1:]) * FT))
        if known[0][0] > 0:
            known.insert(0, (0.0, min(known[0][1] + known[0][0] * math.tan(math.radians(3)), 15000 * FT)))
        alt = [_interp(known, s) for s in d]
        roll = self._rollout(rwy)
        return {"name": name, "rwy": rwy, "kind": "arr", "ifr": True,
                "pts": [(x, y, z) for (x, y), z in zip(pts, alt)], "roll": roll}

    def _rollout(self, rwy):
        a, b = (self.p["RW02"], self.p["RW20"]) if rwy == "02" else (self.p["RW20"], self.p["RW02"])
        return [a, b]

    def missed(self, rwy):
        name, legs = MISSED[rwy]
        pts, marks = self.legs(legs)
        d = self.cum(pts)
        top = 10500 * FT
        alt = [min(self.thr[rwy] + 60 + s * 0.06, top) for s in d]
        return {"name": name, "rwy": rwy, "kind": "miss", "ifr": True, "pts": [(x, y, z) for (x, y), z in zip(pts, alt)]}

    def departure(self, key, grad, rot, cap=15000 * FT):
        name, rwy, legs = DEPARTURES[key]
        pts, _ = self.legs(legs)
        d = self.cum(pts)
        base = self.thr[rwy]
        alt = [min(base + max(s - rot, 0) * grad, cap) for s in d]
        return {"name": name, "rwy": rwy, "kind": "dep", "ifr": True, "pts": [(x, y, z) for (x, y), z in zip(pts, alt)]}

    def vfr(self, key, grad=0.09, rot=900):
        name, rwy, kind, route = VFR[key]
        pts, alts = [], []
        for fx, alt in route:
            P = self.fix(fx)
            if pts:
                S = pts[-1]
                n = max(1, int(math.dist(S, P) / 120))
                for k in range(1, n + 1):
                    pts.append((S[0] + (P[0] - S[0]) * k / n, S[1] + (P[1] - S[1]) * k / n))
                    alts.append(None)
                alts[-1] = alt
            else:
                pts.append(P)
                alts.append(alt)
        d = self.cum(pts)
        thr = self.thr[rwy]
        if kind == "arr":
            known = [(d[i], thr + 15 if a == "THR" else a * FT) for i, a in enumerate(alts) if a is not None]
            alt = [_interp(known, s) for s in d]
        else:
            known = [(d[i], a * FT) for i, a in enumerate(alts) if a]
            alt = [max(min(thr + max(s - rot, 0) * grad, _interp(known, s) if known else 1e9), thr) for s in d]
        return {"name": name, "rwy": rwy, "kind": kind, "ifr": False, "pts": [(x, y, z) for (x, y), z in zip(pts, alt)],
                "roll": self._rollout(rwy) if kind == "arr" else None}

    def vfr_circuit(self, rwy):
        a, b = (self.p["RW02"], self.p["RW20"]) if rwy == "02" else (self.p["RW20"], self.p["RW02"])
        u = ((b[0] - a[0]) / self.rwlen, (b[1] - a[1]) / self.rwlen)
        side = (u[1], -u[0])
        off = 1.6 * NM
        corners = [a, b,
                   (b[0] + u[0] * 1.2 * NM, b[1] + u[1] * 1.2 * NM),
                   (b[0] + u[0] * 1.2 * NM + side[0] * off, b[1] + u[1] * 1.2 * NM + side[1] * off),
                   (a[0] - u[0] * 1.8 * NM + side[0] * off, a[1] - u[1] * 1.8 * NM + side[1] * off),
                   (a[0] - u[0] * 1.8 * NM, a[1] - u[1] * 1.8 * NM), a]
        circ = 5500 * FT if rwy == "02" else 5600 * FT
        thr = self.thr[rwy]
        alts = [thr + 40, thr + 160, circ, circ, circ, thr + 1.8 * NM * math.tan(math.radians(3)), thr + 15]
        pts, al = [corners[0]], [alts[0]]
        for i in range(1, len(corners)):
            S, P = corners[i - 1], corners[i]
            n = max(1, int(math.dist(S, P) / 120))
            for k in range(1, n + 1):
                t = k / n
                pts.append((S[0] + (P[0] - S[0]) * t, S[1] + (P[1] - S[1]) * t))
                al.append(alts[i - 1] + (alts[i] - alts[i - 1]) * t)
        return {"name": f"Visual go-around and circuit, RWY {rwy}", "rwy": rwy, "kind": "miss", "ifr": False,
                "pts": [(x, y, z) for (x, y), z in zip(pts, al)], "roll": self._rollout(rwy)}

    def heli(self, key):
        name, lane_alt, names = HELI_LANES[key]
        route = [self.pad] + [self.fix(n) for n in names]
        pts = [route[0]]
        for S, P in zip(route[:-1], route[1:]):
            n = max(1, int(math.dist(S, P) / 120))
            for k in range(1, n + 1):
                pts.append((S[0] + (P[0] - S[0]) * k / n, S[1] + (P[1] - S[1]) * k / n))
        d = self.cum(pts)
        pad = self.elev(*self.pad)
        cruise = 5000 * FT
        alt = []
        for s, (x, y) in zip(d, pts):
            if s < 900:
                z = pad + (max(cruise, 4800 * FT) - pad) * s / 900
            elif s < 5 * NM:
                z = cruise
            else:
                z = cruise + (lane_alt * FT - cruise) * min((s - 5 * NM) / (d[-1] - 5 * NM + 1), 1)
            alt.append(max(z, self.elev(x, y) + 120))
        return {"name": name, "rwy": None, "kind": "heli", "ifr": False, "pts": [(x, y, z) for (x, y), z in zip(pts, alt)]}


def _interp(known, s):
    if s <= known[0][0]:
        return known[0][1]
    for (d0, a0), (d1, a1) in zip(known[:-1], known[1:]):
        if s <= d1:
            return a0 + (a1 - a0) * (s - d0) / max(d1 - d0, 1e-6)
    return known[-1][1]


TYPES = {
    "A320": {"label": "Airbus A320 / Boeing 737-800", "cls": "narrow", "share": 0.21, "sel_app": 86.0, "sel_dep": 91.0,
             "grad": 0.075, "rot": 1700, "vapp": 70, "vr": 78, "vclimb": 128, "vinit": 118, "roll": 1500,
             "len": 37.6, "span": 35.8},
    "A330": {"label": "Airbus A330 / Boeing 777", "cls": "wide", "share": 0.02, "sel_app": 89.0, "sel_dep": 95.0,
             "grad": 0.060, "rot": 2300, "vapp": 72, "vr": 84, "vclimb": 135, "vinit": 120, "roll": 1900,
             "len": 63.7, "span": 60.3},
    "ATR72": {"label": "ATR 72 / ATR 42 / Dash 8", "cls": "turboprop", "share": 0.52, "sel_app": 80.0, "sel_dep": 83.5,
              "grad": 0.09, "rot": 1000, "vapp": 57, "vr": 58, "vclimb": 92, "vinit": 95, "roll": 900,
              "len": 27.2, "span": 27.1},
    "DHC6": {"label": "Twin Otter / Dornier 228", "cls": "stol", "share": 0.08, "sel_app": 76.0, "sel_dep": 79.0,
             "grad": 0.11, "rot": 450, "vapp": 41, "vr": 36, "vclimb": 62, "vinit": 70, "roll": 400,
             "len": 15.8, "span": 19.8},
    "AS350": {"label": "Airbus H125 (AS350) helicopter", "cls": "heli", "share": 0.17, "sel_app": 84.0, "sel_dep": 85.0,
              "grad": 0.12, "rot": 0, "vapp": 30, "vr": 0, "vclimb": 55, "vinit": 55, "roll": 0,
              "len": 12.9, "span": 10.7},
}

# Which procedure each class flies, by runway in use. Weights are modelling assumptions:
# RNP AR authorised carriers fly the RNP procedures, others the VOR/DME approach.
MIX = {
    "02": {
        "jet_arr": {"Z02_RATAN": 0.55, "VOR02": 0.22, "Y02_IGRIS": 0.10, "Y02_DARKE": 0.05, "Z02_DANFE": 0.08},
        "jet_dep": {"DARKE1F": 0.65, "IGRIS1C": 0.20, "IGRIS1D": 0.15},
        "tp_arr": {"VFR02_W": 0.42, "VFR02_E": 0.33, "VOR02": 0.25},
        "tp_dep": {"VFRD02_W": 0.42, "VFRD02_E": 0.33, "DARKE1F": 0.15, "IGRIS1D": 0.10},
        "stol_arr": {"VFR02_W": 0.3, "VFR02_E": 0.7},
        "stol_dep": {"VFRD02_W": 0.3, "VFRD02_E": 0.7},
    },
    "20": {
        "jet_arr": {"R20_RATAN": 0.5, "R20_IGRIS": 0.25, "R20_DARKE": 0.15, "R20_DANFE": 0.10},
        "jet_dep": {"DARKE1G": 0.5, "DARKE1H": 0.2, "IGRIS1E": 0.3},
        "tp_arr": {"VFR20_W": 0.55, "VFR20_E": 0.45},
        "tp_dep": {"VFRD20_W": 0.42, "VFRD20_E": 0.33, "DARKE1H": 0.15, "IGRIS1E": 0.10},
        "stol_arr": {"VFR20_W": 0.3, "VFR20_E": 0.7},
        "stol_dep": {"VFRD20_W": 0.3, "VFRD20_E": 0.7},
    },
    "heli": {"KARTIKE": 0.17, "NAGARKOT_H": 0.12, "NALA": 0.10, "SANGA": 0.06, "GOKARNA": 0.12, "TOKHA": 0.08,
             "MAIJU": 0.06, "SITAPAILA": 0.08, "THANKOT": 0.10, "THANKOT_K": 0.05, "BAGMATI": 0.06},
}
GO_AROUND = {"clear": 0.004, "haze": 0.02, "storm": 0.05}


def class_key(t):
    c = TYPES[t]["cls"]
    return "jet" if c in ("narrow", "wide") else "tp" if c == "turboprop" else c


def build_all(geom):
    procs = {}
    for k in ARRIVALS:
        procs[k] = geom.arrival(k)
    for r in ("02", "20"):
        procs["MA" + r] = geom.missed(r)
        procs["GA" + r] = geom.vfr_circuit(r)
    for k in VFR:
        procs[k] = geom.vfr(k)
    for k in DEPARTURES:
        procs[k] = geom.departure(k, 0.075, 1700)
    for k in HELI_LANES:
        procs["H_" + k] = geom.heli(k)
    return procs
