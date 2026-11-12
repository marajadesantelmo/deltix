"""Motor conversacional de Tincho: menús predefinidos, palabras clave, verificación de
identidad y consultas SIU. Reproduce el comportamiento del bot de WhatsApp (undelta_bot):
mismos menús y mismas palabras clave de routing, con las correcciones del 8-oct.

Orden de resolución de cada mensaje (equivale a las prioridades del routing original):
  0. clave de inicio (solo si está configurada)
  1. comandos de sistema: menú, inicio, desvincular, baja, alta
  2. comando de salida: chau/chao/adiós/salir/finalizar
  3. palabras clave: carreras, oferta, planes, alumno, docente, ayuda, ...
  4. saludos / iniciar / empezar  → menú principal
  5. respuesta a una conversación en curso (opción de menú, DNI, código)
  6. texto libre → RAG
"""
import json
import os
import re
import secrets
import time

import math

from . import calendario, config, convlog, kb, llm, mailer, siu, store
from .carreras_util import duracion_legible

INST = os.path.join(config.DATA_DIR, "institucional")


def _json(n):
    with open(os.path.join(INST, n), encoding="utf-8") as f:
        return json.load(f)


CARRERAS = _json("carreras-undelta.json")
INGRESO = _json("ingreso-undelta.json")
LINKS = _json("links.json")
RECURSOS = _json("recursos-undelta.json")["recursos"]

EMOJI_INST = {"educacion_y_cultura": "📚", "gobernanza_y_asuntos_globales": "🌍", "tecnologia_y_produccion": "💻",
              "salud_y_bienestar": "🩺", "desarrollo_sostenible_y_turismo": "🌿", "innovacion_y_deportes": "🏅"}
AREAS = CARRERAS["areas"]
CARRERA_POR_ID = {c["id"]: (i, c) for i, a in enumerate(AREAS) for c in a["carreras"]}

SALUDO = "¡Hola! Soy Tincho, el asistente virtual de la UNDelta. ¿En qué te puedo ayudar?"
PIE_ESTUDIANTES = f"¿Dudas? Escribinos a {config.CONTACTO_ESTUDIANTES}."


def norm(s):
    return re.sub(r"[\s!.,¡¿?]+$|^[\s!.,¡¿?]+", "", kb.norm(s)).strip()


def opt(id_, label):
    return {"id": id_, "label": label}


MAIN = [opt("carreras", "🎓 Carreras"), opt("ingreso", "📝 Inscripciones"), opt("siu", "🆔 Consultas SIU"),
        opt("guia", "📚 Guía Estudiantes"), opt("contacto", "☎️ Contacto"),
        opt("preguntar", "💬 Preguntarle a Tincho")]
VOLVER = opt("main", "🏠 Menú principal")


# ───────────────────────── menús ─────────────────────────
def menu_main(st, prompt="Elegí una opción:"):
    st["menu"] = "main"
    return {"reply": prompt, "options": MAIN}


def menu_institutos(st):
    st["menu"] = "institutos"
    o = [opt(f"inst:{i}", f"{EMOJI_INST.get(a['id'], '🎓')} {a['nombre']}"[:24]) for i, a in enumerate(AREAS)]
    return {"reply": "Las carreras de la UNDelta están organizadas por *Institutos*. Elegí uno:",
            "options": o + [VOLVER]}


def menu_instituto(st, i, prefijo=""):
    a = AREAS[i]
    st["menu"] = f"inst:{i}"
    o = [opt(f"car:{c['id']}", c["nombre"].replace("Tecnicatura Universitaria", "Tec. Univ.")
             .replace("Licenciatura", "Lic.")[:24]) for c in a["carreras"]]
    nombres = "\n".join(f"- {c['nombre']}" for c in a["carreras"])
    return {"reply": f"{prefijo}*Instituto de {a['nombre']}*\n{nombres}\n\nElegí una carrera para ver el detalle:",
            "options": o + [opt("carreras", "⬅️ Otros institutos"), VOLVER]}


