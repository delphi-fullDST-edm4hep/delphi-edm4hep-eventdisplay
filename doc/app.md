# The browser app

The display opens on a showcase event and needs nothing installed.

[Open it](../app.html){ .md-button .md-button--primary }

## Two modes

| | showcase | live |
|---|---|---|
| source | the published figure JSON | a `.root` file you drop on the page |
| Python | none — instant | uproot under Pyodide, in your browser |
| entry stepping | disabled | enabled |
| rebinding collections | disabled | enabled |

Dropping a file switches to live mode. The file never leaves your machine: it is read with
[uproot](https://github.com/scikit-hep/uproot5) compiled to WebAssembly.

!!! note "First load"
    Live mode downloads Python, numpy, uproot, awkward and plotly once — roughly 30 MB, cached
    afterwards. The showcase does not need any of it, so the page is useful immediately and still
    works if Pyodide cannot start.

## The collection panel

Beside the figure is every collection in the event: per-event object count, EDM4hep type, domain,
provenance (transcribed from a DST bank, derived by SKELANA, or produced by the converter) and
the relations in and out.

* **Select a collection** — everything in the figure that did not come from it dims to 12 %.
* **Click a track, hit or vertex** — its collection is selected and described.
* **The dropdowns at the top** rebind a role to another collection and re-render (live mode).

The wiring is `meta.collection` on every trace, set by `figure.build`.

## Views and saving

`panels` / `3D` switches between the four-panel figure and the detector scene; both are held in
memory, so switching costs no recompute. `PNG`, `SVG` and `JSON` save whichever view is showing,
named from the run and event (`delphi_run48758_evt2666_3d.svg`). The JSON captures your current
state — a rotated camera, a zoom — and can be reopened in the [editor](../editor.html).

## Captions

`--title` and `--note` describe **one event**. They are stored in figure metadata, never drawn
into the plot and never used as a heading, so a file you open yourself shows no caption rather
than inheriting someone else's physics. Everything true of any event — run, event, source,
charged/neutral, b-tag, B field — is rendered live from the same metadata.
