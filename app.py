from supabase import create_client
import streamlit as st
from openai import OpenAI, AssistantEventHandler
from typing_extensions import override
import os
import re
import requests
import time
import random
import threading
import json
from datetime import datetime


supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
if not supabase_url or not supabase_key:
    raise ValueError("Supabase URL and Key must be set in environment variables")

supabase = create_client(supabase_url, supabase_key)

openrouter_key = os.getenv('OPENROUTER_API_KEY')
if not openrouter_key:
    raise ValueError("OpenRouter API Key must be set in environment variables")

# Define weather-related keywords in Spanish
WEATHER_KEYWORDS = ['clima', 'temperatura', 'pronostico', 'tiempo', 'lluvia', 'viento']

# Define almacen-related keywords in Spanish
ALMACEN_KEYWORDS = ['almacen', 'almacén', 'almacenera']

class EventHandler(AssistantEventHandler):
    @override    
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)
    @override     
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)
        
def on_tool_call_created(self, tool_call):
  print(f"\nassistant > {tool_call.type}\n", flush=True)

def on_tool_call_delta(self, delta, snapshot):
  if delta.type == 'code_interpreter':
    if delta.code_interpreter.input:
      print(delta.code_interpreter.input, end="", flush=True)
    if delta.code_interpreter.outputs:
      print(f"\n\noutput >", flush=True)
      for output in delta.code_interpreter.outputs:
        if output.type == "logs":
          print(f"\n{output.logs}", flush=True)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_key,
)

def get_help_message():
    return ("Ingresando algunas de estas palabras podes obtener información útil:\n"
        "- **mareas**: _obtener el pronóstico de mareas_\n"
        "- **windguru**: _pronóstico meteorológico de windgurú_\n"
        "- **colectivas**: _horarios de lanchas colectivas_\n"
        "- **memes**: _ver los memes más divertidos de la isla_\n"
        "- **clima**: _información meteorológica actualizada_\n"
        "- **almaceneras**: _información sobre lanchas almaceneras de la isla_\n"
    )

def load_weather_data():
    """Load the latest weather data from the JSON file"""
    try:
        weather_file_path = "rag/weather_data.json"
        with open(weather_file_path, 'r') as file:
            weather_data = json.load(file)
        return weather_data
    except Exception as e:
        print(f"Error loading weather data: {e}")
        return None

def format_weather_for_context(weather_data):
    """Format weather data into a readable context in Spanish for the LLM"""
    if not weather_data:
        return ""
    
    try:
        # Get current weather information
        current = weather_data.get('current_weather', {})
        location = current.get('name', 'Desconocido')
        country = current.get('sys', {}).get('country', '')
        temp = current.get('main', {}).get('temp', 'N/A')
        feels_like = current.get('main', {}).get('feels_like', 'N/A')
        description = current.get('weather', [{}])[0].get('description', 'N/A')
        humidity = current.get('main', {}).get('humidity', 'N/A')
        wind_speed = current.get('wind', {}).get('speed', 'N/A')
        
        # Get timestamp
        timestamp_str = weather_data.get('timestamp', 'Desconocido')
        
        # Format forecast information (next 24 hours)
        forecast_items = weather_data.get('forecast', {}).get('list', [])[:8]  # First 24 hours (8 * 3-hour intervals)
        forecast_text = ""
        
        for item in forecast_items:
            dt_txt = item.get('dt_txt', '')
            temp_forecast = item.get('main', {}).get('temp', 'N/A')
            desc_forecast = item.get('weather', [{}])[0].get('description', 'N/A')
            forecast_text += f"- {dt_txt}: {temp_forecast}°C, {desc_forecast}\n"
        
        # Create the context in Spanish
        context = f"""
Información del clima para {location}, {country} (actualizado el {timestamp_str}):
Condiciones actuales: {temp}°C (sensación térmica de {feels_like}°C), {description}
Humedad: {humidity}%, Velocidad del viento: {wind_speed} m/s

Pronóstico para las próximas 24 horas:
{forecast_text}
"""
        return context
    except Exception as e:
        print(f"Error formatting weather data: {e}")
        return "La información del clima está disponible pero no se pudo formatear correctamente."

