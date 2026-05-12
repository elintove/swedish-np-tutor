import os
import re

from .env import load_dotenv
from .error_detector import ErrorDetector
from .exercise_generator import ExerciseGenerator
from .llm_client import BergetChatCompletionsClient
from .retrieval_module import RetrievalModule
from .state_manager import GrammarStateManager
from .tutor_generator import TutorGenerator
from .web_search import DuckDuckGoLiteSearchClient


_QUESTION_TOKEN_RE = re.compile(r"[A-Za-zÅÄÖåäöÉéÜü]+", re.UNICODE)


def _question_tokens(text: str) -> set[str]:
    return {
        m.group(0).lower()
        for m in _QUESTION_TOKEN_RE.finditer(text or "")
        if len(m.group(0)) > 2
    }


class SwedishNPTutor:
    def __init__(
        self,
        state_file: str = "data/state.json",
        *,
        api_key: str | None = None,
        model: str = "openai/gpt-oss-120b",
        use_llm: bool = True,
    ):
        load_dotenv()

        resolved_key = api_key
        if resolved_key is None:
            resolved_key = (
                os.environ.get("API_KEY")
                or os.environ.get("BERGET_API_KEY")
                or os.environ.get("OPENAI_API_KEY")
            )

        llm_client = None
        if use_llm and resolved_key:
            llm_client = BergetChatCompletionsClient(api_key=resolved_key, model=model)
        self.llm_client = llm_client

        self.web_search_client = DuckDuckGoLiteSearchClient()

        self.state_manager = GrammarStateManager(state_file)
        self.error_detector = ErrorDetector(llm_client=llm_client)
        self.retrieval_module = RetrievalModule()
        self.exercise_generator = ExerciseGenerator()
        self.tutor_generator = TutorGenerator(self.retrieval_module, llm_client=llm_client)

    def process_input(self, sentence: str):
        detection_result = self.error_detector.detect_errors(sentence)

        if not detection_result.errors:
            return "Great job! I couldn't find any errors in your noun phrases."

        primary_error = detection_result.errors[0]

        self.state_manager.update_mastery(primary_error.error_type, is_correct=False)
        mastery_level = self.state_manager.get_mastery_level(primary_error.error_type)

        exercise = self.exercise_generator.generate_exercise(
            primary_error.error_type,
            mastery_level,
            primary_error.target_np,
        )

        prior_errors = self.state_manager.get_topic_stats(primary_error.error_type).errors
        hint_level = "full" if prior_errors == 0 else ("short" if prior_errors == 1 else "cue")

        return self.tutor_generator.generate_response(
            primary_error,
            mastery_level,
            exercise,
            hint_level=hint_level,
        )

    def process_input_with_exercise(self, sentence: str) -> dict:
        """
        Like `process_input`, but also returns the exercise payload so a CLI can
        ask the user to answer it and update mastery.
        """
        detection_result = self.error_detector.detect_errors(sentence)

        if not detection_result.errors:
            return {
                "response": "Great job! I couldn't find any errors in your noun phrases.",
                "error_type": None,
                "exercise": None,
            }

        primary_error = detection_result.errors[0]

        prior_errors = self.state_manager.get_topic_stats(primary_error.error_type).errors
        hint_level = "full" if prior_errors == 0 else ("short" if prior_errors == 1 else "cue")

        self.state_manager.update_mastery(primary_error.error_type, is_correct=False)
        mastery_level = self.state_manager.get_mastery_level(primary_error.error_type)

        exercise = self.exercise_generator.generate_exercise(
            primary_error.error_type,
            mastery_level,
            primary_error.target_np,
        )

        response = self.tutor_generator.generate_response(
            primary_error,
            mastery_level,
            exercise,
            hint_level=hint_level,
        )

        return {
            "response": response,
            "error_type": primary_error.error_type,
            "exercise": exercise,
            "hint_level": hint_level,
        }

    def answer_question(
        self,
        question: str,
        *,
        mastery_level: str | None = None,
        include_web: bool = True,
    ) -> str:
        """
        Grammar Q&A mode. Answers in English and grounds the response in hybrid
        retrieval: local JSON grammar rules/examples plus optional web results.
        """
        q = question.strip()
        if not q:
            return "Ask me a Swedish noun phrase grammar question (e.g., en/ett, definiteness, adjectives)."

        level = mastery_level or "beginner"

        local_hits = self.retrieval_module.retrieve_for_question(q, mastery_level=level, k=6)
        top_topic = local_hits[0].error_type if local_hits else "definiteness_mismatch"
        retrieved = self.retrieval_module.retrieve(top_topic, level)

        web_results = []
        web_error = None
        if include_web and self.web_search_client is not None:
            try:
                web_results = self.web_search_client.search(q, max_results=4)
            except RuntimeError as error:
                web_error = str(error)

        hybrid_context = self._rank_question_context(q, local_hits, web_results)

        if self.llm_client is None:
            text = "### Hybrid retrieved context\n"
            for item in hybrid_context[:6]:
                text += f"- [{item['source']}] score={item['score']:.2f}: {item['text']}\n"
            if web_error:
                text += f"\nWeb retrieval note: {web_error}\n"
            text += f"\n### {retrieved.get('rule_name', top_topic)}\n{retrieved.get('explanation', '')}\n"
            mp = retrieved.get("minimal_pair")
            if mp:
                text += "\n### Minimal pair\n"
                text += f"Incorrect: {mp.get('incorrect')}\nCorrect: {mp.get('correct')}\nNote: {mp.get('note')}\n"
            return text.strip()

        system = (
            "You are a Swedish grammar tutor. Answer in English. "
            "Use the provided hybrid retrieval context. Prefer the local JSON grammar rules "
            "when they conflict with web results, and use web results only as supporting context. "
            "Be clear and give 2-4 short examples if helpful."
        )
        mp = retrieved.get("minimal_pair") or {}
        exs = retrieved.get("examples") or []
        ex0 = exs[0] if exs else {}
        context_lines = "\n".join(
            [
                f"- source={item['source']}, score={item['score']:.2f}, text={item['text']}"
                for item in hybrid_context[:6]
            ]
        )
        user = f"""
Question: {q}

Context:
- top_topic_from_local_ir: {top_topic}
- hybrid_retrieved_context:
{context_lines}
- web_retrieval_note: {web_error or "ok"}
- rule_name: {retrieved.get('rule_name')}
- explanation: {retrieved.get('explanation')}
- example_correct: {ex0.get('correct')}
- example_incorrect: {ex0.get('incorrect')}
- minimal_pair_incorrect: {mp.get('incorrect')}
- minimal_pair_correct: {mp.get('correct')}
- minimal_pair_note: {mp.get('note')}

Write the answer with these sections:
1) Direct answer (1-3 sentences)
2) Rule of thumb (bullets)
3) Examples (at least 2)
""".strip()

        return self.llm_client.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.3,
            max_tokens=600,
        )

    def _rank_question_context(self, question: str, local_hits, web_results) -> list[dict]:
        """
        Merge local grammar hits and web search results into one ranked context.
        Local hits keep their BM25 signal; web hits use rank plus token overlap.
        """
        q_tokens = _question_tokens(question)
        ranked: list[dict] = []

        max_local = max((h.score for h in local_hits), default=1.0) or 1.0
        for hit in local_hits:
            normalized_score = hit.score / max_local
            ranked.append(
                {
                    "source": f"local:{hit.kind}:{hit.error_type}",
                    "score": 1.0 + normalized_score,
                    "text": hit.text,
                }
            )

        for rank, result in enumerate(web_results, start=1):
            text = " ".join([result.title, result.snippet]).strip()
            tokens = _question_tokens(text)
            overlap = len(q_tokens & tokens) / max(1, len(q_tokens))
            rank_bonus = 1.0 / rank
            ranked.append(
                {
                    "source": "web",
                    "score": overlap + rank_bonus,
                    "text": f"{result.title}: {result.snippet} ({result.url})",
                }
            )

        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked

    def check_exercise_answer(self, error_type: str, user_answer: str, expected_answer: str):
        is_correct = user_answer.strip().lower() == expected_answer.strip().lower()
        self.state_manager.update_mastery(error_type, is_correct=is_correct)
        return is_correct
