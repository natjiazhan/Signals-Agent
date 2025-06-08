# import os
# import json
# from dotenv import load_dotenv
# from llama_index.llms.openai import OpenAI

# load_dotenv()

# GROUND_TRUTH_FILE = "eval.json"
# OUTPUT_DIR = "outputs/"

# llm = OpenAI(model="o3-mini")

# source_eval_prompt="""
# You are a grading assistant for an audio classification task.

# Instructions: 
# - You must grade the agent's prediction against the correct answer.
# - You must return ONLY the word `PASS` or `FAIL` — nothing else.
# - A `PASS` is only valid if:
#   - Every predicted label matches a label in the ground truth (either literally or semantically),
#   - No extra or unrelated labels are in the prediction,
#   - All ground truth labels are covered.

# If any of these conditions are violated, return `FAIL`.


# Examples:

# PASS Examples:

# - Example 1 
# Ground truth: ["machine", "human"]  
# Prediction: ["human", "machine"]  
# Result: PASS

# - Example 2  
# Ground truth: ["nature"]  
# Prediction: ["natural sound"]  
# Result: PASS

# - Example 3
# Ground truth: ["synthesized", "video game"]  
# Prediction: ["video game", "synthesized"]  
# Result: PASS

# - Example 4
# Ground truth: ["music", "classical", "strings", "woodwinds", "brass", "piano"]  
# Prediction: ["piano", "classical", "music", "woodwinds", "brass", "strings"]  
# Result: PASS

# - Example 5
# Ground truth: ["beach", "waves"]  
# Prediction: ["waves", "beach"]  
# Result: PASS

# - Example 6
# Ground truth: ["keyboard", "typing", "machine"]  
# Prediction: ["typing", "machine", "keyboard"]  
# Result: PASS

# - Example 7
# Ground truth: ["bird", "nature", "forest", "leaves"]  
# Prediction: ["forest", "leaves", "bird", "nature"]  
# Result: PASS

# - Example 8
# Ground truth: ["human"]  
# Prediction: ["person speaking"]  
# Result: PASS

# - Example 9
# Ground truth: ["fireplace", "crackling", "wood"]  
# Prediction: ["crackling", "wood", "fireplace"]  
# Result: PASS

# - Example 10
# Ground truth: ["baby", "crying"]  
# Prediction: ["crying", "baby"]  
# Result: PASS

# FAIL Examples:

# - Example 1
# Ground truth: ["nature"]  
# Prediction: ["synthesized"]  
# Result: FAIL

# - Example 2
# Ground truth: ["machine", "human"]  
# Prediction: ["machine"]  
# Result: FAIL

# - Example 3
# Ground truth: ["synthesized", "video game"]  
# Prediction: ["video game", "synthesized", "gunfire"]  
# Result: FAIL

# - Example 4
# Ground truth: ["music"]  
# Prediction: ["noise"]  
# Result: FAIL

# - Example 5
# Ground truth: ["cafe", "music"]  
# Prediction: ["restaurant"]  
# Result: FAIL

# - Example 6
# Ground truth: ["construction", "machine"]  
# Prediction: ["office"]  
# Result: FAIL

# - Example 7
# Ground truth: ["human"]  
# Prediction: ["human", "synthesized"]  
# Result: FAIL

# - Example 8
# Ground truth: ["bird", "forest"]  
# Prediction: ["bird"]  
# Result: FAIL

# - Example 9
# Ground truth: ["cheering", "crowd"]  
# Prediction: ["music"]  
# Result: FAIL

# - Example 10
# Ground truth: ["typing"]  
# Prediction: ["machine", "keyboard", "clicks"]  
# Result: FAIL

# Now evaluate:

# Ground truth labels: {true_labels}  
# Predicted labels: {pred_labels}  

# Result:

# """

# summary_eval_prompt="""

# You are a grading assistant for an audio classification task.

# Instructions:
# You must evaluate whether the generated summary correctly captures the ground truth summary. A `PASS` is only valid if:
# - All major elements and details from the ground truth are mentioned or paraphrased in the prediction.
# - No irrelevant or fabricated information is present in the prediction.
# - The tone and content must match semantically.

