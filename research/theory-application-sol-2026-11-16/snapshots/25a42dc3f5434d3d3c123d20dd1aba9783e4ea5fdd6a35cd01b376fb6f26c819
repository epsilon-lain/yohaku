# application-distance-v1

For the fixed ordinary AC challenge `ac-07445`, with instance hash `sha256:25d9dc7570c0403aca323a3e7d53706c025dde87acb4deab63cac3e6176404d6`, the exact distance to the ordered target `((1,), (2,))` under the frozen 14-move `ac-r2-v1` table is **13**.

Upper witness: `[6,4,12,1,3,6,12,2,5,6,4,2,4]`, accepted by the pinned official verifier, peak total relator length 13, cumulative work 127. This improves the previously retained legal 17-move witness (peak12, work157).

Lower bound: complete, unpruned radius-six balls have 1200765 initial-side states and 336477 target-side states, with empty intersection. All 14 moves have their listed inverses. Any path of length at most12 has a vertex at distance at most6 from both endpoints. The empty intersection therefore excludes all lengths0–12; the upper witness attains13. Every generated edge in this certificate was crosschecked by an independent tuple-word implementation against official `core.apply_move`.

Ball layers from the initial state: [1, 14, 145, 1388, 12895, 117898, 1068424]. Ball layers from the target: [1, 10, 77, 574, 4453, 35664, 295698]. Hashes and exact reproduction code are retained in `distance_certificate.json` and `certify.py`. Enumeration costs are separate from search costs.

Scope: finite metric certification for one already-seen instance and the exact ordered AC target. It does not certify a Stable AC distance, a leaderboard record, novelty in the literature, or the Andrews–Curtis conjecture. No platform submission was made.
