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
        "5. DEDUPLICATION: Declare each 'var' and process EXACTLY once. Group vars at the top."
    ),

    "safety": (
        "1. EXIT GUARD: To fix P -> Q violations, inhibit the Provider from stopping if a "
        "Consumer is active: [Provider_Active && Class_Empty] stop -> ...\n"
        "2. INVARIANT ALIGNMENT: Ensure guards match the macro definitions exactly."
    ),

    "liveness": (
        "1. STUTTERING PREVENTION: If the trace shows a process repeating the same two events "
        "without progress (e.g., start -> stop -> start), add a 'Progress Guard'.\n"
        "2. FAIRNESS (ANTI-HOGGING): If one process prevents others from acting, add a "
        "turn-taking variable or a guard that forces the process to yield after an action.\n"
        "   - Example: var turn = 1; ... [turn == 1] action{turn = 2;} -> Proc()\n"
        "3. LIVENESS COMPLETION: For []<>Goal, ensure every cycle in the state graph contains "
        "the 'Goal' event or a state where the 'Goal' condition is true."
    ),

    "lifecycle_coupling": (
        "1. STARVATION CHECK: Ensure that guards added for Safety do not accidentally "
        "create a deadlock that violates Liveness. Every 'start' must eventually have a 'stop' "
        "path that is reachable."
    ),

    "generalization_and_overfitting": (
        "1. NO ASSERTION OVERFITTING: You are strictly forbidden from copying specific variable "
        "indices (e.g., user '0' or '1') or specific state values directly from #assert properties "
        "into process guards just to satisfy a mismatch trace.\n"
        "2. RESOURCE ABSTRACTION: If an assertion dictates that multiple specific events cannot "
        "occur concurrently (mutual exclusion), enforce this by modeling a shared resource limit "
        "(e.g., a global 'active_calls' counter), NOT by writing exclusionary logic for specific actors.\n"
        "3. ACTOR SYMMETRY: Process definitions parameterized by generic variables (like 'caller' "
        "or 'target') must remain mathematically symmetric. Never evaluate the absolute integer "
        "value of a generic parameter to restrict flow."
    )
}