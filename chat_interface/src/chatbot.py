import redis
import requests


def get_chatbot_response(message: str, conversation_id: str) -> str:
    """Sends user message to chatbot and returns response."""

    url = "http://localhost:5005/webhooks/rest/webhook"
    body = {"sender": conversation_id, "message": message}
    response = requests.post(url, json=body)
    return response.json()


def reset_chatbot_conversation(conversation_id: str) -> None:
    """Resets chatbot's conversation state."""

    # Reset rasa history:
    url = f"http://localhost:5005/conversations/{conversation_id}/tracker/events"
    requests.post(url, json={"event": "restart"})

    # Reset conversation database:
    redis_client = redis.StrictRedis(host="localhost", port=6379, db=0)
    redis_client.delete(conversation_id)
