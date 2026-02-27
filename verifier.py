import subprocess
import re
import json
import os

PAT_CONSOLE_PATH = "/Users/dom/Desktop/PAT/PAT3.Console.exe"

def run_pat_verification(model_path, output_json="mismatch_traces.json"):
    if not os.path.exists(PAT_CONSOLE_PATH):
        print(f"❌ Error: PAT Console executable not found at {PAT_CONSOLE_PATH}")
        return False

    print(f"🔎 Verifying {os.path.basename(model_path)}...")

    abs_model_path = os.path.abspath(model_path)
    report_file = abs_model_path + ".log"
    
    # Restored the required report_file argument
    cmd = ["mono", PAT_CONSOLE_PATH, "-csp", "-v", abs_model_path, report_file]
    
    try:
        # We still capture stdout just in case other modules complain
        result = subprocess.run(cmd, timeout=45, capture_output=True, text=True)
        
        if "Could not load" in result.stdout or result.stderr:
            print("\n=== 🛑 PAT INITIALIZATION WARNINGS ===")
            print(result.stdout)
            print(result.stderr)
            
    except Exception as e:
        print(f"   ❌ Execution failed: {e}")
        return False

    errors = []
    
    # Parse the actual report file PAT generated
    if os.path.exists(report_file):
        with open(report_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        print("\n=== 📄 PAT REPORT OUTPUT ===")
        print(content.strip())
        print("============================\n")
        
        # Regex to find failing assertions
        failure_pattern = r"Assertion\s+(.*?)\s+is\s+(?:NOT valid|Invalid)"
        matches = re.findall(failure_pattern, content, re.IGNORECASE)

        for assertion in matches:
            clean_assert = assertion.strip()
            errors.append({
                "assertion": clean_assert,
                "status": "failed",
                "model_file": model_path
            })
            print(f"   🚩 Found violation: {clean_assert}")
            
        os.remove(report_file) # Clean up the log file
    else:
        print(f"   ⚠️ Warning: PAT did not create the report file. It may have crashed.")

    # Save to JSON for the repair engine
    if errors:
        with open(output_json, 'w') as f:
            json.dump(errors, f, indent=4)
        print(f"   💾 Saved {len(errors)} errors to {output_json}")
        return True
    else:
        print("   ✅ No verification errors found. Model satisfies all assertions.")
        if os.path.exists(output_json):
            with open(output_json, 'w') as f:
                json.dump([], f)
        return False