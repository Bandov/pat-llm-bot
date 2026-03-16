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
        "7. EMPTY BRACES BAN (ABSOLUTE): You are STRICTLY FORBIDDEN from generating empty curly braces '{}'. "
        "   If an event has no state updates, you MUST completely omit the braces (e.g., write 'event -> Proc()', "
        "   NEVER 'event{} -> Proc()'). Writing 'event{}' will cause a fatal syntax parsing error.\n"
        "8. CHOICE SYNTAX (CRITICAL): Use '[]' between branches. Do NOT put ';' after each branch.\n"
        "   Only terminate the entire process definition once at the end with a single ';' (if needed).\n"
        "9. NO TERNARY OPERATORS: You are STRICTLY FORBIDDEN from using ternary operators (e.g., 'condition ? true : false') "
        "   inside state updates. PAT CSP# does not parse them. If you need conditional logic during an update, you MUST use "
        "   standard 'if (cond) { ... } else { ... }' blocks inside the curly braces.\n"
        "10. TURN-TAKING RULE: If using a turn variable, put 'turn == k' inside each branch guard,\n"
        "   e.g. [turn==1 && ...] action{turn=2;} -> Proc(). Do NOT wrap choices in [turn==k](...).\n"
        "11. ASSERTION PRESERVATION & INITIALIZATION (CRITICAL): You are STRICTLY FORBIDDEN from deleting, modifying, "
        "   or commenting out any '#assert' lines or '#define' macros used in assertions. \n"
        "   EXCEPTION: If an assertion fails at the '<init>' trace, you ARE EXPLICITLY AUTHORIZED AND REQUIRED "
        "   to change the initial assigned values of global 'var' declarations so they do not violate the "
        "   invariants at step 0 (e.g., separating starting positions or defaulting signals to safe states).\n"
        "12. CONTROLLED REFACTORING: You MAY delete or modify specific event branches within a process "
        "    IF AND ONLY IF they cause race conditions, deadlocks, or bypass global synchronization. "
        "    However, you MUST NOT delete an entire process definition or remove an actor's ability to "
        "    participate in the system.\n"
        "13. REFACTORING AUTHORITY: You have explicit permission to add new global variables \n"
        "   and append new conditions to existing guards to solve starvation or race conditions."
    ),

    "desired_result_alignment": (
        "1. TARGET RESULT AWARENESS (CRITICAL): Always check the REQUIRED FINAL RESULT. "
        "   Do NOT blindly attempt to make all assertions 'Valid'.\n"
        "2. INTENTIONAL INVALIDATION: If the required result is 'INVALID', you MUST modify the model "
        "   so that the assertion FAILS. For liveness properties ([]<> or <>), do NOT add fairness variables. "
        "   Instead, ensure the model can deadlock, livelock, or allow starvation.\n"
        "3. PRESERVING NEGATIVE PROPERTIES: If fixing a 'Valid' safety property inadvertently makes "
        "   a liveness property 'Valid' (when it should be 'Invalid'), adjust your fix to ensure "
        "   it still allows the liveness failure.\n"
        "4. SYMMETRIC STARVATION (CRITICAL): If symmetric assertions (e.g., <> Track1 and <> Track2) MUST BOTH be INVALID, "
        "   the model MUST allow symmetric infinite loops. Track 1 must be able to infinitely loop without Track 2 ever starting, "
        "   AND Track 2 must be able to infinitely loop without Track 1 ever starting. Do not hardcode a forced starting sequence."
        "5. REACHABILITY INJECTION: If a '#assert ... reaches [State]' property evaluates to INVALID but MUST be VALID, "
        "   it means the target state is mathematically impossible to reach in the current logic. You MUST explicitly "
        "   inject a new event branch or modify an existing guard to ALLOW that specific combination of variables "
        "   (e.g., adding a specific event that allows the engine to be turned off while driving)."
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
        "   - atomically update state so B is established in the same step.\n"
        "4. ANTI-TRIVIALIZATION: You must not fix safety violations by permanently locking the system "
        "   (e.g., making a 'start' guard mathematically impossible). The system must retain its ability "
        "   to execute its primary intended workflow.\n"
        "5. RESOURCE LOCK INTEGRITY (CRITICAL): NEVER release a global resource lock (e.g., setting "
        "   lineState = IDLE) while transitioning actors into an active or engaged phase (e.g., connect_call). "
        "   The shared lock MUST be held for the entire duration of the engagement and ONLY released "
        "   during terminal actions (e.g., hang_up, disconnect, or rejection).\n"
        "6. IDENTITY TRACKING & PERSISTENCE (CRITICAL): Do not define completion or ownership \n"
        "   based on temporary physical proximity (e.g., Robot_position == Item_position). \n"
        "   Use dedicated state variables (e.g., var C1_Maker = 1;) assigned exactly when the task finishes.\n"
        "7. INITIALIZATION RESOLUTION: If the verification trace is exactly '<init>', immediately inspect the "
        "   global variables. You MUST alter their starting values to logically space out actors or restrict "
        "   resources so the system starts in a mathematically safe state."
        "8. PHYSICAL CONFINEMENT: Actors cannot perform physical transitions (e.g., exiting a vehicle) "
        "   if the parent container is in an active/moving state. You MUST gate 'exit' or 'leave' events "
        "   by requiring the system to be STOPPED (e.g., 'drivingStatus == DRIVING_STOPPED').\n"
        "9. RESOURCE DEPLETION SIDE-EFFECTS: If an event depletes a vital resource to EMPTY (e.g., fuel), "
        "   it MUST atomically update the dependent active states in the same block. If fuel goes to EMPTY, "
        "   you MUST force 'drivingStatus = DRIVING_STOPPED' and 'engineStatus = ENGINE_OFF' simultaneously.\n"
        "10. CONDITIONAL LOCKING (NO TRAPPING): Prevent locked-in or locked-out states by checking container "
        "    contents before sealing. Do NOT allow a door to 'lock' if the key is inside but the owners are outside."
    ),

    "cross_process_interlocking": (
        "1. MUTUAL EXCLUSION GUARDS: If two interleaved processes manage mutually exclusive resources "
        "   (e.g., two tracks that cannot both be green), you MUST inject cross-process guard checks. "
        "   Process A cannot claim the active state without explicitly verifying Process B is in the inactive state "
        "   (e.g., Track1 turning green MUST require `Track2_signal == SIGNAL_RED`).\n"
        "2. SHARED RESOURCE CONTENTION: Prevent two actors from evaluating the same open resource simultaneously. "
        "   If multiple actors can trigger a transition based on identical global conditions, inject a state update "
        "   or ownership flag in the very first transition to immediately invalidate the guard for the other actor."
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

    "psl_phase_dependency": (
        "1. PHASE-TRANSITION COMPLETENESS: If an actor moves from Phase A to Phase B to achieve a goal, "
        "   ensure the 'Phase Change' event is guarded by the successful completion of Phase A.\n"
        "2. COMPLEMENTARY CHANNEL LOGIC: In distributed models, if Node A sends a message, "
        "   the receiving Node B MUST have a corresponding branch to consume that state change.\n"
        "3. HANDSHAKE INTEGRITY: For every 'request' event, there MUST be both a 'grant' and a 'deny' "
        "   path to prevent an actor from being permanently stuck in a REQUESTING state.\n"
        "4. PHASE HARMONIZATION (DEADLOCK ESCAPE HATCH): If a trace shows a deadlock because an event updated "
        "   a phase tracker (e.g., 'progress_phase = 7') but the next logical event expects a different phase "
        "   (e.g., 'progress_phase == 0'), you are EXPLICITLY AUTHORIZED to modify the guards of the blocked "
        "   events to accept the new phase (e.g., changing to 'progress_phase == 0 || progress_phase == 7') "
        "   to restore the lifecycle flow."
    ),

    "liveness": (
        "1. FAIRNESS INJECTION RULES: ONLY inject a scheduler/turn-variable if the required result for the "
        "   liveness assertion is 'VALID'. If the desired result is 'INVALID', DO NOT inject fairness.\n"
        "   - Add 'var turn = 0;' at the top of the file.\n"
        "   - Append '&& turn == 0' to Process A's guards, and add '{turn = 1;}' to its updates.\n"
        "   - Append '&& turn == 1' to Process B's guards, and add '{turn = 0;}' to its updates.\n"
        "   If one process prevents others from acting, add a turn-taking variable or a guard that forces yielding.\n"
        "2. LOOP BREAKING: Use progress counters or turn variables to force states to exit loops.\n"
        "3. LIVENESS COMPLETION: For []<>Goal, ensure every cycle in the state graph contains "
        "   the 'Goal' event or a state where the 'Goal' condition is true.\n"
        "4. STARVATION VALIDITY CHECK: If fixing starvation requires enforcing a particular scheduling "
        "   outcome that contradicts a safety constraint, leave the liveness assertion to fail.\n"
        "5. LOCAL-OBLIGATION-FIRST: Prioritize local service before movement/phase change.\n"
        "6. TRANSIENT STATE FALLBACKS (CRITICAL): If a local actor enters a transient state \n"
        "   to use a shared global resource, the global manager MUST have branches to handle that state. "
        "   If the resource is BUSY, you MUST add a rejection/fallback branch to bounce the actor back.\n"
        "7. STUTTERING PREVENTION: If the trace shows a process repeating the same two events "
        "   without progress, add a 'Progress Guard'.\n"
        "8. NON-PRODUCTIVE LOOP BREAKING (LIVENESS ESCAPE HATCH): If a liveness assertion ([]<>) fails "
        "   because an actor can infinitely loop through reversible, non-productive events (e.g., approach "
        "   -> leave -> approach) without ever triggering the goal, you MUST break the loop. You are AUTHORIZED "
        "   to restrict the 'leave' or 'abort' branches by adding phase guards or counters so that once an "
        "   actor commits to a sequence, they are forced to progress toward the liveness goal.\n"
        "9. FORCED PROGRESSION (STUTTERING FIX): If a liveness trace shows an actor "
        "   repeatedly performing reversible actions (e.g., approach -> leave) or "
        "   idling (e.g., motor_idle -> motor_pass) without reaching the Goal, "
        "   you MUST inject a 'Commitment Guard.' \n"
        "   - Create a 'progress' variable (e.g., var goal_reached = false;). \n"
        "   - Once a critical step is taken (e.g., owner enters car), set it to true. \n"
        "   - Use this variable to disable 'reversal' events (like owner_leave or motor_idle) "
        "     so the system is forced to move toward the terminal Goal."
        "10. INTERRUPT RECOVERY (CRITICAL): If a global liveness property ([]<> Goal) must be VALID, "
        "    but the model contains a terminal interrupt (e.g., 'interrupt (event -> Stop)'), the liveness "
        "    will inevitably fail because 'Stop' deadlocks the system. You MUST replace 'Stop' with a recursive "
        "    call to the main system process (e.g., 'interrupt (event -> recover -> SystemProc)') so the model can continue."
        "11. ERROR-RECOVERY LIVELOCKS (INTERRUPT THROTTLING): If a liveness trace shows an infinite loop "
        "    where the system repeatedly triggers an error/interrupt (e.g., 'water_sensor_high') and recovers "
        "    without ever reaching the goal (e.g., 'start_driving'), you MUST throttle the interrupt. "
        "    Introduce a state variable (e.g., 'var hazard_active = 0;') that prevents the interrupt from firing "
        "    again until the primary liveness goal has been successfully executed at least once."
    ),

    "resource_management": (
        "1. ATOMIC RESOURCE CLAIMING: When an actor moves to a shared resource, \n"
        "   it MUST update the availability flag in the SAME event update block '{...}'.\n"
        "2. MONITOR ANTI-PATTERN REMOVAL: Do NOT use separate asynchronous processes to monitor "
        "   physical positions and update locks. Merge the lock updates directly into the actor's transition."
    ),

    "lifecycle_coupling": (
        "1. STARVATION CHECK: Ensure safety guards do not create deadlocks. Every 'start' must "
        "   eventually have a 'stop' path. If a deadlock occurs, add a 'reset' branch to unblock the system.\n"
        "2. PHASE-DEPENDENCY GATING: Require downstream actions to enable only after upstream "
        "   assignment/activation states are reached/finalized.\n"
        "3. CYCLE CLEANUP: On terminal actions of a cycle, reset transient stage flags.\n"
        "4. GLOBAL SYNCHRONIZATION OVERRIDE: If a local process has a branch that unilaterally resets "
        "   its state while a global controller is still processing that actor, DELETE the local reset branch. "
        "   Force the local actor to wait for the global controller to release them."
    ),
    
    "generalization_and_overfitting": (
        "1. NO ASSERTION OVERFITTING (ABSOLUTE): You are strictly forbidden from hardcoding "
        "specific actor IDs, variable indices (e.g., 'caller == 0'), or state values directly "
        "from #assert properties into process guards just to satisfy a mismatch trace. "
        "Never break the model's generalized abstraction to force a test to pass.\n"
        "2. RESOURCE ABSTRACTION: If an assertion dictates mutual exclusion, enforce this by modeling "
        "   a shared resource limit, NOT by writing exclusionary logic for specific actors.\n"
        "3. ACTOR SYMMETRY: Process definitions parameterized by generic variables must remain "
        "   mathematically symmetric."
    ),

    "architecture_preservation": (
        "1. PROCESS FRAGMENTATION BAN (ABSOLUTE): You MUST NOT split a single "
        "controller process into multiple sub-processes. You MUST use a single unified process.\n"
        "2. OVERLOADED TRANSIENT STATES: If multiple actors share the same transient state, "
        "your unified global manager MUST include catch-all fallback branches to safely reset "
        "anomalous local state changes."
    )
}