import streamlit as st
import datetime
from astro_engine import SkyEngine
from logger import log_pageload, log_error, log_event, get_summary
from spot_finder import (
    load_spots, find_nearby_spots, describe_spot,
    compass_from_azimuth, altitude_words,
)

st.set_page_config(page_title="SkyWatch", page_icon="🌌", layout="wide")

# ── Custom CSS — tighten spacing, clean up metric cards ──────────────────────
st.markdown("""
<style>
  /* Tighter top padding */
  .block-container { padding-top: 1rem; padding-bottom: 0.5rem; }
  /* Metric label smaller */
  [data-testid="metric-container"] label { font-size: 0.72rem; color: #888; text-transform: uppercase; letter-spacing: 0.04em; }
  /* Event time labels — white, slightly smaller than body */
  .event-label { color: #ffffff; font-size: 0.88rem; line-height: 1.4; }
  /* Tooltip icon sits inline, slightly smaller and grey */
  .event-label + div button { font-size: 0.78rem !important; color: #888 !important; }
  /* Section headers */
  .section-header { font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
                    letter-spacing: 0.08em; color: #888; margin-bottom: 0.3rem; margin-top: 0.8rem; }
  /* Summary card */
  .summary-card { background: #1a1f2e; border-left: 3px solid #4a9eff;
                  padding: 0.6rem 1rem; border-radius: 4px; margin-bottom: 0.8rem; font-size: 0.95rem; }
  /* Spot card */
  .spot-card { background: #161b27; border: 1px solid #2a3040;
               padding: 0.5rem 0.75rem; border-radius: 4px; margin-bottom: 0.4rem; font-size: 0.85rem; }
  /* Reduce h3 margin */
  h3 { margin-top: 0.4rem !important; margin-bottom: 0.2rem !important; }
  /* Divider color */
  hr { border-color: #2a3040 !important; margin: 0.5rem 0 !important; }
</style>
""", unsafe_allow_html=True)

