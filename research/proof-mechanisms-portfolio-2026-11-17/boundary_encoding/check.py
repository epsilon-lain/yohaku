#!/usr/bin/env python3
"""Deterministic finite check and complete data-arithmetic ledger; stdlib only.

Run from any directory: python /absolute/path/to/check.py
Only this directory's checks.json and SHA256SUMS are written.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from itertools import product
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
CASE_CAP = 200_000
FORMAT = "reversible-boundary-encoding-v1"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def signed_width(magnitude):
    """One sign bit plus the magnitude bits (zero therefore has width one)."""
    return 1 + magnitude.bit_length()


@dataclass
class Ledger:
    additions: int = 0
    subtractions: int = 0
    unary_negations: int = 0
    input_scalar_copies: int = 0
    output_scalar_copies: int = 0
    arithmetic_result_stores: int = 0
    maximum_absolute_integer: int = 0

    def observe(self, value):
        self.maximum_absolute_integer = max(self.maximum_absolute_integer, abs(value))

    def add(self, left, right):
        self.additions += 1
        self.arithmetic_result_stores += 1
        value = left + right
        self.observe(value)
        return value

    def sub(self, left, right):
        self.subtractions += 1
        self.arithmetic_result_stores += 1
        value = left - right
        self.observe(value)
        return value

    def as_dict(self):
        arithmetic = self.additions + self.subtractions + self.unary_negations
        copies = self.input_scalar_copies + self.output_scalar_copies
        return {
            "additions": self.additions,
            "subtractions": self.subtractions,
            "unary_negations": self.unary_negations,
            "data_arithmetic_total": arithmetic,
            "input_scalar_copies": self.input_scalar_copies,
            "output_scalar_copies": self.output_scalar_copies,
            "arithmetic_result_stores_already_included_in_arithmetic": self.arithmetic_result_stores,
            "arithmetic_plus_copies_total": arithmetic + copies,
            "maximum_absolute_integer": self.maximum_absolute_integer,
            "maximum_signed_width": signed_width(self.maximum_absolute_integer),
        }


def initialize(a, operations):
    assert len(a) >= 1
    n = len(a)
    for left, right, value in operations:
        assert 0 <= left <= right < n
        assert isinstance(value, int)
    ledger = Ledger(input_scalar_copies=n)
    for value in a:
        assert isinstance(value, int)
        ledger.observe(value)
    for _, _, value in operations:
        ledger.observe(value)
    return list(a), ledger


def finish(buffer, ledger):
    ledger.output_scalar_copies += len(buffer)
    return tuple(buffer), ledger.as_dict()


def elementwise(a, operations):
    buffer, ledger = initialize(a, operations)
    for left, right, value in operations:
        for index in range(left, right + 1):
            buffer[index] = ledger.add(buffer[index], value)
    return finish(buffer, ledger)


def boundary_encoded(a, operations):
    buffer, ledger = initialize(a, operations)
    n = len(buffer)
    # Descending order preserves the original left operand until it is used.
    for index in range(n - 1, 0, -1):
        buffer[index] = ledger.sub(buffer[index], buffer[index - 1])
    for left, right, value in operations:
        buffer[left] = ledger.add(buffer[left], value)
        if right + 1 < n:
            # A direct binary subtraction; no materialized -value is hidden.
            buffer[right + 1] = ledger.sub(buffer[right + 1], value)
    # Ascending order is the inverse, including the retained zeroth coordinate.
    for index in range(1, n):
        buffer[index] = ledger.add(buffer[index], buffer[index - 1])
    return finish(buffer, ledger)


def closed_form_oracle(a, operations):
    # Different formula from either in-place implementation. Its work belongs
    # to the test harness and is not charged to either compared algorithm.
    return tuple(
        value + sum(delta for left, right, delta in operations if left <= index <= right)
        for index, value in enumerate(a)
    )


def check_case(a, operations):
    a, operations = tuple(a), tuple(tuple(op) for op in operations)
    n, q = len(a), len(operations)
    length_sum = sum(right - left + 1 for left, right, _ in operations)
    inner_ends = sum(right < n - 1 for _, right, _ in operations)
    expected = closed_form_oracle(a, operations)
    old, old_ledger = elementwise(a, operations)
    new, new_ledger = boundary_encoded(a, operations)
    assert old == new == expected
    assert old_ledger["additions"] == length_sum
    assert old_ledger["subtractions"] == 0
    assert new_ledger["additions"] == q + n - 1
    assert new_ledger["subtractions"] == n - 1 + inner_ends
    assert new_ledger["data_arithmetic_total"] == 2 * (n - 1) + q + inner_ends
    for ledger in (old_ledger, new_ledger):
        assert ledger["unary_negations"] == 0
        assert ledger["input_scalar_copies"] == n
        assert ledger["output_scalar_copies"] == n
        assert ledger["arithmetic_result_stores_already_included_in_arithmetic"] == ledger["data_arithmetic_total"]
    initial_bound = max(map(abs, a))
    total_delta_bound = sum(abs(value) for _, _, value in operations)
    assert old_ledger["maximum_absolute_integer"] <= initial_bound + total_delta_bound
    assert new_ledger["maximum_absolute_integer"] <= 2 * initial_bound + total_delta_bound
    return {
        "n": n,
        "Q": q,
        "K": inner_ends,
        "S": length_sum,
        "output": list(expected),
        "elementwise": old_ledger,
        "boundary_encoded": new_ledger,
        "arithmetic_saving": length_sum - new_ledger["data_arithmetic_total"],
    }


def exhaustive_checks():
    digest = sha256()
    by_n = []
    total = 0
    outcomes = {"strict_saving": 0, "tie": 0, "strict_loss": 0}
    arithmetic_totals = {"elementwise": 0, "boundary_encoded": 0}
    max_width = {"elementwise": 0, "boundary_encoded": 0}
    for n in range(1, 5):
        alphabet = tuple((left, right, delta)
                         for left in range(n)
                         for right in range(left, n)
                         for delta in (-1, 1))
        count = 0
        for a in product((-1, 0, 1), repeat=n):
            for q in range(3):
                for operations in product(alphabet, repeat=q):
                    record = check_case(a, operations)
                    digest.update(canonical([a, operations, record]))
                    digest.update(b"\n")
                    count += 1
                    total += 1
                    assert total <= CASE_CAP
                    saving = record["arithmetic_saving"]
                    key = "strict_saving" if saving > 0 else "tie" if saving == 0 else "strict_loss"
                    outcomes[key] += 1
                    for method in arithmetic_totals:
                        ledger = record[method]
                        arithmetic_totals[method] += ledger["data_arithmetic_total"]
                        max_width[method] = max(max_width[method], ledger["maximum_signed_width"])
        expected_count = (3 ** n) * sum(len(alphabet) ** q for q in range(3))
        assert count == expected_count
        by_n.append({"n": n, "initial_arrays": 3 ** n,
                     "operation_alphabet_size": len(alphabet),
                     "operation_sequences_per_array": sum(len(alphabet) ** q for q in range(3)),
                     "cases": count})
    assert total == 38_748
    return {
        "scope": "all n=1..4, all a coordinates in {-1,0,1}, every ordered sequence of 0,1,2 inclusive-interval +/-1 updates",
        "by_n": by_n,
        "cases": total,
        "outcomes": outcomes,
        "aggregate_data_arithmetic": arithmetic_totals,
        "maximum_observed_signed_width": max_width,
        "ordered_inputs_outputs_and_ledgers_sha256": digest.hexdigest(),
    }


def named_checks():
    specs = [
        ("full_range_Q1_loss", tuple(range(-3, 3)), ((0, 5, 1),), "a_i=i-3; b_i=i-2"),
        ("full_range_Q2_tie", tuple(range(-3, 3)), ((0, 5, 1),) * 2, "a_i=i-3; b_i=i-1"),
        ("full_range_Q3_saving", tuple(range(-3, 3)), ((0, 5, 1),) * 3, "a_i=i-3; b_i=i"),
        ("suffix_family_n4_tie", tuple(range(-2, 2)), tuple((j, 3, 1) for j in range(4)), "a_i=i-2; b_i=2i-1"),
        ("suffix_family_n5_saving", tuple(range(-2, 3)), tuple((j, 4, 1) for j in range(5)), "a_i=i-2; b_i=2i-1"),
        ("large_full_range_saving", tuple(i - 500 for i in range(1000)), ((0, 999, 1),) * 200, "a_i=i-500; b_i=i-300"),
        ("large_point_updates_loss", tuple(i - 500 for i in range(1000)), ((500, 500, 1),) * 200, "a_i=i-500; b_500=200 and b_i=a_i otherwise"),
        ("distinct_suffix_saving", tuple(i - 50 for i in range(100)), tuple((j, 99, 1) for j in range(100)), "a_i=i-50; b_i=2i-49"),
        ("large_integer_signed_updates", (2 ** 100, -(2 ** 100), 2 ** 100 - 1), ((0, 1, 2 ** 120), (1, 2, -(2 ** 119))), "explicit input and operations recorded below"),
        ("empty_update_batch", (7, -5, 2), (), "b=a; conversion/recovery still charged"),
    ]
    results = []
    for name, a, operations, formula in specs:
        record = check_case(a, operations)
        record.update({"name": name, "input_formula": formula,
                       "input_sha256": sha256(canonical([a, operations])).hexdigest(),
                       "output_sha256": sha256(canonical(record["output"])).hexdigest()})
        # A deterministic formula plus hashes specifies large arrays completely;
        # retain the full short examples and all exact ledgers in the report.
        if len(a) <= 6:
            record["initial_array"] = list(a)
            record["operations"] = list(operations)
        else:
            record["operation_specification"] = (
                "200 repetitions of (0,999,+1)" if name == "large_full_range_saving" else
                "200 repetitions of (500,500,+1)" if name == "large_point_updates_loss" else
                "(j,99,+1) for j=0..99 in increasing order")
            record["output_first_5"] = record["output"][:5]
            record["output_last_5"] = record["output"][-5:]
            del record["output"]
        results.append(record)
    return results


def boundary_loss_checks():
    first, second = (0, 1, 0), (5, 6, 5)
    def interior(a):
        return tuple(a[i] - a[i - 1] for i in range(1, len(a)))
    assert interior(first) == interior(second) == (1, -1)
    assert first != second
    # The same legal nonempty update preserves the lost constant offset too.
    operations = ((1, 2, -1),)
    left = check_case(first, operations)
    right = check_case(second, operations)
    assert interior(left["output"]) == interior(right["output"])
    return {
        "initial_arrays": [list(first), list(second)],
        "equal_interior_differences": [1, -1],
        "no_update_outputs": [list(first), list(second)],
        "same_nonempty_operations": list(operations),
        "different_outputs_after_same_operations": [left["output"], right["output"]],
        "additional_full_algorithm_cases": 2,
    }


def main():
    exhaustive = exhaustive_checks()
    named = named_checks()
    loss = boundary_loss_checks()
    total = exhaustive["cases"] + len(named) + loss["additional_full_algorithm_cases"]
    assert total <= CASE_CAP
    results = {
        "format": FORMAT,
        "cost_model": {
            "unit_data_addition": 1,
            "unit_data_subtraction": 1,
            "unary_negation_as_0_minus_value": 1,
            "explicit_unary_negations_used": 0,
            "input_scalar_copies_each_algorithm": "n",
            "output_scalar_copies_each_algorithm": "n",
            "index_loop_control_validation_and_test_harness": "not data-arithmetic units; no CPU timing claim",
            "working_array_cells_each_algorithm": "n",
            "output_array_cells_each_algorithm": "n",
            "input_is_retained": True,
        },
        "formula": {"elementwise": "S", "boundary_encoded": "2(n-1)+Q+K",
                    "strict_saving_iff": "S>2(n-1)+Q+K",
                    "S": "sum of inclusive interval lengths", "K": "number of updates with right<n-1"},
        "exhaustive": exhaustive,
        "named_cases": named,
        "deleted_boundary_counterexample": loss,
        "resource_ledger": {"synthetic_case_cap": CASE_CAP, "full_algorithm_cases": total,
                            "official_AC_search_apply": 0, "official_AC_verification_apply": 0,
                            "official_action_lists_read": 0},
        "provenance": {"stdlib_only": True, "deterministic": True,
                       "scope": "finite self-check plus algebraic proof; not independent review or CPU benchmark"},
    }
    results["result_payload_sha256"] = sha256(canonical(results)).hexdigest()
    sources = {name: sha256((HERE / name).read_bytes()).hexdigest()
               for name in ("check.py", "README.md", "METHOD-LOG.md")}
    results["artifact_source_sha256"] = sources
    output = HERE / "checks.json"
    output.write_text(json.dumps(results, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    hashes = {**sources, "checks.json": sha256(output.read_bytes()).hexdigest()}
    (HERE / "SHA256SUMS").write_text("".join(f"{value}  {name}\n" for name, value in sorted(hashes.items())))
    print(json.dumps({"cases": total, "exhaustive_cases": exhaustive["cases"],
                      "outcomes": exhaustive["outcomes"], "source_sha256": sources["check.py"],
                      "checks_json_sha256": hashes["checks.json"],
                      "result_payload_sha256": results["result_payload_sha256"]},
                     ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
