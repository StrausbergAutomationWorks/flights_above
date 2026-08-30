"""Build the bundled government-rotorcraft table from the FAA registry.

Downloads the FAA Releasable Aircraft Database, extracts government aircraft
registered to government entities, and writes a compact JSON keyed by Mode S
hex - which is what ADS-B actually transmits.

This is the same logic the integration runs on its 30-day refresh; running it
here just produces the snapshot that ships in the repo so the feature works
offline from first install.

    python gen_registrations.py <output.json>
"""

from __future__ import annotations

import csv
import io
import json
import sys
import urllib.request
import zipfile

FAA_URL = "https://registry.faa.gov/database/ReleasableAircraft.zip"

# A plain urllib UA gets 403; the registry wants something browser-like.
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"),
    "Accept": "application/zip,*/*",
}

TYPE_ACFT_ROTORCRAFT = "6"
TYPE_REGISTRANT_GOVERNMENT = "5"

# LOCAL CHANGE: federal operators registered as an LLC rather than as
# government. EXACT names only - keyword matching was measured and rejected:
#   "MARSHAL" -> 248 hits, 4 real (people surnamed Marshall, Marshall
#                University, Marshall Soaring Club)
#   "ICE"     -> 14 hits, ZERO real (Ice Man Holdings, Two Bag Ice,
#                Commerical Ice & Refrigeration)
#   "CUSTOMS" -> crop-spraying and custom-fabrication outfits
#
# ⚠ DHS OPERATIONS LLC (20 aircraft) is deliberately NOT here. Nineteen are
# Cessna 172s - a training fleet, not a mission fleet - and "DHS" may simply
# be someone's initials. Not added on an acronym.
#
# ⚠ ICE (Immigration and Customs Enforcement) has NO aircraft under its own
# name. Its air operations run through DHS registrations and CONTRACTED
# carriers with ordinary commercial names, so no registry search reaches
# ICE Air flights. Military aircraft on serials rather than N-numbers are not
# in this civil registry at all (SAM, PAT, RCH callsigns).
FEDERAL_OPERATOR_ALLOWLIST = {
    "CBP AIR LOGISTICS LLC",      # Citation 525C/680, King Air B100
    "HOMELAND AVIATION LLC",      # Cessna R172K, Aviat A-1C
}

# The FAA classes drones as rotorcraft, so a bare TYPE-ACFT filter sweeps in
# every registered municipal Phantom and Mavic. Those never appear on ADS-B.
DRONE_MFR_PREFIXES = (
    "DJI", "AUTEL", "YUNEEC", "3D ROBOTICS", "PARROT", "SKYDIO", "FREEFLY",
    "AGEAGLE", "INSPIRED FLIGHT", "WINGTRA", "QUANTUM SYSTEMS", "ENYU LUO",
    "SENSEFLY", "EHANG", "XIAOMI", "POWERVISION",
)


def _rows(zf: zipfile.ZipFile, name: str):
    """Stream a member as dicts.

    utf-8-sig matters: these files carry a BOM, which would otherwise leave the
    first column named '\ufeffCODE' rather than 'CODE'.
    """
    with zf.open(name) as fh:
        for row in csv.DictReader(io.TextIOWrapper(fh, "utf-8-sig", errors="replace")):
            yield {(k or "").strip(): (v or "").strip() for k, v in row.items()}


def build(raw: bytes) -> dict:
    zf = zipfile.ZipFile(io.BytesIO(raw))

    # ACFTREF first, filtered to rotorcraft so the lookup dict stays small.
    types: dict[str, tuple[str, int]] = {}
    for r in _rows(zf, "ACFTREF.txt"):
        # LOCAL CHANGE: the rotorcraft filter is gone.
        # It excluded every government FIXED-WING aircraft, so a government
        # Gulfstream fell through to lookup_operator and displayed as
        # "Private". Measured: rotorcraft-only 1,594 entries; all government
        # aircraft 5,723 (0.32 MB) - 2,120 fixed-wing single, 792 fixed-wing
        # multi, 920 additional rotorcraft that the seat filter had removed.
        pass
        try:
            seats = int(r.get("NO-SEATS") or 0)
        except ValueError:
            seats = 0
        types[r.get("CODE", "")] = ((r.get("MFR") or "").upper(), seats)

    out: dict[str, list[str]] = {}
    for r in _rows(zf, "MASTER.txt"):
        if (r.get("TYPE REGISTRANT") != TYPE_REGISTRANT_GOVERNMENT
                and (r.get("NAME") or "").strip().upper()
                not in FEDERAL_OPERATOR_ALLOWLIST):
            continue
        t = types.get(r.get("MFR MDL CODE", ""))
        if not t:
            continue
        mfr, seats = t
        # LOCAL CHANGE: drones are kept. A government UAS that does
        # broadcast is worth naming, and the cost is 1,186 entries / 70 KB.
        pass
        hx = (r.get("MODE S CODE HEX") or "").strip().upper()
        if not hx:
            continue
        out[hx] = [
            "N" + (r.get("N-NUMBER") or "").strip(),
            (r.get("NAME") or "").strip(),
            (r.get("STATE") or "").strip(),
        ]
    return out


def main() -> None:
    dest = sys.argv[1] if len(sys.argv) > 1 else "gov_rotorcraft.json"
    print(f"downloading {FAA_URL} ...")
    req = urllib.request.Request(FAA_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=300) as resp:
        raw = resp.read()
    print(f"  {len(raw)/1e6:.1f} MB")

    print("parsing ...")
    table = build(raw)
    print(f"  {len(table):,} government aircraft (all types, drones included)")

    payload = {"schema": 1, "source": "FAA Releasable Aircraft Database",
               "count": len(table), "aircraft": table}
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"))
    import os
    print(f"wrote {dest}  ({os.path.getsize(dest)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
