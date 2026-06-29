"""
api.py — API web (FastAPI) consommée par le frontend.

Endpoints :
    GET  /api/stats           → statistiques d'indexation + chemin courant
    GET  /api/tree            → arborescence des fichiers
    GET  /api/critical        → fichiers critiques détectés
    POST /api/ask  {query}    → réponse sourcée (mode llm | extractive | guardrail)
    POST /api/load {path}     → ré-indexe un autre dépôt local

Le dépôt analysé est défini par la variable d'environnement REPO_PATH
(par défaut : ./sample_repo). Lancement :
    python -m uvicorn backend.api:app --reload
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()  # charge GROQ_API_KEY / ANTHROPIC_API_KEY depuis .env
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .assistant import RepoAssistant

DEFAULT_REPO = os.path.join(os.path.dirname(__file__), "..", "sample_repo")
REPO_PATH = os.getenv("REPO_PATH", DEFAULT_REPO)

app = FastAPI(title="Repo Lens API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# État global : l'assistant courant et le chemin indexé.
state = {"assistant": RepoAssistant(REPO_PATH).build(),
         "path": os.path.abspath(REPO_PATH)}


class AskBody(BaseModel):
    query: str
    k: int = 4


class LoadBody(BaseModel):
    path: str


class LoadFilesBody(BaseModel):
    files: list  # [{path, content}]
    label: str = "dépôt importé"


def _stats():
    s = state["assistant"].stats()
    s["path"] = state["path"]
    return s


@app.get("/api/stats")
def stats():
    return _stats()


@app.get("/api/tree")
def tree():
    return state["assistant"].tree()


@app.get("/api/critical")
def critical():
    return state["assistant"].critical()


@app.post("/api/ask")
def ask(body: AskBody):
    return state["assistant"].ask(body.query, k=body.k)


@app.post("/api/load")
def load(body: LoadBody):
    path = os.path.expanduser(body.path.strip().strip('"').strip("'"))
    if not os.path.isdir(path):
        return {"ok": False, "error": f"Dossier introuvable : {path}"}
    try:
        assistant = RepoAssistant(path).build()
    except ValueError:
        return {"ok": False, "error": "Aucun fichier de code/doc indexable dans ce dossier."}
    except Exception as e:
        return {"ok": False, "error": f"Échec de l'indexation : {e}"}
    state["assistant"] = assistant
    state["path"] = os.path.abspath(path)
    return {"ok": True, "stats": _stats()}


@app.post("/api/load_files")
def load_files(body: LoadFilesBody):
    contents = {f["path"]: f["content"] for f in body.files
                if isinstance(f, dict) and f.get("path") and f.get("content")}
    if not contents:
        return {"ok": False, "error": "Aucun fichier lisible reçu."}
    try:
        assistant = RepoAssistant.from_contents(contents, body.label)
    except ValueError:
        return {"ok": False, "error": "Aucun fichier de code/doc indexable dans ce dossier."}
    except Exception as e:
        return {"ok": False, "error": f"Échec de l'indexation : {e}"}
    state["assistant"] = assistant
    state["path"] = body.label
    return {"ok": True, "stats": _stats()}


# Sert le frontend statique sur "/"
_frontend = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_frontend):
    app.mount("/", StaticFiles(directory=_frontend, html=True), name="frontend")
