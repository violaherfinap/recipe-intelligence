"""Build the cleaned document corpus, passages, split, and manifests."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path

from .schema import Doc, Passage
from .split import assign_splits, split_summary

SECTION_ORDER = ("ingredients", "directions")
HEADING_ORDER = (("ingredients", "Ingredients"), ("directions", "Directions"))

TokenOffsets = Callable[[str], list[tuple[int, int]]]


def read_jsonl(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on line {line_number} of {path}") from exc


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(text: str) -> str:
    """Normalise whitespace without changing the wording of the source."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_sections(body: str) -> dict[str, str]:
    """Split a recipe body on ``## Heading`` markers."""
    body = body.replace("\r\n", "\n").replace("\r", "\n")
    parts = re.split(r"(?m)^##\s+(.+?)\s*$", body)
    sections: dict[str, str] = {}
    for index in range(1, len(parts) - 1, 2):
        heading = parts[index].strip().lower()
        sections[heading] = parts[index + 1]
    return sections


def section_lines(content: str) -> list[str]:
    return [line.strip() for line in content.split("\n") if line.strip()]


def _build_text_clean(sections: dict[str, str]) -> tuple[str, dict[str, tuple[int, int]]]:
    parts: list[str] = []
    spans: dict[str, tuple[int, int]] = {}
    cursor = 0

    for section, heading in HEADING_ORDER:
        content = sections.get(section, "")
        if not content:
            continue
        header = f"## {heading}\n"
        parts.append(header)
        cursor += len(header)
        start = cursor
        parts.append(content)
        cursor += len(content)
        spans[section] = (start, cursor)
        parts.append("\n\n")
        cursor += 2

    return "".join(parts).rstrip(), spans


def make_doc(
    row: dict,
    commit_sha: str,
    doc_id: str,
    doc_slug: str,
    collection: str = "ye-old-american",
) -> Doc:
    title = normalize_text(str(row.get("title") or ""))
    body = str(row.get("body") or "")
    raw_slug = str(row.get("slug") or "").strip()

    if not title:
        raise ValueError("missing title")
    if not body.strip():
        raise ValueError("missing body")
    if not raw_slug:
        raise ValueError("missing slug")

    raw_sections = parse_sections(body)
    ingredients = normalize_text(raw_sections.get("ingredients", ""))
    directions = normalize_text(raw_sections.get("directions", ""))
    if not ingredients and not directions:
        raise ValueError("missing Ingredients and Directions sections")

    year_value = row.get("source_year")
    if year_value is None or str(year_value).strip() == "":
        raise ValueError("missing source_year")
    try:
        source_year = int(str(year_value).strip())
    except ValueError as exc:
        raise ValueError(f"invalid source_year: {year_value!r}") from exc

    text_clean, _ = _build_text_clean({"ingredients": ingredients, "directions": directions})
    sections = {
        "ingredients": section_lines(ingredients),
        "directions": section_lines(directions),
    }

    return Doc(
        doc_id=doc_id,
        title=title,
        slug=doc_slug,
        collection=str(row.get("collection") or collection),
        culture=str(row.get("culture") or ""),
        author=str(row.get("author") or ""),
        source_title=str(row.get("source_title") or ""),
        source_url=str(row.get("source_url") or ""),
        source_year=source_year,
        license=str(row.get("license") or ""),
        sections=sections,
        text_clean=text_clean,
        sha256=sha256_text(text_clean),
        commit_sha=commit_sha,
        split=None,
    )


def parse_recipes(
    rows: Iterable[dict],
    commit_sha: str,
    collection: str = "ye-old-american",
) -> tuple[list[Doc], list[dict]]:
    docs: list[Doc] = []
    errors: list[dict] = []
    slug_counts: dict[str, int] = defaultdict(int)

    for index, row in enumerate(rows):
        try:
            raw_slug = str(row.get("slug") or "").strip()
            if not raw_slug:
                raise ValueError("missing slug")
            occurrence = slug_counts[raw_slug]
            slug_counts[raw_slug] += 1
            doc_slug = raw_slug if occurrence == 0 else f"{raw_slug}-{occurrence + 1}"
            doc_id = f"{collection}:{doc_slug}"
            docs.append(make_doc(row, commit_sha, doc_id, doc_slug, collection))
        except Exception as exc:  # noqa: BLE001 - report and keep the rest of the corpus
            errors.append({"row": index, "error": str(exc)})

    docs.sort(key=lambda doc: doc.doc_id)
    return docs, errors


def _dedup_hash(doc: Doc) -> str:
    return sha256_text(doc.title + "\n" + doc.text_clean)


