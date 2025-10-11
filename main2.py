from telegram.ext import ApplicationBuilder,  CommandHandler, ConversationHandler, filters, MessageHandler
import pandas as pd
import nest_asyncio
import os
import asyncio
import random
from tokens import telegram_token
from deltix_funciones import *
from llm_connector import get_llm_response, create_conversation, get_db_connection
import mysql.connector
from mysql.connector import Error

# Initialize a dictionary to store project IDs for each user
user_projects = {}

if os.path.exists('/home/facundol/deltix/'):
    base_path = '/home/facundol/deltix/'
else:
        base_path = ''
user_experience_path = base_path + 'user_experience.csv'

def store_chat_message(phone_number, role, content):
    """Store a chat message in MySQL."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # get conversation ID from the database by phone number
        cursor.execute("SELECT id FROM conversations WHERE name = %s", (phone_number,))
        conversation_id = cursor.fetchone()
        
        if conversation_id is None:
            print(f"No conversation found for phone: {phone_number}. Creating a new one.")
            conversation_id = create_conversation(phone_number)
            # Get the conversation ID in the correct format
            if not isinstance(conversation_id, (tuple, list)):
                conversation_id = (conversation_id,)

        conn = get_db_connection()
        cursor = conn.cursor()    
        cursor.execute(
            "INSERT INTO chat_history (conversation_id, role, content) VALUES (%s, %s, %s)",
            (conversation_id[0], role, content)
        )
        conn.commit()
        
        # Verify insertion
        message_id = cursor.lastrowid
        print(f"Message stored with ID: {message_id}")
        
        cursor.close()
        return True
    except Error as err:
        print(f"Error storing chat message: {err}")
        if 'conn' in locals() and conn:
            conn.rollback()
        return False

try:
    user_experience = pd.read_csv(user_experience_path)
except pd.errors.ParserError:
    # If there's a parser error, try with more robust error handling
    print("Warning: Issues detected in the CSV file. Attempting to load with error handling...")
    # Use on_bad_lines='skip' for newer pandas versions or error_bad_lines=False for older versions
    try:
        # Try with newer pandas syntax
        user_experience = pd.read_csv(user_experience_path, on_bad_lines='skip')
    except TypeError:
        # Fall back to older pandas syntax if needed
        user_experience = pd.read_csv(user_experience_path, error_bad_lines=False)
    
    # Save a clean version of the file to prevent future errors
    print("Saving a cleaned version of the user experience data...")
    user_experience.to_csv(user_experience_path, index=False)
    print("File cleaned and saved successfully.")

# Create helper function to track bot responses
async def track_bot_response(user_id, message_text):
    """Store bot response in chat history"""
    try:
        store_chat_message(user_id, "assistant", message_text)
    except Exception as e:
        print(f"Failed to store bot message: {e}")

# Create a function to track the reply
async def tracked_reply(update, text, *args, **kwargs):
    """Helper function to send a reply and track it in history"""
    # First send the reply
    await update.message.reply_text(text, *args, **kwargs)
    
    # Then store it in chat history
    try:
        await track_bot_response(update.effective_user.id, text)
    except Exception as e:
        print(f"Failed to track bot response: {e}")

# Update the llm_fallback handler to use tracked_reply
async def llm_fallback(update, context):
    user_id = update.effective_user.id
    user_input = update.message.text
    
    # Create a task to send "Dejame pensar..." after 3 seconds
    thinking_message_task = asyncio.create_task(
        send_thinking_message_after_delay(update, context, 3)
    )
    
    try:
        # Get response from LLM (ensure this is awaited)
        # Don't track the message here since it's already tracked by the handler wrapper
        llm_response = await asyncio.to_thread(get_llm_response, user_input, user_id)
        
        # Cancel the thinking message task if it hasn't been sent yet
        thinking_message_task.cancel()
        
        # Send the response back to the user and track it
        await tracked_reply(update, llm_response)
    except Exception as e:
        # Log the error and notify the user
        print(f"Error in LLM fallback: {e}")
        await tracked_reply(update, "Lo siento, ocurrió un error al procesar tu consulta. Por favor, intentá más tarde.")
    
    # Return to the conversation handler state
    return ConversationHandler.END

# Helper function to send "Dejame pensar..." after a delay
async def send_thinking_message_after_delay(update, context, delay_seconds):
    # List of possible thinking messages
    thinking_messages = [
        "Dejame pensar...",
        "...estoy pensando...",
        "...deltix pensando...",
        "Aguantame que pienso qué responderte",
        "Procesando tu consulta...",
        "Dame unos segundos para pensar...",
        "ya te pienso una respuesta...",
        "Un momento, por favor...",
        "Conectando neuronas artificiales...",
        "Buscando la mejor respuesta..."
    ]
    
    try:
        await asyncio.sleep(delay_seconds)
        thinking_message = random.choice(thinking_messages)
        
        # Send and track the thinking message
        await tracked_reply(update, thinking_message)
    except asyncio.CancelledError:
        # Task was cancelled because response arrived before timeout
        pass

# Define the wrap_handler_with_tracking function (keep only one version)
def wrap_handler_with_tracking(handler):
    """Wrap a handler with message tracking functionality"""
    if isinstance(handler, (CommandHandler, MessageHandler)):
        original_callback = handler.callback
        
        async def wrapped_callback(update, context):
            # Track user message exactly once
            if update.message and update.message.text:
                user_id = update.effective_user.id
                try:
                    # Only track messages here, remove tracking from llm_connector.py
                    store_chat_message(user_id, "user", update.message.text)
                except Exception as e:
                    print(f"Failed to store user message: {e}")
            
            # Add tracked_reply to context for handlers to use
            context.tracked_reply = lambda text, *args, **kwargs: tracked_reply(update, text, *args, **kwargs)
            
            # Call original handler
            return await original_callback(update, context)
        
        handler.callback = wrapped_callback
    
    elif isinstance(handler, ConversationHandler):
        # Wrap entry points
        for entry_point in handler.entry_points:
            wrap_handler_with_tracking(entry_point)
        
        # Wrap state handlers
        for state, state_handlers in handler.states.items():
            for state_handler in state_handlers:
                wrap_handler_with_tracking(state_handler)
        
        # Wrap fallbacks
        for fallback in handler.fallbacks:
            wrap_handler_with_tracking(fallback)
    
    return handler

nest_asyncio.apply()

if __name__ == '__main__':
    application = ApplicationBuilder().token(telegram_token).build()
    
    # Define command handlers and wrap them with tracking
    command_handlers = [
        wrap_handler_with_tracking(CommandHandler("start", start)),
        wrap_handler_with_tracking(CommandHandler("menu", menu)),
        wrap_handler_with_tracking(CommandHandler("cancel", cancel)),
        wrap_handler_with_tracking(CommandHandler('charlar', charlar)),
        wrap_handler_with_tracking(CommandHandler('mareas', mareas)),
        wrap_handler_with_tracking(CommandHandler('mareaa', mareas)),
        wrap_handler_with_tracking(CommandHandler('windguru', windguru)),
        wrap_handler_with_tracking(CommandHandler('memes', memes)),
        wrap_handler_with_tracking(CommandHandler('colaborar', colaborar)),
        wrap_handler_with_tracking(CommandHandler('mensajear', mensaje_trigger)),
        wrap_handler_with_tracking(CommandHandler('colectivas', colectivas)),
        wrap_handler_with_tracking(CommandHandler('almaceneras', almaceneras)),
        wrap_handler_with_tracking(CommandHandler('hidrografia', hidrografia)),
        wrap_handler_with_tracking(CommandHandler('suscribirme', suscribirme)),
        wrap_handler_with_tracking(CommandHandler('desuscribirme', desuscribirme)),
        wrap_handler_with_tracking(CommandHandler('amanita', amanita)),
        wrap_handler_with_tracking(CommandHandler('alfareria', alfareria)),
        wrap_handler_with_tracking(CommandHandler('labusqueda', labusqueda)),
        wrap_handler_with_tracking(CommandHandler('canaveralkayaks', canaveralkayaks)),
        wrap_handler_with_tracking(CommandHandler('charco_masajes', charco_masajes)),
        wrap_handler_with_tracking(CommandHandler('familia_islena', familia_islena)),
    ]
    
    # Other handlers for message text with tracking
    message_handlers = [
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(Mareas|mareas|MAREAS|Marea|marea|MAREA)$'), mareas)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(Windguru|windguru|WINDGURU)$'), windguru)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(Desuscribirme|desuscribirme|DESUSCRIBIRME)$'), desuscribirme)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(Memes|memes|MEMES|Meme|meme|MEME)$'), memes)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(Colaborar|colaborar|COLABORAR)$'), colaborar)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(Mensajear|mensajear|MENSAJEAR)$'), mensaje_trigger)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(Hola|hola|HOLA)[\s!,.¿?]*'), start)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(Colectivas|colectivas|COLECTIVAS|horarios)$'), colectivas)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(Gracias|gracias|GRACIAS)$'), de_nada)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(Interislena|interislena|INTERISLENA)$'), Interislena)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(Jilguero|jilguero|JILGUERO)$'), Jilguero)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(LineasDelta|lineasdelta|LINEASDELTA)$'), LineasDelta)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(Almaceneras|almaceneras|ALMACENERAS)$'), almaceneras)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(Hidrografia|hidrografia|HIDROGRAFIA)$'), hidrografia)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(Suscribirme|suscribirme|SUSCRIBIRME)$'), suscribirme)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(Amanita|amanita|AMANITA)$'), amanita)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(Alfareria|alfareria|ALFARERIA)$'), alfareria)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(Labusqueda|labusqueda|LABUSQUEDA)$'), labusqueda)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(Canaveralkayaks|canaveralkayaks|CANAVERALKAYAKS)$'), canaveralkayaks)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(masajes|charco|MASAJES)$'), charco_masajes)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'^(familia islena|familia_islena|FAMILIA ISLENA)$'), familia_islena)),
        # Handlers for words contained in messages
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bcharlar\b.*)'), charlar)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bmareas\b.*)'), mareas)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bmarea\b.*)'), mareas)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bhidrografia\b.*)'), hidrografia)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bwindguru\b.*)'), windguru)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bdesuscribirme\b.*)'), desuscribirme)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bmemes\b.*)'), memes)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bmeme\b.*)'), memes)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bcolaborar\b.*)'), colaborar)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bmensajear\b.*)'), mensaje_trigger)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bhola\b.*)'), start)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bcolectivas\b.*)'), colectivas)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bgracias\b.*)'), de_nada)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bJilguero\b.*)'), Jilguero)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bInterislena\b.*)'), Interislena)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bLineasDelta\b.*)'), LineasDelta)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\balmaceneras\b.*)'), almaceneras)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\balmacenera\b.*)'), almaceneras)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\balmacén\b.*)'), almaceneras)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\balmacen\b.*)'), almaceneras)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bhidrografia\b.*)'), hidrografia)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bamanita\b.*)'), amanita)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\balfareria\b.*)'), alfareria)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\blabusqueda\b.*)'), labusqueda)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bcanaveralkayaks\b.*)'), canaveralkayaks)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bmasajes\b.*)'), charco_masajes)),
        wrap_handler_with_tracking(MessageHandler(filters.Regex(r'(?i)(.*\bfamilia islena\b.*)'), familia_islena)),
        # LLM como fallback
        MessageHandler(filters.TEXT, llm_fallback)
    ]
    
    # Combine all handlers, with command handlers first to ensure they take priority
    handlers = command_handlers + message_handlers

    # Wrap the conversation handler with tracking
    conv_handler = wrap_handler_with_tracking(ConversationHandler(
        entry_points=handlers,
        states={
            ANSWER_charlar: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), answer_charlar)],
            ANSWER_meme: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), answer_meme)],
            ANSWER_meme2: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), answer_meme2)],
            ANSWER_colaborar: [MessageHandler(filters.Regex(r'^(Mensajear|mensajear|MENSAJEAR|Aportar|aportar|APORTAR)$'), answer_colaborar)],
            ANSWER_mareas_suscribir: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), mareas_suscribir)],
            ANSWER_windguru_suscribir: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), windguru_suscribir)],
            ANSWER_hidrografia_suscribir: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), hidrografia_suscribir)],
            ANSWER_mensajear: [MessageHandler(filters.TEXT, mensajear)],
            ANSWER_desuscribir: [MessageHandler(filters.Regex(r'^(Mareas|MAREAS|mareas|Windguru|WINDGURU|windguru|Hidrografía|HIDROGRAFÍA|hidrografia|Hidrografia)$'), answer_desuscribir)],
            ANSWER_charlar_windguru: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), charlar_windguru)],
            ANSWER_jilguero: [MessageHandler(filters.TEXT, answer_jilguero)],
            ANSWER_interislena: [MessageHandler(filters.TEXT, answer_interislena)],
            ANSWER_direction: [MessageHandler(filters.TEXT, direction)],
            ANSWER_schedule: [MessageHandler(filters.TEXT, schedule)],
            ANSWER_almacenera_select: [MessageHandler(filters.TEXT, almacenera_selected)],
            ANSWER_colectivas: [MessageHandler(filters.TEXT, answer_colectivas)],
            ANSWER_suscribirme: [MessageHandler(filters.Regex(r'^(Mareas|mareas|Hidrografia|hidrografia|Windguru|windguru)$'), answer_suscribirme)],
        },
        # LLM fallback handler
        fallbacks=[MessageHandler(filters.TEXT, llm_fallback)] + handlers,
    ))

    application.add_handler(conv_handler)
    application.run_polling()