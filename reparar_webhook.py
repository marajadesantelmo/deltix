# -*- coding: utf-8 -*-
"""
Saca el webhook del bot de Telegram para que vuelva a funcionar el polling.

Por que existe esto: si alguien (o algo) registra un webhook en el bot, Telegram
deja de permitir getUpdates y el always-on task muere en loop con:

    telegram.error.Conflict: can't use getUpdates method while webhook is active

Este script lee el token de tokens.py (nunca lo imprime), borra el webhook y
muestra como quedo. Correrlo en PythonAnywhere DESPUES de poner el token nuevo
en tokens.py y ANTES de arrancar el always-on task:

    python3 reparar_webhook.py

Es idempotente: si no hay webhook, no rompe nada.
"""
import sys

import requests

from tokens import telegram_token

API = "https://api.telegram.org/bot%s" % telegram_token


def info():
    r = requests.get("%s/getWebhookInfo" % API, timeout=30)
    r.raise_for_status()
    return r.json().get("result", {})


def main():
    me = requests.get("%s/getMe" % API, timeout=30).json()
    if not me.get("ok"):
        print("ERROR: el token de tokens.py no es valido (getMe fallo).")
        print("       Revisa que pegaste el token nuevo completo, sin espacios.")
        return 1
    u = me["result"]
    print("bot: @%s (id=%s)" % (u.get("username"), u.get("id")))

    antes = info()
    url = antes.get("url") or ""
    if url:
        print("\nwebhook activo -> %s" % url)
        print("pending_update_count: %s" % antes.get("pending_update_count"))
        print("\nEste webhook es el que bloquea el polling. Lo borro.")
    else:
        print("\nNo hay webhook activo. Nada que borrar.")

    # drop_pending_updates descarta la cola que se acumulo mientras el webhook
    # estuvo puesto: son mensajes que ya fueron entregados a ese endpoint, no
    # queremos reprocesarlos al arrancar.
    r = requests.post(
        "%s/deleteWebhook" % API,
        data={"drop_pending_updates": "true"},
        timeout=30,
    )
    d = r.json()
    print("\ndeleteWebhook -> ok=%s %s" % (d.get("ok"), d.get("description", "")))

    despues = info()
    if despues.get("url"):
        print("\nATENCION: todavia figura un webhook -> %s" % despues["url"])
        print("Si el token viejo sigue vivo, alguien lo puede volver a poner:")
        print("revocalo en BotFather con /revoke antes de seguir.")
        return 1

    print("\nListo: sin webhook. Ya se puede arrancar el always-on task (main2.py).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
