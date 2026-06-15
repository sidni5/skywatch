import datetime
import math
import urllib.request
import json
import astronomy
import pytz
from timezonefinder import TimezoneFinder

_tf = TimezoneFinder()

# ── Planets visible to naked eye ──────────────────────────────────────────────
PLANETS = [
    astronomy.Body.Mercury,
    astronomy.Body.Venus,
    astronomy.Body.Mars,
    astronomy.Body.Jupiter,
    astronomy.Body.Saturn,
]
PLANET_NAMES = {
    astronomy.Body.Mercury: ("Mercury", "☿"),
    astronomy.Body.Venus:   ("Venus",   "♀"),
    astronomy.Body.Mars:    ("Mars",    "♂"),
    astronomy.Body.Jupiter: ("Jupiter", "♃"),
    astronomy.Body.Saturn:  ("Saturn",  "♄"),
}

# ── Meteor showers (hardcoded — orbital mechanics don't change) ───────────────
METEOR_SHOWERS = [
    {"name": "Quadrantids",   "peak": (1,  3),  "rate": 120, "icon": "☄️"},
    {"name": "Lyrids",        "peak": (4,  22), "rate": 18,  "icon": "☄️"},
    {"name": "Eta Aquariids", "peak": (5,  6),  "rate": 50,  "icon": "☄️"},
    {"name": "Perseids",      "peak": (8,  12), "rate": 100, "icon": "☄️"},
    {"name": "Orionids",      "peak": (10, 21), "rate": 20,  "icon": "☄️"},
    {"name": "Leonids",       "peak": (11, 17), "rate": 15,  "icon": "☄️"},
    {"name": "Geminids",      "peak": (12, 14), "rate": 150, "icon": "☄️"},
    {"name": "Ursids",        "peak": (12, 22), "rate": 10,  "icon": "☄️"},
]


def get_timezone_from_coords(lat: float, lng: float) -> pytz.BaseTzInfo:
    tz_name = _tf.timezone_at(lat=lat, lng=lng)
    if not tz_name:
        raise ValueError(f"Could not determine timezone for ({lat}, {lng})")
    return pytz.timezone(tz_name)


