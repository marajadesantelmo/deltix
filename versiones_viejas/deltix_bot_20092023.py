from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, ConversationHandler, filters, MessageHandler
import pandas as pd
import os 
import urllib.request
import random
import time


os.chdir('C:/Users/facun/OneDrive/Documentos/deltix/')
urllib.request.urlretrieve('https://alerta.ina.gob.ar/ina/42-RIODELAPLATA/productos/Prono_SanFernando.png', "marea.png")

# ANSWER, ANSWER_meme = range(2)
ANSWER, ANSWER_meme, ANSWER_colaborar, ANSWER_mensajear = range(4)

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
        text=("- <b>/charlar</b>   <i>para charlar conmigo y suscribirte a mis envios diarios</i>.\n"
              "- <b>/mareas </b>   <i>para obtener el pronóstico de hoy de mareas del INA &#9875</i>\n"
              "- <b>/memes </b>   <i>para ver los memes más divertidos de la isla</i>\n"
              "- <b>/informacion </b>   <i>para saber más sobre Deltix &#128057</i>\n"
              "- <b>/colaborar </b>   <i>para hacer sugerencias o un aporte monetario</i>\n"             
              "- <b>/desuscribirme </b>   <i>para darte de baja de los envios diarios &#x1F989</i>\n"
              ),
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup([["/charlar", "/mareas", "/memes"], ["/informacion", "/colaborar", "/desuscribirme"] ]))

async def charlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Soy un bot en desarrollo y mi mayor gracia es mandarte una vez por día el pronóstico de mareas del INA. ¿Querés recibir el pronóstico de mareas de San Fernando todos los días?",
    reply_markup=ReplyKeyboardMarkup(
        [["Si", "No"]], one_time_keyboard=True, input_field_placeholder="Si o No?"
    ),)
    return ANSWER

async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
            return ConversationHandler.END
        
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
            return ConversationHandler.END
        
    if user_response == 'no':
        await update.message.reply_text(
            "Bueno... espero poder ayudarte en el futuro.",
        )
        return ConversationHandler.END
    
async def mareas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        chat_id=update.effective_chat.id
        await update.message.reply_text(
            "Ahí te mando el informe de mareas del INA para San Fernando",
        )
        await context.bot.send_photo(chat_id, open("Marea.png", "rb"))
        return ConversationHandler.END
    
async def memes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        chat_id=update.effective_chat.id
        await update.message.reply_text("A mí también me encantan los memes islenials &#128514 Te mando uno.",
                                        parse_mode='HTML')
        time.sleep(1)
        numero = random.randint(1, 13)
        await context.bot.send_photo(chat_id, open(f"memes/{numero}.png", "rb"))
        time.sleep(1)
        await update.message.reply_text("Buenísimo, no? Son de la página Memes Islenials. Te recomiendo que lo sigas en las redes",)
        await update.message.reply_text("Querés otro meme?",
        reply_markup=ReplyKeyboardMarkup(
            [["Si", "No"]], one_time_keyboard=True, input_field_placeholder="Si o No?"
        ),)
        return ANSWER_meme
    
async def answer_meme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        chat_id=update.effective_chat.id
        user_response = update.message.text.lower()
        if user_response == 'si':
            await update.message.reply_text("Dale, te mando otro")
            time.sleep(1)
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
                "Bueno... espero poder ayudarte en el futuro. Cualquier cosa tocá en algunas de las actividades que quieras hacer conmigo",
                reply_markup=ReplyKeyboardMarkup([["/charlar", "/mareas", "/memes"], ["/informacion", "/colaborar", "/desuscribirme"] ])
            )
            return ConversationHandler.END

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
        await update.message.reply_text("Hasta ahora la única forma de aportar económicamente es haciéndole una transferencia a mi desarrollador. Lo podés hacer enviando dinero al alias FACUNDO.LASTRA que es una cuenta del BNA", parse_mode='HTML')
        return ConversationHandler.END

# Version anterior por las dudas
# async def answer_colaborar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#         user_response = update.message.text.lower()
#         if user_response == 'mensajear':
#             await update.message.reply_text("Escribí el mensaje y yo se lo reenvio al desarrollador",
#                                             parse_mode='HTML')
#             return ANSWER_mensajear
#         if user_response == 'aportar':
#             await update.message.reply_text("Muchas gracias por pensar en aportar &#128591 Nos viene muy bien para poder seguir dedicándole tiempo a Deiltix y hacer que crezca este proyecto",
#                                             parse_mode='HTML')
#             await update.message.reply_text("Hasta ahora la única forma de aportar económicamente es haciéndole una transferencia a mi desarrollador. Lo podés hacer enviando dinero al alias FACUNDO.LASTRA que es una cuenta del BNA",
#                                             parse_mode='HTML')
#             return ConversationHandler.END

# def mensajear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     user = update.message.from_user
#     message_text = update.message.text
#     # Enviar el mensaje al desarrollador
#     context.bot.send_message(chat_id=672134330, text=f'Mensaje de {user.first_name}: {message_text}')
#     update.message.reply_text('Mensaje enviado al desarrollador de Deltix con éxito. ¡Gracias!')
#     return ConversationHandler.END

if __name__ == '__main__':
    application = ApplicationBuilder().token("5712079875:AAHhIWwnHN5ws0DEUggA8-STWKmM-ZJ5hQE").build()
    
    start_handler = CommandHandler('start', start)
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("charlar", charlar),
                      CommandHandler('mareas', mareas),
                      CommandHandler('desuscribirme', desuscribirme), 
                      CommandHandler('memes', memes), 
                      CommandHandler('colaborar', colaborar), 
                      MessageHandler(filters.TEXT, start)],  
        states={
            ANSWER: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), answer)],
            ANSWER_meme: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), answer_meme)],
            ANSWER_colaborar: [MessageHandler(filters.Regex(r'^(Mensajear|mensajear|MENSAJEAR|Colaborar|colaborar|COLABORAR)$'), answer_colaborar)],
            # ANSWER_mensajear: [MessageHandler(filters.TEXT, mensajear)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(start_handler)
    application.add_handler(conv_handler)
    
    application.run_polling()
