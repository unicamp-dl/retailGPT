import os
import re
from openai import OpenAI

from dotenv import load_dotenv

from ...prompts import prompt_hack
from ..llm_handler import LLMHandler
from .words_to_be_filtered import words_to_be_filtered

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", None))

_credit_cards_patterns = {
    "Visa": re.compile(
        r"\b(?<!\-|\.)4(\d{3})(?!\1{3})([\ \-]?)(?<!\d\ \d{4}\ )(?!(\d)\3{3})(\d{4})\2(?!\4|(\d)\5{3}|1234|2345|3456|5678|7890)(\d{4})(?!\ \d{4}\ \d)\2(?!\6|(\d)\7{3}|1234|3456)\d{4}(?!\-)(?!\.\d)\b"  # noqa: E501
    ),
    "MasterCard": re.compile(
        r"(?:5[1-5][0-9]{2}|222[1-9]|22[3-9][0-9]|2[3-6][0-9]{2}|27[01][0-9]|2720)[0-9]{12}"  # noqa: E501
    ),
    "American Express": re.compile(r"\b(3[47][0-9]{13})\b"),
    "Diners Club": re.compile(r"\b(3(?:0[0-5]|[68][0-9])[0-9]{11})\b"),
    "Discover": re.compile(
        r"\b(6(?:011\d\d|5\d{4}|4[4-9]\d{3}|22(?:1(?:2[6-9]|[3-9]\d)|[2-8]\d\d|9(?:[01]\d|2[0-5])))\d{10})\b"  # noqa: E501
    ),
    "JCB": re.compile(r"\b((?:2131|1800|35\d{3})\d{11})\b"),
}

_all_sensitive_fields = {
    "Email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "CreditCard": re.compile(
        "|".join(
            [pattern.pattern for pattern in _credit_cards_patterns.values()]
        )
    ),
    "IPv4Address": re.compile(
        r"\b((25[0-5]|(2[0-4]|1[0-9]|[1-9]|)[0-9])(\.(?!$)|$)){4}\b"  # noqa: E501
    ),
}

class Guardrails:

    @staticmethod
    def check_moderations(text: str):
        """Checks the text for moderation.

        Args:
            text: The text to be checked.

        Returns:
            True if Open AI moderations identify problems, otherwise False.
        """
        response = client.moderations.create(input=text)
        return response.results[0].flagged

    @staticmethod
    async def check_prompt_hack(text: str):
        """Checks if the text contains prompt hacks.

        Args:
            text: The text to be checked.

        Returns:
            True if prompt hacks are detected, otherwise False.
        """
        messages = [
            {"role": "system", "content": text},
            {"role": "system", "content": prompt_hack},
        ]

        response = await LLMHandler.call_completions_api(
            messages=messages,
            max_tokens=1,
            temperature=0,
            top_p=1.0,
            logit_bias={56: 100, 45: 100},
        )

        content = response["content"]

        if content not in ("Y", "N"):
            raise ValueError(f'Invalid response from LLM when validating prompt hacking! Content: "{content}".')

        return content == "Y"

    @staticmethod
    def check_sensitive_fields(text: str):
        """Checks if the text contains sensitive fields.

        Args:
            text: The text to be checked.

        Returns:
            True if sensitive fields are detected, otherwise False.
        """
        for _, pattern in _all_sensitive_fields.items():
            if pattern.search(text):
                return True
        return False

    @staticmethod
    def check_profanity(text: str):
        """Checks if the text contains profanity.

        Args:
            text: The text to be checked.

        Returns:
            True if profanity is detected, otherwise False.
        """
        for word in words_to_be_filtered:
            if word in text:
                return True

    @staticmethod
    async def run_input_guardrails(text: str):
        """Checks the text for various input guardrails and returns True if none are activated.

        Args:
            text: The text to be checked.

        Returns:
            True if no guardrails are activated and the text is safe, otherwise False.
        """
        
        if Guardrails.check_moderations(text):
            print("OpenAI moderation triggered")
            return False

        if await Guardrails.check_prompt_hack(text):
            print("Prompt hack triggered")
            return False

        if Guardrails.check_sensitive_fields(text):
            print("Sensitive fields triggered")
            return False

        if Guardrails.check_profanity(text):
            print("Profanity triggered")
            return False

        return True
    
    @staticmethod
    def run_output_guardrails(text: str):
        """Checks the text for various output guardrails and returns True if none are activated.

        Args:
            text: The text to be checked.

        Returns:
            True if no guardrails are activated and the text is safe, otherwise False.
        """
        
        if Guardrails.check_moderations(text):
            return False

        if Guardrails.check_sensitive_fields(text):
            return False

        if Guardrails.check_profanity(text):
            return False

        return True
