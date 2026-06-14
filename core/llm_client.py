import re
from pathlib import Path
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from models.config import ModelSettings

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    def __init__(self, settings: ModelSettings, debug: bool = False, debug_dir: Path | None = None):
        self.client = OpenAI(base_url=settings.base_url, api_key=settings.api_key)
        self.settings = settings
        self.debug = debug
        self.debug_dir = debug_dir

    def chat(self, messages: list[dict], schema: type[BaseModel] | None = None) -> str:
        extra_body = _extra_body(self.settings, schema)
        response = self.client.chat.completions.create(
            model=self.settings.name,
            messages=messages,
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
            extra_body=extra_body,
        )
        content = response.choices[0].message.content or ""
        if self.debug and self.debug_dir:
            self.debug_dir.mkdir(parents=True, exist_ok=True)
            count = len(list(self.debug_dir.glob("llm_response_*.txt")))
            (self.debug_dir / f"llm_response_{count + 1}.txt").write_text(content, encoding="utf-8")
        return content

    def chat_structured(self, messages: list[dict], schema: type[T]) -> T:
        last_error: Exception | None = None
        working_messages = list(messages)
        for _ in range(2):
            raw = self.chat(working_messages, schema=schema)
            cleaned = _strip_markdown_fences(raw)
            try:
                return schema.model_validate_json(cleaned)
            except ValidationError as exc:
                last_error = exc
                working_messages.append(
                    {
                        "role": "user",
                        "content": (
                            "The previous response did not match the required JSON schema. "
                            f"Validation error: {exc}. Return only valid JSON."
                        ),
                    }
                )
        raise last_error or ValueError("Structured LLM response could not be parsed")


def _extra_body(settings: ModelSettings, schema: type[BaseModel] | None = None) -> dict | None:
    extra: dict = {}
    if schema:
        extra["format"] = schema.model_json_schema()
    model_name = settings.name.lower()
    if model_name.startswith("qwen"):
        extra["top_k"] = 20
        extra["chat_template_kwargs"] = {"enable_thinking": False}
    elif "nemotron" in model_name:
        extra["chat_template_kwargs"] = {"enable_thinking": False}
    return extra or None


def _strip_markdown_fences(text: str) -> str:
    stripped = text.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else stripped
