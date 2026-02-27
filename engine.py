import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

# The new SDK automatically looks for the GEMINI_API_KEY environment variable.
# If your .env file is set up correctly, you don't need to pass it explicitly.
client = genai.Client()

def repair_snippet(full_code, rule, assertion):
    """
    Acts as the direct interface to Gemini. 
    Receives full context and returns full corrected code.
    """
    prompt = f"""
    ### TASK
    Repair the following PAT CSP# model to satisfy this LTL property: {assertion}
    
    ### FULL MODEL
    {full_code}
    
    ### REQUIREMENTS
    1. Fix logic in processes (guards, variable updates).
    2. Syntax: Exactly ONE '->' per transition. NO trailing semicolons after process calls.
    3. Output: Return the FULL corrected model. No prose. No markdown.
    """
    
    try:
        # The new method signature for the updated SDK
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        # Remove any lingering backticks
        return response.text.strip().replace('```csp', '').replace('```', '')
    except Exception as e:
        print(f"❌ Engine Error: {e}")
        return None