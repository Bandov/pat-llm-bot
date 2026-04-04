import os
import json
import time
import re
from engine import RepairEngine
from verifier import PATVerifier

# Configuration matching project structure
MODELS_DIR = "./models"
OUTPUT_DIR = "./repaired_models"
INITIAL_LOG_FILE = "mismatch_traces.json"
MAX_ITERATIONS = 4

def normalize_assertion(assertion_text):
    """Helper to remove empty parentheses and extra spaces for exact dictionary matching."""
    if not assertion_text: return ""
    return assertion_text.replace("()", "").replace(" ", "").strip()

def deduplicate_and_clean_issues(issues, expected_target, base_name):
    """
    Removes contradictory duplicates and dynamically rewrites the assertion 
    strings to match the exact formatting of the original .csp file.
    """
    seen = {}
    deduped = []
    
    for issue in issues:
        raw_assert = issue.get('assertion', '')
        norm_assert = normalize_assertion(raw_assert)
        
        if norm_assert not in seen:
            if expected_target and base_name:
                # Force the JSON string to match the original file's signature
                issue['assertion'] = re.sub(rf'\b{base_name}(\s*\(\))?\s*\|=', f'{expected_target} |=', raw_assert)
            seen[norm_assert] = True
            deduped.append(issue)
        else:
            print(f"[!] Dropping contradictory duplicate target: {raw_assert}")
            
    return deduped

def filter_fixable_errors(issues):
    """
    Filters out issues that are not actual mismatches.
    Keeps errors where the current_result does not match the desired_result.
    """
    fixable = []
    for entry in issues:
        current = entry.get('current_result')
        desired = entry.get('desired_result') 
        
        if current == "Invalid_Assertion":
            continue
            
        if desired and current and str(desired).lower() == str(current).lower():
            continue
            
        fixable.append(entry)
    return fixable

