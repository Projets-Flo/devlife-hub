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

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🚀 DevLife Hub")
    st.caption("Tableau de bord personnel")
    st.divider()
    page = st.radio(
        "Navigation",
        ["🏠 Accueil", "🔍 Offres d'emploi", "🏃 Sport", "🎯 Coach", "⚙️ ML Pipeline"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("v0.1.0 · dev mode")


# ── Chargement données Samsung (mis en cache) ─────────────────────────────────
@st.cache_data(show_spinner="Chargement des séances…")
def load_sport_data():
    parser = SamsungHealthParser()
    sessions = parser.parse_workouts()
    df = parser.to_dataframe(sessions)
    return df, parser


# ── Pages ─────────────────────────────────────────────────────────────────────

if page == "🏠 Accueil":
    st.title("Bonjour Florian 👋")
    st.caption("Voici ton résumé")

    df, parser = load_sport_data()
    runs = df[df["sport_type"] == "running"] if not df.empty else pd.DataFrame()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Séances totales", len(df))
    with col2:
        st.metric("Courses enregistrées", len(runs))
    with col3:
        total_km = round(runs["distance_km"].sum(), 1) if not runs.empty else 0
        st.metric("Km courus au total", f"{total_km} km")
    with col4:
        st.metric("Nouvelles offres", "—")

    st.divider()
    if not runs.empty:
        st.subheader("Progression km — 3 derniers mois")
        recent = runs[runs["date"] >= runs["date"].max() - pd.Timedelta(days=90)].copy()
        recent["week"] = recent["date"].dt.to_period("W").dt.start_time
        weekly = recent.groupby("week")["distance_km"].sum().reset_index()
        fig = px.bar(weekly, x="week", y="distance_km", labels={"week": "", "distance_km": "km"})
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=220)
        st.plotly_chart(fig, use_container_width=True)


elif page == "🏃 Sport":
    st.title("🏃 Activité sportive")
    df, parser = load_sport_data()

    if df.empty:
        st.warning(
            "Aucune donnée — vérifie que le dossier samsunghealth est bien dans data/exports/samsung_health/"
        )
        st.stop()

    tab1, tab2, tab3 = st.tabs(["📊 Courses", "💪 Toutes séances", "📅 Semaines"])

    runs = df[df["sport_type"] == "running"].copy()

    with tab1:
        st.subheader("Mes courses")

        if runs.empty:
            st.info("Aucune course trouvée.")
        else:
            # Métriques clés
            stats = parser.stats_running(df)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total courses", stats.get("total_sessions", 0))
            c2.metric("Km totaux", f"{stats.get('total_km', 0)} km")
            c3.metric("Plus longue sortie", f"{stats.get('best_km', 0)} km")
            c4.metric("Allure moyenne", f"{stats.get('avg_pace', 0)} min/km")

            st.divider()

            # Filtre période
            col_f1, col_f2 = st.columns([2, 1])
            with col_f1:
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

            # Graphe distance par sortie
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

            # Graphe allure
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

            # Tableau détail
            with st.expander("Voir toutes les sorties"):
                display = runs[
                    ["date", "distance_km", "duration_min", "avg_pace_min_km", "avg_hr", "calories"]
                ].copy()
                display["date"] = display["date"].dt.strftime("%d/%m/%Y %H:%M")
                display.columns = [
                    "Date",
                    "Distance (km)",
                    "Durée (min)",
                    "Allure (min/km)",
                    "FC moy.",
                    "Calories",
                ]
                st.dataframe(display, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Toutes les activités")
        counts = df["sport_type"].value_counts().reset_index()
        counts.columns = ["Type", "Séances"]
        counts["Type"] = counts["Type"].str.replace("SportType.", "")
        fig3 = px.pie(counts, values="Séances", names="Type", hole=0.4)
        fig3.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig3, use_container_width=True)

        st.dataframe(
            df[["date", "sport_type", "distance_km", "duration_min", "avg_hr", "calories"]]
            .tail(20)
            .sort_values("date", ascending=False)
            .assign(date=lambda x: x["date"].dt.strftime("%d/%m/%Y"))
            .rename(
                columns={
                    "date": "Date",
                    "sport_type": "Type",
                    "distance_km": "km",
                    "duration_min": "min",
                    "avg_hr": "FC",
                    "calories": "Cal",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    with tab3:
        st.subheader("Résumé hebdomadaire — courses")
        if not runs.empty:
            weekly = parser.weekly_summary(runs)
            weekly["week"] = weekly["week"].astype(str)
            fig4 = px.bar(
                weekly,
                x="week",
                y="total_km",
                labels={"week": "Semaine", "total_km": "km totaux"},
            )
            fig4.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig4, use_container_width=True)


elif page == "🔍 Offres d'emploi":
    st.title("🔍 Offres d'emploi")
    st.info(
        "📡 Le scraping automatique sera activé en Phase 2. "
        "En attendant, importe des offres via le CLI."
    )

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

elif page == "⚙️ ML Pipeline":
    st.title("⚙️ ML Pipeline")
    st.info(
        "MLflow disponible sur localhost:5000. " "Les premiers modèles seront trackés en Phase 3."
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
