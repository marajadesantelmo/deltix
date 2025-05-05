import pandas as pd
from telegram import Bot
import asyncio
import nest_asyncio
import datetime
from tokens import telegram_token

nest_asyncio.apply()

bot = Bot(token=telegram_token)

subscribers_mareas = pd.read_csv("/home/facundol/deltix/subscribers_mareas.csv")
#subscribers_mareas = pd.read_csv("subscribers_mareas2.csv")

subscribers_windguru = pd.read_csv("/home/facundol/deltix/subscribers_windguru.csv")
#subscribers_windguru = pd.read_csv("subscribers_windguru2.csv")

subscribers_hidrografia = pd.read_csv("/home/facundol/deltix/subscribers_hidrografia.csv")
#subscribers_hidrografia = pd.read_csv("subscribers_hidrografia.csv")

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
        log_entries.append(log_entry)

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

    #Envios a suscriptos para hidrografia
    try:
        for user_id in subscribers_hidrografia['User ID']:
            print(f'enviando hidrografia a {user_id}')
            user_name = subscribers_hidrografia.loc[subscribers_hidrografia['User ID'] == user_id, 'First Name'].values[0]
            
            # Read and format data from table_data.txt
            with open("/home/facundol/deltix/table_data.txt", "r") as file:
                lines = file.readlines()
            
            if not lines:
                content = "Lo siento, no tengo datos de mareas de hidrografía en este momento."
            else:
                formatted_message = "<b>📊 PRONÓSTICO DE MAREAS - HIDROGRAFÍA NAVAL</b>\n\n"
                if len(lines) > 0:
                    port_name = lines[0].strip()
                    formatted_message += f"<b>🚢 {port_name}</b>\n\n"
                if len(lines) > 2:
                    for line in lines[2:]:
                        data = line.strip().split('\t')
                        if len(data) >= 4:
                            tide_type = data[0]
                            time = data[1]
                            height = data[2]
                            date = data[3]
                            emoji = "🌊" if tide_type == "PLEAMAR" else "⬇️"
                            formatted_message += f"{emoji} <b>{tide_type}</b>: {time} hs - {height} m ({date})\n"
                content = formatted_message
            
            await asyncio.wait_for(bot.send_message(user_id, content, parse_mode='HTML'), timeout=12000)
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
        print(f"Error sending text to user {user_id}: {str(e)}")
        log_entry = {'Timestamp': datetime.datetime.now(),
                     'User ID': user_id,
                     'user_name': user_name}
        log_entries.append(log_entry)

    envio_diarios_log = pd.concat([envio_diarios_log, pd.DataFrame(log_entries)], ignore_index=True)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(send_image_to_subscribers())
    envio_diarios_log.to_csv('/home/facundol/deltix/envio_diario_log.csv', index=False)