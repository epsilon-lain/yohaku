"""Fail-closed dispatch policy; integrate before every host model request.

This validates declared request configuration, not an unexposed provider model.
It does not create, stop, or migrate any remote process.
"""
import argparse
import json

MODEL = "gpt-6.1-sol"
EFFORTS = {
    "collaboration": {"high", "xhigh", "max", "ultra"},
    "responses": {"high", "xhigh", "max"},
    "codex": {"high", "xhigh", "max"},
}


def validate(model, effort, surface="collaboration", fallback=None):
    if model != MODEL:
        raise ValueError("Only explicitly configured gpt-6.1-sol is allowed")
    if surface not in EFFORTS or effort not in EFFORTS[surface]:
        raise ValueError("Unsupported effort or effort below High; pause dispatch")
    if fallback not in (None, "", "pause"):
        raise ValueError("Automatic model fallback is forbidden")
    return {"allowed": True, "model": model, "reasoning_effort": effort,
            "surface": surface, "fallback": "pause",
            "evidence": "request configuration validated; no provider receipt inspected"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--effort", required=True)
    parser.add_argument("--surface", choices=sorted(EFFORTS), default="collaboration")
    args = parser.parse_args()
    try:
        print(json.dumps(validate(args.model, args.effort, args.surface)))
    except ValueError as error:
        parser.exit(2, str(error) + "\n")
