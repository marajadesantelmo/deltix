from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, ConversationHandler, filters, MessageHandler

import os 
import urllib.request
os.chdir('/Users/facun/deltix/')
urllib.request.urlretrieve('https://alerta.ina.gob.ar/ina/42-RIODELAPLATA/productos/Prono_SanFernando.png', "Marea.png")


ANSWER = range(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE)-> None:
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(f"Hola {update.effective_user.first_name}! soy Deltix, el bot del humedal.\n"
              "Podés usar los siguientes comandos, tocando en ellos o escribiendolos en el chat\n "
              "- <b>/mareas </b>     <i>para obtener el informe de mareas del INA</i>,\n"
              "- <b>/charlar_un_rato</b>     <i>para que te cuente en que te puedo ayudar y para suscribirte a mis envios diarios</i>.\n"
              "Espero poder ofrecerte pronto un monton de cosas útiles para la vida isleña."
              ),
        parse_mode='HTML'
    )

async def charlar_un_rato(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Como te contaba {update.effective_user.first_name}, yo soy un bot en desarrollo y por ahora tan sólo puedo mandarte una vez por día el pronóstico de mareas del INA para el Puerto de San Fernando. ¿Querés recibir el pronóstico de mareas todos los días?",
    reply_markup=ReplyKeyboardMarkup(
        [["Si", "No"]], one_time_keyboard=True, input_field_placeholder="Si o No?"
    ),)
    
    return ANSWER

async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_response = update.message.text.lower()
    if user_response == 'si':
        await update.message.reply_text(
            "¡Gracias por suscribirte! A partir de ahora recibirás el pronóstico de mareas una vez al día a las 9 de la mañana. Te mando ahora el último pronóstico que tengo...",
        )
        return ConversationHandler.END
    if user_response == 'no':
        await update.message.reply_text(
            "Bueno... espero poder ayudarte en el futuro.",
        )
        return ConversationHandler.END
        
   
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Chauuu! Hablamos!", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END    

if __name__ == '__main__':
    application = ApplicationBuilder().token("5712079875:AAHhIWwnHN5ws0DEUggA8-STWKmM-ZJ5hQE").build()
    
    start_handler = CommandHandler('start', start)   #Ver si genera problemas que en conv_handler está igual
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("charlar_un_rato", charlar_un_rato)],
        states={
            ANSWER: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), answer)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    
    application.add_handler(start_handler)
    application.add_handler(conv_handler)
    
    application.run_polling()
