import re
from dataclasses import dataclass
from sqlalchemy.orm import Session
from app.models import KnowledgeArticle

STOP_WORDS = {"a","an","and","are","can","for","from","how","i","in","is","it","me","my","of","on","please","the","to","what","with"}
MULTILINGUAL_ALIASES = {
    "cheque": {"check", "chequebook", "cheque book", "चेक", "चेकबुक", "kitab", "kitab"},
    "order": {"mangwana", "mangwani", "mangani", "karni", "chahiye", "ऑर्डर", "मंगवानी"},
    "debit card": {"card", "डेबिट कार्ड", "atm card"},
    "block": {"band", "बंद", "disable", "lost", "stolen", "gum"},
    "home loan": {"house loan", "ghar", "मकान", "होम लोन"},
    "documents": {"document", "papers", "kagaz", "कागज़", "दस्तावेज"},
    "minimum balance": {"min balance", "average monthly balance", "amb", "न्यूनतम बैलेंस", "minimum balance requirement"},
    "statement": {"transactions", "स्टेटमेंट", "vivaran"},
}

@dataclass(frozen=True)
class KnowledgeMatch:
    article_id: int
    title: str
    category: str
    content: str
    score: float

def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[\w]+", value.lower(), flags=re.UNICODE) if len(token) > 1 and token not in STOP_WORDS}

def _expanded_query(query: str) -> set[str]:
    normalized = query.lower()
    result = _tokens(normalized)
    for canonical, aliases in MULTILINGUAL_ALIASES.items():
        if canonical in normalized or any(alias in normalized for alias in aliases):
            result.update(_tokens(canonical))
            for alias in aliases:
                result.update(_tokens(alias))
    return result

class KnowledgeRetrievalService:
    """Retrieves active, approved KB content. Replace scoring with vector search without changing callers."""

    def search(self, db: Session, query: str, limit: int = 3) -> list[KnowledgeMatch]:
        query_terms = _expanded_query(query)
        matches: list[KnowledgeMatch] = []
        for article in db.query(KnowledgeArticle).filter_by(active=True).all():
            title_terms = _tokens(article.title)
            keyword_terms = _tokens(article.keywords)
            content_terms = _tokens(article.content)
            score = 4 * len(query_terms & title_terms) + 3 * len(query_terms & keyword_terms) + len(query_terms & content_terms)
            # A single incidental content-word overlap is too weak to ground a banking answer.
            if score >= 3:
                matches.append(KnowledgeMatch(article.id, article.title, article.category, article.content, float(score)))
        return sorted(matches, key=lambda item: (-item.score, item.title))[:limit]

knowledge_retriever = KnowledgeRetrievalService()
