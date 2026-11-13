"""Build and query the BM25 and dense retrieval indexes."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import bm25s
import numpy as np
import pandas as pd

from ..corpus.build import read_jsonl, sha256_file, write_json

TOKEN_RE = re.compile(r"[a-z0-9']+")

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# NLTK-style English stopwords plus a few query verbs. Removing these keeps
# BM25 focused on content words; A2 can still compare the raw variant.
STOPWORDS = frozenset(
    """
    a about above after again against all am an and any are aren't as at be
    because been before being below between both but by can't cannot could
    couldn't did didn't do does doesn't doing don't down during each few for
    from further had hadn't has hasn't have haven't having he he'd he'll he's
    her here here's hers herself him himself his how how's i i'd i'll i'm i've
    if in into is isn't it it's its itself let's me more most mustn't my myself
    no nor not of off on once only or other ought our ours ourselves out over
    own same shan't she she'd she'll she's should shouldn't so some such than
    that that's the their theirs them themselves then there there's these they
    they'd they'll they're they've this those through to too under until up
    very was wasn't we we'd we'll we're we've were weren't what what's when
    when's where where's which while who who's whom why why's with won't would
    wouldn't you you'd you'll you're you've your yours yourself yourselves
    make made making
    """.split()
)


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def tokenize_for_index(text: str) -> list[str]:
    """Tokenize for BM25 and drop function words."""
    return [token for token in tokenize(text) if token not in STOPWORDS]


def _read_passages(path: Path) -> list[dict]:
    return list(read_jsonl(path))


def _doc_titles(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return {doc["doc_id"]: doc.get("title", "") for doc in read_jsonl(path)}


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_bm25(
    passages_path: Path,
    out_dir: Path,
    k1: float = 1.5,
    b: float = 0.75,
) -> dict:
    passages = _read_passages(passages_path)
    if not passages:
        raise ValueError(f"no passages found in {passages_path}")

    titles = _doc_titles(passages_path.parent / "docs.jsonl")
    corpus_tokens = [
        tokenize_for_index(f"{titles.get(passage['doc_id'], '')} {passage['text']}")
        for passage in passages
    ]
    retriever = bm25s.BM25(k1=k1, b=b)
    retriever.index(corpus_tokens)

    bm25_dir = out_dir / "bm25"
    bm25_dir.mkdir(parents=True, exist_ok=True)
    retriever.save(str(bm25_dir))

    meta = {
        "index": "bm25",
        "library": f"bm25s-{getattr(bm25s, '__version__', 'unknown')}",
        "k1": k1,
        "b": b,
        "tokenizer": "lowercase regex [a-z0-9']+; English stopwords removed",
        "stopwords": "nltk-english + make/made/making",
        "title_in_index": True,
        "passage_count": len(passages),
        "passages_sha256": sha256_file(passages_path),
        "created_at": _utc_now(),
    }
    write_json(bm25_dir / "meta.json", meta)
    return meta


def load_bm25(out_dir: Path):
    return bm25s.BM25.load(str(out_dir / "bm25"))


def bm25_search(
    out_dir: Path,
    passages: list[dict],
    query: str,
    k: int = 10,
) -> list[dict]:
    query_tokens = tokenize_for_index(query)
    if not query_tokens:
        return []
    retriever = load_bm25(out_dir)
    results, scores = retriever.retrieve([query_tokens], k=k)
    result_indices, result_scores = results[0], scores[0]
    hits: list[dict] = []
    for index, score in zip(result_indices, result_scores, strict=False):
        passage = passages[int(index)]
        hits.append(
            {
                "passage_id": passage["passage_id"],
                "doc_id": passage["doc_id"],
                "score": float(score),
            }
        )
    return hits


def build_dense(
    passages_path: Path,
    out_dir: Path,
    model_name: str = "BAAI/bge-small-en-v1.5",
    batch_size: int = 32,
) -> dict:
    import torch
    from sentence_transformers import SentenceTransformer

    torch.set_num_threads(8)
    passages = _read_passages(passages_path)
    if not passages:
        raise ValueError(f"no passages found in {passages_path}")

    model = SentenceTransformer(model_name, device="cpu")
    embeddings = model.encode(
        [passage["text"] for passage in passages],
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=True,
        convert_to_numpy=True,
    )
    embeddings = np.asarray(embeddings, dtype=np.float32)

    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / "dense.npy", embeddings)

    meta = pd.DataFrame(
        {
            "row": np.arange(len(passages), dtype=np.int64),
            "passage_id": [passage["passage_id"] for passage in passages],
            "doc_id": [passage["doc_id"] for passage in passages],
            "section": [passage["section"] for passage in passages],
            "split": [passage["split"] for passage in passages],
            "source_year": [passage["source_year"] for passage in passages],
        }
    )
    meta.to_parquet(out_dir / "dense_meta.parquet", index=False)

    manifest = {
        "embedding_model": model_name,
        "dim": int(embeddings.shape[1]),
        "passage_count": int(embeddings.shape[0]),
        "passages_sha256": sha256_file(passages_path),
        "normalized": True,
        "created_at": _utc_now(),
    }
    write_json(out_dir / "manifest.json", manifest)
    return manifest


def dense_search(
    out_dir: Path,
    query: str,
    model_name: str = "BAAI/bge-small-en-v1.5",
    k: int = 10,
) -> list[dict]:
    import torch
    from sentence_transformers import SentenceTransformer

    torch.set_num_threads(8)
    embeddings = np.load(out_dir / "dense.npy")
    meta = pd.read_parquet(out_dir / "dense_meta.parquet")
    model = SentenceTransformer(model_name, device="cpu")
    query_vector = model.encode(
        [QUERY_PREFIX + query],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )[0]

    scores = embeddings @ query_vector
    top_indices = np.argsort(-scores)[:k]
    hits: list[dict] = []
    for index in top_indices:
        row = meta.iloc[int(index)]
        hits.append(
            {
                "passage_id": row["passage_id"],
                "doc_id": row["doc_id"],
                "score": float(scores[int(index)]),
            }
        )
    return hits


def smoke(
    out_dir: Path,
    passages_path: Path,
    query: str,
    model_name: str = "BAAI/bge-small-en-v1.5",
    k: int = 5,
) -> dict:
    passages = _read_passages(passages_path)
    payload = {
        "query": query,
        "passage_count": len(passages),
        "bm25": bm25_search(out_dir, passages, query, k=k),
        "dense": dense_search(out_dir, query, model_name=model_name, k=k),
    }
    return payload


def build_all_indexes(
    passages_path: Path,
    out_dir: Path,
    model_name: str = "BAAI/bge-small-en-v1.5",
    batch_size: int = 32,
) -> dict:
    bm25_meta = build_bm25(passages_path, out_dir)
    dense_meta = build_dense(
        passages_path,
        out_dir,
        model_name=model_name,
        batch_size=batch_size,
    )
    return {"bm25": bm25_meta, "dense": dense_meta}


def load_index_manifest(out_dir: Path) -> dict:
    path = out_dir / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