# If any of these conditions are violated, return `FAIL`.

# PASS Examples:

# - Example 1
# GT: "Audio clip with jackhammer construction noise and background conversations."  
# Pred: "Construction noise from a jackhammer and people talking can be heard."  
# Result: PASS

# - Example 2
# GT: "Clip from a forest creek with water and wind."  
# Pred: "Nature sounds including water flowing over rocks and rustling leaves."  
# Result: PASS

# - Example 3
# GT: "Synthesized piano music with a calming melody."  
# Pred: "Soft synthesized piano plays a gentle tune."  
# Result: PASS

# - Example 4
# GT: "Human voices in a crowded event space."  
# Pred: "Several human conversations taking place in a busy environment."  
# Result: PASS

# - Example 5
# GT: "Waves crashing and seagulls squawking at a beach."  
# Pred: "Beach sounds with crashing waves and seagull noises."  
# Result: PASS

# - Example 6
# GT: "Call center with ringing phones and people talking."  
# Pred: "Office environment with phone rings and multiple voices."  
# Result: PASS

# - Example 7
# GT: "Classical music with strings, brass, and piano."  
# Pred: "Soft classical tune played by piano and string instruments."  
# Result: PASS

# - Example 8
# GT: "Street sounds with cars, honking, and people."  
# Pred: "Urban street ambiance with vehicles, horns, and crowd murmurs."  
# Result: PASS

# - Example 9
# GT: "Fireplace with crackling wood."  
# Pred: "The sound of a fire crackling and wood popping."  
# Result: PASS

# - Example 10
# GT: "Thunderstorm with rain and thunder."  
# Pred: "Raining heavily with distant thunder."  
# Result: PASS


# FAIL Examples:

# - Example 1
# GT: "Construction noise and conversations."  
# Pred: "Birds chirping in a peaceful forest."  
# Result: FAIL

# - Example 2
# GT: "Forest creek with flowing water and leaves."  
# Pred: "Piano music with electronic beats."  
# Result: FAIL

# - Example 3
# GT: "Busy street with traffic and crowd."  
# Pred: "Office sounds with keyboards and phone calls."  
# Result: FAIL

# - Example 4
# GT: "Human voices in a crowded event space."  
# Pred: "Synthesized tones and explosions."  
# Result: FAIL

# - Example 5
# GT: "Thunderstorm with lightning and thunder."  
# Pred: "Happy beach music and waves."  
# Result: FAIL

# - Example 6
# GT: "Seagulls and ocean waves."  
# Pred: "Typing and machine noises."  
# Result: FAIL

# - Example 7
# GT: "Birdsong and rustling leaves in forest."  
# Pred: "Heavy machinery and construction site."  
# Result: FAIL

# - Example 8
# GT: "Baby crying loudly."  
# Pred: "Dogs barking in the distance."  
# Result: FAIL

# - Example 9
# GT: "Human conversation in a call center."  
# Pred: "Ambient nature sounds with a river."  
# Result: FAIL

# - Example 10
# GT: "Classical piano and brass instruments."  
# Pred: "Fast-paced electronic dance music."  
# Result: FAIL

# Now evaluate:

# Ground truth summary: {true_summary}  
# Predicted summary: {pred_summary}  

# Result:

# """

# def grade_source_type(true_labels, pred_labels):
#     prompt = source_eval_prompt.format(
#         true_labels=true_labels,
#         pred_labels=pred_labels
#     )
#     try:
#         response = llm.complete(prompt)
#         return "PASS" in response.text.strip().upper()
#     except Exception as e:
#         print("LLM source_type grading failed:", e)
#         return False

# def grade_summary(true_summary, pred_summary):
#     prompt = summary_eval_prompt.format(
#         true_summary=true_summary,
#         pred_summary=pred_summary
#     )
#     try:
#         response = llm.complete(prompt)
#         return "PASS" in response.text.strip().upper()
#     except Exception as e:
#         print("LLM summary grading failed:", e)
#         return False

# def main():
#     if not os.path.exists(GROUND_TRUTH_FILE):
#         print(f"Cannot find {GROUND_TRUTH_FILE}. Make sure it exists.")
#         return

