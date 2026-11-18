"""Cross-encoder reranking for hybrid retrieval."""

from __future__ import annotations

from .types import Hit


class Reranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L6-v2") -> None:
        import torch
        from sentence_transformers import CrossEncoder

        torch.set_num_threads(8)
        self.model_name = model_name
        self.model = CrossEncoder(model_name, device="cpu")

    def rerank(self, query: str, hits: list[Hit], top_n: int = 10) -> list[Hit]:
        if not hits:
            return []
        pairs = [(query, hit.passage.get("text", "")) for hit in hits]
        scores = self.model.predict(pairs)
        reranked = [
            Hit(
                passage_id=hit.passage_id,
                doc_id=hit.doc_id,
                score=float(score),
                passage=hit.passage,
            )
            for hit, score in zip(hits, scores, strict=True)
        ]
        reranked.sort(key=lambda hit: (-hit.score, hit.passage_id))
        return [
            Hit(
                passage_id=hit.passage_id,
                doc_id=hit.doc_id,
                score=hit.score,
                passage=hit.passage,
                rank=rank,
            )
            for rank, hit in enumerate(reranked[:top_n], start=1)
        ]
