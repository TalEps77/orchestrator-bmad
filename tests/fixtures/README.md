# Catalog fixtures

These CSVs project only actual workflow names and required flags from the core
and BMM module-help catalogs in BMAD-METHOD; descriptions/instructions are omitted.
They test routing and gate selection, not LLM execution of those workflows.

- 6.8.0: commit `3bcd6c3cce6e381b759e23185b099081496567a5`.
- 6.11.0: commit `9ce3c397c9b238de96f7365da8019f6f66b059da`.
- Source paths: `src/bmm-skills/module-help.csv` and
  `src/core-skills/module-help.csv` in each tag.
- Upstream: https://github.com/bmad-code-org/BMAD-METHOD

Refresh deliberately with Python csv.DictReader, projecting `skill,required`
for rows whose skill starts with `bmad-`. Do not fabricate removed commands to
make a test pass. Other tests use deliberately small synthetic catalogs.
