"""
pages/monitoring.py — Usage monitoring dashboard for SkyWatch.
Accessible at the /monitoring route in Streamlit's multipage navigation.
Shows aggregated, anonymised usage data — no PII.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import datetime

st.set_page_config(page_title="SkyWatch — Monitoring", page_icon="📊", layout="wide")

st.markdown("## SkyWatch — Usage Monitoring")
st.caption("Anonymised usage data. No personally identifiable information is collected or stored.")
st.markdown("---")

from logger import get_summary, LOG_FILE

summary = get_summary()

if summary is None:
    st.info("No usage data yet. Load the main app a few times and come back here.")
    st.stop()

# ── Top metrics ───────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total page loads",    summary["total_loads"])
c2.metric("Errors logged",       summary["total_errors"])
c3.metric("Weather API success", f"{summary['weather_success_pct']}%" if summary['weather_success_pct'] is not None else "—")
c4.metric("Milky Way visible",   f"{summary['mw_visible_pct']}% of loads" if summary['mw_visible_pct'] is not None else "—")

st.markdown("---")

# ── Top locations ─────────────────────────────────────────────────────────────
st.markdown("### Most searched locations")
if summary["top_locations"]:
    for loc, count in summary["top_locations"].items():
        st.caption(f"**{loc}** — {count} load{'s' if count != 1 else ''}")
else:
    st.caption("No location data yet.")

st.markdown("---")

# ── Raw log viewer ────────────────────────────────────────────────────────────
with st.expander("Raw log (last 50 entries)"):
    try:
        import pandas as pd
        df = pd.read_csv(LOG_FILE)
        st.dataframe(df.tail(50), use_container_width=True)
    except Exception as e:
        st.caption(f"Could not read log file: {e}")

st.markdown("---")
st.caption(f"Log file: `{LOG_FILE}`  ·  All times UTC")