"""Helices, the curvature-sign check and where each track starts.

The display draws nothing it has not measured: a track is the helix of its own
perigee parameters, started at the vertex it belongs to, and the part between the
IP and that vertex is drawn dotted so the picture never claims a path the particle
did not travel.
"""

from __future__ import annotations

import numpy as np

from .read import Event


def helix(p, s, sign=1.0):
    """Point(s) at arc length s on the helix with perigee parameters p.

    p = [x0, y0, z0, phi0, omega, tanLambda]; omega is the signed curvature, so the
    sign argument lets the caller flip it (see curvature_sign)."""
    x0, y0, z0, f0, w, tl = p
    w = w * sign
    if abs(w) < 1e-12:  # straight line
        return x0 + s * np.cos(f0), y0 + s * np.sin(f0), z0 + s * tl
    th = s * w
    return x0 + (np.sin(f0 + th) - np.sin(f0)) / w, y0 - (np.cos(f0 + th) - np.cos(f0)) / w, z0 + s * tl


def curvature_sign(e: Event, verbose=False):
    """+1 or -1: which sign of omega actually bends tracks onto their own calorimeter clusters.

    Re-checked per event rather than hard-coded, because the convention has moved between
    converter versions. Returns (sign, message)."""
    if not e.clusters:
        return 1.0, "curvature check: no track-cluster links found, using omega as stored"
    dist = {1.0: [], -1.0: []}
    s = np.linspace(0, 4000, 4001)
    for i, cx, cy in e.clusters:
        rc = np.hypot(cx, cy)
        for sg in (1.0, -1.0):
            x, y, _ = helix(e.par[i], s, sg)
            j = int(np.argmin(np.abs(np.hypot(x, y) - rc)))
            dist[sg].append(np.hypot(x[j] - cx, y[j] - cy))
    m1, m2 = np.median(dist[1.0]), np.median(dist[-1.0])
    sign = 1.0 if m1 <= m2 else -1.0
    msg = f"curvature check on {len(dist[1.0])} track-cluster links: median miss {m1:.0f} mm (omega as stored) vs {m2:.0f} mm (flipped) -> sign {sign:+.0f}"
    return sign, msg


def track_to(p, rmax, sign=1.0, n=900, s0=0.0):
    """The helix from arc length s0 out to radius rmax, at most half a turn."""
    w = abs(p[4])
    smax = rmax * 1.7 if w < 1e-12 else min(rmax * 1.7, np.pi / w)
    s = np.linspace(s0, s0 + smax, n)
    x, y, z = helix(p, s, sign)
    r = np.hypot(x, y)
    k = int(np.argmax(r >= rmax)) if np.any(r >= rmax) else len(s) - 1
    return x[: k + 1], y[: k + 1], z[: k + 1], r[: k + 1]


def fit_vertex(e: Event, ids, sign=1.0):
    """Least-squares crossing point of the IP direction lines of the given tracks.

    Our own straight-line fit, not a DELPHI vertex: the figure labels it as such."""
    ids = [i for i in ids if i in e.par]
    if len(ids) < 2:
        return None
    lines = []
    for i in ids:
        x0, y0, z0, f0, _w, tl = e.par[i]
        lam = np.arctan(tl)
        lines.append((np.array([x0, y0, z0]), np.array([np.cos(f0) * np.cos(lam), np.sin(f0) * np.cos(lam), np.sin(lam)])))
    M, b = np.zeros((3, 3)), np.zeros(3)
    for p, u in lines:
        T = np.eye(3) - np.outer(u, u)
        M += T
        b += T @ p
    xv = np.linalg.solve(M, b)
    rms = 1000 * np.sqrt(np.mean([np.linalg.norm((xv - p) - ((xv - p) @ u) * u) ** 2 for p, u in lines]))
    return xv, ids, rms


def start_points(e: Event, vtx: dict, sign=1.0):
    """Arc length at which to start each track, and where its dotted back-extrapolation begins.

    A track on a vertex starts at that vertex; otherwise it starts at the primary vertex when it
    passes within 1 mm of it, and at its own perigee when it does not."""
    s_grid = np.linspace(-80.0, 250.0, 33001)
    s0, s_pv, miss = {}, {}, []
    for i in e.par:
        xs, ys, zs = helix(e.par[i], s_grid, sign)
        jpv = int(np.argmin(np.hypot(xs - e.pv[0], ys - e.pv[1])))
        d_pv = float(np.hypot(xs[jpv] - e.pv[0], ys[jpv] - e.pv[1]))
        if i in vtx:
            v = vtx[i]
            d = (xs - v[0]) ** 2 + (ys - v[1]) ** 2 + (zs - v[2]) ** 2
            jv = int(np.argmin(d))
            s0[i] = float(s_grid[jv])
            s_pv[i] = float(min(s_grid[jpv], s_grid[jv]))
            miss.append(1000 * np.sqrt(d[jv]))
        else:
            s0[i] = float(s_grid[jpv]) if d_pv < 1.0 else 0.0
    n_pv = sum(1 for i in e.par if i not in vtx and abs(s0[i]) > 0)
    msg = (
        f"track start points: {len(vtx)} at their secondary vertex (miss {min(miss, default=0):.0f}-{max(miss, default=0):.0f} um), "
        f"{n_pv} at the primary vertex, {len(e.par) - len(vtx) - n_pv} at their perigee (pass > 1 mm from the PV in r-phi)"
    )
    return s0, s_pv, msg


def vd_residuals(e: Event, sign=1.0):
    """Check the VD strip decoding against each track's own crossing of the layer.

    A median r-phi residual of a few microns is what says the strip decoding is right;
    plotting the raw (x, y) instead would show hundreds of mm here."""
    res_rphi, res_z = [], []
    s = np.linspace(-50.0, 400.0, 9001)
    for i, hits in e.track_hits.items():
        xs, ys, zs = helix(e.par[i], s, sign)
        rs = np.hypot(xs, ys)
        for j in hits:
            if e.vd_r[j] <= 0:
                continue
            k = int(np.argmin(np.abs(rs - e.vd_r[j])))
            if e.vd_type[j] == 0:
                res_rphi.append(1000.0 * e.vd_r[j] * ((e.vd_phi[j] - np.arctan2(ys[k], xs[k]) + np.pi) % (2 * np.pi) - np.pi))
            elif e.vd_type[j] == 1:
                res_z.append(float(e.vd_raw_z[j] - zs[k]))
    msg = (
        f"VD hit decoding check: r-phi hits vs own track |d(R*phi)| median "
        f"{np.median(np.abs(res_rphi)) if res_rphi else float('nan'):.0f} um (n={len(res_rphi)}); "
        f"z hits |dz| median {np.median(np.abs(res_z)) if res_z else float('nan'):.2f} mm (n={len(res_z)})"
    )
    return res_rphi, res_z, msg


def impact_parameter(e: Event, i, sign=1.0):
    """Closest approach of track i to the primary vertex in r-phi [mm]."""
    w = abs(e.par[i][4])
    smx = min(3000.0, np.pi / w) if w > 1e-12 else 3000.0
    xs, ys, _ = helix(e.par[i], np.linspace(-smx, smx, 20001), sign)
    return float(np.min(np.hypot(xs - e.pv[0], ys - e.pv[1])))
