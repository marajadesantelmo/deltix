"""
Utility functions for formatting WhatsApp messages 
and handling media for the Deltix bot.
"""

import requests
import os
import random
from datetime import datetime

def format_whatsapp_text(text):
    """
    Format text for WhatsApp - convert HTML tags to WhatsApp formatting.
    
    WhatsApp uses:
    *bold*
    _italic_
    ~strikethrough~
    ```code```
    """
    # Replace HTML formatting with WhatsApp formatting
    formatted = text.replace("<b>", "*").replace("</b>", "*")
    formatted = formatted.replace("<i>", "_").replace("</i>", "_")
    formatted = formatted.replace("<s>", "~").replace("</s>", "~")
    formatted = formatted.replace("<code>", "```").replace("</code>", "```")
    
    return formatted

def download_media_from_github(filename, base_url="https://raw.githubusercontent.com/marajadesantelmo/deltix/main/"):
    """
    Download media from GitHub repository and return the local path.
    This is useful for PythonAnywhere which may need to download media files.
    """
    url = f"{base_url}{filename}"
    local_path = f"/tmp/{filename.replace('/', '_')}"
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    # Download the file
    response = requests.get(url)
    if response.status_code == 200:
        with open(local_path, 'wb') as f:
            f.write(response.content)
        return local_path
    else:
        raise Exception(f"Failed to download file: {url}, Status code: {response.status_code}")

def format_mareas_data(data_text):
    """Format mareas data from Hidrografia Naval for WhatsApp"""
    lines = data_text.strip().splitlines()
    if not lines:
        return "Sin datos disponibles"
    
    formatted = "📊 *PRONÓSTICO DE MAREAS - HIDROGRAFÍA NAVAL*\n\n"
    
    # First line contains the port name
    if len(lines) > 0:
        port_name = lines[0].strip()
        formatted += f"🚢 *{port_name}*\n\n"
    
    # Skip header line and process data
    if len(lines) > 2:
        for line in lines[2:]:
            data = line.strip().split('\t')
            if len(data) >= 4:
                tide_type = data[0]
                time = data[1]
                height = data[2]
                date = data[3]
                
                emoji = "🌊" if tide_type == "PLEAMAR" else "⬇️"
                formatted += f"{emoji} *{tide_type}*: {time} hs - {height} m ({date})\n"
    
    return formatted

def get_random_meme_url(count=56):
    """Return URL for a random meme from the Deltix repository"""
    meme_number = random.randint(1, count)
    return f"https://raw.githubusercontent.com/marajadesantelmo/deltix/main/memes/{meme_number}.png"

