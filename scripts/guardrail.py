#!/usr/bin/env python3
"""Inspect Terraform plan JSON for a focused set of AWS lab risks."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SEVERITY = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
PUBLIC_CIDRS = {"0.0.0.0/0", "::/0"}
TAGGED_TYPES = {
    "aws_instance",
    "aws_security_group",
    "aws_ebs_volume",
    "aws_db_instance",
    "aws_s3_bucket",
}


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    address: str
    message: str
    remediation: str


def finding(rule_id: str, severity: str, address: str, message: str, remediation: str) -> Finding:
    return Finding(rule_id, severity, address, message, remediation)


def has_public_cidr(rule: dict[str, Any]) -> bool:
    cidrs = rule.get("cidr_blocks") or []
    ipv6 = rule.get("ipv6_cidr_blocks") or []
    single = rule.get("cidr_block")
    if isinstance(single, str):
        cidrs = [*cidrs, single]
    return bool(PUBLIC_CIDRS.intersection(str(cidr) for cidr in [*cidrs, *ipv6]))


def inspect_ingress(rule: dict[str, Any], address: str) -> list[Finding]:
    if not has_public_cidr(rule):
        return []

    direction = str(rule.get("type", "ingress")).lower()
    if direction not in {"ingress", ""}:
        return []

    protocol = str(rule.get("protocol", "tcp")).lower()
    start = rule.get("from_port")
    end = rule.get("to_port")
    findings: list[Finding] = []

    if protocol == "-1":
        findings.append(finding(
            "NET003", "critical", address,
            "A public ingress rule allows every protocol and port.",
            "Limit ingress to the exact application port and trusted CIDR ranges.",
        ))
        return findings

    try:
        first, last = int(start), int(end)
    except (TypeError, ValueError):
        findings.append(finding(
            "NET002", "high", address,
            "A public ingress rule has an unknown port range.",
            "Set a narrow port range and restrict the source CIDR.",
        ))
        return findings

    if first <= 22 <= last:
        findings.append(finding(
            "NET001", "critical", address,
            "SSH is reachable from the public internet.",
            "Remove public SSH; use Systems Manager Session Manager or restrict SSH to a fixed admin CIDR.",
        ))
    if first <= 3389 <= last:
        findings.append(finding(
            "NET004", "critical", address,
            "RDP is reachable from the public internet.",
            "Remove public RDP and use a managed remote-access path.",
        ))
    if not (first == last and first in {80, 443}):
        findings.append(finding(
            "NET002", "high", address,
            f"Public ingress is allowed on TCP ports {first}-{last}.",
            "Expose only the public web ports required by the application; keep admin and app-internal ports private.",
        ))
    return findings


def policy_has_wildcard_allow(policy_value: Any) -> bool:
    if isinstance(policy_value, str):
        try:
            policy_value = json.loads(policy_value)
        except json.JSONDecodeError:
            return False
    if not isinstance(policy_value, dict):
        return False
    statements = policy_value.get("Statement", [])
    if isinstance(statements, dict):
        statements = [statements]
    for statement in statements if isinstance(statements, list) else []:
        if not isinstance(statement, dict) or statement.get("Effect") != "Allow":
            continue
        actions = statement.get("Action", [])
        resources = statement.get("Resource", [])
        actions = [actions] if isinstance(actions, str) else actions
        resources = [resources] if isinstance(resources, str) else resources
        if isinstance(actions, list) and "*" in actions and isinstance(resources, list) and "*" in resources:
            return True
    return False


def inspect_resource(resource: dict[str, Any]) -> list[Finding]:
    address = str(resource.get("address", "unknown resource"))
    resource_type = str(resource.get("type", ""))
    change = resource.get("change") or {}
    actions = change.get("actions") or []
    after = change.get("after")
    if "delete" in actions and "create" not in actions or not isinstance(after, dict):
        return []

    findings: list[Finding] = []

    if resource_type == "aws_security_group":
        for rule in after.get("ingress") or []:
            if isinstance(rule, dict):
                findings.extend(inspect_ingress(rule, address))

    if resource_type == "aws_security_group_rule":
        findings.extend(inspect_ingress(after, address))

    if resource_type == "aws_instance":
        metadata = after.get("metadata_options") or []
        metadata = metadata[0] if isinstance(metadata, list) and metadata else metadata
        if isinstance(metadata, dict) and metadata.get("http_tokens") != "required":
            findings.append(finding(
                "EC2-001", "high", address,
                "IMDSv2 is not required for this instance.",
                "Set metadata_options.http_tokens to required.",
            ))
        for volume in after.get("root_block_device") or []:
            if isinstance(volume, dict) and volume.get("encrypted") is False:
                findings.append(finding(
                    "EBS001", "high", address,
                    "The root EBS volume is explicitly unencrypted.",
                    "Enable EBS encryption for the root volume.",
                ))

    if resource_type == "aws_ebs_volume" and after.get("encrypted") is False:
        findings.append(finding(
            "EBS001", "high", address,
            "The EBS volume is explicitly unencrypted.",
            "Set encrypted = true and review existing snapshots separately.",
        ))

    if resource_type == "aws_db_instance":
        if after.get("publicly_accessible") is True:
            findings.append(finding(
                "RDS001", "critical", address,
                "The database is publicly accessible.",
                "Keep databases in private subnets and allow access only from the application security group.",
            ))
        if after.get("storage_encrypted") is False:
            findings.append(finding(
                "RDS002", "high", address,
                "Database storage encryption is disabled.",
                "Enable storage_encrypted and select an approved KMS key when required.",
            ))

    if resource_type == "aws_s3_bucket_public_access_block":
        public_access_settings = (
            "block_public_acls",
            "block_public_policy",
            "ignore_public_acls",
            "restrict_public_buckets",
        )
        if any(after.get(setting) is False for setting in public_access_settings):
            findings.append(finding(
                "S3-001", "high", address,
                "One or more S3 Block Public Access controls are disabled.",
                "Keep all bucket-level public access controls enabled unless a reviewed static-site design requires otherwise.",
            ))

    if resource_type == "aws_s3_bucket_acl" and str(after.get("acl", "")).startswith("public-"):
        findings.append(finding(
            "S3-002", "high", address,
            f"The bucket ACL is {after.get('acl')}.",
            "Prefer private ACLs and a reviewed CloudFront origin access design for public websites.",
        ))

    if resource_type in {"aws_iam_policy", "aws_iam_role_policy"}:
        policy = after.get("policy")
        if policy_has_wildcard_allow(policy):
            findings.append(finding(
                "IAM001", "high", address,
                "An Allow statement grants both Action * and Resource *.",
                "Replace wildcard actions and resources with the smallest required action/resource set.",
            ))

    if resource_type in TAGGED_TYPES:
        tags = after.get("tags") or {}
        missing = [key for key in ("Project", "Environment") if not tags.get(key)]
        if missing:
            findings.append(finding(
                "TAG001", "medium", address,
                "Required lab tags are missing: " + ", ".join(missing) + ".",
                "Add Project and Environment tags so resources can be attributed and cleaned up safely.",
            ))

    return findings


def inspect_plan(plan: dict[str, Any]) -> list[Finding]:
    changes = plan.get("resource_changes")
    if not isinstance(changes, list):
        raise ValueError("input is not Terraform plan JSON: resource_changes array is missing")
    findings: list[Finding] = []
    for resource in changes:
        if isinstance(resource, dict):
            findings.extend(inspect_resource(resource))
    return findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_json", type=Path, help="Path to JSON produced by terraform show -json")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--fail-on", choices=("never", *SEVERITY.keys()), default="high")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        plan = json.loads(args.plan_json.read_text(encoding="utf-8"))
        if not isinstance(plan, dict):
            raise ValueError("plan JSON root must be an object")
        findings = inspect_plan(plan)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"cloudops-guard: {exc}", file=sys.stderr)
        return 2

    findings.sort(key=lambda item: (-SEVERITY[item.severity], item.rule_id, item.address))
    if args.format == "json":
        print(json.dumps({"finding_count": len(findings), "findings": [asdict(item) for item in findings]}, indent=2))
    elif findings:
        for item in findings:
            print(f"{item.severity.upper():8} {item.rule_id:7} {item.address}: {item.message}")
            print(f"         Fix: {item.remediation}")
        print(f"\n{len(findings)} finding(s).")
    else:
        print("No findings for the rules in this guardrail set.")

    if args.fail_on == "never":
        return 0
    threshold = SEVERITY[args.fail_on]
    return 1 if any(SEVERITY[item.severity] >= threshold for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
