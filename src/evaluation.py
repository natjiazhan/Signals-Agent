import os
import json
from dotenv import load_dotenv
from llama_index.llms.openai import OpenAI

load_dotenv()

GROUND_TRUTH_FILE = "eval.json"
OUTPUT_DIR = "outputs/"

llm = OpenAI(model="o3-mini")


def llm_grade_source_types(true_labels, pred_labels):

    prompt = f"""
    You are a grading assistant for an audio classification task.

    Instructions:
    - You must grade the agent's prediction against the correct answer.
    - You must return ONLY the word PASS or FAIL — nothing else.
    - A PASS is only valid if:
      - Every predicted label matches a label in the ground truth (semantically or literally),
      - No extra or unrelated labels are in the prediction,
      - All ground truth labels are covered.

    If these conditions are not perfectly met, return FAIL.

    Evaluate:

    Ground truth labels: {true_labels}
    Predicted labels: {pred_labels}

    Result:
    """

    try:
        response = llm.complete(prompt)
        output = response.text.strip().upper()
        return "PASS" in output
    except Exception as e:
        print("LLM evaluation failed.", e)
        return False
    
def llm_grade_summary(true_summary, pred_summary):
    prompt = f"""
    You are a grading assistant for an audio classification task.

    Instructions:
    - Evaluate the semantic similarity between the agent's predicted summary and the ground truth summary.
    - Only return PASS if the summaries convey the same key meaning or information.
    - If the prediction misses major elements or includes hallucinated ones, return FAIL.
    - You must return ONLY the word PASS or FAIL — nothing else.

    Ground truth summary: {true_summary}
    Predicted summary: {pred_summary}

    Result:
    """
    try:
        response = llm.complete(prompt)
        output = response.text.strip().upper()
        return "PASS" in output
    except Exception as e:
        print("LLM summary evaluation failed.", e)
        return False

def main():
    if not os.path.exists(GROUND_TRUTH_FILE):
        print(f"Cannot find {GROUND_TRUTH_FILE}. Make sure it exists.")
        return

    with open(GROUND_TRUTH_FILE, "r") as f:
        ground_truth = json.load(f)

    total = 0
    passed = 0

    for fname, truth in ground_truth.items():
        pred_path = os.path.join(OUTPUT_DIR, fname.replace(".m4a", ".json").replace(".mp3", ".json"))
        if not os.path.exists(pred_path):
            print(f"Missing prediction for {fname}")
            continue

        with open(pred_path, "r") as f:
            pred = json.load(f)

        pred_sources = pred.get("structured", {}).get("source_type", [])
        true_sources = truth["structured"]["source_type"]

        pred_summary = pred.get("summary", "")
        true_summary = truth["summary"]

        source_type_pass = llm_grade_source_types(true_sources, pred_sources)
        summary_pass = llm_grade_summary(true_summary, pred_summary)

        print(f"{fname}")
        print(f"  Source Types - expected: {true_sources}, predicted: {pred_sources}")
        print(f"  Summary - expected: {true_summary}, predicted: {pred_summary}")
        print(f"  Source Type Grade: {'PASS' if source_type_pass else 'FAIL'}")
        print(f"  Summary Grade: {'PASS' if summary_pass else 'FAIL'}")

        total += 1
        passed += int(source_type_pass and summary_pass)

    print(f"Final Evaluation: {passed}/{total} files passed both source type and summary grading")

if __name__ == "__main__":
    main()
