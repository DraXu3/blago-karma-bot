from os import environ as env
from dotenv import load_dotenv
from json import loads

load_dotenv()

TELEGRAM_BOT_TOKEN = env['TELEGRAM_BOT_TOKEN']
GOOGLE_API_ACCESS_FILE = env['GOOGLE_API_ACCESS_FILE']
GOOGLE_SPREADSHEET_ID = env['GOOGLE_SPREADSHEET_ID']
GOOGLE_SPREADSHEET_USER_COLUMNS = loads(env['GOOGLE_SPREADSHEET_USER_COLUMNS'])
GOOGLE_SPREADSHEET_FIRST_DATA_ROW = 3
SESSION_TTL = 60 * 60 * 10