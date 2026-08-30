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
# LOCAL ONLY - do NOT include in a PR to Tobhs.
MAX_COUNT = 64
# LOCAL CHANGE: ceiling raised from 8 for the Chicagoland map, which wants ORD
# and out to St. Charles at a 56 km radius. Upstream ships 3.
#
# ⚠ THIS IS A VALIDATION CEILING, NOT THE SLOT COUNT. config_flow uses it as
# vol.Range(max=MAX_COUNT); the live number is CONF_COUNT on the config entry,
# defaulting to DEFAULT_COUNT = 3. Raising this permits a larger count to be
# selected in the options flow - it does not create slots.
#
# ⚠ Slot count does NOT drive route lookups. coordinator.py resolves a route
# for every aircraft in RADIUS and only then slices to self.count, so widening
# the radius is what costs; more slots costs nothing.
#
# ⚠ DAMAGE ITEM 2. Each slot is an entity with unique_id
# f"{entry_id}_flight_{index}". Selecting 64 creates 56 new entities
# PERMANENTLY; reverting to 8 leaves 56 orphans in the registry - the same
# mess as backlog item 16. Choose the number once, deliberately.
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
    # airplanes.live REMOVED 2026-08-26 - OPERATIONAL, not licensing.
    # api.airplanes.live/v2/point/... returns HTTP 403 with a request to email
    # contact@airplanes.live, so it supplies no data while still costing a
    # request every update cycle.
    #
    # Their API guide (airplanes.live/api-guide/) documents this endpoint as
    # publicly available: no key, no feeder required, 1 request/second,
    # non-commercial. airplanes.live/api/ lists a free tier of 500 req/day.
    # Why we get a 403 is unknown; an access request has been sent.
    #
    # If access is restored, note 500/day cannot sustain a 30s poll
    # (~2,880/day) - it would suit a third fallback, not a primary source.
]
# Route / airport lookup by callsign.
ADSBDB_CALLSIGN_URL = "https://api.adsbdb.com/v0/callsign/"

# Shown as the airport NAME when a code is present but cannot be resolved to
# a named airport - an ambiguous or unlisted identifier. Deliberately NOT the
# same as an absent route: "Chicago O'Hare to Somewhere" still tells you where
# the flight departed, whereas a blank tells you nothing.
# WARNING: display only. Never written into stored or published data.
UNRESOLVED_AIRPORT_NAME = "Somewhere"

ATTRIBUTION = (
    "Live data from adsb.lol and adsb.fi (https://adsb.fi); "
    "routes from adsbdb.com"
)

USER_AGENT = "home-assistant-flights-above/1.0"
REQUEST_TIMEOUT = 25  # seconds

# Nautical miles per kilometre conversion helpers
KM_PER_NM = 1.852
MAX_RADIUS_NM = 250  # adsb.lol point endpoint hard cap
