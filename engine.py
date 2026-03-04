import os
import time
import re
from dotenv import load_dotenv
from google import genai
from rules import RULES

load_dotenv()

class RepairEngine:
    INVALID_PREFIX = "INVALID_ASSERTION:"

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY missing from .env")
        
        self.client = genai.Client(api_key=api_key)
        self.model_id = 'gemini-3-flash-preview'

    def _global_sanitizer(self, code):
        """Final structural check to ensure single declarations and clean syntax."""
        lines = code.split('\n')
        seen_headers = set()
        clean_lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                clean_lines.append(""); continue

            # 1. Deduplicate: var, #define, or Process() =
            header_match = re.match(r'^(var\s+\w+|#define\s+\w+|\w+\(\)\s*=)', stripped)
            if header_match:
                header = header_match.group(1)
                if header in seen_headers: continue 
                seen_headers.add(header)
            
            # 2. Strip 'atomic' keyword (Parser Error Fix)
            line = re.sub(r'\{atomic\s*\{(.*?)\}\s*\}', r'{\1}', line)
            line = line.replace("atomic{", "{")
            
            # 3. Ensure #define/var end with ;
            if stripped.startswith(("#define", "var")) and not stripped.endswith(";"):
                line = stripped + ";"
            
            clean_lines.append(line)
            
        return '\n'.join(clean_lines)

    def request_repair(self, full_context, error_log, target_assertion="", other_assertions=None):
        # Determine strategy: Does the log contain Liveness operators?
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

        prompt = f"""
        Role: Formal Methods Expert (PAT CSP#).
        Task: Fix the Liveness/Safety failure in the FULL model below while preventing regressions.
        
        [STRATEGY]
        {" ".join(strategy_list)}

        [TARGET ASSERTION TO FIX]
        {target_assertion}

        [REGRESSION GUARD - OTHER ASSERTIONS THAT MUST REMAIN VALID]
        {preserve_assertions_block}
        
        [VERIFICATION FAILURE]
        {error_log}
        
        [ORIGINAL MODEL]
        {full_context}
        
        [ASSERTION VALIDITY CHECK - MUST OBEY]
        If the TARGET assertion is NOT a meaningful/valid requirement for this model,
        then you MUST:
        1) Output FIRST LINE exactly:  INVALID_ASSERTION: <one-sentence reason>
        2) Output the FULL ORIGINAL MODEL with NO behavioral changes,
        except append " // INVALID ASSERTION" to the TARGET #assert line.
        Do NOT attempt to "make it pass" by breaking the model.

        [HARD CONSTRAINTS - MUST FOLLOW OR DECLARE INVALID]
        - You are NOT allowed to remove/rename any existing event labels or delete any existing branches.
        (Example forbidden: removing any existing event such as request, grant, update, or notify.)
        - You are NOT allowed to "disable" a branch by making its guard permanently false unless that guard already existed.
        If satisfying the TARGET requires violating any of the above, you MUST output INVALID_ASSERTION mode.

        Otherwise (assertion is valid), output ONLY the FULL repaired model.
        Return ONLY raw CSP# text (no prose, no markdown, no duplicates, no 'atomic').
        """

        try:
            print(f"[*] Calling {self.model_id} for repair...")
            response = self.client.models.generate_content(model=self.model_id, contents=prompt)
            parsed = self._parse_response(response.text)

            output = self._clean_output(parsed["content"])
            sanitized = self._global_sanitizer(output)

            if parsed["status"] == "invalid_assertion":
                base_model = sanitized if sanitized else full_context
                tagged = self._tag_invalid_assertion(base_model, target_assertion)
                return {
                    "status": "invalid_assertion",
                    "model": tagged,
                    "reason": parsed.get("reason") or "No reason provided."
                }

            # If the model "repaired" by deleting too much, force invalid mode
            if self._too_destructive(full_context, sanitized):
                # auto-tag the target assert line yourself
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
                return self.request_repair(
                    full_context=full_context,
                    error_log=error_log,
                    target_assertion=target_assertion,
                    other_assertions=other_assertions
                )
            return {"status": "error", "model": "", "reason": str(e)}

    def _parse_response(self, text):
        stripped = text.replace("```", "").strip()
        if not stripped:
            return {"status": "error", "model": "", "reason": "Empty response", "content": ""}

        lines = stripped.splitlines()
        first_line = lines[0].strip()

        if first_line.startswith(self.INVALID_PREFIX):
            reason = first_line.split(self.INVALID_PREFIX, 1)[1].strip() or "No reason provided."
            # Keep the rest as model content
            content = "\n".join(lines[1:]).strip()
            return {"status": "invalid_assertion", "model": "", "reason": reason, "content": content}

        return {"status": "repaired", "model": "", "reason": None, "content": stripped}
    
    def _extract_event_labels(self, code: str) -> set[str]:
        """
        Heuristic: event labels are tokens followed by '{' or '->' inside process bodies.
        Excludes #define/var/assert lines.
        """
        labels = set()
        process_names = self._extract_process_names(code)
        for line in code.splitlines():
            s = line.strip()
            if not s or s.startswith(("#define", "var", "#assert")):
                continue
            # Grab tokens like event_name{...} or event_name -> NextProc()
            for m in re.finditer(r'\b([A-Za-z_]\w*)\s*(\{|->)', s):
                name = m.group(1)
                # Exclude process definition names discovered from this model.
                if name in process_names:
                    continue
                labels.add(name)
        return labels

    def _extract_process_names(self, code: str) -> set[str]:
        names = set()
        for line in code.splitlines():
            s = line.strip()
            m = re.match(r'^([A-Za-z_]\w*)\s*\(\)\s*=', s)
            if m:
                names.add(m.group(1))
        return names

    def _too_destructive(self, original: str, repaired: str, drop_ratio: float = 0.15) -> bool:
        orig = self._extract_event_labels(original)
        rep = self._extract_event_labels(repaired)
        if not orig:
            return False
        dropped = orig - rep
        return (len(dropped) / len(orig)) > drop_ratio
    
    def _looks_like_starvation_liveness(self, target_assertion: str, error_log: str) -> bool:
        if "[]<>" not in target_assertion:
            return False
        # General starvation-loop signals.
        if "Starvation" in error_log or "SCC" in error_log:
            return True
        if re.search(r'\)\s*\*', error_log):   # matches "... (event)*"
            return True
        return False

    def _clean_output(self, text):
        text = text.replace("```csp", "").replace("```", "").strip()
        match = re.search(r'(#define|var|[\w]+\(\)\s*=)', text)
        return text[match.start():] if match else text

    def _tag_invalid_assertion(self, model_text: str, target_assertion: str) -> str:
        if not model_text or not target_assertion:
            return model_text

        target = target_assertion.strip()
        tagged_lines = []
        tagged = False

        for line in model_text.splitlines():
            if not tagged and line.strip() == target:
                if "// INVALID ASSERTION" not in line:
                    tagged_lines.append(line + " // INVALID ASSERTION")
                else:
                    tagged_lines.append(line)
                tagged = True
            else:
                tagged_lines.append(line)

        if tagged:
            return "\n".join(tagged_lines)

        # Fallback for minor whitespace differences.
        if target in model_text and "// INVALID ASSERTION" not in model_text:
            return model_text.replace(target, target + " // INVALID ASSERTION", 1)

        return model_text

