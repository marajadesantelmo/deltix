"""Calendario académico: datos estructurados (fecha ↔ evento) y consulta determinista.

Las fechas NUNCA pasan por el modelo de lenguaje: en la prueba del 11/11 el LLM asociaba cada evento con la fecha
de la fila siguiente (6 errores de 12) porque la tabla llegaba aplastada a texto. Acá cada fila es un par
(fecha, evento) y las preguntas de calendario se responden citando la fila tal cual.

Fuente: data/institucional/calendario.json, generado por scripts/crawl_undelta.py desde la tabla de
https://undelta.edu.ar/servicios-academicos/.
"""
import json
import os
import re

from . import config, kb

RUTA = os.path.join(config.DATA_DIR, "institucional", "calendario.json")
URL_PDF = "https://undelta.edu.ar/wp-content/themes/undelta/assets/doc/calendario-academico-undelta-2026.pdf"
URL_PAGINA = "https://undelta.edu.ar/servicios-academicos/"

# Una pregunta es "de calendario" solo si menciona alguno de estos temas (evita capturar preguntas ajenas).
_TEMAS = re.compile(
    r"calendario|cuatrimestre|receso|llamado|mesas?\b|finales?\b|ex[aá]menes?|equivalencias?|cambio de carrera|"
    r"ciclo lectivo|inicio de clases|comienzo de clases|empiezan? las clases|fin de clases|inscripci[oó]n a (materias|ex[aá]menes|finales)|"
    r"cu[aá]ndo (empieza|comienza|termina|finaliza|abre|cierra|es la inscripci[oó]n)",
    re.I)
# Vocabulario de las preguntas → vocabulario de la tabla.
_SIN = {"empieza": "inicio", "empiezan": "inicio", "comienza": "inicio", "comienzan": "inicio", "arranca": "inicio",
        "termina": "finalizacion", "terminan": "finalizacion", "finaliza": "finalizacion", "fin": "finalizacion",
        "cierra": "finalizacion", "vacaciones": "receso", "mesas": "mesa", "examenes": "examenes finales",
        "materias": "materias"}
UMBRAL_REL = 0.8     # solo se agregan filas con al menos 80 % del puntaje de la mejor (empates reales, p. ej. "inicio de clases")
_MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "setiembre",
          "octubre", "noviembre", "diciembre")
MAX_FILAS = 3

_cache = None


def cargar():
    global _cache
    if _cache is None:
        try:
            with open(RUTA, encoding="utf-8") as f:
                _cache = json.load(f)
        except (OSError, ValueError):
            _cache = {"filas": [], "aclaracion": "", "titulo": "Calendario académico"}
    return _cache


def _retriever():
    cal = cargar()
    filas = [{"id": i, "titulo": f["evento"], "texto": f"{f['evento']} {f['mes']}", "peso": 1.0, "fila": f}
             for i, f in enumerate(cal["filas"])]
    return kb.Retriever(filas) if filas else None


_ret = None


def es_pregunta_de_calendario(texto):
    return bool(_TEMAS.search(texto or "")) and bool(cargar()["filas"])


def buscar(pregunta):
    """Filas del calendario que responden a la pregunta (lista de dicts; [] si no hay una coincidencia clara)."""
    global _ret
    if _ret is None:
        _ret = _retriever()
    if not _ret:
        return []
    q = " ".join(_SIN.get(w, w) for w in re.findall(r"\w+", kb.norm(pregunta)))
    hits = _ret.buscar(q, k=len(_ret.chunks))
    # Si la pregunta nombra un mes, solo compiten las filas de ese mes (o que lo mencionan en el evento).
    meses = {m for m in _MESES if m in q.split()}
    if meses:
        del_mes = [h for h in hits if kb.norm(h["fila"]["mes"]) in meses or any(m in kb.norm(h["fila"]["evento"]) for m in meses)]
        hits = del_mes or hits
    if not hits or hits[0]["score"] < 2.5:
        return []
    mejor = hits[0]["score"]
    elegidas = [h for h in hits if h["score"] >= UMBRAL_REL * mejor][:MAX_FILAS]
    return [h["fila"] for h in sorted(elegidas, key=lambda h: h["id"])]   # orden del calendario


def _linea(f, negrita=True):
    ev = f"*{f['evento']}*" if negrita else f["evento"]
    return f"📅 {ev}: {f['fecha']}"


def responder(pregunta):
    """Texto de respuesta determinista, o None si la pregunta no encaja con ninguna fila."""
    filas = buscar(pregunta)
    if not filas:
        return None
    cal = cargar()
    out = [_linea(f) for f in filas]
    out.append(f"\n({cal['titulo']}.) Ante cualquier diferencia con una resolución posterior, vale la resolución. "
               f"Ver calendario completo: {URL_PAGINA}")
    return "\n".join(out)


def texto_completo():
    """Calendario entero agrupado por mes, para el menú."""
    cal = cargar()
    if not cal["filas"]:
        return f"🗓 Calendario académico: {URL_PDF}\nTambién está en {URL_PAGINA}"
    out, mes = [f"🗓 *{cal['titulo']}*"], None
    for f in cal["filas"]:
        if f["mes"] != mes:
            mes = f["mes"]
            out.append(f"\n*{mes}*")
        out.append(f"- {f['fecha']}: {f['evento']}" + (" ⭐" if f.get("hito") else ""))
    if cal.get("aclaracion"):
        out.append(f"\n{cal['aclaracion']}")
    out.append(f"\n📄 PDF: {URL_PDF}\n🔗 {URL_PAGINA}")
    return "\n".join(out)


def chunks_para_kb():
    """Fragmentos del RAG: uno por mes, con cada fila como 'fecha: evento' (nunca separados)."""
    cal = cargar()
    porm = {}
    for f in cal["filas"]:
        porm.setdefault(f["mes"], []).append(f)
    return [(f"{cal['titulo']} — {mes}",
             "\n".join(f"- {f['fecha']}: {f['evento']}" for f in filas) +
             (f"\n{cal['aclaracion']}" if cal.get("aclaracion") else ""))
            for mes, filas in porm.items()]
