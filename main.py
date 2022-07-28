import logging

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_USERS, GOOGLE_API_ACCOUNT, GOOGLE_SPREADSHEET_ID, SELECT_USER_SESSION_TTL
from config import CONFIRM_REQUEST_SESSION_TTL, GOOGLE_SPREADSHEET_USER_COLUMNS, GOOGLE_SPREADSHEET_FIRST_DATA_ROW

from managers.google_spreadsheet import GoogleSpreadsheetManager
from managers.karma import KarmaManager
from managers.bot import BotManager
from managers.session import SessionManager, SessionType
from managers.users import UsersManager

logging.basicConfig(
    format='%(asctime)s %(levelname)s [%(name)s:%(funcName)s]: %(message)s',
    level=logging.INFO
)

google_spreadsheet_manager = GoogleSpreadsheetManager(
    account_dict=GOOGLE_API_ACCOUNT,
    spreadsheet_id=GOOGLE_SPREADSHEET_ID,
    spreadsheet_user_columns=GOOGLE_SPREADSHEET_USER_COLUMNS,
    spreadsheet_first_data_row=GOOGLE_SPREADSHEET_FIRST_DATA_ROW
)

session_manager = SessionManager(session_ttls={
    SessionType.SELECT_USER: SELECT_USER_SESSION_TTL,
    SessionType.CONFIRM_REQUEST: CONFIRM_REQUEST_SESSION_TTL
})

karma_manager = KarmaManager(google_spreadsheet_manager=google_spreadsheet_manager)
users_manager = UsersManager(users=TELEGRAM_USERS)

bot_manager = BotManager(
    token=TELEGRAM_BOT_TOKEN,
    karma_manager=karma_manager,
    session_manager=session_manager,
    users_manager=users_manager
)

if __name__ == '__main__':
    bot_manager.run()
