"""One preregistered finite experiment for M-91f60b428262ac67@1; no numeric pi."""
import hashlib
import json
from math import factorial
from pathlib import Path

CANDIDATE = "M-91f60b428262ac67@1"
BODY_SHA256 = "73f6a0dcbc40d36f9675b70f2b1f216c43d7fc758ce2948b45e6ee174fe7fb2a"
DOMAIN = tuple(range(2, 257)) + (355,)
CATEGORIES = (
    "B_zero",
    "B_nonzero_gap_nonpositive",
    "gap_positive_below_threshold",
    "pass",
)
DEGREE_LABELS = ("2n", "2n+1", "4n", "8n")
ARTIFACT = "pade_finite_01.json"


def candidates(n):
    y = 2 * n
    y2 = y * y
    degrees = (2 * n, 2 * n + 1, 4 * n, 8 * n)
    wanted = set(degrees)
    prev_a, prev_b = 1, 0
    a, b = 2, y
    for m in range(1, degrees[-1] + 1):
        if m in wanted:
            yield (m, a, b)
        coeff = 2 * (2 * m + 1)
        prev_a, a = a, coeff * a - y2 * prev_a
        prev_b, b = b, coeff * b - y2 * prev_b


def make_row(n, m, a, b):
    d = abs(a) + abs(b)
    if d == 0:
        raise ArithmeticError("Zero Padé value")
    u = pow(2 * n, 2 * m + 1) * factorial(m)
    v = factorial(2 * m + 1)
    gap = 2 * v * abs(b) - u
    h = 1000 * n * gap - 2 * v * d
    index = 0 if b == 0 else 1 if gap <= 0 else 2 if h < 0 else 3
    if (index == 3) != (h >= 0):
        raise ArithmeticError("Category threshold mismatch")
    line = (",".join((str(n), str(m), *(hex(x) for x in (a, b, u, v, h)))) + "\n").encode("ascii")
    return index, h, line, (a, b, u, v, h)


def witness(n, m, line, values):
    a, b, u, v, h = values
    record = {
        "n": n, "m": m, "row_sha256": hashlib.sha256(line).hexdigest(),
        "B_nonzero": b != 0, "gap_sign": (2 * v * abs(b) > u) - (2 * v * abs(b) < u),
        "H_sign": (h > 0) - (h < 0),
        "bit_lengths_abs_A_B_u_v_H": [abs(x).bit_length() for x in values],
    }
    if max(record["bit_lengths_abs_A_B_u_v_H"]) <= 128:
        record["exact_decimal_strings"] = dict(zip(("A", "B", "u", "v", "H"), map(str, values)))
    return record


def main():
    transcript = hashlib.sha256()
    counts = dict.fromkeys(CATEGORIES, 0)
    accepted_by_degree = dict.fromkeys(DEGREE_LABELS, 0)
    first_by_category = {}
    n_records = []
    all_failed = []
    first_failure_four = None
    equality_count = 0
    pair_count = 0
    for n in DOMAIN:
        pairs = list(candidates(n))
        if tuple(m for m, _, _ in pairs) != (2 * n, 2 * n + 1, 4 * n, 8 * n):
            raise ArithmeticError("Degree coverage mismatch")
        m0, a0, b0 = pairs[0]
        _, a1, b1 = pairs[1]
        if a0 * b1 - b0 * a1 != pow(2 * n, 2 * m0 + 1) or not (b0 or b1):
            raise ArithmeticError("Adjacent determinant/nonzero mismatch")
        outcomes = []
        for label, (m, a, b) in zip(DEGREE_LABELS, pairs):
            index, h, line, values = make_row(n, m, a, b)
            category = CATEGORIES[index]
            counts[category] += 1
            pair_count += 1
            equality_count += (h == 0)
            if index == 3:
                accepted_by_degree[label] += 1
            outcomes.append(index)
            transcript.update(line)
            if category not in first_by_category:
                first_by_category[category] = witness(n, m, line, values)
        n_records.append([n, outcomes])
        if 3 not in outcomes:
            all_failed.append(n)
            if first_failure_four is None:
                first_failure_four = []
                for m, a, b in pairs:
                    index, _, line, values = make_row(n, m, a, b)
                    first_failure_four.append({"category": CATEGORIES[index], **witness(n, m, line, values)})
    if len(n_records) != 256 or pair_count != 1024 or sum(counts.values()) != pair_count:
        raise ArithmeticError("Scope/count mismatch")
    summary = {
        "format": "pi-pade-preregistered-finite/1",
        "candidate": CANDIDATE,
        "candidate_body_sha256": BODY_SHA256,
        "accept_event": 786,
        "domain": "integers 2..256 inclusive, followed by 355",
        "degrees_by_n": list(DEGREE_LABELS),
        "threshold": "1/1000",
        "domain_size": len(n_records),
        "pair_count": pair_count,
        "n_pass_count": len(n_records) - len(all_failed),
        "n_fail_count": len(all_failed),
        "min_failed_n": all_failed[0] if all_failed else None,
        "pair_category_counts": counts,
        "pass_pairs_by_degree": accepted_by_degree,
        "H_equality_count": equality_count,
        "transcript_rows_sha256": transcript.hexdigest(),
        "transcript_encoding": "ASCII; one row n,m,A,B,u,v,H comma-separated + LF; n,m decimal, other fields Python hex() signed lowercase; n ascend then degree order above",
    }
    artifact = {
        "summary": summary,
        "categories_by_code": list(CATEGORIES),
        "rows_by_n": n_records,
        "first_row_by_nonempty_category": first_by_category,
        "minimum_failure_all_four": first_failure_four,
    }
    payload = (json.dumps(artifact, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    Path("/output", ARTIFACT).write_bytes(payload)
    print(json.dumps({
        "summary": summary,
        "artifact": ARTIFACT,
        "artifact_sha256": hashlib.sha256(payload).hexdigest(),
        "artifact_bytes": len(payload),
        "representatives": first_by_category,
    }, ensure_ascii=True, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
