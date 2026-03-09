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
        self.os_type = platform.system().lower()

    def verify_model(self, file_path):
        abs_csp_path = os.path.abspath(file_path)
        repaired_dir = os.path.join(self.project_root, "repaired_models")
        os.makedirs(repaired_dir, exist_ok=True)
        abs_log_path = os.path.join(repaired_dir, "output.txt")
        
        if os.path.exists(abs_log_path):
            os.remove(abs_log_path)

        command = ["wine", self.pat_path, "-csp", abs_csp_path, abs_log_path]
        
        try:
            print(f"--- Verifying: {os.path.basename(abs_csp_path)} ---")
            result = subprocess.run(command, capture_output=True, text=True, timeout=300)
            
            # --- NEW FILTERING LOGIC ---
            # Extract real errors by excluding Wine/MoltenVK/MVK system noise
            clean_stdout = self._filter_noise(result.stdout)
            clean_stderr = self._filter_noise(result.stderr)

            # Check for actual PAT syntax errors (usually contain '[Error]' or line numbers)
            if "[Error]" in clean_stdout or "exception" in clean_stdout.lower() or "[Error]" in clean_stderr:
                print(f"❌ Actual Syntax Error detected in {os.path.basename(abs_csp_path)}!")
                return [{
                    "assertion": "SYNTAX_CHECK",
                    "trace": (clean_stdout + "\n" + clean_stderr).strip(),
                    "current_result": "Syntax_Error",
                    "desired_result": "Valid"
                }]

            # 2. Process valid output from output.txt
            if os.path.exists(abs_log_path):
                with open(abs_log_path, "r") as f:
                    content = f.read()
                
                if not content.strip():
                    # If PAT didn't write to file, check if there was a silent crash
                    return [{"assertion": "PARSING", "trace": clean_stderr, "current_result": "Syntax_Error"}]
                    
                return self._parse_output(content)
            
            return [{"assertion": "EXECUTION", "trace": "No log file created", "current_result": "Syntax_Error"}]
                
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return []

    def _filter_noise(self, text):
        """Removes Wine, MoltenVK, and Vulkan system logs from the output."""
        noise_patterns = [
            r"^[0-9a-f]+:err:.*",    # Wine error logs
            r"^[0-9a-f]+:fixme:.*",  # Wine fixme logs
            r"^\[mvk-info\].*",       # MoltenVK info
            r"^VK_.*",                # Vulkan extension lists
            r"^\tVK_.*"               # Tabbed Vulkan extensions
        ]
        lines = text.splitlines()
        filtered_lines = [
            line for line in lines 
            if not any(re.match(pattern, line) for pattern in noise_patterns)
        ]
        return "\n".join(filtered_lines).strip()

    def _parse_output(self, raw_output):
        issues = []
        blocks = raw_output.split("=======================================================")
        
        for block in blocks:
            if "is NOT valid" in block:
                assertion_match = re.search(r"Assertion:\s*(.*)", block)
                assertion_name = assertion_match.group(1).strip() if assertion_match else "Unknown"
                
                # Capture the full trace until the next section
                trace_match = re.search(r"presented as follows\.\n(.*?)\n\n\*\*\*\*\*\*\*\*", block, re.DOTALL)
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
    target = os.path.join("repaired_models", "repaired_model.csp")
    if os.path.exists(target):
        found_issues = verifier.verify_model(target)
        verifier.save_json(found_issues)
    else:
        print(f"❌ File {target} not found.")