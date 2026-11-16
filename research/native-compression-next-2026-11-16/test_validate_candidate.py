"""Offline tests only: pinned official replay, with explicitly marked fixtures.

The padded fixture below exercises the success branch of the validator. It is
deliberately artificial and is never evidence of a new competition improvement.
Run: python -m unittest discover -s native_compression_next -p 'test_validate_candidate.py' -v
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_candidate as v


ROOT = Path(__file__).resolve().parent.parent


def raw(value):
    return json.dumps(value, ensure_ascii=True).encode("ascii")


def locked_registry():
    return {
        "format": "yohaku-locked-baselines/1", "official_commit": v.PIN,
        "comparison_scope": "our_fixed_archived_paths_not_live_leaderboard",
        "baselines": {cid: {"moves": moves[:], "proved_minimum": v.PROVED_MINIMA.get(cid)}
                      for cid, moves in v.LOCKED_BASELINES.items()},
    }


class ExpansionTests(unittest.TestCase):
    def reject(self, tokens, macros, message=None):
        with self.assertRaises(v.ValidationError) as caught:
            v.expand_tokens(tokens, macros, 14)
        if message:
            self.assertIn(message, str(caught.exception))

    def test_nested_macro_preserves_literal_order(self):
        self.assertEqual(v.expand_tokens(["outer", 0], {"leaf": [7, 4], "outer": ["leaf", 12]}, 14),
                         [7, 4, 12, 0])

    def test_direct_and_indirect_cycles(self):
        self.reject(["a"], {"a": ["a"]}, "cyclic")
        self.reject(["a"], {"a": ["b"], "b": ["a"]}, "cyclic")

    def test_undefined_and_unused_invalid_definitions(self):
        self.reject(["missing"], {}, "undefined")
        self.reject([0], {"unused": ["missing"]}, "undefined")
        self.reject([0], {"unused": ["unused"]}, "cyclic")

    def test_bool_and_noninteger_move_rejected_everywhere(self):
        for token in (True, False, 1.0, None, {}, []):
            with self.subTest(token=token):
                self.reject([token], {})
                self.reject([0], {"unused": [token]})

    def test_move_id_range_is_spec_specific(self):
        self.reject([14], {}, "out of range")
        self.reject([-1], {}, "out of range")
        self.assertEqual(v.expand_tokens([256], {}, 257), [256])
        with self.assertRaises(v.ValidationError):
            v.expand_tokens([257], {}, 257)

    def test_no_conditional_or_implicit_action_format(self):
        self.reject([{"if": "equivalent", "then": 0}], {})
        self.reject([0], {"m": []}, "nonempty")
        self.reject([0], {"bad-name": [0]}, "name")

    def test_exact_official_length_boundary(self):
        self.assertEqual(len(v.expand_tokens([0] * 100000, {}, 14)), 100000)
        self.reject([0] * 100001, {})
        self.assertEqual(len(v.expand_tokens(["x"] * 1000, {"x": [0] * 100}, 14)), 100000)
        self.reject(["x"] * 1001, {"x": [0] * 100}, "boundary")

    def test_exponential_unused_definition_counted_before_expansion(self):
        macros = {"m0": [0]}
        for i in range(1, 25):
            macros["m" + str(i)] = ["m" + str(i - 1)] * 2
        self.reject([0], macros, "boundary")

    def test_maximum_depth_and_cached_deep_path(self):
        macros = {"m0": [0]}
        for i in range(1, 32):
            macros["m" + str(i)] = ["m" + str(i - 1)]
        self.assertEqual(v.expand_tokens(["m31"], macros, 14), [0])
        macros["m32"] = ["m31"]
        self.reject(["m32"], macros, "depth")

    def test_duplicate_json_keys_and_nonfinite_rejected(self):
        for text in (b'{"tokens":[],"tokens":[0]}', b'{"value": NaN}', b'{"value": Infinity}'):
            with self.assertRaises(v.ValidationError):
                v.parse_json(text)


class OfficialReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.official = v.Official(Path(os.environ.get("YOHAKU_OFFICIAL_CHECKOUT", str(ROOT / "ac_official"))))

    def evaluate(self, moves=None, *, tokens=None, macros=None, cid="ac-08491", registry=None, fixture=False):
        if tokens is None:
            tokens = list(v.LOCKED_BASELINES[cid] if moves is None else moves)
        candidate = {"challenge_id": cid, "tokens": tokens, "macros": {} if macros is None else macros}
        return v.validate(raw(candidate), raw(locked_registry() if registry is None else registry),
                          self.official, fixture)

    def test_all_four_fixed_paths_officially_replay(self):
        for cid, moves in v.LOCKED_BASELINES.items():
            with self.subTest(cid=cid):
                result = self.evaluate(cid=cid)
                self.assertEqual(result["status"], "no_strict_improvement")
                self.assertTrue(result["baseline_official_verdict"]["ok"])
                self.assertTrue(result["official_verdict"]["ok"])
                self.assertEqual(result["lengths"]["expanded_primitive_length"], len(moves))

    def test_whole_eight_step_path_in_one_macro_still_eight(self):
        moves = v.LOCKED_BASELINES["ac-08491"]
        result = self.evaluate(tokens=["whole"], macros={"whole": moves})
        self.assertEqual(result["lengths"], {"input_token_length": 1,
                                           "dictionary_token_length": 9,
                                           "expanded_primitive_length": 8})
        self.assertEqual(result["expanded_moves"], moves)
        self.assertEqual(result["status"], "no_strict_improvement")
        self.assertFalse(result["accepted_as_strict_improvement"])

    def test_work48_is_not_primitive_length_improvement(self):
        result = self.evaluate()
        self.assertEqual(result["official_verdict"]["work"], 48)
        self.assertEqual(result["official_verdict"]["length"], 8)
        self.assertEqual(result["status"], "no_strict_improvement")
        self.assertFalse(result["competition_record_claim"])

    def test_omitted_final_action_fails_official_target(self):
        result = self.evaluate(v.LOCKED_BASELINES["ac-08491"][:-1])
        self.assertEqual(result["status"], "official_replay_failed")
        self.assertFalse(result["official_verdict"]["ok"])
        self.assertEqual(result["official_verdict"]["code"], "E_NOT_TARGET")

    def test_order_and_stable_branch_preconditions_are_official(self):
        swapped = v.LOCKED_BASELINES["ac-08491"][:]
        swapped[0], swapped[1] = swapped[1], swapped[0]
        self.assertFalse(self.evaluate(swapped)["official_verdict"]["ok"])
        result = self.evaluate([16, 15], cid="sac-08491")
        self.assertEqual(result["official_verdict"]["code"], "E_MOVE_NOT_APPLICABLE")
        self.assertFalse(result["accepted_as_strict_improvement"])

    def test_baseline_cannot_be_silently_padded_or_replaced(self):
        registry = locked_registry()
        registry["baselines"]["ac-08491"]["moves"] += [0, 0]
        result = self.evaluate(registry=registry)
        self.assertEqual(result["status"], "rejected_input")
        self.assertIn("locked baseline", result["error"])
        registry = locked_registry()
        del registry["baselines"]["ac-08491"]
        self.assertEqual(self.evaluate(registry=registry)["status"], "rejected_input")

    def test_fixture_positive_branch_is_explicitly_not_a_record(self):
        registry = {"format": "yohaku-validator-fixture/1", "official_commit": v.PIN,
                    "fixture_only": True, "comparison_scope": "artificial_unit_test_not_competition",
                    "baselines": {"ac-08491": {"moves": v.LOCKED_BASELINES["ac-08491"] + [0, 0]}}}
        self.assertEqual(self.evaluate(registry=registry)["status"], "rejected_input")
        result = self.evaluate(registry=registry, fixture=True)
        self.assertEqual(result["status"], "verified_strict_improvement")
        self.assertTrue(result["fixture_only"])
        self.assertFalse(result["competition_record_claim"])
        self.assertFalse(result["fixed_archived_baseline_improvement"])
        self.assertEqual(result["baseline_official_verdict"]["length"], 10)
        self.assertEqual(result["official_verdict"]["length"], 8)

    def test_bad_fixture_baseline_must_itself_replay(self):
        registry = {"format": "yohaku-validator-fixture/1", "official_commit": v.PIN,
                    "fixture_only": True, "baselines": {"ac-08491": {"moves": [0]}}}
        result = self.evaluate(registry=registry, fixture=True)
        self.assertEqual(result["status"], "rejected_input")
        self.assertFalse(result["baseline_official_verdict"]["ok"])

    def test_proved_bound_contradiction_cannot_be_promoted(self):
        # Impossible official witnesses are not manufactured or searched for.
        # This directly exercises policy dispatch on a hypothetical positive verdict.
        for cid, minimum in v.PROVED_MINIMA.items():
            self.assertEqual(v.comparison_status(cid, {"ok": True}, minimum - 1, minimum),
                             "contradiction_requires_review")

    def test_hashes_and_external_preflight_identity(self):
        moves = v.LOCKED_BASELINES["ac-08491"]
        candidate = {"challenge_id": "ac-08491", "tokens": ["m"], "macros": {"m": moves}}
        registry = locked_registry()
        result = v.validate(raw(candidate), raw(registry), self.official)
        self.assertEqual(result["candidate_input_sha256"], v.digest(raw(candidate)))
        self.assertEqual(result["baseline_registry_sha256"], v.digest(raw(registry)))
        self.assertEqual(result["macro_dictionary_sha256"], v.digest(v.canonical_bytes(candidate["macros"])))
        self.assertEqual(result["official_commit"], v.PIN)
        self.assertEqual(len(result["official_source_fingerprints"]), 7)
        self.assertEqual(result["kind"], "external_preflight")
        self.assertFalse(result["native_receipt"])
        self.assertFalse(result["platform_upload"])

    def test_tampered_official_code_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / v.PREFIX
            path.mkdir(parents=True)
            (path / "canon.py").write_text("raise RuntimeError('must never execute')\n")
            with self.assertRaises(v.ValidationError) as caught:
                v.Official(folder)
            self.assertIn("fingerprint mismatch", str(caught.exception))

    def test_candidate_cannot_override_challenge_or_add_free_actions(self):
        for cid in ("ac08491", "missing", True):
            result = self.evaluate(cid=cid, tokens=[])
            self.assertEqual(result["status"], "rejected_input")
        candidate = {"challenge_id": "ac-08491", "tokens": [], "macros": {}, "free_swap": True}
        result = v.validate(raw(candidate), raw(locked_registry()), self.official)
        self.assertEqual(result["status"], "rejected_input")


if __name__ == "__main__":
    unittest.main()
