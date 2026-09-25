# Collections and roles

A DELPHI edm4hep file offers many collections of each kind. Entry 3990 of
`Y13709.126.edm4hep.root` holds 67 collections, 27 of them populated:

| EDM4hep type | how many | examples (objects in that event) |
|---|---|---|
| `ParticleID` | 24 | `sDST_HAID_HadronID` (19), `sDST_BBDXGET_Dedx` (17), `sDST_AABTAG_TrackTag` (15) |
| `Vertex` | 7 | `sDST_AABTAG_PrimaryVertex` (1), `sDST_AABTAG_SecondaryVertices` (2), `sDST_V0_V0Candidates` (4), `sDST_PV_Vertices` (4) |
| `Cluster` | 4 | `sDST_EMNC_Showers` (18), `sDST_HCNC_Showers` (0) |
| `Track` | 3 | `sDST_TRAC_Tracks` (19), `sDST_ELTR_RefitTracks` (5) |
| `TrackerHit3D` | 2 | `sDST_TDVD_VDHits` (79), `sDST_TDVD_VDPoints` (65) |

Pinning one of each by name would show a single arbitrary slice, so the display does not.

## Roles

[`schema.read_schema`][delphi_eventdisplay.schema.read_schema] reads podio's `podio_metadata` —
the same source the converter's collection map is built from — and
[`Schema.resolve`][delphi_eventdisplay.schema.Schema.resolve] binds each **role** to a collection
using the preference lists in `schema.ROLES`:

| role | EDM4hep type | default preference |
|---|---|---|
| `particles` | `ReconstructedParticle` | `*MAIN_Particles` |
| `tracks` | `Track` | `*TRAC_Tracks` |
| `jets` | `ReconstructedParticle` | `*_Jets` |
| `primary_vertex` | `Vertex` | `*AABTAG_PrimaryVertex`, `*PV_PrimaryVertex` |
| `secondary_vertices` | `Vertex` | `*AABTAG_SecondaryVertices` |
| `em_clusters` | `Cluster` | `*EMNC_Showers` |
| `vd_hits` | `TrackerHit3D` | `*TDVD_VDHits` |
| `hadron_id` | `ParticleID` | `*HAID_HadronID` |

A populated collection beats an empty one of the same rank. The historical DELPHI names are
simply the first preference, so defaults reproduce the original display exactly.

Override from the command line:

```bash
delphi-display FILE --entry 3990 --out e.html \
  --collection vd_hits=sDST_TDVD_VDPoints \
  --collection secondary_vertices=sDST_V0_V0Candidates
```

or from Python:

```python
e = read_event(path, 3990, collections={"vd_hits": "sDST_TDVD_VDPoints"})
```

or with the dropdowns in the app.

## Provenance and domains

Provenance comes from the file itself: each collection is *transcribed* from a DST bank, *derived*
by SKELANA at conversion time, or *custom* to the converter.

Domains are the one field podio does not carry. They are taken from the converter's published
collection map and shipped as `docs/collection_domains.json`.

!!! warning "The published map can lag the file"
    The map describes 64 collections; this file has 67. `sDST_AABTAG_SecondaryVertices`,
    `sDST_AABTAG_Jets` and `sDST_AABTAG_JetTag` — which the display depends on — are not in it,
    so they show as domain `unknown`. Regenerate the map from the converter to fix that.
