import subprocess
import json
import os
import re
import platform

class PATVerifier:
    def __init__(self, pat_path="bin/MONO-PAT-v3.6.0/PAT3.Console.exe", output_json="mismatch_traces.json"):
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.pat_path = os.path.abspath(pat_path)
        self.output_json = os.path.abspath(output_json)
        self.os_type = platform.system().lower() # Detects 'darwin' (Mac), 'linux', or 'windows'

    def verify_model(self, csp_filename):
        repaired_dir = os.path.join(self.project_root, "repaired_models")
        abs_csp_path = os.path.join(repaired_dir, csp_filename)
        abs_log_path = os.path.join(repaired_dir, "output.txt")
        
        if not os.path.exists(abs_csp_path):
            print(f"❌ Error: {csp_filename} not found.")
            return []

        # --- OS GENERALIZATION LOGIC ---
        if self.os_type == "windows":
            # Direct execution on Windows
            command = [self.pat_path, "-csp", abs_csp_path, abs_log_path]
        else:
            # Use Wine for macOS (darwin) and Linux
            command = ["wine", self.pat_path, "-csp", abs_csp_path, abs_log_path]
        
        try:
            print(f"--- Verifying on {platform.system()}: {csp_filename} ---")
            subprocess.run(command, capture_output=True, text=True, timeout=300)
            
            if os.path.exists(abs_log_path):
                with open(abs_log_path, "r") as f:
                    content = f.read()
                return self._parse_output(content)
            return []
                
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return []

    def _parse_output(self, raw_output):
        issues = []
        # Split by blocks to isolate each assertion's results
        blocks = raw_output.split("=======================================================")
        
        for block in blocks:
            if "is NOT valid" in block:
                # Extracting Assertion Name
                assertion_match = re.search(r"Assertion:\s*(.*)", block)
                assertion_name = assertion_match.group(1).strip() if assertion_match else "Unknown"
                
                # Extracting Counterexample Trace
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
        with open(self.output_json, 'w') as f:
            json.dump(issues, f, indent=2)
        print(f"📂 Found {len(issues)} issues. Updated: mismatch_traces.json")

if __name__ == "__main__":
    verifier = PATVerifier()
    target = "repaired_model.csp" 
    
    if os.path.exists(os.path.join("repaired_models", target)):
        found_issues = verifier.verify_model(target)
        verifier.save_json(found_issues)
    else:
        print(f"❌ Target file 'repaired_models/{target}' missing.")