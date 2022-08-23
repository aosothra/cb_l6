import os
import requests
from geopy import distance
from jinja2 import Environment
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import PARSEMODE_HTML
from telegram.ext import CallbackContext

from moltin_api import SimpleMoltinApiClient
from state_machine import State, StateMachine


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def fetch_coordinates(apikey, address):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(
        base_url,
        params={
            "geocode": address,
            "apikey": apikey,
            "format": "json",
        },
    )
    response.raise_for_status()
    found_places = response.json()["response"]["GeoObjectCollection"]["featureMember"]

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant["GeoObject"]["Point"]["pos"].split(" ")
    return lon, lat


class MenuState(State):
    def __init__(self, menu_page=None):
        self.__page = menu_page if menu_page else 0

    def prepare_state(
        self,
        update: Update,
        context: CallbackContext,
        moltin: SimpleMoltinApiClient,
        jinja: Environment,
    ):
        self.__chat_id = update.effective_chat.id
        products = moltin.get_products()
        cart_items, total_price = moltin.get_cart_and_full_price(self.__chat_id)
        cart_items_mapped = {
            item["product_id"]: item["quantity"] for item in cart_items
        }

        inline_keyboard = []
        for product_name, product_id in products.items():
            button_label = (
                f"{product_name} (x{cart_items_mapped.get(product_id)})"
                if cart_items_mapped.get(product_id, None) is not None
                else product_name
            )
            inline_keyboard.append(
                InlineKeyboardButton(button_label, callback_data=product_id)
            )

        per_page = 8

        if len(inline_keyboard) > per_page:
            navigation_row = []
            if self.__page > 0:
                navigation_row.append(
                    InlineKeyboardButton("< < <", callback_data="prev_page")
                )
            if len(inline_keyboard) > self.__page * per_page + per_page:
                navigation_row.append(
                    InlineKeyboardButton("> > >", callback_data="next_page")
                )
            inline_keyboard = list(
                chunks(
                    inline_keyboard[
                        self.__page * per_page : self.__page * per_page + per_page
                    ],
                    2,
                )
            )
            if navigation_row:
                inline_keyboard.append(navigation_row)
        else:
            inline_keyboard = list(chunks(inline_keyboard, 1))

        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    f"Корзина ({total_price})" if cart_items else "Корзина (пусто)",
                    callback_data="cart",
                ),
                InlineKeyboardButton("Оформить заказ", callback_data="order"),
            ]
        )

        message_template = jinja.get_template("menu_message.html")

        self.__message_id = context.bot.send_message(
            chat_id=self.__chat_id,
            text=message_template.render(),
            parse_mode=PARSEMODE_HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard),
        ).message_id

    def handle_input(
        self,
        update: Update,
        context: CallbackContext,
        moltin: SimpleMoltinApiClient,
        jinja: Environment,
    ):
        if not update.callback_query:
            return None

        user_input = update.callback_query.data
        update.callback_query.answer()

        if user_input == "cart":
            return CartState()
        if user_input == "order":
            return DeliveryState()
        if user_input == "next_page":
            return MenuState(menu_page=self.__page + 1)
        if user_input == "prev_page":
            return MenuState(menu_page=self.__page - 1)
        return PizzaDescriptionState(user_input)

    def clean_up(self, update: Update, context: CallbackContext):
        context.bot.delete_message(chat_id=self.__chat_id, message_id=self.__message_id)


class PizzaDescriptionState(State):
    def __init__(self, product_id):
        self.__product_id = product_id

    def prepare_state(
        self,
        update: Update,
        context: CallbackContext,
        moltin: SimpleMoltinApiClient,
        jinja: Environment,
    ):
        self.__chat_id = update.effective_chat.id
        product = moltin.get_product_by_id(self.__product_id)
        image_url = moltin.get_image_url_by_file_id(
            product["relationships"]["main_image"]["data"]["id"]
        )

        self.__product_name = product["name"]

        inline_keyboard = [
            [
                InlineKeyboardButton("Добавить в корзину", callback_data="add_to_cart"),
                InlineKeyboardButton("Вернуться в меню", callback_data="menu"),
            ]
        ]

        message_template = jinja.get_template("product_details_message.html")

        self.__message_id = context.bot.send_photo(
            chat_id=self.__chat_id,
            photo=image_url,
            caption=message_template.render(product=product),
            parse_mode=PARSEMODE_HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard),
        ).message_id

    def handle_input(
        self,
        update: Update,
        context: CallbackContext,
        moltin: SimpleMoltinApiClient,
        jinja: Environment,
    ):
        if not update.callback_query:
            return None

        user_input = update.callback_query.data

        if user_input == "menu":
            update.callback_query.answer()
            return StateMachine.INITIAL_STATE
        if user_input == "add_to_cart":
            moltin.add_product_to_cart(self.__chat_id, self.__product_id, 1)
            update.callback_query.answer(text="Товар добавлен в корзину")
            return StateMachine.INITIAL_STATE

    def clean_up(self, update: Update, context: CallbackContext):
        context.bot.edit_message_reply_markup(
            chat_id=self.__chat_id, message_id=self.__message_id
        )


