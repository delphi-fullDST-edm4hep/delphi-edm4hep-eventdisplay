# Panels and the 3-D scene

## The four panels

The layout of the original matplotlib figure, for slides and papers.

**(a) r-φ, whole event** — track helices, EM showers as towers of length proportional to energy,
and the HPC radius taken from the shower positions themselves (a dashed circle at r ≈ 2.14 m).

**(b) r-z** — the same tracks, with r signed by which thrust hemisphere the track's momentum
points into, so the two jets separate.

**(c) vertex detector, r-φ** — the three VD layers, their radii clustered out of the hits
(62.5, 87.8, 106.5 mm in the reference event), the R-φ hits, the primary vertex and the accepted
AABTAG secondary vertices. The matplotlib version needed a fixed inset for the vertex region;
here you zoom with the mouse, which is the one place interactivity pays for itself immediately.

**(d) RICH** — Cherenkov angle against momentum for chosen tracks, liquid and gas radiators, with
the expected π/K/p curves (n_liq 1.2718, n_gas 1.0019; gas thresholds π 2.26, K 8.0, p 15.2 GeV).
A track above the pion threshold with **zero** gas photons is drawn as a veto marker (▼), because
that absence is a measurement, not missing data.

## The 3-D scene

The layout a general-purpose event display uses: the VD layers and HPC as translucent barrels, the
helices in space, showers as towers pointing outward, vertices as markers, and the beam line.

`scene.aspectmode="data"` keeps it physically proportional, which is why the 2.1 m barrel dwarfs
the vertex region — that ratio is real, and stretching it would be a lie about the detector.

!!! important "A VD hit is not a point in space"
    A type-0 (R-φ) strip measures R and φ but **not** z; a type-1 strip measures R and z but not
    φ. So in three dimensions a single hit constrains a *line*, not a dot.

    * A hit belonging to a track is drawn at the z its **own track** measures — a real quantity.
    * A hit belonging to no track is drawn as the line parallel to the beam that it actually
      constrains, not as an invented point.

## What the interactivity adds

* hover names each track: index, charge, momentum, VD hit count, which vertex it starts from
* the legend switches whole classes of object off
* zoom replaces the fixed inset in panel (c)
* selecting a collection dims everything that did not come from it

## Both views carry

The DELPHI + EDM4hep mark, embedded as a data URI so it survives PNG/SVG export and an offline
HTML file, anchored top-right — the subplot titles are left-aligned over their own panel, so a
top-left mark lands on "(a) r-φ view".

No title and no run/event line are drawn into either figure: every number lives in `layout.meta`
and the page renders it as live text.
