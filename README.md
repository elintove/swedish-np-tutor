# Adaptive Swedish Noun Phrase Tutor Agent

An AI-powered tutor for learning Swedish noun phrase grammar, specifically focusing on definiteness and articles.

## Features
- Error detection in Swedish noun phrases.
- Adaptive explanations based on learner mastery.
- Structured retrieval of grammar rules and minimal pairs.
- Dynamic exercise generation.

## Run the agent (LLM-backed)
1) Create a `.env` file in the project root:

```bash
API_KEY=your_berget_key_here
```

2) Run:

```bash
python SweNPAgent.py
```

The agent will use the `openai/gpt-oss-120b` model via Berget's chat-completions API. If no key is set, it will fall back to the built-in heuristic detector.

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
