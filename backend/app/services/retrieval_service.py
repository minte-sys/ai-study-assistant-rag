import numpy as np
from .pdf_service import Chunk


class DocumentIndex:
    def __init__(self, chunks: list[Chunk], embeddings: list[list[float]]):
        matrix = np.asarray(embeddings, dtype=np.float32)
        if matrix.ndim != 2 or len(matrix) != len(chunks) or not np.all(np.isfinite(matrix)):
            raise ValueError("Invalid document embeddings")
        lengths = np.linalg.norm(matrix, axis=1, keepdims=True)
        if np.any(lengths == 0):
            raise ValueError("Empty document embeddings")
        self.chunks = chunks
        self.matrix = matrix / lengths

    def search(self, embedding: list[float], limit: int = 4) -> list[Chunk]:
        vector = np.asarray(embedding, dtype=np.float32)
        if vector.shape != (self.matrix.shape[1],) or not np.all(np.isfinite(vector)):
            raise ValueError("Invalid query embedding")
        norm = np.linalg.norm(vector)
        if norm == 0:
            raise ValueError("Empty query embedding")
        scores = self.matrix @ (vector / norm)
        indices = np.argsort(-scores, kind="stable")[:limit]
        return [self.chunks[int(index)] for index in indices]
