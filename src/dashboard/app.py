"""
DevLife Hub — Dashboard Streamlit MVP
Point d'entrée : streamlit run src/dashboard/app.py
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.sport.parsers.samsung_health import SamsungHealthParser

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


@st.cache_data(show_spinner="Chargement des séances…")
def load_sport_data():
    parser = SamsungHealthParser()
    sessions = parser.parse_workouts()
    df = parser.to_dataframe(sessions)
    return df, parser


@st.cache_data(show_spinner="Chargement des courses…")
def load_runs():
    df, parser = load_sport_data()
    df, parser = load_sport_data()
    runs = df[
        (df["sport_type"] == "running")
        & (df["distance_km"].notna())
        & (df["distance_km"] >= 1)
        & (df["duration_min"] >= 2)
    ].copy()
    return runs, parser


# ── Accueil ───────────────────────────────────────────────────────────────────
if page == "🏠 Accueil":
    st.title("Tableau de bord DevLife Hub ")
    # Sous-titre
    st.subheader("Voici ton résumé")

    runs, parser = load_runs()
    stats = parser.stats_running(runs)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total courses", len(runs))
    col2.metric("Km totaux", f"{stats.get('total_km', 0)} km")
    col3.metric("Plus longue sortie", f"{stats.get('best_km', 0)} km")
    col4.metric("Nouvelles offres", "—")

    st.divider()

    if not runs.empty:
        st.subheader("Km courus — 3 derniers mois")
        recent = runs[runs["date"] >= runs["date"].max() - pd.Timedelta(days=90)].copy()
        recent["week"] = recent["date"].dt.to_period("W").dt.start_time
        weekly = recent.groupby("week")["distance_km"].sum().reset_index()
        fig = px.bar(
            weekly,
            x="week",
            y="distance_km",
            labels={"week": "", "distance_km": "km"},
        )
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=220)
        st.plotly_chart(fig, use_container_width=True)


# ── Sport ─────────────────────────────────────────────────────────────────────
elif page == "🏃 Sport":
    st.title("🏃 Activité sportive")
    runs, parser = load_runs()

    if runs.empty:
        st.warning("Aucune donnée.")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["📊 Courses", "📋 Détail", "📅 Période"])

    with tab1:
        st.subheader("Mes courses")

        if runs.empty:
            st.info("Aucune course trouvée.")
        else:
            stats = parser.stats_running(runs)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total courses", stats.get("total_sessions", 0))
            c2.metric("Km totaux", f"{stats.get('total_km', 0)} km")
            c3.metric("Plus longue sortie", f"{stats.get('best_km', 0)} km")
            c4.metric("Sortie moyenne", f"{stats.get('avg_km', 0)} km")

            c5, c6, c7, c8 = st.columns(4)
            c5.metric("Allure moyenne", f"{stats.get('avg_pace', 0)} min/km")
            c6.metric("Meilleure allure", f"{stats.get('best_pace', 0)} min/km")
            c7.metric("FC moyenne", f"{stats.get('avg_hr', 0):.0f} bpm")
            c8.metric("Calories totales", f"{stats.get('total_calories', 0):,}")

            st.divider()

            periode = st.selectbox(
                "Période",
                ["Tout", "12 derniers mois", "6 derniers mois", "3 derniers mois"],
            )
            cutoffs = {
                "3 derniers mois": 90,
                "6 derniers mois": 180,
                "12 derniers mois": 365,
            }
            if periode in cutoffs:
                runs = runs[
                    runs["date"] >= runs["date"].max() - pd.Timedelta(days=cutoffs[periode])
                ]

            st.subheader("Distance par sortie")
            fig1 = px.scatter(
                runs,
                x="date",
                y="distance_km",
                color="avg_hr",
                color_continuous_scale="RdYlGn_r",
                labels={"date": "", "distance_km": "km", "avg_hr": "FC moy."},
                hover_data=["duration_min", "avg_pace_min_km"],
            )
            fig1.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig1, use_container_width=True)

            runs_with_pace = runs.dropna(subset=["avg_pace_min_km"])
            if not runs_with_pace.empty:
                st.subheader("Évolution de l'allure (min/km)")
                fig2 = px.line(
                    runs_with_pace.sort_values("date"),
                    x="date",
                    y="avg_pace_min_km",
                    labels={"date": "", "avg_pace_min_km": "min/km"},
                )
                fig2.update_layout(height=250, margin=dict(l=0, r=0, t=0, b=0))
                fig2.update_yaxes(autorange="reversed")
                st.plotly_chart(fig2, use_container_width=True)

            runs_with_hr = runs.dropna(subset=["avg_hr"])
            if not runs_with_hr.empty:
                st.subheader("Évolution de la fréquence cardiaque")
                fig3 = px.line(
                    runs_with_hr.sort_values("date"),
                    x="date",
                    y="avg_hr",
                    labels={"date": "", "avg_hr": "FC moy. (bpm)"},
                )
                fig3.update_layout(height=250, margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig3, use_container_width=True)

    with tab2:
        st.subheader("Toutes mes courses")
        display = (
            runs[["date", "distance_km", "duration_min", "avg_pace_min_km", "avg_hr", "calories"]]
            .copy()
            .sort_values("date", ascending=False)
        )
        display["date"] = display["date"].dt.strftime("%d/%m/%Y %H:%M")
        display.columns = [
            "Date",
            "Distance (km)",
            "Durée (min)",
            "Allure (min/km)",
            "FC moy.",
            "Calories brûlées",
        ]
        st.dataframe(display, use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("Résumé par période")

        decoupage = st.radio(
            "Découpage",
            ["Semaine", "Mois", "Année"],
            horizontal=True,
        )

        periode_map = {"Semaine": "W", "Mois": "M", "Année": "Y"}
        runs_copy = runs.copy()
        runs_copy["periode"] = runs_copy["date"].dt.to_period(periode_map[decoupage]).astype(str)

        summary = (
            runs_copy.groupby("periode")
            .agg(
                sessions=("date", "count"),
                total_km=("distance_km", "sum"),
                total_min=("duration_min", "sum"),
                avg_hr=("avg_hr", "mean"),
                avg_pace=("avg_pace_min_km", "mean"),
            )
            .round(1)
            .reset_index()
            .sort_values("periode", ascending=False)
        )

        fig = px.bar(
            summary.sort_values("periode"),
            x="periode",
            y="total_km",
            labels={"periode": "", "total_km": "km"},
        )
        fig.update_layout(height=280, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            summary.rename(
                columns={
                    "periode": "Période",
                    "sessions": "Séances",
                    "total_km": "Km totaux",
                    "total_min": "Durée (min)",
                    "avg_hr": "FC moy. (bpm)",
                    "avg_pace": "Allure moy. (min/km)",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


# ── Offres d'emploi ───────────────────────────────────────────────────────────
elif page == "🔍 Offres d'emploi":
    from src.dashboard.pages.jobs import render

    render()


# ── Coach ─────────────────────────────────────────────────────────────────────
elif page == "🎯 Coach":
    st.title("🎯 Coach quotidien")
    st.info(
        "Le module Coach (Claude API) sera activé une fois "
        "l'API configurée (.env → ANTHROPIC_API_KEY)."
    )
    st.subheader("Prochaines actions")
    st.markdown("""
    - [x] Setup projet ✓
    - [x] Docker + MLflow + Prefect ✓
    - [x] Import Samsung Health ✓ (1606 séances)
    - [ ] Module Job Search (scraping offres)
    - [ ] NLP matching CV ↔ offres
    - [ ] Module Coach (Claude API)
    """)


# ── ML Pipeline ───────────────────────────────────────────────────────────────
elif page == "⚙️ ML Pipeline":
    st.title("⚙️ ML Pipeline")
    st.info(
        "MLflow disponible sur localhost:5000. " "Les premiers modèles seront trackés plus tard"
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Modèles prévus**")
        st.markdown("""
        - 🔍 Job matcher (sentence-transformers)
        - 💰 Salary predictor (XGBoost)
        - 📈 Training load forecaster (Prophet)
        - 📄 CV gap analyzer
        """)
    with c2:
        st.markdown("**Stack MLOps**")
        st.markdown("""
        - 📊 MLflow — tracking
        - 🗂 DVC — versioning
        - 🐳 Docker — reproductibilité
        - ⚡ GitHub Actions — CI/CD
        """)
