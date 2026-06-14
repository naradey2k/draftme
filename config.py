from functools import lru_cache

from models.config import AppSettings


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()

