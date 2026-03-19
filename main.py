import os
import json
import time
from engine import RepairEngine
from verifier import PATVerifier

# Configuration matching project structure
MODELS_DIR = "./models"
OUTPUT_DIR = "./repaired_models"
INITIAL_LOG_FILE = "mismatch_traces.json"
MAX_ITERATIONS = 5

def filter_fixable_errors(issues):
    """
    Filters out issues that are not actual mismatches.
    Keeps errors where the current_result does not match the desired_result.
    """
    fixable = []
    for entry in issues:
        current = entry.get('current_result')
        desired = entry.get('desired_result') 
        
        # Skip LLM flagged invalid assertions
        if current == "Invalid_Assertion":
            continue
            
        # If a desired result is provided, only keep it if there's a mismatch.
        if desired and current and str(desired).lower() == str(current).lower():
            continue
            
        fixable.append(entry)
    return fixable

def normalize_assertion(assertion_text):
    """Helper to remove empty parentheses and extra spaces for exact matching."""
    if not assertion_text: return ""
    return assertion_text.replace("()", "").strip()

def reconcile_issues(tracked_issues, verifier_output):
    """
    Cross-references the verifier's raw output against the tracked issues
    to maintain the correct 'desired_result' and catch hidden 'Valid' states.
    """
    # 1. If the verifier hit a Syntax Error, immediately return it
    for issue in verifier_output:
        if issue.get("current_result") == "Syntax_Error":
            return [issue]
            
    # 2. Map issues using NORMALIZED keys so 'keyless_car' matches 'keyless_car()'
    tracked_map = { 
        normalize_assertion(issue['assertion']): issue 
        for issue in tracked_issues if issue.get('assertion') 
    }
    
    verifier_map = { 
        normalize_assertion(issue['assertion']): issue 
        for issue in verifier_output if issue.get('assertion') 
    }
    
    reconciled = []
    
    # 3. Update the status of all tracked target assertions
    for norm_assertion, tracked_issue in tracked_map.items():
        original_assertion_text = tracked_issue['assertion'] # Keep original formatting
        desired = tracked_issue.get('desired_result', 'Valid')
        
        if norm_assertion in verifier_map:
            # The verifier explicitly flagged this as "is NOT valid" -> currently Invalid
            reconciled.append({
                "assertion": original_assertion_text,
                "trace": verifier_map[norm_assertion].get('trace', ''),
                "current_result": "Invalid",
                "desired_result": desired
            })
        else:
            # The verifier ignored it, meaning PAT evaluated it as "Valid"
            reconciled.append({
                "assertion": original_assertion_text,
                "trace": "Property satisfied.",
                "current_result": "Valid",
                "desired_result": desired
            })
            
    # 4. Catch NEW regressions (things that broke that weren't tracked)
    for norm_assertion, v_issue in verifier_map.items():
        if norm_assertion not in tracked_map and norm_assertion not in ["PARSING", "EXECUTION"]:
            reconciled.append({
                "assertion": v_issue['assertion'],
                "trace": v_issue.get('trace', ''),
                "current_result": "Invalid",
                "desired_result": "Valid" # New breaks default to wanting to be Valid
            })
            
    return reconciled

