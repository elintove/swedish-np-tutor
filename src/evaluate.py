import sys
import os
from typing import List, Dict

# Add current directory to path
sys.path.append(os.getcwd())

from src.agent import SwedishNPTutor
from src.error_detector import ErrorDetector

def technical_evaluation():
    print("--- Technical Evaluation ---")
    ed = ErrorDetector()
    test_cases = [
        ("Jag ser en bilen", "definiteness_mismatch"),
        ("Här är en stora bilen", "double_definiteness"),
        ("Jag har hund", "article_omission"),
        ("Bilen är röd", None) # Correct
    ]
    
    correct_detections = 0
    for sentence, expected_error in test_cases:
        res = ed.detect_errors(sentence)
        detected_types = [e.error_type for e in res.errors]
        
        if expected_error is None:
            if not detected_types:
                correct_detections += 1
                print(f"PASS: '{sentence}' correctly identified as error-free.")
            else:
                print(f"FAIL: '{sentence}' falsely identified with errors {detected_types}")
        else:
            if expected_error in detected_types:
                correct_detections += 1
                print(f"PASS: '{sentence}' correctly identified as {expected_error}")
            else:
                print(f"FAIL: '{sentence}' failed to identify {expected_error}")
    
    accuracy = correct_detections / len(test_cases)
    print(f"Detection Accuracy: {accuracy:.2f}\n")

def pedagogical_evaluation():
    print("--- Pedagogical Evaluation (Simulation) ---")
    state_file = "data/eval_state.json"
    if os.path.exists(state_file):
        os.remove(state_file)
        
    tutor = SwedishNPTutor(state_file)
    topic = "double_definiteness"
    
    print(f"Initial mastery: {tutor.state_manager.state.topics[topic].mastery}")
    
    # Simulate learner making mistakes
    print("Simulating 3 errors...")
    for _ in range(3):
        tutor.process_input("en stora bilen")
    
    print(f"Mastery after errors: {tutor.state_manager.state.topics[topic].mastery}")
    print(f"Level: {tutor.state_manager.get_mastery_level(topic)}")
    
    # Simulate learner getting it right
    print("Simulating 7 correct answers...")
    for _ in range(7):
        tutor.check_exercise_answer(topic, "den", "den")
    
    print(f"Final mastery: {tutor.state_manager.state.topics[topic].mastery}")
    print(f"Level: {tutor.state_manager.get_mastery_level(topic)}")
    
    if os.path.exists(state_file):
        os.remove(state_file)

if __name__ == "__main__":
    technical_evaluation()
    pedagogical_evaluation()
