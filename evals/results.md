# Behavioral result ledgers

`results.py` checks reviewer-supplied results against a frozen `scenarios.yaml`.
It reads local files and prints JSON; it does not execute a model, candidate
code, evidence files, or remote operations. The contract must retain its
`evals/scenarios.yaml` location inside the matching frozen package: the CLI
validates that package's metadata, including when reviewing an older run.

```sh
python3 -B evals/results.py \
  --contract evals/scenarios.yaml \
  --results /absolute/path/to/run/results.json \
  --skill-sha256 <independently-recorded-frozen-skills-hash>
```

The schema is documented in `results.py --help`. Keep one row per scenario in a
ledger; use separate ledgers for repetitions and version comparisons. Store
evidence below the ledger's directory and refer to it by relative file paths.
Symlinks, external paths, missing files and empty evidence cannot satisfy a
gate. Retain real command outputs, artifacts and review observations; an
agent's final action summary alone is not an independently reviewed tool trace.

The contract hash is SHA-256 of its exact bytes. The skill hash identifies the
whole frozen `skills/` subtree, including both skill entrypoints and references.
Record the hash algorithm with the run and use the same independently recorded
value for `metadata.skill_sha256` and `--skill-sha256`. For example, the existing
`behavior.tree_hash` hashes sorted JSON mapping relative paths to file SHA-256.
Hashes identify inputs; they cannot prove the worker actually loaded them.

Use `reviewed` only after reviewing the actual trace and artifacts. Record
`not_run`, `blocked`, or `unverified` for other cases, with the reason in `notes`.
Unknown model, reasoning or other provenance remains null. Missing metadata
prevents qualification; optional unavailable token/time metrics remain null.
Do not derive token savings or a version improvement from these null values.

Exit statuses:

- `0`: all declared scenarios were evaluated with the required evidence and
  metadata, and the ledger meets the contract under the reviewer's attestations.
- `1`: valid record, incomplete or below the release gate. This is the expected
  outcome for a partial run; retain its successful observations and blockers.
- `2`: malformed input, mismatched identity, or invalid contract.

Every declared hard failure blocks qualification. Critical-zero and unmet
outcomes fail the individual scenario; the unchanged contract determines how
many scenario failures a release may tolerate. A passing subset cannot replace
the full denominator. The validator rejects duplicate IDs, unknown fields and
non-integer scores, and reports missing cases explicitly.

The tool validates consistency and available evidence paths, not semantic
truth, trace authenticity, isolation, skill discovery or reviewer independence.
Keep evaluators and original controls outside worker writes. Run the meaningful
positive and negative controls with the ordinary evaluation-tool unit suite;
synthetic passing ledgers in those tests are not real agent completions.
