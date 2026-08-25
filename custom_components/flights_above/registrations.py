"""Resolve US government aircraft from their Mode S address.

The ADS-B feeds give a callsign and a type designator. For airline traffic the
callsign resolves to an operator via airlines.py. For an aircraft squawking its
registration - N911VH, say - there is nothing to resolve against, and the
honest fallback is "Private / General Aviation".

That fallback is wrong for a large and locally visible class of aircraft:
police, sheriff, fire and air-ambulance helicopters, which orbit at low level
and are exactly what a person looking up wants identified. They transmit an
N-number as their callsign and appear in no commercial aircraft database -
adsbdb.com and hexdb.io both 404 on them.

The FAA Releasable Aircraft Database does list them, keyed by the Mode S hex
that ADS-B transmits. This module ships a snapshot of the crewed, government-
registered rotorcraft from it and refreshes itself periodically.

SCOPE - this is deliberately inert outside the US:
  * The table only loads when the configured location is in US territory.
  * Lookups only run for hex addresses in the US ICAO block A00000-AFFFFF.
A user in Europe downloads nothing, parses nothing, and sees no change.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

_LOGGER = logging.getLogger(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "gov_rotorcraft.json")

# US ICAO 24-bit allocation. Exact, not heuristic.
US_HEX_MIN = 0xA00000
US_HEX_MAX = 0xAFFFFF

# Coarse boxes covering the US and its territories. The point is to avoid a
# 73 MB download for someone nowhere near the US, not to police borders - the
# CONUS box does catch southern Canada, which is harmless because Canadian
# aircraft are C0xxxx and fail the hex gate anyway.
_US_BOXES = (
    (24.4, 49.4, -125.0, -66.9),    # CONUS
    (51.0, 71.5, -168.0, -129.0),   # Alaska
    (51.0, 56.0, 172.0, 180.0),     # Aleutians beyond the antimeridian
    (18.9, 22.3, -160.3, -154.8),   # Hawaii
    (17.6, 18.6, -67.3, -64.5),     # Puerto Rico / USVI
    (13.2, 13.7, 144.6, 145.0),     # Guam
    (14.1, 15.3, 145.1, 146.1),     # Northern Marianas
)


def location_is_us(latitude: float | None, longitude: float | None,
                   country: str | None = None) -> bool:
    """Whether this install should bother with the US registry at all.

    ``country`` is Home Assistant's own configured country when available,
    which is the user's declaration and beats any bounding box. The boxes are
    the fallback for installs where it was never set.
    """
    if country:
        return country.upper() == "US"
    if latitude is None or longitude is None:
        return False
    return any(a <= latitude <= b and c <= longitude <= d
               for a, b, c, d in _US_BOXES)


def is_us_hex(hex_code: str | None) -> bool:
    """Whether a Mode S address falls in the US ICAO allocation."""
    if not hex_code:
        return False
    try:
        return US_HEX_MIN <= int(str(hex_code), 16) <= US_HEX_MAX
    except (TypeError, ValueError):
        return False


_SMALL_WORDS = {"of", "and", "the", "for", "at", "in", "on"}
_KEEP_UPPER = {"US", "USA", "USDA", "NASA", "DHS", "FBI", "DEA", "CBP", "ICE",
               "EMS", "LAPD", "NYPD", "CHP", "DPS", "ATF", "TSA", "NOAA"}


def prettify_owner(owner: str) -> str:
    """The registry stores owners in caps; make them readable."""
    words = []
    for i, w in enumerate(owner.split()):
        core = w.strip(".,")
        if core in _KEEP_UPPER:
            words.append(core)
        elif core.lower() in _SMALL_WORDS and i > 0:
            words.append(core.lower())
        elif "'" in w:                       # SHERIFF'S -> Sheriff's
            head, tail = w.split("'", 1)
            words.append(head.capitalize() + "'" + tail.lower())
        else:
            words.append(w.capitalize())
    out = " ".join(words)
    for abbr, full in (("Dept", "Department"), ("Cnty", "County")):
        out = out.replace(f" {abbr} ", f" {full} ")
        if out.endswith(f" {abbr}"):
            out = out[: -len(abbr)] + full
    return out


_CATEGORIES = (
    # Acronyms are listed explicitly: LAPD and NYPD contain no literal
    # "POLICE", and CHP no "HIGHWAY PATROL".
    ("Law enforcement", ("SHERIFF", "POLICE", "MARSHAL", "CONSTABLE",
                         "PUBLIC SAFETY", "STATE PATROL", "HIGHWAY PATROL",
                         "DEPARTMENT OF CORRECTION", "LAPD", "NYPD", "CHP",
                         "DPS", "TROOPER")),
    ("Fire / EMS", ("FIRE", "RESCUE", "EMS", "MEDICAL", "AMBULANCE",
                    "MEDEVAC", "LIFE FLIGHT", "AIR CARE")),
    ("Federal law enforcement", ("HOMELAND", "CUSTOMS", "BORDER", "CBP",
                                 "DEA", "FBI", "ICE ", "ATF")),
    ("Military", ("NAVAL", "ARMY", "AIR FORCE", "MARINE CORPS",
                  "NATIONAL GUARD", "DEFENSE", "DOD")),
    ("Natural resources", ("FOREST", "APHIS", "WILDLIFE", "NATURAL RESOURCE",
                           "PARK", "FISH AND GAME", "CONSERVATION")),
    ("Research / academic", ("UNIVERSITY", "COLLEGE", "INSTITUTE", "NASA",
                             "RESEARCH", "NOAA")),
)


def categorise(owner: str) -> str:
    up = owner.upper()
    for label, keys in _CATEGORIES:
        if any(k in up for k in keys):
            return label
    return "Government"


class GovRegistry:
    """The lookup table. Loaded lazily, and only for US installs."""

    def __init__(self) -> None:
        self._table: dict[str, list[str]] = {}
        self._loaded = False

    def load(self, path: str | None = None) -> int:
        """Load the table from disk. Returns how many entries were read.

        Never raises: a missing or corrupt file leaves the registry empty and
        every lookup simply returns None, which is the same behaviour as not
        having the feature at all.
        """
        target = path or DATA_FILE
        try:
            with open(target, encoding="utf-8") as fh:
                payload = json.load(fh)
            table = payload.get("aircraft") if isinstance(payload, dict) else None
            if not isinstance(table, dict):
                raise ValueError("no 'aircraft' mapping in payload")
            self._table = table
            self._loaded = True
            _LOGGER.debug("Loaded %s government aircraft from %s",
                          len(table), target)
        except Exception:  # noqa: BLE001
            self._table = {}
            self._loaded = True
            _LOGGER.debug("Could not load %s; government lookups disabled",
                          target, exc_info=True)
        return len(self._table)

    def lookup(self, hex_code: str | None) -> dict[str, Any] | None:
        """Resolve a Mode S address, or None.

        Returns None for anything outside the US ICAO block without touching
        the table, so non-US traffic costs a single integer comparison.
        """
        if not is_us_hex(hex_code):
            return None
        if not self._loaded:
            self.load()
        row = self._table.get(str(hex_code).upper())
        if not row:
            return None
        registration, owner, state = (row + ["", "", ""])[:3]
        return {
            "registration": registration or None,
            "operator": prettify_owner(owner) if owner else None,
            "operator_category": categorise(owner) if owner else None,
            "operator_state": state or None,
        }

    @property
    def size(self) -> int:
        return len(self._table)


REGISTRY = GovRegistry()


def lookup_government(hex_code: str | None) -> dict[str, Any] | None:
    """Module-level convenience wrapper around the shared registry."""
    return REGISTRY.lookup(hex_code)
