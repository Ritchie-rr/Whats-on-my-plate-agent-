# What's On My Plate — Setup Guide

This project turns Ninety (EOS) rocks, milestones, and issues, plus
stewardship client data (meeting attendees and strategic timelines), into
daily knowledge files that Microsoft Copilot agent(s) use to give GKG
employees a morning briefing of what's on their plate. Monday.com tasks
are no longer part of this daily pipeline — Monday data is now read live
through an MCP connector instead, so it's always current without a batch
pull. The `scripts/monday/` files still exist for manual/ad-hoc use (see
"Monday.com (manual use only)" below) but `run_daily_pipeline.py` doesn't
call them.

How it works, end to end:

Ninety API + Stewardships - Documents → Python scripts → knowledge files,
written straight into SharePoint-synced folders → Copilot agent(s) (agent
builder) → "What's on my plate?" briefings in Copilot Chat. (Monday.com
data reaches the same agent(s) separately, live, via MCP.)

---

## 1. Folder layout

Three folders sit side by side, all inside the same SharePoint-synced
library ("Automation Database" → "What's on my plate agent"):

```
What's on my plate agent/                        <- SharePoint-synced root
├── Code/                                          run the pipeline from here
│   ├── run_daily_pipeline.py                      <- run this one, nothing else
│   ├── keys/
│   │   ├── ninety_key                             Ninety API token
│   │   ├── monday_key                             Monday.com API token (manual use only, see below)
│   │   └── pipeline.log                           every run logs here
│   ├── SETUP_README.md
│   ├── scripts/                                   all the worker .py files
│   │   ├── 1-Ninety-dashboard.py
│   │   ├── build_employee_dashboard.py
│   │   ├── 2-build_knowledge_file.py
│   │   ├── 3-build_employee_knowledge_file.py
│   │   ├── 4-build_stewardship_knowledge_file.py
│   │   ├── find-ninety-user-id.py
│   │   ├── build-ninety-team-lookup.py
│   │   └── monday/                                Monday.com scripts -- NOT run by run_daily_pipeline.py anymore
│   │       ├── pull-monday-tasks.py                manual use only (see "Monday.com (manual use only)" below)
│   │       ├── build-employee-monday-tasks.py      manual use only
│   │       └── explore-monday-boards.py           exploratory only, not part of any run
│   └── data/
│       └── ID_Decoder.xlsx                        shared ID lookup only
├── Master-data/                                    Master (includes Leadership)
│   ├── Master_Ninety_Dashboard.xlsx
│   ├── Whats_On_My_Plate_Knowledge.md              <- point the master agent here
│   └── Whats_On_My_Plate_Stewardship_Knowledge.md  <- stewardship data for the same agent
└── Employee-data/                                  Employee (Leadership excluded)
    ├── Employee_Dashboard.xlsx
    ├── Whats_On_My_Plate_Employee_Knowledge.md      <- point a second agent here
    └── Whats_On_My_Plate_Stewardship_Knowledge.md  <- identical copy (no Leadership split for this data)
```

`Monday_Tasks.xlsx` may still exist in `Master-data`/`Employee-data` from an
old or manual run, but `run_daily_pipeline.py` no longer creates or
refreshes it — Monday.com data now reaches the agent(s) live via MCP
instead.

Because `Master-data/` and `Employee-data/` are themselves folders inside
the SharePoint-synced library, the scripts writing into them **is** the
publish step — there's no separate copy-to-SharePoint action anymore, and
no `SHAREPOINT_FOLDER` setting to keep in sync with reality.

Every script resolves its own paths from its own file location (via
`Path(__file__).resolve()...`), not from whatever folder you happen to run
it from, so moving `Code/` (or the whole project) elsewhere still works, as
long as `Master-data/` and `Employee-data/` stay as its siblings.