#     with open(GROUND_TRUTH_FILE, "r") as f:
#         ground_truth = json.load(f)

#     total = 0
#     passed = 0

#     for fname, truth in ground_truth.items():
#         pred_path = os.path.join(OUTPUT_DIR, fname.replace(".m4a", ".json").replace(".mp3", ".json"))
#         if not os.path.exists(pred_path):
#             print(f"Missing prediction for {fname}")
#             continue

#         with open(pred_path, "r") as f:
#             pred = json.load(f)

#         # Extract ground truth and predicted data
#         true_sources = truth["structured"]["source_type"]
#         pred_sources = pred.get("structured", {}).get("source_type", [])
#         true_summary = truth["summary"]
#         pred_summary = pred.get("summary", "")

#         source_type_pass = grade_source_type(true_sources, pred_sources)
#         summary_pass = grade_summary(true_summary, pred_summary)

#         print(f"{fname}")
#         print(f"  Source Types - expected: {true_sources}, predicted: {pred_sources}")
#         print(f"  Summary - expected: {true_summary}, predicted: {pred_summary}")
#         print(f"  Source Type Grade: {'PASS' if source_type_pass else 'FAIL'}")
#         print(f"  Summary Grade: {'PASS' if summary_pass else 'FAIL'}\n")

#         total += 1
#         passed += int(source_type_pass and summary_pass)

#     print(f"Final Evaluation: {passed}/{total} files passed both source type and summary grading")

# if __name__ == "__main__":
#     main()

import os
import json
from dotenv import load_dotenv
from llama_index.llms.openai import OpenAI

load_dotenv()

GROUND_TRUTH_FILE = "eval.json"
OUTPUT_DIR = "outputs/"

llm = OpenAI(model="gpt-4o")

source_eval_prompt="""
You are a grading assistant for an audio classification task.

Instructions: 
- You must evaluate whether a single predicted label matches a single ground truth label.
- You must return ONLY the word `PASS` or `FAIL` — nothing else.
- A `PASS` is valid if:
    - The predicted label is a literal or semantic match to the ground truth label.
- A `FAIL` is returned if the predicted label does not match or is unrelated.

Now evaluate:

Ground truth label: {true_labels}  
Predicted label: {pred_labels}  

Result:
"""

# This function evaluates individual labels against the ground truth.
def individual_label_score(true_labels, pred_labels):
    passes = 0
    total = 0
    
    for label in true_labels:
        total += 1
        for pred in pred_labels:
            prompt = source_eval_prompt.format(true_labels=[label], pred_labels=[pred])
            try:
                response = llm.complete(prompt)
                if "PASS" in response.text.strip().upper():
                    passes += 1
                    break  # Stop checking this true label once we find a match
            except Exception as e:
                print(f"LLM individual label grading failed: {e}")
    return passes, total

def main():
    if not os.path.exists(GROUND_TRUTH_FILE):
        print(f"Cannot find {GROUND_TRUTH_FILE}. Make sure it exists.")
        return

    with open(GROUND_TRUTH_FILE, "r") as f:
        ground_truth = json.load(f)

    label_passes = 0
    label_total = 0

    for fname, truth in ground_truth.items():
        pred_path = os.path.join(OUTPUT_DIR, fname.replace(".m4a", ".json").replace(".mp3", ".json"))
        if not os.path.exists(pred_path):
            print(f"Missing prediction for {fname}")
            continue

        with open(pred_path, "r") as f:
            pred = json.load(f)

        true_sources = truth["structured"]["source_type"]
        pred_sources = pred.get("structured", {}).get("source_type", [])

        indiv_pass, indiv_total = individual_label_score(true_sources, pred_sources)
        label_passes += indiv_pass
        label_total += indiv_total

        print(f"{fname}")
        print(f"  Source Types - expected: {true_sources}, predicted: {pred_sources}")
        print(f"  Label Match: {indiv_pass}/{indiv_total} labels matched\n")

    label_score = label_passes / label_total if label_total else 0
    print(f"Final Label Accuracy Score: {label_score:.2f} ({label_passes}/{label_total})")

if __name__ == "__main__":
    main()
