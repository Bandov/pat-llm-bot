import os
import time
import re
from dotenv import load_dotenv
from google import genai
from rules import RULES 

load_dotenv()

class RepairEngine:
    INVALID_PREFIX = "INVALID_ASSERTION:"

    def __init__(self, rules_path="pat_rules.md"):
        """
        Initializes the Repair Engine.
        :param rules_path: Path to the Markdown file containing mandatory PAT syntax.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY missing from .env")
        
        self.client = genai.Client(api_key=api_key)
        self.model_id = 'gemini-3-flash-preview'
        
        # Load external syntax constraints to keep engine.py clean
        self.mandatory_syntax = self._load_external_rules(rules_path)

    def _load_external_rules(self, path):
        """Reads the markdown file containing PAT syntax constraints."""
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return f.read()
            print(f"[!] Warning: {path} not found. Rules not loaded.")
            return ""
        except Exception as e:
            print(f"[!] Error loading rules file: {e}")
            return ""

    def _global_sanitizer(self, code):
        """
        Final structural check to ensure single declarations and clean syntax.
        Enforces flat array initialization and semicolon rules.
        """
        # 1. Brute-force fix for 2D array nesting: [[0,1]] -> [0,1]
        code = re.sub(r'=\s*\[\s*\[(.*?)\]\s*\]', r'= [\1]', code) 
        
        lines = code.split('\n')
        seen_headers = set()
        clean_lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                clean_lines.append("")
                continue

            # 2. Deduplicate: var, #define, or Process() =
            header_match = re.match(r'^(var\s+\w+|#define\s+\w+|\w+\(\)\s*=)', stripped)
            if header_match:
                header = header_match.group(1)
                if header in seen_headers: 
                    continue 
                seen_headers.add(header)
            
            # 3. Strip 'atomic' keyword (Common PAT parser error fix)
            line = re.sub(r'\{atomic\s*\{(.*?)\}\s*\}', r'{\1}', line)
            line = line.replace("atomic{", "{")
            
            # [cite_start]4. Ensure #define/var declarations end with a semicolon [cite: 1]
            if stripped.startswith(("#define", "var")) and not stripped.endswith(";"):
                line = stripped + ";"
            
            clean_lines.append(line)
            
        return '\n'.join(clean_lines)

    def request_repair(self, full_context, error_log, target_assertion="", other_assertions=None):
        """Main entry point to request a model repair from Gemini."""
        
        # Determine strategy based on the error log (Starvation/Liveness check)
        if self._looks_like_starvation_liveness(target_assertion, error_log):
            tagged = self._tag_invalid_assertion(full_context, target_assertion)
            return {
                "status": "invalid_assertion",
                "model": tagged,
                "reason": "Liveness failure is starvation/cycle-based; property assumes fairness not encoded in the model."
            }

        is_liveness = "[]<>" in error_log or "SCC" in error_log
        strategy_list = [RULES["default"]]
        other_assertions = other_assertions or []
        
        if is_liveness:
            strategy_list.append(RULES["liveness"])
        else:
            strategy_list.append(RULES["safety"])
            strategy_list.append(RULES["lifecycle_coupling"])

        preserve_assertions_block = "\n".join(other_assertions) if other_assertions else "(none)"

        # The prompt now references the mandatory syntax loaded from your .md file
        prompt = f"""
        Role: Formal Methods Expert (PAT CSP#).
        Task: Fix the Liveness/Safety failure in the FULL model below.
        
        [STRATEGY]
        {" ".join(strategy_list)}

        [TARGET ASSERTION TO FIX]
        {target_assertion}

        [REGRESSION GUARD]
        {preserve_assertions_block}
        
        [VERIFICATION FAILURE]
        {error_log}
        
        [ORIGINAL MODEL]
        {full_context}
        
        [INSTRUCTIONS]
        - Output ONLY the FULL repaired model.
        - You MUST follow the syntax examples provided in the system context.
        - Return ONLY raw CSP# text (no prose, no markdown).
        """

        try:
            print(f"[*] Calling {self.model_id} for repair...")
            # Inject mandatory syntax into the system_instruction for strict compliance
            response = self.client.models.generate_content(
                model=self.model_id, 
                contents=prompt,
                config={'system_instruction': self.mandatory_syntax}
            )
            
            parsed = self._parse_response(response.text)
            output = self._clean_output(parsed["content"])
            sanitized = self._global_sanitizer(output)

            # Handle Invalid Assertion mode
            if parsed["status"] == "invalid_assertion":
                base_model = sanitized if sanitized else full_context
                tagged = self._tag_invalid_assertion(base_model, target_assertion)
                return {
                    "status": "invalid_assertion",
                    "model": tagged,
                    "reason": parsed.get("reason") or "No reason provided."
                }

            # Regression check for destructive repairs
            if self._too_destructive(full_context, sanitized):
                tagged = self._tag_invalid_assertion(full_context, target_assertion)
                return {
                    "status": "invalid_assertion",
                    "model": tagged,
                    "reason": "Repair required deleting/renaming existing event branches; violates non-destructive constraint."
                }

            return {"status": "repaired", "model": sanitized, "reason": None}

        except Exception as e:
            if "429" in str(e):
                print("[!] Quota hit. Waiting 60s..."); time.sleep(60)
                return self.request_repair(full_context, error_log, target_assertion, other_assertions)
            return {"status": "error", "model": "", "reason": str(e)}

    def _parse_response(self, text):
        stripped = text.replace("```csp", "").replace("```", "").strip()
        if not stripped:
            return {"status": "error", "model": "", "reason": "Empty response", "content": ""}

        lines = stripped.splitlines()
        first_line = lines[0].strip()

        if first_line.startswith(self.INVALID_PREFIX):
            reason = first_line.split(self.INVALID_PREFIX, 1)[1].strip()
            content = "\n".join(lines[1:]).strip()
            return {"status": "invalid_assertion", "model": "", "reason": reason, "content": content}

        return {"status": "repaired", "model": "", "reason": None, "content": stripped}

    def _looks_like_starvation_liveness(self, target_assertion, error_log):
        if "[]<>" not in target_assertion: return False
        return "Starvation" in error_log or "SCC" in error_log or re.search(r'\)\s*\*', error_log)

    def _clean_output(self, text):
        match = re.search(r'(#define|var|[\w]+\(\)\s*=)', text)
        return text[match.start():] if match else text

    def _tag_invalid_assertion(self, model_text, target_assertion):
        if not model_text or not target_assertion: return model_text
        target = target_assertion.strip()
        if target in model_text and "// INVALID ASSERTION" not in model_text:
            return model_text.replace(target, target + " // INVALID ASSERTION", 1)
        return model_text

    def _extract_event_labels(self, code):
        labels = set()
        process_names = self._extract_process_names(code)
        for line in code.splitlines():
            s = line.strip()
            if not s or s.startswith(("#define", "var", "#assert")): continue
            for m in re.finditer(r'\b([A-Za-z_]\w*)\s*(\{|->)', s):
                name = m.group(1)
                if name not in process_names: labels.add(name)
        return labels

    def _extract_process_names(self, code):
        names = set()
        for line in code.splitlines():
            m = re.match(r'^([A-Za-z_]\w*)\s*\(\)\s*=', line.strip())
            if m: names.add(m.group(1))
        return names

    def _too_destructive(self, original, repaired, drop_ratio=0.15):
        orig = self._extract_event_labels(original)
        rep = self._extract_event_labels(repaired)
        if not orig: return False
        return (len(orig - rep) / len(orig)) > drop_ratio