| File | What it does |
|---|---|
| `Code/keys/ninety_key` | Text file containing only the Ninety API token (no extension, no quotes). |
| `Code/keys/monday_key` | Text file containing only the Monday.com personal API token. Only needed if you manually run `pull-monday-tasks.py`/`build-employee-monday-tasks.py` — `run_daily_pipeline.py` doesn't use it. Monday's tokens are long JWT-style strings (three dot-separated segments) — very different from Ninety's `pat_...` tokens, so don't mix them up. |
| `Code/scripts/1-Ninety-dashboard.py` | Pulls rocks + milestones + issues from the Ninety API and writes `Master-data/Master_Ninety_Dashboard.xlsx` — the full data set, including Leadership. |
| `Code/data/ID_Decoder.xlsx` | Shared lookup workbook, one tab per ID type: **Users** (owner ID → name, written by `find-ninety-user-id.py`) and **Departments** / **Unresolved** (team ID → department name, written by `build-ninety-team-lookup.py`). Rebuild either occasionally, as people or teams change — not part of the daily run. |
| `Code/scripts/build_employee_dashboard.py` | Reads `Master-data/Master_Ninety_Dashboard.xlsx` and writes `Employee-data/Employee_Dashboard.xlsx` — same shape, minus any rock/milestone/issue whose department matches "Leadership" (can be confidential). |
| `Code/scripts/2-build_knowledge_file.py` | Reads `Master-data/Master_Ninety_Dashboard.xlsx` and writes `Master-data/Whats_On_My_Plate_Knowledge.md`, one section per person. Also reads both sheets of `Master-data/Monday_Tasks.xlsx` *if present* (from a manual Monday pull) and adds a Monday status-summary section, but nothing in the daily pipeline creates that file anymore, so most runs won't have Monday content here. This feeds the current live Copilot agent. |
| `Code/scripts/3-build_employee_knowledge_file.py` | Same as above but reads the `Employee-data` versions and writes `Employee-data/Whats_On_My_Plate_Employee_Knowledge.md` — Leadership content excluded from both Ninety and (if present) Monday sources, including from the status-summary section. |
| `Code/scripts/4-build_stewardship_knowledge_file.py` | Reads the Cover and Timeline tabs out of every client workbook in `Stewardships - Documents` and writes `Whats_On_My_Plate_Stewardship_Knowledge.md` into **both** `Master-data` and `Employee-data` (identical content in both, since stewardship/client data has no Leadership-vs-everyone split). See its own README-SIMPLE.md/README-DETAILED.md in `scripts/` for full detail. |
| `Code/scripts/monday/pull-monday-tasks.py` | **Not run by `run_daily_pipeline.py`.** Manual/ad-hoc use only — pulls items from the approved Monday.com boards (see board scope below) and writes `Master-data/Monday_Tasks.xlsx` with two sheets: **Tasks** (one row per person per item; RACI-style boards produce a separate row per Responsible/Accountable/Consulted person) and **Item_Columns** (every column value on every item, one row per item+column pair, free text included — see "Views/tabs vs. boards" below). Confidentiality (`category` column, present on both sheets, on every row regardless of column type) is detected automatically from each board's Monday `board_kind`/`permissions` settings, with a manual `FORCE_LEADERSHIP` override as a safety net. The `category` tag — not the column type — is the actual privacy boundary: see "Privacy model" below. |
| `Code/scripts/monday/build-employee-monday-tasks.py` | **Not run by `run_daily_pipeline.py`.** Manual/ad-hoc use only — reads both sheets of `Master-data/Monday_Tasks.xlsx` and writes both sheets to `Employee-data/Monday_Tasks.xlsx`, dropping rows tagged `category == "leadership"` (currently ROCKS \| 2025 and 2026 STEWARDSHIP TRACKER) from each. |
| `Code/run_daily_pipeline.py` | The only script you run. Builds `Code/data/ID_Decoder.xlsx` automatically on a fresh checkout if it's missing, then runs everything else in order (Ninety pull → employee Ninety dashboard → master knowledge doc → employee knowledge doc → stewardship knowledge doc). Monday.com is not part of this run — see intro above. |
| `Code/keys/pipeline.log` | Created automatically; every run logs here. Check it when something breaks. |

