# Adaptive Swedish Noun Phrase Tutor Agent

An AI-powered tutor for learning Swedish noun phrase grammar, specifically focusing on definiteness and articles.

## Features
- Error detection in Swedish noun phrases.
- Adaptive explanations based on learner mastery.
- Structured retrieval of grammar rules and minimal pairs.
- Dynamic exercise generation.

## Run the agent (LLM-backed)

1) Install dependencies:

```bash
pip install -r requirements.txt
```

2) Create a `.env` file in the project root:

```bash
API_KEY=your_berget_key_here
```

3) Run:

```bash
python SweNPAgent.py
```

The agent will use the `openai/gpt-oss-120b` model via Berget's chat-completions API. If no key is set, it will fall back to the built-in heuristic detector.

## Project Structure

swedish-np-tutor/
│
├── src/
│   ├── SweNPAgent.py
│   ├── llm_client.py
│   ├── retrieval_module.py
│   ├── memory_compactor.py
│   ├── env.py
│
├── grammar_db/
│   ├── rules.json
│   ├── examples.json
│   ├── minimal_pairs.json
│
├── data/
│   ├── session_log.jsonl
│   ├── learner_profile.md
│
├── report.tex
├── README.md
├── requirements.txt
└── .env.example

## Interaction style
- The agent **starts by asking you to translate an English NP into Swedish**.
- It then **reviews your translation**, explains any issues **in English**, and gives a short exercise.

## Modes
- **Learning mode** (default): **guided, level-based exercises** (the agent asks you to translate NPs appropriate for your level). It also uses **confusion-aware hinting**:
  - 1st time you make the same error type → full explanation
  - 2nd time → shorter hint
  - 3rd+ time → minimal cue
- **Free training mode**: you type any Swedish NP and get feedback + a targeted exercise.
- **Q&A mode**: ask grammar questions; the agent answers in English using retrieved rules/examples/minimal pairs as context.
- **Exam mode**: no hints, only **Correct/Incorrect** after each answer. Passing can promote your level.

### Commands
- `/learn`: switch to learning mode
- `/free`: switch to free training mode
- `/question` (or `/q`): switch to Q&A mode (type `/back` to leave)
- `/exam`: take the exam
- `/status`: show attempts/errors/mastery per topic

## Compacted long-term memory
The agent appends events to `data/session_log.jsonl` and periodically compacts them into a short summary at `data/learner_profile.md` (level, recurring errors, recommended focus).

## Limitations

- Retrieval is purely lexical (BM25), not semantic
- No fine-tuned Swedish grammar model
- LLM dependency for high-quality explanations
- Limited coverage of complex noun phrase structures
