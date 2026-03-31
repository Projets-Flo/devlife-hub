"""
Page Offres d'emploi — dashboard enrichi avec analyse LLM Mistral.
"""

from collections import Counter

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy.orm import Session

from src.common.database import JobOffer, engine

REGIONS = {
    "Auvergne-Rhône-Alpes": [
        "01",
        "03",
        "07",
        "15",
        "26",
        "38",
        "42",
        "43",
        "63",
        "69",
        "73",
        "74",
    ],
    "Île-de-France": ["75", "77", "78", "91", "92", "93", "94", "95"],
    "Provence-Alpes-Côte d'Azur": ["04", "05", "06", "13", "83", "84"],
    "Occitanie": ["09", "11", "12", "30", "31", "32", "34", "46", "48", "65", "66", "81", "82"],
    "Nouvelle-Aquitaine": ["16", "17", "19", "23", "24", "33", "40", "47", "64", "79", "86", "87"],
    "Bretagne": ["22", "29", "35", "56"],
    "Normandie": ["14", "27", "50", "61", "76"],
    "Hauts-de-France": ["02", "59", "60", "62", "80"],
    "Grand Est": ["08", "10", "51", "52", "54", "55", "57", "67", "68", "88"],
    "Pays de la Loire": ["44", "49", "53", "72", "85"],
    "Centre-Val de Loire": ["18", "28", "36", "37", "41", "45"],
    "Bourgogne-Franche-Comté": ["21", "25", "39", "58", "70", "71", "89", "90"],
}

DEPARTEMENTS = {
    "01": "Ain",
    "02": "Aisne",
    "03": "Allier",
    "04": "Alpes-de-Haute-Provence",
    "05": "Hautes-Alpes",
    "06": "Alpes-Maritimes",
    "07": "Ardèche",
    "08": "Ardennes",
    "09": "Ariège",
    "10": "Aube",
    "11": "Aude",
    "12": "Aveyron",
    "13": "Bouches-du-Rhône",
    "14": "Calvados",
    "15": "Cantal",
    "16": "Charente",
    "17": "Charente-Maritime",
    "18": "Cher",
    "19": "Corrèze",
    "2A": "Corse-du-Sud",
    "2B": "Haute-Corse",
    "21": "Côte-d'Or",
    "22": "Côtes-d'Armor",
    "23": "Creuse",
    "24": "Dordogne",
    "25": "Doubs",
    "26": "Drôme",
    "27": "Eure",
    "28": "Eure-et-Loir",
    "29": "Finistère",
    "30": "Gard",
    "31": "Haute-Garonne",
    "32": "Gers",
    "33": "Gironde",
    "34": "Hérault",
    "35": "Ille-et-Vilaine",
    "36": "Indre",
    "37": "Indre-et-Loire",
    "38": "Isère",
    "39": "Jura",
    "40": "Landes",
    "41": "Loir-et-Cher",
    "42": "Loire",
    "43": "Haute-Loire",
    "44": "Loire-Atlantique",
    "45": "Loiret",
    "46": "Lot",
    "47": "Lot-et-Garonne",
    "48": "Lozère",
    "49": "Maine-et-Loire",
    "50": "Manche",
    "51": "Marne",
    "52": "Haute-Marne",
    "53": "Mayenne",
    "54": "Meurthe-et-Moselle",
    "55": "Meuse",
    "56": "Morbihan",
    "57": "Moselle",
    "58": "Nièvre",
    "59": "Nord",
    "60": "Oise",
    "61": "Orne",
    "62": "Pas-de-Calais",
    "63": "Puy-de-Dôme",
    "64": "Pyrénées-Atlantiques",
    "65": "Hautes-Pyrénées",
    "66": "Pyrénées-Orientales",
    "67": "Bas-Rhin",
    "68": "Haut-Rhin",
    "69": "Rhône",
    "70": "Haute-Saône",
    "71": "Saône-et-Loire",
    "72": "Sarthe",
    "73": "Savoie",
    "74": "Haute-Savoie",
    "75": "Paris",
    "76": "Seine-Maritime",
    "77": "Seine-et-Marne",
    "78": "Yvelines",
    "79": "Deux-Sèvres",
    "80": "Somme",
    "81": "Tarn",
    "82": "Tarn-et-Garonne",
    "83": "Var",
    "84": "Vaucluse",
    "85": "Vendée",
    "86": "Vienne",
    "87": "Haute-Vienne",
    "88": "Vosges",
    "89": "Yonne",
    "90": "Territoire de Belfort",
    "91": "Essonne",
    "92": "Hauts-de-Seine",
    "93": "Seine-Saint-Denis",
    "94": "Val-de-Marne",
    "95": "Val-d'Oise",
}