# ── City / region groups ──────────────────────────────────────────────────────
CITY_GROUPS = {
    "── Northeast ──": None,
    "Providence, RI":         (41.8240, -71.4128),
    "Burlington, VT":         (44.4759, -73.2121),
    "Portland, ME":           (43.6591, -70.2568),
    "Concord, NH":            (43.2081, -71.5376),
    "Hartford, CT":           (41.7658, -72.6851),
    "New Haven, CT":          (41.3083, -72.9279),
    "New York, NY":           (40.7128, -74.0060),
    "Buffalo, NY":            (42.8864, -78.8784),
    "Albany, NY":             (42.6526, -73.7562),
    "Boston, MA":             (42.3601, -71.0589),
    "Philadelphia, PA":       (39.9526, -75.1652),
    "Pittsburgh, PA":         (40.4406, -79.9959),
    "Washington, DC":         (38.9072, -77.0369),
    "Baltimore, MD":          (39.2904, -76.6122),
    "── Mid-Atlantic / Southeast ──": None,
    "Richmond, VA":           (37.5407, -77.4360),
    "Raleigh, NC":            (35.7796, -78.6382),
    "Charlotte, NC":          (35.2271, -80.8431),
    "Charleston, SC":         (32.7765, -79.9311),
    "Atlanta, GA":            (33.7490, -84.3880),
    "Savannah, GA":           (32.0835, -81.0998),
    "Jacksonville, FL":       (30.3322, -81.6557),
    "Orlando, FL":            (28.5383, -81.3792),
    "Miami, FL":              (25.7617, -80.1918),
    "Tampa, FL":              (27.9506, -82.4572),
    "── South / Gulf ──": None,
    "Nashville, TN":          (36.1627, -86.7816),
    "Memphis, TN":            (35.1495, -90.0490),
    "Louisville, KY":         (38.2527, -85.7585),
    "Birmingham, AL":         (33.5186, -86.8104),
    "New Orleans, LA":        (29.9511, -90.0715),
    "Jackson, MS":            (32.2988, -90.1848),
    "Little Rock, AR":        (34.7465, -92.2896),
    "Houston, TX":            (29.7604, -95.3698),
    "Dallas, TX":             (32.7767, -96.7970),
    "San Antonio, TX":        (29.4241, -98.4936),
    "Austin, TX":             (30.2672, -97.7431),
    "El Paso, TX":            (31.7619, -106.4850),
    "Oklahoma City, OK":      (35.4676, -97.5164),
    "Tulsa, OK":              (36.1540, -95.9928),
    "── Midwest ──": None,
    "Chicago, IL":            (41.8781, -87.6298),
    "Indianapolis, IN":       (39.7684, -86.1581),
    "Columbus, OH":           (39.9612, -82.9988),
    "Cleveland, OH":          (41.4993, -81.6944),
    "Cincinnati, OH":         (39.1031, -84.5120),
    "Detroit, MI":            (42.3314, -83.0458),
    "Milwaukee, WI":          (43.0389, -87.9065),
    "Madison, WI":            (43.0731, -89.4012),
    "Minneapolis, MN":        (44.9778, -93.2650),
    "Duluth, MN":             (46.7867, -92.1005),
    "St. Louis, MO":          (38.6270, -90.1994),
    "Kansas City, MO":        (39.0997, -94.5786),
    "Omaha, NE":              (41.2565, -95.9345),
    "Sioux Falls, SD":        (43.5446, -96.7311),
    "Fargo, ND":              (46.8772, -96.7898),
    "── Mountain / Plains ──": None,
    "Denver, CO":             (39.7392, -104.9903),
    "Colorado Springs, CO":   (38.8339, -104.8214),
    "Cheyenne, WY":           (41.1400, -104.8197),
    "Billings, MT":           (45.7833, -108.5007),
    "Missoula, MT":           (46.8721, -113.9940),
    "Boise, ID":              (43.6150, -116.2023),
    "Salt Lake City, UT":     (40.7608, -111.8910),
    "Provo, UT":              (40.2338, -111.6585),
    "Albuquerque, NM":        (35.0844, -106.6504),
    "Santa Fe, NM":           (35.6870, -105.9378),
    "Tucson, AZ":             (32.2226, -110.9747),
    "Phoenix, AZ":            (33.4484, -112.0740),
    "Flagstaff, AZ":          (35.1983, -111.6513),
    "Las Vegas, NV":          (36.1699, -115.1398),
    "Reno, NV":               (39.5296, -119.8138),
    "── Pacific ──": None,
    "Seattle, WA":            (47.6062, -122.3321),
    "Tacoma, WA":             (47.2529, -122.4443),
    "Spokane, WA":            (47.6588, -117.4260),
    "Portland, OR":           (45.5051, -122.6750),
    "Eugene, OR":             (44.0521, -123.0868),
    "Bend, OR":               (44.0582, -121.3153),
    "Sacramento, CA":         (38.5816, -121.4944),
    "San Francisco, CA":      (37.7749, -122.4194),
    "San Jose, CA":           (37.3382, -121.8863),
    "Los Angeles, CA":        (34.0522, -118.2437),
    "San Diego, CA":          (32.7157, -117.1611),
    "Fresno, CA":             (36.7378, -119.7871),
    "── Alaska ──": None,
    "Anchorage, AK":          (61.2181, -149.9003),
    "Fairbanks, AK":          (64.2008, -149.4937),
    "Juneau, AK":             (58.3005, -134.4197),
    "── Hawaii ──": None,
    "Honolulu, HI":           (21.3069, -157.8583),
    "Maui (Kahului), HI":     (20.8893, -156.4729),
    "Big Island (Hilo), HI":  (19.7297, -155.0900),
    "── National Parks ──": None,
    "Acadia NP, ME":          (44.3386, -68.2733),
    "White Mountains, NH":    (44.2705, -71.3033),
    "Great Smoky Mtn NP, TN": (35.6532, -83.5070),
    "Shenandoah NP, VA":      (38.5200, -78.4400),
    "Everglades NP, FL":      (25.2860, -80.8987),
    "Big Bend NP, TX":        (29.1275, -103.2425),
    "Rocky Mountain NP, CO":  (40.3428, -105.6836),
    "Grand Canyon NP, AZ":    (36.1069, -112.1129),
    "Zion NP, UT":            (37.2982, -113.0263),
    "Arches NP, UT":          (38.7331, -109.5925),
    "Bryce Canyon NP, UT":    (37.5930, -112.1871),
    "Canyonlands NP, UT":     (38.4597, -109.8200),
    "Grand Teton NP, WY":     (43.7900, -110.6818),
    "Yellowstone NP, WY":     (44.4280, -110.5885),
    "Glacier NP, MT":         (48.6960, -113.7180),
    "Olympic NP, WA":         (47.8021, -123.6044),
    "Mount Rainier NP, WA":   (46.8523, -121.7603),
    "North Cascades NP, WA":  (48.7718, -121.2985),
    "Crater Lake NP, OR":     (42.9446, -122.1090),
    "Yosemite NP, CA":        (37.7490, -119.5885),
    "Death Valley NP, CA":    (36.5323, -116.9325),
    "Joshua Tree NP, CA":     (33.8734, -115.9010),
    "Sequoia NP, CA":         (36.4864, -118.5658),
    "Hawaii Volcanoes NP, HI":(19.4194, -155.2885),
    "Haleakala NP, HI":       (20.7204, -156.1552),
    "Denali NP, AK":          (63.3333, -150.5000),
    "Wrangell-St. Elias NP, AK": (61.7105, -142.9858),
}

