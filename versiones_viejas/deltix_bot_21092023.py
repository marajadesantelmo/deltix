# %% inicio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, ConversationHandler, filters, MessageHandler
import pandas as pd
import os 
import urllib.request
import random
import time
import nest_asyncio
nest_asyncio.apply()

os.chdir('C:/Users/facun/OneDrive/Documentos/deltix/')
urllib.request.urlretrieve('https://alerta.ina.gob.ar/ina/42-RIODELAPLATA/productos/Prono_SanFernando.png', "marea.png")

ANSWER_charlar, ANSWER_meme, ANSWER_colaborar, ANSWER_mensajear, ANSWER_informacion = range(5)

# %%  menu

def generate_main_menu():
    return ("- <b>/charlar</b>   <i>para charlar conmigo y suscribirte a mis envíos diarios</i>.\n"
            "- <b>/mareas </b>   <i>para obtener el pronóstico de hoy de mareas del INA &#9875</i>\n"
            "- <b>/memes </b>   <i>para ver los memes más divertidos de la isla</i>\n"
            "- <b>/notiDeltix </b>   <i>para suscribirte al envío de info de interés y eventos isleños</i>\n"
            "- <b>/informacion </b>   <i>para saber más sobre Deltix &#128057</i>\n"
            "- <b>/colaborar </b>   <i>para hacer sugerencias o un aporte monetario</i>\n"             
            "- <b>/desuscribirme </b>   <i>para darte de baja de los envíos diarios &#x1F989</i>\n"
            "- <b>/mensajear </b>   <i>para mandarle un mensajito a mi desarrollador</i>\n" 
            )

main_menu_keyboard = ReplyKeyboardMarkup([["/charlar", "/mareas", "/memes"], ["/informacion", "/colaborar", "/desuscribirme"] ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE)-> None:
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
    time.sleep(2)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=("upss.. perdón! estaba chapoteando en el pantanix &#129439\n "),
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
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=generate_main_menu(),
        parse_mode='HTML',
        reply_markup=main_menu_keyboard)
    
# %%  charlar

async def charlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Soy un bot en desarrollo y mi mayor gracia es mandarte una vez por día el pronóstico de mareas del INA. ¿Querés recibir el pronóstico de mareas de San Fernando todos los días?",
    reply_markup=ReplyKeyboardMarkup(
        [["Si", "No"]], one_time_keyboard=True, input_field_placeholder="Si o No?"
    ),)
    return ANSWER_charlar

async def answer_charlar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_response = update.message.text.lower()
    chat_id=update.effective_chat.id
    subscribers = pd.read_csv("subscribers.csv") 
    if user_response == 'si':
        #Chequeo si ya está suscrito
        user_id = update.message.from_user.id
        if user_id in subscribers['User ID'].values:
            await update.message.reply_text(
                "Me parece que ya estabas suscriptx vos! Igual te voy a estar enviando los reportes todos los días. Ahí te mando el reporte actual"
            )
            await context.bot.send_photo(chat_id, open("Marea.png", "rb"))
            time.sleep(5)
            await update.message.reply_text(
                "aii... tengo unas ganas de verme unos memes &#128057. Vemos uno?", parse_mode='HTML')
            return ANSWER_meme
        
        #Si no está suscrito lo subo a la lista   
        else:
            user_info = {"User ID": [update.message.from_user.id],
                        "Username": [update.message.from_user.username],
                        "First Name": [update.message.from_user.first_name],
                        "Last Name": [update.message.from_user.last_name],}
            user_df = pd.DataFrame(user_info)
            subscribers = subscribers.append(user_df, ignore_index=True)
            subscribers.to_csv('subscribers.csv', index=False)
            await update.message.reply_text(
                "¡Gracias por suscribirte! Voy a intentar mandarte el pronóstico de mareas una vez al día. A veces fallo porque dependende de que me ande la internet isleña",
            )
            await update.message.reply_text(
                "Te mando ahora el último pronóstico que tengo...",
            )
            await context.bot.send_photo(chat_id, open("Marea.png", "rb"))
            time.sleep(5)
            await update.message.reply_text(
                "aii... tengo unas ganas de verme unos memes &#128057. Vemos uno?",
            )        
            return ANSWER_meme
        
    if user_response == 'no':
        await update.message.reply_text(
            "Bueno... otra cosa que puedo ofrecerte es un meme de la isla.. querés?",
        )
        return ANSWER_meme

