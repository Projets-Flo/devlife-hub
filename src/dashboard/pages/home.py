import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.data.loaders import load_intervals, load_runs
from src.dashboard.utils.formatting import format_pace


def render():
    st.title("Tableau de bord DevLife Hub")
    st.subheader("Voici ton résumé")

    runs, parser = load_runs()
    intervals = load_intervals()
    stats = parser.stats_running(runs)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total courses", len(runs))
    col2.metric("Km courus", f"{stats.get('total_km', 0)} km")
    col3.metric("Meilleure allure", format_pace(stats.get("best_pace", 0)))
    col4.metric("Séances fractionné", len(intervals))
    col5.metric("Nouvelles offres", "—")

    st.divider()

    if not runs.empty:
        st.subheader("Km courus — 3 derniers mois")
        recent = runs[runs["date"] >= runs["date"].max() - pd.Timedelta(days=90)].copy()
        recent["week"] = recent["date"].dt.to_period("W").dt.start_time
        weekly = recent.groupby("week")["distance_km"].sum().reset_index()
        fig = px.bar(weekly, x="week", y="distance_km", labels={"week": "", "distance_km": "km"})
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=220)
        st.plotly_chart(fig, use_container_width=True)
