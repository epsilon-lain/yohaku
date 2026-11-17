"""Version 2: transport pending slot frames through compatible I/M moves.

Pure symbolic generation only.  Official execution/endpoint/resource checks
remain the caller's responsibility.  The v1 module is retained unchanged.
"""
from frame_rules import RULE_VERSION as V1_RULE_VERSION, reduce_word

RULE_VERSION = "pending-compatible-conjugation-frames-v2"


def pending_frame_candidates(moves, states, move_table):
    """Normalize intervals using U_i = h_i T_i h_i^-1.

    C_i,a updates h_i <- reduce(a h_i); I_i is emitted immediately;
    R_ij^s is emitted only if the two reduced pending words are equal.
    Finally all residual slot frames are expanded in official C primitives.
    At least one multiplication must actually carry a nonempty shared frame.
    This rejects trivial C/I-only cleanup and requires strict shortening.
    """
    if len(states) != len(moves) + 1:
        raise ValueError("all full original states are required")
    conjugations = {(row["relator"], row["conjugator"]): row["id"]
                    for row in move_table if row["category"] == "conjugation"}
    output = []
    seen = set()
    for start in range(len(moves)):
        rank = len(states[start])
        pending = [()] * rank
        emitted = []
        carried = []
        for cursor in range(start, len(moves)):
            row = move_table[moves[cursor]]
            category = row["category"]
            if category not in ("conjugation", "inversion", "multiplication"):
                break
            if len(states[cursor]) != rank or len(states[cursor + 1]) != rank:
                break
            slot = row["relator"]
            if slot >= rank:
                raise ValueError("inapplicable original relator index")
            if category == "conjugation":
                letter = row["conjugator"]
                if abs(letter) > rank:
                    raise ValueError("inapplicable original conjugator")
                pending[slot] = reduce_word((letter,) + pending[slot])
            elif category == "inversion":
                emitted.append(moves[cursor])
            else:
                donor = row["other"]
                if donor >= rank:
                    raise ValueError("inapplicable original donor index")
                if pending[slot] != pending[donor]:
                    break
                if pending[slot]:
                    carried.append({"index": cursor, "target": slot, "donor": donor,
                                    "shared_word": pending[slot]})
                emitted.append(moves[cursor])
            if not carried:
                continue
            residual = tuple(conjugations[slot, letter]
                             for slot, word in enumerate(pending)
                             for letter in reversed(word))
            route = tuple(emitted) + residual
            end = cursor + 1
            if len(route) >= end - start:
                continue
            identity = (start, end, route)
            if identity in seen:
                continue
            seen.add(identity)
            output.append({"start": start, "end": end, "route": route,
                           "rank": rank, "residual_frame_words": tuple(pending),
                           "emitted_im_moves": tuple(emitted),
                           "carried_multiplications": tuple(carried),
                           "primitive_saving": end - start - len(route),
                           "mechanism": RULE_VERSION,
                           "parent_rule": V1_RULE_VERSION})
    yield from sorted(output, key=lambda row: (row["start"], row["end"], row["route"]))
