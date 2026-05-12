from typing import List, Optional
from pydantic import BaseModel
import json

class NPError(BaseModel):
    error_type: str
    target_np: str
    correct_form: str
    explanation_brief: str
    confidence: float

class ErrorDetectionResult(BaseModel):
    sentence: str
    errors: List[NPError]

class ErrorDetector:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.error_categories = [
            "definiteness_mismatch",
            "double_definiteness",
            "article_omission",
            "adjective_agreement"
        ]

    def detect_errors(self, sentence: str) -> ErrorDetectionResult:
        # Prefer LLM if configured; fall back to heuristics if it fails.
        if self.llm_client is not None:
            try:
                llm_result = self._get_llm_detection(sentence)
                if llm_result is not None:
                    return llm_result
            except Exception:
                # Keep the agent working even if the LLM is unavailable.
                pass
        
        errors = []
        
        # Heuristic rules for common errors mentioned in design
        if "en stora bilen" in sentence.lower():
            errors.append(NPError(
                error_type="double_definiteness",
                target_np="en stora bilen",
                correct_form="den stora bilen",
                explanation_brief="When an adjective is used with a definite noun, use 'den/det/de' instead of 'en/ett'.",
                confidence=0.95
            ))
        
        if "en bilen" in sentence.lower():
            errors.append(NPError(
                error_type="definiteness_mismatch",
                target_np="en bilen",
                correct_form="en bil",
                explanation_brief="You used an indefinite article with a definite noun suffix.",
                confidence=0.95
            ))

        if "jag har hund" in sentence.lower() and "jag har en hund" not in sentence.lower():
             errors.append(NPError(
                error_type="article_omission",
                target_np="hund",
                correct_form="en hund",
                explanation_brief="Singular countable nouns usually need an article.",
                confidence=0.85
            ))

        return ErrorDetectionResult(sentence=sentence, errors=errors)

    def _get_llm_detection(self, sentence: str) -> ErrorDetectionResult:
        """
        Uses the configured chat-completions client to return a structured result.
        """
        system = (
            "You are a Swedish grammar tutor. "
            "You detect noun phrase (NP) errors in Swedish sentences and return ONLY valid JSON. "
            "All explanations must be written in English."
        )
        user = f"""
Analyze the following Swedish sentence for Noun Phrase (NP) errors:
{sentence!r}

Focus on these error types ONLY:
- definiteness_mismatch
- double_definiteness
- article_omission
- adjective_agreement

Return ONLY JSON matching this schema exactly:
{{
  "sentence": string,
  "errors": [
    {{
      "error_type": one of the four types above,
      "target_np": string,
      "correct_form": string,
      "explanation_brief": string,
      "confidence": number between 0 and 1
    }}
  ]
}}

Rules:
- If there are no NP errors, return an empty list for "errors".
- Do not include any extra keys.
- Do not wrap the JSON in markdown fences.
""".strip()

        content = self.llm_client.chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.0,
            max_tokens=700,
        )
        data = json.loads(content)
        return ErrorDetectionResult(**data)