def menu_carrera(st, cid, prefijo=""):
    i, c = CARRERA_POR_ID[cid]
    st["menu"] = f"car:{cid}"
    ins = c.get("estadoInscripcion")
    return {"reply": prefijo or f"*{c['nombre']}*\nInstituto de {c['area']}. ¿Qué querés saber?",
            "options": [opt(f"cs:{cid}:sobre", "ℹ️ Sobre la carrera"), opt(f"cs:{cid}:perfil", "🎯 Perfil del graduado"),
                        opt(f"cs:{cid}:ins", "📝 Cómo inscribirme"),
                        opt(f"cs:{cid}:contacto", "✉️ Contactar al instituto"),
                        opt(f"inst:{i}", "⬅️ Volver a carreras de este Instituto"), VOLVER]}


def texto_sobre(c):
    t = [f"*{c['nombre']}*", f"Instituto de {c['area']}"]
    if c["id"] == "licenciatura-en-gestion-de-instituciones-educativas":
        t.append("Es un *Ciclo de Complementación Curricular*.")
    t += [f"🎓 Título: {c.get('tituloOtorgado')}",
          f"⏱ Duración: {duracion_legible(c.get('duracion'))}",
          f"🕒 Carga horaria: {c.get('cargaHoraria')}",
          f"🏫 Modalidad: {c.get('modalidad')} y gratuita"]
    if c.get("descripcion"):
        t.append("\n" + c["descripcion"])
    if c.get("planPdf"):
        t.append(f"\n📄 Plan de estudios: {c['planPdf']}")
    t.append(f"\n🔗 Más info: {c.get('url') or LINKS['carreras']}")
    return "\n".join(t)


def texto_perfil(c):
    p = c.get("perfil") or []
    if not p:
        return "Todavía no tengo cargado el perfil del graduado de esta carrera. Podés consultarlo en " + (c.get("url") or LINKS["carreras"])
    return "*Perfil del graduado/a*\nEl graduado/a de esta carrera podrá:\n" + "\n".join(f"- {x}" for x in p)


def texto_pasos():
    pasos = "\n".join(f"{i}. *{p['titulo']}*: {p['texto']}" for i, p in enumerate(INGRESO["pasos"], 1))
    return (f"*Cómo ingresar a la UNDelta*\n{INGRESO['inscripcion']['texto']} {INGRESO['gratuidad']}\n\n{pasos}\n\n"
            f"🔗 Preinscripción: {LINKS['preinscripcionSiu']}\n📄 Instructivo: {LINKS['instructivoSiu']}\n\n"
            f"{INGRESO['yaEstudiante']}\n{INGRESO['sinRecursosTecnologicos']}")


def texto_doc():
    s = INGRESO["sede"]
    docs = "\n".join(f"- {d}" for d in INGRESO["documentacion"])
    return (f"*Documentación que deberás acercar a nuestra sede de San Fernando*\n{docs}\n\n"
            f"{INGRESO['secundarioEnCurso']}\n{INGRESO['secundarioExtranjero']}\n\n"
            f"📍 {s['lugar']}: {s['direccion']}\n🕒 Atención {s['horario']}.")


def texto_cpu():
    c = INGRESO["cpu"]
    return (f"*{c['nombre']}*\n{c['descripcion']}\n\n*Ejes:*\n" + "\n".join(f"- {e}" for e in c["ejes"])
            + f"\n\n{c['modalidad']}\n⏰ {c['turnos']}\n📅 Inicio del CPU: {INGRESO['fechas']['inicioCPU']}. "
            f"Inicio de clases: {INGRESO['fechas']['inicioClases']}.\n\n*Pueden estar eximidos del CPU:*\n"
            + "\n".join(f"- {e}" for e in c["exenciones"]))


