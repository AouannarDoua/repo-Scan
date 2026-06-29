"""
indexing.py — Phase 2b : index hybride sur les chunks.

Combine deux signaux complémentaires :
  - TF-IDF + cosinus : proximité sémantique-lexicale ;
  - BM25 : pertinence lexicale exacte (crucial pour les noms de
    fonctions/variables comme `authenticate_user` ou `JWT_SECRET`).

En production, la brique TF-IDF serait remplacée par des embeddings de code
multilingues + une base vectorielle (FAISS/Qdrant). L'interface resterait
identique, ce qui rend la migration peu coûteuse.
"""
import re
from typing import List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rank_bm25 import BM25Okapi

from .chunking import Chunk


def tokenize(text: str) -> List[str]:
    """Mots + sous-tokens snake_case / camelCase (améliore le rappel)."""
    out = []
    for t in re.findall(r"[A-Za-z_]\w+", text):
        low = t.lower()
        out.append(low)
        for p in low.split("_"):
            if len(p) > 1:
                out.append(p)
        camel = re.sub(r"([a-z])([A-Z])", r"\1 \2", t).lower().split()
        if len(camel) > 1:
            out.extend(p for p in camel if len(p) > 1)
    return out


class HybridIndex:
    def __init__(self, chunks: List[Chunk]):
        self.chunks = chunks
        corpus = [c.text for c in chunks]
        self.vectorizer = TfidfVectorizer(tokenizer=tokenize, token_pattern=None,
                                          max_features=8000)
        self.tfidf = self.vectorizer.fit_transform(corpus)
        self.bm25 = BM25Okapi([tokenize(t) for t in corpus])

    def raw_scores(self, query: str):
        """Renvoie (scores_denses[0,1], scores_bm25) non normalisés."""
        q_vec = self.vectorizer.transform([query])
        dense = cosine_similarity(q_vec, self.tfidf).flatten()
        sparse = self.bm25.get_scores(tokenize(query))
        return dense, sparse
