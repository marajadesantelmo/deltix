# -*- coding: utf-8 -*-
"""
Hora local de Argentina.

El server corre en UTC (es el default de PythonAnywhere), asi que datetime.now()
devuelve tres horas de mas. Eso llegaba hasta el usuario: build_llm_context le
pasa al LLM la "hora actual" para que compare contra la tabla de mareas, y con
la hora corrida el bot contestaba que recien habia pasado la pleamar de las
21:00 cuando en la isla eran las 18:44.

Argentina no cambia de hora desde 2009, asi que el offset fijo de -3 alcanza;
igual se intenta primero con zoneinfo, y el offset queda de respaldo por si el
server no tiene instalada la base de zonas horarias.

Las funciones devuelven datetime NAIVE a proposito: son reemplazo directo de
datetime.now() en formateos y restas, y mezclar naive con aware explota.
"""

from datetime import datetime, timedelta, timezone

ARG_OFFSET = timezone(timedelta(hours=-3))

try:
    from zoneinfo import ZoneInfo
    ARGENTINA = ZoneInfo("America/Argentina/Buenos_Aires")
except Exception:      # sin tzdata en el server
    ARGENTINA = ARG_OFFSET


def ahora():
    """Hora local de Argentina, naive. Reemplazo de datetime.now()."""
    return datetime.now(ARGENTINA).replace(tzinfo=None)


def hoy():
    """Fecha de hoy en Argentina."""
    return ahora().date()


def desde_timestamp(ts):
    """Un mtime de archivo leido en hora argentina, naive, para poder restarlo
    contra ahora() sin que la resta arrastre las 3 horas del server."""
    return datetime.fromtimestamp(ts, ARGENTINA).replace(tzinfo=None)
