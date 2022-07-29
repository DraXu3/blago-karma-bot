from telegram import Update, MessageEntity, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import filters, ApplicationBuilder, ContextTypes
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.constants import ParseMode
from enum import Enum
import asyncio
import logging

from managers.session import SessionType, SessionException


class ConfirmOptions(str, Enum):
    CONFIRM = 'CONFIRM',
    DECLINE = 'DECLINE'

class RequestType(str, Enum):
    UP = 'UP',
    DOWN = 'DOWN'


def restrict_public_access(inherited_self=None):
    def _restrict_public_access(command):
        async def _restricted_command(*args):
            logger.info(args)

            if inherited_self:
                [self, update] = [inherited_self, args[0]]
            else:
                [self, update, _] = args

            message = update.message if not update.callback_query else update.callback_query.message
            from_chat_id = message.chat.id
            from_user = message["from"]

            if from_chat_id != self.chat_id:
                logger.error(f"Received update from prohibited chat (chat_id={message.chat.id}, user={from_user})")

                reply_text = f"\uE252 _Бот не может быть использован в этом чате_"
                await message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
                return

            await command(*args)

        return _restricted_command
    return _restrict_public_access


logger = logging.getLogger(__name__)

class BotManager:
    def __init__(self, token, karma_manager, session_manager, users_manager, chat_id):
        self.application = ApplicationBuilder().token(token).build()
        self.karma_manager = karma_manager
        self.session_manager = session_manager
        self.users_manager = users_manager
        self.chat_id = chat_id

        self.confirm_request_reply_markup = self._build_reply_markup({
            ConfirmOptions.CONFIRM: 'Разрешить',
            ConfirmOptions.DECLINE: 'Отклонить'
        })

        start_handler = CommandHandler('help', self.help)
        self.application.add_handler(start_handler)
        
        up_handler = CommandHandler('up', self._create_request_command(RequestType.UP))
        self.application.add_handler(up_handler)

        down_handler = CommandHandler('down', self._create_request_command(RequestType.DOWN))
        self.application.add_handler(down_handler)

        show_handler = CommandHandler('show', self.show)
        self.application.add_handler(show_handler)

        unknown_handler = MessageHandler(filters.COMMAND, self.unknown)
        self.application.add_handler(unknown_handler)

        select_user_callback_query_handler = CallbackQueryHandler(self.select_user, pattern=r"^\d+$")
        self.application.add_handler(select_user_callback_query_handler)

        confirm_request_callback_query_handler = CallbackQueryHandler(self.confirm_request, pattern=rf"^(?:{ConfirmOptions.CONFIRM}|{ConfirmOptions.DECLINE})$")
        self.application.add_handler(confirm_request_callback_query_handler)

    def _get_user_markup(self, user):
        user_name = user.id
        if user.first_name:
            user_name = user.first_name
        if user.last_name:
            user_name += f" {user.last_name}"
        return f"[{user_name}](tg://user?id={user.id})"

    def _build_reply_markup(self, data):
        inline_keyboard_layout = []
        row_layout = []
        counter = 0

        for data_id, data_value in data.items():
            row_layout.append(InlineKeyboardButton(data_value, callback_data=data_id))
            counter += 1
            if counter > 1:
                counter = 0
                inline_keyboard_layout.append(row_layout)
                row_layout = []
                
        if counter > 0:
            inline_keyboard_layout.append(row_layout)

        return InlineKeyboardMarkup(
            inline_keyboard_layout,
            one_time_keyboard=True,
            resize_keyboard=True
        )

    async def _get_user_data(self, update: Update, user_id):
        try:
            user_data = await update.message.chat.get_member(user_id)
            logger.info(f"Received user data from API (user_id={user_id}): {user_data}")
            return user_data.user
        except Exception as err:
            logger.error(f"Error fetching user data from API (user_id={user_id}): {err}")
            return None

    async def _select_user_expired_callback(self, session):
        logger.info(f"Expired callback was triggered for session (session_id={session['id']}, session_type=SessionType.SELECT_USER)")
        logger.warning(f"Select user message will be deleted (message_id={session['data']['select_user_message'].message_id})")

        await session["data"]["select_user_message"].delete()
        await session["data"]["request_message"].reply_text(text=f"\uE252 _Запрос более не актуален_", parse_mode=ParseMode.MARKDOWN)

    async def _confirm_request_expired_callback(self, session):
        logger.info(f"Expired callback was triggered for session (session_id={session['id']}, session_type=SessionType.CONFIRM_REQUEST)")
        logger.warning(f"Confirm request message will be deleted (message_id={session['data']['confirm_request_message'].message_id})")

        await session["data"]["confirm_request_message"].delete()
        await session["data"]["request_message"].reply_text(text=f"\uE252 _Запрос более не актуален_", parse_mode=ParseMode.MARKDOWN)

    def _create_request_command(self, request_type):
        @restrict_public_access(self)
        async def request_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.info(f"Update received: {update}")

            command_entity = update.message.entities[0]
            reason = update.message.text[command_entity.offset+command_entity.length:].strip()
            reason = None if len(reason) == 0 else reason

            request_message = update.message
            requesting_user = update.message['from']

            if self.session_manager.user_has_session(requesting_user.id, filter_by_type=SessionType.SELECT_USER):
                logger.error(f"User already has an active session (user_id={requesting_user.id}, session_type=SessionType.SELECT_USER)")

                reply_text = f"\uE252 _Активная сессия выбора участника уже была инициирована_"
                await request_message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
                return

            reply_text = f"\U0001F464 Выберите участника:"
            reply_markup = self._build_reply_markup(self.users_manager.get_all_users(except_user=requesting_user.id))
            select_user_message = await request_message.reply_text(text=reply_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

            logger.info(f"Select user message was sent (message_id={select_user_message.message_id})")

            try:
                session_data = {
                    "requesting_user": requesting_user,
                    "request_message": request_message,
                    "request_type": request_type,
                    "select_user_message": select_user_message,
                    "reason": reason
                }

                session_id = self.session_manager.create_session(
                    id=select_user_message.message_id,
                    type=SessionType.SELECT_USER,
                    user=requesting_user,
                    expired_callback=self._select_user_expired_callback,
                    data=session_data
                )

                logger.info(f"Session was created (user_id={requesting_user.id}, session_type=SessionType.SELECT_USER)")
            except Exception as err:
                logger.error(f"Error creating session for user (user_id={requesting_user.id}, session_type=SessionType.SELECT_USER): {err}")
                logger.warning(f"Select user message will be deleted (message_id={select_user_message.message_id})")

                await select_user_message.delete()

                reply_text = f"\uE252 _Команда не может быть выполнена_"
                await request_message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
                
        return request_command

    @restrict_public_access()
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        reply_text="\U0001F921 Я *Карма Бот*, я манипулирую кармой\n\n" \
            + "Поддерживаются следующие команды:\n\n" \
            + "  - `/help`: вывести список поддерживаемых команд\n\n" \
            + "  - `/up [reason]`: запросить участнику *+1 ОК* по причине `\"reason\"` (опционально)\n\n" \
            + "  - `/down [reason]`: запросить участнику *-1 ОК* по причине `\"reason\"` (опционально)\n\n" \
            + "  - `/show [user_mention]`: показать количество *ОК* участника `\"@user_mention\"` (или всех участников, если параметр не задан)"

        await update.message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
        
    @restrict_public_access()
    async def show(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Update received: {update}")

        mention_entity = None if len(update.message.entities) < 2 else update.message.entities[1]
        mentioned_user = None
        if mention_entity and mention_entity.user and mention_entity.type == MessageEntity.TEXT_MENTION:
            mentioned_user = mention_entity.user

        # show info for specific user only
        if mentioned_user:
            logger.info(f"Found mentioned user. Getting total value for the user: {mentioned_user}")

            try:
                total = self.karma_manager.get_total_value(mentioned_user.id)
            except Exception as err:
                logger.error(f"Error getting total value for the user (user_id={mentioned_user.id}): {err}")

                reply_text=f"\uE252 _Упомянутый участник не зарегистрирован_"
                await update.message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
            else:
                logger.info(f"Received total values for the user (user_id={mentioned_user.id}): {total}")

                reply_text=f"\U0001F50E Участник {self._get_user_markup(mentioned_user)} имеет *{total} OK*"
                await update.message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
        
        # show info for all users
        else:
            logger.info(f"No mentioned user found. Getting total values for all users")

            try:
                total = self.karma_manager.get_total_values()
                total = sorted(list(total.items()), key=lambda item: item[1], reverse=True)
            except Exception as err:
                logger.error(f"Error getting total values for all users: {err}")

                reply_text=f"\uE252 _Команда не может быть выполнена_"
                await update.message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
                return

            logger.info(f"Received total values for all users: {total}")

            users = await asyncio.gather(*[self._get_user_data(update, record[0]) for record in total])

            reply_text = "\uE131 Текущий рейтинг участников:\n\n"
            for (index, record) in enumerate(total):
                [user_id, amount] = record
                if users[index]:
                    user = self._get_user_markup(users[index])
                else:
                    user = self.users_manager.get_user_name(user_id)
                reply_text += f"  {index + 1}. {user}: *{amount} OK*\n"           
            await update.message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)

    @restrict_public_access()
    async def unknown(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        reply_text="\uE252 _Неизвестная команда, наберите /help для помощи_"
        await update.message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)

    @restrict_public_access()
    async def select_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Update received: {update}")

        select_user_message = update.callback_query.message

        try:
            select_user_session = self.session_manager.get_session(select_user_message.message_id)
        except Exception as err:
            logger.error(f"Error getting session (session_id={select_user_message.message_id}): {err}")
            logger.warning(f"Select user message will be deleted (message_id={select_user_message.message_id})")

            await select_user_message.delete()

            reply_text=f"\uE252 _Запрос более не актуален_"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=reply_text, parse_mode=ParseMode.MARKDOWN)
            return

        requesting_user = select_user_session["data"]["requesting_user"]
        request_message = select_user_session["data"]["request_message"]
        request_type = select_user_session["data"]["request_type"]
        reason = select_user_session["data"]["reason"]
        
        if self.session_manager.session_is_expired(select_user_session):
            logger.warning(f"Session is expired (session_id={select_user_session['id']}, session_type=SessionType.SELECT_USER)")
            logger.warning(f"Session will be deleted (session_id={select_user_session['id']}, session_type=SessionType.SELECT_USER)")
            logger.warning(f"Select user message will be deleted (message_id={select_user_message.message_id})")

            self.session_manager.delete_session(select_user_session["id"])            
            await select_user_message.delete()

            reply_text=f"\uE252 _Запрос более не актуален_"
            await request_message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
            return

        logger.info(f"Found active session (session_id={select_user_session['id']}, session_type=SessionType.SELECT_USER)")

        selecting_user = update.callback_query["from"]
        selected_user_id = int(update.callback_query.data)

        if requesting_user.id != selecting_user.id:
            logger.error("Error selecting a user: only requesting user is able to do that (requesting_user_id={equesting_user.id}, selecting_user_id={selecting_user.id})")

            reply_text=f"\uE252 _Только инициатор запроса может указать участника_"
            await request_message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
            return

        self.session_manager.delete_session(select_user_session["id"])
        await select_user_message.delete()

        logger.info(f"Session was deleted (session_id={select_user_session['id']}, session_type=SessionType.SELECT_USER)")
        logger.info(f"Select user message was deleted (message_id={select_user_message.message_id})")

        ok_amount_text = "+1" if request_type == RequestType.UP else "-1"
        selected_user_name = self.users_manager.get_user_name(selected_user_id)
        reply_text = f"\U0001F4AC Участник {self._get_user_markup(selecting_user)} запрашивает *{ok_amount_text} ОК* участнику *{selected_user_name}* по причине: _\"{reason}\"_"
        confirm_request_message = await request_message.reply_text(text=reply_text, reply_markup=self.confirm_request_reply_markup, parse_mode=ParseMode.MARKDOWN)

        logger.info(f"Confirm request message was sent (message_id={confirm_request_message.message_id})")

        try:
            confirm_request_session_data = {
                "requesting_user": requesting_user,
                "request_message": request_message,
                "request_type": request_type,
                "reason": reason,
                "selected_user_id": selected_user_id,
                "confirm_request_message": confirm_request_message
            }

            confirm_request_session_id = self.session_manager.create_session(
                id=confirm_request_message.message_id,
                type=SessionType.CONFIRM_REQUEST,
                user=selecting_user,
                expired_callback=self._confirm_request_expired_callback,
                data=confirm_request_session_data
            )

            logger.info(f"Session was created (session_id={confirm_request_session_id}, session_type=SessionType.CONFIRM_REQUEST)")
        except Exception as err:
            logger.error(f"Error creating a session for user (user_id={selecting_user.id}, session_type=SessionType.CONFIRM_REQUEST): {err}")
            logger.warning(f"Confirm request message will be deleted (message_id={confirm_request_message.message_id})")

            await confirm_request_message.delete()

            reply_text = f"\uE252 _Команда не может быть выполнена_"
            await request_message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)

    @restrict_public_access()
    async def confirm_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Update received: {update}")

        confirm_request_message = update.callback_query.message

        try:
            confirm_request_session = self.session_manager.get_session(confirm_request_message.message_id)
        except Exception as err:
            logger.error(f"Error getting session (session_id={confirm_request_message.message_id}): {err}")
            logger.warning(f"Confirm request message will be deleted: {confirm_request_message}")

            await confirm_request_message.delete()

            reply_text=f"\uE252 _Запрос более не актуален_"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=reply_text, parse_mode=ParseMode.MARKDOWN)
            return

        request_message = confirm_request_session["data"]["request_message"]
        request_type = confirm_request_session["data"]["request_type"]
        reason = confirm_request_session["data"]["reason"]
        requesting_user = confirm_request_session["data"]["requesting_user"]
        selected_user_id = confirm_request_session["data"]["selected_user_id"]
        
        if self.session_manager.session_is_expired(confirm_request_session):
            logger.warning(f"Session is expired (session_id={confirm_request_session['id']}, session_type=SessionType.CONFIRM_REQUEST)")
            logger.warning(f"Session will be deleted (session_id={confirm_request_session['id']}, session_type=SessionType.CONFIRM_REQUEST)")
            logger.warning(f"Confirm request message will be deleted: {confirm_request_message}")

            self.session_manager.delete_session(confirm_request_session["id"])            
            await confirm_request_message.delete()

            reply_text=f"\uE252 _Запрос более не актуален_"
            await request_message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
            return

        logger.info(f"Found active session (session_id={confirm_request_session['id']}, session_type=SessionType.CONFIRM_REQUEST): {confirm_request_session}")

        confirming_user = update.callback_query["from"]
        confirmed_option = update.callback_query.data

        if requesting_user.id == confirming_user.id and confirmed_option == ConfirmOptions.CONFIRM:
            logger.error(f"Error confirming request: requesting user cannot confirm the request (user_id={confirming_user.id})")

            reply_text=f"\uE252 _Запрос не может быть разрешен инициатором_"
            await confirm_request_message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
            return

        if selected_user_id == confirming_user.id and confirmed_option == ConfirmOptions.CONFIRM:
            logger.error(f"Error confirming request: selected user cannot confirm the request (user_id={confirming_user.id})")

            reply_text=f"\uE252 _Запрос не может быть разрешен кандидатом_"
            await confirm_request_message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
            return

        if selected_user_id == confirming_user.id and confirmed_option == ConfirmOptions.DECLINE:
            logger.error(f"Error confirming request: selected user cannot decline the request (user_id={confirming_user.id})")

            reply_text=f"\uE252 _Запрос не может быть отклонен кандидатом_"
            await confirm_request_message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
            return

        self.session_manager.delete_session(confirm_request_session["id"])
        await confirm_request_message.delete()

        logger.info(f"Session was deleted (session_id={confirm_request_session['id']}, session_type=SessionType.CONFIRM_REQUEST)")
        logger.info(f"Confirm request message was deleted: {confirm_request_message}")
        
        if confirmed_option == ConfirmOptions.CONFIRM:
            logger.info(f"Received option from user (user_id={confirming_user.id}, confirm_option=ConfirmOptions.CONFIRM): {confirm_request_message}")

            try:
                if request_type == RequestType.UP:
                    self.karma_manager.up(selected_user_id, reason)
                else:
                    self.karma_manager.down(selected_user_id, reason)
            except Exception as err:
                logger.error(f"Error updating karma for user (user_id={selected_user_id}, reason={reason}): {err}")

                reply_text = f"\uE252 _Команда не может быть выполнена_"
                await request_message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
                return

            ok_amount_text = '+1' if request_type == RequestType.UP else '-1'
            emoji_text = '\uE232' if request_type == RequestType.UP else '\uE233'
            selected_user_name = self.users_manager.get_user_name(selected_user_id)

            reply_text = f"{emoji_text} Участник *{selected_user_name}* получает *{ok_amount_text} OK* по причине: _\"{reason}\"_"
            await request_message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
            
            request_type_text = "RequestType.UP" if request_type == RequestType.UP else "RequestType.DOWN"
            logger.info(f"Request was done (requesting_user_id={requesting_user.id}, confirming_user_id={confirming_user.id}, selected_user_id={selected_user_id}, request_type={request_type_text}, reason={reason})")
        else:
            logger.info(f"Received option from user (user_id={confirming_user.id}, confirm_option=ConfirmOptions.DECLINE): {confirm_request_message}")

            reply_text="\uE333 _Запрос был отклонен_"
            await request_message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)

    def run(self):
        self.application.run_polling()
