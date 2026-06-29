"""
ingest.py — Phase 1 : parcours, classification et métadonnées du repository.
"""
import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

CODE_EXT = {".py", ".js", ".ts", ".java", ".go", ".rb", ".php", ".c", ".cpp",
            ".cs", ".rs", ".kt", ".swift", ".scala"}
DOC_EXT = {".md", ".rst", ".txt"}
CONFIG_EXT = {".yml", ".yaml", ".toml", ".ini", ".cfg", ".env", ".json"}
IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv",
               "dist", "build", ".idea", ".pytest_cache"}


@dataclass
class FileInfo:
    path: str
    category: str          # code | doc | config
    language: str
    n_lines: int
    imports: List[str] = field(default_factory=list)
    churn: int = 0         # nb de commits touchant le fichier (signal Git)


def classify(path: str) -> Tuple[str, str]:
    ext = os.path.splitext(path)[1].lower()
    if ext in CODE_EXT:
        return "code", ext.lstrip(".")
    if ext in DOC_EXT:
        return "doc", ext.lstrip(".")
    if ext in CONFIG_EXT or os.path.basename(path).startswith(".env"):
        return "config", ext.lstrip(".") or "env"
    return "other", ext.lstrip(".")


def extract_imports(text: str, language: str) -> List[str]:
    """Imports → utile pour estimer la centralité (graphe de dépendances)."""
    imports = []
    if language == "py":
        for m in re.finditer(r"^\s*(?:from\s+([\w.]+)|import\s+([\w.]+))",
                             text, re.MULTILINE):
            imports.append(m.group(1) or m.group(2))   # chemin de module complet
    elif language in {"js", "ts"}:
        for m in re.finditer(r"""(?:import.*?from\s+['"]([^'"]+)|require\(['"]([^'"]+))""", text):
            imports.append((m.group(1) or m.group(2)).replace("./", ""))
    return imports


def git_churn(repo_path: str) -> Dict[str, int]:
    """Nombre de commits par fichier. Vide si le dossier n'est pas un repo Git."""
    try:
        out = subprocess.run(
            ["git", "-C", repo_path, "log", "--name-only", "--pretty=format:"],
            capture_output=True, text=True, timeout=30,
        ).stdout
        counts: Dict[str, int] = {}
        for line in out.splitlines():
            line = line.strip()
            if line:
                counts[line] = counts.get(line, 0) + 1
        return counts
    except Exception:
        return {}


def ingest(repo_path: str) -> Tuple[List[FileInfo], Dict[str, str]]:
    """Parcourt le repo, classe les fichiers et lit leur contenu."""
    churn = git_churn(repo_path)
    files: List[FileInfo] = []
    contents: Dict[str, str] = {}
    for root, dirs, names in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for name in names:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, repo_path)
            category, language = classify(name)
            if category == "other":
                continue
            try:
                text = open(full, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            files.append(FileInfo(
                path=rel, category=category, language=language,
                n_lines=text.count("\n") + 1,
                imports=extract_imports(text, language),
                churn=churn.get(rel, 0),
            ))
            contents[rel] = text
    return files, contents


def ingest_from_contents(contents: Dict[str, str]) -> Tuple[List[FileInfo], Dict[str, str]]:
    """Variante en mémoire : indexe des fichiers fournis (import navigateur),
    sans accès disque ni churn Git."""
    files: List[FileInfo] = []
    out: Dict[str, str] = {}
    for raw_path, text in contents.items():
        path = raw_path.replace("\\", "/")
        category, language = classify(path)
        if category == "other":
            continue
        files.append(FileInfo(
            path=path, category=category, language=language,
            n_lines=text.count("\n") + 1,
            imports=extract_imports(text, language), churn=0,
        ))
        out[path] = text
    return files, out
