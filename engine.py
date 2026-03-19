import json, re, os, time
from dotenv import load_dotenv
from google import genai
from rules import RULES 

load_dotenv()

class ProjectAnalyzer:
    def __init__(self, json_path):
        with open(json_path, 'r') as f:
            self.errors = json.load(f)

    def get_repair_targets(self, entry, full_csp_content):
        """
        Dynamically finds all blocks that touch variables mentioned 
        in the failed assertion by expanding macros.
        """
        assertion = entry.get('assertion', '')
        
        # 1. Improved Macro extraction
        macros = re.findall(r'#define\s+(\w+)\s+\((.*?)\);', full_csp_content)
        macro_map = {name: logic for name, logic in macros}

        # 2. Expand macros in the assertion
        expanded_assertion = assertion
        for name, logic in macro_map.items():
            expanded_assertion = expanded_assertion.replace(name, logic)

        # 3. Identify all actual variables
        potential_vars = set(re.findall(r'\b([a-z][a-zA-Z0-9_]*)\b', expanded_assertion))
        blacklist = {'assert', 'if', 'else', 'true', 'false', 'var', 'one_coordinator'}
        vars_involved = {v for v in potential_vars if v not in blacklist}
        
        # 4. Find ALL events modifying these variables
        found_events = ["init"] 
        for var in vars_involved:
            pattern = rf"(\w+)\s*\{{[^}}]*?{var}(?:\[.*?\])?\s*=[^}}]*?\}}"
            matches = re.findall(pattern, full_csp_content)
            for m in matches:
                if m not in found_events:
                    found_events.append(m)
        
        return found_events

def find_process_block(csp_content, event_name):
    """
    Surgically extracts the target code block (Init block or Process transition).
    """
    if event_name.lower() == "init":
        pattern = r"((?:var\s+[\s\S]*?;)+)"
        match = re.search(pattern, csp_content)
        return match.group(0) if match else None

    pattern = rf"(\[.*?\]\s*)?{event_name}\s*\{{.*?\}}"
    match = re.search(pattern, csp_content)
    if match:
        return match.group(0)
    
    pattern_fallback = rf"{event_name}\s*\{{.*?\}}"
    match = re.search(pattern_fallback, csp_content)
    return match.group(0) if match else None