def texto_sede():
    s, c = INGRESO["sede"], INGRESO["contacto"]
    return (f"📍 *{s['lugar']}*\n{s['direccion']}\n🕒 Atención {s['horario']}\n"
            f"✉️ {c['email']}\n📱 WhatsApp {c['telefono']}\n🔗 {LINKS['contacto']}")


def menu_ingreso(st, prefijo=""):
    st["menu"] = "ingreso"
    return {"reply": prefijo or "📝 *Inscripciones*. ¿Qué querés saber?",
            "options": [opt("ing:pasos", "🪜 Cómo ingresar"), opt("ing:doc", "📄 Documentación"), opt("ing:cpu", "📘 CPU"),
                        opt("ing:sede", "📍 Sede y horarios"), opt("ing:cal", "🗓 Calendario académico"),
                        opt("carreras", "🎓 Ver carreras"), VOLVER]}


def menu_guia(st):
    st["menu"] = "guia"
    return {"reply": "📚 *Guía Estudiantes*. Elegí un recurso:",
            "options": [opt(f"rec:{r['id']}", f"📎 {r['nombre']}"[:24]) for r in RECURSOS] + [VOLVER]}


# ───────────────────────── SIU ─────────────────────────
def menu_siu_alumno(st):
    st["menu"] = "siu_alumno"
    return {"reply": "✅ Identidad verificada. ¿Qué querés consultar?",
            "options": [opt("sa:cursadas", "📚 Mis materias"), opt("sa:mesas", "📝 Mis mesas de examen"),
                        opt("sa:resumen", "📊 Mi resumen académico"), opt("desvincular", "🔒 Cerrar sesión"), VOLVER]}


def menu_siu_docente(st):
    st["menu"] = "siu_docente"
    return {"reply": "✅ Identidad verificada (docente). ¿Qué querés consultar?",
            "options": [opt("sd:comisiones", "📚 Mis comisiones"), opt("desvincular", "🔒 Cerrar sesión"), VOLVER]}


def no_identificar_activo():
    """El modo sin verificación solo rige si el bot está protegido por la clave de inicio."""
    return bool(config.NO_IDENTIFICAR and config.CLAVE_INICIO)


def _identidad_vigente(st):
    idn = st.get("identity")
    if not idn:
        return None
    now = time.time()
    if now - idn["ult"] > config.IDENTITY_TTL_SECONDS or now - idn["desde"] > config.IDENTITY_MAX_SECONDS:
        st.pop("identity", None)
        return None
    idn["ult"] = now
    return idn


def iniciar_siu(st, sid, rol=None):
    """Entrada a 'Consultas SIU' / 'alumno' / 'docente'."""
    if not siu.habilitado() or not (mailer.configurado() or config.SIU_MOCK or no_identificar_activo()):
        return {"reply": "Las consultas personales del SIU todavía no están habilitadas en este canal. "
                         f"Mientras tanto podés ingresar a la Autogestión: {LINKS['autogestionSiu']}\n{PIE_ESTUDIANTES}",
                "options": [VOLVER]}
    idn = _identidad_vigente(st)
    if idn:
        return _menu_por_rol(st, idn, rol)
    st["ask"], st["menu"], st["rol_pedido"] = "dni", None, rol
    return {"reply": "Para ver tus datos necesito verificar que sos vos. 🔐\n"
                     "Escribí tu número de documento (sin puntos, por ej.: 31075330).\n"
                     "Te voy a mandar un código al correo que tenés registrado en el SIU.",
            "options": [opt("main", "Cancelar")]}


def _menu_por_rol(st, idn, rol=None):
    roles = [r for r, k in (("alumno", "persona"), ("docente", "docente")) if idn.get(k)]
    if rol in roles:
        roles = [rol]
    if len(roles) == 1:
        return menu_siu_alumno(st) if roles[0] == "alumno" else menu_siu_docente(st)
    st["menu"] = "siu_rol"
    return {"reply": "Tenés perfil de alumno/a y de docente. ¿Con cuál querés ingresar?",
            "options": [opt("rol:alumno", "🎓 Alumno/a"), opt("rol:docente", "🧑‍🏫 Docente"), VOLVER]}


