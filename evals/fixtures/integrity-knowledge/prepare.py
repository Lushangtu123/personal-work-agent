"""Prepare synthetic integrity and knowledge audit cases without running an agent."""
import argparse
from hashlib import sha256
import json
from pathlib import Path


CASES = ("ledger-review", "knowledge-audit", "small-copy", "builder-ledger")
COMMON = "Use the selected skill. These are synthetic inputs. Write only result.md.\n\n"
LEDGER_CONTRACT = """# Accepted ledger rules
Amounts are mandatory positive integer cents. New entries may reference only
active categories. Existing entries retain historical links when a category is
archived. Restoring a category makes it eligible for new entries again.
Entries may move from pending to posted or cancelled. Posted and cancelled are
terminal. Both the API and batch importer can write to the same PostgreSQL
database. Production access and execution are outside this request.
"""


def files_for(case):
    if case == "ledger-review":
        return {
            "TASK.md": COMMON + "Review this proposed ledger migration and current writers against the accepted rules. Explain what must change before approval and what would demonstrate enforcement. Review only.\n",
            "contract.md": LEDGER_CONTRACT,
            "migration.sql": """CREATE TABLE category (id integer PRIMARY KEY, archived_at timestamptz);
CREATE TABLE entry (
  id integer PRIMARY KEY,
  amount_cents bigint CHECK (amount_cents > 0),
  category_id integer NOT NULL REFERENCES category (id),
  state text NOT NULL CHECK (state IN ('pending', 'posted', 'cancelled'))
);
""",
            "writers.md": """# Current writers
The API loads the state and checks the requested transition, then issues
UPDATE entry SET state = :requested WHERE id = :id.
The batch importer upserts the supplied fields, including state and category_id,
using only the entry ID as its conflict key. Category archival updates archived_at
from a separate job. Current production data has not been inspected for this review.
""",
            "snapshot.csv": "id,amount_cents,category_id,state\n101,,1,pending\n102,500,1,cancelled\n103,100,2,posted\n",
        }
    if case == "knowledge-audit":
        return {
            "TASK.md": COMMON + "Audit only decisions.md and preferences.md. I have also attached a screenshot transcript of the account memory summary in summary.md. Treat it as an excerpt. Tell me what to keep, consolidate, or confirm with me. This request is for a report.\n",
            "decisions.md": """# Decision log
ADR-03 (2026-06-04, superseded by ADR-07). Use Python 3.10 to match the former host.
ADR-07 (2026-10-29, accepted). Use Python 3.12 for this service after moving hosts.
The older CI workflow was pinned to 3.10, which motivated ADR-03.
""",
            "preferences.md": """# Confirmed preferences
2026-10-01: Daily updates should use paragraphs.
2026-10-27: Use a bulleted list for daily updates. This replaces the Oct 1 format.
2026-10-27 (copy from the same note): Use a bulleted list for daily updates.
2026-11-02 (confirmed, source A): Maintenance window is Tuesday at 17:00 UTC.
2026-11-02 (confirmed, source B): Maintenance window is Thursday at 17:00 UTC.
Both maintenance entries refer to the same service and no priority is recorded.
""",
            "summary.md": "# Account memory summary excerpt\nDaily updates should use paragraphs. The account's underlying memory sources and controls were not provided.\n",
        }
    if case == "small-copy":
        return {
            "TASK.md": COMMON + "Read copy.txt. What should the singular text be? Answer with the exact corrected sentence.\n",
            "copy.txt": "1 reports ready.\n",
            "migration.sql": "CREATE TABLE report (id integer PRIMARY KEY);\n",
        }
    if case == "builder-ledger":
        return {
            "TASK.md": COMMON + "Prepare a first-slice design and acceptance plan for a new ledger on PostgreSQL using contract.md. Choose the store checks and a shared write path. Planning only.\n",
            "contract.md": LEDGER_CONTRACT,
        }
    raise ValueError(case)


def prepare(case, workspace):
    if not workspace.is_absolute():
        raise ValueError("Use a fresh absolute workspace path")
    files = files_for(case)
    workspace.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for name, content in files.items():
        data = content.encode("utf-8")
        (workspace / name).write_bytes(data)
        hashes[name] = sha256(data).hexdigest()
    return {"case": case, "input_sha256": hashes}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.case, args.output), indent=2))
