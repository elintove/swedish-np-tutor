import json
import os
import math
import re
from dataclasses import dataclass
from typing import Dict, List, Any, Iterable, Tuple
import random

_WORD_RE = re.compile(r"[A-Za-zÅÄÖåäöÉéÜüÖöÄäÅå]+", re.UNICODE)


def _tokenize(text: str) -> List[str]:
    return [m.group(0).lower() for m in _WORD_RE.finditer(text or "")]


@dataclass(frozen=True)
class RetrievalHit:
    """
    A single retrieved 'document' hit from the grammar DB.
    """

    score: float
    error_type: str
    kind: str  # rule | example | minimal_pair
    text: str
    payload: Dict[str, Any]


class RetrievalModule:
    def __init__(self, db_path: str = "grammar_db/"):
        self.db_path = db_path
        self.rules = self._load_json("rules.json")
        self.examples = self._load_json("examples.json")
        self.minimal_pairs = self._load_json("minimal_pairs.json")
        self._bm25 = _BM25Index(self._iter_documents())

    def _load_json(self, filename: str) -> Any:
        path = os.path.join(self.db_path, filename)
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        
        # Return list for examples and minimal pairs, dict for rules
        if filename == "rules.json":
            return {}
        return []

    def _iter_documents(self) -> Iterable[Tuple[str, str, Dict[str, Any]]]:
        """
        Yields (error_type, kind, payload) items to be indexed for lexical retrieval.
        """
        # Rules
        if isinstance(self.rules, dict):
            for et, rule in self.rules.items():
                if not isinstance(rule, dict):
                    continue
                payload = {"rule": rule}
                yield et, "rule", payload

        # Examples
        if isinstance(self.examples, list):
            for ex in self.examples:
                if not isinstance(ex, dict):
                    continue
                et = ex.get("type")
                if not et:
                    continue
                payload = {"example": ex}
                yield et, "example", payload

        # Minimal pairs
        if isinstance(self.minimal_pairs, list):
            for mp in self.minimal_pairs:
                if not isinstance(mp, dict):
                    continue
                et = mp.get("type")
                if not et:
                    continue
                pairs = mp.get("pairs") or []
                if not isinstance(pairs, list):
                    continue
                for pair in pairs:
                    if not isinstance(pair, dict):
                        continue
                    payload = {"minimal_pair": pair}
                    yield et, "minimal_pair", payload

    def retrieve(self, error_type: str, mastery_level: str) -> Dict[str, Any]:
        """
        Novelty 1: Error-Conditioned Retrieval
        retrieval_key = error_type + mastery_level
        """
        rule = self.rules.get(error_type, {})
        level_explanation = rule.get("levels", {}).get(mastery_level, rule.get("explanation", ""))
        
        # Filter examples by error type
        relevant_examples_all = [ex for ex in self.examples if ex.get("type") == error_type]
        relevant_examples = [random.choice(relevant_examples_all)] if relevant_examples_all else []
        
        # Filter minimal pairs by error type
        relevant_pairs = [mp for mp in self.minimal_pairs if mp.get("type") == error_type]
        all_pairs: List[Dict[str, Any]] = []
        for mp in relevant_pairs:
            pairs = mp.get("pairs") or []
            if isinstance(pairs, list):
                all_pairs.extend([p for p in pairs if isinstance(p, dict)])
        pair = random.choice(all_pairs) if all_pairs else None

        return {
            "rule_name": rule.get("name", error_type),
            "explanation": level_explanation,
            "examples": relevant_examples,
            "minimal_pair": pair
        }

    def retrieve_for_question(
        self,
        question: str,
        *,
        mastery_level: str = "beginner",
        k: int = 5,
    ) -> List[RetrievalHit]:
        """
        Lexical retrieval for Q&A. Returns top-k hits across rules/examples/minimal pairs.
        """
        hits = self._bm25.search(question, k=k)
        out: List[RetrievalHit] = []
        for score, meta in hits:
            error_type, kind, payload = meta
            # Provide a compact text for prompt grounding and for debugging output.
            if kind == "rule":
                rule = payload.get("rule") or {}
                text = f"{rule.get('name', error_type)}: {rule.get('levels', {}).get(mastery_level, rule.get('explanation',''))}"
            elif kind == "example":
                ex = payload.get("example") or {}
                text = f"Example: ✔ {ex.get('correct')} / ❌ {ex.get('incorrect')} ({ex.get('context','')})"
            else:
                mp = payload.get("minimal_pair") or {}
                text = f"Minimal pair: ❌ {mp.get('incorrect')} / ✔ {mp.get('correct')} (Note: {mp.get('note','')})"
            out.append(
                RetrievalHit(
                    score=float(score),
                    error_type=str(error_type),
                    kind=str(kind),
                    text=text,
                    payload=payload,
                )
            )
        return out