### Monday.com (manual use only)

Everything in this subsection describes `scripts/monday/pull-monday-tasks.py`
and `build-employee-monday-tasks.py`, which are **not** called by
`run_daily_pipeline.py`. Monday.com data is now read live via an MCP
connector instead of a daily batch pull. These scripts are kept for
occasional manual use (e.g. producing a one-off `Monday_Tasks.xlsx`
snapshot) — run them by hand if you ever need that.

Board scope is decided in two separate steps inside `pull-monday-tasks.py`,
on purpose:

**1. Relevance (manual, human-curated) — `ALLOWED_BOARD_NAMES`.** Monday's
API can't filter boards by name server-side, and it has no "this is real
work vs. demo data" signal, so this is still a hand-maintained list at the
top of the script:

`ROCKS | 2025`, `2026 STEWARDSHIP TRACKER`, `Onboarding`, `Onboarding(Master Sheet)`,
`Facilities`, `Larry Outreach/Testimonials`, `Projects`, `Renewals`,
`RACI Chart`, `Larry's Notes Carrier Party 2025`, `Fall 2025`, `Project Plan`

Excluded on purpose: the "Dept: Interns" workspace, the old
`[OLD - For Reference] ROCKS | Q4 2024` board, and Monday's own demo/template
boards (Accounts, Leads, My To-Do List & Calendar Sync, Client Projects, New
Workflow). If a board gets renamed, the pull script prints a `MISSING`
warning for it — update the name in `ALLOWED_BOARD_NAMES` when that happens.
Two different boards are both named "Larry's Notes Carrier Party 2025";
since they can't be told apart by name, both are currently included (the
pull script prints exactly which board IDs matched each name, so this can
be narrowed down later if one of them turns out to be the wrong one).

**2. Confidentiality (automatic) — `classify()`.** For every board that's in
scope, the script also pulls that board's own `board_kind` (`private` /
`public` / `share`) and `permissions` (`assignee` / `collaborators` /
`everyone` / `owners`) fields from Monday and tags every row from it
`category="leadership"` if `board_kind == "private"` or
`permissions == "owners"`. That's what `build-employee-monday-tasks.py`
filters on to keep Leadership-only content out of `Employee-data`. This
means a brand-new confidential board — like the 2026 STEWARDSHIP TRACKER
section added this month — gets classified correctly automatically, as long as it's
actually set to private or owners-only in Monday and someone adds its name
to `ALLOWED_BOARD_NAMES`. Nobody has to touch the classification logic
itself for each new confidential board.

`FORCE_LEADERSHIP` (currently `ROCKS | 2025` and `2026 STEWARDSHIP TRACKER`) is a manual
override on top of that automatic check — a safety net for boards that must
always be treated as confidential even if someone loosens the board's
sharing settings in Monday later without realizing the implication for this
pipeline. The diagnostic output when the script runs prints each matched
board's `board_kind`, `permissions`, and resulting category, so a
misclassification is visible immediately rather than silently leaking into
`Employee-data`.

### Privacy model: `category` is the boundary, not column type

`pull-monday-tasks.py`'s `Item_Columns` sheet captures every column value
on every item, including free-text/notes columns — on purpose, so it stays
useful without needing a hand-picked allowlist of "safe" column types. The
actual privacy control is the `category` field: every row from a given
board, on both the `Tasks` and `Item_Columns` sheets, gets the exact same
`category` ("leadership" or "regular") stamped on it — including free-text
values. `build-employee-monday-tasks.py` filters both sheets on that one
field. So a leadership board's notes are excluded from `Employee-data` just
as completely as its statuses or its assignees — column type never affects
what's private, only which board a value came from and that board's own
Monday sharing settings. Anyone extending `pull-monday-tasks.py` with a new
field must carry `"category": category` on it, the same as every existing
row, or that guarantee breaks.

