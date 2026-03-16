# PAT CSP# Mandatory Syntax & Examples

## 1. Semicolon Rules (;)
- [cite_start]**Rule**: Required after #define, var, enum, and #assert[cite: 1, 2, 3, 5, 7].
- [cite_start]**Rule**: PROHIBITED inside process expressions (e.g., after `->`, `[]`, or `|||`).
- **Example**: 
    - [cite_start]`#define N 5;` 
    - [cite_start]`var board[N*N];` 
    - [cite_start]`D() = e2 -> p3 -> D();` (No semicolon after events) 

## 2. Array Initialization
- **Rule**: Use square brackets `[]` to list values.
- **Rule**: 2D arrays MUST be a single flat list. Nested lists `[[...]]` are NOT supported.
- **Example**: `var board[2][3] = [0,0,0,1,1,1];`

## 3. Enumerations
- **Rule**: Use curly brackets `{}` immediately after `enum`. [cite_start]Do not specify a name[cite: 5].
- [cite_start]**Example**: `enum {off, on};` [cite: 5]

## 4. Process Definitions & Guards
- **Rule**: Use square brackets `[]` for guard conditions.
- **Rule**: Every process MUST transition back to a process name to avoid deadlocks.
- **Example**: `owner_pos(i) = [owner[i] == far] towards.i{owner[i] = near;} -> owner_pos(i);`

## 5. Assertions & LTL
- **Rule**: Define state macros separately using `#define`.
- **Rule**: LTL operators (`[]`, `<>`, `|=`) must ONLY appear in `#assert` statements.
- **Example**: 
    - `#define goal1 (!on && dim == 50);`
    - `#assert System reaches goal1;`
    - `#assert System |= []<>light50;`

- **Rule**: STRICTLY FORBIDDEN to use ternary operators `? :` in state updates. Use `if (cond) { } else { }` instead.