class _BM25Index:
    """
    Minimal BM25 implementation for small local corpora.
    Stores (tokens, meta) for each document.
    """

    def __init__(self, docs: Iterable[Tuple[str, str, Dict[str, Any]]], *, k1: float = 1.2, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs: List[Tuple[List[str], Tuple[str, str, Dict[str, Any]]]] = []
        self.df: Dict[str, int] = {}
        self.doc_lens: List[int] = []

        for error_type, kind, payload in docs:
            text = self._payload_to_text(error_type, kind, payload)
            tokens = _tokenize(text)
            meta = (error_type, kind, payload)
            self.docs.append((tokens, meta))
            self.doc_lens.append(len(tokens))
            seen = set(tokens)
            for t in seen:
                self.df[t] = self.df.get(t, 0) + 1

        self.N = len(self.docs)
        self.avgdl = (sum(self.doc_lens) / self.N) if self.N else 0.0

    def _payload_to_text(self, error_type: str, kind: str, payload: Dict[str, Any]) -> str:
        if kind == "rule":
            rule = payload.get("rule") or {}
            levels = rule.get("levels") or {}
            parts = [
                str(rule.get("name", error_type)),
                str(rule.get("explanation", "")),
                str(levels.get("beginner", "")),
                str(levels.get("advanced", "")),
            ]
            return " ".join(p for p in parts if p)
        if kind == "example":
            ex = payload.get("example") or {}
            return " ".join(
                [
                    str(ex.get("context", "")),
                    str(ex.get("correct", "")),
                    str(ex.get("incorrect", "")),
                ]
            )
        mp = payload.get("minimal_pair") or {}
        return " ".join([str(mp.get("incorrect", "")), str(mp.get("correct", "")), str(mp.get("note", ""))])

    def _idf(self, term: str) -> float:
        # BM25+ style IDF with smoothing.
        df = self.df.get(term, 0)
        return math.log(1.0 + (self.N - df + 0.5) / (df + 0.5)) if self.N else 0.0

    def search(self, query: str, *, k: int = 5) -> List[Tuple[float, Tuple[str, str, Dict[str, Any]]]]:
        q_tokens = _tokenize(query)
        if not q_tokens or not self.docs:
            return []

        q_counts: Dict[str, int] = {}
        for t in q_tokens:
            q_counts[t] = q_counts.get(t, 0) + 1

        results: List[Tuple[float, Tuple[str, str, Dict[str, Any]]]] = []
        for doc_tokens, meta in self.docs:
            if not doc_tokens:
                continue
            tf: Dict[str, int] = {}
            for t in doc_tokens:
                tf[t] = tf.get(t, 0) + 1

            dl = len(doc_tokens)
            denom_norm = self.k1 * (1 - self.b + self.b * (dl / self.avgdl)) if self.avgdl else self.k1

            score = 0.0
            for term in q_counts.keys():
                f = tf.get(term, 0)
                if f <= 0:
                    continue
                idf = self._idf(term)
                score += idf * (f * (self.k1 + 1)) / (f + denom_norm)

            if score > 0:
                results.append((score, meta))

        results.sort(key=lambda x: x[0], reverse=True)
        return results[: max(1, k)]