def simhash64(text: str) -> int:
    """64-bit SimHash over word 3-grams."""
    tokens = re.findall(r"[a-z0-9']+", text.lower())
    if not tokens:
        return 0
    shingles = tokens if len(tokens) < 3 else [" ".join(tokens[i : i + 3]) for i in range(len(tokens) - 2)]

    weights = [0] * 64
    for shingle in shingles:
        digest = hashlib.blake2b(shingle.encode("utf-8"), digest_size=8).digest()
        hashed = int.from_bytes(digest, "big")
        for bit in range(64):
            weights[bit] += 1 if (hashed >> bit) & 1 else -1

    fingerprint = 0
    for bit in range(64):
        if weights[bit] > 0:
            fingerprint |= 1 << bit
    return fingerprint


def hamming64(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def deduplicate(docs: Iterable[Doc], max_hamming: int = 3) -> tuple[list[Doc], list[dict]]:
    """Find exact and near-duplicate recipes **within the same book**.

    Near-duplicates are detected with 64-bit SimHash and four 16-bit bands so
    the comparison stays close to linear. Duplicates across different books are
    deliberately kept, as required by the plan. The first doc in doc_id order
    wins inside each book.
    """
    groups: dict[str, list[Doc]] = defaultdict(list)
    for doc in sorted(docs, key=lambda item: item.doc_id):
        # ``source_title`` identifies the book; fall back to the collection.
        groups[doc.source_title or doc.collection].append(doc)

    kept: list[Doc] = []
    removed: list[dict] = []

    for book in sorted(groups):
        exact_seen: dict[str, str] = {}
        bands: dict[tuple[int, int], list[int]] = defaultdict(list)
        book_kept: list[tuple[Doc, int]] = []

        for doc in groups[book]:
            exact_hash = _dedup_hash(doc)
            if exact_hash in exact_seen:
                removed.append(
                    {
                        "doc_id": doc.doc_id,
                        "duplicate_of": exact_seen[exact_hash],
                        "kind": "exact",
                        "book": book,
                    }
                )
                continue

            fingerprint = simhash64(doc.title + "\n" + doc.text_clean)
            candidate_indexes: set[int] = set()
            for band in range(4):
                key = (band, (fingerprint >> (16 * band)) & 0xFFFF)
                candidate_indexes.update(bands.get(key, ()))

            duplicate_of = None
            for candidate_index in sorted(candidate_indexes):
                if hamming64(fingerprint, book_kept[candidate_index][1]) <= max_hamming:
                    duplicate_of = book_kept[candidate_index][0].doc_id
                    break

            if duplicate_of is not None:
                removed.append(
                    {
                        "doc_id": doc.doc_id,
                        "duplicate_of": duplicate_of,
                        "kind": "near",
                        "book": book,
                    }
                )
                continue

            exact_seen[exact_hash] = doc.doc_id
            kept_index = len(book_kept)
            book_kept.append((doc, fingerprint))
            for band in range(4):
                key = (band, (fingerprint >> (16 * band)) & 0xFFFF)
                bands[key].append(kept_index)

        kept.extend(doc for doc, _ in book_kept)

    kept.sort(key=lambda doc: doc.doc_id)
    removed.sort(key=lambda entry: entry["doc_id"])
    return kept, removed


def split_clean_sections(text_clean: str) -> dict[str, tuple[str, int]]:
    """Return section -> (content, absolute start offset in text_clean)."""
    matches = list(re.finditer(r"(?m)^##\s+(.+?)\s*$", text_clean))
    sections: dict[str, tuple[str, int]] = {}
    for index, match in enumerate(matches):
        heading = match.group(1).strip().lower()
        start = match.end()
        while start < len(text_clean) and text_clean[start] == "\n":
            start += 1
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text_clean)
        content = text_clean[start:end].rstrip()
        sections[heading] = (content, start)
    return sections


def chunk_offsets(
    offsets: list[tuple[int, int]],
    text: str,
    max_tokens: int = 350,
    overlap: int = 40,
) -> list[dict]:
    """Slice token offsets into overlapping windows and return character spans."""
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    if overlap < 0 or overlap >= max_tokens:
        raise ValueError("overlap must be in [0, max_tokens)")

    token_count = len(offsets)
    if token_count == 0:
        return []

    chunks: list[dict] = []
    start = 0
    while start < token_count:
        end = min(start + max_tokens, token_count)
        char_start = offsets[start][0]
        char_end = offsets[end - 1][1]
        chunks.append(
            {
                "token_start": start,
                "token_end": end,
                "char_start": char_start,
                "char_end": char_end,
                "text": text[char_start:char_end],
            }
        )
        if end == token_count:
            break
        start = end - overlap

    return chunks


