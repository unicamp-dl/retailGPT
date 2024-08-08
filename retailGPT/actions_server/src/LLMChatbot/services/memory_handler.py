from typing import List
import json

from openai.types.chat import ChatCompletionMessageToolCall

from .database import Database

class MemoryHandler:
    """Class that handles the interaction with the user's memory."""

    _history_length: int = 6  # Number of messages to keep in the history

    @staticmethod
    def get_history(user_id: str) -> List:
        """
        Gets the user's message history.

        Args:

        user_id: The user's ID.

        Returns:

        List of messages representing the user's message history.
        """
        user_data = Database.get_data(user_id)
        if "history" in user_data:
            messages = [message for message in user_data["history"]]
        else:
            messages = []

        return messages

    @staticmethod
    def _set_history(user_id: str, history: List) -> None:
        """
        Sets the user's message history.

        Args:

        user_id: The user's ID.
        history: The user's message history.
        """
        user_data = Database.get_data(user_id)
        user_data["history"] = history
        Database.set_data(user_id, user_data)

    @staticmethod
    def add_message_to_history(user_id: str, message: dict) -> None:
        """
        Adds a message to the user's message history.

        Args:

        user_id: The user's ID.
        message: The message to add to the history.
        """
        history = MemoryHandler.get_history(user_id)
        history.append(message)
        MemoryHandler._set_history(user_id, history[-MemoryHandler._history_length :])

    @staticmethod
    def add_cached_tool_calls(user_id: str, tool_calls: list[ChatCompletionMessageToolCall]):
        """
        Adds generated tool calls to the user's cache

        Args:

        user_id: The user's ID
        tool_calls: list of tool calls to be added to the cache
        """
        user_data = Database.get_data(user_id)
        tool_calls = [tool_call.model_dump_json() for tool_call in tool_calls]
        if "tool_calls" in user_data:
            user_data["tool_calls"].extend(tool_calls)
        else:
            user_data["tool_calls"] = tool_calls

        print("Data added to cache: ", tool_calls)

        Database.set_data(user_id, user_data)

    @staticmethod
    def get_cached_tool_calls(user_id: str) -> list[ChatCompletionMessageToolCall]:
        """
        Gets user's cached tool calls

        Args:

        user_id: The user's ID

        Returns:

        List of cached tool calls 
        """
        user_data = Database.get_data(user_id)
        if "tool_calls" in user_data:
            tool_calls = [ChatCompletionMessageToolCall.model_validate_json(tool_call) for tool_call in user_data["tool_calls"]]
        else:
            tool_calls = []

        return tool_calls
