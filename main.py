import os
import warnings
import re
from analyser import ProjectAnalyzer
from engine import repair_snippet # engine.py is now the direct Gemini caller

warnings.filterwarnings("ignore", category=FutureWarning)

MODELS_DIR = "models"
OUTPUT_DIR = "repaired_models"
JSON_LOG = "mismatch_traces.json"

def sanitize_pat_syntax(content):
    """
    Directly addresses the 'double arrow' and 'trailing semicolon' 
    bugs that break PAT's Choice [] operator.
    """
    # 1. Fix Double Arrows: "-> Node() -> Node()" -> "-> Node()"
    # This prevents the AI from chaining state transitions.
    content = re.sub(r'(->\s*\w+\(\))\s*->\s*\w+\(\)', r'\1', content)
    
    # 2. Choice Operator Fix: PAT lines within a choice block must not end in ';'
    lines = content.split('\n')
    fixed_lines = []
    for line in lines:
        stripped = line.strip()
        # If the line looks like a CSP transition, ensure it doesn't have a trailing ;
        if '->' in stripped and stripped.endswith(')'):
            line = line.rstrip(';')
        fixed_lines.append(line)
    
    return "\n".join(fixed_lines)

def repair_model_file(model_name, analyzer):
    model_path = os.path.join(MODELS_DIR, model_name)
    repaired_path = os.path.join(OUTPUT_DIR, f"repaired_{model_name}")

    if not os.path.exists(model_path):
        print(f"❌ Model file {model_name} not found.")
        return

    with open(model_path, "r") as f:
        current_full_content = f.read()

    # Apply fixes based on the JSON trace logs
    for entry in analyzer.errors:
        assertion_text = entry.get('assertion')
        print(f"🛠️  Calling Gemini for full-context repair on: {assertion_text}")

        # Engine now takes the WHOLE file for context
        repaired_content = repair_snippet(current_full_content, "General PAT Repair", assertion_text)

        if repaired_content:
            # Clean the output before moving to the next error or saving
            current_full_content = sanitize_pat_syntax(repaired_content)
            print(f"   ✅ Content updated and sanitized.")

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    with open(repaired_path, "w") as f:
        f.write(current_full_content)
    
    print(f"✨ Final repaired model saved: {repaired_path}")

def run_pipeline():
    if not os.path.exists(JSON_LOG):
        print(f"❌ Error: {JSON_LOG} not found.")
        return

    analyzer = ProjectAnalyzer(JSON_LOG)
    target_models = [f for f in os.listdir(MODELS_DIR) if f.endswith(".csp")]

    for model_name in target_models:
        print(f"\n🚀 Pipeline Entry: {model_name}")
        repair_model_file(model_name, analyzer)

if __name__ == "__main__":
    run_pipeline()