from typing import Dict, Any, List
from .error_detector import NPError
from .retrieval_module import RetrievalModule

class TutorGenerator:
    def __init__(self, retrieval_module: RetrievalModule, llm_client=None):
        self.retrieval_module = retrieval_module
        self.llm_client = llm_client

    def generate_response(
        self,
        error: NPError,
        mastery_level: str,
        exercise: Dict[str, Any],
        *,
        hint_level: str = "full",
    ) -> str:
        retrieved_data = self.retrieval_module.retrieve(error.error_type, mastery_level)

        if self.llm_client is not None:
            try:
                return self._generate_llm_response(error, mastery_level, exercise, retrieved_data, hint_level=hint_level)
            except Exception:
                # Fall back to template response if the LLM fails.
                pass
        
        response = f"I noticed an error in your noun phrase: '{error.target_np}'.\n"
        response += f"Correct form: {error.correct_form}\n\n"
        
        if hint_level == "full":
            response += f"### Grammar Rule: {retrieved_data['rule_name']}\n"
            response += f"{retrieved_data['explanation']}\n\n"
        elif hint_level == "short":
            response += f"### Hint\n"
            response += f"{retrieved_data['rule_name']}: {error.explanation_brief}\n\n"
        elif hint_level == "cue":
            response += "### Minimal cue\n"
            response += "Check definiteness/article agreement and noun gender (en/ett).\n\n"
        else:
            response += "### Minimal cue\n"
            response += "Check definiteness/article agreement and noun gender (en/ett).\n\n"
        
        if hint_level != "cue" and retrieved_data['minimal_pair']:
            response += "### Contrastive Example (Minimal Pair)\n"
            response += f"❌ {retrieved_data['minimal_pair']['incorrect']}\n"
            response += f"✔ {retrieved_data['minimal_pair']['correct']}\n"
            response += f"Note: {retrieved_data['minimal_pair']['note']}\n\n"
        
        response += "### Practice Exercise\n"
        response += f"{exercise['task']}\n"
        
        return response

    def _generate_llm_response(
        self,
        error: NPError,
        mastery_level: str,
        exercise: Dict[str, Any],
        retrieved_data: Dict[str, Any],
        *,
        hint_level: str,
    ) -> str:
        system = (
            "You are an adaptive Swedish noun phrase tutor. "
            "Be concise, supportive, and focus on the learner's specific mistake. "
            "Write all explanations in English."
        )
        minimal_pair = retrieved_data.get("minimal_pair")
        minimal_pair_text = ""
        if minimal_pair:
            minimal_pair_text = (
                f"- Incorrect: {minimal_pair.get('incorrect')}\n"
                f"- Correct: {minimal_pair.get('correct')}\n"
                f"- Note: {minimal_pair.get('note')}\n"
            )

        user = f"""
Learner mastery level: {mastery_level}
Hint level (confusion-aware): {hint_level}

Detected NP error:
- type: {error.error_type}
- target_np: {error.target_np}
- correct_form: {error.correct_form}
- brief_explanation: {error.explanation_brief}

Retrieved rule:
- name: {retrieved_data.get('rule_name')}
- explanation: {retrieved_data.get('explanation')}

Minimal pair (if any):
{minimal_pair_text if minimal_pair_text else "(none)"}

Exercise to give the learner:
- task: {exercise.get('task')}

Write the tutor response with these sections exactly:
1) What to change (1-2 sentences)
2) Why
3) Contrastive example (only if minimal pair exists AND hint_level is not 'cue')
4) Practice exercise (repeat the task verbatim)

Confusion-aware rules:
- If hint_level is 'full': give a full, clear explanation (3-6 sentences in section 2).
- If hint_level is 'short': keep section 2 to 1-2 sentences (a hint, not a lecture).
- If hint_level is 'cue': section 2 should be only one short cue (max 10 words), e.g. "Check definiteness agreement."
""".strip()

        return self.llm_client.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.4,
            max_tokens=700,
        )
