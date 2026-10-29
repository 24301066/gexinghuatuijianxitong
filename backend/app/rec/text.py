"""TF-IDF over titles/categories/tags — plain numpy, no sklearn."""

from __future__ import annotations

import math
import re

import numpy as np

_ASCII_WORD = re.compile(r"[a-z0-9]+")
_CJK = re.compile(r"[\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    """ASCII words + CJK character bigrams (no external tokenizer needed)."""
    lowered = (text or "").lower()
    tokens = _ASCII_WORD.findall(lowered)
    cjk = "".join(_CJK.findall(lowered))
    tokens.extend(cjk[index:index + 2] for index in range(len(cjk) - 1))
    if len(cjk) == 1:
        tokens.append(cjk)
    return tokens


def build_matrix(documents: list[str]) -> np.ndarray:
    """Return an L2-normalised TF-IDF matrix (n_docs x vocab)."""
    if not documents:
        return np.zeros((0, 0), dtype=np.float64)

    tokenized = [tokenize(doc) for doc in documents]
    vocabulary: dict[str, int] = {}
    for tokens in tokenized:
        for token in tokens:
            if token not in vocabulary:
                vocabulary[token] = len(vocabulary)

    matrix = np.zeros((len(documents), len(vocabulary)), dtype=np.float64)
    for row, tokens in enumerate(tokenized):
        for token in tokens:
            matrix[row, vocabulary[token]] += 1.0
        total = len(tokens) or 1
        matrix[row] /= total

    df = (matrix > 0).sum(axis=0)
    idf = np.log((1.0 + len(documents)) / (1.0 + df)) + 1.0
    matrix *= idf

    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def cosine(matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        return np.zeros(matrix.shape[0], dtype=np.float64)
    return matrix @ (vector / norm)


def document_of(title: str, category: str, tags: str) -> str:
    weight_tag = " ".join([tags.replace(",", " ")] * 2)
    return f"{title} {category} {weight_tag}".strip()


def smooth(value: float) -> float:
    return math.tanh(value) if value else 0.0