# %%  mareas   
async def mareas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        chat_id=update.effective_chat.id
        await update.message.reply_text(
            "Ahí te mando el informe de mareas del INA para San Fernando",
        )
        await context.bot.send_photo(chat_id, open("Marea.png", "rb"))
        return ConversationHandler.END

# %%  memes
    
async def memes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        chat_id=update.effective_chat.id
        await update.message.reply_text("...me encantan los memes islenials &#128514 Te mando uno.",
                                        parse_mode='HTML')
        time.sleep(1)
        numero = random.randint(1, 13)
        await context.bot.send_photo(chat_id, open(f"memes/{numero}.png", "rb"))
        time.sleep(1)
        await update.message.reply_text("Buenísimo, no? Son de la página Memes Islenials. Te recomiendo que la sigas en las redes",)
        await update.message.reply_text("Querés otro meme?",
        reply_markup=ReplyKeyboardMarkup(
            [["Si", "No"]], one_time_keyboard=True, input_field_placeholder="Si o No?"
        ),)
        return ANSWER_meme
    
async def answer_meme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        chat_id=update.effective_chat.id
        user_response = update.message.text.lower()
        if user_response == 'si':
            await update.message.reply_text("Dale, te mando")
            time.sleep(2)
            numero = random.randint(1, 12)
            await context.bot.send_photo(chat_id, open(f"memes/{numero}.png", "rb"))
            time.sleep(1)
            await update.message.reply_text("Uno más?",
            reply_markup=ReplyKeyboardMarkup(
                [["Si", "No"]], one_time_keyboard=True, input_field_placeholder="Si o No?"
            ),)
            return ANSWER_meme
        if user_response == 'no':
            await update.message.reply_text(
                "Bueno... si querés podes elegir otra de las actividades para hacer conmigo",
                reply_markup=ReplyKeyboardMarkup([["/charlar", "/mareas", "/memes"], ["/informacion", "/colaborar", "/desuscribirme"] ])
            )

# %%  otros
async def desuscribirme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    subscribers = pd.read_csv("subscribers.csv")
    if user_id in subscribers['User ID'].values:
        subscribers = subscribers[~subscribers['User ID'].eq(user_id)]
        subscribers.to_csv('subscribers.csv', index=False)
        await update.message.reply_text(
            "Te has desuscripto correctamente. Si deseas volver a suscribirte, simplemente utilizá el comando /charlar."
        )
    else:
        await update.message.reply_text(
            "No estabas suscripto previamente. Para suscribirte, utilizá el comando /charlar."
        )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Chauuu! Hablamos!", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END    


async def colaborar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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

async def mensajear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    message_text = update.message.text
    # Enviar el mensaje al desarrollador
    context.bot.send_message(chat_id=672134330, text=f'Mensaje de {user.first_name}: {message_text}')
    await update.message.reply_text('Mensaje enviado al desarrollador de Deltix con éxito. ¡Gracias!')
    return ConversationHandler.END

async def answer_colaborar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_response = update.message.text.lower()
    if user_response == 'mensajear':
        await update.message.reply_text("Escribí el mensaje y yo se lo reenvío al desarrollador", parse_mode='HTML')
        return ANSWER_mensajear
    if user_response == 'aportar':
        await update.message.reply_text("Muchas gracias por pensar en aportar &#128591 Nos viene muy bien para poder seguir dedicándole tiempo a Deltix y hacer que crezca este proyecto", parse_mode='HTML')
        await update.message.reply_text("Hasta ahora la única forma de aportar económicamente es haciéndole una transferencia a mi desarrollador. Lo podés hacer enviando dinero al alias FACUNDO.LASTRA", parse_mode='HTML')
