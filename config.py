from os import environ as env
from dotenv import load_dotenv
from json import loads

load_dotenv()

TELEGRAM_BOT_TOKEN = env['TELEGRAM_BOT_TOKEN']
GOOGLE_SPREADSHEET_ID = env['GOOGLE_SPREADSHEET_ID']
GOOGLE_SPREADSHEET_USER_COLUMNS = loads(env['GOOGLE_SPREADSHEET_USER_COLUMNS'])
GOOGLE_SPREADSHEET_FIRST_DATA_ROW = env['GOOGLE_SPREADSHEET_FIRST_DATA_ROW']
GOOGLE_API_ACCOUNT={
  "type": env['GOOGLE_API_ACCOUNT_TYPE'],
  "project_id": env['GOOGLE_API_ACCOUNT_PROJECT_ID'],
  "private_key_id": env['GOOGLE_API_ACCOUNT_PRIVATE_KEY_ID'],
  "private_key": env['GOOGLE_API_ACCOUNT_PRIVATE_KEY'],
  "client_email": env['GOOGLE_API_ACCOUNT_CLIENT_EMAIL'],
  "client_id": env['GOOGLE_API_ACCOUNT_CLIENT_ID'],
  "auth_uri": env['GOOGLE_API_ACCOUNT_AUTH_URI'],
  "token_uri": env['GOOGLE_API_ACCOUNT_TOKEN_URI'],
  "auth_provider_x509_cert_url": env['GOOGLE_API_ACCOUNT_AUTH_PROVIDER_X509_CERT_URL'],
  "client_x509_cert_url": env['GOOGLE_API_ACCOUNT_CLIENT_X509_CERT_URL']
}
SESSION_TTL = int(env['SESSION_TTL'])
