# Supplied user decisions — 2026-10-14

Synthetic evaluation input containing confirmed user choices for this task.

- U01 — "Entry/条目" means one saved URL with title and optional personal notes. "Archive/归档" keeps the entry and its notes but excludes it from the default list. It is not deletion.
- U02 — Replace the prototype's JSON storage choice with SQLite for the first release, because import and archive changes need transaction boundaries. This replaces D01; its earlier rationale should remain available. The CLI remains local and single-user. This is an accepted design, not an implemented feature.
- U03 — Change the limit from 100 to exactly 200 entries per import file. Keep all-or-nothing failure, first occurrence wins for duplicate URLs, input order, and cross-process persistence requirements unchanged.
- U04 — Unicode title normalization has not been decided. Do not infer a normalization form or silently normalize titles.
- U05 — Update only the existing README and decision record. Keep implementation, these supplied notes, and all other content unchanged. Do not create a new glossary, ADR directory, or global instruction file. No tests have been executed for this first release.
