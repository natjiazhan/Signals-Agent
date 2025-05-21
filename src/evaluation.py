import os
import json
from difflib import SequenceMatcher

GROUND_TRUTH_FILE = "eval.json"
OUTPUT_DIR = "outputs/"

# Checks if summaries are similar
def text_similarity(a, b):
    """Return a float similarity score between 0 and 1."""
    return SequenceMatcher(None, a, b).ratio()

# Checks if source types are similar
def fuzzy_match(a, b, threshold=0.7):
    """Return True if strings a and b are similar above threshold."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= threshold

# Compare source types using fuzzy matching
def compare_source_types(pred_types, true_types, threshold=0.7):
    """
    Compare two lists of source types using fuzzy matching.
    Returns matched labels, match score, and success status.
    """
    matched = set()
    for true_label in true_types:
        for pred_label in pred_types:
            if fuzzy_match(true_label, pred_label, threshold):
                matched.add(true_label)
                break

    score = len(matched) / len(true_types) if true_types else 0
    success = score == 1.0
    return matched, score, success

# Main function to evaluate predictions against ground truth
def main():
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
