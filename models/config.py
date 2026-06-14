from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelSettings(BaseModel):
    name: str = "qwen3.5-27b-fp8"
    base_url: str = "your-qwen-api-url-here"
    api_key: str = "EMPTY"
    temperature: float = 0.3
    max_tokens: int = 4096


class ModelOption(BaseModel):
    name: str
    base_url: str
    label: str
    api_key: str = "EMPTY"


class AppSettings(BaseSettings):
    model: ModelSettings = ModelSettings()
    model_options: dict[str, ModelOption] = Field(
        default_factory=lambda: {
            "qwen": ModelOption(
                label="Qwen 3.5 27B FP8",
                name="qwen3.5-27b-fp8",
                base_url="your-qwen-api-url-here",
            ),
            "nemotron": ModelOption(
                label="Nemotron 3 Nano 30B BF16",
                name="nemotron-3-nano-30b-bf16",
                base_url="your-nemotron-api-url-here",
            ),
        }
    )
    max_iterations: int = 4
    language: str = "en"
    tone: Literal["professional", "concise", "executive"] = "professional"
    output_dir: Path = Path("output")
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")
