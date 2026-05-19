"""
MISRA C:2012 Training Dataset Builder
Generates instruction-following pairs for fine-tuning Llama on MISRA code review.
Each sample: { "instruction": ..., "input": <C code>, "output": <MISRA analysis> }
"""

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Raw MISRA training samples  (instruction + C code + expected analysis)
# ---------------------------------------------------------------------------

SAMPLES = [
    # ── Rule 1.1 ─ Language standard compliance ──────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
// MISRA example: non-standard extension
int x = 0;
void foo() {
    __asm__("nop");   // GCC inline assembly - non-standard
}
""",
        "output": """\
MISRA C:2012 Violation Found:
Rule 1.1 [Required] — The program shall contain no violations of the standard C syntax and constraints, and shall not exceed the implementation's translation limits.
  Line 4: `__asm__` is a compiler extension not part of ISO C99/C11. Using non-standard extensions reduces portability.
  Recommendation: Wrap in a compiler-specific abstraction macro or replace with portable equivalent.
Severity: Required
""",
    },
    # ── Rule 2.1 ─ Unreachable code ──────────────────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
#include <stdint.h>
uint8_t get_status(void) {
    return 0U;
    uint8_t status = 1U;   /* unreachable */
    return status;
}
""",
        "output": """\
MISRA C:2012 Violation Found:
Rule 2.1 [Required] — A project shall not contain unreachable code.
  Line 4-5: The statements `uint8_t status = 1U;` and `return status;` are unreachable because an unconditional `return 0U;` precedes them.
  Recommendation: Remove the dead code or restructure the function logic.
Severity: Required
""",
    },
    # ── Rule 2.2 ─ Dead code ─────────────────────────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
#include <stdint.h>
void process(uint8_t val) {
    uint8_t temp = val;
    temp = 5U;          /* previous assignment to temp is dead */
    (void)temp;
}
""",
        "output": """\
MISRA C:2012 Violation Found:
Rule 2.2 [Required] — There shall be no dead code.
  Line 3: The assignment `temp = val;` is dead because `temp` is immediately overwritten on line 4 before any use.
  Recommendation: Remove the dead assignment `temp = val;` or ensure `val` is actually used.
Severity: Required
""",
    },
    # ── Rule 5.1 ─ Identifier length ─────────────────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
#include <stdint.h>
uint32_t very_long_variable_name_that_exceeds_31_characters = 0U;
uint32_t very_long_variable_name_that_exceeds_32_characters = 1U;
""",
        "output": """\
MISRA C:2012 Violation Found:
Rule 5.1 [Required] — External identifiers shall be distinct in the first 31 characters.
  Lines 2-3: Both identifiers share the same first 31 characters (`very_long_variable_name_that_ex`), making them indistinct when compiled for environments with 31-character significant identifier length.
  Recommendation: Shorten or rename identifiers so they differ within the first 31 characters.
Severity: Required
""",
    },
    # ── Rule 8.4 ─ Compatible declaration ────────────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
/* header.h */
extern int compute(int a, int b);

/* source.c */
int compute(int a, int b, int c) {   /* mismatched signature */
    return a + b + c;
}
""",
        "output": """\
MISRA C:2012 Violation Found:
Rule 8.4 [Required] — A compatible declaration shall be visible when an object or function with external linkage is defined.
  The definition of `compute` has three parameters while its declaration in `header.h` specifies two. This is a signature mismatch and constitutes undefined behaviour.
  Recommendation: Ensure the declaration and definition have identical parameter lists.
Severity: Required
""",
    },
    # ── Rule 9.1 ─ Uninitialised variables ───────────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
#include <stdint.h>
uint8_t compute_sum(uint8_t n) {
    uint8_t sum;          /* not initialised */
    uint8_t i;
    for (i = 0U; i < n; i++) {
        sum += i;         /* reads uninitialised sum on first iteration */
    }
    return sum;
}
""",
        "output": """\
MISRA C:2012 Violation Found:
Rule 9.1 [Mandatory] — The value of an object with automatic storage duration shall not be read before it has been set.
  Line 3: `sum` is declared without initialisation. Line 6: `sum += i;` reads `sum` before it has been assigned a value on the first iteration, resulting in undefined behaviour.
  Recommendation: Initialise `sum` at declaration: `uint8_t sum = 0U;`.
Severity: Mandatory
""",
    },
    # ── Rule 10.1 ─ Inappropriate operand types ──────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
