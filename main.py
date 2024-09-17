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

gmail_token = "crzqeminnwxgzevd"
telegram_token = "5712079875:AAHhIWwnHN5ws0DEUggA8-STWKmM-ZJ5hQE"

user_experience = pd.read_csv('/home/facundol/deltix/user_experience.csv')


logging.getLogger("httpx").setLevel(logging.WARNING)
logging.basicConfig(
    filename='deltix_log.log',
    level=logging.WARNING,
    format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

nest_asyncio.apply()

ANSWER_charlar, ANSWER_meme, ANSWER_colaborar, ANSWER_mensajear, ANSWER_informacion, ANSWER_mareas_suscribir, ANSWER_windguru_suscribir, ANSWER_desuscribir, ANSWER_meme2, ANSWER_charlar_windguru, ANSWER_colectivas  = range(11)

def generate_main_menu():
    '''
    Genera el menu principal
    Ese menu se ejecuta desde las funciones /start, /start2 y /menu
    Las lineas comentadas del menu son proyectos e ideas de funcionalidades
    para agregar a Deltix
    '''
    return ("- <b>/mareas </b>   <i> obtener el pronóstico de mareas &#9875</i>\n"
            "- <b>/windguru </b>   <i> pronóstico meteorológico de windgurú</i>\n"
            "- <b>/charlar</b>   <i> charlar conmigo y suscribirte a mis envíos </i>\n"
            "- <b>/memes </b>   <i> ver los memes más divertidos de la isla &#129315 </i>\n"
            # "- <b>/voy_y_vuelvo </b>   <i> compartir viajes desde y hacia a la isla</i>\n"
            # "- <b>/notiDeltix </b>   <i> suscribirte al envío de info de interés sobre la isla</i>\n"
            "- <b>/colectivas </b>   <i> horarios de lanchas colectivas</i>\n"
            "- <b>/informacion </b>   <i> saber más sobre Deltix &#128057</i>\n"
            "- <b>/colaborar </b>   <i> hacer sugerencias o aportar</i>\n"
            "- <b>/desuscribirme </b>   <i> darte de baja de mis envíos &#x1F989</i>\n"
            "- <b>/mensajear </b>   <i> mandarle un mensajito a mi desarrollador</i>\n")

main_menu_keyboard = ReplyKeyboardMarkup([["/windguru", "/mareas", "/memes"],
                                          ["/colectivas", "/colaborar", "/mensajear"],
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
        user_info = {"User ID": update.message.from_user.id,
            "Username": update.message.from_user.username,
            "First Name": update.message.from_user.first_name,
            "Last Name":update.message.from_user.last_name,
            "first_interaction":  datetime.now().strftime('%d-%m-%Y %H:%M') }
        user_experience = user_experience.append(user_info, ignore_index=True)
        user_experience.to_csv('/home/facundol/deltix/user_experience.csv', index=False)

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
    time.sleep(2)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=("upss.. perdón! estaba distraído chapoteando en el pantanix &#129439 No entendí lo que dijiste"),
        parse_mode='HTML')
    time.sleep(2)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=("En qué te puedo ayudar? Elegí alguna actividad para continuar:\n "),
        parse_mode='HTML')
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=generate_main_menu(),
        parse_mode='HTML',
        reply_markup=main_menu_keyboard)

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
    subscribers_mareas = pd.read_csv("/home/facundol/deltix/subscribers_mareas.csv")
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
            await context.bot.send_photo(chat_id, open("/home/facundol/deltix/marea.png", "rb"))
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
            subscribers_mareas.to_csv('/home/facundol/deltix/subscribers_mareas.csv', index=False)
            await update.message.reply_text(
                "¡Gracias por suscribirte! Voy a intentar mandarte el pronóstico de mareas una vez al día. A veces fallo porque dependo de que me ande la internet isleña")
            await update.message.reply_text(
                "Te mando ahora el último pronóstico que tengo...",
            )
            await context.bot.send_photo(chat_id, open("/home/facundol/deltix/marea.png", "rb"))
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
        subscribers_windguru = pd.read_csv("/home/facundol/deltix/subscribers_windguru.csv")
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
        logger.warning(f"{user.id} - {user.first_name} pidió informe de mareas en chat {chat_id}")
        # await update.message.reply_text("No estoy enviando reporte de mareas :( El INA no está publicando su pronóstico debido a los recortes de personal en el estado")
        await update.message.reply_text("Ahí te mando el informe de mareas del INA para San Fernando")
        await context.bot.send_photo(chat_id, open("/home/facundol/deltix/marea.png", "rb"))
        time.sleep(4)
        if user.id in user_experience['User ID'][user_experience['suscr_marea_ofrecida'].isna()].values:
            await update.message.reply_text("Querés suscribirte para recibir esto todos los días?",
            reply_markup=ReplyKeyboardMarkup(
                [["Si", "No"]], one_time_keyboard=True, input_field_placeholder="Si o No?"
            ),)
            user_experience.loc[user_experience['User ID'] == user.id, 'suscr_marea_ofrecida'] =  datetime.now().strftime('%d-%m-%Y %H:%M')
            user_experience.to_csv('/home/facundol/deltix/user_experience.csv', index=False)
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
        logger.warning(f"{user.id} - {user.first_name} pidió pronóstico de windguru en chat {chat_id}")
        await update.message.reply_text("Ahí te mando el pronóstico de windguru")
        await context.bot.send_photo(chat_id, open("/home/facundol/deltix/windguru.png", "rb"))
        time.sleep(4)
        if user.id in user_experience['User ID'][user_experience['suscr_windguru_ofrecida'].isna()].values:
            await update.message.reply_text("Querés suscribirte para recibir esto todos los días?",
            reply_markup=ReplyKeyboardMarkup(
                [["Si", "No"]], one_time_keyboard=True, input_field_placeholder="Si o No?"
            ),)
            user_experience.loc[user_experience['User ID'] == user.id, 'suscr_windguru_ofrecida'] =  datetime.now().strftime('%d-%m-%Y %H:%M')
            user_experience.to_csv('/home/facundol/deltix/user_experience.csv', index=False)
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
        subscribers_mareas = pd.read_csv("/home/facundol/deltix/subscribers_mareas.csv")
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
            subscribers_mareas.to_csv('/home/facundol/deltix/subscribers_mareas.csv', index=False)
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
        subscribers_windguru = pd.read_csv("/home/facundol/deltix/subscribers_windguru.csv")
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
        logger.warning(f"{user.id} - {user.first_name} pidió memes en chat {chat_id}")
        await context.bot.send_message(chat_id, "...me encantan los memes islenials &#128514 Te mando uno.",
                                        parse_mode='HTML')
        numero = random.randint(1, 56)
        await context.bot.send_photo(chat_id, open(f"/home/facundol/deltix/memes/{numero}.png", "rb"))
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
            await context.bot.send_photo(chat_id, open(f"/home/facundol/deltix/memes/{numero}.png", "rb"))
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
            await context.bot.send_photo(chat_id, open(f"/home/facundol/deltix/memes/{numero}.png", "rb"))
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
    logger.warning(f"{user.id} - {user.first_name} quiere desuscribirse en chat {chat_id}")

    reply_markup = ReplyKeyboardMarkup([["Mareas", "Windguru"]], one_time_keyboard=True, input_field_placeholder="A cuál envío quieres desuscribirte?")
    await update.message.reply_text("A cuál envío quieres desuscribirte: Mareas o Windguru?", reply_markup=reply_markup)

    return ANSWER_desuscribir