def _section_passages(
    doc: Doc,
    token_offsets: TokenOffsets,
    max_tokens: int,
    overlap: int,
) -> list[Passage]:
    sections = split_clean_sections(doc.text_clean)
    passages: list[Passage] = []

    for section in SECTION_ORDER:
        if section not in sections:
            continue
        content, absolute_start = sections[section]
        offsets = token_offsets(content)
        if not offsets:
            continue
        for idx, chunk in enumerate(chunk_offsets(offsets, content, max_tokens, overlap)):
            passages.append(
                Passage(
                    passage_id=f"{doc.doc_id}#{section}#{idx}",
                    doc_id=doc.doc_id,
                    section=section,
                    idx=idx,
                    text=chunk["text"],
                    char_start=absolute_start + chunk["char_start"],
                    char_end=absolute_start + chunk["char_end"],
                    token_count=chunk["token_end"] - chunk["token_start"],
                    source_year=doc.source_year,
                    source_title=doc.source_title,
                    split=doc.split,
                )
            )

    return passages


def _fixed_passages(
    doc: Doc,
    token_offsets: TokenOffsets,
    max_tokens: int,
    overlap: int,
) -> list[Passage]:
    """Fixed-size windows over the whole cleaned document (no heading awareness)."""
    content = doc.text_clean
    offsets = token_offsets(content)
    if not offsets:
        return []
    passages: list[Passage] = []
    for idx, chunk in enumerate(chunk_offsets(offsets, content, max_tokens, overlap)):
        passages.append(
            Passage(
                passage_id=f"{doc.doc_id}#fixed#{idx}",
                doc_id=doc.doc_id,
                section="fixed",
                idx=idx,
                text=chunk["text"],
                char_start=chunk["char_start"],
                char_end=chunk["char_end"],
                token_count=chunk["token_end"] - chunk["token_start"],
                source_year=doc.source_year,
                source_title=doc.source_title,
                split=doc.split,
            )
        )
    return passages


def _hierarchical_passages(
    doc: Doc,
    token_offsets: TokenOffsets,
    max_tokens: int,
    overlap: int,
) -> list[Passage]:
    """Recipe summary (title + ingredients) plus one or more passages per step.

    The summary is a derived passage: its text includes the recipe title, while
    its character span points at the ingredients section in ``text_clean``.
    Step passages are exact substrings of the directions section.
    """
    sections = split_clean_sections(doc.text_clean)
    passages: list[Passage] = []

    if "ingredients" in sections:
        ingredients, ingredients_start = sections["ingredients"]
        summary_text = f"{doc.title}\n{ingredients}" if ingredients else doc.title
        offsets = token_offsets(summary_text)
        for idx, chunk in enumerate(
            chunk_offsets(offsets, summary_text, max_tokens, overlap)
        ):
            passages.append(
                Passage(
                    passage_id=f"{doc.doc_id}#summary#{idx}",
                    doc_id=doc.doc_id,
                    section="summary",
                    idx=idx,
                    text=chunk["text"],
                    char_start=ingredients_start,
                    char_end=ingredients_start + len(ingredients),
                    token_count=chunk["token_end"] - chunk["token_start"],
                    source_year=doc.source_year,
                    source_title=doc.source_title,
                    split=doc.split,
                )
            )

    if "directions" in sections:
        directions, directions_start = sections["directions"]
        cursor = 0
        step_index = 0
        for line in directions.split("\n"):
            line = line.strip()
            if not line:
                continue
            line_start = directions.find(line, cursor)
            if line_start < 0:
                continue
            cursor = line_start + len(line)
            offsets = token_offsets(line)
            if not offsets:
                continue
            for chunk in chunk_offsets(offsets, line, max_tokens, overlap):
                absolute_start = directions_start + line_start + chunk["char_start"]
                passages.append(
                    Passage(
                        passage_id=f"{doc.doc_id}#step#{step_index}",
                        doc_id=doc.doc_id,
                        section="step",
                        idx=step_index,
                        text=chunk["text"],
                        char_start=absolute_start,
                        char_end=absolute_start + chunk["char_end"] - chunk["char_start"],
                        token_count=chunk["token_end"] - chunk["token_start"],
                        source_year=doc.source_year,
                        source_title=doc.source_title,
                        split=doc.split,
                    )
                )
                step_index += 1

    return passages


def build_passages(
    doc: Doc,
    token_offsets: TokenOffsets,
    max_tokens: int = 350,
    overlap: int = 40,
    mode: str = "section",
) -> list[Passage]:
    """Build passages for one of the three A1 chunking modes."""
    if doc.split is None:
        raise ValueError(f"doc {doc.doc_id} has no split assigned")

    if mode == "section":
        return _section_passages(doc, token_offsets, max_tokens, overlap)
    if mode == "fixed":
        return _fixed_passages(doc, token_offsets, max_tokens, overlap)
    if mode == "hierarchical":
        return _hierarchical_passages(doc, token_offsets, max_tokens, overlap)
    raise ValueError(f"unknown chunking mode: {mode}")


