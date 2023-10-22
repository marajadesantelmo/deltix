import pandas as pd
from telegram import Bot
import urllib.request
import asyncio
import nest_asyncio
import datetime
import os

nest_asyncio.apply()

telegram_token = os.environ.get('telegram_token')
bot = Bot(token=telegram_token) 

urllib.request.urlretrieve('https://alerta.ina.gob.ar/ina/42-RIODELAPLATA/productos/Prono_SanFernando.png', "Marea.png")
# subscribers = pd.read_csv("C://Users//Usuario//Documents//GitHub//deltix//subscribers.csv")
subscribers = pd.read_csv("subscribers2.csv")
envio_diarios_log = pd.read_csv('envio_diario_log.csv')


async def send_image_to_subscribers():
    global envio_diarios_log
    log_entries = []  
    try:
        for user_id in subscribers['User ID']:
            print(f'enviando a {user_id}')
            user_name = subscribers.loc[subscribers['User ID'] == user_id, 'First Name'].values[0]
            await asyncio.wait_for(bot.send_photo(user_id, open("Marea.png", "rb")), timeout=12000)
            log_entry = {'Timestamp': datetime.datetime.now(), 
                         'User ID': user_id, 
                         'user_name': user_name}
            log_entries.append(log_entry)
    except asyncio.TimeoutError:
        user_name = "Operation timed out"
        print("Operation timed out")
        log_entry = {'Timestamp': datetime.datetime.now(), 
                     'User ID': user_id, 
                     'user_name': user_name}
        log_entries.append(log_entry)
    except Exception as e:
        user_name = f"{str(e)}"
        print(f"Error sending image to user {user_id}: {str(e)}")
        log_entry = {'Timestamp': datetime.datetime.now(), 
                     'User ID': user_id, 
                     'user_name': user_name}
        log_entries.append(log_entry)

    envio_diarios_log = pd.concat([envio_diarios_log, pd.DataFrame(log_entries)], ignore_index=True)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(send_image_to_subscribers())
    envio_diarios_log.to_csv('envio_diario_log.csv', index=False)