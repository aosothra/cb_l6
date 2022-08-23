from __future__ import annotations

import pickle
from typing import Type

from jinja2 import Environment
from telegram import Update
from telegram.ext import CallbackContext

from moltin_api import SimpleMoltinApiClient


class State(object):
    def __init__(self):
        pass

    def prepare_state(
        self,
        update: Update,
        context: CallbackContext,
        moltin: SimpleMoltinApiClient,
        jinja: Environment,
    ):
        """Prepare state.
        That is a good place to acquire data and send messages to user

        Args:
            update (Update): update instance of telegram handler that initiated the state transition
            context (CallbackContext): context instance of telegram handler that initiated the state transition
        """
        pass

    def handle_input(
        self, update: Update, context: CallbackContext
    ) -> Type[State] | None:
        """Handle user input.
        All user input for given state is redirected here.

        Args:
            update (Update): update instance of incoming update handler
            context (CallbackContext): context instance of incoming update handler

        Returns:
            Type[State]|None: new state to transition to or None to keep present state
        """
        return None

    def clean_up(self, update: Update, context: CallbackContext):
        """Clean up before state transition.
        Good place to edit/delete state messages or keyboards or get rid of expired context data.

        Args:
            update (Update): _description_
            context (CallbackContext): _description_
        """
        pass


class StateMachine:
    INITIAL_STATE = "INITIAL_STATE"

    def __init__(
        self, initial_state: Type[State], redis_connection, moltin_client, jinja_env
    ):
        self.users_state = dict()
        self.__initial_state = initial_state
        self.__redis = redis_connection
        self.__moltin_client = moltin_client
        self.__jinja = jinja_env

    def handle_message(self, update: Update, context: CallbackContext):
        chat_id = (
            update.effective_chat.id
            if update.effective_chat
            else update.pre_checkout_query.from_user.id
        )

        # Reset state to initial upon /start command regardless of current state
        if update.message and update.message.text == "/start":
            print("Set initial state for user")
            self.users_state[chat_id] = self.__initial_state()
            self.users_state[chat_id].prepare_state(
                update, context, self.__moltin_client, self.__jinja
            )
            return

        # Try to retrieve user state from persistent redis storage
        if self.users_state.get(chat_id, None) is None and self.__redis.exists(chat_id):
            self.users_state[chat_id] = pickle.loads(self.__redis.get(chat_id))
            print(
                f"Loaded {type(self.users_state[chat_id]).__name__} for user {chat_id} from persistent storage"
            )

        if not (
            new_state := self.users_state[chat_id].handle_input(
                update, context, self.__moltin_client, self.__jinja
            )
        ):
            print("No valid input from user")
            # User input didn't cause state transition
            return

        if new_state == StateMachine.INITIAL_STATE:
            new_state = self.__initial_state()

        # Clean up previous state
        self.users_state[chat_id].clean_up(update, context)

        # Set, prepare and save new state message
        print(f"Switching {chat_id} to {type(new_state).__name__}")
        self.users_state[chat_id] = new_state
        self.users_state[chat_id].prepare_state(
            update, context, self.__moltin_client, self.__jinja
        )
        self.__redis.set(chat_id, pickle.dumps(self.users_state[chat_id]))
