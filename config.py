from os import environ

API_ID = int(environ.get("API_ID", "27353035"))
API_HASH = environ.get("API_HASH", "cf2a75861140ceb746c7796e07cbde9e")
BOT_TOKEN = environ.get("BOT_TOKEN", "5843226951:AAEi-4rmnqU3gQ86Rv0hcuBFLUpdUGRhRcE")

# Make Bot Admin In Log Channel With Full Rights
LOG_CHANNEL = int(environ.get("LOG_CHANNEL", "0")) # Default to 0 (disabled) if not set in environment
ADMINS = int(environ.get("ADMINS", "1327021082"))

# Warning - Give Db uri in deploy server environment variable, don't give in repo.
DB_URI = environ.get("DB_URI", "mongodb+srv://poulomig644_db_user:d9MMUd5PsTP5MDFf@cluster0.q5evcku.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0") # Warning - Give Db uri in deploy server environment variable, don't give in repo.
DB_NAME = environ.get("DB_NAME", "vjlinkchangerbot")
