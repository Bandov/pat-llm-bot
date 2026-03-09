"""
Rules configuration for the Model Repair Engine.
Generalized patterns for fixing Safety, Liveness, and Syntax in PAT CSP#.
"""

RULES = {
    "default": (
        "1. NO PROSE: Return ONLY raw CSP# code. No conversational filler or markdown.\n"
        "2. FULL-FILE REWRITE: Return the ENTIRE model. Do not use snippets.\n"
        "3. SEMICOLON DISCIPLINE: Every '#define' and 'var' MUST end with a semicolon (;).\n"
        "4. STATE UPDATES: Use '{var = val;}'—STRICTLY FORBIDDEN to use the 'atomic' keyword.\n"
        "5. DEDUPLICATION: Declare each 'var' and process EXACTLY once. Group vars at the top.\n"
        "6. PAT PREFIX SYNTAX (CRITICAL): Every branch MUST be written as:\n"
        "   - [guard] event -> NextProc()\n"
        "   - [guard] event{updates;} -> NextProc()\n"
        "   - event -> NextProc()\n"
        "   - event{updates;} -> NextProc()\n"
        "7. CHOICE SYNTAX (CRITICAL): Use '[]' between branches. Do NOT put ';' after each branch.\n"
        "8. REFACTORING AUTHORITY: You have explicit permission to add new global variables \n"
        "   and append new conditions to existing guards to solve starvation or race conditions."
    ),

    "invalid_assertion_criteria": (
        "1. ALLOWLIST (WHEN TO FLAG INVALID): You may ONLY use INVALID_ASSERTION if:\n"
        "   - The assertion is mathematically contradictory (e.g., A == 1 && A == 0).\n"
        "   - The model's core syntax is too broken to parse.\n"
        "2. BLOCKLIST (WHEN TO REPAIR): You are STRICTLY FORBIDDEN from using INVALID_ASSERTION if:\n"
        "   - The failure is a Liveness property ([]<>) failing due to an infinite trace.\n"
        "   - The failure is a Safety property failing due to a RACE CONDITION or OVERWRITTEN STATE. \n"
        "     You MUST fix this by implementing a Lock/Semaphore or a Status variable."
    ),

    "safety": (
        "1. PROACTIVE GATING: If A -> B must hold, add [B] as a mandatory guard to the \n"
        "   event that makes A true. \n"
        "2. INVARIANT ALIGNMENT: Ensure guards match the macro definitions exactly.\n"
        "3. IDENTITY TRACKING: If multiple processes (e.g. Robot1, Robot2) can trigger an event, \n"
        "   assign an ID variable (e.g. 'var made_by = 0;') to track the specific actor."
    ),

    "concurrency_locking": (
        "1. MUTEX PATTERN: To prevent race conditions in interleaved (|||) processes, \n"
        "   inject a boolean lock (e.g., 'var task_locked = false;').\n"
        "   - Guard the 'start' event with '&& !task_locked'.\n"
        "   - Update the 'start' event with '{task_locked = true;}'.\n"
        "   - Update the 'finish' event with '{task_locked = false;}'.\n"
        "2. STATE ENUMERATION: Replace binary flags with status variables (0: IDLE, 1: BUSY, 2: DONE) \n"
        "   to ensure processes do not overwrite progress."
    ),

    "liveness": (
        "1. FAIRNESS INJECTION TEMPLATE (MANDATORY): To fix starvation in interleaved processes,\n"
        "   you MUST inject a scheduler. \n"
        "   - Add 'var turn = 0;' at the top of the file.\n"
        "   - Append '&& turn == 0' to Process A's guards, and add '{turn = 1;}' to its updates.\n"
        "   - Append '&& turn == 1' to Process B's guards, and add '{turn = 0;}' to its updates.\n"
        "2. LOOP BREAKING: Use progress counters or turn variables to force states to exit loops."
    ),

    "lifecycle_coupling": (
        "1. STARVATION CHECK: Ensure safety guards do not create deadlocks. If a deadlock occurs,\n"
        "   add a 'reset' branch or a higher-priority event to unblock the system.\n"
        "2. PHASE-DEPENDENCY GATING: Require downstream actions (e.g. Product) to enable only \n"
        "   after upstream states (e.g. Component_ismade) are finalized."
    )
}