class CartState(State):
    def prepare_state(
        self,
        update: Update,
        context: CallbackContext,
        moltin: SimpleMoltinApiClient,
        jinja: Environment,
    ):
        self.__chat_id = update.effective_chat.id
        cart_items, total_price = moltin.get_cart_and_full_price(self.__chat_id)
        inline_keyboard = [
            InlineKeyboardButton(f"Убрать \"{item['name']}\"", callback_data=item["id"])
            for item in cart_items
        ]
        inline_keyboard = list(chunks(inline_keyboard, 2))
        inline_keyboard.append(
            [
                InlineKeyboardButton("Оформить заказ", callback_data="order"),
                InlineKeyboardButton("Вернуться в меню", callback_data="menu"),
            ]
        )

        message_template = jinja.get_template("cart_message.html")

        self.__message_id = context.bot.send_message(
            chat_id=self.__chat_id,
            text=message_template.render(
                cart_items=cart_items, total_price=total_price
            ),
            parse_mode=PARSEMODE_HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard),
        ).message_id

    def handle_input(
        self,
        update: Update,
        context: CallbackContext,
        moltin: SimpleMoltinApiClient,
        jinja: Environment,
    ):
        if not update.callback_query:
            return None
        user_input = update.callback_query.data

        if user_input == "order":
            update.callback_query.answer()
            return DeliveryState()
        if user_input == "menu":
            update.callback_query.answer()
            return StateMachine.INITIAL_STATE
        update.callback_query.answer(text="Корзина обновлена")
        moltin.remove_product_from_cart(self.__chat_id, user_input)
        return CartState()

    def clean_up(self, update: Update, context: CallbackContext):
        context.bot.delete_message(chat_id=self.__chat_id, message_id=self.__message_id)


class DeliveryState(State):
    def prepare_state(
        self,
        update: Update,
        context: CallbackContext,
        moltin: SimpleMoltinApiClient,
        jinja: Environment,
    ):
        self.__chat_id = update.effective_chat.id

        message_template = jinja.get_template("arrange_delivery_message.html")

        context.bot.send_message(
            chat_id=self.__chat_id,
            text=message_template.render(),
            parse_mode=PARSEMODE_HTML,
        )

    def handle_input(
        self,
        update: Update,
        context: CallbackContext,
        moltin: SimpleMoltinApiClient,
        jinja: Environment,
    ):
        if not update.message:
            return None

        if update.message.location:
            user_input = update.message.location
            return ConfirmAddressState(user_input.longitude, user_input.latitude)
        if not update.message.text:
            return None

        user_input = update.message.text
        coords = fetch_coordinates(os.getenv("YANDEX_GEOCODER_API"), user_input)

        if not coords:
            context.bot.send_message(
                chat_id=self.__chat_id,
                text="Не получилось распознать адрес. Пожалуйста, попробуйте еще раз",
                parse_mode=PARSEMODE_HTML,
            )
            return None
        return ConfirmAddressState(*coords)


class ConfirmAddressState(State):
    def __init__(self, lon, lat):
        self.__lon = lon
        self.__lat = lat

    def __get_distance_to_restaurant(self, restaurant):
        return distance.distance(
            (self.__lon, self.__lat),
            (restaurant["restaurant-lon"], restaurant["restaurant-lat"]),
        )

    def prepare_state(
        self,
        update: Update,
        context: CallbackContext,
        moltin: SimpleMoltinApiClient,
        jinja: Environment,
    ):
        self.__chat_id = update.effective_chat.id
        restaurants = moltin.get_flow_entries(flow_slug="restaurant")
        closest_restaurant = min(restaurants, key=self.__get_distance_to_restaurant)
        distance = self.__get_distance_to_restaurant(closest_restaurant).km
        self.__delivery_price = 0 if distance <= 0.5 else 100 if distance <= 5 else 300

        delivery_options_row = [
            InlineKeyboardButton("Самовывоз", callback_data="pick_up")
        ]
        if distance <= 20:
            delivery_options_row.append(
                InlineKeyboardButton(
                    f"Заказать доставку ( +{self.__delivery_price}р. )",
                    callback_data="request_delivery",
                )
            )
        inline_keyboard = [
            delivery_options_row,
            [
                InlineKeyboardButton(
                    "Изменить адрес доставки", callback_data="change_address"
                ),
                InlineKeyboardButton("Вернуться в меню", callback_data="menu"),
            ],
        ]

        message_template = jinja.get_template("confirm_delivery_message.html")

        self.__message_id = context.bot.send_message(
            chat_id=self.__chat_id,
            text=message_template.render(
                address=closest_restaurant["restaurant-address"], distance=distance
            ),
            parse_mode=PARSEMODE_HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard),
        ).message_id

    def handle_input(
        self,
        update: Update,
        context: CallbackContext,
        moltin: SimpleMoltinApiClient,
        jinja: Environment,
    ):
        if not update.callback_query:
            return None

        update.callback_query.answer()
        user_input = update.callback_query.data
        if user_input == "menu":
            return StateMachine.INITIAL_STATE
        if user_input == "change_address":
            return DeliveryState()

    def clean_up(self, update: Update, context: CallbackContext):
        context.bot.edit_message_reply_markup(
            chat_id=self.__chat_id, message_id=self.__message_id
        )
