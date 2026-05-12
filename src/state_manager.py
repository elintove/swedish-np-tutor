import json
import os
from pydantic import BaseModel, Field
from typing import Dict

class GrammarTopicState(BaseModel):
    mastery: float = 0.0
    attempts: int = 0
    errors: int = 0

class LearnerState(BaseModel):
    topics: Dict[str, GrammarTopicState] = Field(default_factory=lambda: {
        "definiteness_mismatch": GrammarTopicState(),
        "double_definiteness": GrammarTopicState(),
        "article_omission": GrammarTopicState(),
        "adjective_agreement": GrammarTopicState()
    })

class GrammarStateManager:
    def __init__(self, state_file: str = "data/state.json"):
        self.state_file = state_file
        self.state = self.load_state()

    def load_state(self) -> LearnerState:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    return LearnerState(**data)
            except (json.JSONDecodeError, ValueError):
                return LearnerState()
        return LearnerState()

    def save_state(self):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            f.write(self.state.model_dump_json(indent=2))

    def update_mastery(self, topic: str, is_correct: bool):
        if topic not in self.state.topics:
            self.state.topics[topic] = GrammarTopicState()
        
        topic_state = self.state.topics[topic]
        topic_state.attempts += 1
        if not is_correct:
            topic_state.errors += 1
        
        # Simple mastery calculation: (successes / attempts) with some smoothing
        successes = topic_state.attempts - topic_state.errors
        topic_state.mastery = successes / topic_state.attempts
        
        self.save_state()

    def get_mastery_level(self, topic: str) -> str:
        mastery = self.state.topics.get(topic, GrammarTopicState()).mastery
        if mastery >= 0.7:
            return "advanced"
        return "beginner"

    def get_topic_stats(self, topic: str) -> GrammarTopicState:
        """
        Returns current stats for a topic (attempts, errors, mastery).
        """
        return self.state.topics.get(topic, GrammarTopicState())
