"""
assistant.py — Orchestrateur : relie toutes les phases du pipeline.

    ingest → chunk → index → (à chaque question) retrieve → synthesize
"""
from typing import List, Dict

from .ingest import ingest, ingest_from_contents, FileInfo
from .chunking import chunk_repo
from .indexing import HybridIndex
from .retrieval import retrieve
from .critical import critical_files
from .llm import synthesize


class RepoAssistant:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.files: List[FileInfo] = []
        self.index: HybridIndex | None = None

    def build(self) -> "RepoAssistant":
        self.files, contents = ingest(self.repo_path)
        chunks = chunk_repo(self.files, contents)
        if not chunks:
            raise ValueError("aucun fichier indexable")
        self.index = HybridIndex(chunks)
        return self

    @classmethod
    def from_contents(cls, contents: Dict[str, str], label: str = "dépôt importé") -> "RepoAssistant":
        """Construit l'assistant à partir de fichiers fournis en mémoire."""
        self = cls(label)
        self.files, c = ingest_from_contents(contents)
        chunks = chunk_repo(self.files, c)
        if not chunks:
            raise ValueError("aucun fichier indexable")
        self.index = HybridIndex(chunks)
        return self

    def ask(self, query: str, k: int = 4) -> dict:
        result = retrieve(self.index, query, k=k)
        return synthesize(query, result)

    def critical(self) -> List[dict]:
        return [c.__dict__ for c in critical_files(self.files)]

    def tree(self) -> List[dict]:
        return [{"path": f.path, "category": f.category,
                 "language": f.language, "n_lines": f.n_lines}
                for f in sorted(self.files, key=lambda x: x.path)]

    def stats(self) -> Dict[str, int]:
        return {
            "files": len(self.files),
            "chunks": len(self.index.chunks) if self.index else 0,
            "code": sum(f.category == "code" for f in self.files),
            "config": sum(f.category == "config" for f in self.files),
            "doc": sum(f.category == "doc" for f in self.files),
        }