#include <stdbool.h>
#include <stdint.h>
bool flag = true;
uint8_t result = flag + 1U;   /* bool used in arithmetic */
""",
        "output": """\
MISRA C:2012 Violation Found:
Rule 10.1 [Required] — Operands shall not be of an inappropriate essential type.
  Line 4: `flag` is of essentially Boolean type. Using a Boolean operand in an arithmetic expression (`flag + 1U`) is inappropriate.
  Recommendation: Convert the Boolean value explicitly or restructure logic to avoid mixing Boolean and integer arithmetic.
Severity: Required
""",
    },
    # ── Rule 10.4 ─ Mixed arithmetic ─────────────────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
#include <stdint.h>
int16_t  a = 100;
uint16_t b = 200U;
int32_t  result = a + b;   /* signed + unsigned */
""",
        "output": """\
MISRA C:2012 Violation Found:
Rule 10.4 [Required] — Both operands of an operator in which the usual arithmetic conversions are performed shall have the same essential type category.
  Line 4: `a` is essentially signed and `b` is essentially unsigned. Mixing signed and unsigned operands in arithmetic can produce unexpected results due to implicit conversion rules.
  Recommendation: Cast both operands to the same type before addition, e.g., `(int32_t)a + (int32_t)b`.
Severity: Required
""",
    },
    # ── Rule 11.3 ─ Pointer cast ─────────────────────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
#include <stdint.h>
void process(void *ptr) {
    uint32_t *p = (uint32_t *)ptr;  /* cast from void* to object pointer */
    *p = 0xDEADBEEFU;
}
""",
        "output": """\
MISRA C:2012 Violation Found:
Rule 11.3 [Required] — A cast shall not be performed between a pointer to object type and a pointer to a different object type.
  Line 3: Casting `void *` directly to `uint32_t *` bypasses type safety. If `ptr` does not point to a properly aligned `uint32_t` object, this causes undefined behaviour.
  Recommendation: Use a typed parameter instead of `void *`, or ensure alignment is guaranteed and document the assumption.
Severity: Required
""",
    },
    # ── Rule 12.1 ─ Precedence ───────────────────────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
#include <stdint.h>
uint8_t a = 2U, b = 3U, c = 1U;
uint8_t result = a + b * c - 1U;   /* precedence not explicit */
""",
        "output": """\
MISRA C:2012 Violation Found:
Rule 12.1 [Advisory] — The precedence of operators within expressions should be made explicit.
  Line 3: The expression `a + b * c - 1U` relies on implicit operator precedence. While C defines `*` before `+`, the intent is not clear to a reader.
  Recommendation: Add parentheses to make precedence explicit: `a + (b * c) - 1U`.
Severity: Advisory
""",
    },
    # ── Rule 13.2 ─ Side effects in expressions ──────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
#include <stdint.h>
uint8_t i = 0U;
uint8_t arr[5] = {0};
arr[i] = i++;    /* side effect: i modified and read in same expression */
""",
        "output": """\
MISRA C:2012 Violation Found:
Rule 13.2 [Required] — The value of an expression and its persistent side effects shall be the same under all permitted evaluation orders.
  Line 4: Both `arr[i]` and `i++` reference `i`. The order of evaluation of the index and the post-increment is unspecified, causing undefined behaviour.
  Recommendation: Split into two statements: `arr[i] = i; i++;`.
Severity: Required
""",
    },
    # ── Rule 14.4 ─ Controlling expression ──────────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
#include <stdint.h>
uint8_t get_value(void);
void check(void) {
    uint8_t val = get_value();
    if (val) {         /* non-boolean controlling expression */
        /* do something */
    }
}
""",
        "output": """\
MISRA C:2012 Violation Found:
Rule 14.4 [Required] — The controlling expression of an if statement and iteration-statement shall be essentially Boolean.
  Line 5: `val` is of essentially unsigned type, not Boolean. Using it directly as an `if` condition is not essentially Boolean.
  Recommendation: Use an explicit comparison: `if (val != 0U)`.
Severity: Required
""",
    },
    # ── Rule 15.4 ─ Single break per loop ────────────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
