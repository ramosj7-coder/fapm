# Rules for this repository

This is a **public** repository for the FAPM specification. Everything committed here, including history, is visible to anyone.

## Hard rule: no employer-specific content

Nothing tied to the owner's employer may be committed: its name, programs, colleagues, committees, internal
metrics or thresholds, vendor or contract status, EHR build details, or any patient data. Examples must be
synthetic and vendor-agnostic. If a request would put any of that here, stop and ask the owner.

Run `scripts/content-guard.sh` before every commit and push; do not push if it fails. Private terms live in
`~/.config/content-guard/extra.txt` and the `CONTENT_GUARD_EXTRA` Actions secret, never in the repo.

## Working on the spec

- `SPEC.md` is normative. Change definitions there first, then the checker, then the examples.
- Any change to `examples/*/pipeline.yaml` or `tools/fapm_check.py` must keep `pytest -q tools` passing;
  update `EXPECTED` in `tools/test_fapm_check.py` and the example README together if findings change.
- Bump `version` in `CITATION.cff` on each release.
- Documentation is CC BY 4.0 (`LICENSE`); code in `tools/` is MIT (`tools/LICENSE`).
