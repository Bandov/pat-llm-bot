import os
import json
import shutil
from engine import RepairEngine

MODELS_DIR = "./models"
OUTPUT_DIR = "./repaired_models"
LOG_FILE = "mismatch_traces.json"


def main():
    try:
        engine = RepairEngine()
    except Exception as e:
        print(f"[!] Initialization Error: {e}")
        return

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    with open(LOG_FILE, "r") as f:
        errors = json.load(f)

    # Dictionary to track the 'current best version' of each model
    # Key: original_filename, Value: path_to_latest_version
    active_workspace = {}

    print(f"[*] Starting repair pipeline for {len(errors)} failures...")

    for i, entry in enumerate(errors):
        assertion_text = entry.get("assertion")
        error_trace = entry.get("trace")

        # 1. FIND THE FILE: Scan original models AND current repaired workspace
        target_file = None
        current_content = ""
        original_name = ""

        # Check workspace first (to continue from previous fix)
        for f_name in os.listdir(OUTPUT_DIR):
            if f_name.endswith(".csp"):
                with open(os.path.join(OUTPUT_DIR, f_name), "r") as f:
                    content = f.read()
                    if assertion_text in content:
                        target_file = os.path.join(OUTPUT_DIR, f_name)
                        current_content = content
                        original_name = f_name.replace("repaired_", "")
                        break

        # If not in workspace, check original models
        if not target_file:
            for f_name in os.listdir(MODELS_DIR):
                if f_name.endswith(".csp"):
                    with open(os.path.join(MODELS_DIR, f_name), "r") as f:
                        content = f.read()
                        if assertion_text in content:
                            target_file = os.path.join(MODELS_DIR, f_name)
                            current_content = content
                            original_name = f_name
                            break

        if not target_file:
            print(f"[!] Skip: Assertion '{assertion_text}' not found in any file.")
            continue

        print(f"\n[Step {i+1}] Repairing {original_name} for: {assertion_text}")

        # 2. Gather all assertions in this model so the engine can avoid regressions.
        model_assertions = [
            line.strip()
            for line in current_content.splitlines()
            if line.strip().startswith("#assert")
        ]
        other_assertions = [a for a in model_assertions if a != assertion_text]

        # 2. REPAIR: Pass the LATEST content to the engine
        repair_result = engine.request_repair(
            full_context=current_content,
            error_log=f"Assertion: {assertion_text}\nTrace: {error_trace}",
            target_assertion=assertion_text,
            other_assertions=other_assertions,
        )

        out_path = os.path.join(OUTPUT_DIR, f"repaired_{original_name}")

        if repair_result.get("status") == "invalid_assertion":
            invalid_model = repair_result.get("model", "").strip()
            if invalid_model:
                with open(out_path, "w") as f:
                    f.write(invalid_model)
                print(
                    f"    [UPDATED] Tagged invalid assertion in workspace file: {out_path}"
                )

            print(f"    [SKIP] Invalid assertion reported by engine.")
            print(f"           Assertion: {assertion_text}")
            print(
                f"           Reason: {repair_result.get('reason', 'No reason provided.')}"
            )
            continue

        if repair_result.get("status") == "error":
            print(f"    [ERROR] Engine failure for assertion: {assertion_text}")
            print(f"            Reason: {repair_result.get('reason', 'Unknown error')}")
            continue

        repaired_model = repair_result.get("model", "").strip()
        if not repaired_model:
            print(f"    [ERROR] Empty repair result for assertion: {assertion_text}")
            continue

        # 3. UPDATE WORKSPACE: Overwrite the repaired version for the next pass
        with open(out_path, "w") as f:
            f.write(repaired_model)

        print(f"    [SUCCESS] Updated workspace file: {out_path}")

    print("\n[*] Pipeline complete. Check ./repaired_models for the final versions.")


if __name__ == "__main__":
    main()
