from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from .schema import Qrel, Query
from .validate import load_qrels, load_queries, write_jsonl

SLICES = ("easy", "multi-hop", "temporal", "no-evidence")


@dataclass(frozen=True)
class SplitResult:
    queries: int
    train: int
    test: int
    assignments: dict[str, str]
    train_slices: dict[str, int]
    test_slices: dict[str, int]
    components: int
    train_components: int
    mixed_slice_components: int
    gold_docs_train: int
    gold_docs_test: int
    gold_doc_overlap: list[str]
    queries_sha256: str
    qrels_sha256: str
    train_sha256: str
    test_sha256: str


class _UnionFind:
    def __init__(self, keys: list[str]) -> None:
        self._parent = {key: key for key in keys}

    def find(self, key: str) -> str:
        root = key
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[key] != root:
            self._parent[key], key = root, self._parent[key]
        return root

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self._parent[left_root] = right_root


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def allocate_train_counts(slice_counts: dict[str, int], train_total: int) -> dict[str, int]:
    total = sum(slice_counts.values())
    if train_total < 0 or train_total > total:
        raise ValueError(f"train_total {train_total} outside 0..{total}")
    exact = {name: slice_counts.get(name, 0) * train_total / total for name in SLICES}
    allocated = {name: int(exact[name]) for name in SLICES}
    remaining = train_total - sum(allocated.values())
    ranked = sorted(SLICES, key=lambda name: (-(exact[name] - allocated[name]), name))
    for name in ranked[:remaining]:
        allocated[name] += 1
    return allocated


def relevance2_docs(queries: list[Query], qrels: list[Qrel]) -> dict[str, set[str]]:
    known = {query.query_id for query in queries}
    docs: dict[str, set[str]] = {query.query_id: set() for query in queries}
    for row in qrels:
        if row.relevance == 2 and row.query_id in known:
            docs[row.query_id].add(row.doc_id)
    return docs


def build_components(query_ids: list[str], docs_by_query: dict[str, set[str]]) -> list[list[str]]:
    union_find = _UnionFind(query_ids)
    by_doc: dict[str, list[str]] = defaultdict(list)
    for query_id in query_ids:
        for doc_id in docs_by_query.get(query_id, set()):
            by_doc[doc_id].append(query_id)
    for query_ids_for_doc in by_doc.values():
        for other in query_ids_for_doc[1:]:
            union_find.union(query_ids_for_doc[0], other)
    groups: dict[str, list[str]] = defaultdict(list)
    for query_id in query_ids:
        groups[union_find.find(query_id)].append(query_id)
    return sorted((sorted(group) for group in groups.values()), key=lambda g: (-len(g), g[0]))


def component_vector(component: list[str], slice_by_query: dict[str, str]) -> tuple[int, ...]:
    counts = Counter(slice_by_query[query_id] for query_id in component)
    return tuple(counts.get(name, 0) for name in SLICES)


def solve_component_assignment(
    components: list[list[str]],
    slice_by_query: dict[str, str],
    target: dict[str, int],
    seed: int,
) -> list[int]:
    target_vector = tuple(target[name] for name in SLICES)
    origin = (0,) * len(SLICES)
    order = sorted(
        range(len(components)),
        key=lambda index: hashlib.sha256(f"{seed}:{components[index][0]}".encode()).hexdigest(),
    )
    parents: dict[tuple[int, ...], tuple[tuple[int, ...], int] | None] = {origin: None}
    for index in order:
        vector = component_vector(components[index], slice_by_query)
        additions: dict[tuple[int, ...], tuple[tuple[int, ...], int]] = {}
        for state in list(parents):
            candidate = tuple(left + right for left, right in zip(state, vector, strict=True))
            if any(value > cap for value, cap in zip(candidate, target_vector, strict=True)):
                continue
            if candidate in parents or candidate in additions:
                continue
            additions[candidate] = (state, index)
        parents.update(additions)
        if target_vector in parents:
            break

    if target_vector not in parents:
        reachable = max(
            parents,
            key=lambda state: (
                -sum(abs(value - cap) for value, cap in zip(state, target_vector, strict=True)),
                state,
            ),
        )
        raise ValueError(
            f"no component assignment reaches "
            f"{dict(zip(SLICES, target_vector, strict=True))}; "
            f"closest reachable vector is {dict(zip(SLICES, reachable, strict=True))}"
        )

    chosen: list[int] = []
    state = target_vector
    while parents[state] is not None:
        previous, index = parents[state]
        chosen.append(index)
        state = previous
    return sorted(chosen)


