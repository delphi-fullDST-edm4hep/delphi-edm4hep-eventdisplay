# Decoding rules and self-checks

Everything here was validated in the original matplotlib display; this page is the summary a
future maintainer needs before changing `read.py` or `geometry.py`.

## The self-checks are the test suite

There is no unit-test suite. Instead the display re-derives, per event, the things that have
moved between converter versions, and prints what it found. On run 48758 / event 2666:

```text
curvature check on 4 track-cluster links: median miss 15 mm (omega as stored) vs 613 mm (flipped) -> sign +1
VD hit decoding check: r-phi hits vs own track |d(R*phi)| median 3 um (n=47); z hits |dz| median 0.00 mm (n=32)
track start points: 9 at their secondary vertex (miss 10-49 um), 7 at the primary vertex, 3 at their perigee
hidden 3 tracks: 33 (0.49 GeV, 189.5 mm, 0 VD hits), 32 (0.19 GeV, ...), 26 (0.11 GeV, ...)
```

Treat a change in those numbers as a regression:

* a VD residual of **hundreds of mm** means the strip decoding regressed
* a **flipped** curvature sign means the omega convention moved in the converter

## Vertex-detector hits are strip coordinates

In `sDST_TDVD_VDHits`:

| type | `position.x` | `position.z` | measures |
|---|---|---|---|
| 0 — R-φ strip | layer radius R | R·φ | R and φ, **not** z |
| 1 — z strip | −R | measured z | R and z, **not** φ |

Plotting the raw `(x, y)` puts every hit near φ = 0. The decoding is checked on every run against
each track's own crossing of that layer; the median residual is a few microns.

## Tracks

Helices from the **AtIP** (perigee) track state, LCIO convention, `location == 1`:

```python
x0 = referencePoint.x - D0·sin(phi0)
y0 = referencePoint.y + D0·cos(phi0)
z0 = referencePoint.z + Z0
```

Where a track *starts* is a deliberate choice: at its secondary vertex if it belongs to one, else
at the primary vertex if it passes within 1 mm of it in r-φ, else at its own perigee. The piece
between the IP and that vertex is drawn **dotted** — the particle never travelled it.

## Curvature sign

Re-checked per event by extrapolating each track to its linked calorimeter cluster and comparing
both signs of omega, taking whichever lands closer. Not hard-coded, because the convention has
moved between converter versions.

## Vertices and particle ID

* AABTAG secondary vertices are accepted only when their **ITSEC** parameter is ≥ 0; rejected
  hypotheses are not drawn.
* RICH: `sDST_HAID_HadronID` parameters — index 13 liquid angle, 15 liquid photon count, 8 gas
  angle, 10 gas photon count.
* `sDST_RPROCO_CombinedTags` calls about **6 % of 3–8 GeV pions** that radiate in the gas kaons.
  Do not use it for single-event claims.
* TPC dE/dx is in `sDST_BBDXGET_Dedx`; it cannot separate p from π around 1.7 GeV.

## Reading

Branches are read one at a time with `library="np"` and cached
([`read._Entry`][delphi_eventdisplay.read.Event]), rather than materialising the whole entry as an
awkward array. uproot ≥ 5.7 imports awkward itself, so it remains a dependency, but our own code
is numpy-only.

!!! warning "Two spellings of a branch name"
    `tree.keys()` spells branches `parent/parent.field`; `arrays()` calls them `parent.field`.
    Comparing the two silently finds nothing and every collection reads as empty.
