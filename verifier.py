import subprocess
import os
import re

# Dynamic Pathing to ensure it works on your specific Windows path
ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
PAT_EXE_PATH = os.path.normpath(os.path.join(ROOT_PATH, "PAT", "PAT3.Console.exe"))
PAT_FOLDER = os.path.normpath(os.path.join(ROOT_PATH, "PAT"))

def run_simple_verification(model_name, pat_code):
    """
    Runs the PAT verifier and notifies you immediately of any failures or syntax errors.
    """
    # 1. Setup temporary workspace
    temp_folder = os.path.join(ROOT_PATH, "temp_verification", model_name)
    os.makedirs(temp_folder, exist_ok=True)
    
    input_file = os.path.abspath(os.path.join(temp_folder, "model.csp"))
    output_file = os.path.abspath(os.path.join(temp_folder, "output.txt"))

    # Write the code to the input file
    with open(input_file, 'w', encoding='utf-8') as f:
        f.write(pat_code)

    # 2. Command for Windows (direct EXE call)
    command = ["mono", PAT_EXE_PATH, "-csp", input_file, output_file]

    print(f"🔎 Verifying {model_name}...")

    try:
        # 3. Execute PAT
        # capture_output=True allows us to see errors if the file isn't created
        result = subprocess.run(
            command, 
            check=False, # Set to False to handle PAT's own exit codes manually
            timeout=120, 
            cwd=PAT_FOLDER, 
            capture_output=True, 
            text=True
        )
        
        # 4. Handle Results
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            with open(output_file, 'r', encoding='utf-8') as f:
                output = f.read()

            if "is Valid" in output or "is VALID" in output:
                print(f"✅ SUCCESS: {model_name} assertions are Valid.")
            else:
                print(f"❌ FAIL: {model_name} assertions failed (Invalid).")
                if "********Verification Result********" in output:
                    result_section = output.split("********Verification Result********")[1].split("********")[0]
                    print(f"Detail: {result_section.strip()}")
        else:
            # 5. Diagnostic: If no file, show what the console actually said
            print(f"⚠️ ERROR: PAT failed to produce a verification result.")
            if result.stdout or result.stderr:
                print("--- PAT Console Output ---")
                if result.stdout: print(result.stdout)
                if result.stderr: print(result.stderr)
            else:
                print("No console output received. Ensure PAT3.Console.exe is valid and unblocked.")

    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT: PAT took too long (>120s) for {model_name}.")
    except Exception as e:
        print(f"❓ SYSTEM ERROR: {str(e)}")

if __name__ == '__main__':
    # Test with a simple model
    test_code = """
    var x = 0;
    P = set_x_1 -> SKIP;
    #assert P reaches x == 1;
    """
    run_simple_verification("SimpleTest", test_code)