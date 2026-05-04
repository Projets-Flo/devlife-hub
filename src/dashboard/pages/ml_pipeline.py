import streamlit as st


def render():
    st.title("⚙️ ML Pipeline")
    st.info("MLflow disponible sur localhost:5000.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Modèles prévus**")
        st.markdown("""
        - 📈 Training load forecaster (Prophet)
        - 💰 Salary predictor (XGBoost)
        - 🔍 Job matcher (sentence-transformers)
        """)
    with c2:
        st.markdown("**Stack MLOps**")
        st.markdown("""
        - 📊 MLflow — tracking
        - 🗂 DVC — versioning
        - 🐳 Docker — reproductibilité
        - ⚡ GitHub Actions — CI/CD
        """)
