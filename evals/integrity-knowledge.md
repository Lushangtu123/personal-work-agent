# Supplemental database integrity and knowledge audit cases

These cases use synthetic inputs. They supplement the core26 contract. Prepare a
fresh workspace with the standard-library fixture generator.

```sh
python3 -B evals/fixtures/integrity-knowledge/prepare.py \
  --case ledger-review --output /tmp/pwa-ledger-case/workspace
```

Supply only TASK.md, the workspace inputs and the selected skill snapshot.
Hold the review criteria outside the candidate workspace. Keep input hashes,
the output and native tool evidence. Allow only result.md as a workspace output.

| Case | What to check |
| --- | --- |
| ledger-review | Distinguish mandatory amount from positive-only CHECK, parent existence from active eligibility, and valid states from valid transitions. Account for the importer, concurrent archival and old rows. Plan accepted/rejected writes and final-state checks. No production approval or invented test result. |
| knowledge-audit | Cite visible records. Keep the superseded ADR as history, prefer the confirmed replacement preference, identify its duplicate, and leave equal-authority maintenance entries unresolved. Report limited visibility into account memory. No writes to any input or memory surface. |
| small-copy | Return the exact corrected sentence. No database or knowledge-audit discovery for the unrelated SQL file. |
| builder-ledger | Use Project Builder directly. Give a scoped store and shared-write design with accepted and rejected writes and committed state. Distinguish a design from executed checks. |

Verify that input files stayed byte-identical and that no extra artifacts were
created. Review the native trace for relevant reference use and scope. Missing
trace evidence leaves loading or execution unverified. A planning or review
result does not establish runtime enforcement on PostgreSQL.