#include <stdint.h>
void search(const uint8_t *arr, uint8_t n) {
    uint8_t i;
    for (i = 0U; i < n; i++) {
        if (arr[i] == 0U) { break; }
        if (arr[i] > 10U) { break; }   /* second break */
    }
}
""",
        "output": """\
MISRA C:2012 Violation Found:
Rule 15.4 [Advisory] — There should be no more than one break or goto statement used to terminate any iteration statement.
  Lines 5-6: The for-loop contains two `break` statements. Multiple break points make control flow harder to follow.
  Recommendation: Combine the conditions into a single break: `if ((arr[i] == 0U) || (arr[i] > 10U)) { break; }`.
Severity: Advisory
""",
    },
    # ── Rule 15.5 ─ Single return point ─────────────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
#include <stdint.h>
int8_t find(const uint8_t *arr, uint8_t n, uint8_t target) {
    uint8_t i;
    for (i = 0U; i < n; i++) {
        if (arr[i] == target) {
            return (int8_t)i;    /* early return */
        }
    }
    return -1;
}
""",
        "output": """\
MISRA C:2012 Violation Found:
Rule 15.5 [Advisory] — A function should have a single point of exit at the end.
  Line 6: There is an early `return` inside the loop. The function has two exit points.
  Recommendation: Use a result variable and a single `return` at the end:
    int8_t result = -1;
    for (i = 0U; i < n; i++) { if (arr[i] == target) { result = (int8_t)i; break; } }
    return result;
Severity: Advisory
""",
    },
    # ── Rule 16.4 ─ Switch default clause ───────────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
#include <stdint.h>
void handle(uint8_t cmd) {
    switch (cmd) {
        case 1U: break;
        case 2U: break;
        /* no default */
    }
}
""",
        "output": """\
MISRA C:2012 Violation Found:
Rule 16.4 [Required] — Every switch statement shall have a default clause.
  Lines 3-7: The switch statement is missing a `default` clause. Without it, unhandled values of `cmd` cause silent no-ops.
  Recommendation: Add a `default:` clause, even if empty with a comment: `default: /* unreachable */ break;`.
Severity: Required
""",
    },
    # ── Rule 17.3 ─ Implicit function declaration ────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
#include <stdint.h>
void foo(void) {
    uint8_t x = bar();   /* bar() not declared before use */
}
uint8_t bar(void) { return 1U; }
""",
        "output": """\
MISRA C:2012 Violation Found:
Rule 17.3 [Mandatory] — A function shall not be declared implicitly.
  Line 3: `bar()` is called before its declaration. In C99/C11 this is a constraint violation; implicit int declarations are no longer allowed.
  Recommendation: Declare or define `bar` before `foo`, or add a forward declaration: `uint8_t bar(void);`.
Severity: Mandatory
""",
    },
    # ── Rule 17.7 ─ Return value ignored ────────────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
#include <string.h>
void copy_data(char *dst, const char *src) {
    memcpy(dst, src, 10);   /* return value of memcpy discarded */
}
""",
        "output": """\
MISRA C:2012 Violation Found:
Rule 17.7 [Required] — The value returned by a function having non-void return type shall be used.
  Line 3: The return value of `memcpy` (which returns `dst`) is discarded without acknowledgement.
  Recommendation: Either use the return value or explicitly cast to void to show intent: `(void)memcpy(dst, src, 10);`.
Severity: Required
""",
    },
    # ── Rule 18.1 ─ Pointer arithmetic ──────────────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
#include <stdint.h>
void process(uint8_t *buf, uint8_t len) {
    uint8_t *end = buf + 20U;   /* 20 may exceed len */
    while (buf < end) {
        *buf++ = 0U;
    }
}
""",
        "output": """\
MISRA C:2012 Violation Found:
Rule 18.1 [Required] — A pointer resulting from arithmetic on a pointer operand shall address an element of the same array as that pointer operand.
  Line 3: Adding `20U` to `buf` may produce a pointer past the end of the array if `len < 20`. This is undefined behaviour.
  Recommendation: Use `buf + len` so the upper bound is always within the allocated array: `uint8_t *end = buf + len;`.
Severity: Required
""",
    },
    # ── Rule 20.9 ─ Undefined macros ────────────────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
#if FEATURE_ENABLED == 1
    #define BUFFER_SIZE 256U
#else
    #define BUFFER_SIZE 64U
