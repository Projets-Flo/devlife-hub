import streamlit as st

from src.dashboard.components.interval_widgets import render_bloc_summary
from src.dashboard.utils.formatting import track_time_to_seconds


def init_interval_state():
    if "interval_blocs" not in st.session_state:
        st.session_state.interval_blocs = []
    if "adding_bloc" not in st.session_state:
        st.session_state.adding_bloc = False


def render_time_input(label: str, key_prefix: str):
    """Saisie de temps : min + sec + centisec → retourne les 3 valeurs."""
    st.markdown(f"**{label}**")
    c1, c2, c3 = st.columns(3)
    with c1:
        m = st.number_input("min", min_value=0, step=1, value=0, key=f"{key_prefix}_m")
    with c2:
        s = st.number_input(
            "sec", min_value=0, max_value=59, step=1, value=0, key=f"{key_prefix}_s"
        )
    with c3:
        cs = st.number_input(
            "1/100", min_value=0, max_value=99, step=1, value=0, key=f"{key_prefix}_cs"
        )
    return m, s, cs


def render_add_bloc_form():
    """Formulaire d'ajout d'un seul bloc — appelé hors form Streamlit."""
    st.markdown("---")
    st.markdown("**➕ Nouveau bloc**")

    bloc_type = st.selectbox(
        "Type de bloc",
        ["echauffement", "serie", "serie_double", "recuperation"],
        format_func=lambda x: {
            "echauffement": "🔥 Échauffement",
            "serie": "⚡ Série simple (N × distance)",
            "serie_double": "⚡ Série double (N × 2×distance)",
            "recuperation": "🧘 Récupération",
        }[x],
        key="new_bloc_type",
    )

    bloc = {"type": bloc_type}

    if bloc_type in ["echauffement", "recuperation"]:
        label = "Échauffement" if bloc_type == "echauffement" else "Récupération"
        mode = st.radio(
            "Définir par", ["Distance (m)", "Durée"], horizontal=True, key=f"{bloc_type}_mode"
        )
        if mode == "Distance (m)":
            dist = st.number_input(
                "Distance (m)", min_value=0, step=100, value=800, key=f"{bloc_type}_dist"
            )
            bloc["distance_m"] = int(dist)
        else:
            m, s, cs = render_time_input(f"Durée {label}", f"{bloc_type}_dur")
            bloc["duree_sec"] = track_time_to_seconds(m, s, cs)

    elif bloc_type == "serie":
        dist = st.number_input(
            "Distance par répétition (m)", min_value=0, step=50, value=400, key="serie_dist"
        )
        nb_reps = st.number_input(
            "Nombre de répétitions", min_value=1, step=1, value=6, key="serie_nb"
        )
        m_r, s_r, cs_r = render_time_input("Récupération entre chaque", "serie_recup")
        bloc["distance_m"] = int(dist)
        bloc["recup_sec"] = track_time_to_seconds(m_r, s_r, cs_r)

        st.markdown("**Temps de chaque répétition**")
        reps = []
        for i in range(int(nb_reps)):
            m_t, s_t, cs_t = render_time_input(f"Rép. {i + 1}", f"serie_rep_{i}")
            reps.append({"num": i + 1, "temps_sec": track_time_to_seconds(m_t, s_t, cs_t)})
        bloc["repetitions"] = reps

    elif bloc_type == "serie_double":
        dist = st.number_input(
            "Distance par 200m/repetition (m)", min_value=0, step=50, value=200, key="sd_dist"
        )
        nb_groupes = st.number_input("Nombre de groupes", min_value=1, step=1, value=3, key="sd_nb")
        m_pi, s_pi, cs_pi = render_time_input("Pause intra-groupe (entre les 2)", "sd_pause")
        m_r, s_r, cs_r = render_time_input("Récupération entre les groupes", "sd_recup")
        bloc["distance_m"] = int(dist)
        bloc["pause_intra_sec"] = track_time_to_seconds(m_pi, s_pi, cs_pi)
        bloc["recup_sec"] = track_time_to_seconds(m_r, s_r, cs_r)

        st.markdown("**Temps de chaque effort**")
        groupes = []
        for g in range(int(nb_groupes)):
            st.markdown(f"*Groupe {g + 1}*")
            m1, s1, cs1 = render_time_input("Effort 1", f"sd_g{g}_1")
            m2, s2, cs2 = render_time_input("Effort 2", f"sd_g{g}_2")
            groupes.append(
                [
                    {"num": 1, "temps_sec": track_time_to_seconds(m1, s1, cs1)},
                    {"num": 2, "temps_sec": track_time_to_seconds(m2, s2, cs2)},
                ]
            )
        bloc["groupes"] = groupes

    col_add, col_cancel = st.columns(2)
    with col_add:
        if st.button("✅ Ajouter ce bloc", type="primary"):
            st.session_state.interval_blocs.append(bloc)
            st.session_state.adding_bloc = False
            st.rerun()
    with col_cancel:
        if st.button("❌ Annuler"):
            st.session_state.adding_bloc = False
            st.rerun()


def render_fractionne_form():
    """Formulaire complet pour saisir une séance de fractionné."""
    init_interval_state()

    from datetime import datetime as dt_cls

    col1, col2 = st.columns(2)
    with col1:
        date_f = st.date_input("Date", key="int_date")
    with col2:
        heure_f = st.time_input("Heure", key="int_heure")

    notes_f = st.text_area("Notes (optionnel)", key="int_notes")

    if st.session_state.interval_blocs:
        st.markdown("**Blocs de la séance**")
        for i, bloc in enumerate(st.session_state.interval_blocs):
            col_b, col_del = st.columns([5, 1])
            with col_b:
                st.info(f"**Bloc {i + 1}** — {render_bloc_summary(bloc)}")
            with col_del:
                if st.button("🗑️", key=f"del_bloc_{i}"):
                    st.session_state.interval_blocs.pop(i)
                    st.rerun()

    if not st.session_state.adding_bloc:
        if st.button("➕ Ajouter un bloc"):
            st.session_state.adding_bloc = True
            st.rerun()
    else:
        render_add_bloc_form()

    st.markdown("---")

    if st.session_state.interval_blocs and not st.session_state.adding_bloc:
        if st.button("💾 Enregistrer la séance", type="primary"):
            from sqlalchemy.orm import Session as DBSession

            from src.common.database import IntervalSession, engine

            start_dt = dt_cls.combine(date_f, heure_f)
            new_session = IntervalSession(
                date=start_dt,
                notes=notes_f if notes_f else None,
                blocs={"blocs": st.session_state.interval_blocs},
            )
            with DBSession(engine) as db_session:
                db_session.add(new_session)
                db_session.commit()

            st.success(
                f"✅ Séance fractionné du {date_f.strftime('%d/%m/%Y')} enregistrée "
                f"({len(st.session_state.interval_blocs)} blocs)"
            )
            st.session_state.interval_blocs = []
            st.session_state.adding_bloc = False
            st.cache_data.clear()
            st.rerun()
    elif not st.session_state.interval_blocs:
        st.caption("Ajoute au moins un bloc pour pouvoir enregistrer.")
