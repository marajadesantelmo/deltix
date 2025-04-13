"""
Twilio Configuration for Deltix WhatsApp Integration

This file contains the configuration settings for the Twilio WhatsApp integration.
"""

# Twilio WhatsApp Sandbox Mode
# Before going into production, you'll need to use a WhatsApp sandbox number
# provided by Twilio. The sandbox number is usually +1 415 523 8886
SANDBOX_MODE = True

# Default message when a user first contacts the bot
WELCOME_MESSAGE = """
¡Hola! Soy *Deltix, el bot del humedal* 🦫

Te doy la bienvenida a mi servicio de WhatsApp para el Delta del Paraná.

*¿Qué puedo hacer por vos?*

• Ver pronóstico de mareas - Escribe 'mareas'
• Ver pronóstico meteorológico - Escribe 'windguru'
• Consultar horarios de lanchas - Escribe 'colectivas'
• Ver memes isleños - Escribe 'memes'
• Charlar conmigo - Escribe lo que quieras y te responderé

Para ver este menú de nuevo en cualquier momento escribe 'menú' o 'ayuda'.
"""

# Path to GitHub repo raw content
GITHUB_RAW_URL = "https://raw.githubusercontent.com/marajadesantelmo/deltix/main/"

# WhatsApp Message Templates
# You'll need to register these templates with Twilio before using them in production
MESSAGE_TEMPLATES = {
    "welcome": "Bienvenido a Deltix, el bot del humedal. Escriba 'menu' para ver las opciones disponibles.",
    "daily_update": "Actualización diaria del Delta: {{1}}",
    "subscription_confirmation": "Te has suscrito correctamente a las actualizaciones de {{1}}."
}

# The list of capabilities of the bot
BOT_CAPABILITIES = [
    "Pronóstico de mareas INA",
    "Pronóstico meteorológico de windgurú",
    "Pronóstico de mareas Hidrografía Naval",
    "Horarios de lanchas colectivas",
    "Información sobre lanchas almaceneras",
    "Memes Islenials",
    "Asistente IA para consultas",
    "Información sobre actividades isleñas"
]
