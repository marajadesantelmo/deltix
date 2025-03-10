from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, ConversationHandler, filters, MessageHandler
import pandas as pd
import random
import time
import nest_asyncio
from datetime import datetime
import smtplib
from email.message import EmailMessage
import logging
import os
from tokens import gmail_token, telegram_token

# Defino paths segun donde se ejecute el bot
if os.path.exists('/home/facundol/deltix/'):
    base_path = '/home/facundol/deltix/'
else:
        base_path = ''

# Paths
user_experience_path = base_path + 'user_experience.csv'
subscribers_mareas_path = base_path + 'subscribers_mareas.csv'
subscribers_windguru_path = base_path + 'subscribers_windguru.csv'
marea_image_path = base_path + 'marea.png'
windguru_image_path = base_path + 'windguru.png'
memes_path = base_path + 'memes/'
jilguero_ida_path = base_path + 'colectivas/jilguero_ida.png'
jilguero_vuelta_path = base_path + 'colectivas/jilguero_vuelta.png'
interislena_ida_invierno_path = base_path + 'colectivas/interislena_ida_invierno.png'
interislena_ida_verano_path = base_path + 'colectivas/interislena_ida_verano.png'
interislena_vuelta_invierno_path = base_path + 'colectivas/interislena_vuelta_invierno.png'
interislena_vuelta_verano_path = base_path + 'colectivas/interislena_vuelta_verano.png'
lineas_delta_ida_no_escolar_path = base_path + 'colectivas/lineas_delta_ida_no_escolar.png'
lineas_delta_ida_escolar_path = base_path + 'colectivas/lineas_delta_ida_escolar.png'
lineas_delta_vuelta_no_escolar_path = base_path + 'colectivas/lineas_delta_vuelta_no_escolar.png'
lineas_delta_vuelta_escolar_path = base_path + 'colectivas/lineas_delta_vuelta_escolar.png'
carpinchix_trabajando_path = base_path + 'carpinchix_trabajando.png'
almaceneras_path = base_path + 'rag/almaceneras.txt'

user_experience = pd.read_csv(user_experience_path)

# Function to update user experience
def update_user_experience(user_id, option):
    global user_experience
    timestamp_col = f'timestamp_{option}'
    q_col = f'q_{option}'

    if user_id in user_experience['User ID'].values:
        user_experience.loc[user_experience['User ID'] == user_id, timestamp_col] = datetime.now().strftime('%d-%m-%Y %H:%M')
        user_experience.loc[user_experience['User ID'] == user_id, q_col] += 1
        user_experience.to_csv(user_experience_path, index=False)

logging.basicConfig(
    filename='deltix_log.log',
    level=logging.WARNING,
    format='%(asctime)s - %(message)s',
    force=True  # This ensures that the logging configuration is reset
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

nest_asyncio.apply()

ANSWER_charlar, ANSWER_meme, ANSWER_colaborar, ANSWER_mensajear, ANSWER_informacion, ANSWER_mareas_suscribir, ANSWER_windguru_suscribir, ANSWER_desuscribir, ANSWER_meme2, ANSWER_charlar_windguru, ANSWER_colectivas, ANSWER_jilguero, ANSWER_interislena, ANSWER_lineasdelta, ANSWER_direction, ANSWER_schedule, ANSWER_almacenera_select = range(17)

def generate_main_menu():
    '''
    Genera el menu principal
    Ese menu se ejecuta desde las funciones /start, /start2 y /menu
    Las lineas comentadas del menu son proyectos e ideas de funcionalidades
    para agregar a Deltix
    '''
    return ("- <b>/mareas </b>   <i> obtener el pronóstico de mareas &#9875</i>\n"
            "- <b>/windguru </b>   <i> pronóstico meteorológico de windgurú</i>\n"
            "- <b>/colectivas </b>   <i> horarios de lanchas colectivas &#128337</i>\n"
            "- <b>/almaceneras </b>   <i> información de las lanchas almaceneras &#128676</i>\n"
            "- <b>/memes </b>   <i> ver los memes más divertidos de la isla &#129315 </i>\n"
            # "- <b>/voy_y_vuelvo </b>   <i> compartir viajes desde y hacia a la isla</i>\n"
            # "- <b>/notiDeltix </b>   <i> suscribirte al envío de info de interés sobre la isla</i>\n"
            "- <b>/charlar</b>   <i> charlar conmigo y suscribirte a mis envíos </i>\n"
            "- <b>/informacion </b>   <i> saber más sobre Deltix &#128057</i>\n"
            "- <b>/colaborar </b>   <i> hacer sugerencias o aportar</i>\n"
            "- <b>/desuscribirme </b>   <i> darte de baja de mis envíos &#x1F989</i>\n"
            "- <b>/mensajear </b>   <i> mandarle un mensajito al equipo Deltix</i>\n")

main_menu_keyboard = ReplyKeyboardMarkup([["/windguru", "/mareas", "/memes"],
                                          ["/colectivas", "/almaceneras", "/colaborar"],
                                          ["/charlar", "/informacion", "/desuscribirme"]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE)-> None:
    '''
    Respuesta cuando el usuario comienza por /start
    '''
    global user_experience
    chat_id = update.effective_chat.id
    user = update.effective_user
    logger.warning(f"{user.id} - {user.first_name} comenzó charla con comando start en chat {chat_id}")

    if user.id not in user_experience['User ID'].values:
        user_info = {
            "User ID": update.message.from_user.id,
            "Username": update.message.from_user.username,
            "First Name": update.message.from_user.first_name,
            "Last Name": update.message.from_user.last_name,
            "first_interaction": datetime.now().strftime('%d-%m-%Y %H:%M'),
            "suscr_windguru_ofrecida": None,
            "suscr_marea_ofrecida": None,
            "q_mareas": 0,
            "timestamp_mareas": None,
            "q_windguru": 0,
            "timestamp_windguru": None,
            "q_colectivas": 0,
            "timestamp_colectivas": None,
            "q_memes": 0,
            "timestamp_memes": None,
            "q_charlar": 0,
            "timestamp_charlar": None,
            "q_informacion": 0,
            "timestamp_informacion": None,
            "q_colaborar": 0,
            "timestamp_colaborar": None,
            "q_desuscribirme": 0,
            "timestamp_desuscribirme": None,
            "q_mensajear": 0,
            "timestamp_mensajear": None
        }
        user_experience = user_experience.append(user_info, ignore_index=True)
        user_experience.to_csv(user_experience_path, index=False)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(f"Hola {update.effective_user.first_name}! soy Deltix, el bot del humedal &#128057"),
        parse_mode='HTML')
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=("En qué te puedo ayudar? Elegí alguna actividad para continuar:\n "),
        parse_mode='HTML')
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=generate_main_menu(),
        parse_mode='HTML',
        reply_markup=main_menu_keyboard)

