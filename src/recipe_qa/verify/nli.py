"""NLI scoring for claim verification."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

DEFAULT_NLI_MODEL = "cross-encoder/nli-deberta-v3-base"


@dataclass(frozen=True)
class NliScores:
    entailment: float
    contradiction: float
    neutral: float


Scorer = Callable[[str, str], NliScores]


def scores_from_probs(labels: dict[str, int], probs: list[float]) -> NliScores:
    values = {label.lower(): 0.0 for label in labels}
    for label, index in labels.items():
        if 0 <= index < len(probs):
            values[label.lower()] = float(probs[index])
    missing = {"entailment", "contradiction"} - set(values)
    if missing:
        raise ValueError(f"NLI label mapping is missing: {sorted(missing)}")
    return NliScores(
        entailment=values["entailment"],
        contradiction=values["contradiction"],
        neutral=values.get("neutral", 0.0),
    )


class NliVerifier:
    """Cross-encoder NLI model that scores (premise, hypothesis) pairs."""

    def __init__(
        self,
        model_name: str = DEFAULT_NLI_MODEL,
        device: str = "cpu",
        max_length: int = 512,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.max_length = max_length
        self._tokenizer = None
        self._model = None
        self._labels: dict[str, int] | None = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        torch.set_num_threads(8)
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        self._model.to(self.device)
        self._model.eval()
        self._labels = {
            str(label).lower(): int(index)
            for index, label in self._model.config.id2label.items()
        }
        scores_from_probs(self._labels, [0.0] * len(self._labels))

    def score(self, premise: str, hypothesis: str) -> NliScores:
        if not premise.strip() or not hypothesis.strip():
            return NliScores(entailment=0.0, contradiction=0.0, neutral=1.0)

        import torch

        self._ensure_loaded()
        assert self._tokenizer is not None
        assert self._model is not None
        assert self._labels is not None

        inputs = self._tokenizer(
            premise,
            hypothesis,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with torch.inference_mode():
            logits = self._model(**inputs).logits[0]
            probs = torch.softmax(logits, dim=-1).tolist()
        return scores_from_probs(self._labels, probs)