ZONE_PRIORITAIRE = ["74", "73", "01", "38", "69", "42"]
DEP_TO_REGION = {dep: region for region, deps in REGIONS.items() for dep in deps}


def _extract_dep(location: str) -> str:
    if not location:
        return ""
    parts = location.strip().split(" - ")
    if parts:
        code = parts[0].strip().upper()
        if code in DEPARTEMENTS:
            return code
        if code[:2] in DEPARTEMENTS:
            return code[:2]
    return ""


def _normalize_contract(ct: str) -> str:
    ct_up = ct.upper()
    if "CDI" in ct_up:
        return "CDI"
    if "CDD" in ct_up:
        return "CDD"
    if "ALTERNANCE" in ct_up or "APPRENTISSAGE" in ct_up:
        return "Alternance"
    if "STAGE" in ct_up:
        return "Stage"
    if "INTERIM" in ct_up or "INTÉRIM" in ct_up:
        return "Intérim"
    if "FREELANCE" in ct_up:
        return "Freelance"
    return ct.capitalize()


@st.cache_data(ttl=300, show_spinner="Chargement des offres…")
def load_offers() -> tuple[list, pd.DataFrame]:
    with Session(engine) as session:
        all_offers = (
            session.query(JobOffer)
            .order_by(JobOffer.match_score.desc().nullslast(), JobOffer.scraped_at.desc())
            .all()
        )
        session.expunge_all()

    rows = []
    for o in all_offers:
        tags = o.tags or {}
        llm = tags.get("llm_analysis", {})
        sal = llm.get("salaire_estime", {}) or {}
        dep = _extract_dep(o.location or "")
        rows.append(
            {
                "id": o.id,
                "title": o.title or "",
                "company": o.company or "",
                "location": o.location or "",
                "dep": dep,
                "dep_nom": DEPARTEMENTS.get(dep, ""),
                "region": DEP_TO_REGION.get(dep, "—"),
                "contract_type": _normalize_contract(o.contract_type or ""),
                "match_score": o.match_score or 0,
                "remote": llm.get("remote", "non précisé").lower()
                if llm.get("remote")
                else "non précisé",
                "poste_type": llm.get("poste_type", "—").lower() if llm.get("poste_type") else "—",
                "culture": llm.get("culture_entreprise", "—").lower()
                if llm.get("culture_entreprise")
                else "—",
                "domaine": llm.get("domaine_metier", "—").lower()
                if llm.get("domaine_metier")
                else "—",
                "type_missions": llm.get("type_missions", "—").lower()
                if llm.get("type_missions")
                else "—",
                "sal_min": sal.get("min") or o.salary_min or 0,
                "sal_max": sal.get("max") or o.salary_max or 0,
                "llm_analyzed": tags.get("llm_analyzed", False),
                "stack": llm.get("stack_principale", []),
                "exp_ans": llm.get("experience_requise_ans", 0),
                "probabilite_succes": llm.get("probabilite_succes", 0),
                "urgence": llm.get("urgence_candidature", "—").lower()
                if llm.get("urgence_candidature")
                else "—",
                "url": o.url or "",
            }
        )
    return all_offers, pd.DataFrame(rows)


