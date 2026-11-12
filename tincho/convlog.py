"""Histórico de conversaciones de Tincho (equivalente a web_interactions.csv de Deltix, en SQLite).

Archivo propio `conversaciones.db`, separado de `tincho.db`, en modo de journal DELETE (no WAL):
es un único archivo consistente que se puede descargar por la API de PythonAnywhere
(ver dashboard/sync_db.py) y no depende de memoria compartida en discos de red.

Privacidad:
  - NO se guarda el contenido de los pasos DNI / código de verificación, la clave de inicio
    ni las respuestas del SIU (datos personales del alumno): se reemplazan por marcadores.
  - En el texto libre de la persona se enmascaran números largos (posibles DNI/teléfonos) y correos.
  - `sesion` es un HMAC corto del id de sesión: nunca parte de la cookie real.
  - Retención: sin borrado automático (decisión del equipo); `purgar(dias)` queda para uso manual.

`registrar` nunca lanza excepciones: si el log falla, el bot sigue respondiendo.
"""
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone

from . import config, store

try:  # hora argentina (el server de PythonAnywhere corre en UTC)
    from hora_local import ahora
except ImportError:  # pragma: no cover
    def ahora():
        return datetime.now(timezone(timedelta(hours=-3))).replace(tzinfo=None)

MAX_USUARIO = 500
MAX_BOT = 1500
SENSIBLE = "[dato sensible omitido]"
SIU_OMITIDA = "[respuesta SIU omitida]"
ANTES_DE_CLAVE = "[antes de la clave]"

TIPOS = ("inicio", "clave", "opcion", "comando", "siu_verificacion", "siu_consulta",
         "rag", "rag_sin_dato", "calendario", "jailbreak", "limite", "sistema")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS mensajes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    sesion TEXT NOT NULL,
    tipo TEXT NOT NULL,
    usuario TEXT,
    bot TEXT,
    fuentes TEXT,
    opciones TEXT
);
CREATE INDEX IF NOT EXISTS ix_mensajes_ts ON mensajes(ts);
CREATE INDEX IF NOT EXISTS ix_mensajes_sesion ON mensajes(sesion);
"""

_NUMEROS = re.compile(r"\b\d{1,3}(?:[.\s]\d{3}){2,}\b|\d{6,}")
_CORREOS = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def ruta():
    return os.path.join(config.VAR_DIR, "conversaciones.db")


def _abrir():
    os.makedirs(config.VAR_DIR, exist_ok=True)
    con = sqlite3.connect(ruta(), timeout=10)
    con.execute("PRAGMA journal_mode=DELETE")
    con.executescript(_SCHEMA)
    return con


def enmascarar(texto):
    t = _CORREOS.sub("[correo]", texto or "")
    return _NUMEROS.sub("[número]", t)


def sesion_id(sid):
    return store.hmac_hex("sesion:" + (sid or ""))[:10]


def registrar(sid, tipo, usuario="", bot="", fuentes=None, opciones=None, sensible=False):
    try:
        if sensible:
            usuario = SENSIBLE
        elif tipo == "clave":
            usuario = "[clave]"
        else:
            usuario = enmascarar(usuario)
        if tipo == "siu_consulta":
            bot = SIU_OMITIDA
        con = _abrir()
        try:
            con.execute(
                "INSERT INTO mensajes(ts, sesion, tipo, usuario, bot, fuentes, opciones) VALUES(?,?,?,?,?,?,?)",
                (ahora().strftime("%Y-%m-%d %H:%M:%S"), sesion_id(sid), tipo,
                 (usuario or "")[:MAX_USUARIO], (bot or "")[:MAX_BOT],
                 "\n".join(fuentes or []), "|".join(o["label"] for o in (opciones or []))),
            )
            con.commit()
        finally:
            con.close()
    except Exception as e:  # el log jamás debe romper una conversación
        print(f"[tincho] convlog error: {type(e).__name__}")


def purgar(dias):
    """Borra mensajes de más de `dias` días. Uso manual; devuelve cuántos se borraron."""
    limite = (ahora() - timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S")
    con = _abrir()
    try:
        n = con.execute("DELETE FROM mensajes WHERE ts < ?", (limite,)).rowcount
        con.commit()
        con.execute("VACUUM")
        return n
    finally:
        con.close()
