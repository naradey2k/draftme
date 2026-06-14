from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from models.config import AppSettings


def build_modal_model(settings: AppSettings) -> OpenAIChatModel:
    is_qwen = settings.model.name.lower().startswith("qwen")
    client = AsyncOpenAI(
        base_url=settings.model.base_url,
        api_key=settings.model.api_key,
        timeout=180,
        max_retries=1,
    )
    return OpenAIChatModel(
        settings.model.name,
        provider=OpenAIProvider(openai_client=client),
        settings=_modal_model_settings(settings),
        system_prompt_role="user" if is_qwen else None,
    )


def _modal_model_settings(settings: AppSettings) -> dict:
    model_name = settings.model.name.lower()
    model_settings: dict = {
        "temperature": settings.model.temperature,
        "max_tokens": settings.model.max_tokens,
    }
    if model_name.startswith("qwen"):
        model_settings.update(
            {
                "top_p": 0.8,
                "presence_penalty": 1.5,
                "extra_body": {
                    "top_k": 20,
                    "chat_template_kwargs": {"enable_thinking": False},
                },
            }
        )
    elif "nemotron" in model_name:
        model_settings["extra_body"] = {
            "chat_template_kwargs": {"enable_thinking": False},
        }
    return model_settings
