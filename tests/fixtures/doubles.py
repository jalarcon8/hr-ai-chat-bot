"""Deterministic, dependency-light model doubles for F001 tests."""

import hashlib
import re

import numpy as np

_TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


class DeterministicEmbedder:
    model_id = "test-deterministic-embedder-v1"
    tokenizer_id = model_id
    dimensions = 128

    def tokenize_with_offsets(self, text: str) -> list[tuple[int, int]]:
        return [(match.start(), match.end()) for match in _TOKEN.finditer(text)]

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.dimensions), dtype=np.float32)
        for row, text in enumerate(texts):
            for token in re.findall(r"\w+", text.casefold()):
                slot = int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:4], "big")
                vectors[row, slot % self.dimensions] += 1.0 if slot & 1 else -1.0
        return vectors


class EvidenceGenerator:
    def __init__(self, status: str = "answered", claim_prefix: str = "Evidence supports this.") -> None:
        self.status = status
        self.claim_prefix = claim_prefix
        self.calls = 0

    def generate(self, question, evidence):
        self.calls += 1
        if self.status == "unsupported":
            return {
                "status": "unsupported",
                "claims": [],
                "limitations": ["The retrieved passages do not answer this question."],
            }
        claim = {
            "text": self.claim_prefix,
            "citation_ids": [item.chunk_id for item in evidence],
            "kind": "policy_fact",
        }
        limitations = ["Some details are not established."] if self.status in {"partial", "conflicting"} else []
        return {"status": self.status, "claims": [claim], "limitations": limitations}
