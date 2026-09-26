# -*- coding: utf-8 -*-
"""
enviar_saludo_vuelta.py — Saludo de reencuentro por Telegram, por unica vez.

Aprovecha la caida del 22 al 26 de septiembre de 2026 para volver a aparecer en
el chat de la gente que uso el bot alguna vez.

Manda DOS mensajes distintos segun hace cuanto escribio cada uno:

  inactivos (no escriben desde hace DIAS_INACTIVIDAD dias o mas)
      se presenta de cero, "te acordas de mi?", cuenta que sumamos cosas y
      ofrece el menu completo.

  activos (escribieron hace poco)
      ya saben quien es: solo avisa que estuvo caido y deja el teclado a mano.
      Preguntarles "te acordas de mi?" a alguien que lo uso ayer suena raro.

Se manda en burbujas separadas con el bot "tipeando" entre una y otra, en vez de
un parrafo solo: se lee como una conversacion y no como un comunicado.

CORRE EN PYTHONANYWHERE (usa tokens.py, user_experience.csv, tg_interactions.csv
y el menu real de deltix_funciones, asi el menu nunca se desincroniza del /menu).

    python3 enviar_saludo_vuelta.py

POR UNICA VEZ: cada envio exitoso se anota en envios_masivos.csv. Si volves a
correr el script, esa persona se saltea. Podes cortarlo a la mitad y retomar sin
que nadie reciba dos veces.

SEGURIDAD: simula por defecto. Sin argumentos imprime a quien le mandaria y como
se veria cada variante, sin mandar nada. Para mandar de verdad hay que pedirlo
explicitamente:

    python3 enviar_saludo_vuelta.py --enviar

La bandera existe para que correr el script de memoria, o por accidente, nunca
mande nada: son 256 personas.
"""

import argparse
import asyncio
import csv
import datetime
import os
import sys

import pandas as pd
from telegram import Bot
from telegram.constants import ChatAction
from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError

from tokens import telegram_token
from deltix_funciones import generate_main_menu, main_menu_keyboard

# Al redirigir la salida a un archivo (nohup … > saludo.log) Python bufferea
# stdout en bloques de ~8 KB, asi que el log queda vacio varios minutos y parece
# que el envio no arranco. Con line buffering cada linea aparece al instante.
try:
    sys.stdout.reconfigure(line_buffering=True)
except AttributeError:      # python < 3.7
    pass

# ── Configuración ─────────────────────────────────────────────────────────────

DRY_RUN = True      # Se apaga solo con --enviar. No lo cambies acá.

# Identifica este envío en el registro. Si algún día mandás otro saludo, cambiá
# este id: el registro es por (envio_id, user_id), así que un id nuevo permite
# volver a escribirle a la misma gente sin borrar el historial.
ENVIO_ID = "saludo_vuelta_2026_09"

# A quién se le escribe. La variante del mensaje NO depende de esto: se decide
# persona por persona según su última actividad.
#   "todos"     -> los 256 registrados, cada uno con la variante que le toca
#   "inactivos" -> solo los que no escriben desde hace DIAS_INACTIVIDAD
#   "activos"   -> solo los que escribieron hace poco
#   "prueba"    -> solo los IDs de PRUEBA_IDS
# Se puede pisar desde la linea de comandos con --audiencia.
AUDIENCIA = "todos"
DIAS_INACTIVIDAD = 15
PRUEBA_IDS = []     # poné acá tu propio User ID para la primera prueba

# Telegram tolera ~30 mensajes/segundo, pero para un envío masivo conviene ir
# lento: son varios mensajes por persona y no hay ningún apuro.
PAUSA_ENTRE_USUARIOS = 2.0

base_path = '/home/facundol/deltix/' if os.path.exists('/home/facundol/deltix/') else ''
UE_PATH = base_path + 'user_experience.csv'
TG_LOG_PATH = base_path + 'tg_interactions.csv'
REGISTRO_PATH = base_path + 'envios_masivos.csv'
REGISTRO_HEADERS = ["envio_id", "user_id", "nombre", "variante", "timestamp", "estado"]

# Estados que cuentan como "ya resuelto": no se reintenta.
ESTADOS_FINALES = {"enviado", "bloqueado", "inexistente"}

# ── El mensaje ────────────────────────────────────────────────────────────────

CAIDA = ("Estuve unos días sin funcionar, pero ya estoy de vuelta, "
         "enterito y chapoteando en el pantanix 🦟")


