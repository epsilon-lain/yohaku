"""Pure symbolic recognition/compilation of common-conjugation frames.

This module does not execute or verify a move and has no data-set access.
The caller must replay the expanded candidate with the official semantics.
"""

RULE_VERSION = "common-conjugation-pair-v1"


def reduce_word(word):
    out = []
    for letter in word:
        if out and out[-1] == -letter:
            out.pop()
        else:
            out.append(letter)
    return tuple(out)


def inverse(word):
    return tuple(-letter for letter in reversed(word))


def compile_frame(rank, word, move_table):
    """Return k*|word| official C ids realizing simultaneous C_word.

    Execution on each slot reads the conjugator word from right to left.
    All conversions are expanded and must be charged by the caller.
    """
    word = reduce_word(word)
    if any(abs(letter) > rank for letter in word):
        raise ValueError("frame word uses an out-of-rank generator")
    conjugations = {(row["relator"], row["conjugator"]): row["id"]
                    for row in move_table if row["category"] == "conjugation"}
    return tuple(conjugations[slot, letter]
                 for slot in range(rank) for letter in reversed(word))


def frame_intervals(moves, states, move_table):
    """Enumerate every nonempty, pure-C interval with a common nonempty net word.

    The interval may start/end inside a longer C run.  Every slot, including
    untouched slots, participates in the equality test.  Syntactic equality
    is equality of freely reduced conjugator words, not state isomorphism.
    """
    if len(states) != len(moves) + 1:
        raise ValueError("the caller must supply every original full state")
    frames = []
    for start in range(len(moves)):
        rank = len(states[start])
        nets = [()] * rank
        for cursor in range(start, len(moves)):
            row = move_table[moves[cursor]]
            if row["category"] != "conjugation":
                break
            if len(states[cursor]) != rank or len(states[cursor + 1]) != rank:
                raise ValueError("conjugation unexpectedly changed rank")
            slot, letter = row["relator"], row["conjugator"]
            if slot >= rank or abs(letter) > rank:
                raise ValueError("input route contains an inapplicable C move")
            nets[slot] = reduce_word((letter,) + nets[slot])
            if nets and nets[0] and all(word == nets[0] for word in nets):
                frames.append({"start": start, "end": cursor + 1,
                               "rank": rank, "word": nets[0]})
    return frames


def frame_candidates(moves, states, move_table):
    """Yield strict shortenings B_h ; P ; B_g -> P ; C_reduce(g h).

    P is nonempty and contains only inversion/multiplication; both frame
    words are nonempty.  No stabilization, destabilization, relabeling,
    single-slot commutation, or donor-relator macro is used.
    """
    frames = frame_intervals(moves, states, move_table)
    output = []
    seen = set()
    for left in frames:
        for right in frames:
            a, b = left["start"], left["end"]
            c, d = right["start"], right["end"]
            if b >= c or left["rank"] != right["rank"]:
                continue
            middle = tuple(moves[b:c])
            if any(move_table[move]["category"] not in
                   ("inversion", "multiplication") for move in middle):
                continue
            rank = left["rank"]
            if any(len(state) != rank for state in states[a:d + 1]):
                continue
            merged = reduce_word(right["word"] + left["word"])
            route = middle + compile_frame(rank, merged, move_table)
            if len(route) >= d - a:
                continue
            identity = (a, d, route)
            if identity in seen:
                continue
            seen.add(identity)
            output.append({"start": a, "end": d, "route": route,
                           "rank": rank, "left_word": left["word"],
                           "right_word": right["word"], "merged_word": merged,
                           "left_end": b, "right_start": c,
                           "primitive_saving": d - a - len(route),
                           "mechanism": RULE_VERSION})
    yield from sorted(output, key=lambda row: (row["start"], row["end"], row["route"]))
