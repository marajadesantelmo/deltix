from flask import Flask, request, jsonify
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import os
import sys
import json
import random
import time
from datetime import datetime
import requests
import smtplib
from email.message import EmailMessage

# Add the deltix directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import deltix functions and utils
from deltix_funciones import ALMACENERAS_DATA
from llm_connector import get_llm_response, create_conversation
from whatsapp_utils import format_whatsapp_text, format_mareas_data, get_random_meme_url

# Import tokens
try:
    from tokens import account_sid, auth_token, twilio_phone_number, gmail_token
except ImportError:
    # For deployment, use environment variables
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    twilio_phone_number = os.environ.get('TWILIO_PHONE_NUMBER')
    gmail_token = os.environ.get('GMAIL_TOKEN')

# Initialize Twilio client
client = Client(account_sid, auth_token)

# Initialize Flask app
app = Flask(__name__)

# Store user conversation states
user_conversations = {}
user_states = {}

# Define conversation states (mirroring your Telegram implementation)
STATE_START = 'start'
STATE_CHARLAR = 'charlar'
STATE_MEME = 'meme'
STATE_MEME2 = 'meme2'
STATE_COLABORAR = 'colaborar'
STATE_MENSAJEAR = 'mensajear'
STATE_COLECTIVAS = 'colectivas'
STATE_JILGUERO = 'jilguero'
STATE_INTERISLENA = 'interislena'
STATE_LINEASDELTA_DIRECTION = 'lineasdelta_direction'
STATE_LINEASDELTA_SCHEDULE = 'lineasdelta_schedule'
STATE_ALMACENERA_SELECT = 'almacenera_select'

# URLs for static resources
GITHUB_BASE_URL = "https://raw.githubusercontent.com/marajadesantelmo/deltix/main/"

def get_menu_message():
    """Generate the main menu message in WhatsApp format"""
    return (
        "- *mareas* _pronóstico de mareas INA_ ⛵\n"
        "- *hidrografia* _mareas hidrografia_\n"
        "- *windguru* _pronóstico del clima de windgurú_\n"
        "- *colectivas* _horarios lanchas colectivas_ 🕖\n"
        "- *almaceneras* _lanchas almaceneras_ 🚤\n"
        "- *memes* _los memes más divertidos de la isla_ 😂\n"
        "- *mensajear* _mandarle un mensajito al equipo Deltix_\n\n"
        "*Actividades y emprendimientos isleños*\n\n"
        "- *amanita* _paseos en canoa isleña_\n"
        "- *alfareria* _encuentros con el barro_\n"
        "- *labusqueda* _espacio para ceremonias, hostal y mas_\n"
        "- *canaveralkayaks* _excursiones en kayak_"
    )

