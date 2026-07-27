"""
enviar_disculpas.py — Envía un mensaje de disculpa por Telegram a los usuarios que el bot
maltrató (respuestas del LLM con lenguaje despectivo) en las últimas semanas.

Corre en PythonAnywhere (usa tokens.py y tg_interactions.csv).

SEGURIDAD: por defecto DRY_RUN = True → solo imprime a quién le enviaría, sin mandar nada.
Revisá la lista de destinatarios y recién ahí poné DRY_RUN = False para enviar de verdad.
"""

import asyncio
import datetime
import pandas as pd
import nest_asyncio
from telegram import Bot
from tokens import telegram_token

nest_asyncio.apply()

# ── Configuración ─────────────────────────────────────────────────────────────
DRY_RUN = True   # ⚠️ Poné False SOLO cuando confirmes la lista de destinatarios.

MENSAJE = (
    "El equipo deltix detectó que nuestro bot estuvo muy mala onda en los últimos días "
    "con algunos usuarios. Ya hicimos los ajustes correspondientes y esperemos que no vuelva a suceder!"
)

TG_LOG_PATH = "/home/facundol/deltix/tg_interactions.csv"
UE_PATH     = "/home/facundol/deltix/user_experience.csv"
LOG_OUT     = "/home/facundol/deltix/disculpas_log.csv"

DIAS_ATRAS = 21  # ventana para buscar respuestas maltratadoras

# Marcadores de lenguaje despectivo / maltrato (lo que dijo el bot, en minúsculas)
MARCADORES = [
    "flaco", "boludeces", "bolud", "chabón", "chabon", "pelotud",
    "no soy chatgpt", "seguí tu camino", "segui tu camino",
    "no estoy para jueguitos", "no me hagas perder el tiempo",
    "no para boludeces", "no pierdas tiempo ni el mío", "no pierdas tiempo ni el mio",
]

# Destinatarios extra opcionales (por si querés sumar a alguien a mano): lista de User ID
DESTINATARIOS_EXTRA = []


def nombre_de(ue, uid):
    row = ue[ue["User ID"].astype(str) == str(uid)]
    if row.empty:
        return "(sin nombre)"
    fn = str(row["First Name"].values[0]).strip()
    un = str(row["Username"].values[0]).strip()
    if fn and fn.lower() != "nan":
        return fn
    if un and un.lower() != "nan":
        return "@" + un
    return "(sin nombre)"


def obtener_destinatarios():
    tg = pd.read_csv(TG_LOG_PATH)
    tg["timestamp"] = pd.to_datetime(tg["timestamp"], errors="coerce")
    corte = datetime.datetime.now() - datetime.timedelta(days=DIAS_ATRAS)
    tg = tg[tg["timestamp"] >= corte]

    def es_maltrato(txt):
        t = str(txt).lower()
        return any(m in t for m in MARCADORES)

    afectados = tg[tg["bot_reply"].apply(es_maltrato)]["user_id"].dropna().unique().tolist()
    # sumar extras y deduplicar preservando tipo
    ids = list(dict.fromkeys([str(x) for x in afectados] + [str(x) for x in DESTINATARIOS_EXTRA]))
    return ids, afectados


async def enviar():
    bot = Bot(token=telegram_token)
    ue = pd.read_csv(UE_PATH)
    ids, afectados = obtener_destinatarios()

    print("=" * 70)
    print("DESTINATARIOS DE LA DISCULPA (%d):" % len(ids))
    for uid in ids:
        print("  - %s (id %s)" % (nombre_de(ue, uid), uid))
    print("=" * 70)
    print("MENSAJE:\n  %s\n" % MENSAJE)

    if DRY_RUN:
        print(">>> DRY_RUN = True — no se envió nada. Revisá la lista y poné DRY_RUN = False para enviar.")
        return

    log_entries = []
    for uid in ids:
        try:
            await asyncio.wait_for(bot.send_message(int(uid), MENSAJE), timeout=30)
            estado = "enviado"
            print("✓ enviado a %s (id %s)" % (nombre_de(ue, uid), uid))
        except Exception as e:
            estado = "ERROR: %s" % e
            print("✗ error con id %s: %s" % (uid, e))
        log_entries.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "user_id": uid,
            "nombre": nombre_de(ue, uid),
            "estado": estado,
        })

    if log_entries:
        pd.DataFrame(log_entries).to_csv(LOG_OUT, mode="a", header=False, index=False)
        print("\nLog guardado en %s" % LOG_OUT)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(enviar())
