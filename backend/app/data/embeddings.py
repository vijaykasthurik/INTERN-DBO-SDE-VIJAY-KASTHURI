"""Vector embedding store for semantic search over column names and business terms."""

from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class SemanticEmbeddingStore:
    """Embeds schema terms and categorical values with TF-IDF fallback."""

    # Explicit domain synonym mappings for enterprise analytics
    SYNONYM_MAP: dict[str, list[str]] = {
        "revenue": ["turnover", "sales", "earnings", "gross_sales", "income", "receipts"],
        "customer": ["client", "buyer", "account", "consumer", "patron"],
        "product": ["item", "sku", "merchandise", "good", "article"],
        "discount": ["rebate", "allowance", "concession", "markdown"],
        "quantity": ["volume", "units", "amount", "count"],
        "region": ["territory", "location", "geography", "area", "zone"],
    }

    def __init__(self) -> None:
        self.terms: list[str] = []
        self.vectorizer: TfidfVectorizer | None = None
        self.tfidf_matrix: Any = None

    def fit_terms(self, terms: list[str]) -> None:
        """Index catalog terms using TF-IDF for deterministic fast matching."""
        self.terms = list(dict.fromkeys(terms))  # deduplicate preserving order
        if not self.terms:
            return

        # Augment terms with synonyms for training
        corpus = []
        for term in self.terms:
            syns = self.SYNONYM_MAP.get(term.lower(), [])
            corpus.append(f"{term} {' '.join(syns)}")

        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), lowercase=True)
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        """Find most similar schema terms to the query."""
        if not self.terms or self.vectorizer is None or self.tfidf_matrix is None:
            return []

        q_lower = query.lower().strip()

        # Direct synonym lookup check
        for canonical, synonyms in self.SYNONYM_MAP.items():
            if q_lower == canonical or q_lower in synonyms:
                for term in self.terms:
                    if canonical in term.lower():
                        return [(term, 0.99)]

        query_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        scored = [(self.terms[i], float(sims[i])) for i in range(len(self.terms))]
        scored.sort(key=lambda x: x[1], reverse=True)

        return [item for item in scored[:top_k] if item[1] > 0.0]
