"""Constants for the Flights Above integration."""

from __future__ import annotations

DOMAIN = "flights_above"
DEFAULT_NAME = "Flights Above"

# Configuration keys
CONF_RADIUS = "radius"
CONF_COUNT = "count"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_REQUIRE_ROUTE = "require_route"

# Defaults / limits
DEFAULT_RADIUS = 30.0  # km
DEFAULT_COUNT = 3
DEFAULT_SCAN_INTERVAL = 60  # seconds
DEFAULT_REQUIRE_ROUTE = True
MIN_COUNT = 1
MAX_COUNT = 3
MAX_RADIUS_KM = 400.0
MIN_SCAN_INTERVAL = 15
MAX_SCAN_INTERVAL = 3600

# How long a flight stays in the "recently passed through" history (seconds).
# Maximum aircraft plotted on the radar view (bounds the attribute size).
MAX_RADAR_BLIPS = 60

HISTORY_TTL = 1800  # 30 minutes
# How long a resolved callsign -> route lookup is cached (seconds).
ROUTE_CACHE_TTL = 21600  # 6 hours
# How long a "not found" route lookup is cached before retrying (seconds).
ROUTE_MISS_TTL = 3600  # 1 hour

# Data sources (all free, no API key required).
# Position sources are tried in order until one responds successfully.
# Path shapes DIFFER between providers, so each entry is a full template:
# adsb.lol uses /point/{lat}/{lon}/{nm}, adsb.fi uses
# /lat/{lat}/lon/{lon}/dist/{nm}. Response keys differ too ("ac" vs
# "aircraft"), which the parser already handles.
# NOTE: adsb.fi's terms require attribution with a link - see ATTRIBUTION.
ADSB_POINT_URLS = [
    "https://api.adsb.lol/v2/point/{lat}/{lon}/{nm}",
    "https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/{nm}",
    # airplanes.live REMOVED 2026-08-26. It returns HTTP 403 with a request to
    # email contact@airplanes.live, so it supplied no data. More importantly
    # their Legal Terms forbid this use outright: section 3 bars automated
    # access, and section 4 bars distributing "any automated system, including
    # ... scraper ... that accesses the Services". Section 2 grants only a
    # NON-TRANSFERABLE personal licence, so permission obtained by one person
    # cannot cover users who install this integration.
    # Do not re-add without written permission that explicitly covers
    # redistribution. See 03_FLIGHTS_ABOVE.md.
]
# Route / airport lookup by callsign.
ADSBDB_CALLSIGN_URL = "https://api.adsbdb.com/v0/callsign/"

ATTRIBUTION = (
    "Live data from adsb.lol and adsb.fi (https://adsb.fi); "
    "routes from adsbdb.com"
)

USER_AGENT = "home-assistant-flights-above/1.0"
REQUEST_TIMEOUT = 25  # seconds

# Nautical miles per kilometre conversion helpers
KM_PER_NM = 1.852
MAX_RADIUS_NM = 250  # adsb.lol point endpoint hard cap
