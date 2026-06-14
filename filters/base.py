from abc import ABC, abstractmethod

from models.cv import CVData
from models.filters import FilterResult
from models.config import AppSettings


class Filter(ABC):
    name: str
    priority: int
    hard_fail: bool = False

    @abstractmethod
    def run(self, html: str, cv_data: CVData, jd_text: str, settings: AppSettings | None = None) -> FilterResult:
        ...