def contains_weather_keywords(user_input):
    """Check if the user input contains any weather-related keywords"""
    lower_input = user_input.lower()
    return any(keyword in lower_input for keyword in WEATHER_KEYWORDS)

def contains_almacen_keywords(user_input):
    """Check if the user input contains any almacen-related keywords"""
    lower_input = user_input.lower()
    return any(keyword in lower_input for keyword in ALMACEN_KEYWORDS)

def load_almacen_data():
    """Load almacen data from the text file"""
    try:
        almacen_file_path = os.path.join(os.getcwd(), "rag", "almaceneras.txt")
        if os.path.exists(almacen_file_path):
            with open(almacen_file_path, 'r', encoding='utf-8') as file:
                return file.read()
        else:
            print(f"Almacen data file not found at: {almacen_file_path}")
            return ""
    except Exception as e:
        print(f"Error loading almacen data: {e}")
        return ""

def make_api_call(user_input, project_id, documents, retries=3, delay=2):
    try:
        #context_supabase = "\n".join([doc["content"] for doc in documents])
        context = []
        if any(keyword in user_input.lower() for keyword in ['seguridad', 'policia', 'emergencia', 'telefono']):
            with open("rag/policia.txt", "r") as file:
                context.append(file.read())
        
        # Add weather data as context if weather-related keywords are detected
        if contains_weather_keywords(user_input):
            weather_data = load_weather_data()
            if weather_data:
                weather_context = format_weather_for_context(weather_data)
                context.append(weather_context)

        # Add almacen data as context if almacen-related keywords are detected
        if contains_almacen_keywords(user_input):
            almacen_context = load_almacen_data()
            if almacen_context:
                context.append(f"Información sobre almacenes de la isla:\n{almacen_context}")
                
        previous_messages = supabase.from_("chat_history").select("*").eq("project_id", project_id).execute().data
        previous_messages_content = "\n".join([msg["content"] for msg in previous_messages if msg["role"] == "user"])
        
        context_text = "\n\n".join(context)
        
        for attempt in range(retries):
            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "<YOUR_SITE_URL>",  # Optional. Site URL for rankings on openrouter.ai.
                    "X-Title": "<YOUR_SITE_NAME>",  # Optional. Site title for rankings on openrouter.ai.
                },
                extra_body={},
                model="deepseek/deepseek-chat:free",
                messages=[
                    {
                        "role": "system",
                        "content": "Vos sos Deltix, el bot del humedal. Eres argentino y amable. Ingresando algunas de estas palabras el usuario puede obtener información útil: mareas: obtener el pronóstico de mareas, windguru: pronóstico meteorológico de windgurú, Colectivas: horarios de lanchas colectivas, memes: ver los memes más divertidos de la isla, clima/pronostico: información meteorológica actualizada, almaceneras: información sobre almacenes de la isla"
                    },
                    {
                        "role": "user",
                        "content": f"{user_input}\n\nMensajes anteriores:\n{previous_messages_content}\n\nContexto:\n{context_text}"
                    }
                ]
            )
            response_content = completion.choices[0].message.content
            if response_content.strip():
                return response_content
            time.sleep(delay)
        raise ValueError("Received empty response from OpenRouter API after multiple attempts")
    except Exception as e:
        raise e

def store_chat_message(project_id, role, content):
    supabase.from_("chat_history").insert({"project_id": project_id, "role": role, "content": content}).execute()

def create_project():
    response = supabase.from_("projects").insert({"name": "Nueva conversacion"}).execute()
    return response.data[0]["id"]

def get_random_meme():
    meme_files = [f"memes/{file}" for file in os.listdir("memes") if file.endswith(".png")]
    return random.choice(meme_files) if meme_files else None

