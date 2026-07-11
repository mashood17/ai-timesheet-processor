"""
Independent statistical validation of extracted day-values, applied AFTER
extraction and completely independent of any model-reported confidence.

WHY THIS EXISTS: manual verification against a real source document found
that a vision model can silently produce a smooth, plausible-looking but
WRONG pattern (discarding a genuine outlier value) while still reporting
high self-confidence. Since the model's own confidence score cannot be
trusted to catch its own smoothing behavior, this module re-examines the
raw extracted values with pure statistics — no reliance on the model at
all — and forces mandatory human review whenever a suspicious pattern is
detected, REGARDLESS of what confidence the model reported.

All thresholds here are generic pattern-detection heuristics (run length,
change-point count, cross-row similarity) — not tied to any specific
document, employee, or value. They apply identically to any timesheet.
"""
from app.models.process_models import EmployeeProcessResult

# A run of this many or more CONSECUTIVE identical values is flagged —
# real handwritten entries almost always have some natural variation
# (weekends, leave days, minor differences) over this many consecutive days.
MIN_SUSPICIOUS_RUN_LENGTH = 7

# If the total number of value-CHANGES across an employee's entire month is
# at or below this count, the row is suspiciously smooth (a real month
# almost always includes several weekend/leave transitions).
MAX_SUSPICIOUS_CHANGE_POINTS = 2

# If two different employees share an identical subsequence of at least
# this many consecutive days, both rows are flagged — real handwriting
# from different people essentially never produces byte-identical runs
# this long by chance.
MIN_CROSS_EMPLOYEE_DUPLICATE_LENGTH = 10


def flag_suspicious_patterns(results: list[EmployeeProcessResult]) -> list[str]:
    """
    Mutates `needs_review` on day cells in place wherever a suspicious
    statistical pattern is found, regardless of the model's own reported
    confidence. Returns a list of human-readable warning strings
    describing what was flagged and why, for surfacing to the user.
    """
    warnings: list[str] = []

    # Build a lookup for cross-employee comparison up front.
    employee_sequences: list[tuple[EmployeeProcessResult, list[str]]] = []
    for employee in results:
        if not employee.matched or not employee.day_cells:
            continue
        ordered_cells = sorted(employee.day_cells, key=lambda c: c.iso_date)
        values = [c.value for c in ordered_cells]
        employee_sequences.append((employee, values))

    for employee, values in employee_sequences:
        ordered_cells = sorted(employee.day_cells, key=lambda c: c.iso_date)

        # --- Check 1: long runs of identical consecutive values ---
        run_start = 0
        for i in range(1, len(values) + 1):
            if i == len(values) or values[i] != values[run_start]:
                run_length = i - run_start
                if run_length >= MIN_SUSPICIOUS_RUN_LENGTH:
                    for j in range(run_start, i):
                        ordered_cells[j].needs_review = True
                    warnings.append(
                        f"{employee.employee_name or employee.iqama_or_passport}: "
                        f"{run_length} consecutive days all read as '{values[run_start]}' "
                        f"({ordered_cells[run_start].iso_date} to {ordered_cells[i-1].iso_date}) "
                        "— unusually long for handwritten data; flagged for manual verification."
                    )
                run_start = i

        # --- Check 2: suspiciously few value changes across the whole month ---
        change_points = sum(1 for i in range(1, len(values)) if values[i] != values[i - 1])
        if len(values) >= 14 and change_points <= MAX_SUSPICIOUS_CHANGE_POINTS:
            for cell in ordered_cells:
                cell.needs_review = True
            warnings.append(
                f"{employee.employee_name or employee.iqama_or_passport}: "
                f"only {change_points} value change(s) across {len(values)} days — "
                "suspiciously smooth for real handwritten entries (most timesheets "
                "have several weekend/leave transitions); entire row flagged for review."
            )

    # --- Check 3: identical long subsequences across DIFFERENT employees ---
    for i in range(len(employee_sequences)):
        for j in range(i + 1, len(employee_sequences)):
            emp_a, values_a = employee_sequences[i]
            emp_b, values_b = employee_sequences[j]
            shared_run = _longest_common_run(values_a, values_b)
            if shared_run >= MIN_CROSS_EMPLOYEE_DUPLICATE_LENGTH:
                for cell in sorted(emp_a.day_cells, key=lambda c: c.iso_date):
                    cell.needs_review = True
                for cell in sorted(emp_b.day_cells, key=lambda c: c.iso_date):
                    cell.needs_review = True
                warnings.append(
                    f"{emp_a.employee_name or emp_a.iqama_or_passport} and "
                    f"{emp_b.employee_name or emp_b.iqama_or_passport} share an identical "
                    f"{shared_run}-day sequence of values — real handwriting from different "
                    "people essentially never matches this closely by chance; both rows "
                    "flagged for manual verification."
                )

    return warnings


def _longest_common_run(a: list[str], b: list[str]) -> int:
    """Longest run of positions where a[i] == b[i] (aligned by day index, not
    a general subsequence match — we specifically care about identical
    same-day values, which is what indicates copy/hallucination)."""
    best = 0
    current = 0
    for i in range(min(len(a), len(b))):
        if a[i] == b[i]:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best