"""
chunking.py — Phase 2a : découpage 'code-aware' du contenu en chunks.

On coupe en priorité sur les frontières de fonctions/classes plutôt qu'au
milieu d'un bloc. En production, remplacer la regex par un parse AST
(tree-sitter) pour un découpage syntaxiquement exact et multi-langage.
"""
import re
from dataclasses import dataclass
from typing import List, Dict

from .ingest import FileInfo

_BOUNDARY = re.compile(r"^\s*(def |class |function |func |public |private |export )")


@dataclass
class Chunk:
    file: str
    start: int      # ligne de début (1-indexée)
    end: int        # ligne de fin
    text: str
    category: str


def chunk_file(info: FileInfo, text: str, max_lines: int = 40) -> List[Chunk]:
    lines = text.splitlines()
    if not lines:
        return []
    chunks, start = [], 0
    for i, line in enumerate(lines):
        if (_BOUNDARY.match(line) and i > start) or (i - start >= max_lines):
            chunks.append(Chunk(info.path, start + 1, i,
                                "\n".join(lines[start:i]), info.category))
            start = i
    chunks.append(Chunk(info.path, start + 1, len(lines),
                        "\n".join(lines[start:]), info.category))
    return [c for c in chunks if c.text.strip()]


def chunk_repo(files: List[FileInfo], contents: Dict[str, str]) -> List[Chunk]:
    chunks: List[Chunk] = []
    for f in files:
        chunks.extend(chunk_file(f, contents[f.path]))
    return chunks