@app.route('/', methods=['GET'])
def home():
    return "Deltix WhatsApp webhook está funcionando!"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming WhatsApp messages"""
    # Get incoming message data
    incoming_msg = request.values.get('Body', '').strip().lower()
    sender_number = request.values.get('From', '')
    
    # Create a TwiML response
    resp = MessagingResponse()
    
    # Log incoming message
    print(f"Received message: '{incoming_msg}' from {sender_number}")
    
    # Get or create a conversation ID for this user
    if sender_number not in user_conversations:
        user_conversations[sender_number] = create_conversation()
    conversation_id = user_conversations[sender_number]
    
    # Get the current state for this user
    current_state = user_states.get(sender_number, STATE_START)
    
    try:
        # Process message based on current state and command
        process_message(sender_number, incoming_msg, current_state)
    except Exception as e:
        error_msg = f"Ocurrió un error: {str(e)}"
        print(error_msg)
        client.messages.create(
            body="Ups, algo salió mal. Por favor, intenta nuevamente más tarde.",
            from_=twilio_phone_number,
            to=sender_number
        )
    
    return str(resp)

def process_message(sender_number, message, current_state):
    """Process incoming message based on current state and message content"""
    # Command messages - override current state
    if 'hola' in message:
        send_start_message(sender_number)
        user_states[sender_number] = STATE_START
        return
    
    # Process based on current state
    if current_state == STATE_MEME:
        handle_meme_response(sender_number, message)
    elif current_state == STATE_MENSAJEAR:
        handle_mensajear_response(sender_number, message)
    elif current_state == STATE_COLECTIVAS:
        handle_colectivas_response(sender_number, message)
    elif current_state == STATE_JILGUERO:
        handle_jilguero_response(sender_number, message)
    elif current_state == STATE_INTERISLENA:
        handle_interislena_response(sender_number, message)
    elif current_state == STATE_LINEASDELTA_DIRECTION:
        handle_lineasdelta_direction(sender_number, message)
    elif current_state == STATE_LINEASDELTA_SCHEDULE:
        handle_lineasdelta_schedule(sender_number, message)
    elif current_state == STATE_ALMACENERA_SELECT:
        handle_almacenera_select(sender_number, message)

    # Command based processing
    elif 'mareas' in message:
        send_mareas(sender_number)
    elif 'marea' in message:
        send_mareas(sender_number)
    elif 'windguru' in message:
        send_windguru(sender_number)
    elif 'hidrografia' in message:
        send_hidrografia(sender_number)
    elif 'memes' in message:
        send_meme(sender_number)
    elif 'colectivas' in message:
        send_colectivas_options(sender_number)
    elif 'almaceneras' in message:
        send_almaceneras_list(sender_number)
    elif 'mensajear' in message:
        request_mensaje(sender_number)
    elif 'amanita' in message:
        send_amanita(sender_number)
    elif 'alfareria' in message:
        send_alfareria(sender_number)
    elif 'labusqueda' in message:
        send_labusqueda(sender_number)
    elif 'canaveralkayaks' in message:
        send_canaveralkayaks(sender_number)
    elif 'jilguero' in message:
        start_jilguero(sender_number)
    elif 'interislena' in message:
        start_interislena(sender_number)
    elif 'lineasdelta' in message:
        start_lineasdelta(sender_number)
    elif 'gracias' in message:
        send_de_nada(sender_number)
    # Use LLM as fallback for other messages
    else:
        send_llm_response(sender_number, message)

def send_start_message(sender_number):
    """Send welcome message and menu options"""
    client.messages.create(
        body="¡Hola! Soy Deltix, el bot del humedal 🦫\n\nEn qué te puedo ayudar?\n",
        from_=twilio_phone_number,
        to=sender_number)
    time.sleep(1)
    client.messages.create(
        body="- *mareas* _pronóstico de mareas INA_ ⛵\n"
            "- *hidrografia* _mareas hidrografia_\n"
            "- *windguru* _pronóstico del clima de windgurú_\n"
            "- *colectivas* _horarios lanchas colectivas_ 🕖\n"
            "- *almaceneras* _lanchas almaceneras_ 🚤\n"
            "- *memes* _los memes más divertidos de la isla_ 😂\n"
            "- *mensajear* _mandarle un mensajito al equipo Deltix_\n\n"
            "*Actividades y emprendimientos isleños*\n\n"
            "- *amanita* _paseos en canoa isleña_\n"
            "- *alfareria* _encuentros con el barro_\n"
            "- *labusqueda* _espacio para ceremonias, hostal y mas_\n"
            "- *canaveralkayaks* _excursiones en kayak_",
        from_=twilio_phone_number,
        to=sender_number)
    time.sleep(2)
    client.messages.create(
        body="... o también me podés preguntar lo que quieras y yo te voy a responder lo mejor que pueda usando mi inteligencia artificial de carpincho digital",
        from_=twilio_phone_number,
        to=sender_number)

def send_mareas(sender_number):
    """Send mareas information and offer subscription"""
    client.messages.create(
        body="Acá tenés el informe de mareas",
        from_=twilio_phone_number,
        to=sender_number,
        media_url=[f'{GITHUB_BASE_URL}marea.png']
    )
    
    user_states[sender_number] = STATE_START

def send_windguru(sender_number):
    """Send windguru information and offer subscription"""
    client.messages.create(
        body="Ahí te mando el pronóstico de windguru",
        from_=twilio_phone_number,
        to=sender_number,
        media_url=[f'{GITHUB_BASE_URL}windguru.png']
    )
    
    user_states[sender_number] = STATE_START

def send_hidrografia(sender_number):
    """Send hidrografia information and offer subscription"""
    try:
        # Fetch data from GitHub
        response = requests.get(f'{GITHUB_BASE_URL}table_data.txt')
        if response.status_code == 200:
            formatted_message = format_mareas_data(response.text)
            client.messages.create(
                body=formatted_message,
                from_=twilio_phone_number,
                to=sender_number
            )
            
            user_states[sender_number] = STATE_START
        else:
            client.messages.create(
                body="Lo siento, no pude obtener los datos de mareas de hidrografía en este momento.",
                from_=twilio_phone_number,
                to=sender_number
            )
    except Exception as e:
        client.messages.create(
            body="Ocurrió un error al procesar los datos de mareas.",
            from_=twilio_phone_number,
            to=sender_number
        )
        user_states[sender_number] = STATE_START

def send_meme(sender_number):
    """Send a random meme and ask if user wants another"""
    client.messages.create(
        body="...me encantan los memes islenials 😂 Te mando uno.",
        from_=twilio_phone_number,
        to=sender_number
    )
    meme_url = get_random_meme_url()
    client.messages.create(
        media_url=[meme_url],
        from_=twilio_phone_number,
        to=sender_number
    )
    
    # Add delay
    time.sleep(3)
    
    client.messages.create(
        body="Buenísimo, no? Son de la página Memes Islenials. Te recomiendo que la sigas en las redes\n\nQuerés otro meme?",
        from_=twilio_phone_number,
        to=sender_number
    )
    
    user_states[sender_number] = STATE_MEME

def handle_meme_response(sender_number, message):
    """Handle response to meme offer"""
    if message in ['si', 'sí', 'SI', 'Si', 'Sí']:
        meme_url = get_random_meme_url()
        client.messages.create(
            media_url=[meme_url],
            from_=twilio_phone_number,
            to=sender_number
        )
        client.messages.create(
            body="Uno más?",
            from_=twilio_phone_number,
            to=sender_number
        )
        user_states[sender_number] = STATE_MEME2
    else:
        client.messages.create(
            body="Bueno... si querés podes elegir otra de las actividades para hacer conmigo",
            from_=twilio_phone_number,
            to=sender_number
        )
        user_states[sender_number] = STATE_START

def handle_meme2_response(sender_number, message):
    """Handle response to second meme offer"""
    if message in ['si', 'sí', 'SI', 'Si', 'Sí']:
        meme_url = get_random_meme_url()
        client.messages.create(
            media_url=[meme_url],
            from_=twilio_phone_number,
            to=sender_number
        )
        # Add delay
        time.sleep(2)
        client.messages.create(
            body="Te mando otro?",
            from_=twilio_phone_number,
            to=sender_number
        )
        user_states[sender_number] = STATE_MEME
    else:
        client.messages.create(
            body="Bueno... si querés podes elegir otra de las actividades para hacer conmigo",
            from_=twilio_phone_number,
            to=sender_number
        )
        user_states[sender_number] = STATE_START

def request_mensaje(sender_number):
    """Request a message to forward to the developer"""
    client.messages.create(
        body="Escribí el mensaje y yo se lo reenvío al equipo Deltix",
        from_=twilio_phone_number,
        to=sender_number
    )
    user_states[sender_number] = STATE_MENSAJEAR

def handle_mensajear_response(sender_number, message):
    """Handle and forward user message to developer"""
    try:
        # Prepare email content
        body = f"Mensaje de {sender_number}: {message}"
        email_message = EmailMessage()
        email_message['From'] = "marajadesantelmo@gmail.com"
        email_message['To'] = "marajadesantelmo@gmail.com"
        email_message['Subject'] = "Mensaje de Deltix WhatsApp Bot"
        email_message.set_content(body)

        # Send email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login("marajadesantelmo@gmail.com", gmail_token)
        server.send_message(email_message)
        server.quit()

        # Notify user of success
        client.messages.create(
            body='Mensaje enviado con éxito. ¡Gracias!',
            from_=twilio_phone_number,
            to=sender_number
        )
    except Exception as e:
        # Notify user of failure
        client.messages.create(
            body=f"Lo siento, ocurrió un error al enviar tu mensaje: {str(e)}",
            from_=twilio_phone_number,
            to=sender_number
        )
    user_states[sender_number] = STATE_START

# --- COLECTIVAS FUNCTIONS --- #

def send_colectivas_options(sender_number):
    """Send options for colectivas services"""
    client.messages.create(
        body="""Elegí la empresa de lancha colectiva:\n