### Monday.com "views"/tabs vs. boards — and the auto status summary

A Monday board (like `2026 STEWARDSHIP TRACKER`) usually has several tabs
down the left side inside it — Main table, a Calendar View, a "Leader
Board" or "Schedule View - ALL" dashboard, filtered views like Red Flags,
CERs, Need to Schedule, Alternative Plans. These are **not** separate data
sources. They're all different filters/layouts over the exact same items
and columns that live on that one board, and Monday's API has no way to
query "a view" directly — there's nothing to pull that isn't already
covered by pulling the board's items and columns.

Because of that, `pull-monday-tasks.py` dumps every column value on every
item into the **Item_Columns** sheet, regardless of column type or name.
`2-build_knowledge_file.py` and `3-build_employee_knowledge_file.py` then
read that sheet and auto-generate a "Monday.com board status summaries"
section — one line per status/dropdown/checkbox-type column on each board,
showing how many items sit at each value (e.g. `Meeting Status: Complete
(63), Scheduled (18), Not Scheduled (36), ...`). This is the same
information as Monday's own leader-board/dashboard views, just written as
text. Nothing here is hardcoded to a specific column or board name, so:

- A new status/dropdown column added to an already-approved board (and
  therefore whatever new tab/dashboard/view someone builds on top of it in
  Monday) shows up in this summary automatically on the next pipeline run.
  No code change needed.
- The one thing that still needs a manual code change is a genuinely new
  **board** — see "Relevance" above. Monday has no signal for "this is a
  real board someone should see," so a brand-new board (as opposed to a
  new tab on an existing approved board) still has to be added to
  `ALLOWED_BOARD_NAMES` by hand.

If you're ever unsure whether something you see in Monday is "a new board"
or "a new tab on an existing board," check the URL: `monday.com/boards/
<id>/views/<view id>` — the `<id>` right after `/boards/` is the board ID.
If that number matches a board already in `ALLOWED_BOARD_NAMES`, it's just
a new view and nothing needs to change in code.

## 2. One-time setup

1. **Python packages** (once per machine):
   ```
   pip install requests pandas openpyxl
   ```

2. **Ninety API token**: generate it in Ninety's settings, paste it into a
   file named exactly `ninety_key` inside `Code/keys/` (not inside
   `scripts/` or `data/`). If the token expires or is regenerated, replace
   this file — nothing else changes.

3. **Monday.com API token** *(optional — only needed for manual Monday
   runs, not for `run_daily_pipeline.py`)*: in Monday, click your profile
   picture → **Developers** → **API token** → **Show** (or
   **Administration** → **Connections** → **Personal API token** if
   you're an admin). Paste it into a file named exactly `monday_key`
   inside `Code/keys/`. It should look like a long string with two
   periods in it (a JWT) — if it starts with `pat_`, that's actually a
   Ninety token and won't authenticate against Monday.

4. **Confirm the three folders are synced**: `Code/`, `Master-data/`, and
   `Employee-data/` should all already be inside the "What's on my plate
   agent" SharePoint library and syncing via OneDrive. Nothing to configure
   in the scripts for this — they find `Master-data/` and `Employee-data/`
   automatically as siblings of `Code/`.

5. **Test run**:
   ```
   python run_daily_pipeline.py
   ```
   Run this from inside `Code/`. This is genuinely the only command you
   need. On a brand-new checkout with no `Code/data/ID_Decoder.xlsx` yet,
   it builds that first automatically (runs `find-ninety-user-id.py` and
   `build-ninety-team-lookup.py` for you), then does the daily pulls. The
   pre-flight check tells you immediately if a filename is wrong or a
   folder is missing, and lists every `.py` file it actually found.
   Success looks like several DONE lines, then three "... knowledge file is
   current" lines, then "Pipeline complete." Confirm all three `.md` files
   show up (or refresh their Modified date) in `Master-data/` and
   `Employee-data/` in SharePoint online.

## 3. Schedule it weekly (Task Scheduler)

1. Find your Python path: run `where python` in PowerShell and copy the
   full path (e.g. `C:\Users\<you>\AppData\Local\...\python.exe`).
2. Open **Task Scheduler** → **Create Basic Task**.
3. Name: `What's On My Plate - Weekly Pipeline`. Trigger: Weekly, Monday,
   6:30 AM.
4. Action: **Start a program**:
   - Program/script: the full python.exe path from step 1.
   - Add arguments: `run_daily_pipeline.py`
   - **Start in**: the full path of the `Code` folder (the one containing
     `run_daily_pipeline.py`, `keys/`, `scripts/`, and `data/`). Required —
     without it the script can't find the key files.
5. After creating, open the task's **Properties** and check
   *"Run task as soon as possible after a scheduled start is missed."*
6. Right-click the task → **Run** to test it once. Then check
   `keys/pipeline.log` and the three knowledge files' Modified times in
   SharePoint.

Limitations of this setup: the PC must be on and you must be logged in at
run time. If the pipeline doesn't run, the agent serves stale data (it
tells users the "Data as of" date, so staleness is visible). The long-term
fix is running this from a server or GitHub Actions with a Microsoft Graph
upload — talk to IT about an app registration when the pilot proves value.

