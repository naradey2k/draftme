import math
import re
from collections import Counter

import spacy

from filters.base import Filter
from models.config import AppSettings
from models.cv import CVData
from models.filters import FilterResult

_NLP = None


class KeywordFilter(Filter):
    name = "keyword"
    priority = 3

    def run(self, html: str, cv_data: CVData, jd_text: str, settings: AppSettings | None = None) -> FilterResult:
        keywords = _extract_keywords(jd_text)
        if not keywords:
            return FilterResult(filter_name=self.name, passed=True, score=1.0, detail={"keywords": []})
        resume_text = re.sub(r"<[^>]+>", " ", html).lower()
        present = [kw for kw in keywords if kw.lower() in resume_text]
        score = len(present) / len(keywords)
        missing = [kw for kw in keywords if kw not in present][:15]
        passed = score >= 0.65
        feedback = "" if passed else "Missing important job-description keywords: " + ", ".join(missing)
        return FilterResult(
            filter_name=self.name,
            passed=passed,
            score=score,
            feedback=feedback,
            detail={"keywords": keywords, "present": present, "missing": missing},
        )


def _extract_keywords(text: str) -> list[str]:
    nlp = _load_nlp()
    if nlp:
        doc = nlp(text)
        terms = [chunk.text.strip().lower() for chunk in doc.noun_chunks if 2 <= len(chunk.text.strip()) <= 40]
        terms.extend(token.lemma_.lower() for token in doc if token.pos_ in {"PROPN", "NOUN"} and not token.is_stop)
    else:
        terms = re.findall(r"\b[a-zA-Z][a-zA-Z0-9+#.-]{2,}\b", text.lower())

    counts = Counter(term for term in terms if len(term) > 2)
    if not counts:
        return []
    total = sum(counts.values())
    scored = [(term, count * math.log(1 + total / count)) for term, count in counts.items()]
    return [term for term, _ in sorted(scored, key=lambda item: item[1], reverse=True)[:25]]


def _load_nlp():
    global _NLP
    if _NLP is not None:
        return _NLP
    try:
        _NLP = spacy.load("en_core_web_sm")
    except Exception:
        _NLP = False
    return _NLP
