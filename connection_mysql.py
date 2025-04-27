import os
import mysql.connector


# Load environment variables or tokens
try:
    from tokens import supabase_url, supabase_key, openrouter_key, mysql_password, mysql_database
except ImportError:
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    mysql_password = os.getenv('MYSQL_PASSWORD')
    mysql_database = os.getenv('MYSQL_DATABASE')

# Connect to the MySQL database
db = mysql.connector.connect(
    host="facundol.mysql.pythonanywhere-services.com",
    user="facundol",
    password= mysql_password,
    database= mysql_database
)
