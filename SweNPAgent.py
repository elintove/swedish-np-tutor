import os

from src.agent import SwedishNPTutor
from src.env import load_dotenv
from src.llm_client import BergetChatCompletionsClient
from src.error_detector import NPError
from src.memory_compactor import append_event, maybe_compact, write_profile


def main() -> None:
    load_dotenv()

    # Accept a few common env var names.
    api_key = (
        os.environ.get("API_KEY")
        or os.environ.get("BERGET_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )

    if not api_key:
        print(
            "Missing API key. Set API_KEY (or BERGET_API_KEY) in your environment or a .env file.\n"
            "Continuing in heuristic fallback mode (no LLM calls)."
        )

    # We still construct the tutor agent for later stages (after placement),
    # but the placement quiz itself is specialized for en/ett.
    agent = SwedishNPTutor(
        api_key=api_key,
        model="openai/gpt-oss-120b",
        use_llm=bool(api_key),
    )
    llm = BergetChatCompletionsClient(api_key=api_key, model="openai/gpt-oss-120b") if api_key else None

    print(
        "Hejhej!\n"
        "\n"
        "I'm your Swedish NP Tutor Agent. I will help you master the art of the Swedish en/ett distinction.\n"
        "Let's begin by finding out which level you're at. I'll give you some English noun phrases.\n"
        "You'll translate them into Swedish.\n" 
        "\n"
        "Psst...! Just a tip: Remember that about 75-80% of all Swedish words are utrum (\"en\"-words)!"
    )

    print("\nType 'exit' to quit at any time.\n")

    quiz_items = [
        # Keep these mostly about the article choice (en/ett), with simple modifiers.
        {"en": "a big house", "targets": ["ett stort hus", "ett stort hus."]},
        {"en": "a small dog", "targets": ["en liten hund", "en liten hund."]},
        {"en": "an apple", "targets": ["ett äpple", "ett äpple."]},
    ]

    def grade_with_llm(english_np: str, user_swedish: str) -> tuple[bool, str]:
        """
        Returns (is_correct, feedback_in_english).
        The judgement is primarily about en/ett (utrum/neutrum) for the head noun.
        """
        system = (
            "You are an expert Swedish teacher. "
            "You grade translations of English noun phrases into Swedish. "
            "Focus on the en/ett (utrum/neutrum) distinction for the head noun and article usage. "
            "Write feedback in English. "
            "Return exactly two lines:\n"
            "LINE 1: CORRECT or INCORRECT\n"
            "LINE 2: A brief explanation in English (1-3 sentences)."
        )
        user = (
            f'English NP: "{english_np}"\n'
            f'Student Swedish: "{user_swedish}"\n\n'
            "If incorrect, explain the specific issue and give one correct Swedish version."
        )
        text = llm.chat([{"role": "system", "content": system}, {"role": "user", "content": user}], temperature=0.0, max_tokens=220)
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            return False, "I couldn't parse the grading output. Try again with a short noun phrase like: 'en hund' / 'ett hus'."
        verdict = lines[0].upper()
        is_correct = verdict.startswith("CORRECT")
        feedback = lines[1] if len(lines) >= 2 else ("Looks good." if is_correct else "Not quite—check whether the noun is an en-word or ett-word.")
        return is_correct, feedback

    def grade_heuristic(item: dict, user_swedish: str) -> tuple[bool, str]:
        # Simple fallback: compare normalized strings against acceptable targets.
        norm = " ".join(user_swedish.strip().lower().replace("’", "'").split())
        targets = {" ".join(t.lower().split()) for t in item["targets"]}
        if norm in targets:
            return True, "Correct."
        # Give a targeted hint focusing on en/ett.
        if item["en"] == "a big house":
            return False, "INCORRECT. 'house' is 'hus' (an ett-word), so it should be 'ett stort hus'."
        if item["en"] == "a small dog":
            return False, "INCORRECT. 'dog' is 'hund' (an en-word), so it should be 'en liten hund'."
        return False, "INCORRECT. 'apple' is 'äpple' (an ett-word), so it should be 'ett äpple'."

    errors = 0
    for idx, item in enumerate(quiz_items, start=1):
        print(f"[{idx}/3] Translate into Swedish: {item['en']}")
        ans = input("You: ").strip()
        if ans.lower() in {"exit", "quit"}:
            return
        if not ans:
            ans = ""

        if llm is not None:
            is_correct, feedback = grade_with_llm(item["en"], ans)
        else:
            is_correct, feedback = grade_heuristic(item, ans)

        if not is_correct:
            errors += 1
            print("\nAgent:\n" + feedback + "\n")
        else:
            print("\nAgent:\n" + feedback + "\n")

    if errors == 0:
        level = "advanced"
    elif errors == 1:
        level = "intermediate"
    else:
        level = "beginner"

    print(f"Placement result: **{level.upper()}** (errors: {errors}/3)\n")
    append_event(
        "data/session_log.jsonl",
        {"type": "placement", "errors": errors, "total": 3, "level": level},
    )
    maybe_compact(
        log_path="data/session_log.jsonl",
        profile_path="data/learner_profile.md",
        state_manager=agent.state_manager,
        current_level=level,
        every_n_events=10,
    )

    if level == "beginner":
        plan = (
            "### Study plan (Beginner)\n"
            "- Build a starter list of high-frequency ett-words (because most words are en-words).\n"
            "- Practice 'a/an + noun' → 'en/ett + noun' with 10 items/day.\n"
            "- Add adjectives: 'en liten X' vs 'ett litet Y' (notice adjective endings).\n"
            "- Weekly check-in: redo a 10-item quiz and track accuracy.\n"
        )
    elif level == "intermediate":
        plan = (
            "### Study plan (Intermediate)\n"
            "- Focus on the most common ett-words and pattern groups (e.g., many -ande/-ende nouns are en).\n"
            "- Practice with modifiers: adjective agreement ('liten/litet') + en/ett.\n"
            "- Add definites: 'huset' vs 'bilen' and keep the gender consistent.\n"
            "- Weekly check-in: mixed quiz (indefinite + definite + adjectives).\n"
        )
    else:
        plan = (
            "### Study plan (Advanced)\n"
            "- Consolidate: keep a short 'exceptions' list (ett-words you still hesitate on).\n"
            "- Practice in sentences: choose article + adjective agreement under time pressure.\n"
            "- Add compound nouns: keep gender from the head noun.\n"
            "- Weekly check-in: short writing task with self-correction.\n"
        )

    print(plan)
    print(
        "Modes:\n"
        "- Type `/learn` for learning mode (guided, level-based exercises).\n"
        "- Type `/free` for free training mode (type any NP; get feedback).\n"
        "- Type `/question` to ask grammar questions (Q&A mode).\n"
        "- Type `/exam` to take a short exam (no hints, just correct/incorrect).\n"
        "- Type `/status` to see your current mastery stats.\n"
        "- Type `exit` to quit.\n"
    )

    def run_exam(current_level: str) -> None:
        """
        Exam mode: no hints, only correctness after each answer.
        Pass thresholds:
        - beginner: 4/5 correct -> promote to intermediate
        - intermediate: 4/5 correct -> promote to advanced
        - advanced: 5/5 correct -> "master"
        """
        if llm is None:
            print("Exam mode needs an API key (LLM grading). Set API_KEY in your .env.\n")
            return

        if current_level == "beginner":
            pass_needed = 4
        elif current_level == "intermediate":
            pass_needed = 4
        else:
            pass_needed = 5

        exam_items = [
            {"en": "a big house"},
            {"en": "a small dog"},
            {"en": "an apple"},
            {"en": "a red book"},
            {"en": "a small table"},
        ]

        print("Exam mode. Translate each NP into Swedish. No hints will be given.\n")
        correct = 0
        for i, it in enumerate(exam_items, start=1):
            print(f"[{i}/5] {it['en']}")
            ans = input("You: ").strip()
            if ans.lower() in {"exit", "quit"}:
                return

            is_correct, _feedback = grade_with_llm(it["en"], ans)
            if is_correct:
                correct += 1
                print("\nAgent:\nCorrect.\n")
            else:
                print("\nAgent:\nIncorrect.\n")

        print(f"Exam score: {correct}/5\n")
        passed = correct >= pass_needed
        append_event(
            "data/session_log.jsonl",
            {
                "type": "exam_result",
                "level_before": current_level,
                "correct": correct,
                "total": 5,
                "passed": passed,
            },
        )
        maybe_compact(
            log_path="data/session_log.jsonl",
            profile_path="data/learner_profile.md",
            state_manager=agent.state_manager,
            current_level=level,
            every_n_events=10,
        )

        if passed:
            if current_level == "beginner":
                level = "intermediate"
                print("Result: PASS. Congratulations — you graduate to **INTERMEDIATE**.\n")
            elif current_level == "intermediate":
                level = "advanced"
                print("Result: PASS. Congratulations — you graduate to **ADVANCED**.\n")
            else:
                print("Result: PASS. Congratulations, you are officially the master of Swedish noun phrases.\n")
        else:
            print("Result: NOT PASSED. Stay in learning mode and try again later.\n")

    def learn_pool(for_level: str) -> list[dict]:
        """
        Returns a list of English NP prompts suitable for the learner level.
        These are intended to practice en/ett + (optionally) adjective agreement/definiteness.
        """
        if for_level == "beginner":
            return [
                {"en": "a house"},
                {"en": "a dog"},
                {"en": "an apple"},
                {"en": "a table"},
                {"en": "a book"},
            ]
        if for_level == "intermediate":
            return [
                {"en": "a big house"},
                {"en": "a small dog"},
                {"en": "a red book"},
                {"en": "a new table"},
                {"en": "a small apple"},
            ]
        # advanced
        return [
            {"en": "the big car"},
            {"en": "the old house"},
            {"en": "the red book"},
            {"en": "the new apple"},
            {"en": "the small dog"},
        ]

    def run_learn_round(current_level: str) -> None:
        """
        Learning mode: the agent asks one exercise at a time.
        - If the user is incorrect, give explanation (confusion-aware) and then continue.
        - If correct, reinforce briefly and continue.
        """
        pool = learn_pool(current_level)
        if not pool:
            print("No exercises available for this level.\n")
            return

        # rotate deterministically through the list
        if not hasattr(run_learn_round, "_idx"):
            run_learn_round._idx = 0  # type: ignore[attr-defined]
        idx = run_learn_round._idx % len(pool)  # type: ignore[attr-defined]
        run_learn_round._idx += 1  # type: ignore[attr-defined]

        item = pool[idx]
        print(f"Exercise ({current_level}): Translate into Swedish: {item['en']}")
        ans = input("You: ").strip()
        if ans.lower() in {"exit", "quit"}:
            raise SystemExit
        if ans.startswith("/"):
            # allow switching modes even while learning is auto-running
            nonlocal mode
            cmd = ans.lower().strip()
            if cmd == "/free":
                mode = "free"
                print("\nAgent:\nFree training mode enabled. Type any Swedish NP for feedback.\n")
                return
            if cmd in {"/question", "/q"}:
                mode = "question"
                print("\nAgent:\nQ&A mode enabled. Ask a Swedish NP grammar question in English. I will use local grammar retrieval plus web results (type /back to return).\n")
                return
            if cmd == "/exam":
                run_exam(level)
                return
            if cmd == "/status":
                topics = agent.state_manager.state.topics
                print("\nAgent:\nYour current stats:")
                for k, v in topics.items():
                    print(f"- {k}: attempts={v.attempts}, errors={v.errors}, mastery={v.mastery:.2f}")
                print("")
                return
            if cmd == "/learn":
                print("\nAgent:\nYou're already in learning mode.\n")
                return
            print("\nAgent:\nUnknown command. Try /free, /question, /exam, or /status.\n")
            return
        if not ans:
            ans = ""

        # Prefer LLM grading for translation exercises; fallback to tutor's heuristic detection if no key.
        nonlocal learn_correct_count
        if llm is not None:
            is_correct, feedback = grade_with_llm(item["en"], ans)
            if is_correct:
                learn_correct_count += 1
                print("\nAgent:\nCorrect.\n")
                append_event(
                    "data/session_log.jsonl",
                    {"type": "learn_exercise", "level": current_level, "prompt": item["en"], "answer": ans, "correct": True},
                )
            else:
                print("\nAgent:\n" + feedback + "\n")
                append_event(
                    "data/session_log.jsonl",
                    {"type": "learn_exercise", "level": current_level, "prompt": item["en"], "answer": ans, "correct": False},
                )
                # Create tutor feedback from the translation context so we don't falsely say "Great job".
                system = (
                    "You are an expert Swedish teacher. "
                    "Given an English NP and a student's Swedish attempt, identify the most relevant NP error type "
                    "from this closed set: definiteness_mismatch, double_definiteness, article_omission, adjective_agreement. "
                    "Return ONLY valid JSON for a single error."
                )
                user = f"""
English NP: {item['en']!r}
Student Swedish: {ans!r}

Return ONLY JSON matching this schema exactly:
{{
  "error_type": "definiteness_mismatch" | "double_definiteness" | "article_omission" | "adjective_agreement",
  "target_np": string,
  "correct_form": string,
  "explanation_brief": string,
  "confidence": number between 0 and 1
}}
Rules:
- explanation_brief must be in English.
- correct_form should be a good Swedish translation of the English NP.
- target_np should be the student phrase (or the wrong sub-phrase).
""".strip()
                err_json = llm.chat(
                    [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    temperature=0.0,
                    max_tokens=250,
                )
                err = NPError.model_validate_json(err_json)

                prior_errors = agent.state_manager.get_topic_stats(err.error_type).errors
                hint_level = "full" if prior_errors == 0 else ("short" if prior_errors == 1 else "cue")
                agent.state_manager.update_mastery(err.error_type, is_correct=False)
                mastery_level = agent.state_manager.get_mastery_level(err.error_type)
                exercise = agent.exercise_generator.generate_exercise(err.error_type, mastery_level, err.target_np)
                tutor_text = agent.tutor_generator.generate_response(
                    err,
                    mastery_level,
                    exercise,
                    hint_level=hint_level,
                )
                print("Agent (tutor):\n", tutor_text, "\n")
        else:
            # Without the LLM, we can still provide tutor feedback if we detect anything,
            # but correctness of the translation isn't reliably gradeable.
            turn = agent.process_input_with_exercise(ans)
            print("\nAgent:\n", turn["response"], "\n")
            append_event(
                "data/session_log.jsonl",
                {"type": "learn_exercise", "level": current_level, "prompt": item["en"], "answer": ans, "correct": None},
            )

        if learn_correct_count > 0 and learn_correct_count % 10 == 0:
            print(
                "Agent:\n"
                "Nice work — you've answered 10 learning exercises correctly. "
                "You might be ready to try `/exam` to graduate and get closer to becoming the master of Swedish noun phrases.\n"
            )
        maybe_compact(
            log_path="data/session_log.jsonl",
            profile_path="data/learner_profile.md",
            state_manager=agent.state_manager,
            current_level=level,
            every_n_events=10,
        )

    def run_free_training(np_text: str) -> None:
        """
        Free training mode: user types any NP and gets feedback + an exercise.
        """
        turn = agent.process_input_with_exercise(np_text)
        print("\nAgent:\n", turn["response"], "\n")
        append_event(
            "data/session_log.jsonl",
            {"type": "free_training", "input": np_text, "error_type": turn.get("error_type"), "hint_level": turn.get("hint_level")},
        )
        maybe_compact(
            log_path="data/session_log.jsonl",
            profile_path="data/learner_profile.md",
            state_manager=agent.state_manager,
            current_level=level,
            every_n_events=10,
        )

        exercise = turn.get("exercise") or None
        if exercise and exercise.get("answer") and exercise.get("answer") != "...":
            ans = input("Your answer to the exercise: ").strip()
            if ans.lower() in {"exit", "quit"}:
                raise SystemExit
            is_correct = agent.check_exercise_answer(
                turn["error_type"],
                ans,
                str(exercise.get("answer")),
            )
            if is_correct:
                print("\nAgent:\nCorrect.\n")
            else:
                print(f"\nAgent:\nNot quite. Expected: {exercise.get('answer')}\n")

    mode = "learn"
    learn_correct_count = 0
    print(f"Learning mode is enabled. Your current level is **{level.upper()}**.\n")
    print("Type /free to type your own noun phrases, or /question for grammar Q&A.\n")

    while True:
        if mode == "learn":
            try:
                run_learn_round(level)
            except SystemExit:
                break
            continue

        user_input = input("User: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        if user_input.startswith("/"):
            cmd = user_input.lower().strip()
            if cmd == "/back" and mode == "question":
                mode = "free"
                print("\nAgent:\nLeaving Q&A mode.\n")
                continue
            if cmd == "/learn":
                mode = "learn"
                print("\nAgent:\nLearning mode enabled (guided exercises).\n")
                continue
            if cmd == "/free":
                mode = "free"
                print("\nAgent:\nFree training mode enabled. Type any Swedish NP for feedback.\n")
                continue
            if cmd in {"/question", "/q"}:
                mode = "question"
                print("\nAgent:\nQ&A mode enabled. Ask a Swedish NP grammar question in English. I will use local grammar retrieval plus web results (type /back to return).\n")
                continue
            if cmd == "/exam":
                mode = "exam"
                run_exam(level)
                mode = "learn"
                continue
            if cmd == "/status":
                topics = agent.state_manager.state.topics
                print("\nAgent:\nYour current stats:")
                for k, v in topics.items():
                    print(f"- {k}: attempts={v.attempts}, errors={v.errors}, mastery={v.mastery:.2f}")
                print("")
                continue
            print("\nAgent:\nUnknown command. Try /learn, /free, /question, /exam, or /status.\n")
            continue

        if mode == "question":
            answer = agent.answer_question(user_input, mastery_level=level)
            print("\nAgent:\n", answer, "\n")
            append_event(
                "data/session_log.jsonl",
                {"type": "question", "level": level, "q": user_input},
            )
            maybe_compact(
                log_path="data/session_log.jsonl",
                profile_path="data/learner_profile.md",
                state_manager=agent.state_manager,
                current_level=level,
                every_n_events=10,
            )
        else:
            run_free_training(user_input)

    # Final compaction on exit
    write_profile(
        log_path="data/session_log.jsonl",
        profile_path="data/learner_profile.md",
        state_manager=agent.state_manager,
        current_level=level,
    )


if __name__ == "__main__":
    main()
