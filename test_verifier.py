import os
# Import your specific function from the verifier file
from verifier import run_simple_verification

# 1. Define the model file location
# Using normpath ensures Windows handles the slashes correctly
model_to_test = os.path.normpath("models/model.csp")

def execute_test():
    # Check if the model exists before starting the engine
    if not os.path.exists(model_to_test):
        print(f"❌ Error: Could not find {model_to_test}.")
        print(f"Current Working Directory: {os.getcwd()}")
        return

    try:
        # 2. Read the CSP content
        with open(model_to_test, 'r', encoding='utf-8') as f:
            csp_code = f.read()
        
        print(f"🚀 Initializing Windows PAT Agent")
        print(f"--- Testing: {os.path.basename(model_to_test)} ---")

        # 3. Call your verifier
        # Since your verifier handles the subprocess and printing, 
        # we just need to pass the data.
        run_simple_verification("Manual_Test_Run", csp_code)

        print("-" * 40)
        print("✅ Workflow Complete.")

    except Exception as e:
        print(f"❓ An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    execute_test()