#!/usr/bin/env python3
"""fapm_check: static analysis of a Feature-Annotated Process Model.

Reads a pipeline annotation (YAML, see SPEC.md) and reports structural findings:

  G1  missing-producer   a node requires or consumes a feature that no upstream node
                         produces on every path and that is not declared external
  G2  branch-dependent   a required/consumed feature is produced on some incoming paths only
  G3  undeclared-flow    a node lists a feature as available that has no producer and no
                         declared external source (provenance unaccounted for)
  G4  provenance-gap     governance requires a feature to be traceable from the provenance
                         record, but the record does not include it
  G5  unstructured       a feature on a branch output is free text, so downstream monitoring
                         cannot classify it

Usage:  python tools/fapm_check.py examples/ambient-documentation/pipeline.yaml [--json]
Exit code is 1 if any G1, G2 or G4 finding is present.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict

import yaml


@dataclass
class Finding:
    code: str
    kind: str
    node: str
    feature: str
    detail: str


def _names(items) -> list[str]:
    return [i["name"] if isinstance(i, dict) else i for i in (items or [])]


def _typed(items) -> list[dict]:
    return [i for i in (items or []) if isinstance(i, dict)]


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def topo_order(nodes: dict[str, dict]) -> list[str]:
    indeg = {n: 0 for n in nodes}
    for n in nodes.values():
        for m in n.get("next", []):
            indeg[m] += 1
    queue = [n for n, d in indeg.items() if d == 0]
    order = []
    while queue:
        n = queue.pop(0)
        order.append(n)
        for m in nodes[n].get("next", []):
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    if len(order) != len(nodes):
        raise SystemExit("fapm_check: pipeline graph has a cycle; loops are not supported in v0.1")
    return order


def out_sets(node: dict) -> tuple[set[str], set[str]]:
    """Features a node guarantees (every branch) and possibly produces (any branch)."""
    base = set(_names(node.get("produced")))
    branches = node.get("branches") or []
    if not branches:
        return base, base
    per_branch = [set(_names(b.get("produced"))) for b in branches]
    return base | set.intersection(*per_branch), base | set.union(*per_branch)


def check(model: dict) -> list[Finding]:
    nodes = {n["id"]: n for n in model["nodes"]}
    order = topo_order(nodes)
    preds: dict[str, list[str]] = {n: [] for n in nodes}
    for n in nodes.values():
        for m in n.get("next", []):
            preds[m].append(n["id"])

    # External features become available from their declared node onward.
    ext_from: dict[str, str] = {e["name"]: e["from"] for e in model.get("external", [])}
    reach: dict[str, set[str]] = {}  # node -> set of nodes at or upstream of it
    for nid in order:
        reach[nid] = {nid}.union(*(reach[p] for p in preds[nid])) if preds[nid] else {nid}

    def external_at(nid: str) -> set[str]:
        return {f for f, src in ext_from.items() if src in reach[nid]}

    guaranteed_in: dict[str, set[str]] = {}
    possible_in: dict[str, set[str]] = {}
    guaranteed_out: dict[str, set[str]] = {}
    possible_out: dict[str, set[str]] = {}
    for nid in order:
        if preds[nid]:
            guaranteed_in[nid] = set.intersection(*(guaranteed_out[p] for p in preds[nid]))
            possible_in[nid] = set.union(*(possible_out[p] for p in preds[nid]))
        else:
            guaranteed_in[nid], possible_in[nid] = set(), set()
        g, p = out_sets(nodes[nid])
        guaranteed_out[nid] = guaranteed_in[nid] | g
        possible_out[nid] = possible_in[nid] | p

    findings: list[Finding] = []
    for nid in order:
        node = nodes[nid]
        ext = external_at(nid)
        guaranteed = guaranteed_in[nid] | ext
        possible = possible_in[nid] | ext
        reported: set[str] = set()

        needed = [(f, "required") for f in _names(node.get("required"))]
        needed += [(f, "consumed") for f in _names(node.get("consumed")) if f not in _names(node.get("required"))]
        for f, role in needed:
            if f in guaranteed or f in reported:
                continue
            reported.add(f)
            if f in possible:
                findings.append(Finding("G2", "branch-dependent", nid, f,
                    f"{role} here but produced on only some incoming paths"))
            else:
                findings.append(Finding("G1", "missing-producer", nid, f,
                    f"{role} here but no upstream node produces it and it is not declared external"))

        for f in _names(node.get("available")):
            if f in possible or f in reported:
                continue
            reported.add(f)
            findings.append(Finding("G3", "undeclared-flow", nid, f,
                "listed as available but has no producer and no declared external source"))

        for b in node.get("branches") or []:
            for t in _typed(b.get("produced")):
                if t.get("type") == "free_text":
                    findings.append(Finding("G5", "unstructured", f"{nid}/{b['id']}", t["name"],
                        "branch output is free text; downstream monitoring cannot classify it"))

    prov = model.get("provenance")
    if prov:
        includes = set(prov.get("includes", []))
        for f in prov.get("required", []):
            if f not in includes:
                findings.append(Finding("G4", "provenance-gap", prov["produced_at"], f,
                    f"governance requires this to be traceable but {prov['record']} does not include it"))
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pipeline")
    ap.add_argument("--json", action="store_true", help="emit findings as JSON")
    args = ap.parse_args()

    model = load(args.pipeline)
    findings = check(model)

    if args.json:
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        print(f"{model.get('title', model.get('pipeline'))}: {len(findings)} finding(s)\n")
        for f in findings:
            print(f"  {f.code} {f.kind:<17} {f.node:<6} {f.feature:<26} {f.detail}")
    return 1 if any(f.code in {"G1", "G2", "G4"} for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
