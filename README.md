# SkyWatch

> **Is tonight worth going outside?**

A lightweight web app that answers the one question every amateur stargazer, photographer, and nature lover asks - and tells you exactly where to go to make the most of it.

---

## The Story

During a meteor shower, the weather around Boston was bad - overcast and no sign of clearing. I wanted to see it badly enough that I got in the car and started driving north, checking weather maps on my phone, looking for a gap in the clouds. I ended up at a beach in northern Massachusetts, found a patch of clear sky, and it was worth every mile.

The next trip I was planning, I realised I had no idea what the moon phase would be. A full moon would wash out everything I came to see. Sunrise and sunset times, when the Milky Way would be visible, whether the sky would even get dark enough - that information existed somewhere, scattered across four or five different apps and websites, none of which talked to each other.

That is what SkyWatch is. Weather is not in our control but sunrise times, moon phases, Milky Way windows, and which nearby spot has the darkest sky are all knowable in advance. This app puts all of it in one place, so the only variable left on the night is the one we cannot predict.

---

## What It Does

- **Sky event times** — Sunrise, golden hour, sunset, moonrise, moonset, and Milky Way window for any US location, in order, in plain English
- **One-sentence summary** — Answers "should I go out tonight?" before you see a single number
- **7-night forecast chart** — Sky quality score (0–100) for the week ahead, so you can pick the best night rather than just check tonight
- **Nearby viewing spots** — 86 curated dark-sky parks, national parks, and viewpoints ranked by tonight's actual cloud cover and darkness, not just distance
- **Where to look** — The Milky Way direction and how high it will climb, so you know whether a treeline or building will block it
- **Planets and meteor showers** — Which planets are visible tonight and whether any active shower is peaking
- **Full US coverage** — All timezones including Alaska and Hawaii, with location search for any US town or city

---

## Dashboard Layout

```
[ Location search / City dropdown ]        [ Date picker ]
[ Plain-English summary — one sentence                   ]
───────────────────────────────────────────────────────────
[ Event Times ]   [ Sky Conditions ]   [ Nearby Spots    ]
───────────────────────────────────────────────────────────
[ 7-Night Sky Quality Forecast — bar chart               ]
```

Single-page dashboard. No scrolling required on a standard laptop screen.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Frontend / app | Streamlit |
| Astronomy calculations | astronomy-engine (runs locally, no API) |
| Weather & cloud cover | Open-Meteo API (free, no key required) |
| Geocoding / location search | Open-Meteo Geocoding API (free) |
| Data visualisation | Altair |
| Timezone resolution | timezonefinder |
| Spot data | Curated JSON — 116 locations across all 50 states |

**Running cost: $0.** All data sources are free for non-commercial use. No API keys required.

---

## Data Sources

| Data | Source | License |
|---|---|---|
| Sun / moon / Milky Way math | astronomy-engine | MIT |
| Hourly cloud cover forecast | Open-Meteo | Free (non-commercial) |
| Place search / geocoding | Open-Meteo Geocoding | Free |
| Dark-sky certified locations | DarkSky International | Public data |
| National Parks | NPS open data | Public domain |
| Viewpoints & landmarks | Curated + OpenStreetMap | ODbL |
| Sky darkness estimates | Curated Bortle ratings per spot (estimated) | — |

---

## Run Locally

```bash
git clone https://github.com/YOUR_USERNAME/skywatch.git
cd skywatch
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

App opens at `http://localhost:8501`

---

## Live App

[**Open SkyWatch →**](https://your-streamlit-url.streamlit.app)

---

## What Is Next

The MVP is complete and working. Three things are on the roadmap that are grounded, feasible, and would genuinely improve the experience:

- **Real light pollution ratings** — Bortle scale values per spot are currently estimated. Replacing them with NOAA VIIRS satellite data would make the darkness ratings accurate and verifiable
- **Terrain-aware horizons** — The app currently tells you when the Milky Way is above the horizon. Using free USGS elevation data it could tell you when it clears the actual ridgeline or hill at your specific spot — a meaningful difference in the mountains
- **Public telescope venues** — Places like Griffith Observatory in LA offer free public telescope nights but are too light-polluted for the Milky Way. A separate category for these would serve a different user who wants a guided experience rather than a dark sky

---

*Built with Python and Streamlit. All astronomy calculations run locally — no third-party astronomy API.*