def _recibir_dni(st, sid, ip, texto):
    dni = re.sub(r"[.\s]", "", texto)
    if not re.fullmatch(r"\d{6,9}", dni):
        return {"reply": "Eso no parece un número de documento (6 a 9 dígitos, sin puntos ni espacios). Probá de nuevo o tocá Cancelar.",
                "options": [opt("main", "Cancelar")]}
    dh = store.hmac_hex("dni:" + dni)
    if not (store.hit(f"otp-ip:{ip}", config.OTP_MAX_SENDS_PER_IP_HOUR, 3600)
            and store.hit(f"otp-doc:{dh}", config.OTP_MAX_SENDS_PER_DOC_HOUR, 3600)):
        store.auditar(sid, "otp_limite")
        st["ask"] = None
        return {"reply": "Hiciste demasiados intentos de verificación. Esperá una hora y volvé a intentar, "
                         f"o escribí a {config.CONTACTO_ESTUDIANTES}.", "options": [VOLVER]}
    contexto = None
    try:
        ident = siu.buscar_identidad(dni)
        if (ident["persona"] or ident["docente"]) and ident["email"]:
            code = f"{secrets.randbelow(10**6):06d}"
            if config.SIU_MOCK and not mailer.configurado():
                print(f"[tincho][MOCK] código para sesión {sid[:6]}: {code}")  # nunca va al cliente
            else:
                mailer.enviar_codigo(ident["email"], code, config.OTP_TTL_SECONDS // 60)
            store.guardar_otp(sid, dh, code, {"persona": ident["persona"], "docente": ident["docente"]})
            contexto = True
        store.auditar(sid, "otp_enviado" if contexto else "otp_sin_envio")
    except (siu.SiuError, Exception) as e:  # SIU caído, SMTP caído, etc.
        store.auditar(sid, "otp_error", type(e).__name__)
        st["ask"] = None
        return {"reply": "No pude completar la verificación en este momento. Probá de nuevo en un rato "
                         f"o escribí a {config.CONTACTO_ESTUDIANTES}.", "options": [VOLVER]}
    st["ask"] = "otp"
    # Respuesta idéntica exista o no el documento (evita enumerar personas).
    return {"reply": "Si el documento corresponde a una persona registrada y tiene un correo cargado en el SIU, "
                     f"te acabo de enviar un código de 6 dígitos (vence en {config.OTP_TTL_SECONDS // 60} minutos).\n"
                     f"Escribilo acá. Si no te llega, revisá spam o escribí a {config.CONTACTO_ESTUDIANTES}.",
            "options": [opt("main", "Cancelar")]}


def _recibir_dni_sinid(st, sid, ip, texto):
    """Modo 'no identificar': busca por DNI y entra sin código. Queda auditado."""
    dni = re.sub(r"[.\s]", "", texto)
    if not re.fullmatch(r"\d{6,9}", dni):
        return {"reply": "Eso no parece un número de documento (6 a 9 dígitos, sin puntos ni espacios).",
                "options": [opt("main", "Cancelar")]}
    if not store.hit(f"sinid-ip:{ip}", 20, 3600):
        st["ask"] = None
        return {"reply": "Hiciste demasiados intentos. Esperá un rato y volvé a probar.", "options": [VOLVER]}
    try:
        ident = siu.buscar_identidad(dni)
    except siu.SiuError as e:
        store.auditar(sid, "sinid_error", str(e))
        st["ask"] = None
        return {"reply": "El SIU no me respondió en este momento. Probá de nuevo en un rato.", "options": [VOLVER]}
    st["ask"] = None
    if not (ident["persona"] or ident["docente"]):
        store.auditar(sid, "sinid_no_encontrado")
        return {"reply": "No encontré ese documento en el SIU. Revisalo y escribí *no identificar* para probar de nuevo.",
                "options": [VOLVER]}
    now = time.time()
    st["identity"] = {"persona": ident["persona"], "docente": ident["docente"], "desde": now, "ult": now, "sin_verificar": True}
    store.auditar(sid, "sinid_ingreso")
    return _menu_por_rol(st, st["identity"], st.pop("rol_pedido", None))


def _recibir_otp(st, sid, texto):
    code = re.sub(r"\s", "", texto)
    if not re.fullmatch(r"\d{6}", code):
        return {"reply": "El código tiene 6 dígitos. Escribilo de nuevo o tocá Cancelar.", "options": [opt("main", "Cancelar")]}
    estado, ctx = store.verificar_otp(sid, code)
    store.auditar(sid, "otp_" + estado)
    if estado == "ok":
        now = time.time()
        st["identity"] = {"persona": ctx["persona"], "docente": ctx["docente"], "desde": now, "ult": now}
        st["ask"] = None
        return _menu_por_rol(st, st["identity"], st.pop("rol_pedido", None))
    if estado == "invalido":
        return {"reply": "Ese código no es correcto. Probá de nuevo.", "options": [opt("main", "Cancelar")]}
    st["ask"] = None
    return {"reply": "No pude verificar tu identidad (código incorrecto, vencido o sin intentos). "
                     "Escribí *siu* para empezar de nuevo.", "options": [VOLVER]}


def _accion_siu(st, sid, accion):
    idn = _identidad_vigente(st)
    if not idn:
        st["menu"] = None
        return {"reply": "Tu sesión venció por seguridad. Escribí *siu* para verificarte de nuevo.", "options": [VOLVER]}
    try:
        if accion == "sa:cursadas" and idn.get("persona"):
            txt = siu.texto_cursadas(siu.cursadas(idn["persona"]))
        elif accion == "sa:mesas" and idn.get("persona"):
            txt = siu.texto_mesas(siu.mesas(idn["persona"]))
        elif accion == "sa:resumen" and idn.get("persona"):
            txt = siu.texto_resumen(siu.resumen(idn["persona"]))
        elif accion == "sd:comisiones" and idn.get("docente"):
            txt = siu.texto_comisiones_docente(siu.comisiones_docente(idn["docente"]))
        else:
            return _menu_por_rol(st, idn)
        store.auditar(sid, "siu_consulta", accion)
    except siu.SiuError as e:
        store.auditar(sid, "siu_error", str(e))
        txt = "El SIU no me respondió en este momento. Probá de nuevo en un rato."
    r = menu_siu_alumno(st) if accion.startswith("sa:") else menu_siu_docente(st)
    r["reply"] = txt + "\n\n¿Querés consultar algo más?"
    return r


def desvincular(st, sid):
    st.pop("identity", None)
    st["ask"] = None
    store.auditar(sid, "desvincular")
    r = menu_main(st, "🔒 Cerré tu sesión y borré la verificación de identidad. ¿Algo más?")
    return r


# ───────────────────────── palabras clave ─────────────────────────
# Mismas palabras clave que el routing del bot de WhatsApp (prioridad 50) + sistema (100).
SALUDOS = re.compile(r"^(hola|buenas|buen dia|buenos dias|buenas tardes|buenas noches|iniciar|empezar|menu|inicio)$")
SALIDA = re.compile(r"^(chau|chao|adios|salir|finalizar)$")


def comando(st, sid, t):
    """Devuelve respuesta si `t` (normalizado) es un comando/palabra clave; si no, None."""
    if t in ("menu", "inicio"):
        st["ask"] = None
        return menu_main(st, SALUDO if t == "inicio" else "Elegí una opción:")
    if t == "desvincular":
        return desvincular(st, sid)
    if t in ("baja", "alta"):
        return {"reply": "Tincho web no envía avisos ni suscripciones, así que no hay nada para dar de "
                         + ("baja." if t == "baja" else "alta.") + " Escribí *menú* para ver las opciones.",
                "options": [VOLVER]}
    if SALIDA.match(t):
        store.borrar_sesion(sid)
        st.clear()
        st["cerrada"] = True
        return {"reply": "¡Chau! Cerré la conversación y la verificación de identidad. Cuando quieras, escribime de nuevo. 👋",
                "options": [opt("main", "🏠 Empezar de nuevo")]}
    if t in ("carreras", "oferta", "planes"):
        st["ask"] = None
        return menu_institutos(st)
    if t in ("no identificar", "demo") and no_identificar_activo() and siu.habilitado():
        st["ask"], st["menu"] = "dni_sinid", None
        return {"reply": "Modo de prueba: consulta sin verificar identidad. Escribí el número de documento "
                         "(sin puntos, por ej.: 31075330).", "options": [opt("main", "Cancelar")]}
    if t in ("alumno", "docente", "siu", "consultas siu", "mis materias"):
        return iniciar_siu(st, sid, rol=t if t in ("alumno", "docente") else None)
    if t in ("ayuda", "guia", "guia estudiantes", "herramientas", "instructivo"):
        st["ask"] = None
        return menu_guia(st)
    if t in ("inscripcion", "inscripciones", "ingreso", "ingresar", "cpu", "documentacion", "calendario", "calendario academico"):
        st["ask"] = None
        if t.startswith("calendario"):
            return menu_ingreso(st, calendario.texto_completo() + "\n\n¿Algo más?")
        if t == "cpu":
            return menu_ingreso(st, texto_cpu() + "\n\n¿Algo más?")
        if t == "documentacion":
            return menu_ingreso(st, texto_doc() + "\n\n¿Algo más?")
        return menu_ingreso(st)
    if t == "contacto":
        st["ask"] = None
        return menu_main(st, texto_sede())
    if SALUDOS.match(t):
        st["ask"] = None
        return menu_main(st, SALUDO)
    return None


# ───────────────────────── opciones de menú ─────────────────────────
def opcion(st, sid, oid):
    """Ejecuta el id de una opción de menú. None si el id no existe."""
    st["ask"] = None  # elegir una opción cancela cualquier pregunta pendiente (DNI/código)
    if oid == "main":
        return menu_main(st)
    if oid == "carreras":
        return menu_institutos(st)
    if oid == "ingreso":
        return menu_ingreso(st)
    if oid == "siu":
        return iniciar_siu(st, sid)
    if oid == "guia":
        return menu_guia(st)
    if oid == "contacto":
        return menu_main(st, texto_sede())
    if oid == "preguntar":
        st["menu"] = None
        return {"reply": "Contame qué querés saber sobre la UNDelta (carreras, ingreso, trámites…) y te respondo. 💬",
                "options": [VOLVER]}
    if oid == "desvincular":
        return desvincular(st, sid)
    if oid.startswith("inst:"):
        i = int(oid[5:])
        return menu_instituto(st, i) if 0 <= i < len(AREAS) else None
    if oid.startswith("car:"):
        return menu_carrera(st, oid[4:]) if oid[4:] in CARRERA_POR_ID else None
    if oid.startswith("cs:"):
        _, cid, sec = oid.split(":")
        if cid not in CARRERA_POR_ID:
            return None
        _, c = CARRERA_POR_ID[cid]
        txt = {"sobre": lambda: texto_sobre(c), "perfil": lambda: texto_perfil(c),
               "ins": lambda: texto_pasos(),
               "contacto": lambda: f"✉️ Instituto de {c['area']}: {c.get('contacto')}\n{PIE_ESTUDIANTES}"}[sec]()
        return menu_carrera(st, cid, txt + "\n\n¿Qué más querés saber de esta carrera?")
    if oid.startswith("ing:"):
        k = oid[4:]
        txt = {"pasos": texto_pasos, "doc": texto_doc, "cpu": texto_cpu, "sede": texto_sede,
               "cal": calendario.texto_completo}.get(k)
        return menu_ingreso(st, txt() + "\n\n¿Algo más?") if txt else None
    if oid.startswith("rec:"):
        r = next((r for r in RECURSOS if r["id"] == oid[4:]), None)
        if not r:
            return None
        out = menu_guia(st)
        out["reply"] = r["texto"] + (f"\n🔗 {LINKS[r['link']]}" if r.get("link") in LINKS else "") + "\n\n¿Algo más?"
        return out
    if oid.startswith("rol:"):
        idn = _identidad_vigente(st)
        return _menu_por_rol(st, idn, oid[4:]) if idn else iniciar_siu(st, sid)
    if oid.startswith(("sa:", "sd:")):
        return _accion_siu(st, sid, oid)
    return None


def _match_opcion(t, opciones):
    for o in opciones:
        etiqueta = norm(re.sub(r"^[^\w]+", "", o["label"]))
        if t == norm(o["id"]) or t == norm(o["label"]) or (etiqueta and t == etiqueta):
            return o["id"]
    return None


def _opciones_pendientes(st):
    """Reconstruye las opciones del menú pendiente (para aceptar que la persona las escriba)."""
    m = st.get("menu")
    if not m:
        return []
    tmp = {}
    try:
        r = {"main": lambda: menu_main(tmp), "institutos": lambda: menu_institutos(tmp), "ingreso": lambda: menu_ingreso(tmp),
             "guia": lambda: menu_guia(tmp), "siu_alumno": lambda: menu_siu_alumno(tmp),
             "siu_docente": lambda: menu_siu_docente(tmp)}.get(m)
        if r is None and m.startswith("inst:"):
            return menu_instituto(tmp, int(m[5:]))["options"]
        if r is None and m.startswith("car:"):
            return menu_carrera(tmp, m[4:])["options"]
        if r is None and m == "siu_rol":
            return [opt("rol:alumno", "Alumno/a"), opt("rol:docente", "Docente")]
        return r()["options"] if r else []
    except (KeyError, ValueError):
        return []


# ───────────────────────── punto de entrada ─────────────────────────
def limpiar(texto):
    t = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", texto or "")
    return t.strip()[: config.MAX_MESSAGE_CHARS]


def _tipo_opcion(oid):
    return "siu_consulta" if oid.startswith(("sa:", "sd:")) else "opcion"


def procesar(sid, ip, texto, option_id=None):
    """Procesa un mensaje, lo registra en el histórico (convlog) y devuelve la respuesta."""
    r, tipo, usuario, sensible = _procesar(sid, ip, texto, option_id)
    fuentes = r.pop("_fuentes", None)  # claves internas: nunca llegan al navegador
    convlog.registrar(sid, tipo, usuario, r.get("reply", ""), fuentes, r.get("options"), sensible)
    return r


def _procesar(sid, ip, texto, option_id=None):
    """Devuelve (respuesta, tipo de respuesta, texto a registrar, ¿es dato sensible?)."""
    st = store.cargar_estado(sid)
    texto = limpiar(texto)
    if not st:
        st = {"hist": []}
    st.pop("cerrada", None)

    # 0. clave de inicio (modo testing, opcional)
    if config.CLAVE_INICIO and not st.get("activado"):
        if norm(texto) == norm(config.CLAVE_INICIO):
            st["activado"] = True
            r, usuario = menu_main(st, SALUDO), texto
        else:
            r = {"reply": "Tincho está en período de pruebas. Ingresá la clave de acceso para empezar.", "options": []}
            usuario = convlog.ANTES_DE_CLAVE if texto else ""
        store.guardar_estado(sid, st)
        # Antes de la clave se registra solo "clave" (acierto) o "sistema" (aviso), sin el texto escrito.
        return r, ("clave" if st.get("activado") else "sistema"), usuario, False

    r, tipo, usuario, sensible = None, "sistema", texto, False
    if option_id:  # clic en un botón: el id viaja explícito (se valida contra el menú pendiente)
        validos = {o["id"] for o in _opciones_pendientes(st)} | {"main", "desvincular"}
        if option_id in validos:
            r, tipo, usuario = opcion(st, sid, option_id), _tipo_opcion(option_id), f"[botón] {option_id}"
    if r is None and not texto:
        r = menu_main(st, SALUDO) if not st.get("menu") else None
        tipo, usuario = "inicio", ""
        if r is None:
            r = {"reply": "Escribime tu consulta o elegí una opción del menú.", "options": _opciones_pendientes(st) or MAIN}
    if r is None:
        t = norm(texto)
        r = comando(st, sid, t)
        if r is not None:
            tipo = "comando"
    if r is None and st.get("ask") == "dni_sinid":
        r, tipo, sensible = _recibir_dni_sinid(st, sid, ip, texto), "siu_verificacion", True
    if r is None and st.get("ask") == "dni":
        r, tipo, sensible = _recibir_dni(st, sid, ip, texto), "siu_verificacion", True
    if r is None and st.get("ask") == "otp":
        r, tipo, sensible = _recibir_otp(st, sid, texto), "siu_verificacion", True
    if r is None:
        oid = _match_opcion(norm(texto), _opciones_pendientes(st))
        if oid:
            r, tipo = opcion(st, sid, oid), _tipo_opcion(oid)
    if r is None:
        r = _texto_libre(st, sid, ip, texto)
        tipo = r.pop("_tipo")

    if not st.get("cerrada"):
        store.guardar_estado(sid, st)
    return r, tipo, usuario, sensible


def _texto_libre(st, sid, ip, texto):
    if llm.es_jailbreak(texto):
        store.auditar(sid, "jailbreak")
        return {"reply": llm.REPLY_JAILBREAK, "options": [VOLVER], "_tipo": "jailbreak"}
    # Calendario académico: las fechas se responden citando la fila de la tabla, sin pasar por el LLM.
    if calendario.es_pregunta_de_calendario(texto):
        resp = calendario.responder(texto)
        if resp:
            st["menu"] = "main"
            return {"reply": resp, "options": [opt("ing:cal", "🗓 Ver calendario completo"), VOLVER],
                    "_tipo": "calendario", "_fuentes": [calendario.URL_PAGINA]}
    ok, espera = store.hit_all([
        (f"llm-s-min:{sid}", config.LLM_SID_MIN, 60), (f"llm-s-h:{sid}", config.LLM_SID_HORA, 3600),
        (f"llm-s-d:{sid}", config.LLM_SID_DIA, 86400),
        (f"llm-min:{ip}", config.LLM_IP_MIN, 60), (f"llm-h:{ip}", config.LLM_IP_HORA, 3600),
        (f"llm-d:{ip}", config.LLM_IP_DIA, 86400)])
    if not ok:
        store.auditar(sid, "limite_llm", f"espera {int(espera)}s")
        m = max(1, math.ceil(espera / 60))
        return {"reply": "Hiciste muchas consultas seguidas. Probá de nuevo en "
                         + ("un minuto" if m == 1 else f"{m} minutos") + ". 🌿",
                "options": [VOLVER], "_tipo": "limite"}
    hist = st.setdefault("hist", [])
    texto_resp, fuentes = llm.responder(texto, hist)
    hist += [{"role": "user", "content": texto[:250]}, {"role": "assistant", "content": texto_resp[:250]}]
    st["hist"] = hist[-6:]
    store.auditar(sid, "rag", f"{len(fuentes)} fuentes")
    st["menu"] = "main"
    return {"reply": texto_resp, "options": [opt("main", "🏠 Menú principal"), opt("ingreso", "📝 Inscripciones"),
                                              opt("carreras", "🎓 Carreras")],
            "_tipo": "rag_sin_dato" if texto_resp == llm.REPLY_SIN_DATO else "rag", "_fuentes": fuentes}
