"""Nearby-object index (FOUNDATION_PLAN §6.4).

Published objects come from the commons build artifact (streamed line-by-line —
the one-feature-per-line format makes that trivial), cached with an mtime
check and explicitly invalidated after a publish. In-flight submissions are
unioned in so two contributors racing on the same cliff see each other.
Plain bbox-prefilter + haversine over thousands of tuples: ~1 ms; a spatial
index would be ceremony.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from openexits_validator.normalize import haversine_m

from ..models import Submission

PROMPT_RADIUS_M = 200   # UX radius: "is your exit part of this object?"
GATE_RADIUS_M = 50      # the hard commons gate (OE-R11)


@dataclass(frozen=True)
class NearbyObject:
    object_id: str
    path: str | None       # None for in-flight submissions
    name: str
    lat: float
    lon: float
    feature_count: int
    pending: bool = False


_cache: dict = {"mtime": None, "path": None, "objects": []}


def invalidate() -> None:
    _cache["mtime"] = None


def _published_objects(commons_repo: Path) -> list[NearbyObject]:
    """One entry per object, positioned at its FIRST EXIT (not the centroid):
    duplicate detection keys on where you jump from — the same choice the
    commons gate makes (gate_lib.primary_position). Reads features.geojson,
    whose one-feature-per-line format allows streaming."""
    geojson = commons_repo / "build" / "features.geojson"
    if not geojson.exists():
        return []
    mtime = geojson.stat().st_mtime_ns
    if _cache["mtime"] == mtime and _cache["path"] == str(geojson):
        return _cache["objects"]
    by_object: dict[str, dict] = {}
    with open(geojson, encoding="utf-8") as f:
        for line in f:
            line = line.strip().rstrip(",")
            if not line.startswith('{"geometry"'):
                continue
            try:
                feat = json.loads(line)
            except json.JSONDecodeError:
                continue
            props = feat.get("properties", {})
            oid = props.get("objectId")
            if not oid:
                continue
            entry = by_object.setdefault(oid, {
                "path": props.get("objectPath"), "name": props.get("objectName", "?"),
                "count": 0, "pos": None,
            })
            entry["count"] += 1
            lon, lat = feat["geometry"]["coordinates"]
            if entry["pos"] is None or (props.get("role") == "exit" and not entry.get("pos_is_exit")):
                entry["pos"] = (lat, lon)
                entry["pos_is_exit"] = props.get("role") == "exit"
    objects = [
        NearbyObject(object_id=oid, path=e["path"], name=e["name"],
                     lat=e["pos"][0], lon=e["pos"][1], feature_count=e["count"])
        for oid, e in by_object.items() if e["pos"] is not None
    ]
    _cache.update(mtime=mtime, path=str(geojson), objects=objects)
    return objects


def _inflight_objects(db) -> list[NearbyObject]:
    rows = db.execute(
        select(Submission).where(Submission.status.in_(("pending", "approved", "publishing")),
                                 Submission.kind == "new_object")
    ).scalars().all()
    out = []
    for sub in rows:
        try:
            doc = json.loads(sub.normalized_json or "")
            exit_feat = next(f for f in doc["features"] if f.get("role") == "exit")
            pos = exit_feat["position"]
            out.append(NearbyObject(
                object_id=doc.get("id", sub.public_id), path=None,
                name=doc.get("name", "?"), lat=pos["lat"], lon=pos["lon"],
                feature_count=len(doc.get("features", [])), pending=True,
            ))
        except (ValueError, KeyError, StopIteration):
            continue
    return out


def objects_near(commons_repo: Path, db, lat: float, lon: float,
                 radius_m: float = PROMPT_RADIUS_M) -> list[dict]:
    """Published + in-flight objects within radius, sorted by distance."""
    candidates = _published_objects(commons_repo) + _inflight_objects(db)
    # bbox prefilter: 1 deg lat ~= 111 km
    dlat = radius_m / 111_000
    dlon = radius_m / (111_000 * max(0.2, math.cos(math.radians(lat))))
    hits = []
    for s in candidates:
        if abs(s.lat - lat) > dlat or abs(s.lon - lon) > dlon:
            continue
        d = haversine_m(lat, lon, s.lat, s.lon)
        if d <= radius_m:
            hits.append({
                "object_id": s.object_id, "path": s.path, "name": s.name,
                "distance_m": round(d), "feature_count": s.feature_count,
                "pending": s.pending, "lat": s.lat, "lon": s.lon,
            })
    hits.sort(key=lambda h: h["distance_m"])
    return hits


def object_exists(commons_repo: Path, object_id: str) -> bool:
    return any(s.object_id == object_id for s in _published_objects(commons_repo))