async def answer_desuscribir(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_response = update.message.text.lower()
    if user_response == "mareas":
        subscribers_mareas = pd.read_csv("/home/facundol/deltix/subscribers_mareas.csv")
        user_id = update.message.from_user.id

        if user_id in subscribers_mareas['User ID'].values:
            subscribers_mareas = subscribers_mareas[~subscribers_mareas['User ID'].eq(user_id)]
            subscribers_mareas.to_csv('/home/facundol/deltix/subscribers_mareas.csv', index=False)
            await update.message.reply_text("Te has desuscrito con éxito del pronóstico de mareas. Si deseas desuscribirte de Windguru o realizar otra acción, decime nomas")
        else:
            await update.message.reply_text("No estabas suscrito previamente al pronóstico de mareas. Si deseas desuscribirte de Windguru o realizar otra acción, decime nomas")
    elif user_response == "windguru":
        subscribers_windguru = pd.read_csv("/home/facundol/deltix/subscribers_windguru.csv")
        user_id = update.message.from_user.id

        if user_id in subscribers_windguru['User ID'].values:
            subscribers_windguru = subscribers_windguru[~subscribers_windguru['User ID'].eq(user_id)]
            subscribers_windguru.to_csv('subscribers_windguru.csv', index=False)
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
    await update.message.reply_text("Escribí el mensaje y yo se lo reenvío al desarrollador",
                                    parse_mode='HTML')
    return ANSWER_mensajear

async def mensajear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    '''
    Envia mensaje por mail a Facu
    '''
    user = update.message.from_user
    message_text = update.message.text

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
    await update.message.reply_text('Mensaje enviado al desarrollador de Deltix con éxito. ¡Gracias!')
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
    time.sleep(1)
    await update.message.reply_text('Mis primeras funcionalidades son mandar el reporte de mareas del Instituto Nacional del Agua y el pronóstico del clima de WindGurú. Si te suscribís, lo vas a recibir todos los días')
    time.sleep(1)
    await update.message.reply_text('En el futuro espero sumar más funcionalidades, como enviar info con notas de interés y eventos de la isla a quienes quieran, o armar un sistema automático de avisos de voy-y-vuelvo para compartir viajes en botes desde y hacia la isla')
    time.sleep(3)
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
        await update.message.reply_text("Estoy desarrollado en código python por Facu, vecino de 1era sección de la isla. Si querés decirle algo lo podés mensajear. Se aceptan mensajitos de aliento, sugerencias o cualquier comentario :) También le podés pedir que te desarrolle un bot para tu emprendimiento o negocio...",
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
        chat_id=update.effective_chat.id
        await context.bot.send_photo(chat_id, open("/home/facundol/deltix/interislena_invierno.jpg", "rb"))
        time.sleep(2)
        await context.bot.send_message(chat_id, "Esta es la info que tengo. Te recomiendo de todas maneras confirmar los horarios por teléfono con la empresa")
        await context.bot.send_message(chat_id, "Si ves que hay algún horario incorrecto o a mejorar, no dudes en mandarle un mensajito al equipo Deltix")   ### AGREGAR OPCION PARA MANDAR MENSAJE
        return ConversationHandler.END

async def Jilguero(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id=update.effective_chat.id
    await context.bot.send_photo(chat_id, open("/home/facundol/deltix/jilguero.png", "rb"))
    time.sleep(2)
    await context.bot.send_message(chat_id, "Esta es la info que tengo. Te recomiendo de todas maneras confirmar los horarios por teléfono con la empresa")
    await context.bot.send_message(chat_id, "Si ves que hay algún horario incorrecto o información a corregir, no dudes en mandarle un mensajito al equipo Deltix")   ### AGREGAR OPCION PARA MANDAR MENSAJE
    return ConversationHandler.END

async def LineasDelta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id=update.effective_chat.id
    await context.bot.send_photo(chat_id, open("/home/facundol/deltix/lineas_delta.jpg", "rb"))
    time.sleep(2)
    await context.bot.send_message(chat_id, "Esta es la info que tengo. Te recomiendo de todas maneras confirmar los horarios por teléfono con la empresa")
    await context.bot.send_message(chat_id, "Si ves que hay algún horario incorrecto o información a corregir, no dudes en mandarle un mensajito al equipo Deltix")   ### AGREGAR OPCION PARA MANDAR MENSAJE
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
    #Handlers otros
    MessageHandler(filters.TEXT, start2)]

    conv_handler = ConversationHandler(
        entry_points= handlers,
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
            ANSWER_charlar_windguru : [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), charlar_windguru)],
        },
        fallbacks= handlers,
    )

    application.add_handler(start_handler)

    application.add_handler(conv_handler)

    application.run_polling()
