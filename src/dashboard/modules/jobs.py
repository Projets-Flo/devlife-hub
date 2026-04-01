"""
Page Offres d'emploi — triage rapide avec statuts.
"""

import pandas as pd
import plotly.express as px
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

TRIAGE_DISPLAY_LIMIT = 80

STATUS_LABELS = {
    "new": ("🆕", "À trier"),
    "interesting": ("✅", "Intéressant"),
    "maybe": ("⏳", "À voir"),
    "rejected": ("❌", "Non pertinent"),
}


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
    return ct.capitalize()


def _update_status(offer_id: int, status: str):
    """Met à jour le statut d'une offre directement en base."""
    with Session(engine) as session:
        offer = session.get(JobOffer, offer_id)
        if offer:
            offer.status = status
            session.commit()


@st.cache_data(ttl=60, show_spinner="Chargement des offres…")
def load_offers() -> tuple[list, pd.DataFrame]:
    with Session(engine) as session:
        all_offers = session.query(JobOffer).order_by(JobOffer.scraped_at.desc()).all()
        session.expunge_all()

    rows = []
    for o in all_offers:
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
                "salary_min": o.salary_min or 0,
                "salary_max": o.salary_max or 0,
                "remote": o.remote,
                "status": o.status or "new",
                "url": o.url or "",
                "description": (o.description or "")[:800],
            }
        )
    return all_offers, pd.DataFrame(rows)


