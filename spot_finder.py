"""
spot_finder.py  -- offline spot discovery + plain-English helpers for SkyWatch.

Design goals:
  * No network calls in this module (fully unit-testable offline).
  * No paid services. Distance is pure math; weather is injected by the caller
    via an optional `cloud_lookup` callable so the single free API call lives in
    one cached place in the app, not scattered here.
  * Translate jargon (Bortle, azimuth) into plain English, keeping the technical
    term available in brackets/tooltips.
"""

import json
import math
import os

# ── Loading ───────────────────────────────────────────────────────────────────
def load_spots(path="spots.json"):
    """Load the curated spot dataset. Returns the list of spot dicts."""
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("spots", [])


# ── Distance & travel (all offline) ─────────────────────────────────────────────
EARTH_RADIUS_MI = 3958.8

def haversine_miles(lat1, lng1, lat2, lng2):
    """Great-circle ('as the crow flies') distance in miles."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2)
    return EARTH_RADIUS_MI * 2 * math.asin(math.sqrt(a))

def estimate_drive_minutes(straight_miles, circuity=1.3, avg_mph=45.0):
    """
    Rough OFFLINE drive-time estimate. Real roads are longer and slower than a
    straight line, so we inflate distance by a circuity factor and assume a
    modest average speed. Clearly an approximation -- label it as such in the UI.
    Returns (road_miles_estimate, minutes_estimate).
    """
    road_miles = straight_miles * circuity
    minutes = (road_miles / avg_mph) * 60.0
    return road_miles, minutes

def format_drive(straight_miles, minutes):
    if minutes < 60:
        t = f"~{int(round(minutes))} min"
    else:
        h = int(minutes // 60)
        m = int(round(minutes % 60))
        t = f"~{h}h {m:02d}m"
    return f"{straight_miles:.0f} mi away \u00b7 {t} drive (approx)"


# ── Plain-English translation of jargon ─────────────────────────────────────────
def bortle_words(bortle):
    """Plain-English darkness label. Returns (phrase, technical_with_value)."""
    if bortle is None:
        return ("darkness unknown", "Bortle n/a")
    table = {
        1: "pristine dark sky", 2: "excellent dark sky", 3: "very dark sky",
        4: "fairly dark sky", 5: "moderate light pollution",
        6: "bright suburban sky", 7: "bright suburban sky",
        8: "city sky", 9: "inner-city sky",
    }
    phrase = table.get(int(bortle), "unknown sky")
    return (phrase, f"Bortle {int(bortle)} of 9")

_COMPASS_16 = [
    ("N", "north"), ("NNE", "north-northeast"), ("NE", "northeast"),
    ("ENE", "east-northeast"), ("E", "east"), ("ESE", "east-southeast"),
    ("SE", "southeast"), ("SSE", "south-southeast"), ("S", "south"),
    ("SSW", "south-southwest"), ("SW", "southwest"), ("WSW", "west-southwest"),
    ("W", "west"), ("WNW", "west-northwest"), ("NW", "northwest"),
    ("NNW", "north-northwest"),
]

def compass_from_azimuth(azimuth_deg):
    """Convert a compass bearing (0=N, 90=E, 180=S, 270=W) to (abbrev, words)."""
    if azimuth_deg is None:
        return ("", "")
    idx = int((azimuth_deg % 360) / 22.5 + 0.5) % 16
    return _COMPASS_16[idx]

def altitude_words(altitude_deg):
    """Plain-English height above the horizon."""
    if altitude_deg is None:
        return "above the horizon"
    if altitude_deg < 15:
        return "low on the horizon"
    if altitude_deg < 40:
        return "fairly low"
    if altitude_deg < 65:
        return "high in the sky"
    return "nearly overhead"


# ── Condition scoring ───────────────────────────────────────────────────────────
# Higher score = better. Darkness dominates for the Milky Way / stars; cloud is a
# strong override (a clear bright-sky spot still beats a cloudy dark one for sunset,
# and a cloudy dark spot is useless for the Milky Way).
SIGNAL_EMOJI = {"great": "\U0001F7E2", "ok": "\U0001F7E1", "poor": "\U0001F534", "unknown": "\u26AA"}

def _cloud_signal(cloud_pct):
    if cloud_pct is None:
        return None
    if cloud_pct <= 20:
        return "great"
    if cloud_pct <= 50:
        return "ok"
    return "poor"

def score_spot(spot, distance_miles, cloud_pct=None, needs_dark=True):
    """
    Returns (score_float, signal_str). `needs_dark` is True for milkyway/stars
    (darkness matters), False for sunrise/sunset (darkness barely matters).
    """
    bortle = spot.get("bortle")
    # Darkness component (only meaningful when needs_dark)
    dark_component = 0.0
    if needs_dark and bortle is not None:
        dark_component = (9 - bortle) * 10  # Bortle 1 -> 80, Bortle 9 -> 0

    # Cloud component
    cloud_sig = _cloud_signal(cloud_pct)
    cloud_component = {"great": 60, "ok": 25, "poor": -40, None: 30}[cloud_sig]

    # Distance penalty (gentle): conditions should outrank proximity
    distance_penalty = distance_miles * 0.15

    score = dark_component + cloud_component - distance_penalty

    # Overall signal: worst of darkness-as-signal and cloud-as-signal
    parts = []
    if cloud_sig is not None:
        parts.append(cloud_sig)
    if needs_dark and bortle is not None:
        parts.append("great" if bortle <= 3 else "ok" if bortle <= 5 else "poor")
    if not parts:
        signal = "unknown"
    else:
        order = {"poor": 0, "ok": 1, "great": 2, "unknown": 3}
        signal = min(parts, key=lambda s: order[s])
    return score, signal


# ── Event-type mapping ──────────────────────────────────────────────────────────
def _relevant(spot, event_type):
    best = spot.get("bestFor", [])
    if event_type in ("milkyway", "stars"):
        return ("milkyway" in best) or ("stars" in best)
    return event_type in best

def needs_dark_for(event_type):
    return event_type in ("milkyway", "stars")


# ── Main entry point ────────────────────────────────────────────────────────────
def find_nearby_spots(origin_lat, origin_lng, spots, event_type="milkyway",
                      max_miles=200, candidate_pool=12, limit=3,
                      cloud_lookup=None):
    """
    Rank curated spots near an origin for a given event type.

    cloud_lookup: optional callable (lat, lng) -> cloud_pct (0-100) or None.
                  Called only for the nearest `candidate_pool` spots, so the
                  caller can wrap it in a cache and stay well within free limits.

    Returns a list (len <= limit) of dicts:
      {spot, distance_miles, road_miles, drive_minutes, cloud_pct, score, signal}
    """
    needs_dark = needs_dark_for(event_type)

    # 1) Offline distance filter -> nearest candidate pool (no network).
    scored = []
    for s in spots:
        if not _relevant(s, event_type):
            continue
        d = haversine_miles(origin_lat, origin_lng, s["lat"], s["lng"])
        if d <= max_miles:
            scored.append((d, s))
    scored.sort(key=lambda x: x[0])
    candidates = scored[:candidate_pool]

    # 2) Annotate the small candidate pool with conditions and final score.
    results = []
    for d, s in candidates:
        cloud = None
        if cloud_lookup is not None:
            try:
                cloud = cloud_lookup(s["lat"], s["lng"])
            except Exception:
                cloud = None
        score, signal = score_spot(s, d, cloud_pct=cloud, needs_dark=needs_dark)
        road_mi, mins = estimate_drive_minutes(d)
        results.append({
            "spot": s,
            "distance_miles": d,
            "road_miles": road_mi,
            "drive_minutes": mins,
            "cloud_pct": cloud,
            "score": score,
            "signal": signal,
        })

    # 3) Rank by conditions (score), not raw distance.
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]


def describe_spot(result, event_type="milkyway", mw_direction=None, mw_window=None):
    """
    Build a plain-English card for a ranked spot result.
    Returns (headline, detail) strings. Jargon goes in brackets after plain words.
    Recommendations are area-level — always verify access, permits, hours,
    and seasonal closures before visiting any location.
    """
    s = result["spot"]
    emoji = SIGNAL_EMOJI.get(result["signal"], "\u26AA")
    headline = f"{emoji} {s['name']} \u2014 {format_drive(result['distance_miles'], result['drive_minutes'])}"

    bits = []
    # Cloud
    if result["cloud_pct"] is not None:
        c = result["cloud_pct"]
        if c <= 20:
            bits.append("clear skies")
        elif c <= 50:
            bits.append(f"partly cloudy ({c:.0f}% cloud)")
        else:
            bits.append(f"mostly cloudy ({c:.0f}% cloud)")
    # Darkness (only when it matters)
    if needs_dark_for(event_type):
        phrase, tech = bortle_words(s.get("bortle"))
        bits.append(f"{phrase} ({tech})")
    # Milky Way direction/time
    if event_type in ("milkyway", "stars") and mw_window:
        if mw_direction:
            bits.append(f"Milky Way to the {mw_direction[1]} ({mw_direction[0]})")
        if mw_window.get("start_str") and mw_window.get("end_str"):
            bits.append(f"best {mw_window['start_str']}\u2013{mw_window['end_str']}")
    detail = ". ".join(b[0].upper() + b[1:] for b in bits if b)
    note = s.get("notes")
    if note:
        detail = f"{detail}. {note}" if detail else note
    return headline, detail


if __name__ == "__main__":
    # Offline self-test (no network) -- run: python spot_finder.py
    spots = load_spots()
    print(f"Loaded {len(spots)} spots.\n")

    # Origin: Bellevue, WA (the example from the design discussion).
    origin = (47.6101, -122.2015)

    for ev in ("milkyway", "sunrise", "sunset"):
        print(f"=== Nearest spots for '{ev}' from Bellevue, WA ===")
        ranked = find_nearby_spots(origin[0], origin[1], spots, event_type=ev,
                                   max_miles=250, limit=3, cloud_lookup=None)
        for r in ranked:
            head, detail = describe_spot(r, event_type=ev)
            print(" ", head)
            print("     ", detail)
        print()

    # Jargon translation spot-checks
    print("Compass checks:", compass_from_azimuth(135), compass_from_azimuth(180), compass_from_azimuth(225))
    print("Bortle checks:", bortle_words(1), bortle_words(4), bortle_words(7))