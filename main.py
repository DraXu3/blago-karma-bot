import logging

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_USERS, TELEGRAM_CHAT_ID, GOOGLE_API_ACCOUNT, GOOGLE_SPREADSHEET_ID, SELECT_USER_SESSION_TTL
from config import CONFIRM_REQUEST_SESSION_TTL, GOOGLE_SPREADSHEET_USER_COLUMNS, GOOGLE_SPREADSHEET_FIRST_DATA_ROW

from services.google_spreadsheet import GoogleSpreadsheetService
from services.karma import KarmaService
from services.bot import BotService
from services.session import SessionService, SessionType
from services.users import UsersService


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def init():
    google_spreadsheet_service = GoogleSpreadsheetService(
        account_dict=GOOGLE_API_ACCOUNT,
        spreadsheet_id=GOOGLE_SPREADSHEET_ID,
        spreadsheet_user_columns=GOOGLE_SPREADSHEET_USER_COLUMNS,
        spreadsheet_first_data_row=GOOGLE_SPREADSHEET_FIRST_DATA_ROW
    )

    session_service = SessionService(session_ttls={
        SessionType.SELECT_USER: SELECT_USER_SESSION_TTL,
        SessionType.CONFIRM_REQUEST: CONFIRM_REQUEST_SESSION_TTL
    })

    karma_service = KarmaService(google_spreadsheet_service=google_spreadsheet_service)
    users_service = UsersService(users=TELEGRAM_USERS)

    bot_service = BotService(
        token=TELEGRAM_BOT_TOKEN,
        karma_service=karma_service,
        session_service=session_service,
        users_service=users_service,
        chat_id=TELEGRAM_CHAT_ID
    )

    return bot_service

if __name__ == '__main__':
    bot_service = init()
    bot_service.run()
