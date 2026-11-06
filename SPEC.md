# FAPM Specification, v0.1

**Feature-Annotated Process Model**: a way to specify a clinical AI workflow so that the same document works for a governance committee, an engineering team, and an auditor.

Status: draft for public comment. Version 0.1 is the first public release; breaking changes are possible before 1.0.

---

## 1. The problem FAPM addresses

A clinical AI workflow is usually described twice. Governance and clinical leaders read a process map: who does what, in what order, with what decision authority. Engineers read a feature specification: data dictionaries, schemas, pipeline contracts. The two are written by different people for different purposes and are reconciled only when something breaks.

Neither one answers the questions that matter most before go-live:

- What data must be present for each step to run, and where does it come from?
- Where does the AI output enter a human decision, and what record does that decision leave?
- Can the final record be traced back to the model version and the inputs that produced it?

FAPM attaches the data specification directly to the process map. Each step declares what it needs, what it can see, what it reads, and what it writes. Gaps in that chain become visible on paper, before deployment, instead of in an incident review afterward.

## 2. Core definitions

### 2.1 Feature

A **feature** is any named data element a workflow step can depend on or create: an identifier, a flag, a score, a document, a permission, a model output. Features are named in `snake_case`. A feature may carry a type; v0.1 defines one type that the checker reads, `free_text`.

### 2.2 Node

A **node** is a discrete step in the workflow. Every node `N` carries four feature sets:

| Set | Meaning |
|---|---|
| `F_required(N)` | Features that must be present for `N` to execute. |
| `F_available(N)` | Features the step can see, whether or not it uses them. |
| `F_consumed(N)` | Features the step actually reads. |
| `F_produced(N)` | Features the step creates or modifies, available to downstream nodes. |

The separation between sets is the point:

- **Required vs. available.** A feature can be present in today's configuration without being guaranteed. Declaring it required makes the dependency explicit.
- **Available vs. consumed.** A step that can see the patient's problem list is different from a step that reads it. Consumed features are latent dependencies: remove them upstream and this step breaks, even if nobody knew it used them.

Well-formedness: `F_consumed(N) ⊆ F_available(N) ∪ F_required(N)`.

### 2.3 External features

Some features enter from outside the pipeline: a person's action, a device, the EHR. These are declared once with the node from which they are available:

```yaml
external:
  - { name: audio_stream, from: N2, source: "capture device" }
```

A feature that is neither produced upstream nor declared external has no stated origin. That is a finding, not an oversight to fix silently.

### 2.4 Branches

A node may route execution down alternative branches. Each branch declares its own `F_produced`. The routing condition is a decision boundary in feature space: a function of the features present at that node. Writing it down forces the question of whether the features it depends on are actually guaranteed.

## 3. Context propagation

Reading a feature does not remove it. Context accumulates as the workflow moves forward.

For a node `N` with predecessors `P₁ … Pₖ`:

```
C_in(N)  = C_out(P₁) ∩ … ∩ C_out(Pₖ)          features guaranteed on every incoming path
C_out(N) = C_in(N) ∪ F_produced(N) ∪ X(N)       X(N): external features declared at or before N
```

For a branching node, `F_produced(N)` in `C_out` is the intersection of the branch outputs: only what every branch produces is guaranteed downstream. The union of branch outputs is the **possible** context.

The **transition delta** from `N` to its successor `M` is what `N` adds:

```
Δ(N → M) = C_out(N) − C_in(N)
```

The delta is the handoff contract between two steps. In a multi-agent pipeline it is literally the specification of what one component must pass to the next.

## 4. Findings

Static analysis of an annotated pipeline yields five kinds of finding. None require the system to be running.

| Code | Finding | Rule |
|---|---|---|
| G1 | Missing producer | `f ∈ F_required(N) ∪ F_consumed(N)` and `f ∉ C_in(N) ∪ X(N)` under any path |
| G2 | Branch-dependent | `f` is required or consumed at `N`, present on some incoming paths, absent on others |
| G3 | Undeclared flow | `f ∈ F_available(N)` with no producer and no external declaration: its provenance is unaccounted for |
| G4 | Provenance gap | Governance requires `f` to be traceable from the final record, but the record does not include it |
| G5 | Unstructured branch output | A branch produces `f` as free text, so downstream monitoring cannot classify it |

G1, G2 and G4 block deployment readiness. G3 and G5 are warnings that need a decision, recorded in the annotation.

### 4.1 Provenance requirements

Audit expectations are declared as features too. The pipeline names its provenance record, what it currently includes, and what governance requires to be traceable:

```yaml
provenance:
  record: finalization_metadata
  produced_at: N5
  includes: [acceptance_flag, model_version_ID]
  required: [model_version_ID, acceptance_flag, rejection_reason]
```

This turns "is this auditable?" from a judgment call into a set comparison.

## 5. Annotation format

A pipeline is a YAML file. See [`examples/ambient-documentation/pipeline.yaml`](examples/ambient-documentation/pipeline.yaml) for a complete one.

```yaml
fapm: "0.1"
pipeline: <slug>
title: <human-readable name>
external:   [ { name, from, source } ]
provenance: { record, produced_at, includes: [], required: [] }
nodes:
  - id: N1
    name: <step name>
    required:  []
    available: []
    consumed:  []
    produced:  []          # or `branches:` with per-branch `produced`
    decision:  <optional>  # routing condition, for branching nodes
    next: [N2]
```

A feature entry is either a name or an object: `{ name: rejection_reason, type: free_text, optional: true }`.

v0.1 supports directed acyclic workflows. Loops (retry, re-review) are planned for a later version.

## 6. Running the checker

```bash
pip install pyyaml
python tools/fapm_check.py examples/ambient-documentation/pipeline.yaml
```

The checker prints one line per finding and exits non-zero if any G1, G2 or G4 finding is present, so it can run as a CI gate on a pipeline specification.

## 7. How FAPM relates to existing methods

FAPM borrows from each of these. It is not a replacement for any of them.

| Method | Readable by a governance committee | Feature-level precision | Usable before deployment | Produces an audit trail |
|---|---|---|---|---|
| BPMN with data objects | Yes | No: data objects are labels, not schemas | Yes | Only with added instrumentation |
| Feature store lineage | No | Yes | No: records what was built | Yes, for the ML pipeline only |
| Object-centric process mining | Partly | Yes | No: needs event logs from a running system | Yes |
| Contextual state machines | Partly | Partly | Yes | Partly |
| **FAPM** | Yes | Yes | Yes | Yes, as a byproduct of the annotation |

These assessments are the author's and have not been independently validated. An empirical comparison of gap detection across methods is planned.

## 8. Regulatory context

FAPM is not a compliance framework, but its outputs line up with what current guidance asks for:

- **NIST AI 600-1** (Generative AI Profile of the AI Risk Management Framework, 2024) recommends provenance tracking and documentation of data and model lineage. A provenance requirement block (§4.1) makes those expectations checkable.
- **FDA PCCP guidance** (final guidance on Predetermined Change Control Plans for AI-enabled device software functions, December 2024) expects planned modifications to be described along with their impact. The transition deltas show which downstream nodes depend on any feature a modification would change.

Both documents are guidance. FAPM does not establish that a system satisfies either.

## 9. Limitations

- One worked example in one clinical domain. Transfer to decision support, imaging and population-health pipelines is argued on structural grounds, not yet shown.
- Annotation quality bounds analysis quality. A feature the annotator never names cannot be checked.
- v0.1 handles acyclic workflows only.
- The checker finds structural gaps. Whether each one matters clinically is a human judgment.
