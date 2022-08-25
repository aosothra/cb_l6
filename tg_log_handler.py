import logging

import telegram


class TelegramLogHandler(logging.Handler):
    def __init__(self, bot_token, chat_id):
        super().__init__()
        self.__bot = telegram.Bot(bot_token)
        self.__chat_id = chat_id

    def emit(self, record):
        log_entry = self.format(record)

        self.__bot.send_message(chat_id=self.__chat_id, text=log_entry)