async def start2(update: Update, context: ContextTypes.DEFAULT_TYPE)-> None:
    '''
    Respuesta cuando el bot no entiende respuesta del usuario
    '''
    chat_id = update.effective_chat.id
    user = update.effective_user
    logger.warning(f"{user.id} - {user.first_name} usó comando start2 en chat {chat_id}")
    responses = [
        "upss.. perdón! estaba distraído chapoteando en el pantanix &#129439 No entendí lo que dijiste",
        "upsss... no entendí eso",
        "Hmm... eso no lo entendí bien",
        "Perdón, no capté eso. Itentemos de vuelta"
    ]
    response = random.choice(responses)
    time.sleep(2)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=response,
        parse_mode='HTML'
    )
    time.sleep(2)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=("En qué te puedo ayudar? Elegí alguna actividad para continuar:\n "),
        parse_mode='HTML'
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=generate_main_menu(),
        parse_mode='HTML',
        reply_markup=main_menu_keyboard
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE)-> None:
    '''
    Respuesta cuando el usuario pide el menu
    '''
    chat_id = update.effective_chat.id
    user = update.effective_user
    logger.warning(f"{user.id} - {user.first_name} usó comando menu en chat {chat_id}")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=generate_main_menu(),
        parse_mode='HTML',
        reply_markup=main_menu_keyboard)


async def charlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    '''
    1era respuesta para el comando /charlar
    La idea de esta respuesta es que el bot vaya llevando al usuario por todas
    sus funcionalidad (falta mejorarlo)
    '''
    chat_id = update.effective_chat.id
    user = update.effective_user
    update_user_experience(user.id, 'charlar')
    logger.warning(f"{user.id} - {user.first_name} comenzó charla con comando charlar en chat {chat_id}")
    await update.message.reply_text("Soy un bot en desarrollo. Puedo mandarte una vez por día el pronóstico de mareas del INA y del clima de WindGurú. ¿Querés recibir el pronóstico de mareas de San Fernando todos los días?",
    reply_markup=ReplyKeyboardMarkup([["Si", "No"]], one_time_keyboard=True, input_field_placeholder="Si o No?"))
    return ANSWER_charlar

async def answer_charlar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    '''
    2da respuesta para el comando /charlar
    Suscribe al usuario a pronostico de mareas y luego le pregunta si quiere
    ver memes
    '''
    user_response = update.message.text.lower()
    chat_id=update.effective_chat.id
    subscribers_mareas = pd.read_csv(subscribers_mareas_path)
    if user_response == 'si':
        chat_id = update.effective_chat.id
        user = update.effective_user
        logger.warning(f"{user.id} - {user.first_name} se inscribió a mareas en chat {chat_id}")

        #Chequeo si ya está suscrito
        user_id = update.message.from_user.id
        if user_id in subscribers_mareas['User ID'].values:
            await update.message.reply_text(
                "Me parece que ya estabas suscriptx vos! Igual te voy a estar enviando los reportes todos los días. Ahí te mando el reporte actual"
            )
            await context.bot.send_photo(chat_id, open(marea_image_path, "rb"))
            time.sleep(5)
            await update.message.reply_text(
                "También te puedo mandar todos los días una captura de pantalla del pronóstico de Windgurú para la zona de las islas. Querés?",
                reply_markup=ReplyKeyboardMarkup([["Si", "No"]], one_time_keyboard=True, input_field_placeholder="Si o No?"))
            return ANSWER_charlar_windguru

        #Si no está suscrito lo subo a la lista
        else:
            user_info = {"User ID": [update.message.from_user.id],
                        "Username": [update.message.from_user.username],
                        "First Name": [update.message.from_user.first_name],
                        "Last Name": [update.message.from_user.last_name],}
            user_df = pd.DataFrame(user_info)
            subscribers_mareas = subscribers_mareas.append(user_df, ignore_index=True)
            subscribers_mareas.to_csv(subscribers_mareas_path, index=False)
            await update.message.reply_text(
                "¡Gracias por suscribirte! Voy a intentar mandarte el pronóstico de mareas una vez al día. A veces fallo porque dependo de que me ande la internet isleña")
            await update.message.reply_text(
                "Te mando ahora el último pronóstico que tengo...",
            )
            await context.bot.send_photo(chat_id, open(marea_image_path, "rb"))
            time.sleep(5)
            await update.message.reply_text(
                "También te puedo mandar todos los días una captura de pantalla del pronóstico de Windgurú para la zona de las islas. Querés?",
                reply_markup=ReplyKeyboardMarkup([["Si", "No"]], one_time_keyboard=True, input_field_placeholder="Si o No?"))
            return ANSWER_charlar_windguru

    if user_response == 'no':
        await update.message.reply_text(
            "Bueno... otra cosa que puedo ofrecerte es mandarte todos los días una captura de pantalla del pronóstico de Windgurú para la zona de las islas. Querés?",
        reply_markup=ReplyKeyboardMarkup([["Si", "No"]], one_time_keyboard=True, input_field_placeholder="Si o No?"))
        return ANSWER_charlar_windguru

