"""
DevLife Hub — Dashboard Streamlit MVP
Point d'entrée : streamlit run src/dashboard/app.py
"""

import streamlit as st

# ── Config page ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DevLife Hub",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS minimal ───────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
    .metric-card {
        background: #f8f9fa; border-radius: 10px;
        padding: 1rem 1.2rem; border: 1px solid #e9ecef;
    }
    .status-new { color: #0d6efd; font-weight: 500; }
    .status-applied { color: #fd7e14; font-weight: 500; }
    .status-interview { color: #198754; font-weight: 500; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Sidebar navigation ────────────────────────────────────────────────────────
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


# ── Pages ─────────────────────────────────────────────────────────────────────

if page == "🏠 Accueil":
    st.title("Bonjour 👋")
    st.caption("Voici ton résumé du jour")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Nouvelles offres", "—", help="Offres scrappées aujourd'hui")
    with col2:
        st.metric("Candidatures", "—", help="Candidatures en cours")
    with col3:
        st.metric("Séances ce mois", "—", help="Entraînements ce mois")
    with col4:
        st.metric("Score matching max", "—%", help="Meilleur score NLP du jour")

    st.divider()
    st.subheader("Plan du jour")
    st.info("💡 Le coach quotidien sera disponible après la connexion à l'API Claude.")

elif page == "🔍 Offres d'emploi":
    st.title("🔍 Offres d'emploi")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("Rechercher", placeholder="Data scientist, ML engineer…")
    with col2:
        location = st.selectbox("Zone", ["Tout", "Genève", "Lausanne", "Annecy", "Remote"])
    with col3:
        contract = st.selectbox("Contrat", ["Tous", "CDI", "CDD", "Stage", "Freelance"])

    st.info(
        "📡 Le scraping automatique sera activé en Phase 2. En attendant, importe des offres via le CLI."
    )

    # Placeholder table
    st.subheader("Offres récentes")
    st.caption("Aucune offre importée — lance le scraper pour commencer.")

elif page == "🏃 Sport":
    st.title("🏃 Activité sportive")

    tab1, tab2, tab3 = st.tabs(["📊 Mes séances", "📥 Import Samsung Health", "📅 Plan semaine"])

    with tab1:
        st.info("Aucune séance importée. Va dans l'onglet 'Import Samsung Health'.")

    with tab2:
        st.subheader("Import Samsung Health")
        st.markdown("""
        **Comment exporter tes données :**
        1. Ouvre **Samsung Health** → profil → paramètres → *Télécharger les données personnelles*
        2. Sélectionne la période et confirme l'export
        3. Tu recevras un ZIP par email — dépose-le ici ⬇️
        """)

        uploaded = st.file_uploader(
            "Dépose ton export Samsung Health (ZIP ou CSV)", type=["zip", "csv"]
        )
        if uploaded:
            st.success(f"Fichier reçu : {uploaded.name} ({uploaded.size / 1024:.0f} Ko)")
            if st.button("Importer les séances", type="primary"):
                with st.spinner("Parsing en cours…"):
                    # Import réel : sera connecté au parser
                    st.info(
                        "Parser Samsung Health — à connecter (src/sport/parsers/samsung_health.py)"
                    )

    with tab3:
        st.info("Le générateur de plan basé sur la météo sera disponible en Phase 1.")

elif page == "🎯 Coach":
    st.title("🎯 Coach quotidien")
    st.info(
        "Le module Coach (Claude API) sera activé une fois l'API configurée (.env → ANTHROPIC_API_KEY)."
    )

    st.subheader("Prochaines actions suggérées")
    st.markdown("""
    - [ ] Finaliser le setup du projet (ce que tu fais maintenant ✓)
    - [ ] Configurer les variables d'environnement
    - [ ] Lancer `docker compose up -d`
    - [ ] Exporter tes données Samsung Health
    - [ ] Créer un compte OpenWeatherMap (API gratuite)
    """)

elif page == "⚙️ ML Pipeline":
    st.title("⚙️ ML Pipeline")
    st.subheader("Expériences MLflow")
    st.info("Connecter MLflow : MLFLOW_TRACKING_URI dans .env puis `docker compose up mlflow`")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Modèles prévus**")
        st.markdown("""
        - 🔍 Job matcher (sentence-transformers)
        - 💰 Salary predictor (XGBoost)
        - 📈 Training load forecaster (Prophet)
        - 📄 CV gap analyzer (NLP)
        """)
    with col2:
        st.markdown("**Stack MLOps**")
        st.markdown("""
        - 📊 MLflow — tracking des expériences
        - 🗂 DVC — versioning des datasets
        - 🐳 Docker — reproductibilité
        - ⚡ GitHub Actions — CI/CD
        """)
