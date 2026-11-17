{
  "format": "round3-delayed-execution-block/1",
  "stage": "native-concept-transformations-sol-20261117-02",
  "user_event": 968,
  "user_authorized_new_request": true,
  "request_id": "app-r3-07445-target-info-delayed-v2",
  "action": "round3-target-search",
  "project_id": "native-application",
  "planned_source_set": "2c3db8649a4359d58446f4e834afc34afabccdd7e2a38da3055a831ddae64d95",
  "source_revision": "83729b0a652916bc94e2e23d8602e86fa92b6c4f0054c0826669f023b76ae561",
  "protocol_revision": "176395c299be95781e67506f5af0b5d11a7dbbde4058cc67d6709bd44ed5a7f5",
  "submit": {
    "ok": false,
    "error": "New native admission stopped; original tasks are retained",
    "error_type": "GateStopped",
    "replay_unknown_request": false
  },
  "status": {
    "ok": false,
    "error": "No task with this identity; no process targeted",
    "kind": "unknown_task",
    "replay_allowed": false,
    "task_id": "project-task-72d32b9295e96f94419b9ca251029e4a",
    "host_workflow_budget": {
      "experiment_id": "native-concept-transformations-sol-20261117-02",
      "native_turns_remaining": 6,
      "remaining_seconds": 9125.5916929245
    }
  },
  "resources": {
    "ok": true,
    "result": {
      "experiment_id": "native-concept-transformations-sol-20261117-02",
      "phase": "open",
      "shared_stop": {
        "reason": "Continuation dispatch requires original-ID inspection",
        "evidence": {
          "queue_id": 2,
          "request_id": "continue-d637079e69fc161c056a4746b87a0251",
          "error": "Worker resource profile exceeds native envelope"
        },
        "at": 1794887889.9293995,
        "new_dispatch_allowed": false
      },
      "leaders": {
        "theory": "ai-node-b912b62d9e95d94ddb26bfd6",
        "application": "ai-node-0299a356d74db83b9ab4ebc7"
      },
      "members": [
        "ai-node-60ce43c0fdb954913d5cf32f",
        "ai-node-b912b62d9e95d94ddb26bfd6",
        "ai-node-0299a356d74db83b9ab4ebc7"
      ],
      "native_turns_reserved": 3,
      "native_turns_remaining": 6,
      "remaining_seconds": 9125.857843875885,
      "provider_identity": "unknown; requested/native thread configuration separately recorded",
      "provider_cost": "unknown",
      "adaption_authority_used": false
    }
  },
  "no_execution_receipt": true,
  "no_new_search_or_cli_results": true,
  "not_a_negative_search_experiment": true,
  "no_platform_upload": true,
  "old_records_unchanged": true
}