US_CITIES   = {k: v for k, v in CITY_GROUPS.items() if v is not None}
SEPARATORS  = {k for k, v in CITY_GROUPS.items() if v is None}

REGION_MAX_MILES = {"HI": 60, "AK": 200}

SCORE_DOT  = {"great": "●", "ok": "●", "poor": "●", "unknown": "○"}
SCORE_COLOR = {"great": "#2ecc71", "ok": "#f39c12", "poor": "#e74c3c", "unknown": "#888"}

def guess_state(lat, lng):
    if 18.0 <= lat <= 23.0 and -161.0 <= lng <= -154.0: return "HI"
    if lat >= 54.0: return "AK"
    return "US"

def fmt(dt):
    return dt.strftime("%-I:%M %p") if dt else "—"

def score_dot(score):
    color = SCORE_COLOR.get(score, "#888")
    return f'<span style="color:{color};font-size:1.1em">●</span>'

# ── Cached helpers ────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def get_spots():
    return load_spots()

@st.cache_data(ttl=3600, show_spinner=False)
def get_weather(lat, lng):
    """Single API call for all weather data needed by the app — 7 days hourly.
    Cached 1 hour. Everything else (night cloud, week chart) derives from this.
    No key required; free for non-commercial use via Open-Meteo."""
    import urllib.request, json
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}"
           f"&hourly=cloud_cover&timezone=auto&forecast_days=7")
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        hourly = data.get("hourly", {})
        times  = hourly.get("time", [])
        clouds = hourly.get("cloud_cover", []) or hourly.get("cloudcover", [])
        return times, clouds
    except Exception as e:
        if "weather_error_shown" not in st.session_state:
            st.session_state["weather_error_shown"] = True
            st.warning(f"Weather data unavailable ({e}). Spots ranked by darkness only.")
        return [], []

def get_night_cloud_from(times, clouds, date_iso):
    """Derive night average cloud cover from already-fetched weather data.
    No API call — just slices the cached array."""
    import datetime as _dt
    next_iso = (_dt.date.fromisoformat(date_iso) + _dt.timedelta(days=1)).isoformat()
    vals = [c for t, c in zip(times, clouds) if c is not None and
            ((t[:10] == date_iso and int(t[11:13]) >= 20) or
             (t[:10] == next_iso  and int(t[11:13]) <= 2))]
    return (sum(vals) / len(vals)) if vals else None

def get_night_cloud(lat, lng, date_iso):
    """Wrapper kept for spot_finder compatibility — reuses cached weather data."""
    times, clouds = get_weather(round(lat, 2), round(lng, 2))
    return get_night_cloud_from(times, clouds, date_iso)

