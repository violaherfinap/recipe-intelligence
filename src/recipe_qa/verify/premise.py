from __future__ import annotations

import re

_SUFFIX_RE = re.compile(r"-\d+$")


def recipe_title(doc_id: str) -> str:
    slug = _SUFFIX_RE.sub("", doc_id.split(":", 1)[-1])
    return slug.replace("-", " ")


def premise_text(passage: dict) -> str:
    doc_id = str(passage.get("doc_id", ""))
    data: list[str] = []
    if doc_id:
        data.append(recipe_title(doc_id))
    title = str(passage.get("source_title") or "")
    year = passage.get("source_year")
    if title:
        data.append(f"{title} ({year})" if year else title)
    text = str(passage.get("text", ""))
    if not data:
        return text
    return f"{'. '.join(data)}. {text}"
