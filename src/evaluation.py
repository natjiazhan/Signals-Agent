import os
import json
import requests
from difflib import SequenceMatcher
from dotenv import load_dotenv

load_dotenv()

HF_API_TOKEN = os.getenv("HF_API_TOKEN")
LLM_ENDPOINT = "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"
GROUND_TRUTH_FILE = "eval.json"
OUTPUT_DIR = "outputs/"

def text_similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def fuzzy_match(a, b, threshold=0.7):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= threshold

def fuzzy_compare_source_types(pred_types, true_types):
    matched = set()
    for true_label in true_types:
        for pred_label in pred_types:
            if fuzzy_match(true_label, pred_label):
                matched.add(true_label)
                break
    score = len(matched) / len(true_types) if true_types else 0
    return matched, score, score == 1.0

def llm_grade_with_zephyr(true_labels, pred_labels):
    if HF_API_TOKEN is None:
        print("HF_API_TOKEN not found. Falling back to fuzzy matching.")
        return fuzzy_compare_source_types(pred_labels, true_labels)[2]

    prompt = f"""
        You are a grading assistant. Given predicted and ground truth audio source types, respond strictly with either PASS or FAIL.

        Ground truth labels: {true_labels}
        Predicted labels: {pred_labels}

        If all predicted labels are equivalent to the ground truth and no predicted labels are present as ground truth, return PASS.
        If not, return FAIL.
        Response:
        """

    try:
        response = requests.post(
            LLM_ENDPOINT,
            headers={"Authorization": f"Bearer {HF_API_TOKEN}"},
            json={"inputs": prompt},
        )
        result = response.json()

        if isinstance(result, list) and "generated_text" in result[0]:
            output_text = result[0]["generated_text"].upper()
            return "PASS" in output_text
        elif "error" in result:
            print(f"LLM API error: {result['error']}")
        else:
            print(f"Unexpected LLM API response: {result}")

    except Exception as e:
        print("LLM evaluation failed. Falling back to fuzzy matching:", e)

    return fuzzy_compare_source_types(pred_labels, true_labels)[2]

def compare_source_types(pred_types, true_types):
    passed = llm_grade_with_zephyr(true_types, pred_types)
    matched = set(pred_types).intersection(true_types)
    score = 1.0 if passed else 0.0
    return matched, score, passed

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

        matched, score, success = compare_source_types(pred_sources, true_sources)
        sim = text_similarity(pred.get("summary", ""), truth.get("summary", ""))

        print(f"{fname}")
        print(f"  Source Types - expected: {true_sources}, predicted: {pred_sources}")
        print(f"  Matched: {list(matched)}, Score: {score:.2f}")
        print(f"  Summary Similarity: {sim:.2f}")
        print(f"  {'PASS' if success else 'FAIL'}\n")

        total += 1
        passed += int(success)

    print(f"Final Evaluation: {passed}/{total} correct source_type predictions")

if __name__ == "__main__":
    main()
