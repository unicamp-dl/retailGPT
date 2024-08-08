# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions

import os
import sys
import unicodedata
from typing import Any, Dict, List, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.events import ActiveLoop, FollowupAction, SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from rasa_sdk.types import DomainDict

current_directory = os.path.dirname(os.path.realpath(__file__))
sys.path.append(current_directory)

from LLMChatbot.chatbot import LLMChatbot
from LLMChatbot.services.cart_handler import CartHandler


class CartStatus(Action):
    """Action that returns the user's cart summary."""

    def name(self) -> Text:
        return "return_cart_status"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        cart = CartHandler.get_cart_summary(tracker.sender_id)
        dispatcher.utter_message(text=cart)

        return [FollowupAction("action_listen")]


class ValidateZipcodeForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_zipcode_form"

    def validate_zipcode(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate the user's input for the zipcode. If the input is invalid, ask the user to answer again."""

        payment_method = tracker.get_slot("payment_method")
        zipcode = slot_value
        zipcode = [c for c in zipcode if c.isdigit()]
        if len(zipcode) != 8 and len(zipcode) != 5:
            dispatcher.utter_message(text="Invalid or incomplete ZIP code. Use the Brazilian 8-digit format (CEP) or the American 5-digit format.")
            return {"zipcode": None}

        if payment_method is None:
            if zipcode[0] == "0":
                dispatcher.utter_message(
                    text="We don't have any products available for ZIP codes that start with '0', please try another."
                )
                return {"zipcode": None}

            elif zipcode[0] == "9":
                dispatcher.utter_message(
                    text="We have a limited catalog for ZIP codes that start with '9'."
                )

        return {"zipcode": "".join(zipcode)}

    def validate_legal_age(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate if the user is of legal age.
        If not, ask the user to answer again."""

        if slot_value:
            return {"legal_age": True}
        else:
            dispatcher.utter_message(
                text=(
                    "You need to be of legal age to use the service."
                    " If you mistakenly responded that you are under legal age,"
                    " please respond again."
                )
            )
            return {"legal_age": None}


def return_responses(messages: list[dict], dispatcher: CollectingDispatcher) -> None:
    """
    Formats and dispatches the responses to the user.

    Args:

    messages: A list of dictionaries containing the responses and buttons to be dispatched.
    dispatcher: The dispatcher object used to send messages to the user.
    """

    for message in messages:
        if "text" in message:
            try:
                dispatcher.utter_message(text=message["text"])
            except Exception as e:
                print(f"Dispatcher error: {e}")
        if "buttons" in message:
            try:
                dispatcher.utter_message(buttons=message["buttons"])
            except Exception as e:
                print(f"Dispatcher error: {e}")


class ProcessCachedUserDemands(Action):
    def name(self) -> Text:
        return "process_cached_user_demands"

    async def run(
        self,
        dispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        user_id = tracker.sender_id
        zipcode = tracker.get_slot("zipcode")

        try:
            responses = await LLMChatbot.get_response_from_cache(user_id, zipcode)
            if responses is None:
                zipcode_submitted_message = domain["responses"]["utter_submit_zipcode"][
                    0
                ]["text"]
                dispatcher.utter_message(text=zipcode_submitted_message)
            else:
                return_responses(responses, dispatcher)
        except Exception as e:
            raise (e)
            print(f"Error generating responses from cache: {e}")
        return [FollowupAction("action_listen")]


class LLMProcessing(Action):
    """Processes the user's message and returns a response, using a LLM-based approach."""

    def name(self) -> Text:
        return "llm_processing"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        zipcode = tracker.get_slot("zipcode")
        is_legal_age = tracker.get_slot("legal_age")
        message = tracker.latest_message.get("text")
        user_id = tracker.sender_id

        # Checks if we are still before starting the initial form:
        if tracker.active_loop is None and is_legal_age is None:
            greeting = domain["responses"]["utter_ask_legal_age"][0]["text"]
            dispatcher.utter_message(text=greeting)

        responses = await LLMChatbot.get_response(
            user_id, zipcode, message, is_legal_age
        )

        return_responses(responses, dispatcher)

        if zipcode is None or is_legal_age is None:
            return [FollowupAction("zipcode_form"), ActiveLoop("zipcode_form")]
        if CartHandler.get_should_finish_purchase(user_id):
            CartHandler.set_should_finish_purchase(user_id, False)
            return [
                FollowupAction("payment_method_form"),
                ActiveLoop("payment_method_form"),
            ]
        return [FollowupAction("action_listen")]


class ActionDefaultFallback(Action):
    def name(self) -> Text:
        return "action_default_fallback"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        form = tracker.active_loop.get("name")

        zipcode = tracker.get_slot("zipcode")

        if zipcode is None:
            return [FollowupAction("zipcode_form"), ActiveLoop("zipcode_form")]

        if form is not None:
            return [FollowupAction(form), ActiveLoop(form)]

        dispatcher.utter_message(response="utter_default")

        return [FollowupAction("action_listen")]


def normalize_string(string: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFD", string)
        if unicodedata.category(c) != "Mn"
    ).lower()


def valid_methods() -> List[str]:
    return [normalize_string(x) for x in ["Cash", "Credit", "Debit"]]


class ValidatePaymentForm(FormValidationAction):
    def name(self) -> str:
        return "validate_payment_method_form"

    def validate_payment_method(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate payment_method value."""
        original_string = slot_value
        slot_value = normalize_string(slot_value)
        if slot_value in valid_methods():
            return {"payment_method": original_string}
        else:
            dispatcher.utter_message(response="utter_ask_payment_method")
            return {"payment_method": None}


def valid_details() -> List[str]:
    return ["zipcode", "payment_method", "ok", "cart"]


class ValidateConfirmationForm(FormValidationAction):
    def name(self):
        return "validate_confirmation_form"

    def validate_modify_details(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:

        if slot_value in valid_details():
            return {"modify_details": slot_value}
        else:
            return {"modify_details": None}


class ActionSummarizeDetails(Action):
    def name(self) -> str:
        return "summarize_details"

    async def run(self, dispatcher, tracker, domain):
        # Retrieve slot values
        zipcode = tracker.get_slot("zipcode")
        payment_method = tracker.get_slot("payment_method")
        cart = CartHandler.get_cart_summary(tracker.sender_id)

        # Create a summary message
        message = (
            "Finally, please confirm your purchase details:\n"
            f"ZIP code: {zipcode}\n"
            f"Payment method: {payment_method}.\n"
            f"{cart}"
        )

        dispatcher.utter_message(text=message)

        return []


class CorrectDetail(Action):
    def name(self) -> Text:
        return "correct_detail"

    async def run(
        self,
        dispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        detail_to_correct = tracker.get_slot("modify_details")
        if detail_to_correct == "ok":
            dispatcher.utter_message(
                text="Noted! 📝 Now just wait for your order to arrive at your home! Our conversation ends here, if you want to place another order, restart the bot."
            )
            return []
        elif detail_to_correct == "cart":
            dispatcher.utter_message(
                text="Okay, now just continue building your cart. What do you want?"
            )
            return [SlotSet("modify_details", None), FollowupAction("action_listen")]
        elif detail_to_correct is not None:
            return [
                SlotSet("modify_details", None),
                SlotSet(detail_to_correct, None),
                FollowupAction(name=f"{detail_to_correct}_form"),
                ActiveLoop(f"{detail_to_correct}_form"),
            ]
        dispatcher.utter_message(
            text="Sorry, I didn't understand what you want to correct. Could you repeat?"
        )
        return []
