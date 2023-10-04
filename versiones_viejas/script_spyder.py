
#%% 
import os 
import urllib.request
import telebot
import schedule
import time

#%% 
os.chdir('/Users/facun/deltix/')
urllib.request.urlretrieve('https://alerta.ina.gob.ar/ina/42-RIODELAPLATA/productos/Prono_SanFernando.png', "Marea.png")

#%% 
token= "5712079875:AAHhIWwnHN5ws0DEUggA8-STWKmM-ZJ5hQE"

#%% 

# URL de la imagen del pronóstico de mareas
IMAGEN_URL = "https://alerta.ina.gob.ar/ina/42-RIODELAPLATA/productos/Prono_SanFernando.png"

# Lista para almacenar los números de teléfono de los suscriptores
suscriptores = []

# Crea una instancia del bot
bot = telebot.TeleBot(token)

# Manejador del comando /start o al enviar el primer mensaje
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, f"Hola {message.from_user.first_name}! soy Deltix, el bot del humedal. Soy un bot en desarrollo y por ahora tan sólo puedo mandarte una vez por día el pronóstico de mareas del INA para el Puerto de San Fernando. ¿Querés recibir el pronóstico de mareas todos los días? Por favor respóndeme escribiendo 'Si' o 'No'.")

# Manejador de mensajes de textoiuju
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.lower()

    if text == 'si':
        suscriptores.append(chat_id)
        bot.send_message(chat_id, "¡Gracias por suscribirte! A partir de ahora recibirás el pronóstico de mareas una vez al día a las 9 de la mañana. Te mando ahora el último pronóstico que tengo...")
        bot.send_photo(chat_id, open("Marea.png", "rb"))
        bot.send_message(chat_id, "Espero que te sirva! Para desuscribirte, simplemente escribime diciendo que no querés recibir más mensajes. Quedamos en contacto!")
        
    elif text == 'no':
        suscriptores.remove(chat_id)
        bot.send_message(chat_id, "Fue un gusto hablar contigo. ¡Espero poder ayudarte en el futuro!")
    else:
        bot.send_message(chat_id, "Por favor, responde 'Si' o 'No'.")

# Función para enviar la imagen a los suscriptores
def enviar_imagen():
    for chat_id in suscriptores:
        bot.send_photo(chat_id, open("Marea.png", "rb"))

# Función para descargar la imagen del pronóstico de mareas
def descargar_imagen():
    urllib.request.urlretrieve(IMAGEN_URL, "Marea.png")

# Programar la descarga de la imagen y el envío diario
schedule.every().day.at("08:00").do(descargar_imagen)
schedule.every().day.at("09:00").do(enviar_imagen)

# Bucle principal del bot
while True:
    try:
        bot.polling()
        schedule.run_pending()
        time.sleep(1)
    except Exception as e:
        print(e)
        time.sleep(10)