def get_week_clouds(lat, lng):
    """Wrapper for chart — reuses the same cached call as everything else."""
    return get_weather(round(lat, 2), round(lng, 2))

@st.cache_data(show_spinner=False)
def get_place_index():
    idx = dict(US_CITIES)
    for s in get_spots():
        idx[f"{s['name']} ({s['state']})"] = (s["lat"], s["lng"])
    return idx

@st.cache_data(ttl=3600, show_spinner=False)
def geocode_query(query):
    import urllib.request, urllib.parse, json
    url = (f"https://geocoding-api.open-meteo.com/v1/search"
           f"?name={urllib.parse.quote(query)}&count=8&language=en&country_code=US")
    try:
        with urllib.request.urlopen(url, timeout=6) as r:
            data = json.loads(r.read())
        out = []
        for r in (data.get("results") or []):
            if r.get("latitude") is None: continue
            label = f"{r.get('name','')}, {r.get('admin1','')}"
            out.append((label.strip(", "), float(r["latitude"]), float(r["longitude"])))
        return out
    except Exception:
        return []

# ── Location bar (top of page, horizontal) ───────────────────────────────────
st.markdown("## SkyWatch")
loc_c1, loc_c2, loc_c3 = st.columns([2, 3, 1.2])

with loc_c1:
    input_mode = st.radio("Input mode", ["City", "Search", "Coordinates"],
                          horizontal=True, label_visibility="collapsed")

with loc_c2:
    if input_mode == "City":
        for k in ("search_lat","search_lng","search_label"):
            st.session_state.pop(k, None)
        all_options = list(CITY_GROUPS.keys())
        seattle_idx = next((i for i, k in enumerate(all_options) if k == "Seattle, WA"), None)
        default_idx = seattle_idx if seattle_idx is not None else next(i for i, k in enumerate(all_options) if k not in SEPARATORS)
        selected_city = st.selectbox("Location", all_options, index=default_idx,
                                     format_func=lambda n: n,
                                     label_visibility="collapsed")
        if selected_city in SEPARATORS:
            selected_city = all_options[all_options.index(selected_city) + 1]
        lat, lng = US_CITIES[selected_city]
        location_label = selected_city
        st.session_state["selected_city_name"] = selected_city

    elif input_mode == "Search":
        index = get_place_index()
        query = st.text_input("Search", placeholder="Type any US city or town…",
                              key="place_search_query", label_visibility="collapsed")
        if query and len(query) >= 2:
            local = [n for n in index if query.lower() in n.lower()][:10]
            if local:
                choice = st.selectbox("Match", local, key="place_search_choice",
                                      label_visibility="collapsed")
                st.session_state.update({"search_lat": index[choice][0],
                                         "search_lng": index[choice][1],
                                         "search_label": choice})
            else:
                with st.spinner("Searching…"):
                    live = geocode_query(query)
                if live:
                    choice_i = st.selectbox("Match", [l for l,_,_ in live],
                                            key="place_search_choice",
                                            label_visibility="collapsed")
                    chosen = next(r for r in live if r[0] == choice_i)
                    st.session_state.update({"search_lat": chosen[1],
                                             "search_lng": chosen[2],
                                             "search_label": chosen[0]})
                else:
                    st.caption("No results — try a nearby city.")
        if "search_lat" in st.session_state:
            lat = st.session_state["search_lat"]
            lng = st.session_state["search_lng"]
            location_label = st.session_state.get("search_label", f"{lat:.2f}, {lng:.2f}")
        else:
            # Fall back to current city selection so data stays consistent
            _city_name = st.session_state.get("selected_city_name", "Seattle, WA")
            lat, lng = US_CITIES.get(_city_name, (47.6062, -122.3321))
            location_label = _city_name

    else:
        for k in ("search_lat","search_lng","search_label"):
            st.session_state.pop(k, None)
        # Default coordinates to current city selection
        _city_name = st.session_state.get("selected_city_name", "Seattle, WA")
        _def_lat, _def_lng = US_CITIES.get(_city_name, (47.6062, -122.3321))
        cv1, cv2 = st.columns(2)
        lat = cv1.number_input("Lat", value=_def_lat, min_value=18.0, max_value=72.0,
                               format="%.4f", label_visibility="collapsed")
        lng = cv2.number_input("Lng", value=_def_lng, min_value=-180.0, max_value=-66.0,
                               format="%.4f", label_visibility="collapsed")
        # Try to find a nearby known city name for the label
        _coord_label = None
        for _cname, (_clat, _clng) in US_CITIES.items():
            if abs(_clat - lat) < 0.05 and abs(_clng - lng) < 0.05:
                _coord_label = _cname
                break
        location_label = _coord_label if _coord_label else f"Custom location ({lat:.2f}°, {lng:.2f}°)"

