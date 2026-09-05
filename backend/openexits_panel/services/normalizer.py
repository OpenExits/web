"""Wizard payload -> standard OpenExits object JSON. THE one place this
translation exists — the wizard preview, instant validation, moderator
edit-then-approve and the publisher all call normalize().

Wizard payload contract (FE <-> BE):
{
  "kind": "new_object" | "new_feature" | "correction",
  "targetObjectPath": "fr/pointe-du-heron" | null, # required unless new_object
  "object": { "name", "country", "objectType"?, "status", "access",
              "seasonalClosure"?, "region"?, "city"? },
  "features": [ { "role", "name"?, "lat", "lon", "elevationM"?,
                  "positionSource": "gps"|"map", "precisionM"?,
                  "suitability"?, "exitDirectionDeg"?,
                  "approachTimeMin"?, "surface"?, "measurements"? } ],
  "notes": { "language": "en"|"fr", "<guideSection>": "text", ... }?,
  "duplicateOverride": bool?
}

Provenance note (rule OE-R07): the entry written here is PROVISIONAL — enough
for the validator to pass during drafting. The publisher bot REGENERATES it
from the actual submission route/author/merge date at publish time; nothing
the user types survives into published provenance.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone

from ulid import ULID

from openexits_validator.normalize import read_json

GUIDE_SECTIONS = (
    "access", "approach", "ledgeAndGearUp", "gear", "landing",
    "returnTrip", "weather", "hazards", "observations", "history",
)

FEATURE_MEASUREMENTS = (
    "rockdrop", "heightAgl", "totalHeight", "distanceToTalus",
    "flyableAltitude", "minGlideRatio",
)


class NormalizeError(Exception):
    """Payload too malformed to normalize; message is an i18n key."""

    def __init__(self, key: str):
        super().__init__(key)
        self.key = key


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _feature(f: dict) -> dict:
    if not isinstance(f, dict):
        raise NormalizeError("wizard.feature_invalid")
    try:
        lat, lon = float(f["lat"]), float(f["lon"])
    except (KeyError, TypeError, ValueError):
        raise NormalizeError("wizard.position_missing")
    position: dict = {"lat": round(lat, 6), "lon": round(lon, 6)}
    if f.get("elevationM") is not None:
        position["elevationM"] = f["elevationM"]
    if f.get("precisionM") is not None:
        position["precisionM"] = f["precisionM"]
    out: dict = {"role": f.get("role", "exit"), "position": position}
    if f.get("name"):
        out["name"] = f["name"]
    for key in ("suitability", "exitDirectionDeg", "approachTimeMin", "surface"):
        if f.get(key) is not None:
            out[key] = f[key]
    m_in = f.get("measurements") or {}
    m_out = {k: m_in[k] for k in FEATURE_MEASUREMENTS if isinstance(m_in.get(k), dict)}
    for opt in ("verticality", "terrainProfiles"):
        if m_in.get(opt) is not None:
            m_out[opt] = m_in[opt]
    if m_out:
        out["measurements"] = m_out
    return out


def _guide_from_notes(notes: dict | None, existing: dict | None = None) -> dict | None:
    guide = copy.deepcopy(existing) if existing else {}
    if notes:
        lang = notes.get("language") if notes.get("language") in ("en", "fr") else "en"
        for section in GUIDE_SECTIONS:
            text = notes.get(section)
            if isinstance(text, str) and text.strip():
                guide.setdefault(section, {})[lang] = text.strip()
    return guide or None


def _provisional_provenance(contributor_handle: str, source_id: str | None) -> list[dict]:
    return [{
        "source": "panel",
        "sourceId": source_id,
        "contributor": contributor_handle,
        "contributedAt": _today(),
        "licence": "ODbL-1.0",
    }]


def normalize(payload: dict, *, contributor_handle: str, commons_repo,
              submission_public_id: str | None = None) -> dict:
    """Return a standard object document for this wizard payload."""
    kind = payload.get("kind")
    features_in = payload.get("features") or []
    if kind == "new_object":
        obj = payload.get("object") or {}
        if not obj.get("name") or not obj.get("country"):
            raise NormalizeError("wizard.object_identity_missing")
        if not features_in:
            raise NormalizeError("wizard.no_features")
        doc: dict = {
            "schemaVersion": "2.0",
            "id": str(ULID()),
            "name": obj["name"],
            "country": obj["country"],
            "status": obj.get("status", "unknown"),
            "access": obj.get("access", "unknown"),
            "sensitivity": "public",
            "provenance": _provisional_provenance(contributor_handle, submission_public_id),
            "updatedAt": _now(),
            "features": [_feature(f) for f in features_in],
        }
        for opt in ("objectType", "region", "city"):
            if obj.get(opt):
                doc[opt] = obj[opt]
        if obj.get("seasonalClosure"):
            doc["seasonalClosure"] = obj["seasonalClosure"]
        guide = _guide_from_notes(payload.get("notes"))
        if guide:
            doc["guide"] = guide
        return doc

    if kind in ("new_feature", "correction"):
        target = payload.get("targetObjectPath")
        if not target:
            raise NormalizeError("wizard.target_missing")
        base_path = commons_repo / "objects" / f"{target}.json"
        if not base_path.exists():
            raise NormalizeError("wizard.target_not_found")
        doc = read_json(base_path)
        doc["updatedAt"] = _now()
        if kind == "new_feature":
            if not features_in:
                raise NormalizeError("wizard.no_features")
            doc["features"] = doc.get("features", []) + [_feature(f) for f in features_in]
        else:  # correction: overlay object fields + full feature set + notes
            obj = payload.get("object") or {}
            for key in ("name", "country", "objectType", "region", "city", "status", "access"):
                if obj.get(key) is not None:
                    doc[key] = obj[key]
            if obj.get("seasonalClosure") is not None:
                doc["seasonalClosure"] = obj["seasonalClosure"]
            if features_in:
                doc["features"] = [_feature(f) for f in features_in]
            guide = _guide_from_notes(payload.get("notes"), doc.get("guide"))
            if guide:
                doc["guide"] = guide
        # id, provenance, sameAs, media, routes: untouched — provenance is
        # APPENDED by the publisher, never rewritten here (append-only rule)
        return doc

    raise NormalizeError("wizard.kind_invalid")