def format_date_spanish(date_obj=None):
    """Format date in Spanish"""
    if date_obj is None:
        date_obj = datetime.now()
    
    months = ["enero", "febrero", "marzo", "abril", "mayo", "junio", 
              "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    
    day = date_obj.day
    month = months[date_obj.month - 1]
    year = date_obj.year
    
    return f"{day} de {month} de {year}"

def format_almacenera_data(almacenera_name, almacenera_info):
    """Format almacenera data for WhatsApp message"""
    formatted = f"*{almacenera_name}* "
    
    if almacenera_info.get('propietario'):
        formatted += f"de {almacenera_info['propietario']}\n\n"
    
    if almacenera_info.get('recorridos'):
        formatted += f"{almacenera_info['recorridos']}\n\n"
    
    if almacenera_info.get('telefono'):
        formatted += f"📞 *Teléfono*: {almacenera_info['telefono']}"
    
    return formatted

def format_colectivas_menu():
    """Format colectivas menu for WhatsApp"""
    return (
        "Elegí la empresa de lancha colectiva:\n\n"
        "- *Jilguero* _va por el Carapachay-Angostura_\n"
        "- *Interisleña* _Sarmiento, San Antonio y muchos más_\n"
        "- *Lineas Delta* _Caraguatá, Canal Arias, Paraná Miní_\n\n"
        "Responde con el nombre de la empresa que te interesa."
    )

def format_activity_info(activity_name):
    """Format activity information for WhatsApp based on name"""
    activities = {
        "amanita": {
            "title": "Experiencias en Canoa Isleña",
            "details": [
                "Paseos por el Delta del Paraná",
                "Con Guía Bilingüe (opcional)",
                "Servicio puerta a puerta (opcional)"
            ],
            "contact": "Contacto: 1169959272",
            "social": "instagram.com/amanitaturismodelta"
        },
        "alfareria": {
            "title": "Kutral Alfarería",
            "details": [
                "Encuentros con el barro",
                "Talleres de alfarería",
                "Experimentación y creación con arcilla"
            ],
            "contact": "",
            "social": "instagram.com/kutralalfareria"
        },
        "labusqueda": {
            "title": "La Búsqueda",
            "details": [
                "Espacio para encuentros y ceremonias",
                "Hostal en el Delta",
                "Conexión con la naturaleza"
            ],
            "contact": "Contacto: 1150459556",
            "social": "instagram.com/labusqueda_cabanadelta"
        },
        "canaveralkayaks": {
            "title": "Cañaveral Kayaks",
            "details": [
                "Excursiones en Kayak",
                "Paseos con guía",
                "Remadas nocturnas"
            ],
            "contact": "Contacto: 1126961274",
            "social": "linktr.ee/canaveralkayaks"
        }
    }
    
    if activity_name.lower() not in activities:
        return f"No se encontró información para {activity_name}"
    
    info = activities[activity_name.lower()]
    formatted = f"*{info['title']}*\n\n"
    
    for detail in info['details']:
        formatted += f"_{detail}_\n"
    
    formatted += "\n"
    
    if info['social']:
        formatted += f"{info['social']}\n"
    
    if info['contact']:
        formatted += f"{info['contact']}"
    
    return formatted

def get_media_url(filename):
    """Get the URL for media files from GitHub repository"""
    return f"https://raw.githubusercontent.com/marajadesantelmo/deltix/main/{filename}"

def format_weather_data(data):
    """Format weather data for WhatsApp"""
    if not data:
        return "Sin datos disponibles del clima"
    
    try:
        current = data.get('current_weather', {})
        location = current.get('name', 'Desconocido')
        temp = current.get('main', {}).get('temp', 'N/A')
        description = current.get('weather', [{}])[0].get('description', 'N/A')
        humidity = current.get('main', {}).get('humidity', 'N/A')
        wind_speed = current.get('wind', {}).get('speed', 'N/A')
        
        forecast_items = data.get('forecast', {}).get('list', [])[:3]  # First 9 hours
        forecast_text = ""
        
        for item in forecast_items:
            dt_txt = item.get('dt_txt', '').split(' ')[1][:5]  # Time only
            temp_forecast = item.get('main', {}).get('temp', 'N/A')
            desc_forecast = item.get('weather', [{}])[0].get('description', 'N/A')
            forecast_text += f"🕒 *{dt_txt}*: {temp_forecast}°C, _{desc_forecast}_\n"
        
        formatted = (
            f"🌦️ *PRONÓSTICO DEL TIEMPO - {location.upper()}*\n\n"
            f"🌡️ *Temperatura actual*: {temp}°C\n"
            f"🌤️ *Condición*: {description}\n"
            f"💧 *Humedad*: {humidity}%\n"
            f"💨 *Viento*: {wind_speed} m/s\n\n"
            f"*Próximas horas:*\n{forecast_text}"
        )
        
        return formatted
    except Exception as e:
        return f"Error al formatear datos del clima: {str(e)}"

def create_simple_buttons(options):
    """Format options as simple WhatsApp button UI simulation"""
    formatted = "Opciones disponibles:\n\n"
    for option in options:
        formatted += f"• *{option}*\n"
    formatted += "\n_Escribe tu elección_"
    return formatted

def format_message_receipt(message_text, user_name):
    """Format receipt message for user messages sent to developers"""
    return (
        f"✅ *Mensaje enviado exitosamente*\n\n"
        f"Tu mensaje ha sido enviado al equipo de Deltix. "
        f"Gracias por ayudarnos a mejorar, {user_name}!"
    )
