import logging
from functools import lru_cache

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _pipeline():
    """Load the English classifier once, on first use."""
    if not settings.local_sentiment_enabled:
        return None
    try:
        from transformers import pipeline

        return pipeline(
            "sentiment-analysis",
            model=settings.local_sentiment_model,
            tokenizer=settings.local_sentiment_model,
            model_kwargs={"local_files_only": settings.local_sentiment_local_files_only},
        )
    except Exception as exc:
        logger.warning("Local sentiment model unavailable; using deterministic fallback: %s", exc)
        return None


def analyze_english_sentiment(text: str) -> tuple[str, float] | None:
    """Return the canonical label and a signed score for English text."""
    classifier = _pipeline()
    if classifier is None or not text.strip():
        return None
    try:
        result = classifier(text[:4000], truncation=True, max_length=512)[0]
        label = str(result["label"]).lower()
        confidence = float(result["score"])
        if "negative" in label or label in {"label_0", "0"}:
            return "Negative", -confidence
        if "neutral" in label or label in {"label_1", "1"}:
            return "Neutral", 0.0
        if "positive" in label or label in {"label_2", "2"}:
            return "Positive", confidence
    except Exception as exc:
        logger.warning("Local sentiment inference failed; using deterministic fallback: %s", exc)
    return None
