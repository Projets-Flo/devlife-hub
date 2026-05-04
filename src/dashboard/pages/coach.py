import streamlit as st


def render():
    st.title("🎯 Coach quotidien")
    st.info("Le module Coach sera activé avec l'API Claude (.env → ANTHROPIC_API_KEY).")
    st.subheader("Prochaines actions")
    st.markdown("""
    - [x] Setup projet ✓
    - [x] Docker + PostgreSQL ✓
    - [x] Import Samsung Health ✓
    - [x] Courses manuelles + fractionné ✓
    - [ ] Module Coach (Claude API)
    """)
