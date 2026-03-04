import os
import time
import re
from dotenv import load_dotenv
from openai import OpenAI
from rules import RULES

load_dotenv()


class RepairEngine:
    def __init__(self):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("API_KEY missing from .env")

        self.client = OpenAI(
            api_key=api_key, base_url="https://api.deepseek.com", timeout=120
        )

        self.model_id = "deepseek-reasoner"

    def _global_sanitizer(self, code):
        """Final structural check to ensure single declarations and clean syntax."""
        lines = code.split("\n")
        seen_headers = set()
        clean_lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                clean_lines.append("")
                continue

            # 1. Deduplicate: var, #define, or Process() =
            header_match = re.match(r"^(var\s+\w+|#define\s+\w+|\w+\(\)\s*=)", stripped)
            if header_match:
                header = header_match.group(1)
                if header in seen_headers:
                    continue
                seen_headers.add(header)

            # 2. Strip 'atomic' keyword (Parser Error Fix)
            line = re.sub(r"\{atomic\s*\{(.*?)\}\s*\}", r"{\1}", line)
            line = line.replace("atomic{", "{")

            # 3. Ensure #define/var end with ;
            if stripped.startswith(("#define", "var")) and not stripped.endswith(";"):
                line = stripped + ";"

            clean_lines.append(line)

        return "\n".join(clean_lines)

    def request_repair(self, full_context, error_log):
        # Determine strategy: Does the log contain Liveness operators?
        is_liveness = "[]<>" in error_log or "SCC" in error_log
        strategy_list = [RULES["default"]]

        if is_liveness:
            strategy_list.append(RULES["liveness"])
        else:
            strategy_list.append(RULES["safety"])
            strategy_list.append(RULES["lifecycle_coupling"])

        prompt = f"""
        Role: Formal Methods Expert (PAT CSP#).
        Task: Fix the Liveness/Safety failure in the FULL model below.

        [STRATEGY]
        {" ".join(strategy_list)}

        [VERIFICATION FAILURE]
        {error_log}

        [ORIGINAL MODEL]
        {full_context}

        Return the FULL repaired model. No prose. No 'atomic'. No duplicates.
        """

        try:
            print(f"[*] Calling {self.model_id} for repair...")

            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {
                        "role": "system",
                        "content": "You are expert in PAT (Process Analysis Toolkit) and CSP# formal model repair.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4096,
                temperature=0,
            )

            output = self._clean_output(response.choices[0].message.content)
            return self._global_sanitizer(output)

        except Exception as e:
            if "429" in str(e):
                print("[!] Quota hit. Waiting 60s...")
                time.sleep(60)
                return self.request_repair(full_context, error_log)
            return f"Error: {str(e)}"

    def _clean_output(self, text):
        text = text.replace("```csp", "").replace("```", "").strip()
        match = re.search(r"(#define|var|[\w]+\(\)\s*=)", text)
        return text[match.start() :] if match else text
