"""Seed a THROWAWAY dev commons for local development.

The real commons repo ships empty (clean-hands rule) — local dev still needs
objects on the map, so this creates var/dev-commons: a git-initialized commons
tree filled with SYNTHETIC objects at invented coordinates, plus built
artifacts. Point the backend at it:

    $env:OPENEXITS_COMMONS_REPO = "<backend>/openexits_panel/var/dev-commons"
    python -m flask --app openexits_panel.app:create_app run

Re-running wipes and re-seeds. Everything here is invented; never add a real
object to this script.
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path


def _rmtree_git_safe(path: Path) -> None:
    """rmtree that survives git's read-only object files on Windows."""
    def _clear_ro(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    shutil.rmtree(path, onexc=lambda f, p, e: _clear_ro(f, p, e))

from openexits_validator import validate_file
from openexits_validator.normalize import slugify, write_json

BACKEND = Path(__file__).resolve().parents[1]
DEV_COMMONS = BACKEND / "openexits_panel" / "var" / "dev-commons"
COMMONS_SCRIPTS = BACKEND.parents[1] / "commons" / "scripts"

sys.path.insert(0, str(COMMONS_SCRIPTS))
from build_artifacts import build  # noqa: E402


def obj_record(object_id, name, country, region, city, lat, lon, elev, *, rockdrop=None,
               agl=None, direction=180, status="open", access="tolerated",
               landing=None, suitability=None, guide_fr=None):
    features = [{
        "role": "exit",
        "name": "Main exit",
        "position": {"lat": lat, "lon": lon, "elevationM": elev, "precisionM": 10,
                     "pinConfirmed": True},
        "suitability": suitability or {"slick": False, "sliderOff": True, "sliderUp": True,
                                       "wingsuit": True, "tracksuit": True, "staticLine": False},
        "exitDirectionDeg": direction,
        "approachTimeMin": 90,
    }]
    m = {}
    if rockdrop:
        m["rockdrop"] = {"valueM": rockdrop, "method": "laser", "measuredAt": "2026-06-01"}
    if agl:
        m["heightAgl"] = {"valueM": agl, "reference": "landing", "method": "gps",
                          "measuredAt": "2026-06-01"}
    if m:
        features[0]["measurements"] = m
    if landing:
        features.append({
            "role": "landing", "name": "LZ", "surface": "grass",
            "position": {"lat": landing[0], "lon": landing[1], "elevationM": landing[2],
                         "precisionM": 15, "pinConfirmed": True},
        })
    doc = {
        "schemaVersion": "2.0",
        "id": object_id,
        "name": name,
        "country": country,
        "region": region,
        "city": city,
        "status": status,
        "access": access,
        "sensitivity": "public",
        "objectType": "earth",
        "provenance": [{"source": "panel", "sourceId": None, "contributor": "dev_seed",
                        "contributedAt": "2026-08-27", "licence": "ODbL-1.0"}],
        "updatedAt": "2026-08-27T09:00:00Z",
        "features": features,
    }
    if guide_fr:
        doc["guide"] = {"observations": {"fr": guide_fr}}
    return doc


# All SYNTHETIC — invented names, invented coordinates.
OBJECTS = [
    obj_record("01J9V0AAAAAAAAAAAAAAAAAAAA", "Pointe du Héron", "FR", "Massif des Ardines",
         "Saint-Elphe", 45.9012, 6.5123, 2140, rockdrop=220, agl=940, direction=210,
         landing=(45.8951, 6.5089, 1180),
         guide_fr="Objet fictif de démonstration — toutes les valeurs sont inventées."),
    obj_record("01J9V0AAAAAAAAAAAAAAAAAAAB", "Aiguille des Fauvettes", "FR", "Massif des Ardines",
         "Brévane", 45.8871, 6.4892, 1960, rockdrop=205, direction=230),
    obj_record("01J9V0AAAAAAAAAAAAAAAAAAAC", "Roc de l'Épervier", "FR", "Massif des Ardines",
         "Saint-Elphe", 45.8211, 6.4312, 2105, rockdrop=215, agl=910, direction=230,
         landing=(45.8149, 6.4281, 1195)),
    obj_record("01J9V0AAAAAAAAAAAAAAAAAAAD", "Torre di Malvento", "IT", "Alpi Immaginarie",
         "Prellavena", 46.1012, 10.9234, 1410, rockdrop=140, direction=10,
         status="seasonal", access="restricted-seasonal",
         suitability={"sliderOff": True, "staticLine": True}),
    obj_record("01J9V0AAAAAAAAAAAAAAAAAAAE", "Paroi des Chouettes", "CH", "Vallée Fictive",
         "Grunmatt", 46.5123, 7.8123, 1980, rockdrop=260, agl=1050, direction=300,
         landing=(46.5051, 7.8060, 930)),
]

# the seasonal one needs its closure block
OBJECTS[3]["seasonalClosure"] = {"from": "--02-15", "to": "--06-30",
                               "reason": {"en": "invented nesting window"}}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if DEV_COMMONS.exists():
        _rmtree_git_safe(DEV_COMMONS)
    for doc in OBJECTS:
        path = DEV_COMMONS / "objects" / doc["country"].lower() / f"{slugify(doc['name'])}.json"
        write_json(path, doc)
        report = validate_file(path)
        if not report.ok:
            print(f"seed object invalid: {path.name}: {[f.message for f in report.findings]}")
            return 1
    # the publisher runs ci/run_gates.py from inside the repo — mirror the real
    # commons toolchain into the dev repo
    real_commons = BACKEND.parents[1] / "commons"
    for sub in ("ci", "scripts"):
        shutil.copytree(real_commons / sub, DEV_COMMONS / sub,
                        ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(real_commons / ".gitignore", DEV_COMMONS / ".gitignore")
    build(DEV_COMMONS, DEV_COMMONS / "build")
    subprocess.run(["git", "-C", str(DEV_COMMONS), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(DEV_COMMONS), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(DEV_COMMONS), "-c", "user.name=dev-seed",
         "-c", "user.email=dev@openexits.invalid", "commit", "-q", "-m", "seed dev commons"],
        check=True,
    )
    print(f"seeded {len(OBJECTS)} synthetic object(s) -> {DEV_COMMONS}")
    print(f'set OPENEXITS_COMMONS_REPO to "{DEV_COMMONS}" and start the backend')
    return 0


if __name__ == "__main__":
    sys.exit(main())