#endif
""",
        "output": """\
MISRA C:2012 Violation Found:
Rule 20.9 [Required] — All identifiers used in the controlling expression of #if or #elif preprocessing directives shall be #defined before evaluation.
  Line 1: `FEATURE_ENABLED` is used in a preprocessor `#if` expression. If it is not `#define`d, the preprocessor treats it as `0`, which silently selects the `#else` branch rather than raising an error.
  Recommendation: Define `FEATURE_ENABLED` explicitly (e.g., in a configuration header) before this file is included.
Severity: Required
""",
    },
    # ── Rule 21.3 ─ Dynamic memory allocation ───────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
#include <stdlib.h>
#include <stdint.h>
uint8_t *create_buffer(uint32_t size) {
    uint8_t *buf = (uint8_t *)malloc(size);
    return buf;
}
""",
        "output": """\
MISRA C:2012 Violation Found:
Rule 21.3 [Required] — The memory allocation and deallocation functions of <stdlib.h> shall not be used.
  Line 4: `malloc` from `<stdlib.h>` is used. Dynamic memory allocation is prohibited in MISRA C:2012 because heap fragmentation and allocation failures are difficult to manage safely in embedded/safety-critical contexts.
  Recommendation: Use statically allocated buffers or a dedicated memory pool instead of `malloc`/`free`.
Severity: Required
""",
    },
    # ── Clean code (no violation) ────────────────────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
#include <stdint.h>
static uint8_t calculate_checksum(const uint8_t *data, uint16_t length) {
    uint8_t  checksum = 0U;
    uint16_t i;
    for (i = 0U; i < length; i++) {
        checksum ^= data[i];
    }
    return checksum;
}
""",
        "output": """\
No MISRA C:2012 violations detected.
Code review summary:
  - Variables are initialised before use (Rule 9.1 satisfied).
  - Loop variable `i` type `uint16_t` matches the range of `length` (Rule 10.4 satisfied).
  - Single return point (Rule 15.5 satisfied).
  - No dynamic memory allocation (Rule 21.3 satisfied).
  - No implicit function declarations (Rule 17.3 satisfied).
  - All expressions have unambiguous types and operands.
The code appears compliant with MISRA C:2012 for the rules checked.
""",
    },
    # ── Multiple violations in one file ──────────────────────────────────
    {
        "instruction": "Review the following C code for MISRA C:2012 violations.",
        "input": """\
#include <stdint.h>
#include <stdlib.h>
int process_data(int *arr, int n) {
    int sum;                    /* uninitialised */
    int *extra = malloc(n);    /* dynamic allocation */
    int i;
    for (i = 0; i < n; i++) {
        if (n) {                /* non-boolean controlling expression */
            sum += arr[i];
        }
    }
    return sum;
}
""",
        "output": """\
MISRA C:2012 Violations Found (multiple):

1. Rule 9.1 [Mandatory] — Uninitialised variable.
   Line 4: `sum` is read on line 9 (`sum += arr[i]`) before being assigned. Initialise to `0`.

2. Rule 21.3 [Required] — Dynamic memory allocation.
   Line 5: `malloc` from `<stdlib.h>` must not be used. Replace with a static buffer.

3. Rule 14.4 [Required] — Non-Boolean controlling expression.
   Line 8: `n` is of essentially signed type; use an explicit comparison: `if (n > 0)`.

4. Rule 10.1 [Required] — Inappropriate essential type (advisory note).
   Array index `i` and length `n` use plain `int` rather than `uint*_t`; prefer unsigned types for counts and indices.

Recommendation: Initialise all local variables, remove dynamic allocation, use explicit Boolean expressions in conditions, and prefer fixed-width unsigned types for indices.
""",
    },
]


def build_dataset(output_path: str = "misra_train.json") -> None:
    """Write training samples to a JSON-lines file."""
    out = Path(output_path)
    records = []
    for s in SAMPLES:
        # Build the full text in Alpaca instruction-following format
        text = (
            f"### Instruction:\n{s['instruction']}\n\n"
            f"### Input:\n{s['input']}\n\n"
            f"### Response:\n{s['output']}"
        )
        records.append({"text": text, **s})

    with out.open("w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"[dataset] Wrote {len(records)} samples → {out.resolve()}")


if __name__ == "__main__":
    build_dataset()