def burbujas(nombre, variante):
    """Las burbujas en orden, como (texto, teclado).

    La última de cada variante lleva el teclado, que es lo que le deja los
    botones a mano en el chat.
    """
    hola = "Hola %s!" % nombre if nombre else "Hola!"

    if variante == "activo":
        # Ya sabe quién es Deltix: no se presenta ni le ofrece novedades.
        return [
            ("%s 🐹 %s" % (hola, CAIDA), None),
            ("Perdón por la ausencia! Si necesitás algo, acá abajo tenés todo 👇",
             main_menu_keyboard),
        ]

    return [
        ("%s 🐹 Soy Deltix, el bot del humedal… ¿te acordás de mí?" % hola, None),
        (CAIDA, None),
        ("En el último tiempo sumamos varias funcionalidades, "
         "te invito a que las chusmees", None),
        (generate_main_menu(), main_menu_keyboard),
    ]


def demora(texto):
    """Cuánto 'tipea' el bot antes de soltar la burbuja.

    Proporcional al largo, para que las cortas salgan rápido y las largas den
    tiempo a leer la anterior. Con techo, para no aburrir en el menú.
    """
    return min(0.6 + len(texto) / 55.0, 3.0)


# ── Destinatarios ─────────────────────────────────────────────────────────────

def nombre_de(row):
    fn = str(row.get("First Name", "")).strip()
    if fn and fn.lower() != "nan":
        return fn.split()[0]
    un = str(row.get("Username", "")).strip()
    if un and un.lower() != "nan":
        return "@" + un
    return ""


