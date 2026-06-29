"""
critical.py — Phase 4 : détection des fichiers / zones critiques.

Le score combine plusieurs signaux (plus robuste qu'un critère unique) :
  - centralité   : nombre de fichiers qui importent ce fichier (fan-in) ;
  - sensibilité  : nom/chemin évoquant sécurité, secrets ou configuration ;
  - point d'entrée ;
  - instabilité  : fréquence de modification (churn Git).
"""
import os
from dataclasses import dataclass
from typing import List, Dict

from .ingest import FileInfo

SENSITIVE = ["auth", "login", "password", "secret", "token", "crypto", "payment",
             "credential", "security", "config", "settings", ".env",
             "database", "db", "migration"]
ENTRYPOINT = ["main", "app", "server", "index", "__main__", "manage", "wsgi", "asgi"]


@dataclass
class CriticalFile:
    path: str
    score: float
    reasons: List[str]


def _stem(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def critical_files(files: List[FileInfo]) -> List[CriticalFile]:
    # Centralité : un fichier est "importé" si un chemin de module pointe vers lui.
    # Ex. "from utils.db import X" → module "utils.db" → fichier "utils/db.py".
    paths_no_ext = {f.path: os.path.splitext(f.path)[0].replace(os.sep, "/") for f in files}
    fan_in: Dict[str, int] = {f.path: 0 for f in files}
    for f in files:
        for imp in f.imports:
            target = imp.replace(".", "/")
            for g in files:
                if g.path == f.path:
                    continue
                gp = paths_no_ext[g.path]
                if gp == target or gp.endswith("/" + target):
                    fan_in[g.path] += 1

    max_fan = max(fan_in.values(), default=1) or 1
    max_churn = max((f.churn for f in files), default=1) or 1

    stems = {f.path: _stem(f.path) for f in files}
    out: List[CriticalFile] = []
    for f in files:
        score, reasons = 0.0, []
        if fan_in[f.path]:
            score += 0.40 * (fan_in[f.path] / max_fan)
            reasons.append(f"importé par {fan_in[f.path]} fichier(s) — centralité")
        low = f.path.lower()
        if any(h in low for h in SENSITIVE):
            score += 0.30
            reasons.append("nom/chemin sensible — sécurité ou configuration")
        if stems[f.path] in ENTRYPOINT:
            score += 0.20
            reasons.append("point d'entrée probable")
        if f.churn:
            score += 0.30 * (f.churn / max_churn)
            reasons.append(f"modifié {f.churn} fois — instabilité")
        if score > 0:
            out.append(CriticalFile(f.path, round(min(score, 1.0), 3), reasons))
    return sorted(out, key=lambda c: c.score, reverse=True)
