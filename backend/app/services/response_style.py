import re


def strip_unnecessary_apology(text: str) -> str:
    """Remove a model-added opening apology from neutral informational answers."""
    cleaned = re.sub(
        r"^\s*(?:(?:i(?:'|’)m|i am) sorry|sorry)(?:\s+that|\s+to hear)?[^.!?]*[.!?]\s*",
        "",
        text,
        count=1,
        flags=re.I,
    ).strip()
    return cleaned or text.strip()