def ya_enviados():
    """user_ids que ya tienen un estado final PARA ESTE ENVIO_ID.

    Filtra por envio_id acá y no en el llamador, para que el contador que se
    imprime no mezcle destinatarios de otros envíos guardados en el mismo csv.
    """
    hechos = set()
    if not os.path.exists(REGISTRO_PATH):
        return hechos
    with open(REGISTRO_PATH, newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            if fila.get("envio_id") != ENVIO_ID:
                continue
            if (fila.get("estado") or "").split(":")[0].strip() in ESTADOS_FINALES:
                hechos.add(str(fila.get("user_id")))
    return hechos


def anotar(uid, nombre, variante, estado):
    """Anota una fila YA MISMO. Escribir de a una es lo que hace que el script
    sea interrumpible sin que nadie reciba el mensaje dos veces."""
    nuevo = not os.path.exists(REGISTRO_PATH)
    with open(REGISTRO_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(REGISTRO_HEADERS)
        w.writerow([ENVIO_ID, uid, nombre, variante,
                    datetime.datetime.now().isoformat(timespec="seconds"), estado])


def activos_recientes():
    """user_ids que escribieron en los últimos DIAS_INACTIVIDAD días.

    Los timestamps del log están en UTC igual que datetime.now() en
    PythonAnywhere, así que la comparación es consistente. Quien nunca aparece
    en el log cuenta como inactivo, que es lo correcto: son los que se
    registraron y no volvieron, o los de antes de que el log existiera.
    """
    if not os.path.exists(TG_LOG_PATH):
        return set()
    tg = pd.read_csv(TG_LOG_PATH)
    tg["timestamp"] = pd.to_datetime(tg["timestamp"], errors="coerce")
    corte = datetime.datetime.now() - datetime.timedelta(days=DIAS_INACTIVIDAD)
    recientes = tg[tg["timestamp"] >= corte]["user_id"].dropna()
    return set(recientes.astype("int64").astype(str))


def destinatarios():
    """[(uid, nombre, variante)] pendientes, más cuántos ya recibieron."""
    ue = pd.read_csv(UE_PATH)
    ue = ue[pd.to_numeric(ue["User ID"], errors="coerce").notna()]
    ue["uid"] = ue["User ID"].astype("int64").astype(str)
    ue = ue.drop_duplicates(subset="uid", keep="last")

    recientes = activos_recientes()
    ue["variante"] = ue["uid"].apply(
        lambda u: "activo" if u in recientes else "inactivo")

    if AUDIENCIA == "prueba":
        ue = ue[ue["uid"].isin([str(x) for x in PRUEBA_IDS])]
    elif AUDIENCIA == "inactivos":
        ue = ue[ue["variante"] == "inactivo"]
    elif AUDIENCIA == "activos":
        ue = ue[ue["variante"] == "activo"]
    elif AUDIENCIA != "todos":
        raise SystemExit("AUDIENCIA invalida: %r" % AUDIENCIA)

    hechos = ya_enviados()
    filas = [(r["uid"], nombre_de(r), r["variante"]) for _, r in ue.iterrows()
             if r["uid"] not in hechos]
    return filas, len(hechos)


# ── Envío ─────────────────────────────────────────────────────────────────────

async def saludar(bot, uid, nombre, variante):
    for texto, teclado in burbujas(nombre, variante):
        await bot.send_chat_action(chat_id=int(uid), action=ChatAction.TYPING)
        await asyncio.sleep(demora(texto))
        await bot.send_message(chat_id=int(uid), text=texto,
                               parse_mode="HTML", reply_markup=teclado)


def mostrar_variantes(filas):
    ejemplo = {}
    for _, nombre, variante in filas:
        ejemplo.setdefault(variante, nombre)
    for variante in ("inactivo", "activo"):
        nombre = ejemplo.get(variante, "Guadalupe")
        n = sum(1 for _, _, v in filas if v == variante)
        print("\n" + "-" * 72)
        print("VARIANTE '%s' — %d destinatarios (ejemplo con %r)"
              % (variante, n, nombre or "sin nombre"))
        print("-" * 72)
        for i, (texto, teclado) in enumerate(burbujas(nombre, variante), 1):
            print("\n[%d] (tipea %.1fs)" % (i, demora(texto)))
            print(texto)
            if teclado:
                print("   + teclado: %s" % [[b.text for b in fila]
                                            for fila in teclado.keyboard])


async def main():
    filas, saltados = destinatarios()
    n_inact = sum(1 for _, _, v in filas if v == "inactivo")
    n_act = len(filas) - n_inact

    print("=" * 72)
    print("ENVIO: %s   AUDIENCIA: %s   DRY_RUN: %s" % (ENVIO_ID, AUDIENCIA, DRY_RUN))
    print("ya recibieron este envio (se saltean): %d" % saltados)
    print("pendientes: %d  (inactivos %d, activos %d)" % (len(filas), n_inact, n_act))
    print("=" * 72)
    for uid, nombre, variante in filas[:40]:
        print("   %-9s %-14s %s" % (variante, uid, nombre or "(sin nombre)"))
    if len(filas) > 40:
        print("   ... y %d mas" % (len(filas) - 40))

    mostrar_variantes(filas)

    if DRY_RUN:
        print("\n>>> Simulacion — no se envio nada.")
        print(">>> Si la lista esta bien, para mandar de verdad:")
        print(">>>   nohup python3 enviar_saludo_vuelta.py --enviar > saludo.log 2>&1 &")
        return
    if not filas:
        print("\nNo queda nadie pendiente.")
        return

    bot = Bot(token=telegram_token)
    ok = fallos = bloqueados = 0

    for n, (uid, nombre, variante) in enumerate(filas, 1):
        try:
            try:
                await saludar(bot, uid, nombre, variante)
            except RetryAfter as e:
                # Flood control: Telegram dice exactamente cuanto esperar.
                espera = int(getattr(e, "retry_after", 30)) + 1
                print("   … flood control, espero %ds" % espera)
                await asyncio.sleep(espera)
                await saludar(bot, uid, nombre, variante)
            estado = "enviado"
            ok += 1
            print("[%d/%d] ✓ %-9s %s (%s)"
                  % (n, len(filas), variante, nombre or "(sin nombre)", uid))
        except Forbidden:
            # Bloqueo al bot o borro la cuenta. No se reintenta nunca mas.
            estado, bloqueados = "bloqueado", bloqueados + 1
            print("[%d/%d] – %s bloqueo al bot" % (n, len(filas), uid))
        except BadRequest as e:
            estado = "inexistente: %s" % e
            bloqueados += 1
            print("[%d/%d] – %s chat inexistente (%s)" % (n, len(filas), uid, e))
        except (TelegramError, asyncio.TimeoutError, OSError) as e:
            # Error transitorio: queda anotado sin estado final y se reintenta
            # la proxima corrida.
            estado, fallos = "error: %s" % e, fallos + 1
            print("[%d/%d] ✗ %s -> %s" % (n, len(filas), uid, e))

        anotar(uid, nombre, variante, estado)
        if n < len(filas):
            await asyncio.sleep(PAUSA_ENTRE_USUARIOS)

    print("\n" + "=" * 72)
    print("enviados %d | bloqueados/inexistentes %d | errores a reintentar %d"
          % (ok, bloqueados, fallos))
    print("registro: %s" % REGISTRO_PATH)
    if fallos:
        print("Volve a correr el script para reintentar solo los %d que fallaron."
              % fallos)


def _leer_argumentos():
    p = argparse.ArgumentParser(
        description="Saludo de reencuentro por Telegram. Simula salvo --enviar.")
    p.add_argument("--enviar", action="store_true",
                   help="manda de verdad. Sin esta bandera solo simula.")
    p.add_argument("--audiencia", choices=["todos", "inactivos", "activos", "prueba"],
                   help="pisa AUDIENCIA para esta corrida (default: %s)" % AUDIENCIA)
    return p.parse_args()


if __name__ == "__main__":
    if sys.version_info < (3, 7):
        raise SystemExit("hace falta python 3.7+")
    _a = _leer_argumentos()
    if _a.enviar:
        DRY_RUN = False
    if _a.audiencia:
        AUDIENCIA = _a.audiencia
    asyncio.run(main())
