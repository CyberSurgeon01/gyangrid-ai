"""
vector_store.py
FAISS-backed vector store for section-aware chunk retrieval.
Stores (vector, section, text) triples and supports similarity search,
optionally filtered by section name.
"""

import faiss
import numpy as np


class VectorStore:
    def __init__(self, dimension: int = 384):
        # multilingual-e5-small produces 384-dim embeddings
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)  # inner product = cosine sim (vectors are normalized)
        self.chunks = []  # parallel list: chunks[i] corresponds to vector at index i

    def add_chunks(self, embedded_chunks: list):
        """
        embedded_chunks: list of {section, text, chunk_index, embedding}
        as produced by embeddings.embed_chunks()  
        """
        vectors = np.array([c["embedding"] for c in embedded_chunks], dtype="float32")
        self.index.add(vectors)
        self.chunks.extend(embedded_chunks)

    def search(self, query_vector: list, top_k: int = 5, section_filter: str = None) -> list:
        """
        Search for the top_k most similar chunks to query_vector.
        If section_filter is given, only chunks from that section are considered.
        """
        query_vector = np.array([query_vector], dtype="float32")

        if section_filter:
            # Filter chunks by section, search only within that subset
            filtered_indices = [
                i for i, c in enumerate(self.chunks) if c["section"] == section_filter
            ]
            if not filtered_indices:
                return []

            filtered_vectors = np.array(
                [self.chunks[i]["embedding"] for i in filtered_indices], dtype="float32"
            )
            temp_index = faiss.IndexFlatIP(self.dimension)
            temp_index.add(filtered_vectors)

            scores, local_ids = temp_index.search(query_vector, min(top_k, len(filtered_indices)))
            results = []
            for score, local_id in zip(scores[0], local_ids[0]):
                if local_id == -1:
                    continue
                original_idx = filtered_indices[local_id]
                results.append({**self.chunks[original_idx], "score": float(score)})
            return results

        scores, ids = self.index.search(query_vector, top_k)
        results = []
        for score, idx in zip(scores[0], ids[0]):
            if idx == -1:
                continue
            results.append({**self.chunks[idx], "score": float(score)})
        return results

    def is_empty(self) -> bool:
        return self.index.ntotal == 0

    #need to upadate 
