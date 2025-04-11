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