- *Jilguero* _va por el Carapachay-Angostura_
- *Interisleña* _Sarmiento, San Antonio y muchos más_
- *Lineas Delta* _Caraguatá, Canal Arias, Paraná Miní_
        
Responde con el nombre de la empresa que te interesa.""",
        from_=twilio_phone_number,
        to=sender_number
    )
    
    user_states[sender_number] = STATE_COLECTIVAS

def handle_colectivas_response(sender_number, message):
    """Handle selection of colectivas company"""
    message = message.lower()
    
    if "jilguero" in message:
        start_jilguero(sender_number)
    elif "interisleña" in message or "interislena" in message:
        start_interislena(sender_number)
    elif "lineas delta" in message or "lineasdelta" in message:
        start_lineasdelta(sender_number)
    else:
        client.messages.create(
            body="No reconozco esa empresa de lanchas. Por favor, selecciona Jilguero, Interisleña o Lineas Delta.",
            from_=twilio_phone_number,
            to=sender_number
        )

# --- JILGUERO FUNCTIONS --- #

def start_jilguero(sender_number):
    """Start Jilguero schedule inquiry"""
    client.messages.create(
        body="En qué sentido querés viajar? Ida a la isla o vuelta a Tigre?",
        from_=twilio_phone_number,
        to=sender_number
    )
    user_states[sender_number] = STATE_JILGUERO

def handle_jilguero_response(sender_number, message):
    """Handle Jilguero direction selection"""
    message = message.lower()
    
    if 'ida' in message or 'isla' in message:
        client.messages.create(
            body="Estos son los horarios de ida a la isla de Jilguero. Si ves que hay algún horario incorrecto o información a corregir, no dudes en mandarle un mensajito al equipo Deltix",
            from_=twilio_phone_number,
            to=sender_number,
            media_url=[f'{GITHUB_BASE_URL}colectivas/jilguero_ida.png']
        )
        
        # Add delay
        time.sleep(2)
        
        client.messages.create(
            body="Siempre recomiendo llamar antes a la empresa porque los horarios suelen cambiar. El teléfono es 4749-0987",
            from_=twilio_phone_number,
            to=sender_number
        )
        
        user_states[sender_number] = STATE_START
    
    elif 'vuelta' in message or 'tigre' in message:
        client.messages.create(
            body="Estos son los horarios de vuelta a Tigre de Jilguero. Si ves que hay algún horario incorrecto o información a corregir, no dudes en mandarle un mensajito al equipo Deltix",
            from_=twilio_phone_number,
            to=sender_number,
            media_url=[f'{GITHUB_BASE_URL}colectivas/jilguero_vuelta.png']
        )
        
        # Add delay
        time.sleep(2)
        
        client.messages.create(
            body="Siempre recomiendo llamar antes a la empresa porque los horarios suelen cambiar. El teléfono es 4749-0987",
            from_=twilio_phone_number,
            to=sender_number
        )
        
        user_states[sender_number] = STATE_START
    
    else:
        client.messages.create(
            body="No comprendí tu elección. Por favor, indica si necesitas los horarios de ida a la isla o vuelta a Tigre.",
            from_=twilio_phone_number,
            to=sender_number
        )

# --- INTERISLENA FUNCTIONS --- #

def start_interislena(sender_number):
    """Start Interislena schedule inquiry"""
    client.messages.create(
        body="Para Interisleña, por ahora solo tengo los horarios de Ida hacia la isla. Querés los horarios de verano o de inverno?",
        from_=twilio_phone_number,
        to=sender_number
    )
    user_states[sender_number] = STATE_INTERISLENA

def handle_interislena_response(sender_number, message):
    """Handle Interislena season selection"""
    message = message.lower()
    
    if 'invierno' in message:
        client.messages.create(
            media_url=[f'{GITHUB_BASE_URL}colectivas/interislena_ida_invierno.png'],
            from_=twilio_phone_number,
            to=sender_number
        )
        
        client.messages.create(
            body=f"Estos son los horarios de invierno de Interisleña. Si ves que hay algún horario incorrecto o información a corregir, no dudes en mandarle un mensajito al equipo Deltix",
            from_=twilio_phone_number,
            to=sender_number
        )
        
        # Add delay
        time.sleep(1)
        
        client.messages.create(
            body=f"Siempre recomiendo llamar antes a la empresa porque los horarios suelen cambiar. El teléfono es 4749-0900",
            from_=twilio_phone_number,
            to=sender_number
        )
        
        user_states[sender_number] = STATE_START
    
    elif 'verano' in message:
        client.messages.create(
            media_url=[f'{GITHUB_BASE_URL}colectivas/interislena_ida_verano.png'],
            from_=twilio_phone_number,
            to=sender_number
        )
        
        client.messages.create(
            body=f"Estos son los horarios de verano de Interisleña. Si ves que hay algún horario incorrecto o información a corregir, no dudes en mandarle un mensajito al equipo Deltix",
            from_=twilio_phone_number,
            to=sender_number
        )
        
        # Add delay
        time.sleep(1)
        
        client.messages.create(
            body=f"Siempre recomiendo llamar antes a la empresa porque los horarios suelen cambiar. El teléfono es 4749-0900",
            from_=twilio_phone_number,
            to=sender_number
        )
        
        user_states[sender_number] = STATE_START
    
    else:
        client.messages.create(
            body="No comprendí tu elección. Por favor, indica si necesitas los horarios de verano o invierno.",
            from_=twilio_phone_number,
            to=sender_number
        )

# --- LINEASDELTA FUNCTIONS --- #

def start_lineasdelta(sender_number):
    """Start LineasDelta schedule inquiry"""
    client.messages.create(
        body="Qué recorrido necesitás? Ida a la isla o vuelta a Tigre?",
        from_=twilio_phone_number,
        to=sender_number
    )
    user_states[sender_number] = STATE_LINEASDELTA_DIRECTION

def handle_lineasdelta_direction(sender_number, message):
    """Handle LineasDelta direction selection"""
    message = message.lower()
    
    if "ida" in message:
        # Store direction in user context (you might want to use a dict for this)
        user_data = user_states.get(f"{sender_number}_data", {})
        user_data["direction"] = "ida a la isla"
        user_states[f"{sender_number}_data"] = user_data
        
        client.messages.create(
            body="En época escolar o no escolar?",
            from_=twilio_phone_number,
            to=sender_number
        )
        
        user_states[sender_number] = STATE_LINEASDELTA_SCHEDULE
    
    elif "vuelta" in message:
        user_data = user_states.get(f"{sender_number}_data", {})
        user_data["direction"] = "vuelta a tigre"
        user_states[f"{sender_number}_data"] = user_data
        
        client.messages.create(
            body="En época escolar o no escolar?",
            from_=twilio_phone_number,
            to=sender_number
        )
        
        user_states[sender_number] = STATE_LINEASDELTA_SCHEDULE
    
    else:
        client.messages.create(
            body="Por favor, elegí 'Ida' o 'Vuelta'.",
            from_=twilio_phone_number,
            to=sender_number
        )

def handle_lineasdelta_schedule(sender_number, message):
    """Handle LineasDelta schedule type selection"""
    message = message.lower()
    user_data = user_states.get(f"{sender_number}_data", {})
    direction = user_data.get("direction", "ida a la isla")
    
    if "escolar" in message and "no" not in message:
        user_data["epoca"] = "escolar"
        user_states[f"{sender_number}_data"] = user_data
    elif "no escolar" in message:
        user_data["epoca"] = "no escolar"
        user_states[f"{sender_number}_data"] = user_data
    else:
        client.messages.create(
            body="Por favor, elegí 'Escolar' o 'No escolar'.",
            from_=twilio_phone_number,
            to=sender_number
        )
        return
    
    client.messages.create(
        body=f"Estos son los horarios de {direction} en época {user_data['epoca']}.",
        from_=twilio_phone_number,
        to=sender_number
    )
    
    # Send the appropriate image based on user choices
    if direction == "ida a la isla":
        if user_data["epoca"] == "escolar":
            media_path = f"{GITHUB_BASE_URL}colectivas/lineas_delta_ida_escolar.png"
        else:
            media_path = f"{GITHUB_BASE_URL}colectivas/lineas_delta_ida_no_escolar.png"
    else:  # vuelta a tigre
        if user_data["epoca"] == "escolar":
            media_path = f"{GITHUB_BASE_URL}colectivas/lineas_delta_vuelta_escolar.png"
        else:
            media_path = f"{GITHUB_BASE_URL}colectivas/lineas_delta_vuelta_no_escolar.png"
    
    client.messages.create(
        media_url=[media_path],
        from_=twilio_phone_number,
        to=sender_number
    )
    
    user_states[sender_number] = STATE_START

# --- ALMACENERAS FUNCTIONS --- #

def send_almaceneras_list(sender_number):
    """Send list of almaceneras"""
    # Create a message with the list of available almaceneras
    client.messages.create(
        body="📋 Acá te muestro las lanchas almaceneras disponibles. ¿Sobre cuál querés información?\n\nEnvía el nombre exacto de la almacenera o 'Ver todas' para ver la lista completa.",
        from_=twilio_phone_number,
        to=sender_number
    )
    
    # Create message with almacenera options
    almaceneras_list = list(ALMACENERAS_DATA.keys())
    almaceneras_message = ""
    for i, name in enumerate(almaceneras_list):
        almaceneras_message += f"{i+1}. {name}\n"
    
    almaceneras_message += "\nEscribe 'Ver todas' para ver información de todas las almaceneras."
    
    client.messages.create(
        body=almaceneras_message,
        from_=twilio_phone_number,
        to=sender_number
    )
    
    user_states[sender_number] = STATE_ALMACENERA_SELECT

def handle_almacenera_select(sender_number, message):
    """Handle almacenera selection"""
    if message.lower() == "ver todas":
        # Send info about all almaceneras
        client.messages.create(
            body="Acá te muestro la información de todas las lanchas almaceneras:",
            from_=twilio_phone_number,
            to=sender_number
        )
        
        for nombre, info in ALMACENERAS_DATA.items():
            formatted_message = f"*{nombre}* de {info['propietario']}\n"
            if info['recorridos']:
                formatted_message += f"{info['recorridos']}\n"
            if info['telefono']:
                formatted_message += f"📞 {info['telefono']}"
            
            client.messages.create(
                body=formatted_message,
                from_=twilio_phone_number,
                to=sender_number
            )
            time.sleep(0.3)  # Small pause between messages
    else:
        # Try to find the requested almacenera
        found = False
        for nombre in ALMACENERAS_DATA.keys():
            if nombre.lower() == message.lower():
                info = ALMACENERAS_DATA[nombre]
                
                formatted_message = f"*{nombre}* de {info['propietario']}\n"
                if info['recorridos']:
                    formatted_message += f"\n{info['recorridos']}\n"
                if info['telefono']:
                    formatted_message += f"\n📞 Teléfono: {info['telefono']}"
                
                client.messages.create(
                    body=formatted_message,
                    from_=twilio_phone_number,
                    to=sender_number
                )
                found = True
                break
        
        if not found:
            client.messages.create(
                body="No encontré información sobre esa almacenera. Por favor, elegí una de la lista o escribe 'Ver todas'.",
                from_=twilio_phone_number,
                to=sender_number
            )
            return
    
    # Final recommendation message
    client.messages.create(
        body="Los horarios y recorridos de las almaceneras pueden variar, te recomiendo escribir o llamar para confirmar.",
        from_=twilio_phone_number,
        to=sender_number
    )
    
    user_states[sender_number] = STATE_START

# --- ACTIVIDADES FUNCTIONS --- #

def send_amanita(sender_number):
    """Send information about Amanita"""
    client.messages.create(
        media_url=[f'{GITHUB_BASE_URL}actividades_productos/amanita.png'],
        from_=twilio_phone_number,
        to=sender_number
    )
    
    client.messages.create(
        body=(
            "*Experiencias en Canoa Isleña*\n\n"
            "_Paseos por el Delta del Paraná_\n"
            "_Con Guía Bilingüe (opcional)_\n"
            "_Servicio puerta a puerta (opcional)_\n\n"
            "instagram.com/amanitaturismodelta\n"
            "Contacto: 1169959272"
        ),
        from_=twilio_phone_number,
        to=sender_number
    )

def send_alfareria(sender_number):
    """Send information about Kutral Alfarería"""
    client.messages.create(
        media_url=[f'{GITHUB_BASE_URL}actividades_productos/alfareria.png'],
        from_=twilio_phone_number,
        to=sender_number
    )
    
    client.messages.create(
        body=(
            "*Kutral Alfarería*\n\n"
            "_Encuentros con el barro_\n"
            "_Talleres de alfarería_\n"
            "_Experimentación y creación con arcilla_\n\n"
            "instagram.com/kutralalfareria\n"
        ),
        from_=twilio_phone_number,
        to=sender_number
    )

def send_labusqueda(sender_number):
    """Send information about La Búsqueda"""
    client.messages.create(
        media_url=[f'{GITHUB_BASE_URL}actividades_productos/labusqueda.png'],
        from_=twilio_phone_number,
        to=sender_number
    )
    
    client.messages.create(
        body=(
            "*La Búsqueda*\n\n"
            "_Espacio para encuentros y ceremonias_\n"
            "_Hostal en el Delta_\n"
            "_Conexión con la naturaleza_\n\n"
            "instagram.com/labusqueda_cabanadelta\n"
            "Contacto: 1150459556"
        ),
        from_=twilio_phone_number,
        to=sender_number
    )

def send_canaveralkayaks(sender_number):
    """Send information about Cañaveral Kayaks"""
    client.messages.create(
        media_url=[f'{GITHUB_BASE_URL}actividades_productos/canaveralkayaks.png'],
        from_=twilio_phone_number,
        to=sender_number
    )
    
    client.messages.create(
        body=(
            "*Cañaveral Kayaks*\n\n"
            "_Excursiones en Kayak_\n"
            "_Paseos con guía_\n"
            "_Remadas nocturnas_\n\n"
            "linktr.ee/canaveralkayaks\n"
            "Contacto: 1126961274"
        ),
        from_=twilio_phone_number,
        to=sender_number
    )

def send_de_nada(sender_number):
    """Send response to thanks"""
    client.messages.create(
        body="De nada! es un placer a ayudar a lxs humanos que visitan el humedal 🦫",
        from_=twilio_phone_number,
        to=sender_number
    )

def send_llm_response(sender_number, message):
    """Get and send response from LLM for any other message"""
    conversation_id = user_conversations.get(sender_number)
    if not conversation_id:
        conversation_id = create_conversation()
        user_conversations[sender_number] = conversation_id
    
    # Send a "thinking" message for better UX
    client.messages.create(
        body=random.choice([
            "Dejame pensar...",
            "...estoy pensando...",
            "...deltix pensando...",
            "Aguantame que pienso qué responderte",
        ]),
        from_=twilio_phone_number,
        to=sender_number
    )
    
    try:
        # Debugging: Log the conversation_id and message
        print(f"Debug: Sending message to LLM. conversation_id={conversation_id}, message={message}")
        
        # Validate input data
        if not conversation_id or not isinstance(conversation_id, str):
            print(f"Invalid conversation_id detected: {conversation_id}. Reinitializing...")
            conversation_id = create_conversation()
            user_conversations[sender_number] = conversation_id
        
        llm_response = get_llm_response(message, conversation_id)
        
        client.messages.create(
            body=llm_response,
            from_=twilio_phone_number,
            to=sender_number
        )
    except Exception as e:
        # Log the error with more context
        print(f"Error getting LLM response: {str(e)}. conversation_id={conversation_id}, message={message}")
        client.messages.create(
            body="Lo siento, tuve un problema al procesar tu mensaje. ¿Podés intentar con algo más simple o usar uno de mis comandos?",
            from_=twilio_phone_number,
            to=sender_number
        )
    
    user_states[sender_number] = STATE_START

@app.route('/status', methods=['POST'])
def status_callback():
    """Handle message status callback from Twilio"""
    message_sid = request.values.get('MessageSid', '')
    message_status = request.values.get('MessageStatus', '')
    
    print(f"Message {message_sid} status: {message_status}")
    
    return jsonify({"status": "received"})

# For local development
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    # This is the code that will be used by PythonAnywhere
    application = app