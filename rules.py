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
        "   Only terminate the entire process definition once at the end with a single ';' (if needed).\n"
        "8. TURN-TAKING RULE: If using a turn variable, put 'turn == k' inside each branch guard,\n"
        "   e.g. [turn==1 && ...] action{turn=2;} -> Proc(). Do NOT wrap choices in [turn==k](...)."
        "\n"
        "9. ASSERTION PRESERVATION (ABSOLUTE): You are STRICTLY FORBIDDEN from deleting, modifying, "
        "   or commenting out any '#assert' lines, '#define' macros used in assertions, or initial "
        "   state variable declarations. The test criteria must remain exactly as provided.\n"
        "10. CONTROLLED REFACTORING: You MAY delete or modify specific event branches within a process "
        "    IF AND ONLY IF they cause race conditions, deadlocks, or bypass global synchronization. "
        "    However, you MUST NOT delete an entire process definition or remove an actor's ability to "
        "    participate in the system.\n"
        "11. REFACTORING AUTHORITY: You have explicit permission to add new global variables \n"
        "   and append new conditions to existing guards to solve starvation or race conditions."
    ),

    "invalid_assertion_criteria": (
        "1. ALLOWLIST (WHEN TO FLAG INVALID): You may ONLY use INVALID_ASSERTION if:\n"
        "   - The assertion is mathematically contradictory (e.g., A == 1 && A == 0).\n"
        "2. STRICT BLOCKLIST (WHEN TO REPAIR): You are STRICTLY FORBIDDEN from returning INVALID_ASSERTION for:\n"
        "   - Liveness properties ([]<>) failing due to infinite traces or loops.\n"
        "   - Safety properties failing due to RACE CONDITIONS, OVERWRITTEN STATES, or poor guard logic.\n"
        "   - Traces containing unrecognized system logs.\n"
        "   Instead of calling the model invalid, you MUST apply the relevant repair tactics to fix the code."
    ),
    
    "trace_processing": (
        "1. NOISE FILTERING: Actively ignore all environment lines containing 'wineboot', 'MoltenVK', \n"
        "   'mvk-info', or 'Vulkan'. These do NOT indicate a syntax error.\n"
        "2. SIGNAL IDENTIFICATION: Locate the string '********Verification Result********'. \n"
        "   - If 'NOT valid' follows, apply Safety/Liveness repair strategies.\n"
        "   - If this string is missing AND there are no '[Error]' tags, assume the environment failed, not the syntax."
    ),

    "safety": (
        "1. PROACTIVE GATING: If A -> B must hold, add [B] as a mandatory guard to the \n"
        "   event that makes A true. \n"
        "2. INVARIANT ALIGNMENT: Ensure guards match the macro definitions exactly.\n"
        "3. IMPLICATION GUARDING: For properties shaped like [] (A -> B), either:\n"
        "   - gate transitions that make A true so B already holds, or\n"
        "   - atomically update state so B is established in the same step."
        "4. ANTI-TRIVIALIZATION: You must not fix safety violations by permanently locking the system "
        "   (e.g., making a 'start' guard mathematically impossible). The system must retain its ability "
        "   to execute its primary intended workflow."
        "5. RESOURCE LOCK INTEGRITY (CRITICAL): NEVER release a global resource lock (e.g., setting "
        "   lineState = IDLE) while transitioning actors into an active or engaged phase (e.g., connect_call). "
        "   The shared lock MUST be held for the entire duration of the engagement and ONLY released "
        "   during terminal actions (e.g., hang_up, disconnect, or rejection)."
        "6. IDENTITY TRACKING & PERSISTENCE (CRITICAL): Do not define completion or ownership \n"
        "   based on temporary physical proximity (e.g., Robot_position == Item_position). \n"
        "   Use dedicated state variables (e.g., var C1_Maker = 1;) assigned exactly when the task finishes."
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

    "resource_management": (
        "1. ATOMIC RESOURCE CLAIMING: When an actor (e.g., Train) moves to a shared resource, \n"
        "   it MUST update the availability flag (e.g., signal = RED) in the SAME event update block '{...}'.\n"
        "2. MONITOR ANTI-PATTERN REMOVAL: Do NOT use separate asynchronous processes (e.g., Track()) \n"
        "   to monitor physical positions and update locks. Delete these monitor processes and merge \n"
        "   the lock/signal updates directly into the actor's transition."
    ),

    "liveness": (
        "1. FAIRNESS INJECTION TEMPLATE (MANDATORY): To fix starvation in interleaved processes,\n"
        "   you MUST inject a scheduler. \n"
        "   - Add 'var turn = 0;' at the top of the file.\n"
        "   - Append '&& turn == 0' to Process A's guards, and add '{turn = 1;}' to its updates.\n"
        "   - Append '&& turn == 1' to Process B's guards, and add '{turn = 0;}' to its updates.\n"
        "   in explanation, if one process prevents others from acting, add a "
            "turn-taking variable or a guard that forces the process to yield after an action.\n"
        "2. LOOP BREAKING: Use progress counters or turn variables to force states to exit loops."
        "3. LIVENESS COMPLETION: For []<>Goal, ensure every cycle in the state graph contains "
        "   the 'Goal' event or a state where the 'Goal' condition is true.\n"
        "4. STARVATION VALIDITY CHECK: If fixing starvation requires enforcing a particular scheduling "
        "   outcome that contradicts a safety constraint (e.g., forcing a physical system to exceed its "
        "   capacity), you must leave the liveness assertion to fail rather than breaking safety.\n"
        "5. LOCAL-OBLIGATION-FIRST: Prioritize local service before movement/phase change."
        "6. TRANSIENT STATE FALLBACKS (CRITICAL): If a local actor enters a transient state \n"
        "   (e.g., DIALING, WAITING, REQUESTING) to use a shared global resource, the global \n"
        "   manager MUST have branches to handle that state for ALL resource conditions. If the \n"
        "   resource is BUSY, you MUST add a rejection/fallback branch to bounce the actor back \n"
        "   to an IDLE state. Never leave an actor trapped waiting for a busy resource that \n"
        "   cannot respond to them."
        "7. STUTTERING PREVENTION: If the trace shows a process repeating the same two events "
        "   without progress (e.g., start -> stop -> start), add a 'Progress Guard'.\n"
    ),

    "lifecycle_coupling": (
        "1. STARVATION CHECK: Ensure safety guards do not create deadlocks (that violates liveness, for example).  Every 'start' must eventually have a 'stop' path. \n"
        "   If a deadlock occurs, add a 'reset' branch or a higher-priority event to unblock the system.\n"
        "2. PHASE-DEPENDENCY GATING: Require downstream actions (e.g. Product) to enable only \n"
        "   after upstream assignment/activation states (e.g. Component_ismade) are reached/finalized."
        "3. CYCLE CLEANUP: On terminal actions of a cycle, reset transient stage flags.\n"
        "4. GLOBAL SYNCHRONIZATION OVERRIDE: If a local process has a branch that unilaterally resets "
        "   its state while a global controller (e.g., a network, a kitchen head chef) is still processing "
        "   that actor, DELETE the local reset branch. Force the local actor to wait for the global "
        "   controller's transition to release them."
    ),
    
    "generalization_and_overfitting": ( # first implemented by telecom
        "1. NO ASSERTION OVERFITTING (ABSOLUTE): You are strictly forbidden from hardcoding "
        "specific actor IDs, variable indices (e.g., 'caller == 0', 'handsetStates[2]'), or "
        "state values directly from #assert properties into process guards just to satisfy a "
        "mismatch trace. Any transition parameterized by generic variables (like 'i', 'caller', "
        "'target', or 'robot') MUST apply symmetrically to all actors. Never break the model's "
        "generalized abstraction to force a test to pass.\n"
        "2. RESOURCE ABSTRACTION: If an assertion dictates mutual exclusion, enforce this by modeling "
        "   a shared resource limit (e.g., 'active_calls < MAX', 'Track1_signal == SIGNAL_GREEN'), "
        "   NOT by writing exclusionary logic for specific actors.\n"
        "3. ACTOR SYMMETRY: Process definitions parameterized by generic variables must remain "
        "   mathematically symmetric. Never evaluate the absolute integer value of a generic parameter."
    ),

    "architecture_preservation": ( # first implemented by telecom
        "1. PROCESS FRAGMENTATION BAN (ABSOLUTE): You MUST NOT artificially split a single "
        "controller process into multiple sub-processes (e.g., creating Proc_Ringing, Proc_Engaged). "
        "You MUST use a single unified process with comprehensive guards (e.g., [lineState == BUSY]) "
        "to handle all phases. Fragmentation creates blind spots that cause deadlocks.\n"
        "2. OVERLOADED TRANSIENT STATES: If multiple actors share the same transient state (e.g., both "
        "Callers and Targets use 'WAITING'), local processes might allow an actor to trigger an "
        "anomalous event (e.g., a Caller triggering 'ignore_call'). Your unified global manager MUST "
        "include catch-all fallback branches to safely reset these anomalous local state changes."
    )
}