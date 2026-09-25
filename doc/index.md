# DELPHI event display

One DELPHI event drawn straight from an edm4hep file — no DELGRA, no X11, no ROOT, no key4hep.
A port of the matplotlib display written for the September 2026 talk, rebuilt on Plotly so the
figure zooms, hovers, and runs in a browser.

[Open the event display](../app.html){ .md-button .md-button--primary }

## In one minute

```bash
pip install -e .
delphi-display FILE.edm4hep.root --entry 3990 --out event.html --view both
```

That writes a self-contained `event.html`, a `event.json` figure, a `event.schema.json`
describing the collections, and — with `--view both` — the same again for the 3-D scene.

Or open [the app](../app.html) and drop a `.edm4hep.root` file on it: uproot runs in the browser under
Pyodide and reads the file locally. Nothing is uploaded.

## What makes it different from a plotting script

**Nothing is pinned by collection name.** A DELPHI edm4hep file holds far more than one
collection of each kind — the 1994 data file carries 3 `Track` collections, 7 `Vertex`, 4
`Cluster`, 2 `TrackerHit3D` and 24 `ParticleID`. The display discovers them from podio's own
metadata and binds each part of the picture to one by *role*, which you can change.
See [Collections and roles](collections.md).

**Only measured quantities are drawn.** Tracks are helices from their own perigee parameters,
started at the vertex they belong to, with the back-extrapolation to the IP dotted so the picture
never claims a path the particle did not travel. In 3-D this matters more, not less: a
vertex-detector hit is a *strip*, so it is a line in space, not a point.
See [Decoding rules and self-checks](physics.md).

**The numbers are checked on every run, not assumed.** The curvature sign and the VD strip
decoding are re-derived per event and printed. Those printed numbers are the test suite.

## Credits

Ported from `event_display.py` by J. Zhang
(`/eos/experiment/eealliance/Users/zhangj/event_display/`), the reference for the physics and for
every decoding rule. Files are produced by
[delphi-edm4hep](https://github.com/delphi-fullDST-edm4hep/delphi-edm4hep); the collection
vocabulary matches its
[collection map](https://delphi-fulldst-edm4hep.github.io/delphi-edm4hep/collection_map.html).
Styling via [plotlyhep](https://github.com/DickyChant/plotlyhep).
