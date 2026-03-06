import os
import json
import time
from engine import RepairEngine
from verifier import PATVerifier

# Configuration matching project structure
MODELS_DIR = "./models"
OUTPUT_DIR = "./repaired_models"
LOG_FILE = "mismatch_traces.json"
MAX_ITERATIONS = 2

def main():
    try:
        engine = RepairEngine()
        verifier = PATVerifier(output_json=LOG_FILE)
    except Exception as e:
        print(f"[!] Initialization Error: {e}")
        return
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    last_model_content = ""

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n{'='*20} PIPELINE ITERATION {iteration} {'='*20}")

        # 1. VERIFICATION PHASE
        repaired_path = os.path.join(OUTPUT_DIR, "repaired_model.csp")
        original_path = os.path.join(MODELS_DIR, "model.csp")
        
        # Always prioritize the latest repair
        target_to_verify = repaired_path if os.path.exists(repaired_path) else original_path
        
        print(f"[*] Verifying current state: {target_to_verify}")
        all_issues = verifier.verify_model(target_to_verify)
        verifier.save_json(all_issues)
        
        # Filter for fixable errors (skip 'Invalid_Assertion' markers from the LLM)
        fixable_errors = [e for e in all_issues if e.get('current_result') != "Invalid_Assertion"]
        
        if not fixable_errors:
            print("[🎉] Success! No more issues found. Model is verified.")
            break

        # 2. LOAD CONTENT & LOOP DETECTION
        with open(target_to_verify, 'r') as f:
            current_model_content = f.read()

        # Stop if the model content is unchanged to prevent wasting API quota
        if current_model_content == last_model_content:
            print("[⚠️] Loop Detected: Model content is unchanged despite repair attempts.")
            break
        last_model_content = current_model_content

        print(f"[*] Found {len(fixable_errors)} issues. Starting Synchronous Repair...")

        # 3. INCREMENTAL REPAIR PHASE
        for entry in fixable_errors:
            assertion_text = entry.get('assertion')
            error_trace = entry.get('trace')
            status = entry.get('current_result')
            
            # Tailor the error log based on whether it is syntax or liveness/safety
            if status == "Syntax_Error":
                print(f"\n[*] Engine fixing Syntax Errors...")
                error_context = f"The model failed to parse. Technical details:\n{error_trace}"
            else:
                print(f"\n[*] Engine repairing: {assertion_text[:50]}...")
                error_context = f"Assertion: {assertion_text}\nTrace: {error_trace}"

            # Synchronous call to Gemini
            repair_result = engine.request_repair(
                full_context=current_model_content,
                error_log=error_context,
                target_assertion=assertion_text,
                other_assertions=[] 
            )

            # Check status from engine.py ('success' or 'repaired')
            if repair_result.get("status") in ["success", "repaired"]:
                new_content = repair_result.get("model", "").strip()
                
                if new_content and new_content != current_model_content:
                    # Save immediately and sync to disk
                    with open(repaired_path, 'w') as f:
                        f.write(new_content)
                    
                    current_model_content = new_content
                    print(f"    [SUCCESS] Fix saved to {repaired_path}")
                    # Small sleep to ensure the filesystem metadata updates
                    time.sleep(1) 
            
            elif repair_result.get("status") == "invalid_assertion":
                print(f"    [SKIP] Engine flagged assertion as invalid.")
            else:
                print(f"    [!] Engine failed: {repair_result.get('reason', 'Unknown error')}")

    print(f"\n[*] Pipeline finished.")

if __name__ == "__main__":
    main()