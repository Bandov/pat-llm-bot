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
        "   FORBIDDEN forms:\n"
        "   - (event{...}) -> NextProc()\n"
        "   - ([guard] event{...}) -> NextProc()\n"
        "   - [cond] ( ...choice... )  (do NOT guard a whole parenthesized choice)\n"
        "7. CHOICE SYNTAX (CRITICAL): Use '[]' between branches. Do NOT put ';' after each branch.\n"
        "   Only terminate the entire process definition once at the end with a single ';' (if needed).\n"
        "8. TURN-TAKING RULE: If using a turn variable, put 'turn == k' inside each branch guard,\n"
        "   e.g. [turn==1 && ...] action{turn=2;} -> Proc(). Do NOT wrap choices in [turn==k](...)."
        "\n"
        "9. NON-DESTRUCTIVE EDITS (CRITICAL): You MUST NOT delete, rename, or remove any existing event labels\n"
        "   or branches from any process. You may only add guards/updates/extra branches.\n"
        "   If the TARGET assertion cannot be satisfied without deleting/renaming/neutralizing an event branch,\n"
        "   you MUST use INVALID_ASSERTION mode.\n"
        "10. NO MACRO INLINING: Do NOT replace macro names with numbers (e.g. keep PROCESSOR_ROLE not '2').\n"
        "    Keep #define usage consistent with the original.\n"
    ),

    "safety": (
        "1. EXIT GUARD: To fix P -> Q violations, inhibit the Provider from stopping if a "
        "Consumer is active: [Provider_Active && Class_Empty] stop -> ...\n"
        "2. INVARIANT ALIGNMENT: Ensure guards match the macro definitions exactly.\n"
        "3. IMPLICATION GUARDING: For properties shaped like [] (A -> B), either:\n"
        "   - gate transitions that make A true so B already holds, or\n"
        "   - atomically update state so B is established in the same step."
    ),

    "liveness": (
        "1. STUTTERING PREVENTION: If the trace shows a process repeating the same two events "
        "without progress (e.g., start -> stop -> start), add a 'Progress Guard'.\n"
        "2. FAIRNESS (ANTI-HOGGING): If one process prevents others from acting, add a "
        "turn-taking variable or a guard that forces the process to yield after an action.\n"
        "   - Example: var turn = 1; ... [turn == 1] action{turn = 2;} -> Proc()\n"
        "3. LIVENESS COMPLETION: For []<>Goal, ensure every cycle in the state graph contains "
        "the 'Goal' event or a state where the 'Goal' condition is true."
        "4. STARVATION VALIDITY CHECK (GENERAL): If the failure is Liveness (Starvation) or SCC/cycle-based,\n"
        "   and the counterexample shows an infinite repetition '(e)*' or a loop that avoids the goal,\n"
        "   then the TARGET likely assumes fairness that is NOT modeled.\n"
        "   If fixing it would require enforcing a particular scheduling outcome (e.g., forcing a specific branch\n"
        "   to eventually be taken) or adding global fairness constraints, use INVALID_ASSERTION mode.\n"
        "5. PROGRESS GUARDS: Break stuttering/oscillation SCCs by adding guards that force exit toward unresolved obligations.\n"
        "6. LOCAL-OBLIGATION-FIRST: If an actor can service pending local work or move away, prioritize local service before movement/phase change.\n"
    ),

    "lifecycle_coupling": (
        "1. STARVATION CHECK: Ensure that guards added for Safety do not accidentally "
        "create a deadlock that violates Liveness. Every 'start' must eventually have a 'stop' "
        "path that is reachable.\n"
        "2. PHASE-DEPENDENCY GATING: For multi-stage workflows, require downstream actions to be enabled only\n"
        "   after upstream assignment/activation states are reached.\n"
        "3. CYCLE CLEANUP: On terminal actions of a cycle, reset transient stage flags so the next cycle must\n"
        "   re-establish prerequisites through the intended dependency chain."
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