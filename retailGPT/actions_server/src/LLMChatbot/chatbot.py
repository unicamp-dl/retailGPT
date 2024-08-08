import asyncio
import json
import os
import sys

import aiohttp
from colorama import Fore
from openai.types.chat import ChatCompletionMessageToolCall

current_directory = os.path.dirname(os.path.realpath(__file__))
sys.path.append(current_directory)

from .prompts import chatbot_prompt_tools, chatbot_system_prompt
from .schemas import ChatbotResponse
from .services.cart_handler import CartHandler
from .services.llm_handler import LLMHandler
from .services.memory_handler import MemoryHandler
from .services.product_handler import ProductHandler
from .services.guardrails.guardrails import Guardrails


class LLMChatbot:
    """Handles the chatbot logic for the LLM system."""

    _finish_purchase_function_message: str = (
        "The cart has been saved, and we will proceed to the selection of the desired payment method. Just inform this to the user."
    )
    _cache_warning_cep: str = (
        "Your request has been noted, and I will proceed with it as soon as you provide your postal code."
    )
    _cache_warning_cep_age: str = (
        "Your request has been noted, and I will proceed with it as soon as you confirm that you are of legal age and provide your postal code."
    )
    _guardrails_warning: str = (
        "Your message violates the system's usage rules. Please avoid sending inappropriate messages."
    )
    _competing_brands_warning: str = (
        "Your message contains a mention of brands we do not work with."
    )
    _early_operation_warning: str = (
        "Operation not performed. It is necessary to first confirm the desired product from those available in the catalog. Therefore, before editing the cart, confirm with the user if the desired product is among the results in the catalog below:\n"
    )

    @staticmethod
    async def _search_product_recommendation(
        user_id: str,
        product_query: str,
        location_cep: str,
        session: aiohttp.ClientSession | None = None,
    ) -> str:
        """Searches for a product recommendation based on the user's demand.

        Args:

        session: The aiohttp session for concurrent searching.
        user_id: The user's ID.
        product_query: The user's demand for a product, e.g. 'Uma cerveja leve'.
        location_cep: The user's CEP.

        Returns:

        The product recommendation based on the user's demand."""

        recommendation = await ProductHandler.get_product_recommendation(
            user_id, product_query, location_cep, session
        )

        return recommendation

    @staticmethod
    def _edit_cart(user_id: str, operation: str, product: str, amount: str) -> str:
        """Edits the user's cart based on the operation, product and amount.

        Args:

        operation: The operation to be performed on the cart, can be 'add' or 'remove'.
        product: The product to be added or removed from the cart.
        amount: The amount of the product to be added or removed from the cart.

        Returns:

        Summary of the operation result and the current state of the cart.
        """

        function_output = CartHandler.process_cart_operation(
            user_id, operation, product, amount
        )
        return function_output

    @staticmethod
    def _tool_call_sorting(tool_call: ChatCompletionMessageToolCall) -> int:
        """Sorts the tool calls prioritizing removal operations.

        Args:

        tool_call: The tool call to be sorted.

        Returns:

        The sorting key.
        """

        function_arguments = json.loads(tool_call.function.arguments)
        if (
            tool_call.function.name == "edit_cart"
            and function_arguments["operation"] == "remove"
        ):
            return 0
        return 1

    @staticmethod
    async def _process_sequential_tool_calls(
        user_id: str, user_cep: str, tool_calls: list[ChatCompletionMessageToolCall]
    ) -> list[dict]:
        """Processes the tool calls in sequence.

        Args:

        tool_calls: A list of Open Ai's tool calls, containing the function name and arguments.

        Returns:

        A list of messages containing the function calls and their output
        """

        output_messages = []
        # Prioritize removal operations, as the removed products may block the addition of new ones due to the volume limit
        tool_calls.sort(key=LLMChatbot._tool_call_sorting)

        for call in tool_calls:

            call_id = call.id
            function_arguments = json.loads(call.function.arguments)
            if call.function.name == "edit_cart":
                operation = function_arguments["operation"]
                product = function_arguments["product"]
                amount = function_arguments["amount"]

                if (
                    operation == "add"
                    and not ProductHandler.product_was_recommended(user_id, product)
                ):

                    print("Trying to add a product that was not recommended: ", product)

                    function_output = LLMChatbot._early_operation_warning
                    function_output += await LLMChatbot._search_product_recommendation(
                        user_id, product, user_cep
                    )

                else:

                    function_output = LLMChatbot._edit_cart(
                        user_id, operation, product, amount
                    )

                    # Sets the flag to send the cart summary to the user
                    # This is sent from outside the LLM, as avoiding hallucinations is crucial
                    CartHandler.set_should_send_cart_summary(user_id, True)

            else:

                function_output = LLMChatbot._finish_purchase_function_message
                CartHandler.set_should_finish_purchase(user_id, True)

            output_messages.append(
                {"role": "tool", "content": function_output, "tool_call_id": call_id}
            )

        return output_messages

    @staticmethod
    async def _process_tool_calls(
        user_id: str, user_cep: str, tool_calls: list[ChatCompletionMessageToolCall]
    ) -> list[dict]:
        """Processes the tool calls, calling the appropriate fuctions.

        Args:

        tool_calls: A list of Open Ai's tool calls, containing the function name and arguments.

        Returns:

        A list of messages containing the function calls and their output
        """

        search_tool_calls = []
        sequential_tool_calls = []
        tasks = []
        output_messages = []
        call_ids = []

        for tool_call in tool_calls:
            if tool_call.function.name == "search_product_recommendation":
                search_tool_calls.append(tool_call)
            else:
                sequential_tool_calls.append(tool_call)

        async with aiohttp.ClientSession() as session:

            if search_tool_calls:
                for call in search_tool_calls:

                    call_id = call.id
                    function_arguments = json.loads(call.function.arguments)
                    task = asyncio.create_task(
                        LLMChatbot._search_product_recommendation(
                            user_id,
                            function_arguments["product_query"],
                            user_cep,
                            session
                        )
                    )
                    tasks.append(task)
                    call_ids.append(call_id)

                results = await asyncio.gather(*tasks)

                for result, id in zip(results, call_ids):
                    output_messages.append(
                        {"role": "tool", "content": result, "tool_call_id": id}
                    )

        if sequential_tool_calls:
            sequential_calls_output = await LLMChatbot._process_sequential_tool_calls(
                user_id, user_cep, sequential_tool_calls
            )
            output_messages.extend(sequential_calls_output)

        return output_messages

    @staticmethod
    def _build_tool_call_message(tool_calls: list) -> list[dict]:
        """Builds the tool call message.

        Args:

        tool_calls: The tool calls list.

        Returns:

        The tool call message.
        """

        tool_call_message = {
            "role": "assistant",
            "tool_calls": [],
        }
        for tool_call in tool_calls:
            tool_call_message["tool_calls"].append(
                {
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": dict(tool_call.function),
                }
            )
        return tool_call_message

    @staticmethod
    def _response_post_processing(
        user_id: str, final_answer: str
    ) -> list[ChatbotResponse]:
        """Processes the final answer before sending it to the user.

        Args:

        user_id: The user's ID.
        final_answer: The final answer to be sent to the user.

        Returns:

        List containing one or more chatbot's responses to the user's message.
        """

        final_answer_dict = {
            "role": "assistant",
            "content": final_answer,
        }

        MemoryHandler.add_message_to_history(user_id, final_answer_dict)

        # Prints the final answer for debugging purposes
        print(Fore.BLUE + "Final answer: ", final_answer)

        return_responses = []
        # buttons are sent separately after the last return response,
        # so they are rendered after all the text
        buttons = []

        if CartHandler.get_should_send_cart_summary(user_id):

            cart_summary = CartHandler.get_cart_summary(user_id)
            return_responses.append({"text": cart_summary, "buttons": None})
            confirmation_button = {
                "title": "Finish purchase",
                "payload": "/finish_purchase",
            }
            buttons.append(confirmation_button)

            CartHandler.set_should_send_cart_summary(user_id, False)

        return_responses.append({"text": final_answer, "buttons": buttons})

        return return_responses

    def _response_pre_processing(user_id: str, user_message: str) -> list[dict]:
        """Generate the array of messages that will be sent to the completions API.

        Args:

        user_id: The user's ID.
        user_message: The user's message to the chatbot.

        Returns:

        List containing the messages that will be sent to the completions API.
        """

        system_message_dict = {"role": "system", "content": chatbot_system_prompt}
        user_message_dict = {"role": "user", "content": user_message}
        MemoryHandler.add_message_to_history(user_id, user_message_dict)
        history = MemoryHandler.get_history(user_id)
        messages = [system_message_dict] + history

        return messages

    @staticmethod
    async def get_response_from_cache(
        user_id: str, user_cep: str
    ) -> list[ChatbotResponse]:
        """Gets the chatbot's response from the cached tool calls.

        Args:

        user_id: The user's ID.

        Returns:

        List containing one or more chatbot's responses to the user's message.
        """

        tool_calls = MemoryHandler.get_cached_tool_calls(user_id)
        if not tool_calls:
            return None

        print("Running get response from cache")
        print("Cached tool calls ", tool_calls)

        tools_output_messages = await LLMChatbot._process_tool_calls(
            user_id, user_cep, tool_calls
        )
        tool_call_message = LLMChatbot._build_tool_call_message(tool_calls)
        history = MemoryHandler.get_history(user_id)
        history.extend([tool_call_message] + tools_output_messages)

        messages = [{"role": "system", "content": chatbot_system_prompt}] + history
        completion_response = await LLMHandler.call_completions_api(messages)

        final_answer = completion_response["content"]

        return_responses = LLMChatbot._response_post_processing(user_id, final_answer)
        return return_responses

    @staticmethod
    async def get_response(
        user_id: str, user_cep: str | None, user_message: str, is_of_legal_age: bool | None, debug_mode: bool = False
    ) -> list[ChatbotResponse] | dict:
        """Gets the chatbot's response to the user's message.

        Args:

        user_id: The user's ID.
        user_cep: The user's CEP.
        user_message: The user's message to the chatbot.
        is_of_legal_age: Boolean indicating if the user is over legal age.
        debug_mode: When activated, the chatbot will return a dict containing processing data and also the list of responses

        Returns:

        List containing one or more chatbot's responses to the user's message.
        Each response is a dict containing the keys "text" and "buttons".
        """

        # Prints the user message for debugging purposes
        print(Fore.BLUE + "User message: ", Fore.BLUE + user_message)

        # Guardrails checks for the input before processing the message and adding it to the history:
        if not await Guardrails.run_input_guardrails(user_message):
            return [{"text": LLMChatbot._guardrails_warning, "buttons": None}]

        messages = LLMChatbot._response_pre_processing(user_id, user_message)
        tools = chatbot_prompt_tools
        completion_response = await LLMHandler.call_completions_api(messages, tools)

        tool_calls = completion_response.get("tool_calls", None)

        if tool_calls is not None:

            tool_calls = [
                ChatCompletionMessageToolCall(**tool_call) for tool_call in tool_calls
            ]

            if user_cep is None:
                MemoryHandler.add_cached_tool_calls(user_id, tool_calls)
                response = LLMChatbot._cache_warning_cep
                if is_of_legal_age is None:
                    response = LLMChatbot._cache_warning_cep_age
                return LLMChatbot._response_post_processing(user_id, response)

            # Prints the tool calls for debugging purposes
            print(
                Fore.GREEN + "Completion tool calling: ",
                Fore.GREEN + str(completion_response),
            )

            tools_output_messages = await LLMChatbot._process_tool_calls(
                user_id, user_cep, tool_calls
            )

            tool_call_message = LLMChatbot._build_tool_call_message(tool_calls)
            history = MemoryHandler.get_history(user_id)
            history.extend([tool_call_message] + tools_output_messages)

            # Call the completions API without tools, as we want a final response:
            messages = [{"role": "system", "content": chatbot_system_prompt}] + history
            completion_response = await LLMHandler.call_completions_api(messages)

        final_answer = completion_response["content"]

        # Guardrails checks for the output before sending the response or adding it to the history:
        if not Guardrails.run_output_guardrails(user_message):
            return [{"text": LLMChatbot._guardrails_warning, "buttons": None}]

        return_responses = LLMChatbot._response_post_processing(user_id, final_answer)

        if debug_mode:
            return {
                "tool_calls": tool_calls,
                "responses": return_responses,
            }
        
        return return_responses