def write_source_register(path: Path, docs: Iterable[Doc]) -> None:
    columns = [
        "doc_id",
        "title",
        "author",
        "source_title",
        "source_year",
        "source_url",
        "license",
        "sha256",
        "commit_sha",
        "split",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for doc in docs:
            writer.writerow({column: getattr(doc, column) for column in columns})


def _file_hashes(out_dir: Path, names: Iterable[str]) -> dict[str, str]:
    return {name: sha256_file(out_dir / name) for name in names if (out_dir / name).exists()}


def build_corpus(
    raw_path: Path,
    commit_file: Path,
    out_dir: Path,
    token_offsets: TokenOffsets,
    tokenizer_name: str = "BAAI/bge-small-en-v1.5",
    max_tokens: int = 350,
    overlap: int = 40,
    seed: int = 42,
    dedup: bool = True,
) -> dict:
    commit_sha = commit_file.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        raise ValueError(f"invalid corpus commit SHA in {commit_file}: {commit_sha!r}")

    rows = list(read_jsonl(raw_path))
    all_docs, errors = parse_recipes(rows, commit_sha=commit_sha)

    removed: list[dict] = []
    if dedup:
        canonical_docs, removed = deduplicate(all_docs)
    else:
        canonical_docs = list(all_docs)

    assignments = assign_splits(all_docs, seed=seed)
    all_docs = [doc.model_copy(update={"split": assignments[doc.doc_id]}) for doc in all_docs]
    canonical_ids = {doc.doc_id for doc in canonical_docs}
    canonical_docs = [
        doc.model_copy(update={"split": assignments[doc.doc_id]})
        for doc in all_docs
        if doc.doc_id in canonical_ids
    ]

    passages: list[Passage] = []
    for doc in canonical_docs:
        passages.extend(build_passages(doc, token_offsets, max_tokens=max_tokens, overlap=overlap))

    out_dir.mkdir(parents=True, exist_ok=True)
    docs_path = out_dir / "docs.jsonl"
    passages_path = out_dir / "passages.jsonl"
    register_path = out_dir / "source_register.csv"
    split_path = out_dir / "split.json"
    dedup_path = out_dir / "dedup_log.jsonl"

    write_jsonl(docs_path, [doc.model_dump() for doc in all_docs])
    write_jsonl(passages_path, [passage.model_dump() for passage in passages])
    write_source_register(register_path, all_docs)
    split_payload = split_summary(assignments, all_docs, seed=seed)
    write_json(split_path, split_payload)
    if removed:
        write_jsonl(dedup_path, removed)

    file_names = ["docs.jsonl", "passages.jsonl", "source_register.csv", "split.json"]
    if removed:
        file_names.append("dedup_log.jsonl")
    file_hashes = _file_hashes(out_dir, file_names)

    manifest = {
        "corpus": {
            "collection": "ye-old-american",
            "source": "https://github.com/AdamBouhmad/open-recipe-archive",
            "commit_sha": commit_sha,
            "raw_count": len(rows),
        },
        "counts": {
            "docs_raw": len(rows),
            "docs": len(all_docs),
            "docs_indexed": len(canonical_docs),
            "duplicates_removed": len(removed),
            "passages": len(passages),
            "errors": len(errors),
        },
        "dedup": {
            "enabled": dedup,
            "mode": "log_only_excluded_from_index",
            "scope": "same source_title (book)",
            "max_hamming": 3,
            "log": "dedup_log.jsonl" if removed else None,
        },
        "chunking": {
            "mode": "section",
            "max_tokens": max_tokens,
            "overlap": overlap,
            "tokenizer": tokenizer_name,
        },
        "split": {
            "seed": seed,
            "ratios": split_payload["ratios"],
            "counts": split_payload["counts"],
            "by_year": split_payload["by_year"],
        },
        "files": file_hashes,
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "errors": errors[:50],
    }
    manifest_path = out_dir / "manifest.json"
    write_json(manifest_path, manifest)

    hash_lines = [f"{digest}  {name}" for name, digest in file_hashes.items()]
    (out_dir / "manifest.sha256").write_text("\n".join(hash_lines) + "\n", encoding="utf-8")

    return {
        "manifest": manifest,
        "paths": {
            "docs": str(docs_path),
            "passages": str(passages_path),
            "source_register": str(register_path),
            "split": str(split_path),
            "manifest": str(manifest_path),
        },
    }
