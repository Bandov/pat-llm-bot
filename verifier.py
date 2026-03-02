import subprocess
import os
import time

def run_remote_verification(model_name, pat_code):
    local_csp = "temp_model.csp"
    local_out = "result.txt"
    
    with open(local_csp, 'w', encoding='utf-8') as f:
        f.write(pat_code)

    print(f"🔎 Verifying {model_name} (Clean-Room Strategy)...")

    try:
        # Push model
        subprocess.run(["docker", "cp", local_csp, "pat-bridge:/model.csp"], check=True)

        # Execute from /app/PAT using standard -csp flag
        # MONO_REGISTRY_PATH is added to prevent some common Mono crashes on Mac
        docker_cmd = [
            "docker", "exec", "pat-bridge", "sh", "-c",
            "cd /app/PAT && "
            "export MONO_IOMAP=all && "
            "export MONO_REGISTRY_PATH=/tmp/mono-reg && "
            "xvfb-run -a mono PAT3.Console.exe -csp /model.csp /output.txt"
        ]
        
        start_time = time.time()
        result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=120)
        print(f"⏱️ Time: {time.time() - start_time:.2f}s")

        # Pull result
        cp_back = subprocess.run(["docker", "cp", "pat-bridge:/output.txt", local_out], capture_output=True)
        
        if cp_back.returncode != 0:
            print("❌ PAT Error: No result file produced.")
            # If we see 'Invalid Image' here, it means Module.CSP.dll is still not being loaded
            if "Invalid Image" in result.stdout:
                print("⚠️ Still seeing Invalid Image. Checking CSP DLL bitness...")
                subprocess.run(["docker", "exec", "pat-bridge", "file", "/app/PAT/Modules/CSP/PAT.Module.CSP.dll"])
            return

        if os.path.exists(local_out):
            with open(local_out, 'r') as f:
                content = f.read()
                if "is Valid" in content or "is VALID" in content:
                    print(f"✅ SUCCESS: {model_name} is Valid.")
                else:
                    print(f"❌ FAIL: {model_name} is Invalid.")

    except Exception as e:
        print(f"❓ System Error: {e}")
    finally:
        if os.path.exists(local_csp): os.remove(local_csp)

if __name__ == '__main__':
    test_csp = "P = SKIP; #assert P reaches True;"
    run_remote_verification("FinalBridgeTest", test_csp)