class SkyEngine:
    def __init__(self, lat: float, lng: float, timezone_str: str = None):
        self.lat = lat
        self.lng = lng
        self.observer = astronomy.Observer(lat, lng)
        self.tz = pytz.timezone(timezone_str) if timezone_str else get_timezone_from_coords(lat, lng)
        self.tz_name = str(self.tz)

    # ── Internal helpers ──────────────────────────────────────────────────────
    def _to_local(self, ast_time) -> datetime.datetime:
        if ast_time is None:
            return None
        if hasattr(ast_time, 'time'):
            ast_time = ast_time.time
        try:
            time_str = str(ast_time).replace('Z', '+00:00')
            utc_dt = datetime.datetime.fromisoformat(time_str)
            return utc_dt.astimezone(self.tz)
        except Exception:
            pass
        try:
            j2000 = datetime.datetime(2000, 1, 1, 12, 0, 0, tzinfo=pytz.utc)
            return (j2000 + datetime.timedelta(days=ast_time.ut)).astimezone(self.tz)
        except Exception:
            return None

    def _py_to_ast(self, dt: datetime.datetime) -> astronomy.Time:
        u = dt.astimezone(pytz.utc)
        return astronomy.Time.Make(u.year, u.month, u.day, u.hour, u.minute, u.second)

    def _midnight(self, date: datetime.date) -> datetime.datetime:
        return datetime.datetime.combine(date, datetime.time(0, 0), tzinfo=self.tz)

    def _today(self) -> datetime.date:
        return datetime.datetime.now(self.tz).date()

    # ── Sun ───────────────────────────────────────────────────────────────────
    def get_sun_events(self, date: datetime.date = None) -> dict:
        date = date or self._today()
        anchor = self._py_to_ast(self._midnight(date))

        sunrise_t = astronomy.SearchRiseSet(astronomy.Body.Sun, self.observer, astronomy.Direction.Rise, anchor, 1)
        sunset_t  = astronomy.SearchRiseSet(astronomy.Body.Sun, self.observer, astronomy.Direction.Set,  anchor, 1)

        # Civil twilight = -6° (golden hour boundary)
        morning_twilight = astronomy.SearchAltitude(astronomy.Body.Sun, self.observer, astronomy.Direction.Rise, sunrise_t, -1, -6.0) if sunrise_t else None
        evening_twilight = astronomy.SearchAltitude(astronomy.Body.Sun, self.observer, astronomy.Direction.Set,  sunset_t,   1, -6.0) if sunset_t  else None

        # Nautical twilight = -12°
        morning_nautical = astronomy.SearchAltitude(astronomy.Body.Sun, self.observer, astronomy.Direction.Rise, sunrise_t, -1, -12.0) if sunrise_t else None
        evening_nautical = astronomy.SearchAltitude(astronomy.Body.Sun, self.observer, astronomy.Direction.Set,  sunset_t,   1, -12.0) if sunset_t  else None

        # Astronomical twilight = -18° (true darkness)
        morning_astro = astronomy.SearchAltitude(astronomy.Body.Sun, self.observer, astronomy.Direction.Rise, sunrise_t, -1, -18.0) if sunrise_t else None
        evening_astro = astronomy.SearchAltitude(astronomy.Body.Sun, self.observer, astronomy.Direction.Set,  sunset_t,   1, -18.0) if sunset_t  else None

        sunrise_local = self._to_local(sunrise_t)
        sunset_local  = self._to_local(sunset_t)

        return {
            "sunrise": sunrise_local,
            "sunset":  sunset_local,
            "morning_golden_hour": {
                "start": self._to_local(morning_twilight),
                "end":   sunrise_local
            },
            "evening_golden_hour": {
                "start": sunset_local,
                "end":   self._to_local(evening_twilight)
            },
            "twilight": {
                "civil_end":        self._to_local(evening_twilight),
                "nautical_end":     self._to_local(evening_nautical),
                "astronomical_end": self._to_local(evening_astro),
                "astronomical_start": self._to_local(morning_astro),
                "nautical_start":   self._to_local(morning_nautical),
                "civil_start":      self._to_local(morning_twilight),
            }
        }

    # ── Moon ──────────────────────────────────────────────────────────────────
    def get_moon_events(self, date: datetime.date = None) -> dict:
        date = date or self._today()
        anchor = self._py_to_ast(self._midnight(date))

        moonrise_t = astronomy.SearchRiseSet(astronomy.Body.Moon, self.observer, astronomy.Direction.Rise, anchor, 1)
        moonset_t  = astronomy.SearchRiseSet(astronomy.Body.Moon, self.observer, astronomy.Direction.Set,  anchor, 1)

        moon_phase_deg = astronomy.MoonPhase(anchor)
        moon_illum     = 50.0 * (1.0 - math.cos(math.radians(moon_phase_deg)))
        phase_name, phase_icon = self._moon_phase_label(moon_phase_deg)

        return {
            "moonrise":     self._to_local(moonrise_t),
            "moonset":      self._to_local(moonset_t),
            "illumination": round(moon_illum, 1),
            "phase_name":   phase_name,
            "phase_icon":   phase_icon,
        }

    @staticmethod
    def _moon_phase_label(deg):
        a = deg % 360
        if a < 22.5 or a >= 337.5:  return "New Moon",        "🌑"
        elif a < 67.5:               return "Waxing Crescent", "🌒"
        elif a < 112.5:              return "First Quarter",   "🌓"
        elif a < 157.5:              return "Waxing Gibbous",  "🌔"
        elif a < 202.5:              return "Full Moon",       "🌕"
        elif a < 247.5:              return "Waning Gibbous",  "🌖"
        elif a < 292.5:              return "Last Quarter",    "🌗"
        else:                        return "Waning Crescent", "🌘"

    # ── Milky Way ─────────────────────────────────────────────────────────────
    def get_milky_way_window(self, date: datetime.date = None) -> dict:
        date = date or self._today()
        start_dt   = datetime.datetime.combine(date, datetime.time(16, 0), tzinfo=self.tz)
        anchor     = self._py_to_ast(self._midnight(date))

        moon_phase_deg = astronomy.MoonPhase(anchor)
        moon_illum     = 50.0 * (1.0 - math.cos(math.radians(moon_phase_deg)))

        # Darkness check FIRST
        sun_dark = astronomy.SearchAltitude(
            astronomy.Body.Sun, self.observer, astronomy.Direction.Set,
            self._py_to_ast(start_dt), 1, -12.0
        )
        if not sun_dark:
            return {"visible": False, "reason": "Midnight sun / twilight — sky never gets fully dark tonight.", "moon_illumination": moon_illum}

        gc_ra, gc_dec = 17.7611, -29.0078
        window_start = window_end = None
        start_azimuth = None
        peak_dt = None
        peak_alt = -90.0
        lat = self.observer.latitude

        def _altaz(ha_deg):
            """Return (altitude_deg, azimuth_deg) of the galactic center.
            Azimuth measured clockwise from North (0=N, 90=E, 180=S, 270=W)."""
            sin_alt = (math.sin(math.radians(lat)) * math.sin(math.radians(gc_dec)) +
                       math.cos(math.radians(lat)) * math.cos(math.radians(gc_dec)) * math.cos(math.radians(ha_deg)))
            sin_alt = max(-1.0, min(1.0, sin_alt))
            alt = math.degrees(math.asin(sin_alt))
            cos_alt = math.cos(math.radians(alt))
            if abs(cos_alt) < 1e-9:
                return alt, 0.0
            cos_az = (math.sin(math.radians(gc_dec)) - math.sin(math.radians(lat)) * sin_alt) / (math.cos(math.radians(lat)) * cos_alt)
            cos_az = max(-1.0, min(1.0, cos_az))
            az = math.degrees(math.acos(cos_az))
            # If the object is west of the meridian (sin HA > 0), reflect the azimuth.
            if math.sin(math.radians(ha_deg)) > 0:
                az = 360.0 - az
            return alt, az

        for minutes in range(0, 18 * 60, 10):
            test_dt  = start_dt + datetime.timedelta(minutes=minutes)
            test_ast = self._py_to_ast(test_dt)
            gast     = astronomy.SiderealTime(test_ast)
            last     = gast + (self.observer.longitude / 15.0)
            ha       = (last - gc_ra) * 15.0
            altitude, azimuth = _altaz(ha)
            if altitude > 10.0:
                if window_start is None:
                    window_start = test_dt
                    start_azimuth = azimuth
                window_end = test_dt
                if altitude > peak_alt:
                    peak_alt = altitude
                    peak_dt = test_dt

        if window_start is None:
            return {"visible": False, "reason": "Galactic center stays below 10° tonight. Best: March–October, southern US latitudes.",
                    "moon_illumination": moon_illum, "window_start_azimuth": None,
                    "window_peak": None, "window_peak_altitude": None}

        return {
            "visible":              True,
            "window_start":         window_start,
            "window_end":           window_end,
            "window_start_azimuth": start_azimuth,
            "window_peak":          peak_dt,
            "window_peak_altitude": round(peak_alt, 1),
            "moon_illumination":    moon_illum,
            "reason":               "Galactic center is above the horizon."
        }

    # ── Planets ───────────────────────────────────────────────────────────────
    def get_planet_events(self, date: datetime.date = None) -> list:
        date   = date or self._today()
        anchor = self._py_to_ast(self._midnight(date))
        result = []

        for body in PLANETS:
            name, icon = PLANET_NAMES[body]
            try:
                rise_t    = astronomy.SearchRiseSet(body, self.observer, astronomy.Direction.Rise, anchor, 1)
                set_t     = astronomy.SearchRiseSet(body, self.observer, astronomy.Direction.Set,  anchor, 1)
                rise_local = self._to_local(rise_t)
                set_local  = self._to_local(set_t)

                # Is it up at some point tonight (after sunset, before sunrise)?
                sun      = self.get_sun_events(date)
                sunset   = sun.get("sunset")
                sunrise  = sun.get("sunrise")
                visible_tonight = False

                if rise_local and set_local and sunset and sunrise:
                    # Visible if it's above horizon during any part of the night
                    visible_tonight = rise_local < sunrise or set_local > sunset

                result.append({
                    "name":            name,
                    "icon":            icon,
                    "rise":            rise_local,
                    "set":             set_local,
                    "visible_tonight": visible_tonight,
                })
            except Exception:
                result.append({"name": name, "icon": icon, "rise": None, "set": None, "visible_tonight": False})

        return result

    # ── Meteor showers ────────────────────────────────────────────────────────
    def get_meteor_shower(self, date: datetime.date = None) -> dict:
        date = date or self._today()
        for shower in METEOR_SHOWERS:
            peak_m, peak_d = shower["peak"]
            peak_date = datetime.date(date.year, peak_m, peak_d)
            delta = abs((date - peak_date).days)
            if delta <= 2:
                return {
                    "active": True,
                    "name":   shower["name"],
                    "icon":   shower["icon"],
                    "rate":   shower["rate"],
                    "peak":   peak_date,
                    "days_to_peak": (peak_date - date).days
                }
        # Check upcoming within 7 days
        for shower in METEOR_SHOWERS:
            peak_m, peak_d = shower["peak"]
            peak_date = datetime.date(date.year, peak_m, peak_d)
            days_away = (peak_date - date).days
            if 0 < days_away <= 7:
                return {
                    "active":      False,
                    "upcoming":    True,
                    "name":        shower["name"],
                    "icon":        shower["icon"],
                    "rate":        shower["rate"],
                    "peak":        peak_date,
                    "days_to_peak": days_away
                }
        return {"active": False, "upcoming": False}

    # ── Cloud cover + sky quality (Open-Meteo) ────────────────────────────────
    def get_sky_quality(self, date: datetime.date = None) -> dict:
        """
        Fetches cloud cover, visibility, humidity, and precipitation probability
        from Open-Meteo for the given date. Returns a 🟢🟡🔴 signal per event.
        Falls back gracefully if the API is unreachable.
        """
        date = date or self._today()
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={self.lat}&longitude={self.lng}"
            f"&hourly=cloudcover,visibility,relativehumidity_2m,precipitation_probability"
            f"&timezone=auto&forecast_days=7"
        )
        try:
            with urllib.request.urlopen(url, timeout=8) as r:
                data = json.loads(r.read())
            times   = data["hourly"]["time"]
            clouds  = data["hourly"]["cloudcover"]
            vis     = data["hourly"]["visibility"]
            humid   = data["hourly"]["relativehumidity_2m"]
            precip  = data["hourly"]["precipitation_probability"]

            def get_hour_val(target_dt, values):
                if target_dt is None:
                    return None
                target_str = target_dt.astimezone(pytz.utc).strftime("%Y-%m-%dT%H:00")
                for i, t in enumerate(times):
                    if t == target_str:
                        return values[i]
                return None

            def score(cloud, hum, prec):
                """Returns 'great', 'ok', or 'poor' + one-line reason."""
                if cloud is None:
                    return "unknown", "Weather data unavailable"
                if cloud > 70 or prec > 50:
                    return "poor", f"Heavy cloud cover ({cloud}%) or rain likely ({prec}%)"
                if cloud > 35 or hum > 85:
                    return "ok", f"Partial clouds ({cloud}%) or high humidity ({hum}%)"
                return "great", f"Clear skies ({cloud}% cloud cover, {hum}% humidity)"

            sun = self.get_sun_events(date)
            mw  = self.get_milky_way_window(date)

            sunrise_cloud  = get_hour_val(sun.get("sunrise"), clouds)
            sunset_cloud   = get_hour_val(sun.get("sunset"),  clouds)
            mw_cloud       = get_hour_val(mw.get("window_start"), clouds) if mw.get("visible") else None

            sunrise_hum   = get_hour_val(sun.get("sunrise"), humid)
            sunset_hum    = get_hour_val(sun.get("sunset"),  humid)
            mw_hum        = get_hour_val(mw.get("window_start"), humid) if mw.get("visible") else None

            sunrise_prec  = get_hour_val(sun.get("sunrise"), precip)
            sunset_prec   = get_hour_val(sun.get("sunset"),  precip)
            mw_prec       = get_hour_val(mw.get("window_start"), precip) if mw.get("visible") else None

            sunrise_score, sunrise_reason = score(sunrise_cloud, sunrise_hum, sunrise_prec)
            sunset_score,  sunset_reason  = score(sunset_cloud,  sunset_hum,  sunset_prec)
            mw_score,      mw_reason      = score(mw_cloud,      mw_hum,      mw_prec)

            return {
                "available":      True,
                "sunrise":        {"score": sunrise_score, "reason": sunrise_reason, "cloud": sunrise_cloud},
                "sunset":         {"score": sunset_score,  "reason": sunset_reason,  "cloud": sunset_cloud},
                "milky_way":      {"score": mw_score,      "reason": mw_reason,      "cloud": mw_cloud},
            }

        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "sunrise":   {"score": "unknown", "reason": "Weather data unavailable (no internet?)", "cloud": None},
                "sunset":    {"score": "unknown", "reason": "Weather data unavailable (no internet?)", "cloud": None},
                "milky_way": {"score": "unknown", "reason": "Weather data unavailable (no internet?)", "cloud": None},
            }

    # ── 7-day best night finder ───────────────────────────────────────────────
    def get_best_night_this_week(self, start_date: datetime.date = None) -> dict:
        """
        Scans the next 7 days and returns the best night for Milky Way viewing
        based on moon illumination and galactic center visibility.
        """
        start_date = start_date or self._today()
        best = None
        best_score = -1

        for i in range(7):
            d  = start_date + datetime.timedelta(days=i)
            mw = self.get_milky_way_window(d)
            if not mw["visible"]:
                continue
            # Score: lower moon = better. Window length bonus.
            moon_score   = 100 - mw["moon_illumination"]
            window_hours = 0
            if mw.get("window_start") and mw.get("window_end"):
                window_hours = (mw["window_end"] - mw["window_start"]).seconds / 3600
            total_score = moon_score + (window_hours * 3)

            if total_score > best_score:
                best_score = total_score
                best = {
                    "date":           d,
                    "score":          round(total_score, 1),
                    "moon_illum":     round(mw["moon_illumination"], 1),
                    "window_start":   mw["window_start"],
                    "window_end":     mw["window_end"],
                    "days_from_now":  i,
                }

        return best or {"date": None, "reason": "No good Milky Way nights in the next 7 days."}