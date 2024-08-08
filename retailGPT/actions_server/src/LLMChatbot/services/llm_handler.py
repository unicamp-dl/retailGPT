import asyncio
import os

import aiohttp
from dotenv import load_dotenv
from openai import BadRequestError

load_dotenv()


class LLMHandler:
    """Handles LLM calls for the chatbot and its tools."""

    _azure_model_deployment: str = "gpt-4-0125-preview"
    _azure_openai_api_key: str = os.environ.get("AZURE_OPENAI_API_KEY", None)
    _azure_resource: str = os.environ.get("AZURE_RESOURCE", None)
    _api_version: str = os.environ.get("AZURE_API_VERSION", None)
    _azure_inner_guardrail_error: str = (
        "A mensagem não pode ser processada por conter conteúdo inapropriado. Por favor, reformule a mensagem."
    )
    _azure_inner_error: str = "Erro interno ao processar a mensagem."

    _openai_api_key: str = os.environ.get("OPENAI_API_KEY", None)
    _openai_model: str = "gpt-4o"

    @staticmethod
    async def _post_completion_request(
        session: aiohttp.ClientSession,
        headers: dict,
        messages: list,
        tools: list = None,
        use_azure: bool = False,
        **kwargs,
    ) -> dict:
        """Posts a completion request to the OpenAI or Azure completions API."""

        if use_azure:
            url = f"https://{LLMHandler._azure_resource}.openai.azure.com/openai/deployments/{LLMHandler._azure_model_deployment}/chat/completions?api-version={LLMHandler._api_version}"
            payload = {
                "model": LLMHandler._azure_model_deployment,
                "messages": messages,
                "tools": tools,
                **kwargs,
            }
        else:
            url = "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": LLMHandler._openai_model,
                "messages": messages,
                "tools": tools,
                **kwargs,
            }

        attempt = 0
        max_attempts = 100
        backoff_factor = 2  # seconds

        while attempt < max_attempts:
            async with session.post(url, json=payload, headers=headers) as response:

                # Rate limit exceeded
                if response.status == 429:
                    # Exponential backoff
                    retry_after = backoff_factor * (2**attempt)
                    print(f"Rate limit exceeded. Retrying in {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                    attempt += 1
                    continue
                elif response.status != 200:
                    response_text = await response.text()
                    print(
                        f"Error: Received status code {response.status} with response {response_text}"
                    )
                    response.raise_for_status()

                response_json = await response.json()
                if "choices" not in response_json:
                    print(f"'choices' not in response JSON: {response_json}")
                    raise ValueError("'choices' not in response JSON")

                return response_json["choices"][0]["message"]

        raise Exception("Max retries exceeded for API requests")

    @staticmethod
    async def call_completions_api(
        messages: list,
        tools: list | None = None,
        session: aiohttp.ClientSession | None = None,
        use_azure: bool = False,
        **kwargs,
    ) -> dict:
        """Calls the OpenAI completions API to generate a response to the user's message.

        Args:

        messages: A list of messages exchanged between the user and the chatbot, in the Open AI's role-content dict style.

        tools: A list of tools that the chatbot can use to perform specific actions, in the Open AI's tool's definition schema.

        Returns:

        The response message dict.

        """

        if use_azure:
            headers = {
                "Content-Type": "application/json",
                "api-key": f"{LLMHandler._azure_openai_api_key}",
            }
        else:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {LLMHandler._openai_api_key}",
            }

        try:
            async with aiohttp.ClientSession() as session:
                return await LLMHandler._post_completion_request(
                    session, headers, messages, tools, use_azure=use_azure, **kwargs
                )

        except BadRequestError as e:
            error_json = await e.response.json()
            inner_error_type = (
                error_json.get("error", {}).get("innererror", {}).get("code", None)
            )
            if inner_error_type == "ResponsibleAIPolicyViolation":
                error_content = LLMHandler._azure_inner_guardrail_error
            else:
                error_content = LLMHandler._azure_inner_error
            return {
                "role": "assistant",
                "content": error_content,
                "function_call": None,
                "tool_calls": None,
            }
        except Exception as e:
            print(f"Unexpected error in call completions api: {e}")
            return {
                "role": "assistant",
                "content": "An unexpected error occurred.",
                "function_call": None,
                "tool_calls": None,
            }
        
    @staticmethod
    def call_completions_api_sync(
        messages: list,
        tools: list | None = None,
        use_azure: bool = False,
        **kwargs,
    ) -> dict:
        """Synchronous wrapper for the asynchronous call_completions_api."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            loop = new_loop
        else:
            new_loop = loop

        result = loop.run_until_complete(
            LLMHandler.call_completions_api(
                messages, tools=tools, use_azure=use_azure, **kwargs
            )
        )

        if new_loop != loop:
            new_loop.close()
        
        return result
