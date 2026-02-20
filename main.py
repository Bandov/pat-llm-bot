import os
import warnings
from analyser import ProjectAnalyzer, find_process_block
from engine import repair_snippet
from rules import RULES

# Suppress the deprecation warning for the old SDK
warnings.filterwarnings("ignore", category=FutureWarning)

# --- CONFIGURATION ---
MODELS_DIR = "models"
OUTPUT_DIR = "repaired_models"
JSON_LOG = "mismatch_traces.json"

def process_single_repair(csp_content, event_name, entry):
    """
    Coordinates with Gemini to fix a specific block of code.
    Returns the updated full content of the file.
    """
    assertion_text = entry.get('assertion')
    # Use the specific rule for the event, or fallback to the general default rule
    rule = RULES.get(event_name, RULES.get("default", "Repair state inconsistency."))

    print(f"   🔎 Slicing code for event: '{event_name}'")
    
    # Extract the specific snippet (the var block or the process line)
    snippet = find_process_block(csp_content, event_name)

    if not snippet:
        print(f"   ⚠️ Could not find code block for '{event_name}'. Skipping...")
        return None

    print(f"   🤖 Requesting repair from Gemini 2.5 Flash...")
    new_snippet = repair_snippet(snippet, rule, assertion_text)

    if new_snippet:
        # Perform surgical replacement
        updated_content = csp_content.replace(snippet, new_snippet)
        return updated_content
    
    return None

def repair_model_file(model_name, analyzer):
    """Processes all errors and saves a single, fully repaired file."""
    model_path = os.path.join(MODELS_DIR, model_name)
    repaired_path = os.path.join(OUTPUT_DIR, f"repaired_{model_name}")

    if not os.path.exists(model_path):
        print(f"❌ Model file {model_name} not found.")
        return

    # 1. Read the WHOLE original file
    with open(model_path, "r") as f:
        current_full_content = f.read()

    # 2. Iterate through each error in the JSON log
    for entry in analyzer.errors:
        # Get all relevant events using the Deep Scan logic from analyser.py
        targets = analyzer.get_repair_targets(entry, current_full_content)
        print(f"👉 Found {len(targets)} relevant events for repair: {targets}")

        for event in targets:
            # Accumulate the changes into current_full_content
            result = process_single_repair(current_full_content, event, entry)
            if result:
                current_full_content = result
                print(f"   ✅ '{event}' block updated.")

    # 3. Create output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 4. Save the final version
    with open(repaired_path, "w") as f:
        f.write(current_full_content)
    
    print(f"\n✨ SUCCESS: Full repaired model saved to: {repaired_path}")

def run_pipeline():
    """Main orchestrator for the repair process."""
    if not os.path.exists(JSON_LOG):
        print(f"❌ Error: {JSON_LOG} not found.")
        return

    analyzer = ProjectAnalyzer(JSON_LOG)
    
    # Find all .csp files in the models directory
    target_models = [f for f in os.listdir(MODELS_DIR) if f.endswith(".csp")]

    if not target_models:
        print(f"❌ No .csp files found in {MODELS_DIR}/")
        return

    for model_name in target_models:
        print(f"\n🛠️  Starting Pipeline for: {model_name}")
        repair_model_file(model_name, analyzer)

if __name__ == "__main__":
    run_pipeline()