def main():
    try:
        engine = RepairEngine()
        verifier = PATVerifier(output_json=INITIAL_LOG_FILE)
    except Exception as e:
        print(f"[!] Initialization Error: {e}")
        return
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # [PHASE 0]: Load initial mismatches
    if not os.path.exists(INITIAL_LOG_FILE):
        print(f"[!] Could not find initial {INITIAL_LOG_FILE}.")
        return
        
    with open(INITIAL_LOG_FILE, 'r') as f:
        try:
            current_issues = json.load(f)
        except json.JSONDecodeError:
            print(f"[!] Error reading {INITIAL_LOG_FILE}. Ensure it contains valid JSON.")
            return

    # Initial filter
    fixable_errors = filter_fixable_errors(current_issues)
    
    if not fixable_errors:
        print(f"[🎉] No fixable errors in the initial {INITIAL_LOG_FILE}. Model is already verified!")
        return

    last_model_content = ""
    repaired_path = os.path.join(OUTPUT_DIR, "repaired_model.csp")
    original_path = os.path.join(MODELS_DIR, "model.csp")
    target_model = repaired_path if os.path.exists(repaired_path) else original_path

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n{'='*20} PIPELINE ITERATION {iteration} {'='*20}")

        # 1. LOAD FULL CONTENT & LOOP DETECTION
        with open(target_model, 'r') as f:
            current_model_content = f.read()

        if current_model_content == last_model_content and iteration > 1:
            print("[⚠️] Loop Detected: Model content is unchanged despite repair attempts.")
            break
        last_model_content = current_model_content

        print(f"[*] Found {len(fixable_errors)} mismatches. Starting Synchronous Repair on FULL file...")

        # 2. INCREMENTAL REPAIR PHASE
        for entry in fixable_errors:
            assertion_text = entry.get('assertion')
            error_trace = entry.get('trace')
            status = entry.get('current_result')
            desired = entry.get('desired_result', 'Valid')
            
            if status == "Syntax_Error":
                print(f"\n[*] Engine fixing Syntax Errors...")
                error_context = f"The model failed to parse. Technical details:\n{error_trace}"
            else:
                print(f"\n[*] Engine repairing: {assertion_text[:50]}...")
                
                # Contextual prompts based on the desired result vs current state
                if str(desired).lower() == "invalid" and str(status).lower() == "valid":
                    if "reaches" in assertion_text or "[]" in assertion_text and "<>" not in assertion_text:
                        # Safety / Reachability - We want to PREVENT a bad state
                        error_context = (
                            f"Assertion: {assertion_text}\n"
                            f"Goal: This bad state must be UNREACHABLE (INVALID), but currently PAT found a path to it (VALID).\n"
                            f"Failure: You are missing strict safety guards. You MUST locate the events that cause this state "
                            f"(e.g., lock_door, consume_fuel, owner_exit) and add strict negative guards or atomic variable updates "
                            f"to make this state mathematically impossible to reach.\n"
                            f"Trace: {error_trace}"
                        )
                    else:
                        # Liveness - We want to intentionally ALLOW starvation
                        error_context = (
                            f"Assertion: {assertion_text}\n"
                            f"Goal: This liveness assertion currently evaluates to VALID, but it MUST evaluate to INVALID.\n"
                            f"Failure: The system is structurally biased or too fair. You MUST introduce a valid path (an infinite loop or a deadlock) "
                            f"where this goal is NEVER reached. Ensure mathematical symmetry so competing processes can infinitely starve each other.\n"
                            f"Trace: {error_trace}"
                        )
                elif str(desired).lower() == "valid" and str(status).lower() == "invalid":
                    error_context = (
                        f"Assertion: {assertion_text}\n"
                        f"Goal: This assertion evaluates to INVALID, but it MUST evaluate to VALID.\n"
                        f"Failure: The system is over-constrained, deadlocked, or stuck in a stuttering livelock (an infinite loop of non-productive events). "
                        f"You MUST remove artificial 'idle' or 'skip' self-loops, break reversible action loops, and ensure the 'happy path' guards allow the actors to progress.\n"
                        f"Trace: {error_trace}"
                    )
                else:
                    error_context = f"Assertion: {assertion_text}\nTrace: {error_trace}"

            repair_result = engine.request_repair(
                full_context=current_model_content, 
                error_log=error_context,
                target_assertion=assertion_text,
                other_assertions=[],
                desired_result=desired  # <--- FIXED: Now explicitly passing desired result to engine.py
            )

            if repair_result.get("status") in ["success", "repaired"]:
                new_content = repair_result.get("model", "").strip()
                
                if new_content and new_content != current_model_content:
                    with open(repaired_path, 'w') as f:
                        f.write(new_content)
                    
                    current_model_content = new_content
                    print(f"    [SUCCESS] Fix saved to {repaired_path}")
                    time.sleep(1) 
            
            elif repair_result.get("status") == "invalid_assertion":
                print(f"    [SKIP] Engine flagged assertion as invalid.")
            else:
                print(f"    [!] Engine failed: {repair_result.get('reason', 'Unknown error')}")

        target_model = repaired_path

        # 3. VERIFICATION PHASE (Post-Repair)
        print(f"\n[*] Verifying new state: {target_model}")
        raw_verifier_output = verifier.verify_model(target_model)
        
        # Reconcile raw output with our tracked goals (Internal memory keeps all 7)
        current_issues = reconcile_issues(current_issues, raw_verifier_output)
        
        # Filter down to ONLY the actual unresolved mismatches
        fixable_errors = filter_fixable_errors(current_issues)
        
        # --- NEW LOGIC: Save ONLY the unresolved mismatches to the numbered JSON ---
        numbered_log_file = f"mismatch_traces_{iteration}.json"
        
        # Write directly from main.py to avoid the hardcoded print in verifier.py
        with open(numbered_log_file, 'w') as f:
            json.dump(fixable_errors, f, indent=2)
            
        print(f"📂 Found {len(fixable_errors)} unresolved issues. Generated trace history: {numbered_log_file}")
        
        if not fixable_errors:
            print(f"[🎉] Success! Issues resolved and no new mismatches found. Model verified.")
            break
        
    print(f"\n[*] Pipeline finished.")

if __name__ == "__main__":
    main()