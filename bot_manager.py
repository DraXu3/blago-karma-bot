from functools import wraps
from telegram import Update, MessageEntity, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import filters, ApplicationBuilder, ContextTypes
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.constants import ParseMode
from time import time
import asyncio
import logging

# def command_handler(command, handlerType = CommandHandler):
#     def wrapper(func):
#         @wraps(func)
#         def decorator(self):
#             handler = handlerType(command, func)
#             self.application.add_handler(handler)
#         return decorator
#     return wrapper

class BotManager:
    def __init__(self, token, vote_manager, session_manager):
        self.application = ApplicationBuilder().token(token).build()
        self.vote_manager = vote_manager
        self.session_manager = session_manager

        self.confirm_reply_markup = self._build_reply_markup({
            'yes': 'Разрешить',
            'no': 'Отклонить'
        })

        start_handler = CommandHandler('help', self.help)
        self.application.add_handler(start_handler)
        
        up_handler = CommandHandler('up', self._create_vote_command('up'))
        self.application.add_handler(up_handler)

        down_handler = CommandHandler('down', self._create_vote_command('down'))
        self.application.add_handler(down_handler)

        show_handler = CommandHandler('show', self.show)
        self.application.add_handler(show_handler)

        unknown_handler = MessageHandler(filters.COMMAND, self.unknown)
        self.application.add_handler(unknown_handler)

        confirm_callback_query_handler = CallbackQueryHandler(self.confirm_callback_query)
        self.application.add_handler(confirm_callback_query_handler)

    def _get_user_markup(self, user):
        return f"[{user.first_name} {user.last_name}](tg://user?id={user.id})"

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

     # @command_handler('up')
    def _create_vote_command(self, vote_type):
        async def vote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            mention_entity = None if len(update.message.entities) < 2 else update.message.entities[1]
            if not mention_entity or mention_entity.type != MessageEntity.TEXT_MENTION:
                await update.message.reply_text(text="\uE252 _Команда не содержит упоминания участника_", parse_mode=ParseMode.MARKDOWN)
                return

            reason = update.message.text[mention_entity.offset+mention_entity.length:].strip()

            mentioned_user = mention_entity.user
            requesting_user = update.message['from']

            ok_amount = '+1' if vote_type == 'up' else '-1'
            reply_text = f"\U0001F4AC Участник {self._get_user_markup(requesting_user)} реквестает *{ok_amount} ОК* участнику {self._get_user_markup(mentioned_user)} по причине: _\"{reason}\"_"
            message = await update.message.reply_text(text=reply_text, reply_markup=self.confirm_reply_markup, parse_mode=ParseMode.MARKDOWN)

            async def _on_expired_callback():
                await message.delete()
                await update.message.reply_text(text=f"\uE252 _Запрос более не актуален_", parse_mode=ParseMode.MARKDOWN)

            self.session_manager.create(
                id=message.message_id,
                create_time=time(),
                command_message=update.message,
                requesting_user=requesting_user,
                voted_user=mentioned_user,
                vote_type=vote_type,
                vote_reason=reason,
                on_expired=_on_expired_callback
            )
                
        return vote_command

    # @command_handler('help')
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        reply_text="\U0001F921 Я *Карма Бот*, я манипулирую кармой\n\n" \
            + "Поддерживаются следующие команды:\n\n" \
            + "  - `/help`: вывести эту справку\n\n" \
            + "  - `/up @user_mention <reason>`: запрос на *+1 ОК* пользователю `\"@user_mention\"` по причине `\"<reason>\"`\n\n" \
            + "  - `/down @user_mention <reason>`: запрос на *-1 ОК* пользователю `\"@user_mention\"` по причине `\"<reason>\"`\n\n" \
            + "  - `/show [@user_mention]`: вывести количество ОК пользователя `\"@user_mention\"` (или для всех пользователей, если параметр не задан)"

        await update.message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
        
    # @command_handler('show')
    async def show(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        mention_entity = None if len(update.message.entities) < 2 else update.message.entities[1]
        mentioned_user = None
        if mention_entity and mention_entity.type == MessageEntity.TEXT_MENTION:
            mentioned_user = mention_entity.user

        # show info for specific user only
        if mentioned_user:
            try:
                total = self.vote_manager.get_total_value(mentioned_user.id)
            except Exception as err:
                logging.error(err)
                reply_text=f"\uE252 _Упомянутого участника нет в базе данных_"
                await update.message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
            else:
                reply_text=f"\U0001F50E Участник {self._get_user_markup(mentioned_user)} имеет *{total} OK*"
                await update.message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
        
        # show info for all users
        else:
            total = self.vote_manager.get_total_values()
            total = sorted(list(total.items()), key=lambda item: item[1], reverse=True)

            users = await asyncio.gather(*[update.message.chat.get_member(record[0]) for record in total])

            reply_text = "\uE131 Текущий рейтинг участников:\n\n"
            for (index, record) in enumerate(total):
                amount, user = record[1], users[index]["user"]
                reply_text += f"  {index + 1}. {self._get_user_markup(user)}: *{amount} OK*\n"                
            await update.message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)

    # @command_handler(filters.COMMAND, MessageHandler)
    async def unknown(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        reply_text="\uE252 _Неизвестная команда, наберите /help для помощи_"
        await update.message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)

    async def confirm_callback_query(self, update, context):
        session = self.session_manager.get(update.callback_query.message.message_id)

        if not session or time() > session["expired"]:
            await update.callback_query.message.delete()

            reply_text=f"\uE252 _Запрос более не актуален_"
            await session["command_message"].reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)

            return

        choice = update.callback_query.data

        if session["requesting_user"].id == update.callback_query['from'].id and choice == 'yes':
            reply_text=f"\uE252 _Запрос не может быть разрешен инициатором_"
            await update.callback_query.message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
            return

        if session["voted_user"].id == update.callback_query['from'].id and choice == 'no':
            reply_text=f"\uE252 _Запрос не может быть отклонен кандидатом_"
            await update.callback_query.message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
            return
        
        if choice == 'yes':
            amount_text = '+1' if session["vote_type"] == 'up' else '-1'
            emoji_text = '\uE232' if session["vote_type"] == 'up' else '\uE233'
            reply_text = f"{emoji_text} Юзер {self._get_user_markup(session['voted_user'])} получает *{amount_text} OK* по причине: _\"{session['vote_reason']}\"_"
            await session["command_message"].reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)
            
            # if session["vote_type"] == 'up':
            #     self.vote_manager.up(session["voted_user"].id, session["vote_reason"])
            # else:
            #     self.vote_manager.down(session["voted_user"].id, session["vote_reason"])
        else:
            reply_text="\uE333 _Реквест был отклонен_"
            await session["command_message"].reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN)

        await update.callback_query.message.delete()
        self.session_manager.delete(update.callback_query.message.message_id)

    def run(self):
        self.application.run_polling()
