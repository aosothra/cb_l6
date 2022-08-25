import logging

import redis
from environs import Env
from jinja2 import Environment, FileSystemLoader, select_autoescape
from telegram.ext import (
    Updater,
    CallbackQueryHandler,
    MessageHandler,
    CommandHandler,
    Filters,
    PreCheckoutQueryHandler,
)

from moltin_api import SimpleMoltinApiClient
from state_machine import StateMachine
from states import MenuState
from tg_log_handler import TelegramLogHandler


logger = logging.getLogger("pizza_bot")


def on_error(update, context):
    logger.exception("An exception occured while handling an event.")


def main():
    env = Env()
    env.read_env()

    logging.basicConfig(level=logging.ERROR)
    logger.setLevel(logging.DEBUG)
    telegram_handler = TelegramLogHandler(env("ALARM_BOT_TOKEN"), env("ALARM_CHAT_ID"))
    telegram_handler.setLevel(logging.ERROR)
    logger.addHandler(telegram_handler)

    redis_connection = redis.Redis(
        host=env("REDIS_HOST"),
        port=env("REDIS_PORT"),
        password=env("REDIS_PASSWORD"),
    )
    moltin_client = SimpleMoltinApiClient(
        client_id=env("MOLTIN_CLIENT_ID"), client_secret=env("MOLTIN_CLIENT_SECRET")
    )
    jinja_env = Environment(
        loader=FileSystemLoader("./templates/"), autoescape=select_autoescape()
    )

    state_machine = StateMachine(MenuState, redis_connection, moltin_client, jinja_env)

    updater = Updater(env("TELEGRAM_BOT_TOKEN"))
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(state_machine.handle_message))
    dispatcher.add_handler(PreCheckoutQueryHandler(state_machine.handle_message))
    dispatcher.add_handler(MessageHandler(Filters.text, state_machine.handle_message))
    dispatcher.add_handler(
        MessageHandler(
            Filters.successful_payment,
            state_machine.handle_message,
            pass_job_queue=True,
        )
    )
    dispatcher.add_handler(
        MessageHandler(Filters.location, state_machine.handle_message)
    )
    dispatcher.add_handler(CommandHandler("start", state_machine.handle_message))
    dispatcher.add_error_handler(on_error)
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
