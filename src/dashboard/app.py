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


@st.cache_data(ttl=60, show_spinner="Chargement des séances…")
def load_runs():
    from sqlalchemy.orm import Session as DBSession

    from src.common.database import WorkoutSession, engine

    with DBSession(engine) as session:
        all_sessions = session.query(WorkoutSession).order_by(WorkoutSession.date).all()
        session.expunge_all()

    rows = []
    for s in all_sessions:
        if str(s.sport_type).lower() not in ["sporttype.running", "running"]:
            continue
        if not s.distance_km or s.distance_km < 1:
            continue
        if not s.duration_minutes or s.duration_minutes < 2:
            continue
        rows.append(
            {
                "id": s.id,
                "date": s.date,
                "sport_type": "running",
                "distance_km": s.distance_km,
                "duration_min": s.duration_minutes,
                "avg_hr": s.avg_heart_rate,
                "max_hr": s.max_heart_rate,
                "avg_pace_min_km": s.avg_pace_min_km,
                "elevation_m": s.elevation_gain_m,
                "calories": s.calories,
                "source": s.source or "manual",
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
    return df, SamsungHealthParser()


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

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 Courses", "📋 Détail", "📅 Période", "➕ Ajouter une séance", "✏️ Gérer mes séances"]
    )

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

    with tab4:
        st.subheader("Ajouter une séance manuellement")

        with st.form("add_session"):
            col1, col2 = st.columns(2)
            with col1:
                date = st.date_input("Date")
                heure = st.time_input("Heure")
                distance = st.number_input("Distance (km)", min_value=0.0, step=0.1)

                st.markdown("**Durée**")
                col_dmin, col_dsec = st.columns(2)
                with col_dmin:
                    duree_min = st.number_input(
                        "Minutes", min_value=0, step=1, value=0, key="dur_min"
                    )
                with col_dsec:
                    duree_sec = st.number_input(
                        "Secondes", min_value=0, max_value=59, step=1, value=0, key="dur_sec"
                    )

                st.markdown("**Allure moyenne (min/km)**")
                col_amin, col_asec = st.columns(2)
                with col_amin:
                    allure_min = st.number_input("Min", min_value=0, step=1, value=0, key="all_min")
                with col_asec:
                    allure_sec = st.number_input(
                        "Sec", min_value=0, max_value=59, step=1, value=0, key="all_sec"
                    )

            with col2:
                fc_moy = st.number_input("FC moyenne (bpm)", min_value=0, step=1)
                fc_max = st.number_input("FC max (bpm)", min_value=0, step=1)
                calories = st.number_input("Calories", min_value=0, step=1)
                elevation = st.number_input("Dénivelé (m)", min_value=0.0, step=1.0)
                notes = st.text_area("Notes (optionnel)")

            submitted = st.form_submit_button("💾 Enregistrer la séance", type="primary")

        if submitted:
            duree = duree_min + duree_sec / 60
            allure = allure_min + allure_sec / 60 if (allure_min + allure_sec) > 0 else 0

            if distance <= 0 or duree <= 0:
                st.error("La distance et la durée sont obligatoires.")
            else:
                from datetime import datetime

                from sqlalchemy.orm import Session as DBSession

                from src.common.database import WorkoutSession, engine

                start_dt = datetime.combine(date, heure)

                # Calcul allure automatique si non renseignée
                if allure == 0 and distance > 0:
                    allure = duree / distance

                new_session = WorkoutSession(
                    sport_type="running",
                    date=start_dt,
                    duration_minutes=round(duree, 2),
                    distance_km=round(distance, 3),
                    calories=int(calories) if calories > 0 else None,
                    avg_heart_rate=int(fc_moy) if fc_moy > 0 else None,
                    max_heart_rate=int(fc_max) if fc_max > 0 else None,
                    avg_pace_min_km=round(allure, 2) if allure > 0 else None,
                    elevation_gain_m=round(elevation, 1) if elevation > 0 else None,
                    notes=notes if notes else None,
                    source="manual",
                )

                with DBSession(engine) as db_session:
                    db_session.add(new_session)
                    db_session.commit()

                st.success(
                    f"✅ Séance du {date.strftime('%d/%m/%Y')} enregistrée — "
                    f"{distance} km en {duree_min}min{duree_sec:02d}s"
                )
                st.cache_data.clear()
                st.rerun()

    with tab5:
        st.subheader("✏️ Gérer mes séances manuelles")

        from sqlalchemy.orm import Session as DBSession

        from src.common.database import WorkoutSession, engine

        # Charge uniquement les séances manuelles
        with DBSession(engine) as db_session:
            manual_sessions = (
                db_session.query(WorkoutSession)
                .filter(WorkoutSession.source == "manual")
                .order_by(WorkoutSession.date.desc())
                .all()
            )
            db_session.expunge_all()

        if not manual_sessions:
            st.info("Aucune séance manuelle. Ajoute-en une depuis l'onglet ➕ Ajouter.")
        else:
            # Selectbox pour choisir la séance
            options = {
                f"{s.date.strftime('%d/%m/%Y %H:%M')} — {s.distance_km} km "
                f"— {int(s.duration_minutes)}min{int((s.duration_minutes % 1) * 60):02d}s": s
                for s in manual_sessions
            }
            choix = st.selectbox("Sélectionne une séance", list(options.keys()))
            selected = options[choix]

            action = st.radio("Action", ["✏️ Modifier", "🗑️ Supprimer"], horizontal=True)

            if action == "🗑️ Supprimer":
                st.warning(
                    f"Tu vas supprimer la séance du {selected.date.strftime('%d/%m/%Y')} "
                    f"({selected.distance_km} km). Cette action est irréversible."
                )
                if st.button("✅ Confirmer la suppression", type="primary"):
                    with DBSession(engine) as db_session:
                        s = db_session.get(WorkoutSession, selected.id)
                        db_session.delete(s)
                        db_session.commit()
                    st.success("Séance supprimée.")
                    st.cache_data.clear()
                    st.rerun()

            elif action == "✏️ Modifier":
                # Durée décomposée
                dur_min_val = int(selected.duration_minutes)
                dur_sec_val = int((selected.duration_minutes % 1) * 60)

                # Allure décomposée
                pace = selected.avg_pace_min_km or 0
                pace_min_val = int(pace)
                pace_sec_val = int((pace % 1) * 60)

                with st.form("edit_session"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_date = st.date_input("Date", value=selected.date.date())
                        new_heure = st.time_input("Heure", value=selected.date.time())
                        new_distance = st.number_input(
                            "Distance (km)",
                            min_value=0.0,
                            step=0.1,
                            value=float(selected.distance_km or 0),
                        )

                        st.markdown("**Durée**")
                        cd1, cd2 = st.columns(2)
                        with cd1:
                            new_dur_min = st.number_input(
                                "Minutes",
                                min_value=0,
                                step=1,
                                value=dur_min_val,
                                key="edit_dur_min",
                            )
                        with cd2:
                            new_dur_sec = st.number_input(
                                "Secondes",
                                min_value=0,
                                max_value=59,
                                step=1,
                                value=dur_sec_val,
                                key="edit_dur_sec",
                            )

                        st.markdown("**Allure moyenne (min/km)**")
                        ca1, ca2 = st.columns(2)
                        with ca1:
                            new_all_min = st.number_input(
                                "Min", min_value=0, step=1, value=pace_min_val, key="edit_all_min"
                            )
                        with ca2:
                            new_all_sec = st.number_input(
                                "Sec",
                                min_value=0,
                                max_value=59,
                                step=1,
                                value=pace_sec_val,
                                key="edit_all_sec",
                            )

                    with col2:
                        new_fc_moy = st.number_input(
                            "FC moyenne (bpm)",
                            min_value=0,
                            step=1,
                            value=int(selected.avg_heart_rate or 0),
                        )
                        new_fc_max = st.number_input(
                            "FC max (bpm)",
                            min_value=0,
                            step=1,
                            value=int(selected.max_heart_rate or 0),
                        )
                        new_calories = st.number_input(
                            "Calories", min_value=0, step=1, value=int(selected.calories or 0)
                        )
                        new_elevation = st.number_input(
                            "Dénivelé (m)",
                            min_value=0.0,
                            step=1.0,
                            value=float(selected.elevation_gain_m or 0),
                        )
                        new_notes = st.text_area("Notes", value=selected.notes or "")

                    save = st.form_submit_button("💾 Enregistrer les modifications", type="primary")

                if save:
                    new_duree = new_dur_min + new_dur_sec / 60
                    new_allure = new_all_min + new_all_sec / 60

                    if new_distance <= 0 or new_duree <= 0:
                        st.error("La distance et la durée sont obligatoires.")
                    else:
                        from datetime import datetime

                        with DBSession(engine) as db_session:
                            s = db_session.get(WorkoutSession, selected.id)
                            s.date = datetime.combine(new_date, new_heure)
                            s.distance_km = round(new_distance, 3)
                            s.duration_minutes = round(new_duree, 2)
                            s.avg_pace_min_km = (
                                round(new_allure, 2)
                                if new_allure > 0
                                else round(new_duree / new_distance, 2)
                            )
                            s.avg_heart_rate = int(new_fc_moy) if new_fc_moy > 0 else None
                            s.max_heart_rate = int(new_fc_max) if new_fc_max > 0 else None
                            s.calories = int(new_calories) if new_calories > 0 else None
                            s.elevation_gain_m = (
                                round(new_elevation, 1) if new_elevation > 0 else None
                            )
                            s.notes = new_notes if new_notes else None
                            db_session.commit()

                        st.success("✅ Séance modifiée avec succès.")
                        st.cache_data.clear()
                        st.rerun()

# ── Offres d'emploi ───────────────────────────────────────────────────────────
elif page == "🔍 Offres d'emploi":
    from src.dashboard.modules.jobs import render

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
    st.info("MLflow disponible sur localhost:5000. Les premiers modèles seront trackés plus tard")
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
