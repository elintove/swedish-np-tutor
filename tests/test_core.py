import os

from src.agent import SwedishNPTutor
from src.error_detector import ErrorDetector
from src.retrieval_module import RetrievalModule
from src.state_manager import GrammarStateManager
from src.web_search import DuckDuckGoLiteSearchClient, WebSearchResult


def test_state_manager():
    state_file = "tests/test_state.json"
    if os.path.exists(state_file):
        os.remove(state_file)

    sm = GrammarStateManager(state_file)
    sm.update_mastery("definiteness_mismatch", is_correct=True)
    assert sm.state.topics["definiteness_mismatch"].attempts == 1
    assert sm.state.topics["definiteness_mismatch"].mastery == 1.0

    sm.update_mastery("definiteness_mismatch", is_correct=False)
    assert sm.state.topics["definiteness_mismatch"].attempts == 2
    assert sm.state.topics["definiteness_mismatch"].mastery == 0.5

    os.remove(state_file)


def test_error_detector():
    ed = ErrorDetector()
    res = ed.detect_errors("Jag har en stora bilen")
    assert len(res.errors) > 0
    assert res.errors[0].error_type == "double_definiteness"


def test_retrieval_module():
    rm = RetrievalModule()
    data = rm.retrieve("definiteness_mismatch", "beginner")
    assert "explanation" in data
    assert data["rule_name"] == "Definiteness Mismatch"


def test_tutor_agent_smoke():
    state_file = "tests/smoke_state.json"
    if os.path.exists(state_file):
        os.remove(state_file)

    tutor = SwedishNPTutor(state_file)
    response = tutor.process_input("Det ar en bilen")
    assert "definiteness_mismatch" in response.lower() or "noticed an error" in response.lower()

    if os.path.exists(state_file):
        os.remove(state_file)


def test_web_search_uses_no_key_fallback():
    tutor = SwedishNPTutor("tests/no_key_web_state.json", use_llm=False)
    assert isinstance(tutor.web_search_client, DuckDuckGoLiteSearchClient)

    if os.path.exists("tests/no_key_web_state.json"):
        os.remove("tests/no_key_web_state.json")


def test_question_mode_merges_local_and_web_context():
    class MockSearchClient:
        def search(self, query, *, max_results=5):
            return [
                WebSearchResult(
                    title="Swedish articles en and ett",
                    url="https://example.com/en-ett",
                    snippet="Swedish nouns use en or ett articles depending on gender.",
                )
            ]

    state_file = "tests/hybrid_state.json"
    if os.path.exists(state_file):
        os.remove(state_file)

    tutor = SwedishNPTutor(state_file, use_llm=False)
    tutor.web_search_client = MockSearchClient()

    response = tutor.answer_question("How do I choose en or ett?", mastery_level="beginner")
    assert "Hybrid retrieved context" in response
    assert "local:" in response
    assert "Swedish articles en and ett" in response

    if os.path.exists(state_file):
        os.remove(state_file)
