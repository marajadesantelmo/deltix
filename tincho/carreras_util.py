"""Utilidades de presentación de carreras (correcciones del equipo, 8-oct)."""
import re


def duracion_legible(d):
    """'6 cuatrimestres' -> '6 cuatrimestres (3 años)'."""
    m = re.match(r"\s*(\d+)\s*cuatrimestres?", d or "", re.I)
    if not m:
        return d or "a confirmar"
    n = int(m.group(1))
    anios = n // 2
    txt = f"{anios} año{'s' if anios != 1 else ''}" if n % 2 == 0 else f"{anios} años y medio"
    return f"{n} cuatrimestres ({txt})"
