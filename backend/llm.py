"""
llm.py — LA PARTIE INTELLIGENTE.
================================

À partir des extraits de code récupérés, ce module GÉNÈRE une réponse en
langage naturel, rédigée, SOURCÉE et fiable.

Principe central : le GROUNDING STRICT. Le modèle reçoit pour seule matière
les extraits récupérés et a l'interdiction de répondre au-delà. Chaque
affirmation doit citer `fichier:lignes`. Si l'information n'est pas dans les
extraits, il doit répondre « je ne sais pas » → c'est ce qui limite les
hallucinations.

Fournisseur LLM (détecté automatiquement) :
  - GROQ_API_KEY présent      → Groq (gratuit, rapide) — voie par défaut.
  - sinon ANTHROPIC_API_KEY   → Anthropic (Claude).
  - sinon                     → repli extractif déterministe (aucune invention) :
    on présente simplement les extraits cités. Le système reste donc utilisable
    hors-ligne ; le LLM n'ajoute que la mise en forme et le raisonnement.

Clé Groq gratuite : https://console.groq.com/keys
"""
import os
from typing import Optional

from .retrieval import RetrievalResult

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """Tu es un assistant d'analyse de code. Tu réponds en français.
RÈGLES STRICTES :
- Réponds UNIQUEMENT à partir des extraits fournis. N'utilise aucune autre connaissance.
- Pour chaque affirmation, cite la source au format [fichier:lignes].
- Si l'information n'est pas dans les extraits, dis explicitement que tu ne la trouves pas.
- Sois concis et précis. N'invente jamais de nom de fichier, de fonction ou de ligne."""


def _provider() -> Optional[str]:
    if os.getenv("GROQ_API_KEY"):
        return "groq"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


def _complete_groq(system: str, user: str) -> str:
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    model = os.getenv("REPO_LENS_MODEL") or DEFAULT_GROQ_MODEL
    resp = client.chat.completions.create(
        model=model, max_tokens=700, temperature=0.2,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
    )
    return resp.choices[0].message.content


def _complete_anthropic(system: str, user: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model = os.getenv("REPO_LENS_MODEL") or DEFAULT_ANTHROPIC_MODEL
    msg = client.messages.create(
        model=model, max_tokens=700, system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")


def _format_context(result: RetrievalResult) -> str:
    blocks = []
    for h in result.hits:
        c = h.chunk
        blocks.append(f"[{c.file}:{c.start}-{c.end}]\n{c.text.strip()}")
    return "\n\n".join(blocks)


def synthesize(query: str, result: RetrievalResult) -> dict:
    """Renvoie {answer, mode, provider, confidence, sources}."""
    sources = [{"file": h.chunk.file, "start": h.chunk.start,
                "end": h.chunk.end, "relevance": round(h.relevance, 3)}
               for h in result.hits]

    # Garde-fou : aucun extrait suffisamment pertinent.
    if not result.found:
        return {
            "answer": ("Information non trouvée avec une confiance suffisante dans "
                       "ce dépôt. Reformulez la question ou vérifiez que le code "
                       "concerné est présent."),
            "mode": "guardrail", "provider": None,
            "confidence": "faible", "sources": [],
        }

    context = _format_context(result)
    provider = _provider()

    # --- Mode intelligent : synthèse LLM avec grounding strict --------------
    if provider:
        try:
            user_msg = (f"Extraits récupérés du dépôt :\n\n{context}\n\n"
                        f"Question : {query}\n\n"
                        f"Réponds en citant tes sources [fichier:lignes].")
            answer = (_complete_groq(SYSTEM_PROMPT, user_msg) if provider == "groq"
                      else _complete_anthropic(SYSTEM_PROMPT, user_msg))
            return {"answer": answer, "mode": "llm", "provider": provider,
                    "confidence": result.confidence, "sources": sources}
        except Exception as e:
            print(f"[llm] synthèse {provider} indisponible ({e}); repli extractif.")

    # --- Repli extractif (aucune invention) --------------------------------
    lines = ["Extraits les plus pertinents trouvés (mode hors-ligne, sans LLM) :\n"]
    for h in result.hits:
        snippet = h.chunk.text.strip()
        snippet = snippet[:240] + ("…" if len(snippet) > 240 else "")
        lines.append(f"• [{h.chunk.file}:{h.chunk.start}-{h.chunk.end}] "
                     f"(pertinence {h.relevance:.2f})\n    "
                     + snippet.replace("\n", "\n    "))
    return {"answer": "\n".join(lines), "mode": "extractive", "provider": None,
            "confidence": result.confidence, "sources": sources}
