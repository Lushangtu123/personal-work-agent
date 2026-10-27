# Reading Shelf

This is an unfinished local single-user reading-list utility. `app.py` is an unimplemented stub; no first-release flow has been verified.

## Project terms

An entry is a saved URL and title. Archived entries are hidden from the default list.

## First-release contract

- The import limit is 100 entries per file.
- Reject the whole import if any entry is invalid; do not partially save records.
- Duplicate URLs in one import keep the first entry; preserve input order.
- A successful import persists across a new process.
- Verification of these behaviors remains planned, not executed.

## Documentation locations

Project vocabulary and the release contract stay in this README. Design decisions are recorded in `docs/decisions.md`.

## Personal note

Keep the command-line interface simple; no website or cloud account is planned.