class RepairEngine:
    INVALID_PREFIX = "INVALID_ASSERTION:"

    def __init__(self, rules_path="pat_rules.md"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY missing from .env")
        
        self.client = genai.Client(api_key=api_key)
        self.model_id = 'gemini-3-flash-preview'
        self.mandatory_syntax = self._load_external_rules(rules_path)

    def _load_external_rules(self, path):
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
        code = re.sub(r'=\s*\[\s*\[(.*?)\]\s*\]', r'= [\1]', code) 
        lines = code.split('\n')
        seen_headers = set()
        clean_lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                clean_lines.append("")
                continue

            header_match = re.match(r'^(var\s+\w+|#define\s+\w+|\w+\(\)\s*=)', stripped)
            if header_match:
                header = header_match.group(1)
                if header in seen_headers: 
                    continue 
                seen_headers.add(header)
            
            line = re.sub(r'\{atomic\s*\{(.*?)\}\s*\}', r'{\1}', line)
            line = line.replace("atomic{", "{")
            
            if stripped.startswith(("#define", "var")) and not stripped.endswith(";"):
                line = stripped + ";"
            
            clean_lines.append(line)
            
        return '\n'.join(clean_lines)

    def request_repair(self, full_context, error_log, target_assertion="", other_assertions=None, desired_result="Valid"):
        """Main entry point to request a model repair from Gemini."""
        
        # Detect if we are in a Syntax Error loop
        is_syntax_error = target_assertion in ["SYNTAX_CHECK", "PARSING", "EXECUTION"] or "failed to parse" in error_log
        is_liveness = "[]<>" in error_log or "SCC" in error_log
        
        # Load the foundational rules that apply to EVERY model
        strategy_list = [
            "### CORE SYNTAX & INITIALIZATION ###\n" + RULES["default"]
        ]
        
        other_assertions = other_assertions or []
        preserve_assertions_block = "\n".join(other_assertions) if other_assertions else "(none)"
        
        # --- NEW LOGIC: SYNTAX OVERRIDE ---
        # --- NEW LOGIC: SYNTAX OVERRIDE ---
        if is_syntax_error:
            strategy_list.append(
                "### SYNTAX REPAIR STRATEGY (CRITICAL) ###\n"
                "1. DO NOT change the logical architecture of the model.\n"
                "2. Review the error trace strictly to find the line number and missing token.\n"
                "3. Fix missing semicolons (;) after 'var' and '#define' declarations.\n"
                "4. Fix PAT prefix syntax (ensure '[]' is used for choice, and no semicolons separate branches).\n"
                "5. Ensure variables are updated inside curly braces like {var = val;}."
            )
            task_directive = (
                f"CRITICAL TASK: The model has a SYNTAX ERROR and failed to compile.\n"
                f"Your EXCLUSIVE goal is to fix the formatting and structural compilation errors described in the trace.\n"
                f"*** YOU MUST STRICTLY FOLLOW ALL SYNTAX RULES DEFINED IN YOUR SYSTEM INSTRUCTIONS (pat_rules.md). ***\n"
                f"Do NOT attempt to fix safety or liveness properties during this pass. ONLY fix the syntax."
            )
        else:
            # Only load the deep architectural rules if the model actually compiled
            strategy_list.extend([
                "### TARGET RESULT ALIGNMENT ###\n" + RULES.get("desired_result_alignment", ""),
                "### INVALIDATION CRITERIA ###\n" + RULES.get("invalid_assertion_criteria", ""),
                "### ARCHITECTURE & SYMMETRY ###\n" + RULES.get("architecture_preservation", ""),
                "### ANTI-OVERFITTING ###\n" + RULES.get("generalization_and_overfitting", ""),
                "### RESOURCE MANAGEMENT ###\n" + RULES.get("resource_management", ""),
                "### CROSS-PROCESS MUTEX ###\n" + RULES.get("cross_process_interlocking", ""),
                "### PHASE DEPENDENCY ###\n" + RULES.get("psl_phase_dependency", ""),
                "### CONCURRENCY ###\n" + RULES.get("concurrency_locking", "")
            ])
            
            if is_liveness:
                strategy_list.append("### LIVENESS FIXES ###\n" + RULES.get("liveness", ""))
            else:
                strategy_list.append("### SAFETY FIXES ###\n" + RULES.get("safety", ""))
                strategy_list.append("### LIFECYCLE COUPLING ###\n" + RULES.get("lifecycle_coupling", ""))

            # DYNAMIC TASK DIRECTIVE based on the desired result
            if str(desired_result).lower() == "invalid":
                task_directive = (
                    f"CRITICAL TASK: The target assertion ({target_assertion}) MUST FAIL. \n"
                    f"Your goal is to INTENTIONALLY EXPOSE A FLAW (e.g., allow starvation, deadlock, or race conditions) "
                    f"so that this specific assertion evaluates to INVALID. Do NOT use fairness injections here."
                )
            else:
                task_directive = (
                    f"CRITICAL TASK: The target assertion ({target_assertion}) MUST PASS. \n"
                    f"Your goal is to FIX the model so this assertion evaluates to VALID."
                )

        formatted_strategies = "\n\n".join(strategy_list)

        prompt = f"""
        Role: Formal Methods Expert (PAT CSP#).
        {task_directive}
        
        [STRATEGY]
        {formatted_strategies}

        [TARGET ASSERTION]
        {target_assertion}
        REQUIRED FINAL RESULT: {str(desired_result).upper()}

        [REGRESSION GUARD (DO NOT BREAK THESE)]
        {preserve_assertions_block}
        
        [VERIFICATION FAILURE TRACE]
        {error_log}
        
        [ORIGINAL MODEL]
        {full_context}
        
        [INSTRUCTIONS]
        - Output ONLY the FULL repaired model.
        - You MUST follow the syntax examples provided in the system context.
        - Return ONLY raw CSP# text (no prose, no markdown).
        """

        try:
            print(f"[*] Calling {self.model_id} (Target: {str(desired_result).upper()})...")
            response = self.client.models.generate_content(
                model=self.model_id, 
                contents=prompt,
                config={'system_instruction': self.mandatory_syntax}
            )
            
            parsed = self._parse_response(response.text)
            output = self._clean_output(parsed["content"])
            sanitized = self._global_sanitizer(output)

            # if parsed["status"] == "invalid_assertion":
            #     base_model = sanitized if sanitized else full_context
            #     tagged = self._tag_invalid_assertion(base_model, target_assertion)
            #     return {
            #         "status": "invalid_assertion",
            #         "model": tagged,
            #         "reason": parsed.get("reason") or "No reason provided."
            #     }

            # if self._too_destructive(full_context, sanitized, drop_ratio=0.50):
            #     tagged = self._tag_invalid_assertion(full_context, target_assertion)
            #     return {
            #         "status": "invalid_assertion",
            #         "model": tagged,
            #         "reason": "Repair required deleting/renaming existing event branches; violates non-destructive constraint."
            #     }

            return {"status": "repaired", "model": sanitized, "reason": None}

        except Exception as e:
            if "429" in str(e):
                print("[!] Quota hit. Waiting 60s..."); time.sleep(60)
                return self.request_repair(full_context, error_log, target_assertion, other_assertions, desired_result)
            return {"status": "error", "model": "", "reason": str(e)}
        
    def _parse_response(self, text):
        stripped = text.replace("```csp", "").replace("```", "").strip()
        if not stripped:
            return {"status": "error", "model": "", "reason": "Empty response", "content": ""}

        lines = stripped.splitlines()
        first_line = lines[0].strip()

        # Catch INVALID_ASSERTION even if it's jumbled on the first line
        if "INVALID_ASSERTION" in first_line:
            reason = first_line.replace("INVALID_ASSERTION", "").replace(":", "").strip()
            # Drop the contaminated first line entirely so it doesn't pollute the code
            content = "\n".join(lines[1:]).strip()
            return {"status": "invalid_assertion", "model": "", "reason": reason, "content": content}

        return {"status": "repaired", "model": "", "reason": None, "content": stripped}

    def _clean_output(self, text):
        match = re.search(r'(#define|var|[\w]+\(\)\s*=)', text)
        return text[match.start():] if match else text

    def _tag_invalid_assertion(self, model_text, target_assertion):
        if not model_text or not target_assertion: return model_text
        target = target_assertion.strip()
        
        # 1. Clean up any raw text the LLM might have injected directly in the body
        model_text = re.sub(r'INVALID_ASSERTION\s*' + re.escape(target), target, model_text)
        
        # 2. Safely comment out the entire assertion so it's structurally sound
        if target in model_text:
            replacement = f"// {target} // FLAGGED INVALID BY ENGINE"
            return model_text.replace(target, replacement, 1)
            
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

    def _too_destructive(self, original, repaired, drop_ratio=0.50):
        orig = self._extract_event_labels(original)
        rep = self._extract_event_labels(repaired)
        if not orig: return False
        return (len(orig - rep) / len(orig)) > drop_ratio