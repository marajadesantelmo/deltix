
import pandas as pd
from telegram import Bot
import os 
import urllib.request
import asyncio
import nest_asyncio
nest_asyncio.apply()

os.chdir('C:/Users/facun/OneDrive/Documentos/deltix/')
urllib.request.urlretrieve('https://alerta.ina.gob.ar/ina/42-RIODELAPLATA/productos/Prono_SanFernando.png', "marea.png")


subscribers = pd.read_csv("subscribers.csv")

bot = Bot(token="5712079875:AAHhIWwnHN5ws0DEUggA8-STWKmM-ZJ5hQE")  

async def send_image_to_subscribers():
    try:
        # Your code to send the image here
        for user_id in subscribers['User ID']:
            await bot.send_photo(user_id, open("Marea.png", "rb"))
    except Exception as e:
        # Handle any exceptions here
        print(f"Error sending image: {str(e)}")

if __name__ == '__main__':
    # Run the async function within an event loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(send_image_to_subscribers())