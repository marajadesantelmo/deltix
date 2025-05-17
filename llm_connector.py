import os
import json
import time
from openai import OpenAI
import mysql.connector
from mysql.connector import Error


# Load environment variables or tokens
try:
    from tokens import openrouter_key, mysql_password, mysql_database
except ImportError:
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    mysql_password = os.getenv('MYSQL_PASSWORD')
    mysql_database = os.getenv('MYSQL_DATABASE')

# Database connection function with reconnect capability
def get_db_connection():
    """Create or refresh a database connection and return it"""
    try:
        # Check if there's a global connection that's still active
        global db
        if 'db' in globals() and db.is_connected():
            return db
        
        # Create a new connection
        db = mysql.connector.connect(
            host="facundol.mysql.pythonanywhere-services.com",
            user="facundol",
            password=mysql_password,
            database=mysql_database,
            use_pure=True,  # Use pure Python implementation for better compatibility
            connection_timeout=30
        )
        print("Database connection established")
        return db
    except Error as err:
        print(f"Error connecting to database: {err}")
        raise

# Initial database connection
try:
    db = get_db_connection()
except Error as err:
    print(f"Initial database connection failed: {err}")
    # Continue execution as we'll try to reconnect when needed

# Validate environment variables
if not openrouter_key:
    raise ValueError("OpenRouter API Key must be set in environment variables")

# Initialize OpenAI client
openai_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key)

# Keywords for context generation
KEYWORDS = {
    "weather": ['clima', 'temperatura', 'pronostico', 'tiempo', 'lluvia', 'viento', 'llover', 'soleado', 'ventoso', 'humedad', 'tormenta', 'nublado', 'calor', 'frio'],
    "almacen": ['almacen', 'almacén', 'almacenera', 'almaceneras'],
    "jilguero": ['jilguero', 'carapachay', 'angostura'],
    "interislena": ['interisleña', 'interislena', 'sarmiento', 'san antonio', 'capitan', 'capitán'],
    "lineasdelta": ['lineasdelta', 'caraguatá', 'caraguata', 'canal arias', 'paraná miní', 'parana mini', 'lineas delta'],
    "activities": ['actividades', 'emprendimientos', 'hacer', 'visitar', 'conocer', 'experiencias', 'atracciones', 'paseos', 'canoa', 'kayak', 'arcilla', 'barro', 'alfareria', 'hospedaje']
}