def handle_colectivas_input(user_input):
    if st.session_state.colectivas_step == "select_company":
        if "jilguero" in user_input.lower():
            st.session_state.colectivas_company = "Jilguero"
            st.chat_message("assistant", avatar="bot_icon.png").write("En qué sentido querés viajar? Ida a la isla o vuelta a Tigre?")
            st.session_state.colectivas_step = "select_direction"
        elif "interisleña" in user_input.lower():
            st.session_state.colectivas_company = "Interisleña"
            st.chat_message("assistant", avatar="bot_icon.png").write("Querés los horarios de verano o de invierno?")
            st.session_state.colectivas_step = "select_season"
        elif "lineasdelta" in user_input.lower():
            st.session_state.colectivas_company = "LineasDelta"
            st.chat_message("assistant", avatar="bot_icon.png").write("Qué recorrido necesitás? Ida a la isla o vuelta a Tigre?")
            st.session_state.colectivas_step = "select_direction"
        else:
            if st.session_state.get("failed_attempts", 0) >= 1:
                st.session_state.colectivas_step = None
                st.session_state.failed_attempts = 0
                return False  # Indicate to handle with LLM
            st.chat_message("assistant", avatar="bot_icon.png").write("No entendí. Por favor, elegí una empresa de lancha colectiva: Jilguero, Interisleña, LineasDelta")
            st.session_state.failed_attempts = st.session_state.get("failed_attempts", 0) + 1
            st.session_state.colectivas_step = None

    elif st.session_state.colectivas_step == "select_direction":
        if st.session_state.colectivas_company == "Jilguero":
            if "ida" in user_input.lower():
                st.image("colectivas/jilguero_ida.png")
                st.chat_message("assistant", avatar="bot_icon.png").write("Estos son los horarios de ida a la isla de Jilguero.")
                # Reset colectivas flow after showing schedule
                st.session_state.colectivas_step = None
            elif "vuelta" in user_input.lower():
                st.image("colectivas/jilguero_vuelta.png")
                st.chat_message("assistant", avatar="bot_icon.png").write("Estos son los horarios de vuelta a Tigre de Jilguero.")
                # Reset colectivas flow after showing schedule
                st.session_state.colectivas_step = None
            else:
                st.chat_message("assistant", avatar="bot_icon.png").write("No entendí. Por favor, elegí 'Ida a la isla' o 'Vuelta a Tigre'.")
                st.session_state.colectivas_step = None
        elif st.session_state.colectivas_company == "LineasDelta":
            st.session_state.colectivas_direction = user_input.lower()
            st.chat_message("assistant", avatar="bot_icon.png").write("En época escolar o no escolar?")
            st.session_state.colectivas_step = "select_schedule"

    elif st.session_state.colectivas_step == "select_season":
        if "verano" in user_input.lower():
            st.image("colectivas/interislena_ida_verano.png")
            st.chat_message("assistant", avatar="bot_icon.png").write("Estos son los horarios de verano de Interisleña.")
            # Reset colectivas flow after showing schedule
            st.session_state.colectivas_step = None
        elif "invierno" in user_input.lower():
            st.image("colectivas/interisleña_ida_invierno.png")
            st.chat_message("assistant", avatar="bot_icon.png").write("Estos son los horarios de invierno de Interisleña.")
            # Reset colectivas flow after showing schedule
            st.session_state.colectivas_step = None
        else:
            st.chat_message("assistant", avatar="bot_icon.png").write("No entendí. Por favor, elegí 'Verano' o 'Invierno'.")
            st.session_state.colectivas_step = None

    elif st.session_state.colectivas_step == "select_schedule":
        if "escolar" in user_input.lower():
            if "ida" in st.session_state.colectivas_direction:
                st.image("colectivas/lineas_delta_ida_escolar.png")
                st.chat_message("assistant", avatar="bot_icon.png").write("Estos son los horarios de ida a la isla en época escolar de LineasDelta.")
                # Reset colectivas flow after showing schedule
                st.session_state.colectivas_step = None
            elif "vuelta" in st.session_state.colectivas_direction:
                st.image("colectivas/lineas_delta_vuelta_escolar.png")
                st.chat_message("assistant", avatar="bot_icon.png").write("Estos son los horarios de vuelta a Tigre en época escolar de LineasDelta.")
                # Reset colectivas flow after showing schedule
                st.session_state.colectivas_step = None
        elif "no escolar" in user_input.lower():
            if "ida" in st.session_state.colectivas_direction:
                st.image("colectivas/lineas_delta_ida_no_escolar.png")
                st.chat_message("assistant", avatar="bot_icon.png").write("Estos son los horarios de ida a la isla en época no escolar de LineasDelta.")
                # Reset colectivas flow after showing schedule
                st.session_state.colectivas_step = None
            elif "vuelta" in st.session_state.colectivas_direction:
                st.image("colectivas/lineas_delta_vuelta_no_escolar.png")
                st.chat_message("assistant", avatar="bot_icon.png").write("Estos son los horarios de vuelta a Tigre en época no escolar de LineasDelta.")
                # Reset colectivas flow after showing schedule
                st.session_state.colectivas_step = None
        else:
            st.chat_message("assistant", avatar="bot_icon.png").write("No entendí. Por favor, elegí 'Escolar' o 'No escolar'.")
            st.session_state.colectivas_step = None

    # If not explicitly set to None above, set default step
    if st.session_state.colectivas_step is None:
        # Reset any other colectivas-related state variables
        if "colectivas_company" in st.session_state:
            del st.session_state.colectivas_company
        if "colectivas_direction" in st.session_state:
            del st.session_state.colectivas_direction
        if "failed_attempts" in st.session_state:
            del st.session_state.failed_attempts
            
    return True if st.session_state.colectivas_step is not None else False  # Return False to handle with LLM if we've exited the flow

