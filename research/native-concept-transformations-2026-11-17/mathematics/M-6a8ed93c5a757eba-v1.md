{
  "format": "round3-app-bridge03-field-reading/1",
  "task_id": "project-task-f3037adff007a0a53e60c6491983d93d",
  "request_id": "root-app-r3-07445-frozen-delayed-bridge03-v1",
  "source_set": "2c3db8649a4359d58446f4e834afc34afabccdd7e2a38da3055a831ddae64d95",
  "reader": "ai-node-0299a356d74db83b9ab4ebc7",
  "execution_by": "ai-node-60ce43c0fdb954913d5cf32f",
  "method_and_code_author": "ai-node-0299a356d74db83b9ab4ebc7",
  "new_computation_in_this_reading": false,
  "independent_search_reproduction": false,
  "result_field_projection": {
    "format": "round3-target-information-results/1",
    "status": "completed_bounded_search",
    "protocol": {
      "format": "round3-target-information-search/1",
      "stage": "native-concept-transformations-sol-20261117-01",
      "user_event": 968,
      "autonomous_method": "sac07445 no-stabilization target reduction + abelianization lower-bound beam + exact reverse word dictionary",
      "target": [
        [
          2
        ],
        [
          1
        ]
      ],
      "ordinary_prefix_limit": 12,
      "stable_suffix": [
        15,
        15
      ],
      "old_stable_length": 15,
      "reverse_word": {
        "radius": 5,
        "max_states": 60000
      },
      "abelianization": {
        "radius": 8,
        "max_states": 100000
      },
      "beam": {
        "width": 5000,
        "forward_depth": 7,
        "keep_full_ordered_words": true,
        "score": [
          "abelian_lower_bound",
          "total_word_length",
          "exact_word_lexicographic_order"
        ],
        "stop_first_valid_improvement": true
      },
      "guards": {
        "wall_seconds": 150,
        "max_official_move_calls": 1500000
      },
      "resource_pruning": "only admissible abelian lower-bound for g+h>12; beam discarded states make nonexhaustive",
      "evidence_scope": "one known development instance; no dual-arm causal gain/token/search-speed claim; ordinary8/13 and Stable08491=10 only regression",
      "dependencies": [
        {
          "id": "M-95d49b3f9570d1f2",
          "revision": 1
        },
        {
          "id": "external/concept-transformations-20261117-resources",
          "revision": 1
        }
      ]
    },
    "restoration": {
      "official": "/output/round3-fixed/official",
      "acceptance": "/output/round3-fixed/acceptance",
      "archive_sha256": "c8ed06893cf895f1221cae149de5b1c4af1657f713aeaf225618723ced9960d6",
      "files_verified": 41
    },
    "regression_verdicts": {
      "ac-07445": {
        "ok": true,
        "length": 13,
        "peak_total_relator_length": 13,
        "work": 127,
        "certificate_hash": "sha256:e13f345f7c99dd9813e1e59c6eda976d2a8918b6c79feb3027dc73cfe3483e2a"
      },
      "ac-08491": {
        "ok": true,
        "length": 8,
        "peak_total_relator_length": 9,
        "work": 48,
        "certificate_hash": "sha256:f6b1e9cd8eb7b3778eefce5fc75c4cd8f6297dff5b4d96aaa2ebd0fbdf03ccd1"
      },
      "sac-07445": {
        "ok": true,
        "length": 15,
        "peak_total_relator_length": 13,
        "work": 128,
        "certificate_hash": "sha256:69cdffa8edc863a319ddbadf2822ed1bd0a1fabfe3b83c9cf0fee6fb2008831b"
      },
      "sac-08491": {
        "ok": true,
        "length": 10,
        "peak_total_relator_length": 9,
        "work": 50,
        "certificate_hash": "sha256:3432ef3c28cf1da26ebb85f8c9afd094014420570e06e706721a5bbb9cbeed58"
      }
    },
    "matrix_ball": {
      "states": 3808,
      "layer_sizes": [
        1,
        6,
        21,
        58,
        122,
        240,
        480,
        960,
        1920
      ],
      "complete_radius": true,
      "guard": null
    },
    "reverse_word_ball": {
      "states": 40779,
      "layer_sizes": [
        1,
        10,
        77,
        574,
        4453,
        35664
      ],
      "complete_radius": true,
      "guard": null,
      "sha256": "4b26b0fb328aac1aff08b64de041fc724053b20c7941c30a5c341a162cab4c50"
    },
    "information_loss_example": {
      "U": [
        [
          2
        ],
        [
          1
        ]
      ],
      "other": [
        [
          1,
          2,
          -1
        ],
        [
          1
        ]
      ],
      "abelianization": [
        [
          0,
          1
        ],
        [
          1,
          0
        ]
      ],
      "same_matrix": true,
      "same_exact_goal": false
    },
    "layers": [
      {
        "depth": 1,
        "generated": 14,
        "abelian_pruned": 0,
        "previously_kept_revisits": 0,
        "candidate_states": 14,
        "kept": 14,
        "beam_discarded": 0,
        "distinct_matrices_among_kept": 7
      },
      {
        "depth": 2,
        "generated": 196,
        "abelian_pruned": 0,
        "previously_kept_revisits": 14,
        "candidate_states": 145,
        "kept": 145,
        "beam_discarded": 0,
        "distinct_matrices_among_kept": 28
      },
      {
        "depth": 3,
        "generated": 2030,
        "abelian_pruned": 0,
        "previously_kept_revisits": 184,
        "candidate_states": 1388,
        "kept": 1388,
        "beam_discarded": 0,
        "distinct_matrices_among_kept": 86
      },
      {
        "depth": 4,
        "generated": 19432,
        "abelian_pruned": 0,
        "previously_kept_revisits": 1864,
        "candidate_states": 12895,
        "kept": 5000,
        "beam_discarded": 7895,
        "distinct_matrices_among_kept": 59
      },
      {
        "depth": 5,
        "generated": 70000,
        "abelian_pruned": 0,
        "previously_kept_revisits": 7709,
        "candidate_states": 46172,
        "kept": 5000,
        "beam_discarded": 41172,
        "distinct_matrices_among_kept": 16
      },
      {
        "depth": 6,
        "generated": 70000,
        "abelian_pruned": 0,
        "previously_kept_revisits": 8937,
        "candidate_states": 48160,
        "kept": 5000,
        "beam_discarded": 43160,
        "distinct_matrices_among_kept": 5
      },
      {
        "depth": 7,
        "generated": 70000,
        "abelian_pruned": 0,
        "previously_kept_revisits": 9419,
        "candidate_states": 49731,
        "kept": 5000,
        "beam_discarded": 44731,
        "distinct_matrices_among_kept": 1
      }
    ],
    "search_guard": null,
    "winner": null,
    "best_stable_length": 15,
    "strict_improvement": false,
    "official_move_calls": 303283,
    "elapsed_seconds": 11.66964180499781,
    "beam_discarded_total": 136958,
    "complete_search": false,
    "scope": "No global lower bound from beam; no-stabilization subclass only, no free swap/relabel, no causal gain claim",
    "external_review": "Stable08491 exactly10 is subsequent EXTERNAL verification; native previous failure unchanged",
    "platform_upload": false,
    "acceptance": {
      "kind": "external_preflight",
      "native_receipt": false,
      "platform_upload": false,
      "official_commit": "a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e",
      "candidate_input_sha256": "0e07b08115d9da832fd30a9067316395b4e44ae087874ad877acc118e65f139a",
      "baseline_registry_sha256": "2b1d3ec4829e6e283afff0172c5af32ab47bcccb64a60d2c95001ca7585e2865",
      "candidate_input_bytes": 104,
      "macro_dictionary_sha256": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
      "expanded_moves": [
        6,
        4,
        12,
        1,
        3,
        6,
        12,
        2,
        5,
        6,
        4,
        2,
        4,
        16,
        15
      ],
      "official_verdict": {
        "ok": true,
        "length": 15,
        "peak_total_relator_length": 13,
        "work": 128,
        "certificate_hash": "sha256:69cdffa8edc863a319ddbadf2822ed1bd0a1fabfe3b83c9cf0fee6fb2008831b"
      },
      "lengths": {
        "input_token_length": 15,
        "dictionary_token_length": 15,
        "expanded_primitive_length": 15
      },
      "official_source_fingerprints": [
        {
          "path": "competition/tools/verifier/canon.py",
          "sha256": "36cc9e6e79c8087ffaa48c50e2643872e8a0eb4ab0e134e601526604d9abf297"
        },
        {
          "path": "competition/tools/verifier/core.py",
          "sha256": "d2972711dc7008679127a987a8965d41ea1606b0fc50bf67e2e06c71c456b3b5"
        },
        {
          "path": "competition/tools/verifier/stable_core.py",
          "sha256": "234b164c766bf7fd2e1bee7f7bfb3910319c5885e4250bf56520d2d2b0f46e9d"
        },
        {
          "path": "competition/tools/verifier/specs.py",
          "sha256": "181102f058f85b3c793d95127051ac21de793e370a2c4d1f5a9808ae59cb3ed0"
        },
        {
          "path": "competition/tools/verifier/data/move_spec.json",
          "sha256": "411d5d4e791a005c799ce0963b71ccd12f1dc8626c12478122fa06c621cbf708"
        },
        {
          "path": "competition/tools/verifier/data/stable_move_spec.json",
          "sha256": "e31c1afd524b731d45a90439a14429ceac305fb87a415bed7f856ca7d08a86a9"
        },
        {
          "path": "competition/tools/verifier/data/manifest.json",
          "sha256": "dc8587d7dc6855edfb8aad087f27f4db59c558f66bdf838b664c1634a357ad37"
        }
      ],
      "challenge_id": "sac-07445",
      "fixture_only": false,
      "competition_record_claim": false,
      "comparison_scope": "our_fixed_archived_paths_not_live_leaderboard",
      "baseline_entry_sha256": "f0bfa0aa6d2f7b2daec011057041677b701f651974ab1f4de626db1ed934cd1d",
      "baseline_moves_sha256": "e2f5b4397ececf2676655a06c6e20ff2cd585bb2bce4217eadf6567b5da9e74d",
      "baseline_expanded_primitive_length": 15,
      "baseline_official_verdict": {
        "ok": true,
        "length": 15,
        "peak_total_relator_length": 13,
        "work": 128,
        "certificate_hash": "sha256:69cdffa8edc863a319ddbadf2822ed1bd0a1fabfe3b83c9cf0fee6fb2008831b"
      },
      "official_manifest_hash": "sha256:eeeb5cfec64e5ac797f32516c6f1a659383262df6d710cb1a713744e6540b745",
      "official_instance_hash": "sha256:f704cfdedbc0b2205b6af5e0aaff9de3ea51826121e55252dcd72ecbf7637477",
      "official_move_spec": {
        "move_spec_version": "sac-r8-v1",
        "move_spec_hash": "sha256:27ecd0ebd4af39871cbfb23ecbd8be73710e85e04d8be788c1d81117d9f4b2b0",
        "file": "stable_move_spec.json",
        "target_relators": [],
        "max_rank": 8,
        "id_prefix": "sac-"
      },
      "proved_minimum": null,
      "status": "no_strict_improvement",
      "accepted_as_strict_improvement": false,
      "macro_count": 0,
      "strict_primitive_length_decrease": false,
      "fixed_archived_baseline_improvement": false
    }
  },
  "checkpoint_field_projection": {
    "layers": [
      {
        "depth": 1,
        "generated": 14,
        "abelian_pruned": 0,
        "previously_kept_revisits": 0,
        "candidate_states": 14,
        "kept": 14,
        "beam_discarded": 0,
        "distinct_matrices_among_kept": 7
      },
      {
        "depth": 2,
        "generated": 196,
        "abelian_pruned": 0,
        "previously_kept_revisits": 14,
        "candidate_states": 145,
        "kept": 145,
        "beam_discarded": 0,
        "distinct_matrices_among_kept": 28
      },
      {
        "depth": 3,
        "generated": 2030,
        "abelian_pruned": 0,
        "previously_kept_revisits": 184,
        "candidate_states": 1388,
        "kept": 1388,
        "beam_discarded": 0,
        "distinct_matrices_among_kept": 86
      },
      {
        "depth": 4,
        "generated": 19432,
        "abelian_pruned": 0,
        "previously_kept_revisits": 1864,
        "candidate_states": 12895,
        "kept": 5000,
        "beam_discarded": 7895,
        "distinct_matrices_among_kept": 59
      },
      {
        "depth": 5,
        "generated": 70000,
        "abelian_pruned": 0,
        "previously_kept_revisits": 7709,
        "candidate_states": 46172,
        "kept": 5000,
        "beam_discarded": 41172,
        "distinct_matrices_among_kept": 16
      },
      {
        "depth": 6,
        "generated": 70000,
        "abelian_pruned": 0,
        "previously_kept_revisits": 8937,
        "candidate_states": 48160,
        "kept": 5000,
        "beam_discarded": 43160,
        "distinct_matrices_among_kept": 5
      },
      {
        "depth": 7,
        "generated": 70000,
        "abelian_pruned": 0,
        "previously_kept_revisits": 9419,
        "candidate_states": 49731,
        "kept": 5000,
        "beam_discarded": 44731,
        "distinct_matrices_among_kept": 1
      }
    ],
    "winner": null,
    "official_calls": 303283
  },
  "candidate_field_projection": {
    "challenge_id": "sac-07445",
    "tokens": [
      6,
      4,
      12,
      1,
      3,
      6,
      12,
      2,
      5,
      6,
      4,
      2,
      4,
      16,
      15
    ],
    "macros": {}
  },
  "cli_complete_values": {
    "returncode": 0,
    "stdout": "{\n  \"accepted\": true,\n  \"results\": [\n    {\n      \"certificate_hash\": \"sha256:e13f345f7c99dd9813e1e59c6eda976d2a8918b6c79feb3027dc73cfe3483e2a\",\n      \"challenge_id\": \"ac-07445\",\n      \"length\": 13,\n      \"ok\": true,\n      \"work\": 127\n    },\n    {\n      \"certificate_hash\": \"sha256:f6b1e9cd8eb7b3778eefce5fc75c4cd8f6297dff5b4d96aaa2ebd0fbdf03ccd1\",\n      \"challenge_id\": \"ac-08491\",\n      \"length\": 8,\n      \"ok\": true,\n      \"work\": 48\n    },\n    {\n      \"certificate_hash\": \"sha256:69cdffa8edc863a319ddbadf2822ed1bd0a1fabfe3b83c9cf0fee6fb2008831b\",\n      \"challenge_id\": \"sac-07445\",\n      \"length\": 15,\n      \"ok\": true,\n      \"work\": 128\n    },\n    {\n      \"certificate_hash\": \"sha256:3432ef3c28cf1da26ebb85f8c9afd094014420570e06e706721a5bbb9cbeed58\",\n      \"challenge_id\": \"sac-08491\",\n      \"length\": 10,\n      \"ok\": true,\n      \"work\": 50\n    }\n  ]\n}\n",
    "stderr": ""
  },
  "source_mappings": [
    {
      "body_source_line": 10,
      "macro": "macros/raw.source.md",
      "macro_hash": "67ececca3997f000b8d50523fa3bb68af48f319b039493b87d0ce30414cb3bd8",
      "map": ".provenance/maps/cae0aef3f86d8fa4ddaede199b6953f54e14e9ec5b12e84c2132f0b6fb89e218.json",
      "output": "round3-protocol.json",
      "output_hash": "50e4947c3e3458d2f854b07a34224befdc24ec3180c68de9d22715977e0080a7",
      "source": "files/application/round3-protocol.json.tex",
      "source_revision": "176395c299be95781e67506f5af0b5d11a7dbbde4058cc67d6709bd44ed5a7f5",
      "generated_line_count": 55
    },
    {
      "body_source_line": 10,
      "macro": "macros/raw.source.md",
      "macro_hash": "67ececca3997f000b8d50523fa3bb68af48f319b039493b87d0ce30414cb3bd8",
      "map": ".provenance/maps/f32a19ee35b64755fdd548b08a6373fab0f4e944189b601b0953b8c7b248d431.json",
      "output": "round3-target-search.py",
      "output_hash": "e014ffc2c90c77a79c4cea2ea8601029ab18c8d6cc1cc5b2e50e134f84e1786a",
      "source": "files/application/round3-target-search.py.tex",
      "source_revision": "83729b0a652916bc94e2e23d8602e86fa92b6c4f0054c0826669f023b76ae561",
      "generated_line_count": 144
    }
  ],
  "artifacts": [
    {
      "id": "artifact-0f126ccf72b27a2e3cf7ba6f7f04a883d725aee3e93fbd1a7ca72726edfab88c",
      "path": "round3-results.json",
      "expected_sha256": "68d994ea5391a887753b7ab126cd89d666f124733bab00f568e5fb622c4ed6d1",
      "valid": true,
      "snapshot_id": "2c3db8649a4359d58446f4e834afc34afabccdd7e2a38da3055a831ddae64d95",
      "source_set": "2c3db8649a4359d58446f4e834afc34afabccdd7e2a38da3055a831ddae64d95",
      "expected_executable": false,
      "actual_sha256": "68d994ea5391a887753b7ab126cd89d666f124733bab00f568e5fb622c4ed6d1",
      "bytes": 9416,
      "actual_executable": false,
      "bytes_verified": true
    },
    {
      "id": "artifact-07b0abdc552c9c6c2548888ea0028b413f29084eed8d257f35cc5f918f6fcaee",
      "path": "round3-reverse.json",
      "expected_sha256": "7c0ee1286f1529a269af2d8d665243ff1f9b841f233b763ee575274041731ed9",
      "valid": true,
      "snapshot_id": "2c3db8649a4359d58446f4e834afc34afabccdd7e2a38da3055a831ddae64d95",
      "source_set": "2c3db8649a4359d58446f4e834afc34afabccdd7e2a38da3055a831ddae64d95",
      "expected_executable": false,
      "actual_sha256": "7c0ee1286f1529a269af2d8d665243ff1f9b841f233b763ee575274041731ed9",
      "bytes": 12517205,
      "actual_executable": false,
      "bytes_verified": true
    },
    {
      "id": "artifact-295cbbcbca518a643989df5681cb135a252dafab91a7f86de51aae95eb514b38",
      "path": "round3-checkpoint.json",
      "expected_sha256": "78819eff5faff568936bd9808b4aced6a73728a6107fac97780cd809e696b28d",
      "valid": true,
      "snapshot_id": "2c3db8649a4359d58446f4e834afc34afabccdd7e2a38da3055a831ddae64d95",
      "source_set": "2c3db8649a4359d58446f4e834afc34afabccdd7e2a38da3055a831ddae64d95",
      "expected_executable": false,
      "actual_sha256": "78819eff5faff568936bd9808b4aced6a73728a6107fac97780cd809e696b28d",
      "bytes": 1773,
      "actual_executable": false,
      "bytes_verified": true
    },
    {
      "id": "artifact-17e3b2d257ee4c486e30aa51f01c28151391881df837c2e2c270080f152952f2",
      "path": "round3-candidate.json",
      "expected_sha256": "b3674e9483d9bd5ee0a2730f88eeab27cd954b580e898702d0397bae8ec39063",
      "valid": true,
      "snapshot_id": "2c3db8649a4359d58446f4e834afc34afabccdd7e2a38da3055a831ddae64d95",
      "source_set": "2c3db8649a4359d58446f4e834afc34afabccdd7e2a38da3055a831ddae64d95",
      "expected_executable": false,
      "actual_sha256": "b3674e9483d9bd5ee0a2730f88eeab27cd954b580e898702d0397bae8ec39063",
      "bytes": 177,
      "actual_executable": false,
      "bytes_verified": true
    },
    {
      "id": "artifact-eacfd60e5aa28bc9e9c9674ffd557143880dd16bb2cc455354c60062763e9ab0",
      "path": "round3-submission.txt",
      "expected_sha256": "a5061ca016dd710a8a0ea2909bba1a08a796b2c6a75152ee0019d65408c969f2",
      "valid": true,
      "snapshot_id": "2c3db8649a4359d58446f4e834afc34afabccdd7e2a38da3055a831ddae64d95",
      "source_set": "2c3db8649a4359d58446f4e834afc34afabccdd7e2a38da3055a831ddae64d95",
      "expected_executable": false,
      "actual_sha256": "a5061ca016dd710a8a0ea2909bba1a08a796b2c6a75152ee0019d65408c969f2",
      "bytes": 196,
      "actual_executable": false,
      "bytes_verified": true
    },
    {
      "id": "artifact-3c7c844d29e8d784a517b832fb4b67e568d300ead1b31ee3344024bea23aa73e",
      "path": "round3-cli.json",
      "expected_sha256": "a4160c60722f357c8825d2243deccf04df6060272e03cf870fc0819713e5b925",
      "valid": true,
      "snapshot_id": "2c3db8649a4359d58446f4e834afc34afabccdd7e2a38da3055a831ddae64d95",
      "source_set": "2c3db8649a4359d58446f4e834afc34afabccdd7e2a38da3055a831ddae64d95",
      "expected_executable": false,
      "actual_sha256": "a4160c60722f357c8825d2243deccf04df6060272e03cf870fc0819713e5b925",
      "bytes": 1004,
      "actual_executable": false,
      "bytes_verified": true
    }
  ],
  "reverse_body_read_error": {
    "ok": false,
    "error": "Result must be a regular file no larger than 8 MiB",
    "kind": "result_size",
    "replay_allowed": false,
    "host_workflow_budget": {
      "experiment_id": "native-concept-transformations-sol-20261117-03",
      "native_turns_remaining": 4,
      "remaining_seconds": 8615.146837949753
    }
  },
  "limitations": [
    "Selected pointer views reconstructed, not byte-exact copy or claim to full source read by model",
    "Reverse artifact >8MiB; hash verified by host, body not read by model",
    "303283 counts move wrapper only, excludes regressions, try_join replay, acceptance and CLI internals",
    "Winner null is no accepted shorter candidate, not certified empty full search space",
    "Beam discarded states and lexicographic per-word prefix selection are not a resource Pareto frontier"
  ]
}
