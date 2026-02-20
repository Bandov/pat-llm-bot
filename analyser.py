import json, re

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
    # CASE 1: Initialization / Global Variables
    if event_name.lower() == "init":
        pattern = r"((?:var\s+[\s\S]*?;)+)"
        match = re.search(pattern, csp_content)
        return match.group(0) if match else None

    # CASE 2: Process transitions with guards [guard] event { mutation }
    # This regex handles the choice operator [] and multi-line blocks
    pattern = rf"(\[.*?\]\s*)?{event_name}\s*\{{.*?\}}"
    match = re.search(pattern, csp_content)
    if match:
        return match.group(0)
    
    # Fallback: Event without guards
    pattern_fallback = rf"{event_name}\s*\{{.*?\}}"
    match = re.search(pattern_fallback, csp_content)
    return match.group(0) if match else None