# %%  informacion    
async def informacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Te cuento un poco de mí! Soy un bot en desarrollo que tiene como objetivo ayudar a quienes habitamos en la isla, principalmente en la 1era sección')
    time.sleep(1)
    await update.message.reply_text('Una de mis primeras funcionalidades es mandar el pronóstico de mareas del Instituto Nacional del Agua. Si te suscribís, lo vas a recibir todos los días')
    time.sleep(1)
    await update.message.reply_text('En el futuro espero sumar más funcionalidades, como enviar info con notas de interés y eventos de la isla a quienes quieran, o armar un sistema automático de avisos de voy-y-vuelvo para compartir viajes en botes desde y hacia la isla')
    time.sleep(3)
    await update.message.reply_text('Pero bueno, vamos de a poquito. Soy un proyecto que recién empieza y hacemos todo a pulmón... querés saber más?',
    reply_markup=ReplyKeyboardMarkup(
        [["Si", "No"]], one_time_keyboard=True, input_field_placeholder="Si o No?"
    ),)
    return ANSWER_informacion
    
async def answer_informacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_response = update.message.text.lower()
    if user_response == 'si':
        await update.message.reply_text("Estoy desarrollado en código python por Facu, vecino de 1era sección de la isla. Si querés decirle algo lo podés mensajear. Se aceptan mensajitos de aliento, sugerencias o cualquier comentario :) También le podés pedir que te desarrolle un bot para tu emprendimiento o negocio...", 
                                        parse_mode='HTML', 
                                        reply_markup=ReplyKeyboardMarkup(
                                            [["/mensajear", "/colaborar", "/menu"], ["/charlar", "/mareas", "/memes"]], 
                                            one_time_keyboard=True, 
                                            input_field_placeholder="querés hacer otra cosa?")
                                        )
    if user_response == 'no':
        await update.message.reply_text("okisss... igual no había mucho más para contar tampocoo", 
                                        parse_mode='HTML', 
                                        reply_markup=ReplyKeyboardMarkup(
                                            [["/mensajear", "/colaborar", "/menu"], ["/charlar", "/mareas", "/memes"]], 
                                            one_time_keyboard=True, 
                                            input_field_placeholder="querés hacer otra cosa?")
                                        )
    
# %%  handler    
if __name__ == '__main__':
    application = ApplicationBuilder().token("5712079875:AAHhIWwnHN5ws0DEUggA8-STWKmM-ZJ5hQE").build()
    
    start_handler = CommandHandler('start', start)
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('charlar', charlar),
                      CommandHandler('mareas', mareas),
                      CommandHandler('desuscribirme', desuscribirme), 
                      CommandHandler('memes', memes), 
                      CommandHandler('colaborar', colaborar), 
                      CommandHandler('informacion', informacion), 
                      CommandHandler('mensajear', mensajear), 
                      CommandHandler('menu', menu), 
                      MessageHandler(filters.Regex(r'^(Charlar|charlar|CHARLAR)$'), charlar),
                      MessageHandler(filters.Regex(r'^(Mareas|mareas|MAREAS)$'), mareas),
                      MessageHandler(filters.Regex(r'^(Desuscribirme|desuscribirme|DESUSCRIBIRME)$'), desuscribirme),
                      MessageHandler(filters.Regex(r'^(Memes|memes|MEMES)$'), memes),
                      MessageHandler(filters.Regex(r'^(Colaborar|colaborar|COLABORAR)$'), colaborar),
                      MessageHandler(filters.Regex(r'^(Informacion|informacion|INFORMACION)$'), informacion),
                      MessageHandler(filters.Regex(r'^(Mensajear|mensajear|MENSAJEAR)$'), mensajear),
                      MessageHandler(filters.TEXT, start2)],
        states={
            ANSWER_charlar: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), answer_charlar)],
            ANSWER_meme: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), answer_meme)],
            ANSWER_informacion: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), answer_informacion)],
            ANSWER_colaborar: [MessageHandler(filters.Regex(r'^(Mensajear|mensajear|MENSAJEAR|Aportar|aportar|APORTAR)$'), answer_colaborar)],
            ANSWER_mensajear: [MessageHandler(filters.TEXT, mensajear)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(start_handler)
    
    application.add_handler(conv_handler)
    
    application.run_polling()
