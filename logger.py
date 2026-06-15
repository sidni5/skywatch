"""
logger.py — Lightweight usage logging for SkyWatch.

Design principles:
  * No personally identifiable information (PII) is logged.
    Location names are logged but no IP addresses, user IDs, or session tokens.
  * Append-only CSV so logs survive app restarts.
  * Fails silently — a logging error never breaks the app.
  * Log file is excluded from Git via .gitignore.

Log schema (one row per app load):
  timestamp   | ISO 8601 UTC
  location    | City or search term the user selected
  lat         | Rounded to 2dp (not precise enough to identify an address)
  lng         | Rounded to 2dp
  date        | The sky date being viewed
  mw_visible  | Whether Milky Way was visible for that location/date
  weather_ok  | Whether the weather API responded successfully
  event       | Optional event name for specific interactions
  error       | Error message if something failed, else empty
"""

import csv
import datetime
import os
import traceback

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "usage.csv")

FIELDNAMES = [
    "timestamp", "location", "lat", "lng", "date",
    "mw_visible", "weather_ok", "event", "error"
]


def _ensure_log_file():
    """Create logs directory and write CSV header if file doesn't exist."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def log_pageload(location: str, lat: float, lng: float,
                 date, mw_visible: bool, weather_ok: bool):
    """
    Log a page load event. Call once per Streamlit rerun after data is computed.
    All failures are caught and suppressed so logging never breaks the app.
    """
    try:
        _ensure_log_file()
        row = {
            "timestamp":  datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "location":   location[:100],           # cap length
            "lat":        round(lat, 2),             # not precise enough to identify an address
            "lng":        round(lng, 2),
            "date":       str(date),
            "mw_visible": int(mw_visible),
            "weather_ok": int(weather_ok),
            "event":      "pageload",
            "error":      "",
        }
        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writerow(row)
    except Exception:
        pass  # Logging must never break the app


def log_error(location: str, lat: float, lng: float, date, error: Exception):
    """Log an application error with context."""
    try:
        _ensure_log_file()
        row = {
            "timestamp":  datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "location":   location[:100],
            "lat":        round(lat, 2),
            "lng":        round(lng, 2),
            "date":       str(date),
            "mw_visible": "",
            "weather_ok": "",
            "event":      "error",
            "error":      str(error)[:300],
        }
        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writerow(row)
    except Exception:
        pass


def log_event(event: str, location: str = "", lat: float = 0, lng: float = 0):
    """Log a named interaction event (e.g. 'spot_directions_click')."""
    try:
        _ensure_log_file()
        row = {
            "timestamp":  datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "location":   location[:100],
            "lat":        round(lat, 2),
            "lng":        round(lng, 2),
            "date":       "",
            "mw_visible": "",
            "weather_ok": "",
            "event":      event[:50],
            "error":      "",
        }
        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writerow(row)
    except Exception:
        pass


def get_summary():
    """
    Return a summary dict for the monitoring dashboard.
    Returns None if no log data exists yet.
    """
    try:
        import pandas as pd
        if not os.path.exists(LOG_FILE):
            return None
        df = pd.read_csv(LOG_FILE)
        if df.empty:
            return None

        pageloads = df[df["event"] == "pageload"]
        errors    = df[df["event"] == "error"]

        top_locations = (
            pageloads["location"].value_counts().head(5).to_dict()
            if not pageloads.empty else {}
        )
        weather_success_rate = (
            round(pageloads["weather_ok"].astype(float).mean() * 100, 1)
            if not pageloads.empty else None
        )
        mw_visible_rate = (
            round(pageloads["mw_visible"].astype(float).mean() * 100, 1)
            if not pageloads.empty else None
        )

        return {
            "total_loads":          len(pageloads),
            "total_errors":         len(errors),
            "top_locations":        top_locations,
            "weather_success_pct":  weather_success_rate,
            "mw_visible_pct":       mw_visible_rate,
            "log_file":             LOG_FILE,
        }
    except Exception:
        return None