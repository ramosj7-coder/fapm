# FAPM: Feature-Annotated Process Models

**A specification method for clinical AI workflows that a governance committee can read, an engineer can build from, and an auditor can trace.**

Most clinical AI deployments are described twice: a process map for the committee and a data specification for the engineers. They drift apart, and the gaps between them show up after go-live as missing audit records, broken handoffs and override data no one can analyze.

FAPM puts both in one artifact. Every step in the workflow declares four sets of features:

```
Node N = {
  F_required:   what must be present for this step to run
  F_available:  what this step can see
  F_consumed:   what it actually reads
  F_produced:   what it creates for the steps downstream
}
```

From those declarations alone, before anything is deployed, you can ask: does every step get what it needs? Where does each input come from? Can the final record be traced back to the model and data that produced it?

## What's here

| | |
|---|---|
| [`SPEC.md`](SPEC.md) | The method: definitions, context propagation, the five kinds of finding, the YAML format |
| [`examples/ambient-documentation/`](examples/ambient-documentation/) | A vendor-agnostic ambient scribe workflow, annotated end to end |
| [`tools/fapm_check.py`](tools/fapm_check.py) | A checker that reads an annotation and reports structural gaps |

## Try it

```bash
pip install -r requirements.txt
python tools/fapm_check.py examples/ambient-documentation/pipeline.yaml
```

On the ambient documentation example, the checker reports six distinct gaps. Four of them came out of the original manual annotation. Two more, including the fact that no step defines which version of the note actually gets signed, only surfaced once the annotation was machine-checked. [Read the walkthrough.](examples/ambient-documentation/README.md)

## Status

Version 0.1, released November 2026 for public comment. The method is a design contribution: it has been demonstrated on one workflow, not validated across many. A methods paper is in preparation.

If you annotate a pipeline of your own, I'd like to hear what the checker found and what it missed. Open an issue.

## History

First sketched in March 2024. Formalized with the ambient documentation example in April 2026. The checker and this public release followed in November 2026. The method was developed with Claude (Anthropic) as a thinking partner.

## Cite

See [`CITATION.cff`](CITATION.cff), or use GitHub's "Cite this repository" button.

## License

Specification and examples: [CC BY 4.0](LICENSE). Code in `tools/`: [MIT](tools/LICENSE).

---

Jorge A. Ramos, MD · [LinkedIn](https://www.linkedin.com/in/jorge8ramos) · [More work](https://github.com/ramosj7-coder/JorgeOle)