with loc_c3:
    engine = SkyEngine(lat, lng)
    tz     = engine.tz
    today  = datetime.datetime.now(tz).date()
    selected_date = st.date_input("Date", value=today, label_visibility="collapsed")

st.caption(f"**{location_label}**  ·  {selected_date.strftime('%A, %B %-d %Y')}  ·  {engine.tz_name}")

# ── Compute all sky data ──────────────────────────────────────────────────────
with st.spinner(""):
    sun     = engine.get_sun_events(selected_date)
    moon    = engine.get_moon_events(selected_date)
    mw      = engine.get_milky_way_window(selected_date)
    planets = engine.get_planet_events(selected_date)
    shower  = engine.get_meteor_shower(selected_date)
    quality = engine.get_sky_quality(selected_date)
    best    = engine.get_best_night_this_week(selected_date)

sunrise_q = quality["sunrise"]["score"]
sunset_q  = quality["sunset"]["score"]
mw_q      = quality["milky_way"]["score"]

# Log this page load — mw and weather are now available
try:
    _times_raw, _ = get_weather(round(lat, 2), round(lng, 2))
    log_pageload(
        location   = location_label,
        lat        = lat,
        lng        = lng,
        date       = selected_date,
        mw_visible = bool(mw.get("visible")),
        weather_ok = len(_times_raw) > 0,
    )
except Exception as _log_err:
    log_error(location_label, lat, lng, selected_date, _log_err)

# ── Plain English summary ─────────────────────────────────────────────────────
def build_summary():
    parts = []
    # Cloud / conditions
    cloud_reason = quality.get("milky_way", {}).get("reason", "")
    if "clear" in cloud_reason.lower():
        parts.append("Clear skies expected tonight")
    elif "cloud" in cloud_reason.lower():
        parts.append("Some cloud cover expected tonight")
    else:
        parts.append(f"Tonight near {location_label.split(',')[0]}")
    # Moon
    illum = moon['illumination']
    phase = moon['phase_name']
    if illum < 15:
        parts.append(f"new moon — ideal for stargazing")
    elif illum < 40:
        parts.append(f"thin {phase.lower()} ({illum}% lit) sets by {fmt(moon['moonset'])}")
    elif illum > 75:
        parts.append(f"bright {phase.lower()} ({illum}% lit) will wash out faint stars")
    else:
        parts.append(f"{phase} ({illum}% lit)")
    # Milky Way
    if mw.get("visible"):
        _dir = compass_from_azimuth(mw.get("window_start_azimuth"))
        parts.append(f"Milky Way visible {fmt(mw['window_start'])}–{fmt(mw['window_end'])} to the {_dir[1]}")
    else:
        parts.append("Milky Way core below horizon tonight")
    # Shower
    if shower.get("active"):
        parts.append(f"{shower['name']} meteor shower peaking — up to {shower['rate']}/hr")
    return ". ".join(p[0].upper() + p[1:] for p in parts) + "."

st.markdown(f'<div class="summary-card">{build_summary()}</div>', unsafe_allow_html=True)

st.markdown("---")

# ── Main 3-column layout ──────────────────────────────────────────────────────
col_times, col_sky, col_spots = st.columns([1.1, 1.2, 1.4])

