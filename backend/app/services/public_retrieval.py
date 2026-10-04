"""Question normalization and evidence ranking for the public RAG agent."""
import re
import unicodedata

STOP = set("what when where which who how could would please about with this that your there their bank union help provide are does mean means meaning definition explain tell the for and you consumer customer".split())

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"\bconsumers?\b", "customer", text)
    text = re.sub(r"\bcustomers\b", "customer", text)
    return " ".join(re.findall(r"\w+", text))

def terms(text: str) -> set[str]:
    return {word for word in normalize(text).split() if len(word) > 2 and word not in STOP}

def definition_term(question: str) -> str | None:
    text = normalize(question)
    patterns = (
        r"(?:what (?:is|are)(?: a| an| the)?|define|explain(?: the)?(?: meaning of)?) (.+)",
        r"(?:what does )?(.+?) (?:means?|meaning)",
        r"(?:what is the )?(?:meaning|definition) of (.+)",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, text)
        if match and 1 <= len(match[1].split()) <= 7:
            return match[1]
    return None

def definition_excerpt(question: str, passage: str) -> str | None:
    """Extract a complete definition of the requested term, never adjacent terms."""
    term = definition_term(question)
    if not term:
        return None
    clean = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", passage)).strip()
    words = [re.escape(word) for word in term.split()]
    pattern = r"\b" + r"\s+".join(words) + r"[\"'’”]*\s+(?:means|refers to|is defined as)\s+[^.]+\."
    match = re.search(pattern, clean, re.I)
    if match and len(match[0]) <= 1200:
        return match[0].replace('” means', ' means').replace('" means', ' means')
    return None

def rank_passages(question: str, matches: list[dict]) -> list[dict]:
    wanted = terms(question)
    ranked = []
    for item in matches:
        content = item["content"]
        definition = definition_excerpt(question, content)
        overlap = len(wanted & terms(item["title"] + " " + content))
        semantic = item.get("score", 0)
        # Exact definitions are useful even in short glossary chunks. Semantic
        # matches need some topic evidence, but do not require literal synonyms.
        if not definition and (len(content.strip()) < 150 or semantic < 0.52 or (wanted and overlap == 0)):
            continue
        coverage = overlap / max(1, len(wanted))
        rank = semantic + .15 * coverage + (1 if definition else 0)
        ranked.append((rank, item))
    return [item for _, item in sorted(ranked, key=lambda pair: pair[0], reverse=True)]