def render():
    st.title("🔍 Offres d'emploi")

    col_refresh, col_info = st.columns([1, 5])
    with col_refresh:
        if st.button("🔄 Actualiser"):
            st.cache_data.clear()
            st.rerun()

    all_offers, df = load_offers()

    if not all_offers:
        st.warning("Aucune offre en base.")
        st.code("python -m src.jobs.scrapers.job_collector")
        return

    total = len(df)
    n_new = int((df["status"] == "new").sum())
    n_interesting = int((df["status"] == "interesting").sum())
    n_maybe = int((df["status"] == "maybe").sum())
    n_rejected = int((df["status"] == "rejected").sum())

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total", total)
    c2.metric("🆕 À trier", n_new)
    c3.metric("✅ Intéressants", n_interesting)
    c4.metric("⏳ À voir", n_maybe)
    c5.metric("❌ Rejetés", n_rejected)

    st.divider()

    tab_triage, tab_interesting, tab_market, tab_cmd = st.tabs(
        ["🆕 Triage", "⭐ Mes favoris", "🗺️ Marché", "⚙️ Commandes"]
    )

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 1 — TRIAGE
    # ═══════════════════════════════════════════════════════════════════════
    with tab_triage:
        with st.expander("🎛️ Filtres", expanded=True):
            r1 = st.columns([3, 1, 1])
            search = r1[0].text_input("🔍 Recherche", placeholder="python, data, NLP…")
            contracts = r1[1].multiselect("📋 Contrat", ["CDI", "CDD", "Intérim"])
            show_status = r1[2].multiselect(
                "Statut",
                ["new", "interesting", "maybe", "rejected"],
                default=["new", "maybe"],
                format_func=lambda x: STATUS_LABELS[x][1],
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
            ville_search = g4.text_input("Ville / texte libre", placeholder="Lyon, Annecy…")

            sal_min_filter = st.number_input("💰 Salaire min (€)", 0, step=5000)

        # Application filtres
        filtered = _apply_filters(
            df,
            search,
            contracts,
            show_status,
            zone_rapide,
            regions_filter,
            deps_codes,
            ville_search,
            sal_min_filter,
        )
        filtered_offers = [o for o in all_offers if o.id in set(filtered["id"].tolist())]

        st.caption(f"**{len(filtered_offers)}** offres affichées")

        # Affichage compact avec boutons de triage
        for o in filtered_offers[:TRIAGE_DISPLAY_LIMIT]:
            _render_triage_card(o)

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 2 — FAVORIS
    # ═══════════════════════════════════════════════════════════════════════
    with tab_interesting:
        st.subheader("⭐ Offres qui t'intéressent")

        interesting = [o for o in all_offers if (o.status or "new") == "interesting"]
        maybe = [o for o in all_offers if (o.status or "new") == "maybe"]

        if not interesting and not maybe:
            st.info("Aucune offre marquée. Commence le triage dans l'onglet 🆕 Triage.")
        else:
            if interesting:
                st.markdown(f"**✅ Intéressants ({len(interesting)})**")
                for o in interesting:
                    _render_favorite_card(o)

            if maybe:
                st.divider()
                st.markdown(f"**⏳ À voir ({len(maybe)})**")
                for o in maybe:
                    _render_favorite_card(o)

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 3 — MARCHÉ
    # ═══════════════════════════════════════════════════════════════════════
    with tab_market:
        st.subheader("🗺️ Intelligence marché")

        ma, mb = st.columns(2)

        with ma:
            st.subheader("Offres par région")
            reg_counts = df[df["region"] != "—"]["region"].value_counts().reset_index()
            reg_counts.columns = ["Région", "Offres"]
            if not reg_counts.empty:
                fig1 = px.bar(
                    reg_counts.sort_values("Offres"),
                    x="Offres",
                    y="Région",
                    orientation="h",
                    color_discrete_sequence=["#1D9E75"],
                )
                fig1.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig1, use_container_width=True)

        with mb:
            st.subheader("Type de contrat")
            ct_counts = df["contract_type"].value_counts()
            fig2 = px.pie(
                values=ct_counts.values,
                names=ct_counts.index,
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig2.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig2, use_container_width=True)

        # Salaires
        sal_df = df[df["salary_min"] > 20000]
        if not sal_df.empty:
            st.subheader("Salaires par région")
            top_regs = sal_df["region"].value_counts().head(8).index
            sal_top = sal_df[sal_df["region"].isin(top_regs)]
            fig3 = px.box(
                sal_top,
                x="region",
                y="salary_min",
                color="region",
                labels={"region": "", "salary_min": "Salaire min (€)"},
            )
            fig3.update_layout(height=350, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
            st.plotly_chart(fig3, use_container_width=True)
            st.caption(f"Basé sur {len(sal_df)} offres avec salaire renseigné")

        # Répartition statuts
        st.subheader("Avancement du triage")
        status_counts = df["status"].value_counts().reset_index()
        status_counts.columns = ["Statut", "Offres"]
        status_counts["Label"] = status_counts["Statut"].map(
            lambda x: STATUS_LABELS.get(x, ("", x))[1]
        )
        fig4 = px.pie(
            status_counts,
            values="Offres",
            names="Label",
            hole=0.4,
            color_discrete_sequence=["#888780", "#1D9E75", "#EF9F27", "#E24B4A"],
        )
        fig4.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig4, use_container_width=True)

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 4 — COMMANDES
    # ═══════════════════════════════════════════════════════════════════════
    with tab_cmd:
        st.subheader("⚙️ Commandes utiles")
        st.caption("Copie-colle dans le terminal (.venv activé + Docker lancé)")

        st.markdown("#### 🗄️ Démarrer la base")
        st.code("docker compose up -d db", language="bash")

        st.markdown("#### 📥 Collecter les offres")
        st.code("python -m src.jobs.scrapers.job_collector", language="bash")

        st.markdown("#### 🔄 Pipeline quotidien (collecte + nouvelles offres)")
        st.code("python -m src.jobs.flows.daily_pipeline", language="bash")

        st.markdown("#### 🧹 Supprimer alternances/stages")
        st.code(
            '''python -c "
from sqlalchemy.orm import Session
from src.common.database import JobOffer, engine
excluded = [\'alternance\', \'apprentissage\', \'stage\', \'stagiaire\']
with Session(engine) as session:
    deleted = sum(1 for o in session.query(JobOffer).all()
                  if any(kw in (o.title or \'\').lower() for kw in excluded)
                  and (session.delete(o) or True))
    session.commit()
    print(f\'{deleted} offres supprimées\')
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
3. Cliquer 🔄 dans le dashboard
        """)
        st.markdown("#### 🔁 Mise à jour quotidienne")
        st.markdown("""
1. `docker compose up -d db`
2. `python -m src.jobs.flows.daily_pipeline`
3. Cliquer 🔄 dans le dashboard
        """)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _apply_filters(
    df,
    search,
    contracts,
    show_status,
    zone_rapide,
    regions_filter,
    deps_codes,
    ville_search,
    sal_min_filter,
):
    filtered_ids = set(df["id"].tolist())

    if search:
        terms = search.lower().split()
        mask = pd.Series([True] * len(df), index=df.index)
        for t in terms:
            mask &= (
                df["title"].str.lower().str.contains(t, na=False)
                | df["company"].str.lower().str.contains(t, na=False)
                | df["description"].str.lower().str.contains(t, na=False)
            )
        filtered_ids &= set(df[mask]["id"].tolist())

    if contracts:
        mask = df["contract_type"].isin(contracts)
        filtered_ids &= set(df[mask]["id"].tolist())

    if show_status:
        filtered_ids &= set(df[df["status"].isin(show_status)]["id"].tolist())

    if zone_rapide == "Ma zone prioritaire":
        mask = df["dep"].isin(ZONE_PRIORITAIRE) | df["remote"].eq(True)
        filtered_ids &= set(df[mask]["id"].tolist())
    elif zone_rapide == "Île-de-France":
        filtered_ids &= set(df[df["dep"].isin(REGIONS["Île-de-France"])]["id"].tolist())
    elif zone_rapide == "Auvergne-Rhône-Alpes":
        filtered_ids &= set(df[df["dep"].isin(REGIONS["Auvergne-Rhône-Alpes"])]["id"].tolist())
    elif zone_rapide == "Remote uniquement":
        filtered_ids &= set(df[df["remote"].eq(True)]["id"].tolist())

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

    if sal_min_filter > 0:
        filtered_ids &= set(df[df["salary_min"] >= sal_min_filter]["id"].tolist())

    return df[df["id"].isin(filtered_ids)]


def _render_triage_card(offer):
    """Carte compacte avec boutons de triage."""
    status = offer.status or "new"
    icon, label = STATUS_LABELS.get(status, ("🆕", "À trier"))

    dep = _extract_dep(offer.location or "")
    dep_label = f" ({DEPARTEMENTS.get(dep, '')})" if dep else ""

    sal_str = ""
    if offer.salary_min and offer.salary_max:
        sal_str = f"  ·  💰 {offer.salary_min:,.0f}€–{offer.salary_max:,.0f}€"
    elif offer.salary_min:
        sal_str = f"  ·  💰 {offer.salary_min:,.0f}€+"

    remote_str = "  ·  🏠 Remote" if offer.remote else ""

    header = (
        f"{icon} **{offer.title}**"
        f"  —  {offer.company}"
        f"  ·  📍 {offer.location}{dep_label}"
        f"  ·  {_normalize_contract(offer.contract_type or '')}"
        f"{sal_str}{remote_str}"
    )

    with st.expander(header):
        # Description courte
        desc = offer.description or ""
        st.write(desc[:600] + "..." if len(desc) > 600 else desc)

        st.divider()

        # Boutons de triage
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])

        with col1:
            if st.button("✅ Intéressant", key=f"int_{offer.id}"):
                _update_status(offer.id, "interesting")
                st.cache_data.clear()
                st.rerun()
        with col2:
            if st.button("⏳ À voir", key=f"maybe_{offer.id}"):
                _update_status(offer.id, "maybe")
                st.cache_data.clear()
                st.rerun()
        with col3:
            if st.button("❌ Rejeter", key=f"rej_{offer.id}"):
                _update_status(offer.id, "rejected")
                st.cache_data.clear()
                st.rerun()
        with col4:
            if st.button("🆕 Remettre", key=f"new_{offer.id}"):
                _update_status(offer.id, "new")
                st.cache_data.clear()
                st.rerun()
        with col5:
            if offer.url:
                st.link_button("Voir l'offre complète ↗", offer.url)


def _render_favorite_card(offer):
    """Carte pour les favoris avec infos complètes."""
    dep = _extract_dep(offer.location or "")
    dep_label = f" ({DEPARTEMENTS.get(dep, '')})" if dep else ""

    sal_str = ""
    if offer.salary_min and offer.salary_max:
        sal_str = f"  ·  💰 {offer.salary_min:,.0f}€–{offer.salary_max:,.0f}€"
    elif offer.salary_min:
        sal_str = f"  ·  💰 {offer.salary_min:,.0f}€+"

    header = (
        f"**{offer.title}**  —  {offer.company}"
        f"  ·  📍 {offer.location}{dep_label}"
        f"  ·  {_normalize_contract(offer.contract_type or '')}"
        f"{sal_str}"
    )

    with st.expander(header):
        col_desc, col_action = st.columns([3, 1])

        with col_desc:
            desc = offer.description or ""
            st.write(desc[:1000] + "..." if len(desc) > 1000 else desc)

        with col_action:
            if offer.url:
                st.link_button("Postuler ↗", offer.url)
            st.divider()
            if st.button("⏳ Remettre en 'À voir'", key=f"fav_maybe_{offer.id}"):
                _update_status(offer.id, "maybe")
                st.cache_data.clear()
                st.rerun()
            if st.button("❌ Rejeter", key=f"fav_rej_{offer.id}"):
                _update_status(offer.id, "rejected")
                st.cache_data.clear()
                st.rerun()