def render():
    st.title("🔍 Offres d'emploi")

    if st.button("🔄 Actualiser", help="Recharge les données depuis la base"):
        st.cache_data.clear()
        st.rerun()

    all_offers, df = load_offers()

    if not all_offers:
        st.warning("Aucune offre en base.")
        st.code("python -m src.jobs.scrapers.job_collector")
        return

    total = len(df)
    analyzed = int(df["llm_analyzed"].sum())
    pct = round(analyzed / total * 100) if total else 0

    if analyzed < total:
        st.progress(pct / 100, text=f"Analyse IA : {analyzed}/{total} offres ({pct}%)")
        st.caption("`python -m src.jobs.matching.llm_analyzer`")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total offres", total)
    c2.metric("Analysées IA", f"{analyzed}/{total}")
    top = df[df["match_score"] > 0]["match_score"].max()
    c3.metric("Top match", f"{top:.0f}%" if top else "—")
    avg_score = df[df["match_score"] > 0]["match_score"].mean()
    c4.metric("Score moyen", f"{avg_score:.0f}%" if avg_score else "—")
    remote_n = int(df[df["remote"].isin(["full remote", "hybride"])].shape[0])
    c5.metric("Remote/Hybride", remote_n)
    sal_mean = df[df["sal_min"] > 20000]["sal_min"].mean()
    c6.metric("Salaire moy.", f"{sal_mean:,.0f}€" if sal_mean else "—")

    st.divider()

    tab_list, tab_match, tab_stats, tab_market, tab_cmd = st.tabs(
        [
            "📋 Toutes les offres",
            "⭐ Top matches",
            "📊 Statistiques",
            "🗺️ Marché",
            "⚙️ Commandes",
        ]
    )

    with tab_list:
        with st.expander("🎛️ Filtres", expanded=True):
            r1 = st.columns([3, 1, 1])
            search = r1[0].text_input("🔍 Recherche", placeholder="python, NLP, XGBoost…")
            contracts = r1[1].multiselect("📋 Contrat", ["CDI", "CDD", "Intérim"])
            remotes = r1[2].multiselect(
                "🏠 Remote", ["full remote", "hybride", "remote possible", "présentiel"]
            )

            st.markdown("**📍 Localisation**")
            g1, g2, g3, g4 = st.columns([1, 1, 1, 2])
            zone_rapide = g1.selectbox(
                "Zone rapide",
                [
                    "Toute la France",
                    "Ma zone prioritaire",
                    "Île-de-France",
                    "Auvergne-Rhône-Alpes",
                    "Remote uniquement",
                ],
            )
            regions_filter = g2.multiselect(
                "Région", sorted(REGIONS.keys()), placeholder="Choisir…"
            )
            dep_options = [f"{k} — {v}" for k, v in sorted(DEPARTEMENTS.items())]
            deps_filter = g3.multiselect("Département", dep_options, placeholder="ex: 69 — Rhône")
            deps_codes = [d.split(" — ")[0] for d in deps_filter]
            ville_search = g4.text_input(
                "Ville / texte libre", placeholder="Lyon, Annecy, Paris 15…"
            )

            r3 = st.columns([1, 1, 1, 1, 1])
            score_min = r3[0].slider("⭐ Score min", 0, 100, 0, 5)
            proba_min = r3[1].slider("🎯 Proba. min", 0, 100, 0, 5)
            sal_min = r3[2].number_input("💰 Salaire min (€)", 0, step=5000)
            niveaux = r3[3].multiselect("👤 Niveau", ["junior", "confirmé", "senior"])
            cultures = r3[4].multiselect(
                "🏢 Culture",
                [
                    "startup",
                    "scale-up",
                    "grand groupe",
                    "ESN/conseil",
                    "laboratoire/recherche",
                    "PME",
                ],
            )

            r4 = st.columns([1, 1, 2])
            skill_q = r4[0].text_input("🔧 Compétence", placeholder="docker, spark…")
            urgence_filter = r4[1].multiselect("🔥 Urgence", ["haute", "moyenne", "faible"])
            missions_filter = r4[2].multiselect(
                "💼 Missions",
                [
                    "technique/développement",
                    "analyse/reporting",
                    "conseil/client",
                    "recherche/r&d",
                    "mixte",
                ],
            )

        filtered = _apply_filters(
            df,
            search,
            contracts,
            remotes,
            zone_rapide,
            regions_filter,
            deps_codes,
            ville_search,
            score_min,
            proba_min,
            sal_min,
            niveaux,
            cultures,
            skill_q,
            urgence_filter,
            missions_filter,
        )
        filtered_offers = [o for o in all_offers if o.id in set(filtered["id"].tolist())]

        sort_by = st.selectbox(
            "Trier par",
            ["Score ↓", "Probabilité succès ↓", "Salaire estimé ↓", "Date ↓", "Expérience ↑"],
            label_visibility="collapsed",
        )
        filtered_offers = _sort_offers(filtered_offers, filtered, sort_by)
        st.caption(f"**{len(filtered_offers)}** offres affichées")
        for o in filtered_offers[:60]:
            _render_card(o)

    with tab_match:
        st.subheader("🎯 Offres les plus adaptées à ton profil")
        col_s1, col_s2 = st.columns(2)
        threshold = col_s1.slider("Score min", 50, 95, 70, 5)
        proba_threshold = col_s2.slider("Proba. succès min", 0, 95, 0, 5)
        top_df = df[
            (df["match_score"] >= threshold) & (df["probabilite_succes"] >= proba_threshold)
        ].sort_values("match_score", ascending=False)
        top_offers = [o for o in all_offers if o.id in set(top_df["id"].tolist())]

        if not top_offers:
            st.info(f"Aucune offre avec score ≥ {threshold}% et proba ≥ {proba_threshold}%.")
        else:
            st.success(f"**{len(top_offers)}** offres correspondent")
            if analyzed > 0:
                all_stacks = []
                for o in top_offers:
                    all_stacks.extend(
                        (o.tags or {}).get("llm_analysis", {}).get("stack_principale", [])
                    )
                if all_stacks:
                    top_skills = Counter(all_stacks).most_common(8)
                    fig_radar = go.Figure(
                        go.Scatterpolar(
                            r=[s[1] for s in top_skills] + [top_skills[0][1]],
                            theta=[s[0] for s in top_skills] + [top_skills[0][0]],
                            fill="toself",
                            fillcolor="rgba(127,119,221,0.2)",
                            line=dict(color="#7F77DD"),
                        )
                    )
                    fig_radar.update_layout(
                        height=350,
                        margin=dict(l=40, r=40, t=40, b=40),
                        title="Compétences clés dans tes top offres",
                    )
                    st.plotly_chart(fig_radar, use_container_width=True)
            for o in top_offers[:20]:
                _render_card(o, expanded=True)

    with tab_stats:
        if analyzed == 0:
            st.info("Lance l'analyse LLM pour voir les statistiques.")
        else:
            ca, cb = st.columns(2)
            with ca:
                st.subheader("Distribution des scores")
                scores = df[df["match_score"] > 0]["match_score"]
                fig1 = px.histogram(scores, nbins=20, color_discrete_sequence=["#1D9E75"])
                fig1.add_vline(x=70, line_dash="dash", line_color="orange", annotation_text="70%")
                fig1.update_layout(height=280, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
                st.plotly_chart(fig1, use_container_width=True)
                pct_70 = round(len(scores[scores >= 70]) / len(scores) * 100) if len(scores) else 0
                st.caption(f"**{pct_70}%** des offres ont un score ≥ 70%")
            with cb:
                st.subheader("Probabilité de succès")
                probas = df[df["probabilite_succes"] > 0]["probabilite_succes"]
                if not probas.empty:
                    fig1b = px.histogram(probas, nbins=20, color_discrete_sequence=["#7F77DD"])
                    fig1b.update_layout(
                        height=280, margin=dict(l=0, r=0, t=0, b=0), showlegend=False
                    )
                    st.plotly_chart(fig1b, use_container_width=True)

            cc, cd = st.columns(2)
            with cc:
                st.subheader("Niveau requis")
                niv = df[df["poste_type"] != "—"]["poste_type"].value_counts()
                fig2 = px.pie(
                    values=niv.values,
                    names=niv.index,
                    hole=0.4,
                    color_discrete_sequence=["#1D9E75", "#7F77DD", "#D85A30"],
                )
                fig2.update_layout(height=280, margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig2, use_container_width=True)
            with cd:
                st.subheader("Type de missions")
                miss = df[df["type_missions"] != "—"]["type_missions"].value_counts()
                if not miss.empty:
                    fig2b = px.pie(
                        values=miss.values,
                        names=miss.index,
                        hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Set2,
                    )
                    fig2b.update_layout(height=280, margin=dict(l=0, r=0, t=20, b=0))
                    st.plotly_chart(fig2b, use_container_width=True)

            ce, cf = st.columns(2)
            with ce:
                st.subheader("Culture entreprise")
                cult = df[df["culture"] != "—"]["culture"].value_counts().head(8)
                fig3 = px.bar(
                    x=cult.values,
                    y=cult.index,
                    orientation="h",
                    color_discrete_sequence=["#7F77DD"],
                )
                fig3.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig3, use_container_width=True)
            with cf:
                st.subheader("Urgence de candidature")
                urg = df[df["urgence"] != "—"]["urgence"].value_counts()
                if not urg.empty:
                    fig3b = px.pie(
                        values=urg.values,
                        names=urg.index,
                        hole=0.4,
                        color_discrete_map={
                            "haute": "#D85A30",
                            "moyenne": "#EF9F27",
                            "faible": "#1D9E75",
                        },
                    )
                    fig3b.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0))
                    st.plotly_chart(fig3b, use_container_width=True)

            sal_score_df = df[(df["match_score"] > 0) & (df["sal_min"] > 20000)]
            if not sal_score_df.empty:
                st.subheader("Score vs Salaire estimé (taille = probabilité succès)")
                fig5 = px.scatter(
                    sal_score_df,
                    x="match_score",
                    y="sal_min",
                    color="poste_type",
                    size="probabilite_succes",
                    hover_data=["title", "company", "location", "probabilite_succes"],
                    labels={
                        "match_score": "Score %",
                        "sal_min": "Salaire min (€)",
                        "poste_type": "Niveau",
                        "probabilite_succes": "Proba %",
                    },
                    color_discrete_map={
                        "junior": "#1D9E75",
                        "confirmé": "#7F77DD",
                        "senior": "#D85A30",
                    },
                )
                fig5.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig5, use_container_width=True)

    with tab_market:
        st.subheader("🗺️ Intelligence marché — data science en France")
        all_stacks = []
        for _, row in df.iterrows():
            all_stacks.extend(row["stack"])

        if not all_stacks:
            st.info("Lance l'analyse LLM pour voir les tendances marché.")
        else:
            st.subheader("Compétences les plus demandées")
            skill_counts = Counter(all_stacks).most_common(25)
            sk_df = pd.DataFrame(skill_counts, columns=["Compétence", "Offres"])
            TON_PROFIL = {
                "python",
                "r",
                "sql",
                "pandas",
                "scikit-learn",
                "xgboost",
                "pytorch",
                "tensorflow",
                "power bi",
                "tableau",
                "looker",
                "git",
                "pyspark",
                "sas",
                "sklearn",
            }
            sk_df["maîtrisé"] = sk_df["Compétence"].str.lower().isin(TON_PROFIL)
            sk_df["couleur"] = sk_df["maîtrisé"].map({True: "✅ Maîtrisé", False: "📚 À apprendre"})
            fig6 = px.bar(
                sk_df.sort_values("Offres"),
                x="Offres",
                y="Compétence",
                orientation="h",
                color="couleur",
                color_discrete_map={"✅ Maîtrisé": "#1D9E75", "📚 À apprendre": "#7F77DD"},
            )
            fig6.update_layout(height=600, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig6, use_container_width=True)
            maitrisees = sk_df[sk_df["maîtrisé"]]["Offres"].sum()
            total_occ = sk_df["Offres"].sum()
            couverture = round(maitrisees / total_occ * 100) if total_occ else 0
            st.success(
                f"✅ Tu couvres **{couverture}%** des occurrences de compétences dans les offres"
            )

            st.subheader("Offres par région")
            reg_counts = df[df["region"] != "—"]["region"].value_counts().reset_index()
            reg_counts.columns = ["Région", "Offres"]
            fig_reg = px.bar(
                reg_counts.sort_values("Offres"),
                x="Offres",
                y="Région",
                orientation="h",
                color_discrete_sequence=["#1D9E75"],
            )
            fig_reg.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig_reg, use_container_width=True)

            sal_dom = df[(df["sal_min"] > 20000) & (df["domaine"] != "—")]
            if not sal_dom.empty:
                st.subheader("Salaires par domaine")
                fig7 = px.box(
                    sal_dom,
                    x="domaine",
                    y="sal_min",
                    color="domaine",
                    labels={"domaine": "", "sal_min": "Salaire min estimé (€)"},
                )
                fig7.update_layout(height=380, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
                st.plotly_chart(fig7, use_container_width=True)

            sal_reg = df[(df["sal_min"] > 20000) & (df["region"] != "—")]
            if not sal_reg.empty:
                top_regs = sal_reg["region"].value_counts().head(8).index
                fig8 = px.box(
                    sal_reg[sal_reg["region"].isin(top_regs)],
                    x="region",
                    y="sal_min",
                    color="region",
                    labels={"region": "", "sal_min": "Salaire min estimé (€)"},
                )
                fig8.update_layout(
                    height=380,
                    margin=dict(l=0, r=0, t=0, b=0),
                    showlegend=False,
                    title="Salaires par région",
                )
                st.plotly_chart(fig8, use_container_width=True)

            cg, ch = st.columns(2)
            with cg:
                st.subheader("Domaines recrutés")
                dom = df[df["domaine"] != "—"]["domaine"].value_counts()
                fig9 = px.pie(
                    values=dom.values,
                    names=dom.index,
                    hole=0.35,
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                )
                fig9.update_layout(height=320, margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig9, use_container_width=True)
            with ch:
                st.subheader("Expérience requise")
                exp_df = df[df["exp_ans"] > 0]
                if not exp_df.empty:
                    fig10 = px.histogram(
                        exp_df,
                        x="exp_ans",
                        nbins=10,
                        color_discrete_sequence=["#D85A30"],
                        labels={"exp_ans": "Années", "count": "Offres"},
                    )
                    fig10.update_layout(height=320, margin=dict(l=0, r=0, t=0, b=0))
                    st.plotly_chart(fig10, use_container_width=True)

    with tab_cmd:
        st.subheader("⚙️ Commandes utiles")
        st.caption("Copie-colle dans le terminal (.venv activé + Docker lancé)")
        st.markdown("#### 🗄️ Démarrer la base")
        st.code("docker compose up -d db", language="bash")
        st.markdown("#### 📥 Collecter les offres")
        st.code("python -m src.jobs.scrapers.job_collector", language="bash")
        st.markdown("#### 🔄 Pipeline quotidien")
        st.code("python -m src.jobs.flows.daily_pipeline", language="bash")
        st.markdown("#### 🤖 Analyse LLM — nouvelles offres")
        st.code("python -m src.jobs.matching.llm_analyzer", language="bash")
        st.markdown("#### 🤖 Analyse LLM — nombre limité")
        st.code("python -m src.jobs.matching.llm_analyzer --max 50", language="bash")
        st.markdown("#### 🗑️ Réinitialiser analyses LLM")
        st.code(
            '''python -c "
from sqlalchemy.orm import Session
from src.common.database import JobOffer, engine
from sqlalchemy.orm.attributes import flag_modified
with Session(engine) as session:
    for o in session.query(JobOffer).all():
        tags = o.tags or {}
        tags.pop(\'llm_analyzed\', None)
        tags.pop(\'llm_analysis\', None)
        o.tags = tags
        flag_modified(o, \'tags\')
        o.match_score = None
    session.commit()
    print(\'Réinitialisé\')
"''',
            language="bash",
        )
        st.markdown("#### 🗑️ Vider la base")
        st.code(
            '''python -c "
from sqlalchemy.orm import Session
from src.common.database import JobOffer, engine
with Session(engine) as session:
    count = session.query(JobOffer).delete()
    session.commit()
    print(f\'{count} offres supprimées\')
"''',
            language="bash",
        )
        st.divider()
        st.markdown("#### 📋 Démarrage complet")
        st.markdown("""
1. `docker compose up -d db`
2. `python -m src.jobs.scrapers.job_collector`
3. `python -m src.jobs.matching.llm_analyzer`
4. Cliquer 🔄
        """)
        st.markdown("#### 🔁 Mise à jour quotidienne")
        st.markdown("""
1. `docker compose up -d db`
2. `python -m src.jobs.flows.daily_pipeline`
3. Cliquer 🔄
        """)


def _apply_filters(
    df,
    search,
    contracts,
    remotes,
    zone_rapide,
    regions_filter,
    deps_codes,
    ville_search,
    score_min,
    proba_min,
    sal_min,
    niveaux,
    cultures,
    skill_q,
    urgence_filter,
    missions_filter,
):
    filtered_ids = set(df["id"].tolist())

    if search:
        terms = search.lower().split()
        mask = pd.Series([True] * len(df), index=df.index)
        for t in terms:
            mask &= df["title"].str.lower().str.contains(t, na=False) | df[
                "company"
            ].str.lower().str.contains(t, na=False)
        filtered_ids &= set(df[mask]["id"].tolist())

    if contracts:
        mask = df["contract_type"].str.contains("|".join(contracts), case=False, na=False)
        filtered_ids &= set(df[mask]["id"].tolist())

    if remotes:
        filtered_ids &= set(df[df["remote"].isin(remotes)]["id"].tolist())

    if zone_rapide == "Ma zone prioritaire":
        mask = df["dep"].isin(ZONE_PRIORITAIRE) | df["remote"].isin(["full remote"])
        filtered_ids &= set(df[mask]["id"].tolist())
    elif zone_rapide == "Île-de-France":
        filtered_ids &= set(df[df["dep"].isin(REGIONS["Île-de-France"])]["id"].tolist())
    elif zone_rapide == "Auvergne-Rhône-Alpes":
        filtered_ids &= set(df[df["dep"].isin(REGIONS["Auvergne-Rhône-Alpes"])]["id"].tolist())
    elif zone_rapide == "Remote uniquement":
        filtered_ids &= set(df[df["remote"] == "full remote"]["id"].tolist())

    if regions_filter:
        dep_in_regions = set()
        for r in regions_filter:
            dep_in_regions.update(REGIONS.get(r, []))
        filtered_ids &= set(df[df["dep"].isin(dep_in_regions)]["id"].tolist())

    if deps_codes:
        filtered_ids &= set(df[df["dep"].isin(deps_codes)]["id"].tolist())

    if ville_search:
        mask = df["location"].str.lower().str.contains(ville_search.lower(), na=False)
        filtered_ids &= set(df[mask]["id"].tolist())

    if score_min > 0:
        filtered_ids &= set(df[df["match_score"] >= score_min]["id"].tolist())
    if proba_min > 0:
        filtered_ids &= set(df[df["probabilite_succes"] >= proba_min]["id"].tolist())
    if sal_min > 0:
        filtered_ids &= set(df[df["sal_min"] >= sal_min]["id"].tolist())
    if niveaux:
        filtered_ids &= set(df[df["poste_type"].isin(niveaux)]["id"].tolist())
    if cultures:
        filtered_ids &= set(df[df["culture"].isin(cultures)]["id"].tolist())
    if skill_q:
        s = skill_q.lower()
        mask = df["stack"].apply(lambda x: any(s in t.lower() for t in x) if x else False)
        filtered_ids &= set(df[mask]["id"].tolist())
    if urgence_filter:
        filtered_ids &= set(df[df["urgence"].isin(urgence_filter)]["id"].tolist())
    if missions_filter:
        filtered_ids &= set(df[df["type_missions"].isin(missions_filter)]["id"].tolist())

    return df[df["id"].isin(filtered_ids)]


def _sort_offers(offers, df, sort_by):
    if sort_by == "Score ↓":
        return sorted(offers, key=lambda o: o.match_score or 0, reverse=True)
    if sort_by == "Probabilité succès ↓":
        id_to_p = dict(zip(df["id"], df["probabilite_succes"], strict=False))
        return sorted(offers, key=lambda o: id_to_p.get(o.id, 0), reverse=True)
    if sort_by == "Salaire estimé ↓":
        id_to_sal = dict(zip(df["id"], df["sal_min"], strict=False))
        return sorted(offers, key=lambda o: id_to_sal.get(o.id, 0), reverse=True)
    if sort_by == "Expérience ↑":
        id_to_exp = dict(zip(df["id"], df["exp_ans"], strict=False))
        return sorted(offers, key=lambda o: id_to_exp.get(o.id, 99))
    return offers


def _render_card(offer, expanded: bool = False):
    tags = offer.tags or {}
    llm = tags.get("llm_analysis", {})
    score = offer.match_score or 0
    sal = llm.get("salaire_estime", {}) or {}
    stack = llm.get("stack_principale", [])
    poste_type = llm.get("poste_type", "—")
    culture = llm.get("culture_entreprise", "—")
    remote = llm.get("remote", "—")
    proba = llm.get("probabilite_succes", 0)
    urgence = llm.get("urgence_candidature", "")
    type_missions = llm.get("type_missions", "")

    score_badge = (
        f"🟢 {score:.0f}%"
        if score >= 70
        else f"🟡 {score:.0f}%"
        if score >= 50
        else f"🔴 {score:.0f}%"
        if score > 0
        else "⚪ —"
    )
    niveau_icon = {"junior": "🌱", "confirmé": "⚡", "senior": "🏆"}.get(poste_type, "❓")
    urgence_icon = {"haute": "🔥", "moyenne": "⏳", "faible": "🧊"}.get(urgence, "")

    sal_str = "—"
    if sal.get("min") and sal.get("max"):
        sal_str = f"~{sal['min']:,.0f}€–{sal['max']:,.0f}€"
    elif sal.get("min"):
        sal_str = f"~{sal['min']:,.0f}€+"
    sal_base = "📊" if sal.get("base") == "estimé" else "📄"

    dep = _extract_dep(offer.location or "")
    dep_label = f"({DEPARTEMENTS.get(dep,'')})" if dep else ""

    header = (
        f"{score_badge} {niveau_icon} {urgence_icon} **{offer.title}**"
        f"  —  {offer.company}"
        f"  ·  📍 {offer.location} {dep_label}"
        f"  ·  {sal_base} {sal_str}"
    )

    with st.expander(header, expanded=expanded):
        col_main, col_side = st.columns([3, 1])

        with col_side:
            st.markdown("**Fiche poste**")
            st.write(f"📋 {_normalize_contract(offer.contract_type or '')}")
            st.write(f"👤 {poste_type}")
            st.write(f"🏢 {culture}")
            st.write(f"🏠 {remote}")
            if type_missions:
                st.write(f"💼 {type_missions}")
            if urgence:
                icon = {"haute": "🔥", "moyenne": "⏳", "faible": "🧊"}.get(urgence, "")
                st.write(f"{icon} Urgence : **{urgence}**")
                if llm.get("urgence_note"):
                    st.caption(llm["urgence_note"])
            if sal.get("note"):
                st.caption(f"💡 {sal['note']}")
            st.divider()
            if offer.url:
                st.link_button("Postuler ↗", offer.url)

        with col_main:
            if llm.get("resume"):
                st.info(f"**Résumé :** {llm['resume']}")

            if stack:
                st.markdown("**Stack :** " + "  ".join(f"`{s}`" for s in stack))

            if score > 0 or proba > 0:
                sc1, sc2 = st.columns(2)
                with sc1:
                    if score > 0:
                        col = "green" if score >= 70 else "orange" if score >= 50 else "red"
                        st.markdown(f"**Adéquation :** :{col}[**{score:.0f}%**]")
                        if llm.get("score_justification"):
                            st.caption(llm["score_justification"])
                with sc2:
                    if proba > 0:
                        col_p = "green" if proba >= 60 else "orange" if proba >= 40 else "red"
                        st.markdown(f"**Proba. succès :** :{col_p}[**{proba:.0f}%**]")
                        if llm.get("probabilite_succes_note"):
                            st.caption(llm["probabilite_succes_note"])

            pf = llm.get("points_forts_candidature", [])
            faib = llm.get("faiblesses_candidature", [])
            if pf or faib:
                c1, c2 = st.columns(2)
                with c1:
                    if pf:
                        st.markdown("**✅ Tes atouts**")
                        for p in pf[:4]:
                            st.markdown(f"- {p}")
                with c2:
                    if faib:
                        st.markdown("**⚠️ Tes faiblesses**")
                        for f in faib[:4]:
                            st.markdown(f"- {f}")

            pm = llm.get("competences_manquantes", [])
            if pm:
                st.markdown("**🔧 Manquantes :** " + "  ".join(f"`{m}`" for m in pm[:6]))

            if llm.get("conseil_candidature"):
                st.success(f"💡 **Conseil :** {llm['conseil_candidature']}")

            comp_req = llm.get("competences_requises", {})
            indis = comp_req.get("indispensables", [])
            souh = comp_req.get("souhaitees", [])
            if indis or souh:
                with st.expander("📋 Compétences détaillées"):
                    if indis:
                        st.markdown(
                            "**Indispensables :** " + "  ".join(f"`{c}`" for c in indis[:10])
                        )
                    if souh:
                        st.markdown("**Souhaitées :** " + "  ".join(f"`{c}`" for c in souh[:10]))

            with st.expander("📄 Description complète"):
                st.write(offer.description or "—")
