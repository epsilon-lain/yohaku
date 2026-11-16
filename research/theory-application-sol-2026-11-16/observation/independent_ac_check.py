"""Independent official replay and complete bidirectional radius-six check.

Does not import application-team search/certificate code. Uses frozen official
primitive semantics and independently constructs unpruned state balls.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def complete_ball(source, radius, apply_move):
    seen = {source}
    frontier = {source}
    levels = [1]
    evaluations = 0
    for _ in range(radius):
        following = set()
        for state in frontier:
            for move in range(14):
                evaluations += 1
                next_state = apply_move(state, move)
                if next_state not in seen:
                    following.add(next_state)
        seen.update(following)
        frontier = following
        levels.append(len(frontier))
    return seen, {'radius': radius, 'frontier_sizes': levels,
                  'states': len(seen), 'primitive_evaluations': evaluations,
                  'pruning': False, 'equivalence_quotient': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--official-root', type=Path,
                        default=ROOT.parent / 'ac_official',
                        help='root of the pinned Andrews-Curtis reference repository')
    parser.add_argument('--check-inputs-only', action='store_true',
                        help='check input hashes and replay witness without rebuilding balls')
    args = parser.parse_args()
    official = args.official_root.resolve()
    sys.path.insert(0, str(official / 'competition/tools'))
    from verifier.core import apply_move, verify
    began = time.perf_counter()
    result_file = ROOT / 'application/refinement_results.json'
    published = json.loads(result_file.read_text())
    manifest_file = official / 'competition/tools/verifier/data/manifest.json'
    manifest = json.loads(manifest_file.read_text())
    challenge = next(c for c in manifest['challenges'] if c['challenge_id'] == 'ac-07445')
    source = tuple(map(tuple, challenge['initial_relators']))
    target = tuple(map(tuple, challenge['target_relators']))
    witness = published['runs'][0]['moves']
    replay = verify(challenge, witness, challenge['move_spec_version'], manifest['limits'])
    assert replay['ok'] and replay['length'] == 13
    if args.check_inputs_only:
        prior = json.loads((ROOT/'observation/independent_ac_result.json').read_text())
        assert hashlib.sha256(result_file.read_bytes()).hexdigest() == prior['application_refinement_results_sha256']
        assert hashlib.sha256(manifest_file.read_bytes()).hexdigest() == prior['manifest_sha256']
        assert hashlib.sha256((official/'competition/tools/verifier/core.py').read_bytes()).hexdigest() == prior['official_core_sha256']
        assert replay == prior['official_replay']
        print(json.dumps({'input_hashes_match_prior': True, 'official_replay': replay,
                          'ball_reproduction_repeated': False}))
        return
    start_ball, start_summary = complete_ball(source, 6, apply_move)
    target_ball, target_summary = complete_ball(target, 6, apply_move)
    intersection = start_ball & target_ball
    result = {
        'challenge': 'ac-07445',
        'application_refinement_results_sha256': hashlib.sha256(result_file.read_bytes()).hexdigest(),
        'manifest_sha256': hashlib.sha256(manifest_file.read_bytes()).hexdigest(),
        'official_core_sha256': hashlib.sha256((official/'competition/tools/verifier/core.py').read_bytes()).hexdigest(),
        'official_replay': replay, 'witness': witness,
        'start_ball': start_summary, 'target_ball': target_summary,
        'intersection_size': len(intersection),
        'conclusion': 'distance exactly 13 under ordinary rank-two AC primitive moves' if not intersection else '13-move upper bound only',
        'scope': 'No resource pruning or quotient. Complete B6/B6 disjointness excludes every path of at most 12 moves. Does not apply to Stable AC or other cases.',
        'wall_seconds': time.perf_counter() - began,
    }
    assert not intersection
    (ROOT/'observation/independent_ac_result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
