import subprocess
import json
import os
import re
import platform

class PATVerifier:
    def __init__(self, pat_path="bin/MONO-PAT-v3.6.0/PAT3.Console.exe", output_json="mismatch_traces.json"):
        # Use absolute paths to prevent Wine from losing track of the directory structure
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.pat_path = os.path.abspath(pat_path)
        self.output_json = os.path.abspath(output_json)
        self.os_type = platform.system().lower()

    def verify_model(self, file_path):
        """
        Runs PAT3 via Wine. Detects both assertion failures AND syntax errors.
        """
        abs_csp_path = os.path.abspath(file_path)
        repaired_dir = os.path.join(self.project_root, "repaired_models")
        os.makedirs(repaired_dir, exist_ok=True)
        abs_log_path = os.path.join(repaired_dir, "output.txt")
        
        # Clear old logs to ensure we don't read stale results
        if os.path.exists(abs_log_path):
            os.remove(abs_log_path)

        # Standard command for PAT3 Console
        command = ["wine", self.pat_path, "-csp", abs_csp_path, abs_log_path]
        
        try:
            print(f"--- Verifying: {os.path.basename(abs_csp_path)} ---")
            # Capture stdout/stderr to catch syntax/parsing errors
            result = subprocess.run(command, capture_output=True, text=True, timeout=300)
            
            # 1. Check for Syntax/Parsing Errors (often hidden in stderr)
            if "Error" in result.stdout or "Error" in result.stderr or "exception" in result.stdout.lower():
                print(f"❌ Syntax/Parsing Error detected in {os.path.basename(abs_csp_path)}!")
                return [{
                    "assertion": "SYNTAX_CHECK",
                    "trace": (result.stdout + "\n" + result.stderr).strip(),
                    "current_result": "Syntax_Error",
                    "desired_result": "Valid"
                }]

            # 2. Process valid output
            if os.path.exists(abs_log_path):
                with open(abs_log_path, "r") as f:
                    content = f.read()
                
                if not content.strip():
                    return [{"assertion": "PARSING", "trace": "Empty Output", "current_result": "Syntax_Error"}]
                    
                return self._parse_output(content)
            
            return [{"assertion": "EXECUTION", "trace": "No log file created", "current_result": "Syntax_Error"}]
                
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return []

    def _parse_output(self, raw_output):
        """Extracts Invalid results and traces from the PAT3 text dump."""
        issues = []
        # Split by blocks to isolate each assertion's results
        blocks = raw_output.split("=======================================================")
        
        for block in blocks:
            # Match the specific 'is NOT valid' pattern
            if "is NOT valid" in block:
                assertion_match = re.search(r"Assertion:\s*(.*)", block)
                assertion_name = assertion_match.group(1).strip() if assertion_match else "Unknown"
                
                # Capture the counterexample trace
                trace_match = re.search(r"presented as follows\.\n(.*)", block)
                trace = trace_match.group(1).strip() if trace_match else "<init>"
                
                issues.append({
                    "assertion": f"#assert {assertion_name};",
                    "trace": trace,
                    "current_result": "Invalid",
                    "desired_result": "Valid"
                })
        return issues

    def save_json(self, issues):
        """Saves findings to mismatch_traces.json."""
        with open(self.output_json, 'w') as f:
            json.dump(issues, f, indent=2)
        print(f"📂 Found {len(issues)} issues. Updated: mismatch_traces.json")

if __name__ == "__main__":
    verifier = PATVerifier()
    target = os.path.join("repaired_models", "repaired_model.csp")
    if os.path.exists(target):
        found_issues = verifier.verify_model(target)
        verifier.save_json(found_issues)
    else:
        print(f"❌ File {target} not found.")