# ── Column 1: Event Times ─────────────────────────────────────────────────────
with col_times:
    st.markdown('<div class="section-header">Event Times</div>', unsafe_allow_html=True)

    gh = sun.get("morning_golden_hour", {})
    ev = sun.get("evening_golden_hour", {})
    tw = sun.get("twilight", {})

    # Event rows: (label, value, quality_score, tooltip_text)
    true_dark_start = tw.get("astronomical_end")
    true_dark_end   = tw.get("astronomical_start")

    if true_dark_start and true_dark_end:
        dark_window = f"{fmt(true_dark_start)} – {fmt(true_dark_end)}"
        dark_tip = "The window when the sky is fully dark and stars are at their brightest. Outside this window the sun is still lighting up the atmosphere."
    elif true_dark_start:
        dark_window = f"After {fmt(true_dark_start)}"
        dark_tip = "Sky reaches full darkness after this time."
    else:
        dark_window = "None tonight"
        dark_tip = "No true darkness tonight — common in midsummer at northern latitudes."

    rows = [
        ("Sunrise",       fmt(sun.get("sunrise")),   sunrise_q,
         "Sun appears above the horizon."),
        ("Golden hour (AM)",   f"{fmt(gh.get('start'))} – {fmt(gh.get('end'))}",  None,
         "Soft, warm light just after sunrise — best time for outdoor photos."),
        ("Sunset",        fmt(sun.get("sunset")),    sunset_q,
         "Sun dips below the horizon."),
        ("Golden hour (PM)",   f"{fmt(ev.get('start'))} – {fmt(ev.get('end'))}",  None,
         "Soft, warm light just before sunset — best time for outdoor photos."),
        ("Moonrise",      fmt(moon.get("moonrise")), None,
         "Moon appears above the horizon. A bright moon can wash out stars."),
        ("Moonset",       fmt(moon.get("moonset")),  None,
         "Moon drops below the horizon. Stargazing improves after this."),
        ("Civil twilight",
         f"{fmt(tw.get('civil_end'))} – {fmt(tw.get('civil_start'))}", None,
         "Period after sunset (and before sunrise) when it is dim but not fully dark — still enough light to see outside without a torch. Good for setting up equipment or hiking out."),
        ("Dark sky (Astronomical twilight)", dark_window, None,
         dark_tip),
    ]
    if mw.get("visible"):
        rows.append(("Milky Way",
                     f"{fmt(mw.get('window_start'))} – {fmt(mw.get('window_end'))}",
                     mw_q,
                     "Window when the bright core of the Milky Way is above the horizon and visible to the naked eye."))
    else:
        rows.append(("Milky Way", "Not visible tonight", "poor",
                     "The Milky Way core stays below the horizon tonight. Most visible March–October from the US."))

    for label, value, score, tip in rows:
        r1, r2, r3 = st.columns([1.3, 1.8, 0.3])
        r1.caption(label, help=tip)
        r2.markdown(f"**{value}**")
        if score:
            r3.markdown(score_dot(score), unsafe_allow_html=True)