def reconcile_issues(tracked_issues, verifier_output):
    """Cross-references the verifier's raw output against the tracked issues."""
    for issue in verifier_output:
        if issue.get("current_result") == "Syntax_Error":
            return [issue]
            
    tracked_map = { normalize_assertion(issue['assertion']): issue for issue in tracked_issues if issue.get('assertion') }
    verifier_map = { normalize_assertion(issue['assertion']): issue for issue in verifier_output if issue.get('assertion') }
    
    reconciled = []
    
    for norm_assertion, tracked_issue in tracked_map.items():
        original_assertion_text = tracked_issue['assertion']
        desired = tracked_issue.get('desired_result', 'Valid')
        
        if norm_assertion in verifier_map:
            reconciled.append({
                "assertion": original_assertion_text,
                "trace": verifier_map[norm_assertion].get('trace', ''),
                "current_result": "Invalid",
                "desired_result": desired
            })
        else:
            reconciled.append({
                "assertion": original_assertion_text,
                "trace": "Property satisfied.",
                "current_result": "Valid",
                "desired_result": desired
            })
            
    for norm_assertion, v_issue in verifier_map.items():
        if norm_assertion not in tracked_map and norm_assertion not in ["PARSING", "EXECUTION"]:
            reconciled.append({
                "assertion": v_issue['assertion'],
                "trace": v_issue.get('trace', ''),
                "current_result": "Invalid",
                "desired_result": "Valid"
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
    original_path = os.path.join(MODELS_DIR, "model.csp")
    
    # --- [PHASE 0A]: DYNAMIC SIGNATURE DETECTION ---
    expected_target = None
    base_name = None
    if os.path.exists(original_path):
        with open(original_path, 'r') as f:
            original_csp = f.read()
            # Hunt for the first assertion to see how the system is called
            match = re.search(r'#assert\s+([A-Za-z0-9_]+)(\s*\(\))?\s*\|=', original_csp)
            if match:
                base_name = match.group(1)
                has_parens = bool(match.group(2))
                expected_target = f"{base_name}()" if has_parens else base_name
                print(f"[*] Detected ground-truth system signature: '{expected_target}'")

    # --- [PHASE 0B]: LOAD AND SCRUB MISMATCHES ---
    if not os.path.exists(INITIAL_LOG_FILE):
        print(f"[!] Could not find initial {INITIAL_LOG_FILE}.")
        return
        
    with open(INITIAL_LOG_FILE, 'r') as f:
        try:
            current_issues = json.load(f)
        except json.JSONDecodeError:
            print(f"[!] Error reading {INITIAL_LOG_FILE}.")
            return

    # Pass the detected signature to the scrubber
    current_issues = deduplicate_and_clean_issues(current_issues, expected_target, base_name)
    fixable_errors = filter_fixable_errors(current_issues)
    
    if not fixable_errors:
        print(f"[🎉] No fixable errors. Model is already verified!")
        return

    last_model_content = ""
    repaired_path = os.path.join(OUTPUT_DIR, "repaired_model.csp")
    target_model = repaired_path if os.path.exists(repaired_path) else original_path

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n{'='*20} PIPELINE ITERATION {iteration} {'='*20}")

        with open(target_model, 'r') as f:
            current_model_content = f.read()

        if current_model_content == last_model_content and iteration > 1:
            print("[⚠️] Loop Detected: Model content is unchanged despite repair attempts.")
            break
        last_model_content = current_model_content

        print(f"[*] Found {len(fixable_errors)} mismatches. Starting Repair...")

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
                
                if str(desired).lower() == "invalid" and str(status).lower() == "valid":
                    if "reaches" in assertion_text or ("[]" in assertion_text and "<>" not in assertion_text):
                        error_context = f"Assertion: {assertion_text}\nGoal: Must be INVALID (Unreachable).\nTrace: {error_trace}"
                    else:
                        error_context = f"Assertion: {assertion_text}\nGoal: Must be INVALID (Allow Starvation). Delete turn variables and allow non-deterministic choice.\nTrace: {error_trace}"
                elif str(desired).lower() == "valid" and str(status).lower() == "invalid":
                    error_context = f"Assertion: {assertion_text}\nGoal: Must be VALID (Prevent Starvation/Livelock).\nTrace: {error_trace}"
                else:
                    error_context = f"Assertion: {assertion_text}\nTrace: {error_trace}"

            repair_result = engine.request_repair(
                full_context=current_model_content, 
                error_log=error_context,
                target_assertion=assertion_text,
                other_assertions=[],
                desired_result=desired
            )

            if repair_result.get("status") in ["success", "repaired"]:
                new_content = repair_result.get("model", "").strip()
                
                # --- DYNAMIC OUTPUT SCRUBBER ---
                if new_content and expected_target and base_name:
                    new_content = re.sub(rf'^{base_name}(\s*\(\))?\s*=', f'{expected_target} =', new_content, flags=re.MULTILINE)
                    new_content = re.sub(rf'#assert\s+{base_name}(\s*\(\))?\s*\|=', f'#assert {expected_target} |=', new_content)

                if new_content and new_content != current_model_content:
                    with open(repaired_path, 'w') as f:
                        f.write(new_content)
                    current_model_content = new_content
                    print(f"    [SUCCESS] Fix saved to {repaired_path}")
                    time.sleep(1) 
                else:
                    if not new_content:
                        print("    [!] Engine issue: Returned empty model.")
                    else:
                        print("    [!] Engine issue: Returned identical model (No changes made by LLM).")
            
            elif repair_result.get("status") == "invalid_assertion":
                print(f"    [SKIP] Engine flagged assertion as invalid.")
            else:
                print(f"    [!] Engine failed: {repair_result.get('reason', 'Unknown error')}")

        # SAFELY update target_model only if the file was actually written
        if os.path.exists(repaired_path):
            target_model = repaired_path

        print(f"\n[*] Verifying new state: {target_model}")
        raw_verifier_output = verifier.verify_model(target_model)
        
        current_issues = reconcile_issues(current_issues, raw_verifier_output)
        fixable_errors = filter_fixable_errors(current_issues)
        
        numbered_log_file = f"mismatch_traces_{iteration}.json"
        with open(numbered_log_file, 'w') as f:
            json.dump(fixable_errors, f, indent=2)
            
        print(f"📂 Found {len(fixable_errors)} unresolved issues. Log: {numbered_log_file}")
        if not fixable_errors:
            print(f"[🎉] Success! Issues resolved and no new mismatches found.")
            break
        
    print(f"\n[*] Pipeline finished.")

if __name__ == "__main__":
    main()