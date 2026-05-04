import streamlit as st

from src.dashboard.utils.formatting import format_track_time


def render_bloc_summary(bloc: dict) -> str:
    """Résumé textuel d'un bloc pour l'affichage dans la liste."""
    t = bloc.get("type", "")
    if t == "echauffement":
        d = bloc.get("distance_m")
        dur = bloc.get("duree_sec")
        if d:
            return f"🔥 Échauffement — {d}m"
        return f"🔥 Échauffement — {format_track_time(dur)}"
    if t == "recuperation":
        d = bloc.get("distance_m")
        dur = bloc.get("duree_sec")
        if d:
            return f"🧘 Récupération — {d}m"
        return f"🧘 Récupération — {format_track_time(dur)}"
    if t == "serie":
        reps = bloc.get("repetitions", [])
        times = [format_track_time(r["temps_sec"]) for r in reps]
        recup = format_track_time(bloc.get("recup_sec", 0))
        return f"⚡ {len(reps)}×{bloc.get('distance_m')}m (récup {recup}) : {' | '.join(times)}"
    if t == "serie_double":
        groupes = bloc.get("groupes", [])
        recup = format_track_time(bloc.get("recup_sec", 0))
        pause = format_track_time(bloc.get("pause_intra_sec", 0))
        lines = []
        for i, g in enumerate(groupes, 1):
            t1 = format_track_time(g[0]["temps_sec"])
            t2 = format_track_time(g[1]["temps_sec"])
            lines.append(f"Groupe {i}: {t1} / {t2}")
        return (
            f"⚡ {len(groupes)}×(2×{bloc.get('distance_m')}m) "
            f"(pause intra {pause}, récup {recup})\n" + " | ".join(lines)
        )
    return str(bloc)


def render_interval_card(s, expanded: bool = False):
    """Affiche une séance de fractionné sous forme de carte."""
    blocs = s.blocs.get("blocs", []) if isinstance(s.blocs, dict) else []
    total_m = 0
    for b in blocs:
        if b.get("type") in ["echauffement", "recuperation"]:
            total_m += b.get("distance_m") or 0
        elif b.get("type") == "serie":
            total_m += b.get("distance_m", 0) * len(b.get("repetitions", []))
        elif b.get("type") == "serie_double":
            total_m += b.get("distance_m", 0) * 2 * len(b.get("groupes", []))

    header = f"⚡ **{s.date.strftime('%d/%m/%Y')}** — Fractionné — {len(blocs)} blocs — ~{total_m}m"
    with st.expander(header, expanded=expanded):
        for i, bloc in enumerate(blocs, 1):
            st.markdown(f"**Bloc {i}** — {render_bloc_summary(bloc)}")
        if s.notes:
            st.caption(f"📝 {s.notes}")