# Initialize chat history in session state if it doesn't exist
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# Store project_id in session state to persist across conversation
if "project_id" not in st.session_state:
    st.session_state.project_id = create_project()

project_id = st.session_state.project_id

# UI Layout
col_title, col_logo = st.columns([5, 1])
with col_title:
    st.title("Deltix")
    st.write("El bot del humedal...")
with col_logo:
    st.image('bot_icon.png')

# Show initial bot messages only once per session
if "initial_messages_shown" not in st.session_state:
    st.session_state.initial_messages_shown = False

if not st.session_state.initial_messages_shown:
    welcome_msg = "Hola! Soy Deltix. En qué te puedo ayudar? 🐱"
    help_msg = get_help_message()
    
    # Add to session state chat messages
    st.session_state.chat_messages.append({"role": "assistant", "content": welcome_msg})
    st.session_state.chat_messages.append({"role": "assistant", "content": help_msg})
    
    # Store in database
    store_chat_message(project_id, "assistant", welcome_msg)
    store_chat_message(project_id, "assistant", help_msg)
    
    st.session_state.initial_messages_shown = True

# Display all messages from the session state
for message in st.session_state.chat_messages:
    if message["role"] == "user":
        st.chat_message("user").write(message["content"])
    elif message["role"] == "assistant":
        st.chat_message("assistant", avatar="bot_icon.png").write(message["content"])
    elif message["role"] == "image":
        # For images we stored previously
        st.image(message["content"])

# Chat input
user_input = st.chat_input("Ingresa tu mensaje...")

def colectivas():
    msg = "Elegí la empresa de lancha colectiva:\n- **Jilguero**: va por el Carapachay-Angostura\n- **Interisleña**: Sarmiento, San Antonio y muchos más\n- **LineasDelta**: Caraguatá, Canal Arias, Paraná Miní"
    st.session_state.chat_messages.append({"role": "assistant", "content": msg})
    st.chat_message("assistant", avatar="bot_icon.png").write(msg)
    store_chat_message(project_id, "assistant", msg)
    st.session_state.colectivas_step = "select_company"

