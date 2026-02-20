"""
Rules configuration for the Model Repair Engine.
These rules guide the LLM to maintain formal logic and syntax integrity.
"""

RULES = {
    # The default rule is applied when an event name doesn't have a specific rule.
    "default": (
        "1. ATOMIC SYNCHRONIZATION: All state updates (variables and arrays) MUST be "
        "wrapped in a single 'atomic{}' block to ensure property consistency.\n"
        "2. SCOPE INTEGRITY: Only use variables and constants defined in the model. "
        "Do not invent new state variables like 'node_state' or 'status'.\n"
        "3. SYNTAX: Ensure the transition follows the format: event{atomic{...}} -> ProcessName().\n"
        "4. CHOICE CHAIN: Do not include a trailing semicolon (;) at the end of the line. "
        "The Choice Operator '[]' must be able to follow this line immediately."
    ),

    "init": (
        "1. GLOBAL STATE: Ensure all variables in the 'var' section are initialized "
        "to a neutral state (e.g., 0 or PROCESSOR_ROLE).\n"
        "2. ARRAY CONSISTENCY: Ensure arrays like 'coordinatorArray' are fully initialized "
        "to match the required system size."
    ),

    "promote_to_coordinator": (
        "1. SELF-ELECTION: When a node promotes itself, it must update its 'role' to "
        "COORDINATOR_ROLE and set ALL indices of 'coordinatorArray' to its own ID.\n"
        "2. ATOMICITY: These updates must happen in one atomic step to satisfy safety assertions."
    ),

    "receive_coordinator_message": (
        "1. FOLLOWER SYNC: When receiving a message, update 'role' to PROCESSOR_ROLE "
        "and synchronize ALL indices of 'coordinatorArray' to the sender's ID.\n"
        "2. GLOBAL VIEW: The property depends on Node1 knowing who leads Node2 and Node3; "
        "therefore, update indices [0], [1], and [2] simultaneously."
    )
}

# Mapping specific event variants to their general rules
RULES["receive_coordinator_message_from_NODE2"] = RULES["receive_coordinator_message"]
RULES["receive_coordinator_message_from_NODE3"] = RULES["receive_coordinator_message"]