import json

import redis


class Database:
    """Class that handles the interaction with the database."""

    _redis = redis.Redis(host="localhost", port=6379, decode_responses=True)

    @staticmethod
    def set_data(user_id: str, data: dict) -> None:
        """
        Sets the user's cart.

        Args:

        user_id: The user's id.
        data: The user's data.
        """
        data = json.dumps(data)
        Database._redis.set(user_id, data)

    @staticmethod
    def get_data(user_id: str) -> dict:
        """
        Gets the user's cart.

        Args:

        user_id: The user's ID.

        Returns:

        User's data stored in the database. If the user has no data, returns an empty dict.
        """
        data_stringified = Database._redis.get(user_id)
        if data_stringified is None:
            return {}
        data = json.loads(data_stringified)
        return data
