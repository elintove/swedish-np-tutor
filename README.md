# Swedish NP Tutor

An AI-powered tutoring system for Swedish noun phrase grammar learning, combining retrieval-augmented grammar knowledge, large language models, and adaptive learner modeling.

Developed for **Information Retrieval (5LN712), Uppsala University**.

## Links

- GitHub repository: https://github.com/elintove/swedish-np-tutor
- Hugging Face demo: add link here if deployed
- Dataset/resources: structured grammar database in `grammar_db/`

## Project Overview

This project implements an adaptive grammar tutoring agent for Swedish noun phrases.

The system focuses on:

- definiteness, including `en/ett` and suffixation
- adjective agreement
- noun phrase structure
- error-driven learning

The task is framed as an interactive NLP tutoring problem. The agent:

- evaluates learner input
- detects grammatical errors
- retrieves relevant grammar knowledge
- generates explanations with an LLM when an API key is available
- adapts feedback based on learner history

## System Architecture

The system consists of three main components.

### 1. Language Model Backend

The LLM backend uses Berget's OpenAI-compatible chat completions API.

- Model: `openai/gpt-oss-120b`
- Client: `src/llm_client.py`
- Environment loading: `src/env.py`

The LLM is used for:

- explanation generation
- tutoring dialogue
- grammar-question answering
- translation grading
- structured error correction reasoning

If no API key is provided, the agent falls back to built-in heuristic behavior where possible.

### 2. Retrieval System

The project includes a retrieval module for grounding explanations in explicit grammar knowledge.

- Local retrieval method: BM25-style lexical retrieval
- Implementation: `src/retrieval_module.py`
- Local source corpus:
  - `grammar_db/rules.json`
  - `grammar_db/examples.json`
  - `grammar_db/minimal_pairs.json`

For question answering, the agent uses hybrid retrieval:

- local BM25-ranked grammar hits from the JSON files
- no-key DuckDuckGo Lite web snippets from `src/web_search.py`
- merged ranking based on BM25 scores, web result rank, and token overlap

The local grammar database is treated as authoritative if web snippets disagree.

### 3. Memory and Learner Modeling

The agent tracks learner performance over time.

- State manager: `src/state_manager.py`
- Session log: `data/session_log.jsonl`
- Long-term profile: `data/learner_profile.md`
- Memory compaction: `src/memory_compactor.py`

The compaction module summarizes:

- learner level
- recurring error types
- recommended focus areas

Generated learner files are ignored by Git so personal session history is not uploaded.

## Knowledge Base

The project uses a structured grammar knowledge base rather than a traditional dataset.

### `grammar_db/rules.json`

Formal explanations of Swedish noun phrase grammar topics, including beginner-friendly and advanced descriptions.

### `grammar_db/examples.json`

Correct and incorrect noun phrase examples used for retrieval and feedback.

### `grammar_db/minimal_pairs.json`

Contrastive pairs that highlight specific grammatical differences, such as incorrect definiteness or adjective agreement.

Together, these files function as the retrieval corpus for the IR component.

## Interaction Modes

### Learning Mode (`/learn`)

The default guided mode. The agent presents level-appropriate English noun phrases for the learner to translate into Swedish.

Features:

- structured translation exercises
- adaptive difficulty progression
- guided feedback
- suggestions to try the exam after repeated correct answers

### Free Training (`/free`)

The learner can submit any Swedish noun phrase.

The agent:

- checks the phrase
- detects likely NP errors
- explains the issue in English
- gives a targeted follow-up exercise

### Question Answering (`/question`)

The learner can ask natural-language grammar questions.

Example:

```text
Why is "en bilen" wrong?
```

The agent answers using hybrid retrieval:

- local grammar rules, examples, and minimal pairs
- DuckDuckGo Lite web results
- LLM synthesis grounded in the retrieved context

There is no separate `/web` mode; web retrieval is only used inside question answering.

### Exam Mode (`/exam`)

Exam mode gives a short translation quiz with no hints.

Features:

- strict `Correct` / `Incorrect` feedback
- pass thresholds for level progression
- promotion from beginner to intermediate, and intermediate to advanced

### Status (`/status`)

Shows attempts, errors, and mastery scores for each tracked grammar topic.

## Adaptive Tutoring Strategy

The system implements error-aware scaffolding:

| Error frequency | Feedback type |
| --- | --- |
| 1st occurrence | Full explanation + example |
| 2nd occurrence | Short hint |
| 3rd+ occurrence | Minimal cue |

This simulates pedagogical fading of support: the learner receives more help at first, then gradually gets shorter cues as the same error type repeats.

## Installation

Clone or download the repository, then install the Python dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```bash
API_KEY=your_berget_key_here
```

Do not commit your real `.env` file. Use `.env.example` as the template.

## Running the Agent

Start the command-line tutor with:

```bash
python SweNPAgent.py
```

If `API_KEY` is not set, the agent will continue in fallback mode with reduced LLM functionality.

## Project Structure

```text
swedish-np-tutor/
├── SweNPAgent.py
├── README.md
├── README2.md
├── requirements.txt
├── .env.example
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── agent.py
│   ├── env.py
│   ├── error_detector.py
│   ├── evaluate.py
│   ├── exercise_generator.py
│   ├── llm_client.py
│   ├── memory_compactor.py
│   ├── retrieval_module.py
│   ├── state_manager.py
│   ├── tutor_generator.py
│   └── web_search.py
├── grammar_db/
│   ├── rules.json
│   ├── examples.json
│   └── minimal_pairs.json
├── tests/
│   └── test_core.py
└── data/
    └── .gitkeep
```

## Files Not Uploaded

The following should stay local and are ignored by `.gitignore`:

- `.env`
- `.venv/`
- `.vscode/`
- `__pycache__/`
- `data/state.json`
- `data/session_log.jsonl`
- `data/learner_profile.md`

## Testing

Run tests with:

```bash
pytest
```

The tests cover the state manager, error detector, retrieval module, tutor smoke behavior, and hybrid question retrieval with mocked web results.
