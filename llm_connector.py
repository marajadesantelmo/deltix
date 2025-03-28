from supabase import create_client
from openai import OpenAI
import os
import json
import time
from tokens import supabase_url, supabase_key, openrouter_key

# Environment variables
#supabase_url = os.getenv('SUPABASE_URL')
#supabase_key = os.getenv('SUPABASE_KEY')
#openrouter_key = os.getenv('OPENROUTER_API_KEY')

# Validate environment variables
if not supabase_url or not supabase_key:
    raise ValueError("Supabase URL and Key must be set in environment variables")

if not openrouter_key:
    raise ValueError("OpenRouter API Key must be set in environment variables")

# Initialize Supabase client
supabase = create_client(supabase_url, supabase_key)

# Initialize OpenAI client for OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_key,
)

# Keywords for context retrieval
WEATHER_KEYWORDS = ['clima', 'temperatura', 'pronostico', 'tiempo', 'lluvia', 'viento', 'llover', 'soleado', 'ventoso', 'humedad', 'tormenta', 'nublado', 'calor', 'frio']
ALMACEN_KEYWORDS = ['almacen', 'almacén', 'almacenera', 'almaceneras']
JILGUERO_KEYWORDS = ['jilguero', 'carapachay', 'angostura']
INTERISLENA_KEYWORDS = ['interisleña', 'interislena', 'sarmiento', 'san antonio', 'capitan', 'capitán']
LINEASDELTA_KEYWORDS = ['lineasdelta', 'caraguatá', 'caraguata', 'canal arias', 'paraná miní', 'parana mini', 'lineas delta']

def create_project():
    """Create a new conversation project in Supabase"""
    response = supabase.from_("projects").insert({"name": "Nueva conversacion"}).execute()
    return response.data[0]["id"]

def store_chat_message(project_id, role, content):
    """Store a chat message in Supabase"""
    supabase.from_("chat_history").insert({"project_id": project_id, "role": role, "content": content}).execute()

def contains_keywords(user_input, keyword_list):
    """Check if user input contains any of the keywords in the list"""
    lower_input = user_input.lower()
    return any(keyword in lower_input for keyword in keyword_list)

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

def load_file_content(filename):
    """Load content from a text file in the rag directory"""
    try:
        file_path = os.path.join(os.getcwd(), "rag", filename)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        else:
            print(f"File not found at: {file_path}")
            return ""
    except Exception as e:
        print(f"Error loading file {filename}: {e}")
        return ""

def get_llm_response(user_input, project_id=None, previous_messages=None, retries=3, delay=2):
    """Get a response from the LLM with context from the RAG system"""
    if project_id is None:
        project_id = create_project()
    
    try:
        # Prepare context based on user input
        context = []
        
        # Check for security/emergency keywords
        if any(keyword in user_input.lower() for keyword in ['seguridad', 'policia', 'emergencia', 'telefono']):
            context.append(load_file_content("policia.txt"))
        
        # Add weather data if applicable
        if contains_keywords(user_input, WEATHER_KEYWORDS):
            weather_data = load_weather_data()
            if weather_data:
                weather_context = format_weather_for_context(weather_data)
                context.append(weather_context)

        # Add almacen data if applicable
        if contains_keywords(user_input, ALMACEN_KEYWORDS):
            almacen_context = load_file_content("almaceneras.txt")
            if almacen_context:
                context.append(f"Información sobre almacenes de la isla:\n{almacen_context}")
        
        # Add transportation data if applicable
        if contains_keywords(user_input, JILGUERO_KEYWORDS):
            context.append(f"Información sobre la lancha colectiva Jilguero:\n{load_file_content('jilguero.txt')}")
                
        if contains_keywords(user_input, INTERISLENA_KEYWORDS):
            context.append(f"Información sobre la lancha colectiva Interisleña:\n{load_file_content('interislena.txt')}")
                
        if contains_keywords(user_input, LINEASDELTA_KEYWORDS):
            context.append(f"Información sobre la lancha colectiva LineasDelta:\n{load_file_content('lineasdelta.txt')}")
        
        # Get previous messages if not provided
        if previous_messages is None:
            previous_messages = supabase.from_("chat_history").select("*").eq("project_id", project_id).execute().data
        
        previous_messages_content = "\n".join([msg["content"] for msg in previous_messages if msg["role"] == "user"][-5:])
        
        context_text = "\n\n".join(context)
        
        # Make request to LLM with retries
        for attempt in range(retries):
            try:
                response = client.chat.completions.create(
                    extra_body={},
                    model="deepseek/deepseek-chat:free",
                    messages=[
                        {
                            "role": "system",
                            "content": "Vos sos Deltix, el bot del humedal. Eres argentino y amable. Ingresando algunas de estas palabras el usuario puede obtener información útil: mareas: obtener el pronóstico de mareas, windguru: pronóstico meteorológico de windgurú, Colectivas: horarios de lanchas colectivas, memes: ver los memes más divertidos de la isla, almaceneras: información sobre lanchas almacenes de la isla, suscribirme: suscribirte a los envios automaticos de mareas y pronostico. Si hay información de contexto, intenta responder con esa información sin inventar ni alucinar. Responde al ultimo mensaje del usuario. Si no lo puedes responder, guia al usuario para que ingrese alguna de las palabras clave."
                        },
                        {
                            "role": "user",
                            "content": f"Ultimo mensaje:\n\n {user_input}\n\nMensajes anteriores:\n{previous_messages_content}\n\nContexto:\n{context_text}"
                        }
                    ]
                )
                
                # Store the message and response in Supabase
                store_chat_message(project_id, "user", user_input)
                response_text = response.choices[0].message.content
                store_chat_message(project_id, "assistant", response_text)
                
                return response_text
            
            except Exception as e:
                if attempt == retries - 1:
                    raise e
                time.sleep(delay)
    
    except Exception as e:
        error_message = f"Error getting LLM response: {str(e)}"
        print(error_message)
        return f"Lo siento, ocurrió un error al procesar tu mensaje. Por favor, intenta de nuevo más tarde."
