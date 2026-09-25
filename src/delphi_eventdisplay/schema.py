"""What is actually in this file: collections, their types, links and provenance.

The display used to pin one collection of each kind by name. A file offers many
(three Track collections, seven Vertex, four Cluster, twenty-odd ParticleID), so
instead we read podio's own metadata -- the same source the converter's
collection map is built from -- and let the caller choose.

Domains are the one field podio does not carry; they come from the converter's
published collection map when it is supplied, and are "unknown" otherwise.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field

import numpy as np
import uproot

_TYPEINFO = "events___CollectionTypeInfo"

# Which collection each part of the display wants, in order of preference.
# The first pattern that matches a collection of the right type wins; the names
# the original display hard-coded are simply the first preference here.
ROLES = {
    "particles": ("ReconstructedParticle", ["*MAIN_Particles", "*Particles"]),
    "jets": ("ReconstructedParticle", ["*_Jets", "*Jets"]),
    "tracks": ("Track", ["*TRAC_Tracks", "*Tracks", "*"]),
    "primary_vertex": ("Vertex", ["*AABTAG_PrimaryVertex", "*PV_PrimaryVertex", "*PrimaryVertex", "*"]),
    "secondary_vertices": ("Vertex", ["*AABTAG_SecondaryVertices", "*SecondaryVertices", "*_Vertices"]),
    "em_clusters": ("Cluster", ["*EMNC_Showers", "*EM*", "*Showers", "*"]),
    "vd_hits": ("TrackerHit3D", ["*TDVD_VDHits", "*VDHits", "*"]),
    "hadron_id": ("ParticleID", ["*HAID_HadronID", "*HadronID", "*RichTags"]),
}


def short_type(t: str) -> str:
    """edm4hep::TrackCollection -> Track."""
    return t.replace("edm4hep::", "").removesuffix("Collection")


@dataclass
class Collection:
    name: str
    type: str
    kind: str  # short_type
    provenance: str = "unknown"
    domain: str = "unknown"
    count: int = 0  # objects in the event that was read
    links: list = field(default_factory=list)  # [(relation, target collection)]


@dataclass
class Schema:
    path: str
    collections: dict = field(default_factory=dict)  # name -> Collection
    parameters: list = field(default_factory=list)
    entries: int = 0

    def by_kind(self, kind: str):
        return [c for c in self.collections.values() if c.kind == kind]

    def populated(self):
        return {n: c for n, c in self.collections.items() if c.count}

    def resolve(self, overrides: dict | None = None) -> dict:
        """role -> collection name, from the preference lists (overrides win)."""
        overrides = overrides or {}
        out = {}
        for role, (kind, patterns) in ROLES.items():
            if overrides.get(role):
                out[role] = overrides[role]
                continue
            candidates = [c.name for c in self.by_kind(kind)]
            # a populated collection beats an empty one of the same rank
            for pat in patterns:
                hit = [n for n in candidates if fnmatch.fnmatch(n, pat)]
                hit.sort(key=lambda n: (self.collections[n].count == 0, n))
                if hit:
                    out[role] = hit[0]
                    break
        return out


def _typeinfo(f):
    md = f["podio_metadata"]

    def column(field_):
        return list(md[f"{_TYPEINFO}/{_TYPEINFO}.{field_}"].array(library="np")[0])

    return column("collectionID"), column("name"), column("dataType")


def _provenance(f) -> dict:
    try:
        md = f["metadata"]
        keys = list(md["GPStringKeys"].array(library="np")[0])
        vals = md["GPStringValues"].array(library="np")[0]
        table = dict(zip(keys, vals))
        return dict(zip(list(table["provenance_collection"]), list(table["provenance_source"])))
    except Exception:
        return {}


def read_schema(path: str, entry: int | None = None, domains: dict | None = None) -> Schema:
    """Every collection in the file, with per-event counts when an entry is given."""
    f = uproot.open(path)
    tree = f["events"]
    ids, names, types = _typeinfo(f)
    id_to_name = dict(zip(ids, names))
    prov = _provenance(f)
    domains = domains or {}

    s = Schema(path=path, entries=tree.num_entries)
    for n, t in zip(names, types):
        s.collections[n] = Collection(
            name=n, type=t, kind=short_type(t),
            provenance=prov.get(n, "unknown"), domain=domains.get(n, "unknown"),
        )

    keys = {k.rsplit("/", 1)[-1] for k in tree.keys()}  # drop uproot's "parent/" prefix
    if entry is not None:
        fields = keys
        _cache: dict = {}

        def ev_get(k):
            if k not in _cache:
                _cache[k] = np.asarray(tree[k].array(entry_start=entry, entry_stop=entry + 1, library="np")[0])
            return _cache[k]
        for n, c in s.collections.items():
            # a collection's size is the length of any of its own columns
            for suffix in (".x", "_x", ".energy", ".type", ".charge", ".PDG", ".value", ".index", ".position.x", ".momentum.x"):
                k = n + suffix
                if k in fields:
                    c.count = len(ev_get(k))
                    break
            else:
                own = [k for k in fields if k.startswith(n + ".")]
                if own:
                    c.count = len(ev_get(own[0]))
        # links: a relation branch is _<collection>_<relation>, carrying the target collection ID
        for n, c in s.collections.items():
            for k in keys:
                base = k.split(".")[0]
                if not base.startswith(f"_{n}_"):
                    continue
                relation = base[len(n) + 2:]
                cid = f"{base}.collectionID"
                if cid not in fields:
                    continue
                try:
                    targets = {int(x) for x in ev_get(cid)}
                except Exception:
                    continue
                for t_id in targets:
                    tgt = id_to_name.get(t_id)
                    if tgt and (relation, tgt) not in c.links:
                        c.links.append((relation, tgt))
    return s


def to_dict(s: Schema, roles: dict | None = None) -> dict:
    """The shape the web page reads: same vocabulary as the converter's collection map."""
    return {
        "path": s.path.split("/")[-1],
        "entries": s.entries,
        "roles": roles or {},
        "collections": {
            c.name: {
                "type": c.type, "kind": c.kind, "domain": c.domain,
                "provenance": c.provenance, "count": c.count,
                "links": [{"relation": r, "to": t} for r, t in c.links],
            }
            for c in s.collections.values()
        },
        "kinds": sorted({c.kind for c in s.collections.values()}),
        "domains": sorted({c.domain for c in s.collections.values()}),
    }


def load_domains(map_json: str | None) -> dict:
    """collection -> domain, from the converter's published collection map."""
    if not map_json:
        return {}
    import json
    from pathlib import Path

    p = Path(map_json)
    if not p.exists():
        return {}
    m = json.loads(p.read_text())
    # accepts either the converter's collection_map.json or our flat {"domains": {...}} table
    if "domains" in m and isinstance(m["domains"], dict):
        return dict(m["domains"])
    return {n: c.get("domain", "unknown") for n, c in m.get("collections", {}).items()}
