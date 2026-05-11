# 📘 swedish-np-tutor

An AI-powered tutoring system for Swedish noun phrase grammar learning, combining retrieval-augmented grammar knowledge, large language models, and adaptive learner modeling.

Developed for **Information Retrieval (5LN712), Uppsala University**.

---

## 🔗 Links

- GitHub repository: https://github.com/elintove/swedish-np-tutor  
- (optional) Hugging Face demo: *add link here if deployed*  
- (optional) Dataset / resources: *add link if published*

---

## 📌 Project Overview

This project implements an **adaptive grammar tutoring agent** for Swedish noun phrases.

The system focuses on:

- definiteness (en/ett + suffixation)
- adjective agreement
- noun phrase structure
- error-driven learning

The problem is formulated as an **interactive NLP tutoring task**, where the system:

- evaluates user input
- detects grammatical errors
- retrieves relevant grammar knowledge
- generates explanations via an LLM
- adapts difficulty based on learner history

---

## 🧠 System Architecture

The system consists of three main components:

### 1. Language Model Backend
- Model: `openai/gpt-oss-120b`
- Role:
  - generates explanations
  - produces feedback
  - drives tutoring dialogue
  - answers grammar questions

### 2. Retrieval System (IR Module)
- Method: BM25 lexical retrieval
- Source corpus:
  - grammar rules
  - example sentences
  - minimal pairs

Used for:
- grounding explanations
- Q&A mode responses
- error-specific feedback

### 3. Memory & Learner Modeling
- Session logging: `session_log.jsonl`
- Long-term memory: `learner_profile.md`
- Compaction module summarizes:
  - learner level
  - recurring error types
  - recommended focus areas

---

## 📊 Dataset / Knowledge Base

The system uses a structured grammar knowledge base rather than a classical dataset.

### Grammar Database (`grammar_db/`)

- **rules.json**
  - formal grammar rules for noun phrase formation

- **examples.json**
  - correct and incorrect NP constructions

- **minimal_pairs.json**
  - contrastive examples highlighting grammatical differences

These resources function as a **retrieval corpus for the IR component**.

---

## 🤖 Models

### Embedding / Retrieval Model
(Not generative, used for similarity ranking if extended)

- BM25 lexical retrieval (baseline IR method)

### Language Model
- `openai/gpt-oss-120b`
- Used for:
  - explanation generation
  - tutoring dialogue
  - error correction reasoning

---

## 🧪 Interaction Modes

### 1. Learning Mode (`/learn`)
- structured translation exercises
- adaptive difficulty progression
- guided feedback

### 2. Free Training (`/free`)
- user submits any Swedish NP
- system provides correction + follow-up exercise

### 3. Question Answering (`/question`)
- grammar questions in natural language
- retrieval-augmented answers

### 4. Exam Mode (`/exam`)
- no hints
- strict evaluation (Correct / Incorrect only)
- used for level progression

---

## 🔁 Adaptive Tutoring Strategy

The system implements **error-aware scaffolding**:

| Error frequency | Feedback type |
|----------------|--------------|
| 1st occurrence | Full explanation + example |
| 2nd occurrence | Short hint |
| 3rd+ occurrence | Minimal cue |

This simulates pedagogical fading of support.

---

## 💾 Data

### Session Logs