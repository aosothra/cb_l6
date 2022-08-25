# cb_l5 - Pizza Delivery Bot

This project implements a simple telegram commerce bot ([Telegram](https://t.me/pizza_place_45672231_bot)) for selling pizza.

## Installation and Environment setup

You must have Python3 installed on your system.

You may use `pip` (or `pip3` to avoid conflict with Python2) to install dependencies.
```
pip install -r requirements.txt
```
It is strongly advised to use [virtualenv/venv](https://docs.python.org/3/library/venv.html) for project isolation.

Use `store_management.py` script in order to prepare and populate your **Elasticpath** store.

```sh
python3 store_management.py <client_id> <client_secret>
```

Opt for `-h` flag to see what other utilities it provides.

Telegram bot uses `.env` file in root folder to store variables necessary for operation. So, do not forget to create one!

Inside your `.env` file you can specify following settings:

| Key | Type | Description |
| - | - | - |
| `CLIENT_ID` | `str` | Your Client id API KEY for [Elasticpath](https://www.elasticpath.com/) e-commerce platform
| `CLIENT_SECRET` | `str` | Your Client Secret API KEY for [Elasticpath](https://www.elasticpath.com/) e-commerce platform
| `TELEGRAM_BOT_TOKEN` | `str` | Your Telegram bot API token to handle conversations in Telegram.
| `TELEGRAM_PAYMENT_TOKEN` | `str` | Your Telegram payment provider token. Learn [here](https://core.telegram.org/bots/payments)
| `YANDEX_GEOCODER_API` | `str` | Access token of Yandex Geocoder API. Learn [here](https://yandex.ru/dev/maps/geocoder/)
| `REDIS_HOST` | `str` | Host address of your Redis database server.
| `REDIS_PORT` | `int` | Port number of your Redis database server.
| `REDIS_PASSWORD` | `str` | Password for auth purposes for your Redis database.
| `ALARM_BOT_TOKEN` | `str` | Your Telegram bot API token to report errors.
| `ALARM_CHAT_ID` | `str` | Your Telegram chat id to send error messages to.

If you do not know how to acquire Telegram Bot token, you can follow official guidelines [here](https://core.telegram.org/bots#3-how-do-i-create-a-bot).

Present implementation of the bots partially rely on Redis database for user data persistence. So you will have to set up one.
The easiest way is to register free plan on [Redis Enterprise](https://redis.com/try-free/) cloud platform. Once registered, use host address, port and default user password provided for `REDIS_HOST`, `REDIS_PORT` and `REDIS_PASSWORD`.

  
## Basic usage

Use `tg_bot.py` to start Telegram bot:

```
py tg_bot.py 
```

## Project goals

This project was created for educational purposes as part of [dvmn.org](https://dvmn.org/) Backend Developer course.