## 4. Set up the Copilot agent(s)

**Master agent** (everyone, including Leadership):
1. In Microsoft Copilot Chat, choose **Create agent** (agent builder).
2. Name it **What's On My Plate**.
3. **Knowledge**: add the `Master-data` SharePoint folder (the one
   containing `Whats_On_My_Plate_Knowledge.md`).
4. **Instructions**: paste the instructions block (kept in a separate
   file/chat; ~6,500 characters, fits the 8,000 limit).
5. Save and test with these five prompts:
   - "What's on my plate?" (as yourself)
   - "What is Beth Whalen working on?"
   - "What's overdue across the company?"
   - "Who's working on the outmarket rollout?"
   - A name that isn't in the file (should say no items, not guess).
6. Share the agent with the pilot team. Everyone using it needs read
   access to the `Master-data` folder.

**Employee agent** (Leadership excluded) — not set up yet:
1. Same steps as above, but point **Knowledge** at the `Employee-data`
   folder instead, using `Whats_On_My_Plate_Employee_Knowledge.md`.
2. This only actually restricts Leadership's information if
   `Employee-data`'s SharePoint permissions are narrower than
   `Master-data`'s (or narrower than whatever broader group you're
   rolling this out to). Set those permissions before sharing the agent
   widely — see Known Limitations below.

## 5. Weekly operation & troubleshooting

- Normal days: nothing to do. The task runs every Monday, both files refresh,
  and each agent answers with the latest "Data as of" date.

### Fixing a missing or expired API key

How you'll notice: either the pre-flight check fails immediately with
`'keys/ninety_key' not found` (the file is missing entirely — e.g. a
fresh checkout on a new computer that hasn't had keys added yet), or the
pipeline gets further and the Ninety pull fails with a 401 / "Not
authenticated" error (the file exists but the token inside it is wrong or
has expired). Both are fixed the same way: get a fresh token and put it
in the right file. (`monday_key` isn't checked by `run_daily_pipeline.py`
at all anymore — the Monday token section below only matters if you're
running `pull-monday-tasks.py` by hand.)