def split_benchmark(
    queries_path: Path,
    qrels_path: Path,
    out_path: Path,
    out_dir: Path,
    seed: int = 42,
    train_total: int = 65,
    train_counts: dict[str, int] | None = None,
) -> SplitResult:
    queries = load_queries(queries_path)
    qrels = load_qrels(qrels_path)
    query_ids = [query.query_id for query in queries]
    if len(query_ids) != len(set(query_ids)):
        raise ValueError("duplicate query_id in queries file")

    slice_by_query = {query.query_id: query.slice for query in queries}
    docs_by_query = relevance2_docs(queries, qrels)
    components = build_components(query_ids, docs_by_query)
    slice_counts = Counter(slice_by_query.values())
    target = train_counts or allocate_train_counts(dict(slice_counts), train_total)
    if set(target) != set(SLICES):
        raise ValueError(f"train_counts must cover exactly {SLICES}")
    if sum(target.values()) != train_total:
        raise ValueError(f"train_counts sum {sum(target.values())} != {train_total}")
    for name in SLICES:
        if target[name] > slice_counts.get(name, 0):
            raise ValueError(
                f"train_counts[{name!r}]={target[name]} exceeds available "
                f"{slice_counts.get(name, 0)}"
            )

    chosen = solve_component_assignment(components, slice_by_query, target, seed)
    train_ids = {query_id for index in chosen for query_id in components[index]}
    assignments = {
        query_id: ("train" if query_id in train_ids else "test") for query_id in query_ids
    }

    docs_train: set[str] = set()
    docs_test: set[str] = set()
    for query_id in query_ids:
        target_docs = docs_train if assignments[query_id] == "train" else docs_test
        target_docs.update(docs_by_query.get(query_id, set()))
    overlap = sorted(docs_train & docs_test)
    if overlap:
        raise ValueError(f"gold documents shared across split: {overlap[:10]}")

    train_rows = [row for row in queries if assignments[row.query_id] == "train"]
    test_rows = [row for row in queries if assignments[row.query_id] == "test"]
    train_path = out_dir / "queries_train.jsonl"
    test_path = out_dir / "queries_test.jsonl"
    write_jsonl(train_path, [row.model_dump() for row in train_rows])
    write_jsonl(test_path, [row.model_dump() for row in test_rows])

    train_slices = dict(Counter(row.slice for row in train_rows))
    test_slices = dict(Counter(row.slice for row in test_rows))
    mixed = sum(1 for component in components if len({slice_by_query[q] for q in component}) > 1)
    payload = {
        "version": "w3-query-split-v1",
        "seed": seed,
        "query_count": len(queries),
        "train_total": len(train_rows),
        "test_total": len(test_rows),
        "source": {
            "queries": str(queries_path).replace("\\", "/"),
            "queries_sha256": sha256_file(queries_path),
            "qrels": str(qrels_path).replace("\\", "/"),
            "qrels_sha256": sha256_file(qrels_path),
        },
        "slices": {
            name: {
                "total": slice_counts.get(name, 0),
                "train": train_slices.get(name, 0),
                "test": test_slices.get(name, 0),
            }
            for name in SLICES
        },
        "components": {
            "total": len(components),
            "train": len(chosen),
            "test": len(components) - len(chosen),
            "mixed_slice": mixed,
            "largest_train": [
                len(components[index])
                for index in sorted(chosen, key=lambda i: -len(components[i]))[:3]
            ],
        },
        "gold_docs": {
            "train": len(docs_train),
            "test": len(docs_test),
            "overlap": overlap,
        },
        "files": {
            "queries_train.jsonl": sha256_file(train_path),
            "queries_test.jsonl": sha256_file(test_path),
        },
        "assignments": assignments,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return SplitResult(
        queries=len(queries),
        train=len(train_rows),
        test=len(test_rows),
        assignments=assignments,
        train_slices=train_slices,
        test_slices=test_slices,
        components=len(components),
        train_components=len(chosen),
        mixed_slice_components=mixed,
        gold_docs_train=len(docs_train),
        gold_docs_test=len(docs_test),
        gold_doc_overlap=overlap,
        queries_sha256=sha256_file(queries_path),
        qrels_sha256=sha256_file(qrels_path),
        train_sha256=sha256_file(train_path),
        test_sha256=sha256_file(test_path),
    )
