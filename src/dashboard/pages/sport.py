import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.components.interval_form import render_fractionne_form, render_time_input
from src.dashboard.components.interval_widgets import render_bloc_summary, render_interval_card
from src.dashboard.data.loaders import load_intervals, load_runs
from src.dashboard.utils.formatting import (
    format_duration,
    format_pace,
    format_track_time,
    track_time_to_seconds,
)


def render():
    st.title("🏃 Activité sportive")
    runs, parser = load_runs()
    intervals = load_intervals()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 Stats", "📋 Détail", "📅 Période", "➕ Ajouter", "✏️ Gérer"]
    )

    # ── TAB 1 : STATS ────────────────────────────────────────────────────────
    with tab1:
        st.subheader("🏃 Courses endurance")

        if runs.empty:
            st.info("Aucune course enregistrée.")
        else:
            date_min_global = runs["date"].min().date()
            date_max_global = runs["date"].max().date()

            col_mode, col_filtre = st.columns([1, 2])
            with col_mode:
                mode_filtre = st.radio(
                    "Filtrer par",
                    ["Période prédéfinie", "Dates personnalisées"],
                    horizontal=False,
                    key="run_filter_mode",
                )
            with col_filtre:
                if mode_filtre == "Période prédéfinie":
                    periode = st.selectbox(
                        "Période",
                        [
                            "Tout",
                            "Ce mois-ci",
                            "3 derniers mois",
                            "6 derniers mois",
                            "Cette année",
                            "12 derniers mois",
                        ],
                        key="stats_periode",
                    )
                    today = pd.Timestamp.today().normalize()
                    cutoffs = {
                        "Ce mois-ci": today.replace(day=1),
                        "3 derniers mois": today - pd.Timedelta(days=90),
                        "6 derniers mois": today - pd.Timedelta(days=180),
                        "Cette année": today.replace(month=1, day=1),
                        "12 derniers mois": today - pd.Timedelta(days=365),
                    }
                    date_debut = cutoffs.get(periode, pd.Timestamp(date_min_global))
                    date_fin = pd.Timestamp(date_max_global)
                else:
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        date_debut = pd.Timestamp(
                            st.date_input("Du", value=date_min_global, key="run_date_from")
                        )
                    with col_d2:
                        date_fin = pd.Timestamp(
                            st.date_input("Au", value=date_max_global, key="run_date_to")
                        )

            runs_filtered = runs[
                (runs["date"] >= date_debut) & (runs["date"] <= date_fin + pd.Timedelta(days=1))
            ].copy()

            if runs_filtered.empty:
                st.warning("Aucune course sur cette période.")
            else:
                stats = parser.stats_running(runs_filtered)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total courses", stats.get("total_sessions", 0))
                c2.metric("Km totaux", f"{stats.get('total_km', 0)} km")
                c3.metric("Plus longue sortie", f"{stats.get('best_km', 0)} km")
                c4.metric("Sortie moyenne", f"{stats.get('avg_km', 0)} km")

                c5, c6, c7, c8 = st.columns(4)
                c5.metric("Allure moyenne", format_pace(stats.get("avg_pace", 0)))
                c6.metric("Meilleure allure", format_pace(stats.get("best_pace", 0)))
                c7.metric("FC moyenne", f"{stats.get('avg_hr', 0):.0f} bpm")
                c8.metric("Calories totales", f"{stats.get('total_calories', 0):,}")

                st.divider()

                st.subheader("Distance par sortie")
                runs_hover = runs_filtered.copy()
                runs_hover["Durée"] = runs_hover["duration_min"].apply(format_duration)
                runs_hover["Allure"] = runs_hover["avg_pace_min_km"].apply(format_pace)
                fig1 = px.scatter(
                    runs_hover,
                    x="date",
                    y="distance_km",
                    color="avg_hr",
                    color_continuous_scale="RdYlGn_r",
                    labels={"date": "", "distance_km": "km", "avg_hr": "FC moy."},
                    hover_data={
                        "Durée": True,
                        "Allure": True,
                        "duration_min": False,
                        "avg_pace_min_km": False,
                    },
                )
                fig1.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig1, use_container_width=True)

                runs_pace = runs_filtered.dropna(subset=["avg_pace_min_km"])
                if not runs_pace.empty:
                    st.subheader("Évolution de l'allure")
                    runs_pace_hover = runs_pace.copy()
                    runs_pace_hover["Allure"] = runs_pace_hover["avg_pace_min_km"].apply(
                        format_pace
                    )
                    runs_pace_hover["Durée"] = runs_pace_hover["duration_min"].apply(
                        format_duration
                    )
                    fig2 = px.line(
                        runs_pace_hover.sort_values("date"),
                        x="date",
                        y="avg_pace_min_km",
                        labels={"date": "", "avg_pace_min_km": "min/km"},
                        hover_data={"Allure": True, "Durée": True, "avg_pace_min_km": False},
                    )
                    fig2.update_layout(height=250, margin=dict(l=0, r=0, t=0, b=0))
                    fig2.update_yaxes(autorange="reversed")
                    st.plotly_chart(fig2, use_container_width=True)

                runs_hr = runs_filtered.dropna(subset=["avg_hr"])
                if not runs_hr.empty:
                    st.subheader("Évolution de la fréquence cardiaque")
                    runs_hr_hover = runs_hr.copy()
                    runs_hr_hover["Durée"] = runs_hr_hover["duration_min"].apply(format_duration)
                    runs_hr_hover["Allure"] = runs_hr_hover["avg_pace_min_km"].apply(format_pace)
                    fig3 = px.line(
                        runs_hr_hover.sort_values("date"),
                        x="date",
                        y="avg_hr",
                        labels={"date": "", "avg_hr": "FC moy. (bpm)"},
                        hover_data={"Durée": True, "Allure": True},
                    )
                    fig3.update_layout(height=250, margin=dict(l=0, r=0, t=0, b=0))
                    st.plotly_chart(fig3, use_container_width=True)

        st.divider()
        st.subheader("⚡ Fractionné — progression")

        if not intervals:
            st.info("Aucune séance de fractionné enregistrée.")
        else:
            int_dates = [s.date for s in intervals]
            int_date_min = min(int_dates).date()
            int_date_max = max(int_dates).date()

            col_fm, col_ff = st.columns([1, 2])
            with col_fm:
                mode_int = st.radio(
                    "Filtrer par",
                    ["Période prédéfinie", "Dates personnalisées"],
                    horizontal=False,
                    key="int_filter_mode",
                )
            with col_ff:
                if mode_int == "Période prédéfinie":
                    per_int = st.selectbox(
                        "Période",
                        [
                            "Tout",
                            "Ce mois-ci",
                            "3 derniers mois",
                            "6 derniers mois",
                            "Cette année",
                            "12 derniers mois",
                        ],
                        key="int_periode_sel",
                    )
                    today_i = pd.Timestamp.today().normalize()
                    cutoffs_i = {
                        "Ce mois-ci": today_i.replace(day=1),
                        "3 derniers mois": today_i - pd.Timedelta(days=90),
                        "6 derniers mois": today_i - pd.Timedelta(days=180),
                        "Cette année": today_i.replace(month=1, day=1),
                        "12 derniers mois": today_i - pd.Timedelta(days=365),
                    }
                    int_debut = cutoffs_i.get(per_int, pd.Timestamp(int_date_min))
                    int_fin = pd.Timestamp(int_date_max)
                else:
                    ci1, ci2 = st.columns(2)
                    with ci1:
                        int_debut = pd.Timestamp(
                            st.date_input("Du", value=int_date_min, key="int_date_from")
                        )
                    with ci2:
                        int_fin = pd.Timestamp(
                            st.date_input("Au", value=int_date_max, key="int_date_to")
                        )

            intervals_filtered = [
                s
                for s in intervals
                if int_debut <= pd.Timestamp(s.date) <= int_fin + pd.Timedelta(days=1)
            ]

            if not intervals_filtered:
                st.info("Aucune séance fractionné sur cette période.")
            else:
                perf_rows = []
                for s in intervals_filtered:
                    blocs = s.blocs.get("blocs", []) if isinstance(s.blocs, dict) else []
                    for bloc in blocs:
                        if bloc.get("type") == "serie":
                            dist = bloc.get("distance_m", 0)
                            for rep in bloc.get("repetitions", []):
                                t = rep["temps_sec"]
                                perf_rows.append(
                                    {
                                        "date": s.date,
                                        "distance_m": dist,
                                        "temps_sec": t,
                                        "vitesse_kmh": round(dist * 3.6 / t, 2) if t > 0 else 0,
                                    }
                                )
                        elif bloc.get("type") == "serie_double":
                            dist = bloc.get("distance_m", 0)
                            for groupe in bloc.get("groupes", []):
                                for effort in groupe:
                                    t = effort["temps_sec"]
                                    perf_rows.append(
                                        {
                                            "date": s.date,
                                            "distance_m": dist,
                                            "temps_sec": t,
                                            "vitesse_kmh": (
                                                round(dist * 3.6 / t, 2) if t > 0 else 0
                                            ),
                                        }
                                    )

                if perf_rows:
                    perf_df = pd.DataFrame(perf_rows)
                    perf_df["date"] = pd.to_datetime(perf_df["date"])
                    distances = sorted(perf_df["distance_m"].unique())

                    st.markdown("**Récapitulatif par distance**")
                    table_rows = []
                    for dist in distances:
                        sub = perf_df[perf_df["distance_m"] == dist]
                        best_t = sub["temps_sec"].min()
                        last_t = sub.sort_values("date").iloc[-1]["temps_sec"]
                        best_v = sub["vitesse_kmh"].max()
                        avg_v = sub["vitesse_kmh"].mean()
                        last_v = sub.sort_values("date").iloc[-1]["vitesse_kmh"]
                        nb = len(sub)
                        table_rows.append(
                            {
                                "Distance": f"{int(dist)}m",
                                "Rép.": nb,
                                "⚡ Meilleur temps": format_track_time(best_t),
                                "🏁 Meilleure vitesse": f"{best_v:.1f} km/h",
                                "∅ Vitesse moy.": f"{avg_v:.1f} km/h",
                                "🕐 Dernier temps": format_track_time(last_t),
                                "📈 Dernière vitesse": f"{last_v:.1f} km/h",
                            }
                        )

                    st.dataframe(
                        pd.DataFrame(table_rows),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Distance": st.column_config.TextColumn("Distance", width="small"),
                            "Rép.": st.column_config.NumberColumn("Rép.", width="small"),
                            "⚡ Meilleur temps": st.column_config.TextColumn("⚡ Meilleur temps"),
                            "🏁 Meilleure vitesse": st.column_config.TextColumn(
                                "🏁 Meilleure vitesse"
                            ),
                            "∅ Vitesse moy.": st.column_config.TextColumn("∅ Vitesse moy."),
                            "🕐 Dernier temps": st.column_config.TextColumn("🕐 Dernier temps"),
                            "📈 Dernière vitesse": st.column_config.TextColumn(
                                "📈 Dernière vitesse"
                            ),
                        },
                    )

                    st.divider()

                    dist_choice = st.selectbox(
                        "Voir progression sur",
                        distances,
                        format_func=lambda x: f"{int(x)}m",
                        key="frac_dist_choice",
                    )

                    subset = perf_df[perf_df["distance_m"] == dist_choice].copy()
                    subset["date_jour"] = subset["date"].dt.date
                    subset["temps_fmt"] = subset["temps_sec"].apply(format_track_time)
                    subset["hover"] = subset.apply(
                        lambda r: f"{r['temps_fmt']} — {r['vitesse_kmh']:.1f} km/h", axis=1
                    )

                    best_per_session = (
                        subset.groupby("date_jour")["vitesse_kmh"].max().reset_index()
                    )
                    best_per_session.columns = ["date_jour", "vitesse_kmh"]
                    best_per_session["date"] = pd.to_datetime(best_per_session["date_jour"])
                    best_per_session = best_per_session.sort_values("date")
                    best_per_session["temps_sec"] = (
                        dist_choice * 3.6 / best_per_session["vitesse_kmh"]
                    )
                    best_per_session["temps_fmt"] = best_per_session["temps_sec"].apply(
                        format_track_time
                    )
                    best_per_session["hover"] = best_per_session.apply(
                        lambda r: f"{r['temps_fmt']} — {r['vitesse_kmh']:.1f} km/h", axis=1
                    )

                    fig_best = go.Figure()
                    fig_best.add_trace(
                        go.Scatter(
                            x=best_per_session["date"],
                            y=best_per_session["vitesse_kmh"],
                            mode="lines+markers",
                            line=dict(color="#1D9E75", width=2),
                            marker=dict(color="#1D9E75", size=9),
                            hovertext=best_per_session["hover"],
                            hovertemplate="%{hovertext}<extra></extra>",
                            showlegend=False,
                        )
                    )
                    fig_best.update_layout(
                        height=270,
                        margin=dict(l=0, r=0, t=30, b=0),
                        yaxis=dict(title="Vitesse (km/h)"),
                        xaxis=dict(title=""),
                        title=dict(
                            text=f"Meilleure vitesse par séance — {int(dist_choice)}m",
                            font=dict(size=13),
                        ),
                    )
                    st.plotly_chart(fig_best, use_container_width=True)

                    fig_all = go.Figure()
                    fig_all.add_trace(
                        go.Scatter(
                            x=subset["date"],
                            y=subset["vitesse_kmh"],
                            mode="markers",
                            marker=dict(color="#378ADD", size=8, opacity=0.7),
                            hovertext=subset["hover"],
                            hovertemplate="%{hovertext}<extra></extra>",
                            showlegend=False,
                        )
                    )
                    fig_all.update_layout(
                        height=270,
                        margin=dict(l=0, r=0, t=30, b=0),
                        yaxis=dict(title="Vitesse (km/h)"),
                        xaxis=dict(title=""),
                        title=dict(
                            text=f"Toutes les répétitions — {int(dist_choice)}m",
                            font=dict(size=13),
                        ),
                    )
                    st.plotly_chart(fig_all, use_container_width=True)
                    st.caption("Plus haut = plus rapide · Au survol : temps + vitesse")

    # ── TAB 2 : DÉTAIL ───────────────────────────────────────────────────────
    with tab2:
        st.subheader("🏃 Détail des courses d'endurance")
        col_tri, col_ordre = st.columns(2)
        with col_tri:
            tri = st.selectbox(
                "Trier par",
                ["Date", "Distance", "Durée", "Allure", "FC moy.", "Calories"],
                key="det_tri",
            )
        with col_ordre:
            ordre = st.radio(
                "Ordre", ["↓ Décroissant", "↑ Croissant"], horizontal=True, key="det_ordre"
            )

        tri_col = {
            "Date": "date",
            "Distance": "distance_km",
            "Durée": "duration_min",
            "Allure": "avg_pace_min_km",
            "FC moy.": "avg_hr",
            "Calories": "calories",
        }
        ascending = ordre == "↑ Croissant"

        if not runs.empty:
            display = (
                runs[
                    ["date", "distance_km", "duration_min", "avg_pace_min_km", "avg_hr", "calories"]
                ]
                .copy()
                .sort_values(tri_col[tri], ascending=ascending)
            )
            display["duration_min"] = display["duration_min"].apply(format_duration)
            display["avg_pace_min_km"] = display["avg_pace_min_km"].apply(format_pace)
            display["date"] = display["date"].dt.strftime("%d/%m/%Y %H:%M")
            display.columns = ["Date", "Distance (km)", "Durée", "Allure", "FC moy.", "Calories"]
            st.dataframe(
                display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Date": st.column_config.TextColumn("Date"),
                    "Distance (km)": st.column_config.NumberColumn("Distance (km)", format="%.3f"),
                    "Durée": st.column_config.TextColumn("Durée"),
                    "Allure": st.column_config.TextColumn("Allure"),
                },
            )
        else:
            st.info("Aucune course.")

        st.divider()
        st.subheader("⚡ Détail des séances fractionné")

        if not intervals:
            st.info("Aucune séance fractionné.")
        else:
            for s in intervals:
                render_interval_card(s)

    # ── TAB 3 : PÉRIODE ──────────────────────────────────────────────────────
    with tab3:
        st.subheader("🏃 Courses par période")

        if runs.empty:
            st.info("Aucune course enregistrée.")
        else:
            date_min_p = runs["date"].min().date()
            date_max_p = runs["date"].max().date()

            col_mode_p, col_filtre_p = st.columns([1, 2])
            with col_mode_p:
                mode_filtre_p = st.radio(
                    "Filtrer par",
                    ["Période prédéfinie", "Dates personnalisées"],
                    horizontal=False,
                    key="per_filter_mode",
                )
            with col_filtre_p:
                if mode_filtre_p == "Période prédéfinie":
                    periode_sel = st.selectbox(
                        "Période",
                        [
                            "Tout",
                            "Ce mois-ci",
                            "3 derniers mois",
                            "6 derniers mois",
                            "Cette année",
                            "12 derniers mois",
                        ],
                        key="per_periode_sel",
                    )
                    today_p = pd.Timestamp.today().normalize()
                    cutoffs_p = {
                        "Ce mois-ci": today_p.replace(day=1),
                        "3 derniers mois": today_p - pd.Timedelta(days=90),
                        "6 derniers mois": today_p - pd.Timedelta(days=180),
                        "Cette année": today_p.replace(month=1, day=1),
                        "12 derniers mois": today_p - pd.Timedelta(days=365),
                    }
                    p_debut = cutoffs_p.get(periode_sel, pd.Timestamp(date_min_p))
                    p_fin = pd.Timestamp(date_max_p)
                else:
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        p_debut = pd.Timestamp(
                            st.date_input("Du", value=date_min_p, key="per_date_from")
                        )
                    with col_p2:
                        p_fin = pd.Timestamp(
                            st.date_input("Au", value=date_max_p, key="per_date_to")
                        )

            runs_p = runs[
                (runs["date"] >= p_debut) & (runs["date"] <= p_fin + pd.Timedelta(days=1))
            ].copy()

            if runs_p.empty:
                st.warning("Aucune course sur cette période.")
            else:
                decoupage = st.radio(
                    "Découpage",
                    ["Semaine", "Mois", "Année"],
                    horizontal=True,
                    key="per_dec",
                )
                periode_map = {"Semaine": "W", "Mois": "M", "Année": "Y"}

                runs_copy = runs_p.copy()
                runs_copy["periode"] = (
                    runs_copy["date"].dt.to_period(periode_map[decoupage]).astype(str)
                )

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
                )

                all_periods = pd.period_range(
                    start=runs_p["date"].min(),
                    end=runs_p["date"].max(),
                    freq=periode_map[decoupage],
                ).astype(str)

                summary_full = (
                    pd.DataFrame({"periode": all_periods})
                    .merge(summary, on="periode", how="left")
                    .fillna({"sessions": 0, "total_km": 0, "total_min": 0})
                )

                nb_periodes = len(summary_full)
                periodes_actives = summary_full[summary_full["sessions"] > 0]
                regularite = round(len(periodes_actives) / nb_periodes * 100) if nb_periodes else 0
                km_par_periode = round(summary_full["total_km"].mean(), 1)
                label_periode = {"Semaine": "semaine", "Mois": "mois", "Année": "année"}[decoupage]

                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric(f"Km / {label_periode} (moy.)", f"{km_par_periode} km")
                mc2.metric(
                    f"Séances / {label_periode} (moy.)",
                    f"{summary_full['sessions'].mean():.1f}",
                )
                mc3.metric(
                    "Régularité",
                    f"{regularite}%",
                    help=(
                        f"{len(periodes_actives)} {label_periode}s actives "
                        f"sur {nb_periodes} au total"
                    ),
                )
                mc4.metric("Km total", f"{runs_p['distance_km'].sum():.1f} km")

                st.divider()

                def make_tick_labels(periods, freq):
                    labels = []
                    last_month = None
                    for p in periods:
                        try:
                            ts = pd.Period(p, freq=freq).start_time
                            month_key = (ts.year, ts.month)
                            if month_key != last_month:
                                labels.append(ts.strftime("%b %Y"))
                                last_month = month_key
                            else:
                                labels.append("")
                        except Exception:
                            labels.append("")
                    return labels

                tick_labels = make_tick_labels(
                    summary_full["periode"].tolist(), periode_map[decoupage]
                )

                fig_per = px.bar(
                    summary_full,
                    x="periode",
                    y="total_km",
                    labels={"periode": "", "total_km": "km"},
                    color="total_km",
                    color_continuous_scale="Teal",
                )
                fig_per.update_xaxes(
                    tickvals=summary_full["periode"].tolist(),
                    ticktext=tick_labels,
                    tickangle=-45,
                )
                fig_per.update_layout(
                    height=300,
                    margin=dict(l=0, r=0, t=30, b=60),
                    title=dict(text=f"Km par {label_periode}", font=dict(size=13)),
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig_per, use_container_width=True)

                fig_ses = px.bar(
                    summary_full,
                    x="periode",
                    y="sessions",
                    labels={"periode": "", "sessions": "Séances"},
                    color="sessions",
                    color_continuous_scale="Blues",
                )
                fig_ses.update_xaxes(
                    tickvals=summary_full["periode"].tolist(),
                    ticktext=tick_labels,
                    tickangle=-45,
                )
                fig_ses.update_layout(
                    height=250,
                    margin=dict(l=0, r=0, t=30, b=60),
                    title=dict(text=f"Séances par {label_periode}", font=dict(size=13)),
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig_ses, use_container_width=True)

                st.markdown("**Détail par période**")
                col_tri_p, col_ord_p = st.columns(2)
                with col_tri_p:
                    tri_p = st.selectbox(
                        "Trier par",
                        [
                            "Période",
                            "Séances",
                            "Km totaux",
                            "Durée totale",
                            "FC moy.",
                            "Allure moy.",
                        ],
                        key="per_tri",
                    )
                with col_ord_p:
                    ord_p = st.radio(
                        "Ordre",
                        ["↓ Décroissant", "↑ Croissant"],
                        horizontal=True,
                        key="per_ord",
                    )

                tri_col_p = {
                    "Période": "periode",
                    "Séances": "sessions",
                    "Km totaux": "total_km",
                    "Durée totale": "total_min",
                    "FC moy.": "avg_hr",
                    "Allure moy.": "avg_pace",
                }
                asc_p = ord_p == "↑ Croissant"
                summary_sorted = summary.sort_values(tri_col_p[tri_p], ascending=asc_p)

                summary_display = summary_sorted.copy()
                summary_display["total_min"] = summary_display["total_min"].apply(format_duration)
                summary_display["avg_pace"] = summary_display["avg_pace"].apply(format_pace)
                summary_display["avg_hr"] = summary_display["avg_hr"].round(0).astype("Int64")

                st.dataframe(
                    summary_display.rename(
                        columns={
                            "periode": "Période",
                            "sessions": "Séances",
                            "total_km": "Km totaux",
                            "total_min": "Durée totale",
                            "avg_hr": "FC moy.",
                            "avg_pace": "Allure moy.",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Période": st.column_config.TextColumn("Période"),
                        "Km totaux": st.column_config.NumberColumn("Km totaux", format="%.1f km"),
                        "Durée totale": st.column_config.TextColumn("Durée totale"),
                        "Allure moy.": st.column_config.TextColumn("Allure moy."),
                        "FC moy.": st.column_config.NumberColumn("FC moy."),
                    },
                )

        st.divider()
        st.subheader("⚡ Fractionné par période")

        if not intervals:
            st.info("Aucune séance fractionné.")
        else:
            int_rows = []
            for s in intervals:
                blocs = s.blocs.get("blocs", []) if isinstance(s.blocs, dict) else []
                total_m = 0
                nb_reps = 0
                for b in blocs:
                    if b.get("type") == "serie":
                        reps = b.get("repetitions", [])
                        total_m += b.get("distance_m", 0) * len(reps)
                        nb_reps += len(reps)
                    elif b.get("type") == "serie_double":
                        groupes = b.get("groupes", [])
                        total_m += b.get("distance_m", 0) * 2 * len(groupes)
                        nb_reps += len(groupes) * 2
                int_rows.append(
                    {
                        "date": pd.to_datetime(s.date),
                        "distance_m": total_m,
                        "nb_reps": nb_reps,
                    }
                )

            int_df = pd.DataFrame(int_rows)

            if not runs.empty:
                int_df_filtered = int_df[
                    (int_df["date"] >= p_debut) & (int_df["date"] <= p_fin + pd.Timedelta(days=1))
                ].copy()
            else:
                int_df_filtered = int_df.copy()
                periode_map = {"Semaine": "W", "Mois": "M", "Année": "Y"}
                label_periode = "période"

            if int_df_filtered.empty:
                st.info("Aucune séance fractionné sur cette période.")
            else:
                fi1, fi2, fi3 = st.columns(3)
                fi1.metric("Séances fractionné", len(int_df_filtered))
                fi2.metric("Répétitions totales", int(int_df_filtered["nb_reps"].sum()))
                fi3.metric("Distance totale", f"{int(int_df_filtered['distance_m'].sum())} m")

                int_df_filtered["periode"] = (
                    int_df_filtered["date"].dt.to_period(periode_map[decoupage]).astype(str)
                )
                int_summary = (
                    int_df_filtered.groupby("periode")
                    .agg(
                        seances=("date", "count"),
                        total_m=("distance_m", "sum"),
                        total_reps=("nb_reps", "sum"),
                    )
                    .reset_index()
                )

                fig_int = px.bar(
                    int_summary.sort_values("periode"),
                    x="periode",
                    y="total_reps",
                    labels={"periode": "", "total_reps": "Répétitions"},
                    color="total_reps",
                    color_continuous_scale="Purples",
                )
                fig_int.update_layout(
                    height=220,
                    margin=dict(l=0, r=0, t=30, b=0),
                    title=dict(
                        text=f"Répétitions de fractionné par {label_periode}",
                        font=dict(size=13),
                    ),
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig_int, use_container_width=True)

                st.markdown("**Détail par période**")
                col_tri_i, col_ord_i = st.columns(2)
                with col_tri_i:
                    tri_i = st.selectbox(
                        "Trier par",
                        ["Période", "Séances", "Distance (m)", "Répétitions"],
                        key="int_tri",
                    )
                with col_ord_i:
                    ord_i = st.radio(
                        "Ordre",
                        ["↓ Décroissant", "↑ Croissant"],
                        horizontal=True,
                        key="int_ord",
                    )

                tri_col_i = {
                    "Période": "periode",
                    "Séances": "seances",
                    "Distance (m)": "total_m",
                    "Répétitions": "total_reps",
                }
                asc_i = ord_i == "↑ Croissant"
                int_sorted = int_summary.sort_values(tri_col_i[tri_i], ascending=asc_i)

                st.dataframe(
                    int_sorted.rename(
                        columns={
                            "periode": "Période",
                            "seances": "Séances",
                            "total_m": "Distance (m)",
                            "total_reps": "Répétitions",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Période": st.column_config.TextColumn("Période"),
                        "Séances": st.column_config.NumberColumn("Séances"),
                        "Distance (m)": st.column_config.NumberColumn("Distance (m)"),
                        "Répétitions": st.column_config.NumberColumn("Répétitions"),
                    },
                )

    # ── TAB 4 : AJOUTER ──────────────────────────────────────────────────────
    with tab4:
        st.subheader("Ajouter une séance")

        type_seance = st.radio(
            "Type de séance",
            ["🏃 Course endurance", "⚡ Fractionné"],
            horizontal=True,
            key="add_type",
        )

        if type_seance == "🏃 Course endurance":
            with st.form("add_run"):
                col1, col2 = st.columns(2)
                with col1:
                    date = st.date_input("Date")
                    heure = st.time_input("Heure")
                    distance = st.number_input("Distance (km)", min_value=0.0, step=0.1)

                    st.markdown("**Durée**")
                    cd1, cd2 = st.columns(2)
                    with cd1:
                        duree_min = st.number_input(
                            "min", min_value=0, step=1, value=0, key="run_dur_m"
                        )
                    with cd2:
                        duree_sec = st.number_input(
                            "sec", min_value=0, max_value=59, step=1, value=0, key="run_dur_s"
                        )

                    st.markdown("**Allure moyenne**")
                    ca1, ca2 = st.columns(2)
                    with ca1:
                        allure_min = st.number_input(
                            "min", min_value=0, step=1, value=0, key="run_all_m"
                        )
                    with ca2:
                        allure_sec = st.number_input(
                            "sec", min_value=0, max_value=59, step=1, value=0, key="run_all_s"
                        )

                with col2:
                    fc_moy = st.number_input("FC moyenne (bpm)", min_value=0, step=1)
                    fc_max = st.number_input("FC max (bpm)", min_value=0, step=1)
                    calories = st.number_input("Calories", min_value=0, step=1)
                    elevation = st.number_input("Dénivelé (m)", min_value=0.0, step=1.0)
                    notes = st.text_area("Notes (optionnel)")

                submitted = st.form_submit_button("💾 Enregistrer la course", type="primary")

            if submitted:
                duree = duree_min + duree_sec / 60
                allure = allure_min + allure_sec / 60 if (allure_min + allure_sec) > 0 else 0
                if distance <= 0 or duree <= 0:
                    st.error("La distance et la durée sont obligatoires.")
                else:
                    from datetime import datetime

                    from sqlalchemy.orm import Session as DBSession

                    from src.common.database import WorkoutSession, engine

                    if allure == 0 and distance > 0:
                        allure = duree / distance
                    new_run = WorkoutSession(
                        sport_type="running",
                        date=datetime.combine(date, heure),
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
                        db_session.add(new_run)
                        db_session.commit()
                    st.success(
                        f"✅ Course du {date.strftime('%d/%m/%Y')} — "
                        f"{distance} km en {format_duration(duree)}"
                    )
                    st.cache_data.clear()
                    st.rerun()

        else:
            render_fractionne_form()

    # ── TAB 5 : GÉRER ────────────────────────────────────────────────────────
    with tab5:
        st.subheader("✏️ Gérer mes séances")

        from sqlalchemy.orm import Session as DBSession

        from src.common.database import IntervalSession, WorkoutSession, engine

        type_gestion = st.radio(
            "Type", ["🏃 Courses manuelles", "⚡ Fractionné"], horizontal=True, key="gest_type"
        )

        if type_gestion == "🏃 Courses manuelles":
            with DBSession(engine) as db_session:
                manual_runs = (
                    db_session.query(WorkoutSession)
                    .filter(WorkoutSession.source == "manual")
                    .order_by(WorkoutSession.date.desc())
                    .all()
                )
                db_session.expunge_all()

            if not manual_runs:
                st.info("Aucune course manuelle.")
            else:
                options = {
                    f"{s.date.strftime('%d/%m/%Y %H:%M')} — {s.distance_km} km"
                    f" — {format_duration(s.duration_minutes)}": s
                    for s in manual_runs
                }
                choix = st.selectbox(
                    "Sélectionne une course", list(options.keys()), key="gest_run_sel"
                )
                selected = options[choix]
                action = st.radio(
                    "Action",
                    ["✏️ Modifier", "🗑️ Supprimer"],
                    horizontal=True,
                    key="gest_run_action",
                )

                if action == "🗑️ Supprimer":
                    st.warning(
                        f"Supprimer la course du {selected.date.strftime('%d/%m/%Y')} "
                        f"({selected.distance_km} km) ? Action irréversible."
                    )
                    if st.button("✅ Confirmer la suppression", type="primary", key="del_run_btn"):
                        with DBSession(engine) as db_session:
                            s = db_session.get(WorkoutSession, selected.id)
                            db_session.delete(s)
                            db_session.commit()
                        st.success("Course supprimée.")
                        st.cache_data.clear()
                        st.rerun()

                elif action == "✏️ Modifier":
                    dur_min_val = int(selected.duration_minutes)
                    dur_sec_val = int(round((selected.duration_minutes % 1) * 60))
                    pace = selected.avg_pace_min_km or 0
                    pace_min_val = int(pace)
                    pace_sec_val = int(round((pace % 1) * 60))

                    with st.form("edit_run"):
                        col1, col2 = st.columns(2)
                        with col1:
                            new_date = st.date_input("Date", value=selected.date.date())
                            new_heure = st.time_input("Heure", value=selected.date.time())
                            new_dist = st.number_input(
                                "Distance (km)",
                                min_value=0.0,
                                step=0.1,
                                value=float(selected.distance_km or 0),
                            )

                            st.markdown("**Durée**")
                            cd1, cd2 = st.columns(2)
                            with cd1:
                                new_dur_m = st.number_input(
                                    "min",
                                    min_value=0,
                                    step=1,
                                    value=dur_min_val,
                                    key="edit_dur_m",
                                )
                            with cd2:
                                new_dur_s = st.number_input(
                                    "sec",
                                    min_value=0,
                                    max_value=59,
                                    step=1,
                                    value=dur_sec_val,
                                    key="edit_dur_s",
                                )

                            st.markdown("**Allure**")
                            ca1, ca2 = st.columns(2)
                            with ca1:
                                new_all_m = st.number_input(
                                    "min",
                                    min_value=0,
                                    step=1,
                                    value=pace_min_val,
                                    key="edit_all_m",
                                )
                            with ca2:
                                new_all_s = st.number_input(
                                    "sec",
                                    min_value=0,
                                    max_value=59,
                                    step=1,
                                    value=pace_sec_val,
                                    key="edit_all_s",
                                )

                        with col2:
                            new_fc_moy = st.number_input(
                                "FC moy.",
                                min_value=0,
                                step=1,
                                value=int(selected.avg_heart_rate or 0),
                            )
                            new_fc_max = st.number_input(
                                "FC max",
                                min_value=0,
                                step=1,
                                value=int(selected.max_heart_rate or 0),
                            )
                            new_cal = st.number_input(
                                "Calories",
                                min_value=0,
                                step=1,
                                value=int(selected.calories or 0),
                            )
                            new_elev = st.number_input(
                                "Dénivelé (m)",
                                min_value=0.0,
                                step=1.0,
                                value=float(selected.elevation_gain_m or 0),
                            )
                            new_notes = st.text_area("Notes", value=selected.notes or "")

                        save = st.form_submit_button("💾 Enregistrer", type="primary")

                    if save:
                        new_duree = new_dur_m + new_dur_s / 60
                        new_allure = new_all_m + new_all_s / 60
                        if new_dist <= 0 or new_duree <= 0:
                            st.error("Distance et durée obligatoires.")
                        else:
                            from datetime import datetime

                            with DBSession(engine) as db_session:
                                s = db_session.get(WorkoutSession, selected.id)
                                s.date = datetime.combine(new_date, new_heure)
                                s.distance_km = round(new_dist, 3)
                                s.duration_minutes = round(new_duree, 2)
                                s.avg_pace_min_km = (
                                    round(new_allure, 2)
                                    if new_allure > 0
                                    else round(new_duree / new_dist, 2)
                                )
                                s.avg_heart_rate = int(new_fc_moy) if new_fc_moy > 0 else None
                                s.max_heart_rate = int(new_fc_max) if new_fc_max > 0 else None
                                s.calories = int(new_cal) if new_cal > 0 else None
                                s.elevation_gain_m = round(new_elev, 1) if new_elev > 0 else None
                                s.notes = new_notes if new_notes else None
                                db_session.commit()
                            st.success(
                                f"✅ Course modifiée — {new_dist} km en "
                                f"{format_duration(new_duree)}"
                            )
                            st.cache_data.clear()
                            st.rerun()

        else:
            with DBSession(engine) as db_session:
                int_sessions = (
                    db_session.query(IntervalSession).order_by(IntervalSession.date.desc()).all()
                )
                db_session.expunge_all()

            if not int_sessions:
                st.info("Aucune séance fractionné.")
            else:
                options_int = {
                    f"{s.date.strftime('%d/%m/%Y')} — {len(s.blocs.get('blocs', []))} blocs": s
                    for s in int_sessions
                }
                choix_int = st.selectbox(
                    "Sélectionne une séance", list(options_int.keys()), key="gest_int_sel"
                )
                selected_int = options_int[choix_int]

                render_interval_card(selected_int, expanded=True)

                action_int = st.radio(
                    "Action",
                    ["✏️ Modifier", "🗑️ Supprimer"],
                    horizontal=True,
                    key="gest_int_action",
                )

                if action_int == "🗑️ Supprimer":
                    st.warning(
                        f"Supprimer la séance du {selected_int.date.strftime('%d/%m/%Y')} ? "
                        "Action irréversible."
                    )
                    if st.button("✅ Confirmer la suppression", type="primary", key="del_int_btn"):
                        with DBSession(engine) as db_session:
                            s = db_session.get(IntervalSession, selected_int.id)
                            db_session.delete(s)
                            db_session.commit()
                        st.success("Séance supprimée.")
                        st.cache_data.clear()
                        st.rerun()

                elif action_int == "✏️ Modifier":
                    edit_key = f"edit_blocs_{selected_int.id}"
                    if edit_key not in st.session_state:
                        st.session_state[edit_key] = list(selected_int.blocs.get("blocs", []))
                        st.session_state[f"edit_adding_{selected_int.id}"] = False

                    col_d, col_h = st.columns(2)
                    with col_d:
                        edit_date = st.date_input(
                            "Date",
                            value=selected_int.date.date(),
                            key=f"edit_int_date_{selected_int.id}",
                        )
                    with col_h:
                        edit_heure = st.time_input(
                            "Heure",
                            value=selected_int.date.time(),
                            key=f"edit_int_heure_{selected_int.id}",
                        )
                    edit_notes = st.text_area(
                        "Notes",
                        value=selected_int.notes or "",
                        key=f"edit_int_notes_{selected_int.id}",
                    )

                    st.markdown("**Blocs de la séance**")
                    if not st.session_state[edit_key]:
                        st.caption("Aucun bloc — ajoute-en un ci-dessous.")
                    else:
                        for i, bloc in enumerate(st.session_state[edit_key]):
                            col_b, col_up, col_dn, col_del = st.columns([6, 1, 1, 1])
                            with col_b:
                                st.info(f"**Bloc {i + 1}** — {render_bloc_summary(bloc)}")
                            with col_up:
                                if st.button(
                                    "⬆️", key=f"up_{selected_int.id}_{i}", disabled=(i == 0)
                                ):
                                    blocs_list = st.session_state[edit_key]
                                    blocs_list[i], blocs_list[i - 1] = (
                                        blocs_list[i - 1],
                                        blocs_list[i],
                                    )
                                    st.rerun()
                            with col_dn:
                                if st.button(
                                    "⬇️",
                                    key=f"dn_{selected_int.id}_{i}",
                                    disabled=(i == len(st.session_state[edit_key]) - 1),
                                ):
                                    blocs_list = st.session_state[edit_key]
                                    blocs_list[i], blocs_list[i + 1] = (
                                        blocs_list[i + 1],
                                        blocs_list[i],
                                    )
                                    st.rerun()
                            with col_del:
                                if st.button("🗑️", key=f"del_{selected_int.id}_{i}"):
                                    st.session_state[edit_key].pop(i)
                                    st.rerun()

                    adding_key = f"edit_adding_{selected_int.id}"
                    if not st.session_state.get(adding_key, False):
                        if st.button("➕ Ajouter un bloc", key=f"add_btn_{selected_int.id}"):
                            st.session_state[adding_key] = True
                            st.rerun()
                    else:
                        st.markdown("---")
                        st.markdown("**➕ Nouveau bloc**")

                        bloc_type = st.selectbox(
                            "Type",
                            ["echauffement", "serie", "serie_double", "recuperation"],
                            format_func=lambda x: {
                                "echauffement": "🔥 Échauffement",
                                "serie": "⚡ Série simple",
                                "serie_double": "⚡ Série double",
                                "recuperation": "🧘 Récupération",
                            }[x],
                            key=f"edit_new_bloc_type_{selected_int.id}",
                        )
                        bloc = {"type": bloc_type}

                        if bloc_type in ["echauffement", "recuperation"]:
                            mode = st.radio(
                                "Définir par",
                                ["Distance (m)", "Durée"],
                                horizontal=True,
                                key=f"edit_{bloc_type}_mode_{selected_int.id}",
                            )
                            if mode == "Distance (m)":
                                d = st.number_input(
                                    "Distance (m)",
                                    min_value=0,
                                    step=100,
                                    value=800,
                                    key=f"edit_{bloc_type}_d_{selected_int.id}",
                                )
                                bloc["distance_m"] = int(d)
                            else:
                                m, s_, cs = render_time_input(
                                    "Durée", f"edit_{bloc_type}_dur_{selected_int.id}"
                                )
                                bloc["duree_sec"] = track_time_to_seconds(m, s_, cs)

                        elif bloc_type == "serie":
                            d = st.number_input(
                                "Distance (m)",
                                min_value=0,
                                step=50,
                                value=400,
                                key=f"edit_serie_d_{selected_int.id}",
                            )
                            nb = st.number_input(
                                "Répétitions",
                                min_value=1,
                                step=1,
                                value=6,
                                key=f"edit_serie_nb_{selected_int.id}",
                            )
                            m_r, s_r, cs_r = render_time_input(
                                "Récupération", f"edit_serie_recup_{selected_int.id}"
                            )
                            bloc["distance_m"] = int(d)
                            bloc["recup_sec"] = track_time_to_seconds(m_r, s_r, cs_r)
                            reps = []
                            for i in range(int(nb)):
                                m_t, s_t, cs_t = render_time_input(
                                    f"Rép. {i + 1}", f"edit_serie_rep_{selected_int.id}_{i}"
                                )
                                reps.append(
                                    {
                                        "num": i + 1,
                                        "temps_sec": track_time_to_seconds(m_t, s_t, cs_t),
                                    }
                                )
                            bloc["repetitions"] = reps

                        elif bloc_type == "serie_double":
                            d = st.number_input(
                                "Distance (m)",
                                min_value=0,
                                step=50,
                                value=200,
                                key=f"edit_sd_d_{selected_int.id}",
                            )
                            nb = st.number_input(
                                "Groupes",
                                min_value=1,
                                step=1,
                                value=3,
                                key=f"edit_sd_nb_{selected_int.id}",
                            )
                            m_p, s_p, cs_p = render_time_input(
                                "Pause intra-groupe", f"edit_sd_pause_{selected_int.id}"
                            )
                            m_r, s_r, cs_r = render_time_input(
                                "Récupération", f"edit_sd_recup_{selected_int.id}"
                            )
                            bloc["distance_m"] = int(d)
                            bloc["pause_intra_sec"] = track_time_to_seconds(m_p, s_p, cs_p)
                            bloc["recup_sec"] = track_time_to_seconds(m_r, s_r, cs_r)
                            groupes = []
                            for g in range(int(nb)):
                                st.markdown(f"*Groupe {g + 1}*")
                                m1, s1, cs1 = render_time_input(
                                    "Effort 1", f"edit_sd_g{g}_1_{selected_int.id}"
                                )
                                m2, s2, cs2 = render_time_input(
                                    "Effort 2", f"edit_sd_g{g}_2_{selected_int.id}"
                                )
                                groupes.append(
                                    [
                                        {
                                            "num": 1,
                                            "temps_sec": track_time_to_seconds(m1, s1, cs1),
                                        },
                                        {
                                            "num": 2,
                                            "temps_sec": track_time_to_seconds(m2, s2, cs2),
                                        },
                                    ]
                                )
                            bloc["groupes"] = groupes

                        col_ok, col_no = st.columns(2)
                        with col_ok:
                            if st.button(
                                "✅ Ajouter",
                                type="primary",
                                key=f"confirm_add_{selected_int.id}",
                            ):
                                st.session_state[edit_key].append(bloc)
                                st.session_state[adding_key] = False
                                st.rerun()
                        with col_no:
                            if st.button("❌ Annuler", key=f"cancel_add_{selected_int.id}"):
                                st.session_state[adding_key] = False
                                st.rerun()

                    st.markdown("---")
                    col_save, col_reset = st.columns(2)
                    with col_save:
                        if st.button(
                            "💾 Enregistrer les modifications",
                            type="primary",
                            key=f"save_int_{selected_int.id}",
                            disabled=not st.session_state[edit_key]
                            or st.session_state.get(adding_key, False),
                        ):
                            from datetime import datetime as dt_cls

                            from sqlalchemy.orm.attributes import flag_modified

                            with DBSession(engine) as db_session:
                                s = db_session.get(IntervalSession, selected_int.id)
                                s.date = dt_cls.combine(edit_date, edit_heure)
                                s.notes = edit_notes if edit_notes else None
                                s.blocs = {"blocs": st.session_state[edit_key]}
                                flag_modified(s, "blocs")
                                db_session.commit()
                            st.success("✅ Séance modifiée.")
                            del st.session_state[edit_key]
                            if adding_key in st.session_state:
                                del st.session_state[adding_key]
                            st.cache_data.clear()
                            st.rerun()
                    with col_reset:
                        if st.button(
                            "🔄 Annuler les modifications",
                            key=f"reset_int_{selected_int.id}",
                        ):
                            del st.session_state[edit_key]
                            if adding_key in st.session_state:
                                del st.session_state[adding_key]
                            st.rerun()
