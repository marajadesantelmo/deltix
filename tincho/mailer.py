"""Envío del código de verificación por correo (SMTP). Si no hay SMTP configurado, falla cerrado."""
import smtplib
import ssl
from email.message import EmailMessage

from . import config


def configurado():
    return bool(config.SMTP_USER and config.SMTP_PASSWORD)


def enviar_codigo(destino, codigo, minutos):
    if not configurado():
        raise RuntimeError("SMTP no configurado")
    m = EmailMessage()
    m["Subject"] = "Tu código de verificación de Tincho (UNDelta)"
    m["From"] = config.SMTP_FROM
    m["To"] = destino
    m.set_content(
        f"Tu código de verificación es: {codigo}\n\n"
        f"Vence en {minutos} minutos y sirve una sola vez.\n"
        "Si no lo pediste vos, ignorá este mensaje: nadie puede ver tus datos sin este código.\n"
        "La UNDelta nunca te va a pedir este código por otra vía.")
    with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, context=ssl.create_default_context(), timeout=20) as s:
        s.login(config.SMTP_USER, config.SMTP_PASSWORD)
        s.send_message(m)