async def charlar_windguru(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_response = update.message.text.lower()
    if user_response == 'si':
        subscribers_windguru = pd.read_csv(subscribers_windguru_path)
        chat_id = update.effective_chat.id
        user = update.effective_user
        logger.warning(f"{user.id} - {user.first_name} se inscribió a windguru en charla {chat_id}")

        # Check if the user is already subscribed
        user_id = update.message.from_user.id
        if user_id in subscribers_windguru['User ID'].values:
            await update.message.reply_text("Creo que ya estabas suscritx a los pronósticos de Windguru... ¡Te los seguiré enviando todos los días! Siemmpre y cuando wired.com me lo permita &#129315 ",
                                            parse_mode='HTML')
        else:
            user_info = {"User ID": [update.message.from_user.id],
                        "Username": [update.message.from_user.username],
                        "First Name": [update.message.from_user.first_name],
                        "Last Name": [update.message.from_user.last_name],}
            user_df = pd.DataFrame(user_info)
            subscribers_windguru = subscribers_windguru.append(user_df, ignore_index=True)
            subscribers_windguru.to_csv('subscribers_windguru.csv', index=False)
            await update.message.reply_text("Ya te anoté!!! aiiii... tengo unas ganas de verme unos memes &#128057 Vemos uno?", parse_mode='HTML')
            return ANSWER_meme
    elif user_response == 'no':
        await update.message.reply_text("Bueno... otra cosa que puedo ofrecerte es un meme de la isla.. querés?")
        return ANSWER_meme

async def mareas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        '''
        Envia el pronostico de mareas cuando el usuario elige /mareas
        Luego le ofrece suscripcion
        '''
        global user_experience
        user = update.effective_user
        chat_id=update.effective_chat.id
        update_user_experience(user.id, 'mareas')
        if random.random() < 1/3:
            await update.message.reply_text(f"Ya te busco el informe del INA {update.effective_user.first_name}")
            await context.bot.send_photo(chat_id, open(carpinchix_trabajando_path, "rb"))
            time.sleep(3)
        logger.warning(f"{user.id} - {user.first_name} pidió informe de mareas en chat {chat_id}")
        # await update.message.reply_text("No estoy enviando reporte de mareas :( El INA no está publicando su pronóstico debido a los recortes de personal en el estado")
        await update.message.reply_text("Acá tenés el informe de mareas")
        await context.bot.send_photo(chat_id, open(marea_image_path, "rb"))
        time.sleep(4)
        if user.id in user_experience['User ID'][user_experience['suscr_marea_ofrecida'].isna()].values:
            await update.message.reply_text("Querés suscribirte para recibir esto todos los días?",
            reply_markup=ReplyKeyboardMarkup(
                [["Si", "No"]], one_time_keyboard=True, input_field_placeholder="Si o No?"
            ),)
            user_experience.loc[user_experience['User ID'] == user.id, 'suscr_marea_ofrecida'] =  datetime.now().strftime('%d-%m-%Y %H:%M')
            user_experience.to_csv(user_experience_path, index=False)
            return ANSWER_mareas_suscribir
        else:
            return ConversationHandler.END


async def windguru(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        '''
        Envia el pronostico de windguru cuando el usuario elige /windguru
        Luego le ofrece suscripcion
        '''
        global user_experience
        user = update.effective_user
        chat_id=update.effective_chat.id
        update_user_experience(user.id, 'windguru')
        logger.warning(f"{user.id} - {user.first_name} pidió pronóstico de windguru en chat {chat_id}")
        await update.message.reply_text("Ahí te mando el pronóstico de windguru")
        await context.bot.send_photo(chat_id, open(windguru_image_path, "rb"))
        time.sleep(4)
        if user.id in user_experience['User ID'][user_experience['suscr_windguru_ofrecida'].isna()].values:
            await update.message.reply_text("Querés suscribirte para recibir esto todos los días?",
            reply_markup=ReplyKeyboardMarkup(
                [["Si", "No"]], one_time_keyboard=True, input_field_placeholder="Si o No?"
            ),)
            user_experience.loc[user_experience['User ID'] == user.id, 'suscr_windguru_ofrecida'] =  datetime.now().strftime('%d-%m-%Y %H:%M')
            user_experience.to_csv(user_experience_path, index=False)
            return ANSWER_windguru_suscribir
        else:
            return ConversationHandler.END

async def mareas_suscribir(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    '''
    Funcion para obtener respuesta si/no de suscripcion a mareas y realizar
    la suscripción
    '''
    user_response = update.message.text.lower()
    if user_response == 'si':
        subscribers_mareas = pd.read_csv(subscribers_mareas_path)
        chat_id = update.effective_chat.id
        user = update.effective_user
        logger.warning(f"{user.id} - {user.first_name} se inscribió a mareas en chat {chat_id}")
        #Chequeo si ya está suscrito
        user_id = update.message.from_user.id
        if user_id in subscribers_mareas['User ID'].values:
            await update.message.reply_text("Me parece que ya estabas suscriptx vos! Igual te voy a estar enviando los reportes todos los días")
        #Si no está suscrito lo subo a la lista
        else:
            user_info = {"User ID": [update.message.from_user.id],
                        "Username": [update.message.from_user.username],
                        "First Name": [update.message.from_user.first_name],
                        "Last Name": [update.message.from_user.last_name],}
            user_df = pd.DataFrame(user_info)
            subscribers_mareas = subscribers_mareas.append(user_df, ignore_index=True)
            subscribers_mareas.to_csv(subscribers_mareas_path, index=False)
            await update.message.reply_text("¡Gracias por suscribirte! Voy a intentar mandarte el pronóstico de mareas una vez al día. A veces fallo porque dependende de que me ande la internet isleña")
        return ConversationHandler.END
    if user_response == 'no':
        await update.message.reply_text("Bueno dale! avisame si necesitás algo más")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=generate_main_menu(),
            parse_mode='HTML',
            reply_markup=main_menu_keyboard)

async def windguru_suscribir(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_response = update.message.text.lower()
    if user_response == 'si':
        subscribers_windguru = pd.read_csv(subscribers_windguru_path)
        chat_id = update.effective_chat.id
        user = update.effective_user
        logger.warning(f"{user.id} - {user.first_name} se inscribió a windguru en chat {chat_id}")

        # Check if the user is already subscribed
        user_id = update.message.from_user.id
        if user_id in subscribers_windguru['User ID'].values:
            await update.message.reply_text("Ya estás suscrito a los pronósticos de Windguru. ¡Te los seguiré enviando todos los días!")
        else:
            user_info = {"User ID": [update.message.from_user.id],
                        "Username": [update.message.from_user.username],
                        "First Name": [update.message.from_user.first_name],
                        "Last Name": [update.message.from_user.last_name],}
            user_df = pd.DataFrame(user_info)
            subscribers_windguru = subscribers_windguru.append(user_df, ignore_index=True)
            subscribers_windguru.to_csv('/home/facundol/deltix/subscribers_windguru.csv', index=False)
            await update.message.reply_text("¡Gracias por suscribirte! Te enviaré el pronóstico de Windguru una vez al día.")
        return ConversationHandler.END
    elif user_response == 'no':
        await update.message.reply_text("Entendido. Si cambias de opinión, siempre puedes suscribirte más tarde. ¿Hay algo más en lo que te pueda ayudar?")
        return ConversationHandler.END

async def memes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        '''
        Respuesta cuando el usuario pide directamente memes por comando /memes
        '''
        user = update.effective_user
        chat_id=update.effective_chat.id
        update_user_experience(user.id, 'memes')
        logger.warning(f"{user.id} - {user.first_name} pidió memes en chat {chat_id}")
        await context.bot.send_message(chat_id, "...me encantan los memes islenials &#128514 Te mando uno.",
                                        parse_mode='HTML')
        numero = random.randint(1, 56)
        await context.bot.send_photo(chat_id, open(f"{memes_path}{numero}.png", "rb"))
        time.sleep(6)
        await context.bot.send_message(chat_id, "Buenísimo, no? Son de la página Memes Islenials. Te recomiendo que la sigas en las redes",)
        await context.bot.send_message(chat_id, "Querés otro meme?")
        return ANSWER_meme

async def answer_meme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        '''
        Respuesta para enviar o no más memes después de haber mandado el 1ero
        '''
        chat_id=update.effective_chat.id
        user_response = update.message.text.lower()
        if user_response == 'si':
            numero = random.randint(1, 56)
            await context.bot.send_photo(chat_id, open(f"{memes_path}{numero}.png", "rb"))
            await context.bot.send_message(chat_id,"Uno más?")
            return ANSWER_meme2

        if user_response == 'no':
            await update.message.reply_text(
                "Bueno... si querés podes elegir otra de las actividades para hacer conmigo",
                reply_markup=ReplyKeyboardMarkup([["/charlar", "/mareas", "/memes"],
                                                  ["/informacion", "/colaborar", "/desuscribirme"] ]))
            return ConversationHandler.END

async def answer_meme2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        '''
        Respuesta para enviar o no más memes después de haber mandado otro
        '''
        chat_id=update.effective_chat.id
        user_response = update.message.text.lower()
        if user_response == 'si':
            numero = random.randint(1, 56)
            await context.bot.send_photo(chat_id, open(f"{memes_path}{numero}.png", "rb"))
            time.sleep(5)
            await context.bot.send_message(chat_id,"Te mando otro?")
            return ANSWER_meme

        if user_response == 'no':
            await update.message.reply_text(
                "Bueno... si querés podes elegir otra de las actividades para hacer conmigo",
                reply_markup=ReplyKeyboardMarkup([["/charlar", "/mareas", "/memes"],
                                                  ["/informacion", "/colaborar", "/desuscribirme"] ]))
            return ConversationHandler.END

async def desuscribirme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    chat_id = update.effective_chat.id
    update_user_experience(user.id, 'desuscribirme')
    logger.warning(f"{user.id} - {user.first_name} quiere desuscribirse en chat {chat_id}")

    reply_markup = ReplyKeyboardMarkup([["Mareas", "Windguru"]], one_time_keyboard=True, input_field_placeholder="A cuál envío quieres desuscribirte?")
    await update.message.reply_text("A cuál envío quieres desuscribirte: Mareas o Windguru?", reply_markup=reply_markup)

    return ANSWER_desuscribir

async def answer_desuscribir(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_response = update.message.text.lower()
    if user_response == "mareas":
        subscribers_mareas = pd.read_csv(subscribers_mareas_path)
        user_id = update.message.from_user.id

        if user_id in subscribers_mareas['User ID'].values:
            subscribers_mareas = subscribers_mareas[~subscribers_mareas['User ID'].eq(user_id)]
            subscribers_mareas.to_csv(subscribers_mareas_path, index=False)
            await update.message.reply_text("Te has desuscrito con éxito del pronóstico de mareas. Si deseas desuscribirte de Windguru o realizar otra acción, decime nomas")
        else:
            await update.message.reply_text("No estabas suscrito previamente al pronóstico de mareas. Si deseas desuscribirte de Windguru o realizar otra acción, decime nomas")
    elif user_response == "windguru":
        subscribers_windguru = pd.read_csv(subscribers_windguru_path)
        user_id = update.message.from_user.id

        if user_id in subscribers_windguru['User ID'].values:
            subscribers_windguru = subscribers_windguru[~subscribers_windguru['User ID'].eq(user_id)]
            subscribers_windguru.to_csv(subscribers_windguru_path, index=False)
            await update.message.reply_text("Te has desuscrito con éxito del pronóstico de Windguru. Si deseas desuscribirte de Mareas o realizar otra acción, decime nomas")
        else:
            await update.message.reply_text("No estabas suscrito previamente al pronóstico de Windguru. Si deseas desuscribirte de Mareas o realizar otra acción, decime nomas")
    else:
        await update.message.reply_text("No comprendí tu elección. Por favor, selecciona 'Mareas' o 'Windguru' para desuscribirte.")
        return ANSWER_desuscribir

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    '''
    Cierra la conversación cuando el usuario usa /cancel
    '''
    await update.message.reply_text(
        "Chauuu! Hablamos!", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def colaborar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    '''
    Respuesta para cuando se usa el comando /colaborar
    '''
    await update.message.reply_text("Qué bueno que quieras colaborar con Deltix &#128149",
                                    parse_mode='HTML')
    time.sleep(1)
    await update.message.reply_text("Podés ayudar mandando algún comentario o sugerencia a Facu, que es mi desarrollador. O también podés darnos una ayudita monetaria para posteriores desarrollos y poder pagar un servidor. Si llegamos a juntar suficiente dinero voy a poder funcionar las 24hs todos los días durante todo el año",
                                    parse_mode='HTML')
    await update.message.reply_text("Qué querés hacer?",
    reply_markup=ReplyKeyboardMarkup(
        [["Mensajear", "Aportar"]], one_time_keyboard=True, input_field_placeholder="Mensajear o Aportar??"
    ),)
    return ANSWER_colaborar


async def mensaje_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    '''
    Respuesta cuando el usuario quiere mandar un mensaje al desarrollador
    Luego hay que dirigirlo a la funcion mensajear para que el mensaje se mande
    '''
    await update.message.reply_text("Escribí el mensaje y yo se lo reenvío al equipo Deltix",
                                    parse_mode='HTML')
    return ANSWER_mensajear

async def mensajear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    '''
    Envia mensaje por mail a Facu
    '''
    user = update.message.from_user
    message_text = update.message.text
    update_user_experience(user.id, 'mensajear')
    body = f'Mensaje de {user.first_name}: {message_text}'
    message = EmailMessage()

    message['From'] = "marajadesantelmo@gmail.com"
    message['To'] = "marajadesantelmo@gmail.com"
    message['Subject'] = "Mensaje de deltix"
    message.set_content(body)

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login("marajadesantelmo@gmail.com", gmail_token)
    server.send_message(message)

    # context.bot.send_message(chat_id=672134330, text=f'Mensaje de {user.first_name}: {message_text}')
    await update.message.reply_text('Mensaje enviado con éxito. ¡Gracias!')
    return ConversationHandler.END

async def answer_colaborar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    '''
    Respuesta a interacción por medio de /colaborar que dirige al usuario a
    mensajear o a colaborar economicamente
    '''
    user_response = update.message.text.lower()
    if user_response == 'mensajear':
        await update.message.reply_text("Escribí el mensaje y yo se lo reenvío al desarrollador", parse_mode='HTML')
        return ANSWER_mensajear
    if user_response == 'aportar':
        user = update.effective_user
        chat_id=update.effective_chat.id
        logger.warning(f"{user.id} - {user.first_name} entró en aportar en chat {chat_id}")
        await update.message.reply_text("Muchas gracias por pensar en aportar &#128591 Nos viene muy bien para poder seguir dedicándole tiempo a Deltix y hacer que crezca este proyecto", parse_mode='HTML')
        await update.message.reply_text("Podés aportar por medio de la página cafecito:", parse_mode='HTML')
        await update.message.reply_text("<a href='https://cafecito.app/deltix' rel='noopener' target='_blank' > 'Entrá a este enlace para hacer tu aporte'  </a>",
                                        parse_mode='HTML')
        return ConversationHandler.END

async def informacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    '''
    Respuesta al comando /informacion
    '''
    await update.message.reply_text('Te cuento un poco de mí! Soy un bot en desarrollo que tiene como objetivo ayudar a quienes habitamos en la isla, principalmente en la 1era sección')
    await update.message.reply_text('Mis primeras funcionalidades son mandar el reporte de mareas del Instituto Nacional del Agua y el pronóstico del clima de WindGurú. Si te suscribís, lo vas a recibir todos los días. Hace poquito que también mando horarios de lanchas colectivas')
    time.sleep(3)
    await update.message.reply_text('En el futuro espero sumar más funcionalidades, como enviar info con notas de interés y eventos de la isla a quienes quieran, o armar un sistema automático de avisos de voy-y-vuelvo para compartir viajes en botes desde y hacia la isla')
    await update.message.reply_text('Pero bueno, vamos de a poquito. Soy un proyecto que recién empieza y hacemos todo a pulmón... querés saber más?',
    reply_markup=ReplyKeyboardMarkup(
        [["Si", "No"]], one_time_keyboard=True, input_field_placeholder="Si o No?"
    ),)
    return ANSWER_informacion

async def answer_informacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    '''
    Respuesta a si quiere saber más el usuario en /informacion
    '''
    user_response = update.message.text.lower()
    if user_response == 'si':
        await update.message.reply_text("Estoy desarrollado en código python por Facu, vecino de 1era sección de la isla, y los diseños tan lindos están hechos por Eli. Si querés decirle algo lo podés mensajear. Se aceptan mensajitos de aliento, sugerencias o cualquier comentario :) También les podés pedir que te desarrollen un bot para tu emprendimiento...",
                                        parse_mode='HTML',
                                        reply_markup=ReplyKeyboardMarkup(
                                            [["/mensajear", "/colaborar", "/menu"], ["/charlar", "/mareas", "/memes"]],
                                            one_time_keyboard=True,
                                            input_field_placeholder="querés hacer otra cosa?")
                                        )
        return ConversationHandler.END
    if user_response == 'no':
        await update.message.reply_text("okisss... igual no había mucho más para contar tampocoo",
                                        parse_mode='HTML',
                                        reply_markup=ReplyKeyboardMarkup(
                                            [["/mensajear", "/colaborar", "/menu"], ["/charlar", "/mareas", "/memes"]],
                                            one_time_keyboard=True,
                                            input_field_placeholder="qué querés hacer?")
                                        )
        return ConversationHandler.END


async def de_nada(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    '''
    Respuesta a agradecimiento por parte del usuario
    '''
    await update.message.reply_text("De nada! es un placer a ayudar a lxs humanos que visitan el humedal  &#128057\n",
                                     parse_mode='HTML')
    return ConversationHandler.END


async def colectivas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    '''
    Seleccion de empresas de colectiva para pedir horario
    '''
    user = update.effective_user
    update_user_experience(user.id, 'colectivas')
    await update.message.reply_text("""Elegí la empresa de lancha colectiva:\n
            - <b>/Jilguero </b>   <i> va por el Carapachay-Angostura</i>
            - <b>/Interislena </b>   <i> Sarmiento, San Antonio y muchos más</i>
            - <b>/LineasDelta </b>   <i> Caraguatá, Canal Arias, Paraná Miní</i>""",
                                        parse_mode='HTML',
                                        reply_markup=ReplyKeyboardMarkup(
            [["/Jilguero", "/Interisleña", "/LineasDelta"]],
            one_time_keyboard=True,
            input_field_placeholder="Empresa de lanchas"))


async def Interislena(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Para Interisleña, por ahora solo tengo los horarios de Ida hacia la isla. Querés los horarios de verano o de inverno?",
                                reply_markup=ReplyKeyboardMarkup(
                                    [["Verano", "Invierno"]],
                                    one_time_keyboard=True,
                                    input_field_placeholder="Invierno o verano"))
    return ANSWER_interislena

async def answer_interislena(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id=update.effective_chat.id
    user_response = update.message.text.lower()
    if 'invierno' in user_response:
        await context.bot.send_photo(chat_id, open(interislena_ida_invierno_path, "rb"))
        await context.bot.send_message(chat_id, f"Estos son los horarios de {user_response} de Interisleña. Si ves que hay algún horario incorrecto o información a corregir, no dudes en mandarle un mensajito al equipo Deltix")
        time.sleep(1)
        await context.bot.send_message(chat_id, f"Siempre recomiendo llamar antes a la empresa porque los horarios suelen cambiar. El teléfono es 4749-0900",
                           reply_markup=ReplyKeyboardMarkup(
                           [["Jilguero", "LineasDelta", "Interislena"],
                            ["/mensajear", "/menu", "/memes"] ],
                           one_time_keyboard=True,
                           input_field_placeholder="Querés hacer algo más??"))
        return ConversationHandler.END
    elif 'verano' in user_response:
        await context.bot.send_photo(chat_id, open(interislena_ida_verano_path, "rb"))
        await context.bot.send_message(chat_id, f"Estos son los horarios de {user_response} de Interisleña. Si ves que hay algún horario incorrecto o información a corregir, no dudes en mandarle un mensajito al equipo Deltix")
        time.sleep(1)
        await context.bot.send_message(chat_id, f"Siempre recomiendo llamar antes a la empresa porque los horarios suelen cambiar. El teléfono es 4749-0900",
                           reply_markup=ReplyKeyboardMarkup(
                           [["Jilguero", "LineasDelta", "Interislena"],
                            ["/mensajear", "/menu", "/memes"] ],
                           one_time_keyboard=True,
                           input_field_placeholder="Si querés, elegí otra empresa de lanchas u otra actividad para hacer conmigo"))
        return ConversationHandler.END
    else:
        await update.message.reply_text("No comprendí tu elección")
        return ConversationHandler.END

async def Jilguero(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("En qué sentido querés viajar? Ida a la isla o vuelta a Tigre?",
                                    reply_markup=ReplyKeyboardMarkup(
                                        [["Ida a la isla", "Vuelta a Tigre"]],
                                        one_time_keyboard=True,
                                        input_field_placeholder="Ida a la isla o Vuelta a Tigre"))
    return ANSWER_jilguero

async def answer_jilguero(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id=update.effective_chat.id
    user_response = update.message.text.lower()
    if 'ida' in user_response or 'isla' in user_response:
        await context.bot.send_message(chat_id, f"Estos son los horarios de ida a la isla de Jilguero. Si ves que hay algún horario incorrecto o información a corregir, no dudes en mandarle un mensajito al equipo Deltix")
        await context.bot.send_photo(chat_id, open(jilguero_ida_path, "rb"))
        time.sleep(1)
        await context.bot.send_message(chat_id, f"Siempre recomiendo llamar antes a la empresa porque los horarios suelen cambiar. El teléfono es 4749-0987",
                           reply_markup=ReplyKeyboardMarkup(
                           [["Jilguero", "LineasDelta", "Interislena"],
                            ["/mensajear", "/menu", "/memes"] ],
                           one_time_keyboard=True,
                           input_field_placeholder="Elegí otra empresa de lanchas o actividad para hacer conmigo"))
        return ConversationHandler.END
    elif 'vuelta' in user_response or 'tigre' in user_response:
        await context.bot.send_message(chat_id, f"Estos son los horarios de vuelta a Tigre de Jilguero. Si ves que hay algún horario incorrecto o información a corregir, no dudes en mandarle un mensajito al equipo Deltix")
        await context.bot.send_photo(chat_id, open(jilguero_vuelta_path, "rb"))
        time.sleep(1)
        await context.bot.send_message(chat_id, f"Siempre recomiendo llamar antes a la empresa porque los horarios suelen cambiar. El teléfono es 4749-0987",
                           reply_markup=ReplyKeyboardMarkup(
                           [["Jilguero", "LineasDelta", "Interislena"],
                            ["/mensajear", "/menu", "/memes"] ],
                           one_time_keyboard=True,
                           input_field_placeholder="Te ayudo en algo más?"))
        return ConversationHandler.END
    else:
        await update.message.reply_text("No comprendí tu elección")
        return ConversationHandler.END

async def LineasDelta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Ask user for direction (Ida or Vuelta)
    await update.message.reply_text(
        "Qué recorrido necesitás? Ida a la isla o vuelta a Tigre?",
        reply_markup=ReplyKeyboardMarkup(
            [["Ida", "Vuelta"]],
            one_time_keyboard=True,
            input_field_placeholder="Ida o Vuelta?"
        )
    )
    return ANSWER_direction

async def direction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_choice = update.message.text.lower()

    # Match flexible inputs for "Ida" or "Vuelta"
    if "ida" in user_choice:
        context.user_data['direction'] = 'ida a la isla'
    elif "vuelta" in user_choice:
        context.user_data['direction'] = 'vuelta a tigre'
    else:
        await update.message.reply_text("Por favor, elegí 'Ida' o 'Vuelta'.")
        return ANSWER_direction

    # Ask if it's during the school period or not
    await update.message.reply_text(
        "En época escolar o no escolar?",
        reply_markup=ReplyKeyboardMarkup(
            [["Escolar", "No escolar"]],
            one_time_keyboard=True,
            input_field_placeholder="Escolar o No escolar?"
        )
    )
    return ANSWER_schedule

async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id
    user_choice = update.message.text.lower()
    
    if "escolar" in user_choice and "no" not in user_choice:
        context.user_data['epoca'] = 'escolar'
    elif "no escolar" in user_choice:
        context.user_data['epoca'] = 'no escolar'
    else:
        await update.message.reply_text("Por favor, elegí 'Escolar' o 'No escolar'.")
        return ANSWER_schedule
    
    await update.message.reply_text(f"Estos son los horarios de {context.user_data['direction']} en época {context.user_data['epoca']}.")
    
    # Send the appropriate image based on the user choices
    if context.user_data['direction'] == 'ida a la isla':
        if context.user_data['epoca'] == 'escolar':
            await context.bot.send_photo(chat_id, open(lineas_delta_ida_escolar_path, "rb"))
        else:  # 'no escolar'
            await context.bot.send_photo(chat_id, open(lineas_delta_ida_no_escolar_path, "rb"))
    else:  # 'vuelta a tigre'
        if context.user_data['epoca'] == 'escolar':
            await context.bot.send_photo(chat_id, open(lineas_delta_vuelta_escolar_path, "rb"))
        else:  # 'no escolar'
            await context.bot.send_photo(chat_id, open(lineas_delta_vuelta_no_escolar_path, "rb"))
            
    return ConversationHandler.END

# Almaceneras data organized as a dictionary with title case keys
ALMACENERAS_DATA = {
    "Nilda Alicia (Anita)": {
        "propietario": "Miguel Machado",
        "recorridos": "MARTES, VIERNES: Río Sarmiento / Río San Antonio\nMIÉRCOLES, SABADO: Río Capitán / Rama Negra / Arroyo Toro hasta Antequera primer tramo",
        "telefono": "1557490961"
    },
    "Cachito": {
        "propietario": "Aníbal Isea",
        "recorridos": "LUNES, MIÉRCOLES, VIERNES y SABADO: Río Carapachay hasta el 500\nDOMINGO: Río Carapachay hasta Angostura",
        "telefono": "11 6572-1030"
    },
    "Elsa María": {
        "propietario": "MAYORISTA",
        "recorridos": "",
        "telefono": "1565548280"
    },
    "Santa Teresita (ex Negrita)": {
        "propietario": "Ángel Ojeda",
        "recorridos": "MARTES Y SÁBADO: Río Carapachay hasta Río Paraná\nMIÉRCOLES y VIERNES: Arroyo Espera hasta Cruz Colorada",
        "telefono": "1532661770"
    },
    "Juan Y Juan": {
        "propietario": "Tito Hendenreich",
        "recorridos": "MAYORISTA",
        "telefono": "15 5095771/15 31905299"
    },
    "Santa Teresita": {
        "propietario": "Ricardo Ojeda",
        "recorridos": "MARTES, JUEVES, SÁBADO Y DOMINGO: Río Luján / Canal Arias hasta el Paraná",
        "telefono": ""
    },
    "Adriana": {
        "propietario": "Leo Rinaldi",
        "recorridos": "MIÉRCOLES, DOMINGO: Arroyo Abra vieja\nJUEVES, SÁBADO: Toro / Antequera / Arroyo Banco / Arroyo Andresito",
        "telefono": "1569789983"
    },
    "Buena Vida": {
        "propietario": "Cristian Lara",
        "recorridos": "LUNES: Arroyo Dorado /Arroyo Sábalos /Arroyo Arroyon/ Arroyo Boraso\nVIERNES: Arroyo Tiburón / Canal del Este y Aguajes",
        "telefono": "1553395931"
    },
    "Esperanza R": {
        "propietario": "Oscar Suárez",
        "recorridos": "MARTES, JUEVES y SÁBADO: Río Carapachay hasta muelle Sienará, retoma Río Luján / Arroyo Caraguatà hasta el 400",
        "telefono": "1565098174"
    },
    "Gardenia": {
        "propietario": "Lancha Mayorista",
        "recorridos": "",
        "telefono": "1540554422/1531882922"
    },
    "Gloria I": {
        "propietario": "Jorge Rinaldi",
        "recorridos": "MIÉRCOLES: Río San Antonio / Canal Honda/Aguaje del Durazno / Canal 2/Punta del Arroyo Caracoles /Bajos del Temor hasta Arroyo Chaná\nJUEVES: Chaná / la otra punta del Arroyo Caracoles / Paraná Mini / Tuyú Paré / Canal 3 / Arroyo Largo\nVIERNES: Arroyo Correntoso / Arroyo La Barca / Arroyo La Barquita/Arroyo Largo",
        "telefono": "1531298913"
    },
    "Ignacio Franco": {
        "propietario": "Familia Bettiga",
        "recorridos": "MIÉRCOLES: Río Sarmiento / Río Capitán hasta Club Imos / Arroyo Fredes\nJUEVES: Río Capitán / Arroyo Fredes\nVIERNES: Arroyo Estudiante / Arroyo Felicaria / Río Paraná Mini/Canal Arana\nSÁBADO: Arroyo Fredes / Río Paraná Miní / Tuyú Paré / Chaná / Felicaria abajo hasta Fredes",
        "telefono": "1562828206"
    },
    "Madreselva": {
        "propietario": "Familia Bettiga",
        "recorridos": "MIÉRCOLES: Tramo de Capitán arriba / Arroyo Estudiante / Arroyo Paicarabí/Felicaria abajo\nJUEVES: Río Sarmiento / arroyo Espera / Cruz Colorada/tramo de Paraná\nVIERNES: Paicarabí/Canal La Serna / Canal 4 / tramo de Paraná Mini",
        "telefono": "1554709382"
    },
    "Nelida G": {
        "propietario": "José Olivera",
        "recorridos": "LUNES: Arroyo Caraguata / Cruz Colorada / Canal Arias\nMIÉRCOLES: Río Luján / Canal Arias / Río Paraná / Cruz Colorada/Arroyo Caraguatá\nVIERNES: Río Luján / Canal Arias / Río Paraná / Cruz Colorada/ Arroyo Caraguatá\nSÁBADO: Río Luján / Canal Arias / Río Paraná / Cruz Colorada/ Arroyo Caraguatá",
        "telefono": "155644466"
    },
    "Raquel N": {
        "propietario": "Roberto Baraldo",
        "recorridos": "LUNES: Río Sarmiento / Río Capitán / Arroyo La Horca / Paraná hasta Cruz Alta\nMARTES: Río Paraná hasta Carabelas / Canal 5 / Arroyo Las Casillas del Delta\nMIÉRCOLES: Río Paraná hasta Carabelas / Canal 5/ Arroyo Las Casillas\nSÁBADO: Río Sarmiento / Río Capitán / Arroyo La Horca / Paraná hasta Cruz Alta",
        "telefono": "1544981064"
    },
    "Stella Maris": {
        "propietario": "Manuel Compagnucci",
        "recorridos": "VIERNES: Río Paraná zona Escobar hasta el hospital de Carabelas de ahi vuelve hasta el Paycaraby, Estudiantes, Las Cañas Fredes, Mini y La Serna\nSÁBADOS: Puerto de Escobar / Río Paraná / Canal de La Serna / tramo de Arroyo Paycarabí volviendo por Canal 4 / Rio Paraná Mini hasta Arroyo Chana / Bajos del Temor/ Arroyo Felicaria abajo / Arroyo Felicaria hasta la Escuela",
        "telefono": "1562771474"
    }
}

async def almaceneras(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    '''
    Muestra la lista de lanchas almaceneras disponibles para que el usuario elija
    '''
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    try:
        # Crear un mensaje con la lista de almaceneras disponibles
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="📋 Acá te muestro las lanchas almaceneras disponibles. ¿Sobre cuál querés información?",
            parse_mode='HTML')
        
        # Crear teclado con opciones de almaceneras
        # Agrupar en filas de 2 para mejor visualización
        almaceneras_list = list(ALMACENERAS_DATA.keys())
        keyboard = []
        for i in range(0, len(almaceneras_list), 2):
            row = almaceneras_list[i:i+2]
            keyboard.append(row)
        
        # Agregar un botón "Ver todas" al final
        keyboard.append(["Ver todas"])
        
        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            one_time_keyboard=True,
            input_field_placeholder="Selecciona una almacenera"
        )
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Seleccioná una lancha almacenera para ver sus detalles:",
            reply_markup=reply_markup)
        
        return ANSWER_almacenera_select
        
    except Exception as e:
        logger.warning(f"Error al mostrar lista de almaceneras: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Lo siento, tuve un problema al obtener la información de las almaceneras. Por favor, intentá más tarde.",
            parse_mode='HTML')
        return ConversationHandler.END

async def almacenera_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    '''
    Maneja la selección de una almacenera específica y muestra su información
    '''
    selected = update.message.text
    chat_id = update.effective_chat.id
    
    try:
        if selected == "Ver todas":
            # Si el usuario quiere ver todas las almaceneras
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Acá te muestro la información de todas las lanchas almaceneras:")
            
            for nombre, info in ALMACENERAS_DATA.items():
                message = f"<b>{nombre}</b> de {info['propietario']}\n"
                if info['recorridos']:
                    message += f"{info['recorridos']}\n"
                if info['telefono']:
                    message += f"📞 {info['telefono']}"
                
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    parse_mode='HTML')
                time.sleep(0.3)  # Pequeña pausa entre mensajes
        
        else:
            # Buscar la almacenera con coincidencia case-insensitive
            found = False
            for nombre in ALMACENERAS_DATA.keys():
                if nombre.lower() == selected.lower():
                    info = ALMACENERAS_DATA[nombre]
                    
                    message = f"<b>{nombre}</b> de {info['propietario']}\n"
                    if info['recorridos']:
                        message += f"\n{info['recorridos']}\n"
                    if info['telefono']:
                        message += f"\n📞 Teléfono: {info['telefono']}"
                    
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=message,
                        parse_mode='HTML')
                    found = True
                    break
            
            if not found:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="No encontré información sobre esa almacenera. Por favor, elegí una de la lista.")
                return ANSWER_almacenera_select
        
        # Mensaje final con recomendación
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Los horarios y recorridos de las almaceneras pueden variar, te recomiendo escribir o llamar para confirmar.",
            reply_markup=main_menu_keyboard)
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.warning(f"Error al mostrar información de almacenera: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Lo siento, tuve un problema al mostrar la información. Por favor, intentá más tarde.",
            parse_mode='HTML',
            reply_markup=main_menu_keyboard)
        return ConversationHandler.END

if __name__ == '__main__':
    application = ApplicationBuilder().token(telegram_token).build()
    start_handler = CommandHandler('start', start)
    handlers = [#Estos handlers son los que llevan la conversacion de funcion a funcion
                #Sirven como entry_points de la conversacion o como fallbacks
    #Handlers de comandos
    CommandHandler("cancel", cancel),
    CommandHandler('charlar', charlar),
    CommandHandler('mareas', mareas),
    CommandHandler('windguru', windguru),
    CommandHandler('desuscribirme', desuscribirme),
    CommandHandler('memes', memes),
    CommandHandler('colaborar', colaborar),
    CommandHandler('informacion', informacion),
    CommandHandler('mensajear', mensaje_trigger),
    CommandHandler('menu', menu),
    CommandHandler('colectivas', colectivas),
    CommandHandler('almaceneras', almaceneras),
    CommandHandler('Interislena', Interislena),
    CommandHandler('Jilguero', Jilguero),
    CommandHandler('LineasDelta', LineasDelta),

    #Handlers matcheo de palabra exacta
    MessageHandler(filters.Regex(r'^(Charlar|charlar|CHARLAR)$'), charlar),
    MessageHandler(filters.Regex(r'^(Mareas|mareas|MAREAS)$'), mareas),
    MessageHandler(filters.Regex(r'^(Windguru|windguru|WINDGURU)$'), windguru),
    MessageHandler(filters.Regex(r'^(Desuscribirme|desuscribirme|DESUSCRIBIRME)$'), desuscribirme),
    MessageHandler(filters.Regex(r'^(Memes|memes|MEMES|Meme|meme|MEME)$'), memes),
    MessageHandler(filters.Regex(r'^(Colaborar|colaborar|COLABORAR)$'), colaborar),
    MessageHandler(filters.Regex(r'^(Informacion|informacion|INFORMACION)$'), informacion),
    MessageHandler(filters.Regex(r'^(Mensajear|mensajear|MENSAJEAR)$'), mensaje_trigger),
    MessageHandler(filters.Regex(r'^(Hola|hola|HOLA)$'), start),
    MessageHandler(filters.Regex(r'^(Colectivas|colectivas|COLECTIVAS|horarios)$'), colectivas),
    MessageHandler(filters.Regex(r'^(Gracias|gracias|GRACIAS)$'), de_nada),
    MessageHandler(filters.Regex(r'^(Interislena|interislena|INTERISLENA)$'), Interislena),
    MessageHandler(filters.Regex(r'^(Jilguero|jilguero|JILGUERO)$'), Jilguero),
    MessageHandler(filters.Regex(r'^(LineasDelta|lineasdelta|LINEASDELTA)$'), LineasDelta),
    MessageHandler(filters.Regex(r'^(Almaceneras|almaceneras|ALMACENERAS)$'), almaceneras),

    #Handlers si contiene palabra en minuscula
    MessageHandler(filters.Regex(r'(?i)(.*\bcharlar\b.*)'), charlar),
    MessageHandler(filters.Regex(r'(?i)(.*\bmareas\b.*)'), mareas),
    MessageHandler(filters.Regex(r'(?i)(.*\bwindguru\b.*)'), windguru),
    MessageHandler(filters.Regex(r'(?i)(.*\bdesuscribirme\b.*)'), desuscribirme),
    MessageHandler(filters.Regex(r'(?i)(.*\bmemes\b.*)'), memes),
    MessageHandler(filters.Regex(r'(?i)(.*\bmeme\b.*)'), memes),
    MessageHandler(filters.Regex(r'(?i)(.*\bcolaborar\b.*)'), colaborar),
    MessageHandler(filters.Regex(r'(?i)(.*\binformacion\b.*)'), informacion),
    MessageHandler(filters.Regex(r'(?i)(.*\bmensajear\b.*)'), mensaje_trigger),
    MessageHandler(filters.Regex(r'(?i)(.*\bhola\b.*)'), start),
    MessageHandler(filters.Regex(r'(?i)(.*\bcolectivas\b.*)'), colectivas),
    MessageHandler(filters.Regex(r'(?i)(.*\bgracias\b.*)'), de_nada),
    MessageHandler(filters.Regex(r'(?i)(.*\bJilguero\b.*)'), Jilguero),
    MessageHandler(filters.Regex(r'(?i)(.*\bInterislena\b.*)'), Interislena),
    MessageHandler(filters.Regex(r'(?i)(.*\bLineasDelta\b.*)'), LineasDelta),
    MessageHandler(filters.Regex(r'(?i)(.*\balmaceneras\b.*)'), almaceneras),
    MessageHandler(filters.Regex(r'(?i)(.*\balmacenera\b.*)'), almaceneras),
    MessageHandler(filters.Regex(r'(?i)(.*\balmacén\b.*)'), almaceneras),
    MessageHandler(filters.Regex(r'(?i)(.*\balmacen\b.*)'), almaceneras),
    #Handlers otros
    MessageHandler(filters.TEXT, start2)]

    conv_handler = ConversationHandler(
        entry_points=handlers,
        states={
            ANSWER_charlar: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), answer_charlar)],
            ANSWER_meme: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), answer_meme)],
            ANSWER_meme2: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), answer_meme2)],
            ANSWER_informacion: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), answer_informacion)],
            ANSWER_colaborar: [MessageHandler(filters.Regex(r'^(Mensajear|mensajear|MENSAJEAR|Aportar|aportar|APORTAR)$'), answer_colaborar)],
            ANSWER_mareas_suscribir: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), mareas_suscribir)],
            ANSWER_windguru_suscribir: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), windguru_suscribir)],
            ANSWER_mensajear: [MessageHandler(filters.TEXT, mensajear)],
            ANSWER_desuscribir: [MessageHandler(filters.Regex(r'^(Mareas|MAREAS|mareas|Windguru|WINDGURU|windguru)$'), answer_desuscribir)],
            ANSWER_charlar_windguru: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), charlar_windguru)],
            ANSWER_jilguero: [MessageHandler(filters.TEXT, answer_jilguero)],
            ANSWER_interislena: [MessageHandler(filters.TEXT, answer_interislena)],
            ANSWER_direction: [MessageHandler(filters.TEXT, direction)],
            ANSWER_schedule: [MessageHandler(filters.TEXT, schedule)],
            ANSWER_almacenera_select: [MessageHandler(filters.TEXT, almacenera_selected)],
        },
        fallbacks=handlers,
    )

    application.add_handler(start_handler)

    application.add_handler(conv_handler)

    application.run_polling()
