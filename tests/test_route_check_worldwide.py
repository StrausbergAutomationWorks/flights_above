"""Worldwide geometry checks for route_check.

Run directly:  python tests/test_route_check_worldwide.py

Waypoints are computed by spherical interpolation along the great circle
rather than guessed. That distinction matters - an early version of this test
guessed at "points on the route" that were 600-800 km off the actual great
circle, which looked like three failures in route_check when the fault was in
the test.
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "custom_components", "flights_above"))

from route_check import route_is_plausible, _cross_track_km  # noqa: E402

AIRPORTS = {
    "ANC": (61.174, -149.996), "NRT": (35.765, 140.386),
    "LAX": (33.942, -118.408), "SYD": (-33.946, 151.177),
    "LHR": (51.470, -0.454),   "HND": (35.553, 139.781),
    "AMS": (52.309, 4.764),    "BRU": (50.901, 4.484),
    "CDG": (49.010, 2.548),    "DUS": (51.289, 6.767),
    "FRA": (50.033, 8.570),    "JNB": (-26.139, 28.246),
    "CPT": (-33.965, 18.602),  "GRU": (-23.435, -46.473),
    "SIN": (1.359, 103.989),   "AKL": (-37.008, 174.792),
    "SCL": (-33.393, -70.786),
}


def gc_point(a, b, frac):
    """The point `frac` of the way from a to b along the great circle."""
    p1, l1 = math.radians(a[0]), math.radians(a[1])
    p2, l2 = math.radians(b[0]), math.radians(b[1])
    d = 2 * math.asin(math.sqrt(
        math.sin((p2 - p1) / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin((l2 - l1) / 2) ** 2))
    if d == 0:
        return a
    ka = math.sin((1 - frac) * d) / math.sin(d)
    kb = math.sin(frac * d) / math.sin(d)
    x = ka * math.cos(p1) * math.cos(l1) + kb * math.cos(p2) * math.cos(l2)
    y = ka * math.cos(p1) * math.sin(l1) + kb * math.cos(p2) * math.sin(l2)
    z = ka * math.sin(p1) + kb * math.sin(p2)
    return (math.degrees(math.atan2(z, math.hypot(x, y))),
            math.degrees(math.atan2(y, x)))


def _route(o, d):
    return {"origin_iata": o, "destination_iata": d,
            "origin_lat": AIRPORTS[o][0], "origin_lon": AIRPORTS[o][1],
            "destination_lat": AIRPORTS[d][0], "destination_lon": AIRPORTS[d][1]}


FAILURES = []


def expect_kept(label, o, d, frac):
    """A waypoint genuinely on the route must be kept."""
    lat, lon = gc_point(AIRPORTS[o], AIRPORTS[d], frac)
    ok = route_is_plausible(_route(o, d), lat, lon, 35000)
    xt = _cross_track_km(AIRPORTS[o][0], AIRPORTS[o][1],
                         AIRPORTS[d][0], AIRPORTS[d][1], lat, lon)
    if not ok:
        FAILURES.append(label)
    print(f"  {'PASS' if ok else 'FAIL'}  {label:44} "
          f"pos={lat:7.2f},{lon:8.2f} xt={xt:6.0f}")


def expect_rejected(label, o, d, lat, lon, alt=35000):
    """A position nowhere near the route must be rejected."""
    ok = route_is_plausible(_route(o, d), lat, lon, alt)
    xt = _cross_track_km(AIRPORTS[o][0], AIRPORTS[o][1],
                         AIRPORTS[d][0], AIRPORTS[d][1], lat, lon)
    if ok:
        FAILURES.append(label)
    print(f"  {'PASS' if not ok else 'FAIL'}  {label:44} xt={xt:6.0f}")


def main():
    print("ANTIMERIDIAN - longitude wraparound")
    for f in (0.3, 0.5, 0.7):
        expect_kept(f"ANC-NRT at {int(f * 100)}% along", "ANC", "NRT", f)
    expect_rejected("ANC-NRT, aircraft over Kansas", "ANC", "NRT", 38.0, -98.0)

    print("\nPOLAR")
    for f in (0.3, 0.5, 0.7):
        expect_kept(f"LHR-HND at {int(f * 100)}% along", "LHR", "HND", f)
    expect_rejected("LHR-HND, aircraft over Egypt", "LHR", "HND", 27.0, 31.0)

    print("\nSOUTHERN HEMISPHERE AND PACIFIC")
    for o, d in (("JNB", "CPT"), ("SYD", "LAX"), ("GRU", "JNB"),
                 ("AKL", "SCL"), ("SYD", "SIN")):
        expect_kept(f"{o}-{d} at 50%", o, d, 0.5)

    print("\nDENSE EUROPEAN AIRSPACE - short legs")
    expect_kept("AMS-BRU at 50% (158 km leg)", "AMS", "BRU", 0.5)
    expect_rejected("AMS-BRU, aircraft over Frankfurt", "AMS", "BRU",
                    50.03, 8.57, 8000)
    expect_rejected("LHR-CDG, aircraft over Dusseldorf", "LHR", "CDG",
                    51.29, 6.77, 30000)
    expect_rejected("CDG-DUS, aircraft over London", "CDG", "DUS",
                    51.47, -0.45, 30000)
    expect_rejected("AMS-BRU, aircraft over Paris CDG", "AMS", "BRU",
                    49.01, 2.55, 30000)
    expect_rejected("CDG-FRA, aircraft over Amsterdam", "CDG", "FRA",
                    52.31, 4.76, 30000)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S):")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
