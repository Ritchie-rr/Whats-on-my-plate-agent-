# Stewardship Knowledge Script — Detailed Guide

What **4-build_stewardship_knowledge_file.py** does, in depth, and why
it's built the way it is. For the short version, see **README-SIMPLE.md**.

## What it produces

`Whats_On_My_Plate_Stewardship_Knowledge.md`, written in plain sentences
(like the existing `Whats_On_My_Plate_Knowledge.md`) so Copilot's
retrieval matches natural questions like "who was at Bank of Utica's last
stewardship meeting" or "what's coming up for ARC Otsego."

This file is written to **both** Master-data and Employee-data, with
identical content in each copy. Everything else in this project splits
into two versions because Ninety rocks and Monday tasks can contain
Leadership-only content that must stay out of the employee-facing agent;
stewardship data doesn't have that problem — it's client account
information (meeting attendees, timelines), not internal work items, so
there's nothing to filter out per audience. Both Copilot agents (the
Master one and, once it exists, the Employee one) get the same
stewardship knowledge.

One section per client, each containing:

- The client's display name and source workbook filename.
- Most recent annual review **meeting date** (Cover tab).
- **Attendees** (Cover tab) — the client and GKG people who were there.
- The client's full **strategic timeline**: every milestone on their
  450-day timeline grid, with its actual calendar date, which activity
  it belongs to (e.g. "Renewal: Employee Benefits"), and who owns it
  (GKG, the client, or both), sorted chronologically.

Sample/test workbooks (anything with "sample" or "test doc" in the
filename) are skipped automatically.

## Where the data comes from

Each client workbook has a **Cover** tab and a **Timeline** tab.

**Cover tab** — fixed cell locations, the same in every client workbook:
client name (`M10`), meeting date (`S14`), attendees (`S15`).

**Timeline tab** — a grid, not a normal table, so it needs a bit more
explanation:
- Row 3 has day offsets from kickoff: 30, 60, 90 … 450 (in columns F
  through T; column E is day 0, the kickoff date itself).
- Row 5 has the actual calendar date for each of those columns.
- Every row from 6 downward is one tracked activity (e.g. "Open
  Enrollment", "Renewal: Property & Casualty") — column B is the
  activity name, column C is who owns it ("GKG", "You", or "GKG & You").
  Any non-empty cell further along that row, in one of the date columns,
  is a milestone for that activity — its column tells you the date (from
  row 5), its text is the milestone label.

The script scans every row/column combination in that grid and turns
each populated cell into one `(date, activity, owner, label)` entry, then
sorts all of a client's entries chronologically before writing them out.
This layout was checked against all 205 client workbooks before writing
this script and found to be identical in every one, so no per-client
special-casing is needed — a couple of files are simply missing a Cover
or Timeline tab entirely (or a couple of the Cover fields), and those are
noted in the output rather than causing an error.

## Why the source folder path isn't hardcoded

Stewardships - Documents lives in a completely different SharePoint
library than this project (this project is under "Automation Database",
Stewardships is its own site) — so, unlike this project's own
Master-data/Employee-data folders, it can't be found just by climbing up
from this script's own location.

Instead, `find_onedrive_synced_folder()` at the top of the script looks
for it under whoever's Windows home directory is running the script:

1. First it checks the known layout directly:
   `<home>/GILROY KERNAN & GILROY/Stewardships - Documents`.
2. If that's not there, it looks at every folder directly under the home
   directory whose name contains "gilroy" (case-insensitive) — to catch
   OneDrive naming the synced root something slightly different, like
   "OneDrive - Gilroy Kernan & Gilroy" — and searches up to 3 folders
   deep inside each for something named exactly "Stewardships -
   Documents".
3. If it still can't find it, the script stops with a clear message
   rather than guessing, telling you to check that OneDrive is signed in
   and syncing, or to set the `STEWARDSHIP_SOURCE_DIR` environment
   variable yourself as an override.

No Windows username or computer name is hardcoded anywhere — this is
exactly what lets the script keep working unchanged after being copied
to a different computer or account, which matters since this is expected
to move off an intern's laptop to its permanent home at some point.

## Portability of this project's own folders

Master-data, Employee-data, and this `scripts` folder are all part of
the same project, so their paths use the simple, standard
`Path(__file__).resolve().parent.parent` pattern (same as the other
scripts in this folder) — they just walk up from wherever this file is
sitting. That only works because they're all inside the same
OneDrive-synced project folder; it's why Stewardships - Documents (a
separate library entirely) needed the OneDrive search described above
instead.

## Troubleshooting

**"Couldn't find the Stewardships - Documents folder..."** — OneDrive
likely isn't signed in, or isn't syncing the Stewardships site, on this
computer yet. Open OneDrive, confirm that site is syncing, and re-run.
As a one-off workaround, set the `STEWARDSHIP_SOURCE_DIR` environment
variable to the exact path.

**A client is missing attendees/meeting date/timeline in the output** —
that field was blank in the source workbook's Cover or Timeline tab; the
script records "not recorded" or a note rather than guessing or failing.

**Not showing up in Copilot's answers** — this script only writes the
`.md` file; make sure the Copilot agent's knowledge source actually
includes Master-data (or specifically this file), and that it's been
refreshed/re-indexed since this file was last generated.

## Wiring into the daily pipeline

This script is standalone today — it's not called from
`run_daily_pipeline.py`. If you want it to run automatically alongside
the Ninety/Monday pulls, it can be added there the same way
`2-build_knowledge_file.py` and `3-build_employee_knowledge_file.py`
are; ask for that once you're happy with the output.
