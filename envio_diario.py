import pandas as pd
from telegram import Bot
import asyncio
import nest_asyncio
import datetime

nest_asyncio.apply()

bot = Bot(token='5712079875:AAHhIWwnHN5ws0DEUggA8-STWKmM-ZJ5hQE')

subscribers_mareas = pd.read_csv("/home/facundol/deltix/subscribers_mareas.csv")
#subscribers_mareas = pd.read_csv("subscribers_mareas2.csv")

subscribers_windguru = pd.read_csv("/home/facundol/deltix/subscribers_windguru.csv")
#subscribers_windguru = pd.read_csv("subscribers_windguru2.csv")

envio_diarios_log = pd.read_csv('/home/facundol/deltix/envio_diario_log.csv')

async def send_image_to_subscribers():
    global envio_diarios_log
    log_entries = []

    #Envios a suscriptos para mareas
    try:
        for user_id in subscribers_mareas['User ID']:
            print(f'enviando a {user_id}')
            user_name = subscribers_mareas.loc[subscribers_mareas['User ID'] == user_id, 'First Name'].values[0]
            #await bot.send_message(user_id, "Mi desarrollador aprendió a programar gracias a la educación pública, gratuita y de calidad!")
            await asyncio.wait_for(bot.send_photo(user_id, open("/home/facundol/deltix/marea.png", "rb")), timeout=12000)
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

    #Envios a suscriptos para windguru
    try:
        for user_id in subscribers_windguru['User ID']:
            print(f'enviando a {user_id}')
            user_name = subscribers_windguru.loc[subscribers_windguru['User ID'] == user_id, 'First Name'].values[0]
            await asyncio.wait_for(bot.send_photo(user_id, open("/home/facundol/deltix/windguru.png", "rb")), timeout=12000)
            log_entry = {'Timestamp': datetime.datetime.now(),
                         'User ID': user_id,
                         'user_name': user_name}
            log_entries.append(log_entry)
    except asyncio.TimeoutError:                 #Tengo en cuenta excepciones para chequear problemas de conexion
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
    envio_diarios_log.to_csv('/home/facundol/deltix/envio_diario_log.csv', index=False)