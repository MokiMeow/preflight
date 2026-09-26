"""Nonsecret bounded resource plan. Live bootstrap remains operator controlled."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


class PlanError(Exception):
    pass


FIELDS = {
    "account_id",
    "region",
    "operator_label",
    "source_instance_id",
    "source_mode",
    "host_mode",
    "instance_class",
    "allocated_storage_gib",
    "host_instance_type",
    "subnet_group",
    "security_group_ids",
    "max_clones",
    "max_snapshots",
    "approved_spend_ceiling",
    "currency",
    "retention_owner",
    "ssh_cidr",
}


def canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def make_plan(inputs: dict) -> dict:
    if set(inputs) - {"deployment"} != FIELDS:
        raise PlanError("PLAN_INPUT_FIELDS_INVALID")
    if (
        not re.fullmatch(r"\d{12}", str(inputs["account_id"]))
        or not re.fullmatch(r"[a-z]{2}(?:-gov)?-[a-z]+-\d", str(inputs["region"]))
        or inputs["source_mode"] not in {"reuse", "create"}
        or inputs["host_mode"] not in {"reuse", "create"}
        or not isinstance(inputs["max_clones"], int)
        or isinstance(inputs["max_clones"], bool)
        or inputs["max_clones"] != 1
        or not isinstance(inputs["max_snapshots"], int)
        or isinstance(inputs["max_snapshots"], bool)
        or not 1 <= inputs["max_snapshots"] <= 3
        or not isinstance(inputs["approved_spend_ceiling"], (int, float))
        or isinstance(inputs["approved_spend_ceiling"], bool)
        or inputs["approved_spend_ceiling"] <= 0
    ):
        raise PlanError("PLAN_SCOPE_INVALID")
    if (
        any(
            not isinstance(inputs[k], str) or not inputs[k]
            for k in (
                "operator_label",
                "retention_owner",
                "source_instance_id",
                "subnet_group",
                "instance_class",
                "host_instance_type",
                "currency",
                "ssh_cidr",
            )
        )
        or not isinstance(inputs["security_group_ids"], list)
        or not inputs["security_group_ids"]
        or any(
            not isinstance(s, str) or not re.fullmatch(r"sg-[0-9a-f]+", s)
            for s in inputs["security_group_ids"]
        )
        or not isinstance(inputs["allocated_storage_gib"], int)
        or isinstance(inputs["allocated_storage_gib"], bool)
        or not 20 <= inputs["allocated_storage_gib"] <= 100
    ):
        raise PlanError("PLAN_RESOURCE_INPUT_INVALID")
    body = {
        "schema_version": "1",
        "operator_inputs": inputs,
        "storage_type": "gp3",
        "source_count": 1,
        "host_count": 1,
        "engine_major": 18,
        "private_rds": True,
        "pricing_status": "NOT_OBSERVED",
        "aws_identity_status": "NOT_RUN",
        "mutation_status": "NOT_AUTHORIZED",
        "runtime_identity": "separate-instance-role",
        "retention": "no expiry deletion; human cleanup gate; preapply recovery retained",
    }
    return {"plan": body, "plan_sha256": hashlib.sha256(canonical(body)).hexdigest()}


def verify_apply_scope(envelope: dict, approval: dict) -> dict:
    if set(envelope) != {"plan", "plan_sha256"}:
        raise PlanError("PLAN_ENVELOPE_INVALID")
    digest = hashlib.sha256(canonical(envelope["plan"])).hexdigest()
    if envelope["plan_sha256"] != digest:
        raise PlanError("PLAN_DIGEST_MISMATCH")
    plan = make_plan(envelope["plan"]["operator_inputs"])
    if plan != envelope:
        raise PlanError("PLAN_CONTENT_INVALID")
    fields = {
        "plan_sha256",
        "account_id",
        "region",
        "operator_label",
        "approved_spend_ceiling",
        "creation_authorized",
    }
    if set(approval) != fields or approval.get("creation_authorized") is not True:
        raise PlanError("OPERATOR_SCOPE_REQUIRED")
    inputs = envelope["plan"]["operator_inputs"]
    if approval["plan_sha256"] != digest or any(
        approval[k] != inputs[k]
        for k in ("account_id", "region", "operator_label", "approved_spend_ceiling")
    ):
        raise PlanError("OPERATOR_SCOPE_MISMATCH")
    return envelope["plan"]


def read_json(path: str) -> dict:
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise PlanError("DUPLICATE_JSON_KEY")
            value[key] = item
        return value

    value = json.loads(
        Path(path).read_text(encoding="utf-8"),
        object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(PlanError("INVALID_JSON")),
    )
    if not isinstance(value, dict):
        raise PlanError("INVALID_JSON")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("--inputs", required=True)
    plan.add_argument("--out", required=True)
    apply = commands.add_parser("apply")
    apply.add_argument("--plan", required=True)
    apply.add_argument("--approval", required=True)
    apply.add_argument("--state-dir", required=True)
    args = parser.parse_args()
    try:
        if args.mode == "plan":
            result = make_plan(read_json(args.inputs))
            Path(args.out).write_bytes(canonical(result) + b"\n")
            print("PLAN_SAVED; AWS identity/pricing NOT_RUN; no resources created")
            return 0
        from cloud_bootstrap import execute_bootstrap

        execute_bootstrap(read_json(args.plan), read_json(args.approval), args.state_dir)
        print(
            "BOOTSTRAP_OBSERVED; database roles/fixture/TLS readiness require independent verification"
        )
        return 0
    except (PlanError, ValueError, KeyError, TypeError, OSError) as exc:
        # Do not echo input, file path or credentials-bearing provider messages.
        print(str(exc) if isinstance(exc, PlanError) else "PLAN_INPUT_INVALID")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