**Ninety token:**
1. Log into Ninety, go to your settings, and generate/regenerate the API
   token (same place as the original "Ninety API token" step in
   [One-time setup](#2-one-time-setup) above).
2. Copy the token.
3. Open (or create) `Code/keys/ninety_key` in a plain text editor
   (Notepad, not Word — Word can silently add formatting that breaks a
   plain-text token file).
4. Select everything currently in the file and delete it, paste the new
   token in its place, and save. The file should contain nothing but the
   token itself — no quotes, no extra blank lines, no leading/trailing
   spaces.
5. If the file or the `keys/` folder doesn't exist yet at all, just
   create it: a new plain text file, named exactly `ninety_key` (no
   `.txt` extension), inside a `keys` folder directly under `Code/`.

**Monday token** *(only if you're manually running
`scripts/monday/pull-monday-tasks.py` — not used by
`run_daily_pipeline.py`)*:
1. In Monday, click your profile picture → **Developers** → **API
   token** → **Show** (or **Administration** → **Connections** →
   **Personal API token** if you're an admin) and copy it. It's a long
   string with two periods in it (a JWT) — if what you copied starts
   with `pat_`, that's a Ninety token, not a Monday one.
2. Open (or create) `Code/keys/monday_key` the same way as above, replace
   its entire contents with the new token, and save.

**After replacing either file:**
```
python run_daily_pipeline.py
```
Run this from inside `Code/` and watch the output (or check
`keys/pipeline.log` right after) — a successful run prints "Pre-flight
OK," then a DONE line for each step, then "Pipeline complete." If it
fails again with the same error, double-check you saved the file as
plain text with no extra characters, and that you copied the whole token
(these can be long, and easy to accidentally clip when copying).

- **Agent quotes an old date** → the pipeline didn't run or SharePoint
  hasn't re-indexed yet. Check `keys/pipeline.log` first; if the log shows
  success, give indexing a few hours.
- **Pre-flight failure in the log** → a filename is wrong, or
  `Master-data`/`Employee-data` isn't a sibling of `Code/` anymore
  (folder got renamed or moved).
- **Ninety pull fails with 401, or a key file is missing** → see "Fixing a
  missing or expired API key" just above.
- **Stewardship knowledge doc step fails / "Couldn't find the
  Stewardships - Documents folder..."** → OneDrive isn't signed in or
  isn't syncing the Stewardships site on this computer. See
  `scripts/README-DETAILED.md`'s troubleshooting section for the full
  fix.
- *(The items below only apply if you're manually running
  `scripts/monday/pull-monday-tasks.py` — Monday.com isn't part of
  `run_daily_pipeline.py` anymore.)*
- **Monday pull fails with "Not authenticated", or a key file is missing**
  → see "Fixing a missing or expired API key" just above.
- **Monday pull prints a `MISSING` warning for a board name** → that board
  was renamed, archived, or deleted in Monday. Update the name in
  `ALLOWED_BOARD_NAMES` inside `pull-monday-tasks.py`.
- **A board's `category` looks wrong in the diagnostic output** → check
  what the printed `board_kind`/`permissions` actually are for that board
  in Monday; the pipeline trusts those fields unless the board name is
  also listed in `FORCE_LEADERSHIP`. If a board's sharing settings changed
  in Monday, the pipeline's classification changes with it automatically —
  add the name to `FORCE_LEADERSHIP` if it should never follow Monday's
  live settings.
- **Monday pull prints a `MISMATCH` warning for a board** → it pulled
  fewer items than the board reports having; check that board manually in
  Monday, since this usually means pagination stopped early.
- **New employee missing** → they appear automatically once they own a
  rock, milestone, or issue in Ninety and the pipeline runs again. If a
  person shows as a bare ID with no name, rebuild the **Users** tab in
  `Code/data/ID_Decoder.xlsx` with `scripts/find-ninety-user-id.py`.
- **Rock/milestone/issue missing a department** → rebuild the
  **Departments** tab in `Code/data/ID_Decoder.xlsx` with
  `scripts/build-ninety-team-lookup.py`; check its **Unresolved** tab for
  team IDs it saw but couldn't name yet.
- **Someone's Monday tasks aren't showing up in their section** → only
  relevant if `Master-data/Monday_Tasks.xlsx` exists from a manual
  `pull-monday-tasks.py` run; Monday people are matched to Ninety names by
  exact string match in that path (no shared "People" tab yet — see Open
  Items). If their name is spelled or formatted differently between the
  two systems (e.g. a middle initial), they'll get a separate, Monday-only
  section under that name instead of one combined section. This doesn't
  apply to Monday data surfaced live via MCP.
- **Moving `Master-data` or `Employee-data` to a new SharePoint home** →
  move the actual folder (don't just rename it) so it stays a sibling of
  `Code/`; update the matching agent's knowledge source; re-run the five
  test prompts.

## 6. Known limitations (current version)

- `run_daily_pipeline.py` covers rocks, milestones, and issues from
  Ninety, plus stewardship client data (meeting attendees, timelines)
  from `Stewardships - Documents` — not scorecard measurables. Monday.com
  data is intentionally not part of this daily run anymore; it's read
  live via MCP instead. The manual `scripts/monday/` path (if used) is
  still limited to a fixed, manually-approved list of Monday.com boards
  — not any board that isn't already in `ALLOWED_BOARD_NAMES`.
- Data freshness for the Ninety/stewardship knowledge files = last
  successful pipeline run (each agent states the "Data as of" date in
  answers). Monday data via MCP is live, so it doesn't have this
  staleness concern.
- The Ninety public API has no general users endpoint, so people are
  discovered by the items they own; `ID_Decoder.xlsx`'s Users tab covers
  the rest.
- Read-only: no agent can create or update anything in Ninety, Monday, or
  the stewardship workbooks.
- *(Only relevant if using the manual Monday xlsx path, not the MCP
  connector)* Monday people are matched to Ninety owner names by **exact
  string match** — there's no cross-system "People" tab yet. A name
  that's spelled differently between the two systems won't be merged
  into one person's section (see Open Items).
- `Master-data` and `Employee-data` are separate folders, which is what
  makes real Leadership-vs-everyone-else confidentiality possible — but
  it isn't automatic. Confidentiality only exists once `Employee-data`'s
  SharePoint permissions are actually set narrower than `Master-data`'s.
  Right now both may still have the same access if permissions haven't
  been set on the new folders yet — check this in SharePoint before
  relying on it.
- The next two bullets describe the manual `scripts/monday/` path only;
  they don't apply to Monday data read live via MCP.
- Board *relevance* for Monday is a hardcoded name list
  (`ALLOWED_BOARD_NAMES`), so a brand-new board an account manager starts
  using won't show up automatically — it has to be added to that list on
  purpose. Board *confidentiality*, once a board is on that list, is
  detected automatically from Monday's `board_kind`/`permissions` fields,
  so a new confidential board doesn't need new classification code — just
  needs to actually be set to private/owners-only in Monday.
- New tabs/views/dashboards inside an already-approved board (Calendar
  views, "Leader Board"-style dashboards, filtered views) never need a
  code change — they're not separate data, and the status-summary section
  in both knowledge files picks up any new status/dropdown column
  automatically (see "Monday.com views/tabs vs. boards" above).
- The status summary only covers status/dropdown/checkbox-type columns.
  Free-text, numeric, and date-only columns aren't rolled up into counts
  (a date-based summary — e.g. "N items overdue" — is a possible future
  addition, not built yet).

## 7. Open items

- Set distinct SharePoint permissions on `Master-data` vs `Employee-data`
  so the split folders actually restrict who can read Leadership's rocks,
  milestones, issues, and Monday tasks.
- Set up the second Copilot agent pointed at `Employee-data`.
- Decide whether per-department or per-person folders/READMEs are needed
  beyond the Leadership/Employee split.
- Build a `People` tab in `ID_Decoder.xlsx` (one row per human, one column
  per source's ID/name) so Monday and Ninety identities merge into one
  section reliably instead of relying on exact name-string matches.
- Confirm the two boards both named "Larry's Notes Carrier Party 2025"
  are both actually wanted; drop the wrong one from `ALLOWED_BOARD_NAMES`
  if not.
- Decide whether Monday's Consulted role (RACI Chart) should be visually
  de-emphasized in the knowledge file relative to Responsible/Accountable,
  now that it's confirmed all three should be included.
