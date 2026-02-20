import os
import re
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
else:
    print("❌ Error: GEMINI_API_KEY not found. Please check your .env file.")

def repair_snippet(snippet, rule, assertion):
    model_id = 'models/gemini-2.5-flash'
    
    try:
        # 65s delay is safer if you've been hitting the 429 limit recently
        print("⏳ Quota safety delay...")
        time.sleep(5) 

        model = genai.GenerativeModel(model_id)
        
        # Refined prompt for pure logic generation
        prompt = f"""
        ### TASK
        Repair ONLY the internal logic of this CSP# transition: {snippet}
        Property: {assertion}
        
        ### VARIABLES
        - coordinatorArray (indices 0, 1, 2)
        - role, answerCount
        
        ### SYNTAX REQUIREMENTS
        1. Output format: event_name{{atomic{{ assignments }}}} -> Node1()
        2. NO semicolons (;) outside of the curly braces.
        3. NO double arrows (->). 
        4. NO explanations. Return ONLY the code line.
        """
        
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        
        # --- POST-PROCESSING: THE SYNTAX GUARD ---
        
        # 1. Remove markdown and prose
        clean_line = [l.strip() for l in raw_text.split('\n') if '->' in l]
        if not clean_line: return None
        repaired = clean_line[-1].replace('```csp', '').replace('```', '').strip()

        # 2. Fix Double Arrows (Normalization)
        # Finds any sequence of "-> Process()" and ensures only one remains at the end
        repaired = re.sub(r'->\s*\w+\(\).*$', '', repaired).strip()
        repaired += " -> Node1()"

        # 3. Clean up internal semicolons and dangling syntax
        # Ensures no semicolon exists after the final brace before the arrow
        repaired = repaired.replace(';}', '}').replace('}}', '}}')
        
        # 4. Final Semicolon Strip (Crucial for the [] Choice operator)
        # We find the LAST arrow and cut everything after it to prevent terminal ';'
        if "->" in repaired:
            base, target = repaired.split("->")
            repaired = f"{base.strip().rstrip(';')} -> {target.strip().rstrip(';')}"

        return repaired

    except Exception as e:
        print(f"   ❌ Engine Error: {e}")
        return None