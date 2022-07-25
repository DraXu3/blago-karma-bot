import logging

from config import TELEGRAM_BOT_TOKEN, GOOGLE_API_ACCESS_FILE, GOOGLE_SPREADSHEET_ID, SESSION_TTL
from config import GOOGLE_SPREADSHEET_USER_COLUMNS, GOOGLE_SPREADSHEET_FIRST_DATA_ROW
from google_spreadsheet_manager import GoogleSpreadsheetManager
from vote_manager import VoteManager
from bot_manager import BotManager
from session_manager import SessionManager

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

if __name__ == '__main__':
    google_spreadsheet_manager = GoogleSpreadsheetManager(
        access_file=GOOGLE_API_ACCESS_FILE,
        spreadsheet_id=GOOGLE_SPREADSHEET_ID,
        spreadsheet_user_columns=GOOGLE_SPREADSHEET_USER_COLUMNS,
        spreadsheet_first_data_row=GOOGLE_SPREADSHEET_FIRST_DATA_ROW
    )

    vote_manager = VoteManager(google_spreadsheet_manager=google_spreadsheet_manager)
    session_manager = SessionManager(session_ttl=SESSION_TTL)

    bot_manager = BotManager(
        token=TELEGRAM_BOT_TOKEN,
        vote_manager=vote_manager,
        session_manager=session_manager
    )

    bot_manager.run()
