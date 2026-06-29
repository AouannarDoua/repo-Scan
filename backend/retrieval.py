"""
retrieval.py — Phase 3 : recherche hybride + garde-fou anti-hallucination.

Fusionne les scores TF-IDF et BM25 (normalisés) pour le classement, et
conserve la pertinence absolue (cosinus brut) pour décider du niveau de
confiance et déclencher la réponse « information non trouvée ».

Normalisation FR→EN légère : permet aux questions en français de retrouver
du code en anglais. La version production (embeddings multilingues) rend
cette étape inutile.
"""
from dataclasses import dataclass
from typing import List
import re

import numpy as np

from .indexing import HybridIndex
from .chunking import Chunk

SYNONYMS = {
    "authentification": "authenticate login", "authentifier": "authenticate login",
    "connexion": "connection login", "utilisateur": "user", "mot": "password",
    "passe": "password", "paiement": "payment charge pay", "payer": "payment charge",
    "jeton": "token", "jetons": "token", "base": "database", "données": "database",
    "bdd": "database", "sécurité": "security", "configuration": "config settings",
}


def expand_query(query: str) -> str:
    # On extrait les mots (gère l'élision « l'authentification » → authentification).
    tokens = re.findall(r"[a-zàâçéèêëîïôûùüÿñ]+", query.lower())
    extra = [SYNONYMS[t] for t in tokens if t in SYNONYMS]
    return query + " " + " ".join(extra)


@dataclass
class Retrieved:
    chunk: Chunk
    relevance: float    # score fusionné normalisé (classement)
    cosine: float       # pertinence absolue


@dataclass
class RetrievalResult:
    hits: List[Retrieved]
    found: bool
    confidence: str     # élevée | moyenne | faible


def _norm(a: np.ndarray) -> np.ndarray:
    rng = a.max() - a.min()
    return (a - a.min()) / rng if rng > 0 else a * 0


def retrieve(index: HybridIndex, query: str, k: int = 4,
             threshold: float = 0.04) -> RetrievalResult:
    dense, sparse = index.raw_scores(expand_query(query))
    fused = 0.5 * _norm(dense) + 0.5 * _norm(sparse)
    # Léger malus aux chunks de documentation : le README contient souvent tous
    # les mots-clés et masquerait le code réellement pertinent.
    weights = np.array([0.7 if c.category == "doc" else 1.0 for c in index.chunks])
    fused = fused * weights
    order = fused.argsort()[::-1][:k]

    abs_top = float(dense.max()) if len(dense) else 0.0
    found = abs_top >= threshold or (len(sparse) and sparse.max() > 0)
    confidence = "élevée" if abs_top > 0.30 else "moyenne" if abs_top > 0.10 else "faible"

    hits = [Retrieved(index.chunks[i], float(fused[i]), float(dense[i])) for i in order]
    return RetrievalResult(hits=hits, found=found, confidence=confidence)