# ── Column 2: Sky Conditions ──────────────────────────────────────────────────
with col_sky:
    st.markdown('<div class="section-header">Sky Conditions</div>', unsafe_allow_html=True)

    # Moon card
    st.markdown(f"**Moon** — {moon['phase_name']} ({moon['phase_icon']})")
    st.caption(f"{moon['illumination']}% illuminated (brightness in the sky). "
               + ("Ideal for stargazing." if moon['illumination'] < 25
                  else "Some interference with faint stars." if moon['illumination'] < 60
                  else "Bright — will wash out the Milky Way."))

    st.markdown("")

    # Milky Way direction
    if mw.get("visible"):
        _dir  = compass_from_azimuth(mw.get("window_start_azimuth"))
        _peak = mw.get("window_peak_altitude")
        st.markdown("**Milky Way direction**")
        st.caption(
            f"Look to the **{_dir[1]}** as it rises. "
            f"Reaches about **{_peak:.0f}° above the horizon** tonight — {altitude_words(_peak)}. "
            f"(Technical: azimuth {mw.get('window_start_azimuth'):.0f}°, altitude {_peak:.0f}°)"
        )
        st.markdown("")

    # Quality scores — tight spacing, dot aligned with text
    st.markdown("**Conditions**")
    for label, score, reason in [
        ("Sunrise",   sunrise_q, quality["sunrise"]["reason"]),
        ("Sunset",    sunset_q,  quality["sunset"]["reason"]),
        ("Milky Way", mw_q,      quality["milky_way"]["reason"]),
    ]:
        dot_color = SCORE_COLOR.get(score, "#888")
        st.markdown(
            f'''<div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:4px;">
            <span style="color:{dot_color};font-size:0.9rem;line-height:1.5;flex-shrink:0;">●</span>
            <span style="font-size:0.82rem;color:#ccc;line-height:1.5;"><strong style="color:#fff">{label}</strong> — {reason}</span>
            </div>''',
            unsafe_allow_html=True
        )

    st.markdown("")

    # Planets — compact table
    st.markdown("**Planets tonight**")
    visible_p   = [p for p in planets if p.get("visible_tonight")]
    invisible_p = [p for p in planets if not p.get("visible_tonight")]
    if visible_p:
        st.caption("Visible: " + ", ".join(
            f"{p['name']} (rises {fmt(p['rise'])})" for p in visible_p))
    if invisible_p:
        st.caption("Below horizon: " + ", ".join(p['name'] for p in invisible_p))

    # Shower alert
    if shower.get("active"):
        st.markdown("")
        st.info(f"**{shower['name']} meteor shower** — peak tonight, up to {shower['rate']}/hr")
    elif shower.get("upcoming"):
        st.markdown("")
        st.caption(f"{shower['name']} shower peaks in {shower['days_to_peak']} days "
                   f"({shower['peak'].strftime('%b %-d')})")

# ── Column 3: Nearby Spots ────────────────────────────────────────────────────
with col_spots:
    st.markdown('<div class="section-header">Nearby Viewing Spots</div>', unsafe_allow_html=True)
    st.caption("Areas ranked by tonight's conditions. Verify access, permits, seasonal closures, and safety conditions before visiting.")

    spots    = get_spots()
    date_iso = selected_date.isoformat()
    region   = guess_state(lat, lng)
    max_mi   = REGION_MAX_MILES.get(region, 250)

    # Pre-fetch weather once for the user location; spot lookups reuse this cache
    _w_times, _w_clouds = get_weather(round(lat, 2), round(lng, 2))

    def _cloud_lookup(s_lat, s_lng):
        # Each spot still gets its own call but it hits the cache instantly
        # if coordinates are close (rounded to 2dp)
        t, c = get_weather(round(s_lat, 2), round(s_lng, 2))
        return get_night_cloud_from(t, c, date_iso)

    mw_dir     = compass_from_azimuth(mw.get("window_start_azimuth")) if mw.get("visible") else None
    mw_windows = ({"start_str": fmt(mw.get("window_start")),
                   "end_str":   fmt(mw.get("window_end"))}
                  if mw.get("visible") else None)

    tab_mw, tab_ss, tab_sr = st.tabs(["Milky Way / Stars", "Sunset", "Sunrise"])
    for tab, ev, direction, windows in [
        (tab_mw, "milkyway", mw_dir, mw_windows),
        (tab_ss, "sunset",   None,   None),
        (tab_sr, "sunrise",  None,   None),
    ]:
        with tab:
            ranked = find_nearby_spots(lat, lng, spots, event_type=ev,
                                       max_miles=max_mi, candidate_pool=8,
                                       limit=3, cloud_lookup=_cloud_lookup)
            if not ranked:
                st.caption("No curated spots within range for this event type yet.")
                continue
            for r in ranked:
                head, detail = describe_spot(r, event_type=ev,
                                             mw_direction=direction,
                                             mw_window=windows)
                s = r["spot"]
                gmaps = (f"https://www.google.com/maps/dir/?api=1"
                         f"&destination={s['lat']},{s['lng']}")
                st.markdown(
                    f'<div class="spot-card"><strong>{head}</strong><br>'
                    f'<span style="color:#aaa;font-size:0.8rem">{detail}</span><br>'
                    f'<a href="{gmaps}" target="_blank" style="font-size:0.8rem">Directions</a>'
                    f'</div>',
                    unsafe_allow_html=True
                )