class ContextManager:
    """Manages context generation based on user input."""
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

    def load_file(self, filename):
        """Load content from a file in the 'rag' directory."""
        try:
            file_path = os.path.join(self.base_dir, "rag", filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            print(f"File not found: {filename}")
            return ""
        except Exception as e:
            print(f"Error loading file {filename}: {e}")
            return ""

    def load_weather_data(self):
        """Load weather data from a JSON file."""
        try:
            weather_file = os.path.join(self.base_dir, "rag", "weather_data.json")
            with open(weather_file, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            print("Weather data file not found.")
            return None
        except Exception as e:
            print(f"Error loading weather data: {e}")
            return None

    def generate_context(self, user_input):
        """Generate context based on user input."""
        context = []

        # Add weather data if applicable
        if any(keyword in user_input.lower() for keyword in KEYWORDS["weather"]):
            weather_data = self.load_weather_data()
            if (weather_data):
                context.append(self.format_weather_data(weather_data))
            else:
                context.append("No se pudo cargar la información del clima en este momento.")

        # Add other context files based on keywords
        if any(keyword in user_input.lower() for keyword in KEYWORDS["almacen"]):
            context.append(self.load_file("almaceneras.txt"))
        if any(keyword in user_input.lower() for keyword in KEYWORDS["jilguero"]):
            context.append(self.load_file("jilguero.txt"))
        if any(keyword in user_input.lower() for keyword in KEYWORDS["interislena"]):
            context.append(self.load_file("interislena.txt"))
        if any(keyword in user_input.lower() for keyword in KEYWORDS["lineasdelta"]):
            context.append(self.load_file("lineasdelta.txt"))
        if any(keyword in user_input.lower() for keyword in KEYWORDS["activities"]):
            context.append(self.load_file("actividades.txt"))

        return "\n\n".join(context) if context else "No hay contexto disponible."

    def format_weather_data(self, weather_data):
        """Format weather data into a readable string."""
        try:
            current = weather_data.get('current_weather', {})
            location = current.get('name', 'Desconocido')
            temp = current.get('main', {}).get('temp', 'N/A')
            description = current.get('weather', [{}])[0].get('description', 'N/A')
            return f"Clima actual en {location}: {temp}°C, {description}"
        except Exception as e:
            print(f"Error formatting weather data: {e}")
            return "Información del clima no disponible."

class LLMClient:
    """Handles interactions with the LLM."""
    def __init__(self, client, retries=3, delay=2):
        self.client = client
        self.retries = retries
        self.delay = delay

    def get_response(self, user_input, context, phone_number):
        """Get a response from the LLM."""
        conn = get_db_connection()
        cursor = conn.cursor()    
        cursor.execute("SELECT id FROM conversations WHERE name = %s", (phone_number,))
        conversation_id = cursor.fetchone()   

        if conversation_id is None:
            print(f"No conversation found for phone: {phone_number}. Creating a new one.")
            conversation_id = create_conversation(phone_number)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Handle both cases where conversation_id might be subscriptable or an int
        if isinstance(conversation_id, tuple) or isinstance(conversation_id, list):
            conversation_id_value = conversation_id[0]
        else:
            conversation_id_value = conversation_id

        cursor.execute(
            "SELECT content FROM chat_history WHERE conversation_id = %s ORDER BY created_at DESC LIMIT 5", (conversation_id_value,)
        )
        chat_history = cursor.fetchall()
        chat_history = [message for message in chat_history]
        

        system_prompt = (
            "Vos sos Deltix, el bot del humedal. Sos un carpincho digital que ayuda a habitantes y visitantes del Delta del Paraná en Tigre. "
            "Responde al último mensaje del usuario usando el contexto proporcionado. No inventes información ni alucines. Tu opinión es anticapitalista y ambientalista. "
            "Si no puedes responder, guía al usuario para que ingrese palabras clave como: clima, mareas, windguru, colectivas, almaceneras, hidrografia, actividades"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Mensaje: {user_input}\n\nContexto:\n{context}\n\nHistorial de chat con el usuario:\n{chat_history}"},
        ]

        for attempt in range(self.retries):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek/deepseek-chat",
                    messages=messages
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self.retries - 1:
                    raise
                time.sleep(self.delay)

# Public API
def conversation_exists(phone_number):
    """Check if a conversation exists in the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM conversations WHERE name = %s", (phone_number,))
        result = cursor.fetchone()
        cursor.close()
        return result[0]
    except Error as err:
        print(f"Error checking conversation: {err}")
        return False

def create_conversation(phone_number="Nueva conversacion"):
    """Create a new conversation in MySQL."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("INSERT INTO conversations (name, created_at) VALUES (%s, NOW())", (phone_number,))
        conn.commit()
        conversation_id = cursor.lastrowid
        cursor.close()
        print(f"Created new conversation with ID: {conversation_id} for phone: {phone_number}")
        return conversation_id
    except Error as err:
        print(f"Error creating conversation: {err}")
        if conn:
            conn.rollback()
        raise

def get_or_create_conversation(phone_number=None):
    """Get an existing conversation or create a new one if invalid."""
    try:
        # If we have a valid conversation_id, use it
        conversation_id = conversation_exists(phone_number)
        if conversation_id: 
            print(f"Using existing conversation ID: {conversation_id} for phone: {phone_number}")
            return conversation_id
    
        else:
            print(f"No existing conversation found for phone: {phone_number}. Creating a new one.")
            conversation_id = create_conversation(phone_number)
            return conversation_id
    except Error as err:
        print(f"Error getting or creating conversation: {err}")
        return None
        
def store_chat_message(phone_number, role, content):
    """Store a chat message in MySQL."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # get conversation ID from the database by phone number
        cursor.execute("SELECT id FROM conversations WHERE name = %s", (phone_number,))
        conversation_id = cursor.fetchone()   

        conn = get_db_connection()
        cursor = conn.cursor()    
        cursor.execute(
            "INSERT INTO chat_history (conversation_id, role, content) VALUES (%s, %s, %s)",
            (conversation_id[0], role, content)
        )
        conn.commit()
        
        # Verify insertion
        message_id = cursor.lastrowid
        print(f"Message stored with ID: {message_id}")
        
        cursor.close()
        return True
    except Error as err:
        print(f"Error storing chat message: {err}")
        if 'conn' in locals() and conn:
            conn.rollback()
        return False

def get_llm_response(user_input, phone_number=None):
    """Main function to get a response from the LLM."""
    try:               
        context_manager = ContextManager()
        llm_client = LLMClient(openai_client)
        # Generate context
        context = context_manager.generate_context(user_input)
        # Get response from LLM
        response = llm_client.get_response(user_input, context, phone_number)
        # Store messages in MySQL
        user_stored = store_chat_message(phone_number, "user", user_input)
        assistant_stored = store_chat_message(phone_number, "assistant", response)
        
        if not user_stored or not assistant_stored:
            print("Warning: Failed to store one or more chat messages")

        return response
    except Exception as e:
        print(f"Error in get_llm_response: {e}")
        # Return a fallback message and the conversation ID if we have one
        fallback_msg = "Lo siento, tuve un problema técnico. Por favor, intentá nuevamente en unos momentos."
        return fallback_msg or create_conversation()
