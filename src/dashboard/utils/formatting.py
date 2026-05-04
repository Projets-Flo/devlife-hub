def format_duration(minutes) -> str:
    """Minutes décimales → 50'12'' ou 1h03'24''"""
    try:
        v = float(minutes)
    except (TypeError, ValueError):
        return "—"
    if v <= 0:
        return "—"
    total_s = int(round(v * 60))
    h = total_s // 3600
    m = (total_s % 3600) // 60
    s = total_s % 60
    return f"{h}h{m:02d}'{s:02d}''" if h > 0 else f"{m}'{s:02d}''"


def format_pace(pace) -> str:
    """Allure décimale → 5'16''/km"""
    try:
        v = float(pace)
    except (TypeError, ValueError):
        return "—"
    if v <= 0:
        return "—"
    m = int(v)
    s = int(round((v - m) * 60))
    return f"{m}'{s:02d}''/km"


def format_track_time(seconds) -> str:
    """Secondes décimales → 17''03 ou 1'30''00 (piste)"""
    try:
        v = float(seconds)
    except (TypeError, ValueError):
        return "—"
    if v <= 0:
        return "—"
    total_cs = int(round(v * 100))
    mins = total_cs // 6000
    secs = (total_cs % 6000) // 100
    cs = total_cs % 100
    return f"{mins}'{secs:02d}''{cs:02d}" if mins > 0 else f"{secs}''{cs:02d}"


def track_time_to_seconds(mins: int, secs: int, cs: int) -> float:
    """Convertit min/sec/centisec en secondes décimales."""
    return mins * 60 + secs + cs / 100
