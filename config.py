from os import environ

API_ID = int(environ.get("API_ID", "27353035"))
API_HASH = environ.get("API_HASH", "cf2a75861140ceb746c7796e07cbde9e")

# User API Credentials (Must be different from Bot API for user sessions)
USER_API_ID = int(environ.get("USER_API_ID", "27021520"))
USER_API_HASH = environ.get("USER_API_HASH", "a0b7c53390bdcbdb80cb1264b9ea40b6")
BOT_TOKEN = environ.get("BOT_TOKEN", "6431724067:AAHYRtmLAy91HpRonTd2oZvuxoCh9X0MFMA")

# Make Bot Admin In Log Channel With Full Rights
LOG_CHANNEL = int(environ.get("LOG_CHANNEL", "-1002073865889")) # Default to 0 (disabled) if not set in environment
ADMINS = int(environ.get("ADMINS", "1327021082"))

# Warning - Give Db uri in deploy server environment variable, don't give in repo.
DB_URI = environ.get("DB_URI", "mongodb+srv://poulomig644_db_user:d9MMUd5PsTP5MDFf@cluster0.q5evcku.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0") # Warning - Give Db uri in deploy server environment variable, don't give in repo.
DB_NAME = environ.get("DB_NAME", "vjlinkchangerbot")
