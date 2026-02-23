import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def repair_snippet(full_code, rule, assertion):
    """
    Acts as the direct interface to Gemini. 
    Receives full context and returns full corrected code.
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    
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
        response = model.generate_content(prompt)
        # Remove any lingering backticks
        return response.text.strip().replace('```csp', '').replace('```', '')
    except Exception as e:
        print(f"❌ Engine Error: {e}")
        return None