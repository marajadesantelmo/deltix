import pandas as pd
from telegram import Bot
import asyncio
import nest_asyncio
import datetime
from tokens import telegram_token

nest_asyncio.apply()

bot = Bot(token=telegram_token)

subscribers_hidrografia = pd.read_csv("/home/facundol/deltix/subscribers_hidrografia.csv")
#subscribers_hidrografia = pd.read_csv("subscribers_hidrografia.csv")

envio_diarios_log = pd.read_csv('/home/facundol/deltix/envio_diario_log.csv')

async def send_image_to_subscribers():
    global envio_diarios_log
    log_entries = []

    #Envios a suscriptos para hidrografia
    try:
        for user_id in subscribers_hidrografia['User ID']:
            print(f'enviando hidrografia a {user_id}')
            user_name = subscribers_hidrografia.loc[subscribers_hidrografia['User ID'] == user_id, 'First Name'].values[0]
            with open("/home/facundol/deltix/table_data.txt", "r") as file:
                content = file.read()
            await asyncio.wait_for(bot.send_message(user_id, content), timeout=12000)
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

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(send_image_to_subscribers())
    envio_diarios_log.to_csv('/home/facundol/deltix/envio_diario_log.csv', index=False)