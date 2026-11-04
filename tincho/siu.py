"""Cliente SIU Guaraní de SOLO LECTURA para Tincho.

Principios de seguridad:
  - Solo GET, y solo a rutas de una lista blanca (ver PERMITIDOS). Nada puede escribir en SIU.
  - Mínimo privilegio: no se usa `datospersonales` (domicilio, teléfonos); el correo para el
    código sale de la respuesta de `/personas` o `/docentes`.
  - Se valida TLS siempre. Credenciales de la API solo por variables de entorno.
  - Si falta configuración, falla cerrado (la función de consultas SIU queda deshabilitada).
"""
import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from . import config

PERMITIDOS = (
    re.compile(r"^/personas$"),
    re.compile(r"^/personas/\d+/(cursadas|inscripciones-examen|resumen-academico)$"),
    re.compile(r"^/docentes$"),
    re.compile(r"^/docentes/\d+/(comisiones|mesas)$"),
)


class SiuError(Exception):
    pass


def habilitado():
    return config.SIU_MOCK or bool(config.SIU_USER and config.SIU_PASSWORD and config.SIU_URL)


def _get(path, params=None):
    if not any(p.match(path) for p in PERMITIDOS):
        raise SiuError("ruta no permitida")
    if config.SIU_MOCK:
        from . import siu_mock
        return siu_mock.get(path, params or {})
    if not habilitado():
        raise SiuError("SIU no configurado")
    url = config.SIU_URL.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(params, safe=";")
    tok = base64.b64encode(f"{config.SIU_USER}:{config.SIU_PASSWORD}".encode()).decode()
    req = urllib.request.Request(url, method="GET",
                                 headers={"Authorization": "Basic " + tok, "Accept": "application/json",
                                          # Cloudflare (error 1010) bloquea el User-Agent por defecto de Python
                                          "User-Agent": "tincho-undelta/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=config.SIU_TIMEOUT) as r:
            body = r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise SiuError(f"SIU respondió {e.code}")
    except Exception as e:  # timeout, red, TLS
        raise SiuError(type(e).__name__)
    try:
        return json.loads(body or b"[]")
    except ValueError:
        raise SiuError("respuesta no JSON")


def _lista(x):
    if isinstance(x, dict):
        for k in ("data", "items", "resultados", "results"):
            if isinstance(x.get(k), list):
                return x[k]
        return [x] if x else []
    return x or []


def _primero(d, *claves, default=None):
    for k in claves:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return default


def _buscar_clave(d, fragmento):
    """Primer valor str cuya clave contenga `fragmento` (los campos de SIU varían por versión)."""
    if isinstance(d, dict):
        for k, v in d.items():
            if fragmento in k.lower() and isinstance(v, str) and v.strip():
                return v.strip()
    return None


# ── identificación ──
def buscar_identidad(dni):
    """Devuelve {'persona': id|None, 'docente': id|None, 'email': str|None}. Sin datos → todo None."""
    ident = {"persona": None, "docente": None, "email": None}
    pers = _lista(_get("/personas", {"tipo_documento": "0", "numero_documento": dni, "pais": "54"}))
    if pers:
        ident["persona"] = _primero(pers[0], "persona", "id_persona", "id")
        ident["email"] = _primero(pers[0], "email", "mail")
    try:
        docs = _lista(_get("/docentes", {"tipo_documento": "0", "nro_documento": f"es_igual_a;{dni}"}))
        if docs:
            ident["docente"] = _primero(docs[0], "docente", "id_docente", "id")
            ident["email"] = ident["email"] or _primero(docs[0], "email", "mail")
    except SiuError:
        pass  # que falle docentes no impide el rol alumno
    for k in ("persona", "docente"):
        if ident[k] is not None:
            try:
                ident[k] = int(ident[k])
            except (TypeError, ValueError):
                ident[k] = None
    if isinstance(ident["email"], str):
        ident["email"] = ident["email"].strip() if "@" in ident["email"] else None
    return ident


# ── consultas del alumno ──
def cursadas(persona):
    return _lista(_get(f"/personas/{int(persona)}/cursadas", {"vigentes": "1"}))


def mesas(persona):
    return _lista(_get(f"/personas/{int(persona)}/inscripciones-examen", {"vigentes": "1"}))


def resumen(persona):
    return _lista(_get(f"/personas/{int(persona)}/resumen-academico"))


def comisiones_docente(docente):
    return _lista(_get(f"/docentes/{int(docente)}/comisiones"))


def mesas_docente(docente):
    return _lista(_get(f"/docentes/{int(docente)}/mesas"))


# ── formateo (determinista: los datos personales NUNCA pasan por el LLM) ──
def _fecha(v):
    if not v:
        return ""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?", str(v))
    if not m:
        return str(v)
    a, mth, d, hh, mm = m.groups()
    out = f"{d}/{mth}/{a}"
    return out + (f" {hh}:{mm} hs" if hh and (hh, mm) != ("00", "00") else "")


def texto_cursadas(filas):
    if not filas:
        return "No encontré cursadas vigentes a tu nombre."
    out = ["*Tus cursadas vigentes:*"]
    for f in filas[:15]:
        mat = _primero(f, "actividad_nombre", "actividad", "materia", default="Materia")
        com = _primero(f, "comision_nombre", "comision", default="")
        carr = _primero(f, "propuesta_nombre_abreviado", "propuesta_nombre", default="")
        ini, fin = _fecha(_primero(f, "fecha_inicio_dictado", "fecha_desde")), _fecha(_primero(f, "fecha_fin_dictado", "fecha_hasta"))
        linea = f"- {mat}" + (f" (comisión {com})" if com else "") + (f" · {carr}" if carr else "")
        if ini:
            linea += f" · desde {ini}" + (f" hasta {fin}" if fin else "")
        out.append(linea)
    return "\n".join(out)


def texto_mesas(filas):
    if not filas:
        return "No tenés inscripciones vigentes a mesas de examen."
    out = ["*Tus inscripciones a mesas de examen:*"]
    for f in filas[:15]:
        mat = _primero(f, "actividad_nombre", "actividad", "materia", default="Materia")
        fecha = _fecha(_primero(f, "fecha", "fecha_hora", "fecha_mesa"))
        turno = _primero(f, "turno_nombre", "turno", default="")
        llam = _primero(f, "llamado", "llamado_nombre", default="")
        out.append(f"- {mat}" + (f" · {fecha}" if fecha else "") + (f" · {turno}" if turno else "")
                   + (f" · llamado {llam}" if llam else ""))
    return "\n".join(out)


def texto_resumen(filas):
    if not filas:
        return "Todavía no tengo un resumen académico para mostrarte."
    out = ["*Tu resumen académico:*"]
    for f in filas[:10]:
        carr = _primero(f, "propuesta_nombre", "propuesta", default="Carrera")
        prom = _primero(f, "promedio_con_aplazos", "promedio")
        prom_sin = _primero(f, "promedio_sin_aplazos")
        apr = _primero(f, "cantidad_aprobadas", "actividades_aprobadas", "aprobadas")
        tot = _primero(f, "cantidad_actividades_plan", "actividades_total", "total_actividades", "total")
        linea = f"- {carr}: "
        partes = []
        if apr is not None and tot is not None:
            partes.append(f"{apr} de {tot} materias aprobadas")
        if prom_sin is not None:
            partes.append(f"promedio {prom_sin} (sin aplazos)")
        if prom is not None:
            partes.append(f"{prom} (con aplazos)")
        if prom is None and prom_sin is None:
            partes.append("sin promedio numérico")
        out.append(linea + " · ".join(partes))
    return "\n".join(out)


def texto_comisiones_docente(filas):
    if not filas:
        return "No encontré comisiones asignadas a tu nombre."
    out = ["*Tus comisiones:*"]
    for f in filas[:20]:
        mat = _primero(f, "actividad_nombre", "actividad", "materia", default="Materia")
        com = _primero(f, "comision_nombre", "comision", default="")
        out.append(f"- {mat}" + (f" (comisión {com})" if com else ""))
    return "\n".join(out)


def enmascarar_email(e):
    if not e or "@" not in e:
        return ""
    u, d = e.split("@", 1)
    return u[:2] + "***@" + d
