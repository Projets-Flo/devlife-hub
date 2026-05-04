"""
DevLife Hub — Dashboard Streamlit
Point d'entrée : streamlit run src/dashboard/app.py
"""

import streamlit as st

st.set_page_config(
    page_title="DevLife Hub",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.sidebar:
    st.title("🚀 DevLife Hub")
    st.caption("Tableau de bord personnel")
    st.caption("Par Florian REY")
    st.divider()
    page = st.radio(
        "Navigation",
        ["🏠 Accueil", "🔍 Offres d'emploi", "🏃 Sport", "🎯 Coach", "⚙️ ML Pipeline"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("v0.1.0 · dev mode")

if page == "🏠 Accueil":
    from src.dashboard.pages.home import render

    render()

elif page == "🔍 Offres d'emploi":
    from src.dashboard.modules.jobs import render

    render()

elif page == "🏃 Sport":
    from src.dashboard.pages.sport import render

    render()

elif page == "🎯 Coach":
    from src.dashboard.pages.coach import render

    render()

elif page == "⚙️ ML Pipeline":
    from src.dashboard.pages.ml_pipeline import render

    render()
