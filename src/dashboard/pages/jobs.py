"""
Page Offres d'emploi — dashboard enrichi avec filtres avancés et analyse LLM.
"""

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy.orm import Session

from src.common.database import JobOffer, engine


def render():
    st.title("🔍 Offres d'emploi")

    with Session(engine) as session:
        all_offers = (
            session.query(JobOffer)
            .order_by(JobOffer.match_score.desc().nullslast(), JobOffer.scraped_at.desc())
            .all()
        )
        session.expunge_all()

    if not all_offers:
        st.warning("Aucune offre en base. Lance le collecteur d'abord.")
        st.code("python -m src.jobs.scrapers.job_collector")
        return

    rows = []
    for o in all_offers:
        tags = o.tags or {}
        llm = tags.get("llm_analysis", {})
        rows.append(
            {
                "id": o.id,
                "title": o.title or "",
                "company": o.company or "",
                "location": o.location or "",
                "contract_type": o.contract_type or "",
                "match_score": o.match_score or 0,
                "remote": llm.get("remote", tags.get("remote_type", "non précisé")),
                "poste_type": llm.get("poste_type", "—"),
                "culture": llm.get("culture_entreprise", "—"),
                "domaine": llm.get("domaine_metier", "—"),
                "sal_min": llm.get("salaire_estime", {}).get("min") or o.salary_min or 0,
                "sal_max": llm.get("salaire_estime", {}).get("max") or o.salary_max or 0,
                "llm_analyzed": tags.get("llm_analyzed", False),
                "stack": llm.get("stack_principale", []),
            }
        )
    df = pd.DataFrame(rows)

    total = len(df)
    analyzed = int(df["llm_analyzed"].sum())

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total offres", total)
    c2.metric("Analysées par IA", f"{analyzed}/{total}")
    top_match = df[df["match_score"] > 0]["match_score"].max() if not df.empty else 0
    c3.metric("Meilleur match", f"{top_match:.0f}%" if top_match else "—")
    remote_count = int(df[df["remote"].isin(["full remote", "hybride"])].shape[0])
    c4.metric("Remote / Hybride", remote_count)
    sal_mean = df[df["sal_min"] > 0]["sal_min"].mean()
    c5.metric("Salaire moyen estimé", f"{sal_mean:,.0f}€" if sal_mean else "—")

    st.divider()

    with st.expander("🎛️ Filtres avancés", expanded=True):
        r1 = st.columns([2, 2, 1, 1])
        with r1[0]:
            search = st.text_input("🔍 Recherche", placeholder="python, NLP, XGBoost...")
        with r1[1]:
            loc_filter = st.text_input("📍 Localisation", placeholder="Paris, Lyon...")
        with r1[2]:
            contract_filter = st.multiselect("📋 Contrat", ["CDI", "CDD", "Stage", "Alternance"])
        with r1[3]:
            remote_filter = st.multiselect(
                "🏠 Remote", ["full remote", "hybride", "remote possible", "présentiel"]
            )

        r2 = st.columns([1, 1, 1, 1])
        with r2[0]:
            score_min = st.slider("⭐ Score min", 0, 100, 0, step=5)
        with r2[1]:
            sal_min_filter = st.number_input("💰 Salaire min (€)", 0, step=5000)
        with r2[2]:
            niveau_filter = st.multiselect("👤 Niveau", ["junior", "confirmé", "senior"])
        with r2[3]:
            culture_filter = st.multiselect(
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

        r3 = st.columns([2, 1])
        with r3[0]:
            skill_filter = st.text_input("🔧 Compétence", placeholder="python, docker...")
        with r3[1]:
            llm_only = st.checkbox("Analysées par IA uniquement")

    # Application filtres
    filtered_ids = set(df["id"].tolist())

    if search:
        terms = search.lower().split()
        mask = pd.Series([True] * len(df), index=df.index)
        for t in terms:
            mask &= df["title"].str.lower().str.contains(t, na=False) | df[
                "company"
            ].str.lower().str.contains(t, na=False)
        filtered_ids &= set(df[mask]["id"].tolist())

    if loc_filter:
        mask = df["location"].str.lower().str.contains(loc_filter.lower(), na=False)
        filtered_ids &= set(df[mask]["id"].tolist())

    if contract_filter:
        mask = df["contract_type"].str.contains("|".join(contract_filter), case=False, na=False)
        filtered_ids &= set(df[mask]["id"].tolist())

    if remote_filter:
        filtered_ids &= set(df[df["remote"].isin(remote_filter)]["id"].tolist())

    if score_min > 0:
        filtered_ids &= set(df[df["match_score"] >= score_min]["id"].tolist())

    if sal_min_filter > 0:
        filtered_ids &= set(df[df["sal_min"] >= sal_min_filter]["id"].tolist())

    if niveau_filter:
        filtered_ids &= set(df[df["poste_type"].isin(niveau_filter)]["id"].tolist())

    if culture_filter:
        filtered_ids &= set(df[df["culture"].isin(culture_filter)]["id"].tolist())

    if llm_only:
        filtered_ids &= set(df[df["llm_analyzed"]]["id"].tolist())

    if skill_filter:
        s = skill_filter.lower()
        mask = df["stack"].apply(lambda x: any(s in t.lower() for t in x) if x else False)
        filtered_ids &= set(df[mask]["id"].tolist())

    filtered_offers = [o for o in all_offers if o.id in filtered_ids]
    filtered_df = df[df["id"].isin(filtered_ids)]

    st.caption(f"**{len(filtered_offers)}** offres · {analyzed} analysées par IA")

    tab1, tab2, tab3 = st.tabs(["📋 Liste", "📊 Statistiques", "🗺️ Marché"])

    with tab1:
        sort_by = st.selectbox(
            "Trier par",
            ["Score matching ↓", "Salaire estimé ↓", "Date ↓"],
            label_visibility="collapsed",
        )
        if sort_by == "Score matching ↓":
            filtered_offers = sorted(
                filtered_offers, key=lambda o: o.match_score or 0, reverse=True
            )
        elif sort_by == "Salaire estimé ↓":
            filtered_offers = sorted(
                filtered_offers,
                key=lambda o: (o.tags or {})
                .get("llm_analysis", {})
                .get("salaire_estime", {})
                .get("min")
                or o.salary_min
                or 0,
                reverse=True,
            )

        for o in filtered_offers[:60]:
            _render_card(o)

    with tab2:
        if filtered_df.empty:
            st.info("Aucune donnée.")
        else:
            ca, cb = st.columns(2)
            with ca:
                st.subheader("Scores de matching")
                scores = filtered_df[filtered_df["match_score"] > 0]["match_score"]
                if not scores.empty:
                    fig = px.histogram(scores, nbins=20, color_discrete_sequence=["#1D9E75"])
                    fig.update_layout(height=260, margin=dict(l=0, r=0, t=0, b=0))
                    st.plotly_chart(fig, use_container_width=True)
            with cb:
                st.subheader("Niveau requis")
                niv = filtered_df["poste_type"].value_counts()
                if not niv.empty:
                    fig2 = px.pie(values=niv.values, names=niv.index, hole=0.4)
                    fig2.update_layout(height=260, margin=dict(l=0, r=0, t=20, b=0))
                    st.plotly_chart(fig2, use_container_width=True)

            cc, cd = st.columns(2)
            with cc:
                st.subheader("Culture entreprise")
                cult = filtered_df[filtered_df["culture"] != "—"]["culture"].value_counts().head(8)
                if not cult.empty:
                    fig3 = px.bar(
                        x=cult.values,
                        y=cult.index,
                        orientation="h",
                        color_discrete_sequence=["#7F77DD"],
                    )
                    fig3.update_layout(height=280, margin=dict(l=0, r=0, t=0, b=0))
                    st.plotly_chart(fig3, use_container_width=True)
            with cd:
                st.subheader("Remote")
                rem = filtered_df[filtered_df["remote"] != "non précisé"]["remote"].value_counts()
                if not rem.empty:
                    fig4 = px.pie(values=rem.values, names=rem.index, hole=0.4)
                    fig4.update_layout(height=280, margin=dict(l=0, r=0, t=20, b=0))
                    st.plotly_chart(fig4, use_container_width=True)

    with tab3:
        st.subheader("Compétences les plus demandées")
        from collections import Counter

        all_stack = []
        for _, row in filtered_df.iterrows():
            all_stack.extend(row["stack"])
        if all_stack:
            counts = Counter(all_stack).most_common(20)
            sk_df = pd.DataFrame(counts, columns=["Compétence", "Occurrences"])
            fig5 = px.bar(
                sk_df.sort_values("Occurrences"),
                x="Occurrences",
                y="Compétence",
                orientation="h",
                color="Occurrences",
                color_continuous_scale="Teal",
            )
            fig5.update_layout(height=520, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.info(
                "Lance l'analyse LLM pour voir les compétences : `python -m src.jobs.matching.llm_analyzer`"
            )

        sal_df = filtered_df[(filtered_df["sal_min"] > 20000) & (filtered_df["domaine"] != "—")]
        if not sal_df.empty:
            st.subheader("Salaires par domaine")
            fig6 = px.box(
                sal_df,
                x="domaine",
                y="sal_min",
                labels={"domaine": "", "sal_min": "Salaire min estimé (€)"},
                color="domaine",
            )
            fig6.update_layout(height=350, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
            st.plotly_chart(fig6, use_container_width=True)


def _render_card(offer):
    tags = offer.tags or {}
    llm = tags.get("llm_analysis", {})
    score = offer.match_score or 0
    sal = llm.get("salaire_estime", {})
    stack = llm.get("stack_principale", [])
    poste_type = llm.get("poste_type", "—")
    culture = llm.get("culture_entreprise", "—")
    remote = llm.get("remote", tags.get("remote_type", "—"))

    score_badge = (
        f"🟢 {score:.0f}%"
        if score >= 70
        else f"🟡 {score:.0f}%"
        if score >= 50
        else f"🔴 {score:.0f}%"
        if score > 0
        else "⚪"
    )
    niveau_icon = {"junior": "🌱", "confirmé": "⚡", "senior": "🏆"}.get(poste_type, "❓")

    sal_str = "—"
    if sal.get("min") and sal.get("max"):
        sal_str = f"~{sal['min']:,.0f}€–{sal['max']:,.0f}€"
    elif sal.get("min"):
        sal_str = f"~{sal['min']:,.0f}€+"

    header = (
        f"{score_badge} {niveau_icon} **{offer.title}** — "
        f"{offer.company} · 📍{offer.location} · 💰{sal_str}"
    )

    with st.expander(header):
        col_main, col_side = st.columns([3, 1])

        with col_side:
            st.markdown("**Fiche**")
            st.write(f"📋 {offer.contract_type or '—'}")
            st.write(f"👤 {poste_type}")
            st.write(f"🏢 {culture}")
            st.write(f"🏠 {remote}")
            if sal.get("note"):
                st.caption(f"💡 {sal['note']}")
            if offer.url:
                st.link_button("Voir l'offre ↗", offer.url)

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
                    f"**Adéquation :** :{col}[{score:.0f}%]" + (f" — {justif}" if justif else "")
                )

            pf = llm.get("points_forts_candidature", [])
            pm = llm.get("competences_manquantes", [])
            if pf or pm:
                c1, c2 = st.columns(2)
                with c1:
                    if pf:
                        st.markdown("**✅ Points forts**")
                        for p in pf[:3]:
                            st.markdown(f"- {p}")
                with c2:
                    if pm:
                        st.markdown("**⚠️ À développer**")
                        for m in pm[:3]:
                            st.markdown(f"- {m}")

            conseil = llm.get("conseil_candidature")
            if conseil:
                st.success(f"💡 **Conseil :** {conseil}")

            with st.expander("Description complète"):
                st.write(offer.description or "—")
