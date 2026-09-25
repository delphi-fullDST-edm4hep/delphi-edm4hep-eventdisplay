"""edm4hep -> a plain Event object.

Everything the display draws is a measured quantity read here; the decoding rules
(VD strip coordinates, the perigee track state, AABTAG vertex acceptance) are the
ones validated in the original matplotlib display, see README.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import uproot

from .schema import read_schema


class _Entry:
    """One entry, read branch by branch with library="np".

    uproot only needs awkward for its default library; reading this way keeps numpy as
    the single dependency, which is what lets the whole thing run in the browser under
    Pyodide (awkward ships a compiled extension, numpy is built in)."""

    def __init__(self, tree, entry: int):
        self._tree, self._entry = tree, entry
        # tree.keys() spells branches "parent/parent.field"; arrays() calls them "parent.field"
        self._keys = {k.rsplit("/", 1)[-1] for k in tree.keys()}
        self._cache: dict = {}

    def has(self, key: str) -> bool:
        return key in self._keys

    def __call__(self, key: str):
        if key not in self._cache:
            arr = self._tree[key].array(entry_start=self._entry, entry_stop=self._entry + 1, library="np")[0]
            self._cache[key] = np.asarray(arr)
        return self._cache[key]


# Default collection names, kept as documentation of the usual DELPHI output.
# What a given file actually uses is resolved by schema.Schema.resolve().
P = "sDST_MAIN_Particles"
TS = "_sDST_TRAC_Tracks_trackStates"
TRK = "sDST_TRAC_Tracks"
SV = "sDST_AABTAG_SecondaryVertices"
PVA = "sDST_AABTAG_PrimaryVertex"
JJ = "sDST_AABTAG_Jets"
EM = "sDST_EMNC_Showers"
VD = "sDST_TDVD_VDHits"
HAID = "sDST_HAID_HadronID"

LOC_AT_IP = 1  # LCIO track-state location code for the perigee


@dataclass
class Event:
    """One event, decoded. Lengths in mm, momenta in GeV, angles in rad."""

    path: str
    entry: int
    # global parameters
    gi: dict = field(default_factory=dict)
    gf: dict = field(default_factory=dict)
    # particles
    charge: np.ndarray = None
    momentum: np.ndarray = None  # (n, 3)
    p_abs: np.ndarray = None
    # perigee helix parameters per particle index: [x0, y0, z0, phi0, omega, tanLambda]
    par: dict = field(default_factory=dict)
    # vertex detector
    vd_x: np.ndarray = None  # r-phi hits, NaN where the hit is a z strip
    vd_y: np.ndarray = None
    vd_z: np.ndarray = None  # z-strip hit positions only
    vd_raw_z: np.ndarray = None  # the raw z column, per hit index (R*phi for type 0, z for type 1)
    vd_r: np.ndarray = None  # |x| = layer radius, every hit
    vd_phi: np.ndarray = None
    vd_type: np.ndarray = None
    vd_layers: list = field(default_factory=list)
    # electromagnetic showers
    sh_x: np.ndarray = None
    sh_y: np.ndarray = None
    sh_z: np.ndarray = None
    sh_e: np.ndarray = None
    r_em: float = 2100.0
    r_stop: float = 2100.0
    # vertices
    pv: np.ndarray = None
    svs: list = field(default_factory=list)
    sv_tracks: dict = field(default_factory=dict)  # particle index -> secondary vertex position
    # jets and thrust
    jets: list = field(default_factory=list)
    thrust: np.ndarray = None
    # track -> VD hit and track -> cluster links
    track_hits: dict = field(default_factory=dict)  # particle index -> VD hit indices
    clusters: list = field(default_factory=list)  # (particle index, x, y) of linked calorimeter clusters
    # RICH / hadron identification, particle index -> HAID parameter vector
    haid: dict = field(default_factory=dict)
    # what was in the file, and which collection each part of the display used
    schema: object = None
    roles: dict = field(default_factory=dict)

    @property
    def run(self):
        return self.gi.get("sDST_EVT_runNumber")

    @property
    def event(self):
        return self.gi.get("sDST_EVT_eventNumber")

    @property
    def n_charged(self):
        return self.gi.get("sDST_EVT_nCharged")

    @property
    def n_neutral(self):
        return self.gi.get("sDST_EVT_nNeutral")

    @property
    def b_field(self):
        v = self.gf.get("sDST_EVT_BField")
        return float(v[0]) if v is not None and len(v) else None

    @property
    def btag_event(self):
        v = self.gf.get("sDST_AABTAG_CombinedTagEvent")
        return float(v[0]) if v is not None and len(v) else None


def read_event(path: str, entry: int, *, collections: dict | None = None, domains: dict | None = None) -> Event:
    """Read one entry of an edm4hep file into an Event.

    collections overrides which collection each part of the display draws, by role
    ("tracks", "secondary_vertices", ...); anything not given is resolved from the
    file's own podio metadata. See schema.ROLES."""
    f = uproot.open(path)
    t = f["events"]
    if not 0 <= entry < t.num_entries:
        raise IndexError(f"entry {entry} out of range: {path} holds {t.num_entries} events")
    ev = _Entry(t, entry)
    has, A = ev.has, ev

    schema = read_schema(path, entry=entry, domains=domains)
    roles = schema.resolve(collections)
    missing = [r for r in ("particles", "tracks") if r not in roles]
    if missing:
        raise SystemExit(f"{path}: no collection found for {', '.join(missing)} -- is this an edm4hep file from delphi-edm4hep?")
    # shadow the module defaults with what this file actually has
    P = roles["particles"]
    TRK = roles["tracks"]
    TS = f"_{TRK}_trackStates"
    SV = roles.get("secondary_vertices", "")
    PVA = roles.get("primary_vertex", "")
    JJ = roles.get("jets", "")
    EM = roles.get("em_clusters", "")
    VD = roles.get("vd_hits", "")
    HAID = roles.get("hadron_id", "")

    e = Event(path=path, entry=entry, schema=schema, roles=roles)

    # ---- global parameters (run/event numbers, B field, thrust axis, event b-tag)
    ik = [str(x) for x in A("GPIntKeys")]
    iv = A("GPIntValues")
    fk = [str(x) for x in A("GPFloatKeys")]
    fv = A("GPFloatValues")
    e.gi = {k: int(np.asarray(iv[i])[0]) for i, k in enumerate(ik)}
    e.gf = {k: np.asarray(fv[i], float) for i, k in enumerate(fk)}

    T = e.gf.get("sDST_AABTAG_ThrustAxis", np.array([1.0, 0.0, 0.0]))
    e.thrust = T / (np.linalg.norm(T) or 1.0)

    # ---- particles
    e.momentum = np.stack([A(f"{P}.momentum.{c}") for c in "xyz"], 1).astype(float)
    e.charge = A(f"{P}.charge")
    e.p_abs = np.linalg.norm(e.momentum, axis=1)
    npart = len(e.charge)

    # ---- perigee (AtIP) track state per charged particle
    sb, se = A(f"{TRK}.trackStates_begin"), A(f"{TRK}.trackStates_end")
    loc = A(f"{TS}.location")
    D0, Z0 = A(f"{TS}.D0").astype(float), A(f"{TS}.Z0").astype(float)
    F0, TL, OM = A(f"{TS}.phi").astype(float), A(f"{TS}.tanLambda").astype(float), A(f"{TS}.omega").astype(float)
    RX, RY, RZ = (A(f"{TS}.referencePoint.{c}").astype(float) for c in "xyz")
    ptb, pte, pti = A(f"{P}.tracks_begin"), A(f"{P}.tracks_end"), A(f"_{P}_tracks.index")
    for i in range(npart):
        if e.charge[i] == 0 or pte[i] <= ptb[i]:
            continue
        it = int(pti[ptb[i]])
        if it >= len(sb):
            continue
        for s in range(sb[it], se[it]):
            if loc[s] == LOC_AT_IP:
                # perigee -> a point on the helix: d0 is signed in the plane perpendicular to phi0
                e.par[i] = [RX[s] - D0[s] * np.sin(F0[s]), RY[s] + D0[s] * np.cos(F0[s]), RZ[s] + Z0[s], F0[s], OM[s], TL[s]]
                break

    # ---- electromagnetic showers
    if EM and has(f"{EM}.position.x"):
        e.sh_x, e.sh_y, e.sh_z = (A(f"{EM}.position.{c}").astype(float) for c in "xyz")
        e.sh_e = A(f"{EM}.energy").astype(float)
    else:
        e.sh_x = e.sh_y = e.sh_z = e.sh_e = np.array([])
    if len(e.sh_x):
        rr = np.hypot(e.sh_x, e.sh_y)
        e.r_em, e.r_stop = float(np.median(rr)), float(np.min(rr))

    # ---- vertex detector hits, in strip coordinates
    # type 0 (R-phi strip): x = layer radius R, z = R*phi, no z measurement
    # type 1 (z strip):     x = -R,             z = measured z, no phi measurement
    # Plotting the raw (x, y) instead would pile every hit up near phi = 0.
    if VD and has(f"{VD}.position.x"):
        hx, _hy, hz = (A(f"{VD}.position.{c}").astype(float) for c in "xyz")
        e.vd_type = A(f"{VD}.type")
    else:
        hx = hz = np.array([])
        e.vd_type = np.array([], int)
    e.vd_r = np.abs(hx)
    rphi = (e.vd_type == 0) & (e.vd_r > 0)
    e.vd_phi = np.where(rphi, hz / np.where(e.vd_r > 0, e.vd_r, 1.0), np.nan)
    e.vd_x = np.where(rphi, e.vd_r * np.cos(e.vd_phi), np.nan)
    e.vd_y = np.where(rphi, e.vd_r * np.sin(e.vd_phi), np.nan)
    e.vd_z = hz[(e.vd_type == 1) & (e.vd_r > 0)]
    e.vd_raw_z = hz
    # layer radii clustered out of the hits themselves
    rv = np.sort(e.vd_r[e.vd_r > 0])
    e.vd_layers = [float(np.median(g)) for g in np.split(rv, np.where(np.diff(rv) > 8)[0] + 1) if len(g) >= 3] if len(rv) else []

    # ---- vertices; an AABTAG secondary vertex counts only when ITSEC >= 0
    e.pv = (np.array([A(f"{PVA}.position.{c}")[0] for c in "xyz"], float)
            if PVA and has(f"{PVA}.position.x") and len(A(f"{PVA}.position.x")) else np.zeros(3))
    if not (SV and has(f"{SV}.position.x")):
        SV = None
    spar, spb = (A(f"_{SV}_parameters").astype(float), A(f"{SV}.parameters_begin")) if SV else (np.zeros(0), np.zeros(0, int))
    sxyz = np.stack([A(f"{SV}.position.{c}").astype(float) for c in "xyz"], 1) if len(spb) else np.zeros((0, 3))
    accepted = [k for k in range(len(spb)) if spar[spb[k]] >= 0]
    e.svs = [sxyz[k] for k in accepted]
    svb, sve, svi = (A(f"{SV}.particles_begin"), A(f"{SV}.particles_end"), A(f"_{SV}_particles.index")) if SV else (np.zeros(0, int),) * 3
    for k in accepted:
        for i in [int(x) for x in svi[svb[k]:sve[k]]]:
            if i in e.par:
                e.sv_tracks[i] = sxyz[k]

    # ---- track -> VD hit links
    thb, the, thi = A(f"{TRK}.trackerHits_begin"), A(f"{TRK}.trackerHits_end"), A(f"_{TRK}_trackerHits.index")
    for i in e.par:
        it = int(pti[ptb[i]])
        if it < len(thb):
            e.track_hits[i] = [int(j) for j in thi[thb[it]:the[it]] if 0 <= int(j) < len(e.vd_r)]

    # ---- track -> calorimeter cluster links, used for the curvature-sign check
    try:
        meta = f["podio_metadata"].arrays(["events___CollectionTypeInfo.collectionID", "events___CollectionTypeInfo.name"], entry_stop=1)
        cid = dict(
            zip(
                np.asarray(meta["events___CollectionTypeInfo.collectionID"][0]).tolist(),
                [str(x) for x in meta["events___CollectionTypeInfo.name"][0]],
            )
        )
        cb, ce = A(f"{P}.clusters_begin"), A(f"{P}.clusters_end")
        ci, cc = A(f"_{P}_clusters.index"), A(f"_{P}_clusters.collectionID")
        for i in e.par:
            for k in range(cb[i], ce[i]):
                nm = cid.get(int(cc[k]))
                if nm is None or not has(f"{nm}.position.x"):
                    continue
                cx, cy = float(A(f"{nm}.position.x")[ci[k]]), float(A(f"{nm}.position.y")[ci[k]])
                if np.hypot(cx, cy) >= 500:
                    e.clusters.append((i, cx, cy))
    except Exception:
        pass  # the sign check falls back to omega as stored

    # ---- jets
    if JJ and has(f"{JJ}.momentum.x"):
        for jx, jy, jz, je in zip(A(f"{JJ}.momentum.x"), A(f"{JJ}.momentum.y"), A(f"{JJ}.momentum.z"), A(f"{JJ}.energy")):
            e.jets.append((float(jx), float(jy), float(jz), float(je)))

    # ---- RICH / dE/dx hadron identification
    if HAID and has(f"{HAID}.parameters_begin"):
        hb, he = A(f"{HAID}.parameters_begin"), A(f"{HAID}.parameters_end")
        hp = A(f"_{HAID}_parameters").astype(float)
        hi = A(f"_{HAID}_particle.index")
        for r in range(len(hb)):
            e.haid[int(hi[r])] = hp[hb[r]:he[r]]

    return e


def n_entries(path: str) -> int:
    return uproot.open(path)["events"].num_entries
