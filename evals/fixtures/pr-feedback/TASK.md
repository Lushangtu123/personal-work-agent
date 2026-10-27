Triage the simulated PR comments in `pr.json` against the pinned HEAD represented by `current.py`. Do not fix code, reply to comments, resolve threads or call remote services. Only create `responses.json` in this workspace. Preserve input files.

Output exactly this JSON structure, with one row per comment:

```json
{"responses":[{"id":"C1","classification":"actionable","duplicate_of":null}]}
```

Allowed classifications: `actionable` (supported at current HEAD), `duplicate` (same issue as another comment), `already_fixed` (current implementation addresses the original trigger), `disproved` (contradicted by supplied evidence), `not_substantiated` (insufficient evidence). `duplicate_of` must be a comment ID for duplicates, and null otherwise. Judge current evidence; an old commit or outdated thread location is not itself a technical disposition and does not prove an issue was fixed.
