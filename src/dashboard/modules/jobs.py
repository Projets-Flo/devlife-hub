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
        rows.append(
            {
                "id": o.id,
                "title": o.title or "",
                "company": o.company or "",
                "location": o.location or "",
                "contract_type": _normalize_contract(o.contract_type or ""),
                "match_score": o.match_score or 0,
                "remote": llm.get("remote", "non précisé"),
                "poste_type": llm.get("poste_type", "—"),
                "culture": llm.get("culture_entreprise", "—"),
                "domaine": llm.get("domaine_metier", "—"),
                "sal_min": sal.get("min") or o.salary_min or 0,
                "sal_max": sal.get("max") or o.salary_max or 0,
                "llm_analyzed": tags.get("llm_analyzed", False),
                "stack": llm.get("stack_principale", []),
                "exp_ans": llm.get("experience_requise_ans", 0),
                "url": o.url or "",
            }
        )
    return all_offers, pd.DataFrame(rows)


def render():
    st.title("🔍 Offres d'emploi")

    # Bouton refresh cache
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

    # ── Barre de progression analyse ──────────────────────────────────────────
    if analyzed < total:
        st.progress(pct / 100, text=f"Analyse IA en cours : {analyzed}/{total} offres ({pct}%)")
        st.caption("Lance `python -m src.jobs.matching.llm_analyzer` pour analyser le reste.")

    # ── Métriques ─────────────────────────────────────────────────────────────
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
    c6.metric("Salaire moy. estimé", f"{sal_mean:,.0f}€" if sal_mean else "—")

    st.divider()

    # ── Tabs principaux ───────────────────────────────────────────────────────
    tab_list, tab_match, tab_stats, tab_market, tab_cmd = st.tabs(
        [
            "📋 Toutes les offres",
            "⭐ Top matches",
            "📊 Statistiques",
            "🗺️ Marché",
            "⚙️ Commandes",
        ]
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 1 — LISTE COMPLÈTE
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_list:
        with st.expander("🎛️ Filtres", expanded=True):
            r1 = st.columns([2, 2, 1, 1])
            search = r1[0].text_input("🔍 Recherche", placeholder="python, NLP, XGBoost…")
            loc = r1[1].text_input("📍 Localisation", placeholder="Paris, Lyon, Remote…")
            contracts = r1[2].multiselect(
                "📋 Contrat", ["CDI", "CDD", "Stage", "Alternance", "Intérim"]
            )
            remotes = r1[3].multiselect(
                "🏠 Remote", ["full remote", "hybride", "remote possible", "présentiel"]
            )

            r2 = st.columns([1, 1, 1, 1, 1])
            score_min = r2[0].slider("⭐ Score min", 0, 100, 0, 5)
            sal_min = r2[1].number_input("💰 Salaire min (€)", 0, step=5000)
            niveaux = r2[2].multiselect("👤 Niveau", ["junior", "confirmé", "senior"])
            cultures = r2[3].multiselect(
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
            skill_q = r2[4].text_input("🔧 Compétence", placeholder="docker, spark…")

        filtered = _apply_filters(
            df, search, loc, contracts, remotes, score_min, sal_min, niveaux, cultures, skill_q
        )
        filtered_offers = [o for o in all_offers if o.id in set(filtered["id"].tolist())]

        sort_by = st.selectbox(
            "Trier par",
            ["Score ↓", "Salaire estimé ↓", "Date ↓", "Expérience ↑"],
            label_visibility="collapsed",
        )
        filtered_offers = _sort_offers(filtered_offers, filtered, sort_by)

        st.caption(f"**{len(filtered_offers)}** offres affichées")
        for o in filtered_offers[:60]:
            _render_card(o)

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 2 — TOP MATCHES
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_match:
        st.subheader("🎯 Offres les plus adaptées à ton profil")

        threshold = st.slider("Seuil de matching", 50, 95, 70, 5)
        top_df = df[df["match_score"] >= threshold].sort_values("match_score", ascending=False)
        top_offers = [o for o in all_offers if o.id in set(top_df["id"].tolist())]

        if not top_offers:
            st.info(
                f"Aucune offre avec un score ≥ {threshold}%. Baisse le seuil ou lance l'analyse LLM."
            )
        else:
            st.success(f"**{len(top_offers)}** offres avec un score ≥ {threshold}%")

            # Radar chart — profil de compétences demandées dans les top offres
            if analyzed > 0:
                all_stacks = []
                for o in top_offers:
                    all_stacks.extend(
                        (o.tags or {}).get("llm_analysis", {}).get("stack_principale", [])
                    )
                if all_stacks:
                    top_skills = Counter(all_stacks).most_common(8)
                    skills_names = [s[0] for s in top_skills]
                    skills_vals = [s[1] for s in top_skills]

                    fig_radar = go.Figure(
                        go.Scatterpolar(
                            r=skills_vals + [skills_vals[0]],
                            theta=skills_names + [skills_names[0]],
                            fill="toself",
                            fillcolor="rgba(127, 119, 221, 0.2)",
                            line=dict(color="#7F77DD"),
                        )
                    )
                    fig_radar.update_layout(
                        polar=dict(radialaxis=dict(visible=True)),
                        height=350,
                        margin=dict(l=40, r=40, t=40, b=40),
                        title="Compétences clés dans tes top offres",
                    )
                    st.plotly_chart(fig_radar, use_container_width=True)

            for o in top_offers[:20]:
                _render_card(o, expanded=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 3 — STATISTIQUES
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_stats:
        if analyzed == 0:
            st.info("Lance l'analyse LLM pour voir les statistiques.")
        else:
            ca, cb = st.columns(2)

            with ca:
                st.subheader("Distribution des scores")
                scores = df[df["match_score"] > 0]["match_score"]
                fig1 = px.histogram(
                    scores,
                    nbins=20,
                    labels={"value": "Score %", "count": "Offres"},
                    color_discrete_sequence=["#1D9E75"],
                )
                fig1.add_vline(
                    x=70, line_dash="dash", line_color="orange", annotation_text="Seuil 70%"
                )
                fig1.update_layout(height=280, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
                st.plotly_chart(fig1, use_container_width=True)
                pct_70 = round(len(scores[scores >= 70]) / len(scores) * 100) if len(scores) else 0
                st.caption(f"**{pct_70}%** des offres analysées ont un score ≥ 70%")

            with cb:
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

            cc, cd = st.columns(2)

            with cc:
                st.subheader("Culture entreprise")
                cult = df[df["culture"] != "—"]["culture"].value_counts().head(8)
                fig3 = px.bar(
                    x=cult.values,
                    y=cult.index,
                    orientation="h",
                    color_discrete_sequence=["#7F77DD"],
                    labels={"x": "Offres", "y": ""},
                )
                fig3.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig3, use_container_width=True)

            with cd:
                st.subheader("Type de remote")
                rem = df[df["remote"] != "non précisé"]["remote"].value_counts()
                fig4 = px.pie(
                    values=rem.values,
                    names=rem.index,
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                fig4.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig4, use_container_width=True)

            # Scatter score vs salaire
            sal_score_df = df[(df["match_score"] > 0) & (df["sal_min"] > 20000)]
            if not sal_score_df.empty:
                st.subheader("Score matching vs Salaire estimé")
                fig5 = px.scatter(
                    sal_score_df,
                    x="match_score",
                    y="sal_min",
                    color="poste_type",
                    hover_data=["title", "company", "location"],
                    labels={
                        "match_score": "Score %",
                        "sal_min": "Salaire min estimé (€)",
                        "poste_type": "Niveau",
                    },
                    color_discrete_map={
                        "junior": "#1D9E75",
                        "confirmé": "#7F77DD",
                        "senior": "#D85A30",
                    },
                )
                fig5.update_layout(height=350, margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig5, use_container_width=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 4 — MARCHÉ
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_market:
        st.subheader("🗺️ Intelligence marché — data science en France")

        all_stacks = []
        for _, row in df.iterrows():
            all_stacks.extend(row["stack"])

        if not all_stacks:
            st.info("Lance l'analyse LLM pour voir les tendances marché.")
        else:
            # Top compétences
            st.subheader("Compétences les plus demandées")
            skill_counts = Counter(all_stacks).most_common(25)
            sk_df = pd.DataFrame(skill_counts, columns=["Compétence", "Offres"])

            # Colorie les compétences que tu as déjà
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
                labels={"couleur": ""},
            )
            fig6.update_layout(height=600, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig6, use_container_width=True)

            maitrisees = sk_df[sk_df["maîtrisé"]]["Offres"].sum()
            total_occ = sk_df["Offres"].sum()
            couverture = round(maitrisees / total_occ * 100) if total_occ else 0
            st.success(
                f"✅ Tu maîtrises des compétences représentant **{couverture}%** "
                f"des occurrences dans les offres"
            )

            # Salaires par domaine
            sal_dom = df[(df["sal_min"] > 20000) & (df["domaine"] != "—")]
            if not sal_dom.empty:
                st.subheader("Fourchettes salariales par domaine")
                fig7 = px.box(
                    sal_dom,
                    x="domaine",
                    y="sal_min",
                    color="domaine",
                    labels={"domaine": "", "sal_min": "Salaire min estimé (€)"},
                )
                fig7.update_layout(height=380, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
                st.plotly_chart(fig7, use_container_width=True)

            # Salaires par localisation
            sal_loc = df[(df["sal_min"] > 20000)]
            if not sal_loc.empty:
                # Extrait la région (premier mot de la localisation)
                sal_loc = sal_loc.copy()
                sal_loc["region"] = sal_loc["location"].str.split(" ").str[0].str.split("(").str[0]
                top_regions = sal_loc["region"].value_counts().head(10).index
                sal_loc_top = sal_loc[sal_loc["region"].isin(top_regions)]

                st.subheader("Salaires par localisation (top 10 villes)")
                fig8 = px.box(
                    sal_loc_top,
                    x="region",
                    y="sal_min",
                    color="region",
                    labels={"region": "", "sal_min": "Salaire min estimé (€)"},
                )
                fig8.update_layout(height=350, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
                st.plotly_chart(fig8, use_container_width=True)

            # Domaines les plus présents
            ce, cf = st.columns(2)
            with ce:
                st.subheader("Domaines les plus recrutés")
                dom = df[df["domaine"] != "—"]["domaine"].value_counts()
                fig9 = px.pie(
                    values=dom.values,
                    names=dom.index,
                    hole=0.35,
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                )
                fig9.update_layout(height=320, margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig9, use_container_width=True)

            with cf:
                st.subheader("Expérience requise (années)")
                exp_df = df[df["exp_ans"] > 0]
                if not exp_df.empty:
                    fig10 = px.histogram(
                        exp_df,
                        x="exp_ans",
                        nbins=10,
                        color_discrete_sequence=["#D85A30"],
                        labels={"exp_ans": "Années d'expérience", "count": "Offres"},
                    )
                    fig10.update_layout(height=320, margin=dict(l=0, r=0, t=0, b=0))
                    st.plotly_chart(fig10, use_container_width=True)

    # Tab 5 — COMMANDES ──────────────────────────────────────────────────────────────

    with tab_cmd:
        st.subheader("⚙️ Commandes utiles")
        st.caption(
            "Copie-colle ces commandes dans ton terminal (avec .venv activé et Docker lancé)"
        )

        st.markdown("#### 🗄️ Base de données")
        st.code("docker compose up -d db", language="bash")

        st.markdown("#### 📥 Collecte des offres")
        st.code("python -m src.jobs.scrapers.job_collector", language="bash")

        st.markdown("#### 🔄 Pipeline complet (collecte + analyse nouvelles offres)")
        st.code("python -m src.jobs.flows.daily_pipeline", language="bash")

        st.markdown("#### 🤖 Analyse LLM (nouvelles offres uniquement)")
        st.code("python -m src.jobs.matching.llm_analyzer", language="bash")

        st.markdown("#### 🤖 Analyse LLM (nombre limité)")
        st.code("python -m src.jobs.matching.llm_analyzer --max 50", language="bash")

        st.markdown("#### 🗑️ Réinitialiser toutes les analyses LLM")
        st.code(
            """python -c "
    from sqlalchemy.orm import Session
    from src.common.database import JobOffer, engine
    from sqlalchemy.orm.attributes import flag_modified

    with Session(engine) as session:
        for o in session.query(JobOffer).all():
            tags = o.tags or {}
            tags.pop('llm_analyzed', None)
            tags.pop('llm_analysis', None)
            o.tags = tags
            flag_modified(o, 'tags')
            o.match_score = None
        session.commit()
        print('Réinitialisé')
    " """,
            language="bash",
        )

        st.markdown("#### 🗑️ Vider complètement la base d'offres")
        st.code(
            """python -c "
    from sqlalchemy.orm import Session
    from src.common.database import JobOffer, engine

    with Session(engine) as session:
        count = session.query(JobOffer).delete()
        session.commit()
        print(f'{count} offres supprimées')
    " """,
            language="bash",
        )

        st.markdown("#### 🧹 Supprimer alternances/stages de la base")
        st.code(
            """python -c "
    from sqlalchemy.orm import Session
    from src.common.database import JobOffer, engine

    excluded = ['alternance', 'apprentissage', 'stage', 'stagiaire']
    with Session(engine) as session:
        deleted = 0
        for o in session.query(JobOffer).all():
            if any(kw in (o.title or '').lower() for kw in excluded):
                session.delete(o)
                deleted += 1
        session.commit()
        print(f'{deleted} offres supprimées')
    " """,
            language="bash",
        )

        st.divider()
        st.markdown("#### 📋 Ordre recommandé pour un démarrage complet")
        st.markdown("""
        1. `docker compose up -d db` — démarre PostgreSQL
        2. `python -m src.jobs.scrapers.job_collector` — collecte les offres
        3. *(optionnel)* supprimer alternances/stages
        4. `python -m src.jobs.matching.llm_analyzer` — analyse LLM
        5. Rafraîchir le dashboard → bouton 🔄 en haut
        """)

        st.markdown("#### 🔁 Ordre recommandé pour une mise à jour quotidienne")
        st.markdown("""
        1. `docker compose up -d db`
        2. `python -m src.jobs.flows.daily_pipeline` — collecte + analyse en une seule commande
        3. Rafraîchir le dashboard → bouton 🔄 en haut
        """)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _apply_filters(
    df, search, loc, contracts, remotes, score_min, sal_min, niveaux, cultures, skill_q
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

    if loc:
        mask = df["location"].str.lower().str.contains(loc.lower(), na=False)
        filtered_ids &= set(df[mask]["id"].tolist())

    if contracts:
        mask = df["contract_type"].str.contains("|".join(contracts), case=False, na=False)
        filtered_ids &= set(df[mask]["id"].tolist())

    if remotes:
        filtered_ids &= set(df[df["remote"].isin(remotes)]["id"].tolist())

    if score_min > 0:
        filtered_ids &= set(df[df["match_score"] >= score_min]["id"].tolist())

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

    return df[df["id"].isin(filtered_ids)]


def _sort_offers(offers, df, sort_by):
    if sort_by == "Score ↓":
        return sorted(offers, key=lambda o: o.match_score or 0, reverse=True)
    if sort_by == "Salaire estimé ↓":
        id_to_sal = dict(zip(df["id"], df["sal_min"], strict=False))
        return sorted(offers, key=lambda o: id_to_sal.get(o.id, 0), reverse=True)
    if sort_by == "Expérience ↑":
        id_to_exp = dict(zip(df["id"], df["exp_ans"], strict=False))
        return sorted(offers, key=lambda o: id_to_exp.get(o.id, 99))
    return offers  # Date ↓ déjà trié par défaut


def _render_card(offer, expanded: bool = False):
    tags = offer.tags or {}
    llm = tags.get("llm_analysis", {})
    score = offer.match_score or 0
    sal = llm.get("salaire_estime", {}) or {}
    stack = llm.get("stack_principale", [])
    poste_type = llm.get("poste_type", "—")
    culture = llm.get("culture_entreprise", "—")
    remote = llm.get("remote", "—")

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

    sal_str = "—"
    if sal.get("min") and sal.get("max"):
        sal_str = f"~{sal['min']:,.0f}€ – {sal['max']:,.0f}€"
    elif sal.get("min"):
        sal_str = f"~{sal['min']:,.0f}€+"
    sal_base = "📊" if sal.get("base") == "estimé" else "📄"

    header = (
        f"{score_badge} {niveau_icon} **{offer.title}**"
        f"  —  {offer.company}  ·  📍 {offer.location}"
        f"  ·  {sal_base} {sal_str}"
    )

    with st.expander(header, expanded=expanded):
        col_main, col_side = st.columns([3, 1])

        with col_side:
            st.markdown("**Fiche poste**")
            st.write(f"📋 {_normalize_contract(offer.contract_type or '')}")
            st.write(f"👤 Niveau : {poste_type}")
            st.write(f"🏢 {culture}")
            st.write(f"🏠 {remote}")
            if sal.get("note"):
                st.caption(f"💡 {sal['note']}")
            st.divider()
            if offer.url:
                st.link_button("Postuler ↗", offer.url)

        with col_main:
            resume = llm.get("resume")
            if resume:
                st.info(f"**Résumé :** {resume}")

            if stack:
                st.markdown("**Stack :** " + "  ".join(f"`{s}`" for s in stack))

            if score > 0:
                justif = llm.get("score_justification", "")
                col = "green" if score >= 70 else "orange" if score >= 50 else "red"
                st.markdown(
                    f"**Adéquation :** :{col}[**{score:.0f}%**]"
                    + (f"  —  {justif}" if justif else "")
                )

            pf = llm.get("points_forts_candidature", [])
            pm = llm.get("competences_manquantes", [])
            if pf or pm:
                c1, c2 = st.columns(2)
                with c1:
                    if pf:
                        st.markdown("**✅ Tes atouts**")
                        for p in pf[:4]:
                            st.markdown(f"- {p}")
                with c2:
                    if pm:
                        st.markdown("**⚠️ À développer**")
                        for m in pm[:4]:
                            st.markdown(f"- {m}")

            conseil = llm.get("conseil_candidature")
            if conseil:
                st.success(f"💡 **Conseil :** {conseil}")

            comp_req = llm.get("competences_requises", {})
            indis = comp_req.get("indispensables", [])
            souh = comp_req.get("souhaitees", [])
            if indis or souh:
                with st.expander("📋 Compétences requises détaillées"):
                    if indis:
                        st.markdown(
                            "**Indispensables :** " + "  ".join(f"`{c}`" for c in indis[:10])
                        )
                    if souh:
                        st.markdown("**Souhaitées :** " + "  ".join(f"`{c}`" for c in souh[:10]))

            with st.expander("📄 Description complète"):
                st.write(offer.description or "—")


def _normalize_contract(ct: str) -> str:
    ct = ct.upper()
    if "CDI" in ct:
        return "CDI"
    if "CDD" in ct:
        return "CDD"
    if "ALTERNANCE" in ct or "APPRENTISSAGE" in ct:
        return "Alternance"
    if "STAGE" in ct:
        return "Stage"
    if "INTERIM" in ct or "INTÉRIM" in ct:
        return "Intérim"
    if "FREELANCE" in ct or "INDÉPENDANT" in ct:
        return "Freelance"
    return ct.capitalize()