if user_input:
    # Always add the user message to chat history and display immediately
    st.session_state.chat_messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)
    store_chat_message(project_id, "user", user_input)
    
    if "marea" in user_input.lower() or "mareas" in user_input.lower():
        msg = "Sí, ahora te mando..."
        st.session_state.chat_messages.append({"role": "assistant", "content": msg})
        st.chat_message("assistant", avatar="bot_icon.png").write(msg)
        store_chat_message(project_id, "assistant", msg)
        
        if os.path.exists("marea.png"):
            # Update image in real-time by reading the file each time
            st.image("marea.png")
            st.session_state.chat_messages.append({"role": "image", "content": "marea.png"})
        else:
            error_msg = "Error: No se encontró el archivo de mareas."
            st.error(error_msg)
            st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})

    elif "windguru" in user_input.lower():
        msg = "Sí, ahora te mando..."
        st.session_state.chat_messages.append({"role": "assistant", "content": msg})
        st.chat_message("assistant", avatar="bot_icon.png").write(msg)
        store_chat_message(project_id, "assistant", msg)
        
        if os.path.exists("windguru.png"):
            # Update image in real-time by reading the file each time
            st.image("windguru.png")
            st.session_state.chat_messages.append({"role": "image", "content": "windguru.png"})
        else:
            error_msg = "Error: No se encontró el archivo de Windguru."
            st.error(error_msg)
            st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})

    elif "memes" in user_input.lower() or "meme" in user_input.lower() or st.session_state.get("wants_more_memes", False):
        msg = "Ya te mando un meme"
        st.session_state.chat_messages.append({"role": "assistant", "content": msg})
        st.chat_message("assistant", avatar="bot_icon.png").write(msg)
        store_chat_message(project_id, "assistant", msg)
        
        if "memes" in user_input.lower() or "meme" in user_input.lower():
            st.session_state.wants_more_memes = True
        
        if user_input.lower() == "no":
            st.session_state.wants_more_memes = False
            msg = "¡Espero que hayas disfrutado los memes!"
            st.session_state.chat_messages.append({"role": "assistant", "content": msg})
            st.chat_message("assistant", avatar="bot_icon.png").write(msg)
            store_chat_message(project_id, "assistant", msg)
        elif user_input.lower() == "si" or st.session_state.wants_more_memes:
            meme_file = get_random_meme()
            if meme_file:
                st.image(meme_file)
                st.session_state.chat_messages.append({"role": "image", "content": meme_file})
                store_chat_message(project_id, "meme", f"{meme_file}")
                
                if "meme_message_shown" not in st.session_state:
                    msg = "Buenísimo, no? Son de la página Memes Islenials. Te recomiendo que la sigas en las redes"
                    st.session_state.chat_messages.append({"role": "assistant", "content": msg})
                    st.chat_message("assistant", avatar="bot_icon.png").write(msg)
                    store_chat_message(project_id, "assistant", msg)
                    st.session_state.meme_message_shown = True
                
                msg = "¿Queres ver más memes? (Si/No)"
                st.session_state.chat_messages.append({"role": "assistant", "content": msg})
                st.chat_message("assistant", avatar="bot_icon.png").write(msg)
                store_chat_message(project_id, "assistant", msg)
            else:
                error_msg = "Error: No se encontraron archivos de memes."
                st.error(error_msg)
                st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
                st.session_state.wants_more_memes = False
        else:
            st.session_state.wants_more_memes = False

    elif "colectivas" in user_input.lower():
        colectivas()
    elif st.session_state.get("colectivas_step"):
        if not handle_colectivas_input(user_input):
            # Create a placeholder for the "thinking" message
            with st.chat_message("assistant", avatar="bot_icon.png"):
                thinking_placeholder = st.empty()
                thinking_placeholder.write("deltix pensando...")
                
                try:
                    documents = []
                    bot_reply = make_api_call(user_input, project_id, documents)
                    # Replace with actual response
                    thinking_placeholder.write(bot_reply)
                    st.session_state.chat_messages.append({"role": "assistant", "content": bot_reply})
                    store_chat_message(project_id, "assistant", bot_reply)
                except Exception as e:
                    error_msg = f"Error: {e}"
                    thinking_placeholder.error(error_msg)
                    st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
    elif contains_weather_keywords(user_input):
        # Create a placeholder for the "thinking" message
        with st.chat_message("assistant", avatar="bot_icon.png"):
            thinking_placeholder = st.empty()
            thinking_placeholder.write("deltix pensando...")
            
            try:
                documents = []
                bot_reply = make_api_call(user_input, project_id, documents)
                # Replace with actual response
                thinking_placeholder.write(bot_reply)
                st.session_state.chat_messages.append({"role": "assistant", "content": bot_reply})
                store_chat_message(project_id, "assistant", bot_reply)
            except Exception as e:
                error_msg = f"Error: {e}"
                thinking_placeholder.error(error_msg)
                st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
    else:
        # Create a placeholder for the "thinking" message
        with st.chat_message("assistant", avatar="bot_icon.png"):
            thinking_placeholder = st.empty()
            thinking_placeholder.write("deltix pensando...")
            
            try:
                documents = []
                bot_reply = make_api_call(user_input, project_id, documents)
                # Replace with actual response
                thinking_placeholder.write(bot_reply)
                st.session_state.chat_messages.append({"role": "assistant", "content": bot_reply})
                store_chat_message(project_id, "assistant", bot_reply)
            except Exception as e:
                error_msg = f"Error: {e}"
                thinking_placeholder.error(error_msg)
                st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
