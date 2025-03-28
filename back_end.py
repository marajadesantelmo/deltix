'''
Deltix back_end
'''

from flask import Flask, request, jsonify
from supabase import create_client
from openai import OpenAI, AssistantEventHandler
import os
import json
import random
from datetime import datetime

app = Flask(__name__)

supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
openrouter_key = os.getenv('OPENROUTER_API_KEY')

if not supabase_url or not supabase_key:
    raise ValueError("Supabase URL and Key must be set in environment variables")

if not openrouter_key:
    raise ValueError("OpenRouter API Key must be set in environment variables")

supabase = create_client(supabase_url, supabase_key)

WEATHER_KEYWORDS = ['clima', 'temperatura', 'pronostico', 'tiempo', 'lluvia', 'viento', 'llover', 'soleado', 'ventoso', 'humedad', 'tormenta', 'nublado', 'calor', 'frio']
ALMACEN_KEYWORDS = ['almacen', 'almacén', 'almacenera', 'almaceneras']
JILGUERO_KEYWORDS = ['jilguero', 'carapachay', 'angostura']
INTERISLENA_KEYWORDS = ['interisleña', 'interislena', 'sarmiento', 'san antonio', 'capitan', 'capitán']
LINEASDELTA_KEYWORDS = ['lineasdelta', 'caraguatá', 'caraguata', 'canal arias', 'paraná miní', 'parana mini', 'lineas delta']

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_key,
)

def load_weather_data():
    try:
        weather_file_path = "rag/weather_data.json"
        with open(weather_file_path, 'r') as file:
            weather_data = json.load(file)
        return weather_data
    except Exception as e:
        print(f"Error loading weather data: {e}")
        return None

def format_weather_for_context(weather_data):
    if not weather_data:
        return ""
    try:
        current = weather_data.get('current_weather', {})
        location = current.get('name', 'Desconocido')
        country = current.get('sys', {}).get('country', '')
        temp = current.get('main', {}).get('temp', 'N/A')
        feels_like = current.get('main', {}).get('feels_like', 'N/A')
        description = current.get('weather', [{}])[0].get('description', 'N/A')
        humidity = current.get('main', {}).get('humidity', 'N/A')
        wind_speed = current.get('wind', {}).get('speed', 'N/A')
        timestamp_str = weather_data.get('timestamp', 'Desconocido')
        forecast_items = weather_data.get('forecast', {}).get('list', [])[:8]
        forecast_text = ""
        for item in forecast_items:
            dt_txt = item.get('dt_txt', '')
            temp_forecast = item.get('main', {}).get('temp', 'N/A')
            desc_forecast = item.get('weather', [{}])[0].get('description', 'N/A')
            forecast_text += f"- {dt_txt}: {temp_forecast}°C, {desc_forecast}\n"
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
    lower_input = user_input.lower()
    return any(keyword in lower_input for keyword in WEATHER_KEYWORDS)

def contains_almacen_keywords(user_input):
    lower_input = user_input.lower()
    return any(keyword in lower_input for keyword in ALMACEN_KEYWORDS)

def contains_jilguero_keywords(user_input):
    lower_input = user_input.lower()
    return any(keyword in lower_input for keyword in JILGUERO_KEYWORDS)

def contains_interislena_keywords(user_input):
    lower_input = user_input.lower()
    return any(keyword in lower_input for keyword in INTERISLENA_KEYWORDS)

def contains_lineasdelta_keywords(user_input):
    lower_input = user_input.lower()
    return any(keyword in lower_input for keyword in LINEASDELTA_KEYWORDS)

def load_almacen_data():
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

def load_transportation_data(company_name):
    try:
        file_path = os.path.join(os.getcwd(), "rag", f"{company_name}.txt")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        else:
            print(f"Transportation data file not found at: {file_path}")
            return ""
    except Exception as e:
        print(f"Error loading transportation data: {e}")
        return ""

def make_api_call(user_input, project_id, documents, retries=3, delay=2):
    try:
        context = []
        if any(keyword in user_input.lower() for keyword in ['seguridad', 'policia', 'emergencia', 'telefono']):
            with open("rag/policia.txt", "r") as file:
                context.append(file.read())
        if contains_weather_keywords(user_input):
            weather_data = load_weather_data()
            if weather_data:
                weather_context = format_weather_for_context(weather_data)
                context.append(weather_context)
        if contains_almacen_keywords(user_input):
            almacen_context = load_almacen_data()
            if almacen_context:
                context.append(f"Información sobre almacenes de la isla:\n{almacen_context}")
        if contains_jilguero_keywords(user_input):
            jilguero_context = load_transportation_data("jilguero")
            if jilguero_context:
                context.append(f"Información sobre la lancha colectiva Jilguero:\n{jilguero_context}")
        if contains_interislena_keywords(user_input):
            interislena_context = load_transportation_data("interislena")
            if interislena_context:
                context.append(f"Información sobre la lancha colectiva Interisleña:\n{interislena_context}")
        if contains_lineasdelta_keywords(user_input):
            lineasdelta_context = load_transportation_data("lineasdelta")
            if lineasdelta_context:
                context.append(f"Información sobre la lancha colectiva LineasDelta:\n{lineasdelta_context}")
        previous_messages = supabase.from_("chat_history").select("*").eq("project_id", project_id).execute().data
        previous_messages_content = "\n".join([msg["content"] for msg in previous_messages if msg["role"] == "user"][-5:])
        context_text = "\n\n".join(context)
        for attempt in range(retries):
            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "<YOUR_SITE_URL>",
                    "X-Title": "<YOUR_SITE_NAME>",
                },
                extra_body={},
                model="deepseek/deepseek-chat:free",
                messages=[
                    {
                        "role": "system",
                        "content": "Vos sos Deltix, el bot del humedal. Eres argentino y amable. Ingresando algunas de estas palabras el usuario puede obtener información útil: mareas: obtener el pronóstico de mareas, windguru: pronóstico meteorológico de windgurú, Colectivas: horarios de lanchas colectivas, memes: ver los memes más divertidos de la isla, clima/pronostico: información meteorológica actualizada, almaceneras: información sobre almacenes de la isla. Si hay información de contexto, intenta responder con esa información o guia al usuario para que ingrese las palabras clave"
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

def colectivas():
    msg = "Elegí la empresa de lancha colectiva:\n- **Jilguero**: va por el Carapachay-Angostura\n- **Interisleña**: Sarmiento, San Antonio y muchos más\n- **LineasDelta**: Caraguatá, Canal Arias, Paraná Miní"
    st.session_state.chat_messages.append({"role": "assistant", "content": msg})
    st.chat_message("assistant", avatar="bot_icon.png").write(msg)
    store_chat_message(project_id, "assistant", msg)
    st.session_state.colectivas_step = "select_company"

def handle_colectivas_input(user_input):
    # Implement the logic to handle user input for colectivas
    pass

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('user_input')
    project_id = data.get('project_id')
    documents = data.get('documents', [])
    response_content = make_api_call(user_input, project_id, documents)
    store_chat_message(project_id, "user", user_input)
    store_chat_message(project_id, "assistant", response_content)
    return jsonify({"response": response_content})

@app.route('/api/create_project', methods=['POST'])
def create_new_project():
    project_id = create_project()
    return jsonify({"project_id": project_id})

@app.route('/api/get_random_meme', methods=['GET'])
def random_meme():
    meme_file = get_random_meme()
    return jsonify({"meme_file": meme_file})

if __name__ == '__main__':
    app.run(debug=True)