st.markdown("---")

# ── 7-Night Forecast Chart ────────────────────────────────────────────────────
st.markdown('<div class="section-header">7-Night Sky Forecast</div>', unsafe_allow_html=True)
st.caption("Nightly sky quality score (0–100) based on cloud cover and moon phase. "
           "Higher is better for stargazing.")

try:
    import altair as alt
    import pandas as pd

    times_raw, clouds_raw = get_week_clouds(round(lat, 2), round(lng, 2))

    if times_raw:
        # Build one row per night: average cloud 20:00–02:00, moon illumination
        rows_7 = []
        for day_offset in range(7):
            night_date = selected_date + datetime.timedelta(days=day_offset)
            next_date  = night_date + datetime.timedelta(days=1)
            nd_iso     = night_date.isoformat()
            nx_iso     = next_date.isoformat()
            vals = [c for t, c in zip(times_raw, clouds_raw)
                    if c is not None and
                    ((t[:10] == nd_iso and int(t[11:13]) >= 20) or
                     (t[:10] == nx_iso  and int(t[11:13]) <= 2))]
            avg_cloud = sum(vals) / len(vals) if vals else 50
            # Moon illumination for that night
            moon_n = engine.get_moon_events(night_date)
            illum  = moon_n.get("illumination", 50)
            # Sky score: cloud penalty + moon penalty
            cloud_score = max(0, 100 - avg_cloud)
            moon_penalty = illum * 0.4
            sky_score = max(0, min(100, cloud_score - moon_penalty))
            label = "Tonight" if day_offset == 0 else night_date.strftime("%a %-d")
            rows_7.append({
                "Night": label,
                "Score": round(sky_score),
                "Cloud": round(avg_cloud),
                "Moon":  illum,
                "date":  night_date,
            })

        df = pd.DataFrame(rows_7)
        df["color"] = df["Score"].apply(
            lambda s: "#2ecc71" if s >= 65 else "#f39c12" if s >= 40 else "#e74c3c")

        chart = (
            alt.Chart(df)
            .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
            .encode(
                x=alt.X("Night:N", sort=None, axis=alt.Axis(labelAngle=0, title=None)),
                y=alt.Y("Score:Q", scale=alt.Scale(domain=[0, 100]),
                        axis=alt.Axis(title="Sky Quality (0–100)")),
                color=alt.Color("color:N", scale=None, legend=None),
                tooltip=[
                    alt.Tooltip("Night:N", title="Night"),
                    alt.Tooltip("Score:Q", title="Sky quality"),
                    alt.Tooltip("Cloud:Q", title="Avg cloud cover %"),
                    alt.Tooltip("Moon:Q",  title="Moon illumination %"),
                ],
            )
            .properties(height=180)
            .configure_view(strokeWidth=0)
            .configure_axis(grid=False, labelColor="#aaa", titleColor="#aaa")
        )
        st.altair_chart(chart, use_container_width=True)

        # Best night callout
        best_row = df.loc[df["Score"].idxmax()]
        if best_row["Score"] >= 40:
            st.caption(
                f"Best night this week: **{best_row['Night']}** "
                f"(score {best_row['Score']}/100 — "
                f"{best_row['Cloud']:.0f}% cloud cover, moon {best_row['Moon']}% lit)"
            )
    else:
        st.caption("Chart unavailable — weather data could not be fetched.")

except ImportError:
    st.caption("Install `altair` and `pandas` for the forecast chart: "
               "`pip install altair pandas`")

st.markdown("---")
st.caption(
    "Astronomy: astronomy-engine  ·  Weather: Open-Meteo (free, non-commercial)  ·  "
    "Timezone: timezonefinder  ·  All times local  ·  "
    "Distances are straight-line; drive times are estimates."
)