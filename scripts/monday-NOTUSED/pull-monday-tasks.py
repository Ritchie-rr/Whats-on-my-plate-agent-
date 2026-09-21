"""
Pull the approved Monday.com boards into Master-data/Monday_Tasks.xlsx.

Board scope is decided in two separate steps, on purpose:

1. RELEVANCE (still a human judgment call -- Monday's API has no "this is
   real work vs. demo data" signal): ALLOWED_BOARD_NAMES below is the
   full list of boards this pull even looks at. Anything not in this set
   is ignored, including Monday's own demo/template boards (Accounts,
   Leads, My To-Do List & Calendar Sync, Client Projects, New Workflow),
   the "Dept: Interns" workspace, and old/archived boards like
   "[OLD - For Reference] ROCKS | Q4 2024".

2. CONFIDENTIALITY (automatic): for every board that IS in scope, this
   script asks Monday whether the board itself is restricted --
   board_kind == "private" or permissions == "owners" -- and if so,
   tags every row from it category="leadership" (Master-data only,
   excluded from Employee-data by build-employee-monday-tasks.py). This
   means a brand-new confidential board (like 2026 STEWARDSHIP TRACKER) doesn't need
   a code change here as long as it's actually set to private/owners-only
   in Monday -- it gets classified correctly the moment it's added to
   ALLOWED_BOARD_NAMES.

   FORCE_LEADERSHIP is a manual override on top of that automatic check,
   for boards that must always be treated as confidential regardless of
   whatever Monday currently reports (defense in depth, in case someone
   changes a board's sharing settings later without realizing the
   implication for this pipeline).

Matches boards by NAME (Monday's API can't filter boards by name
server-side). A couple of names in this account are not unique -- e.g.
two different boards are both named "Larry's Notes Carrier Party 2025".
Since we can't tell those apart by name alone, every board matching an
approved name is included, and this script prints exactly which board
IDs it matched (plus each one's board_kind/permissions/resulting
category) so that can be sanity-checked.

People-type columns are kept under their own column title as the "role"
(e.g. "Person", "Assigned To", "Owner", or on RACI Chart: "Responsible",
"Accountable", "Consulted") rather than being flattened into one generic
"assignee" -- this preserves the Responsible/Accountable vs. Consulted
distinction requested for RACI Chart, and generalizes to any future board
with a differently-named people column.

Besides the per-person "Tasks" sheet, this script also writes an
"Item_Columns" sheet: every column value on every item, one row per
(item, column) pair, regardless of column type or name -- including
free-text/notes columns. Monday's own dashboard-style views (a "Leader
Board", "Schedule View - ALL", a Calendar view, filtered views like "Red
Flags" or "CERs") are NOT separate data -- they're just different
filters/layouts over the same board's columns, and Monday's API has no
way to query "a view" directly, so this full dump is what makes a
brand-new column (and whatever new view it backs) show up automatically,
without knowing its name ahead of time.

THE PRIVACY BOUNDARY IS THE "category" COLUMN, NOT COLUMN TYPE. Every row
written here -- on the Tasks sheet AND the Item_Columns sheet, whatever
the column's type -- carries the same category ("leadership" or
"regular") as every other row from that board, computed once by
classify() below. build-employee-monday-tasks.py filters BOTH sheets on
that exact same category field. So a leadership board's free-text notes
get excluded from Employee-data exactly as completely as its status
values or its assignees do -- the column type never affects what's
private, only which board the value came from and that board's own
Monday sharing settings (see CONFIDENTIALITY above). Nothing here should
ever bypass that tagging: if a new field is added anywhere in this
script, it must carry `"category": category` like every other row.

A brand-new status/dropdown/checkbox column added to an already-approved
board (and therefore whatever new view someone builds on top of it in
Monday) shows up in the knowledge files' auto-generated status summary
the next time this runs -- no code change needed for that (the summary
builder only groups by status/dropdown/checkbox columns; free-text
columns are stored but not summarized). The one thing that still requires
a code change is a genuinely new BOARD (see ALLOWED_BOARD_NAMES above),
since Monday has no signal for "this is a real board someone should see."

Run manually:
    python pull-monday-tasks.py
"""

import requests
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent  # monday/ -> scripts/ -> Code/
KEY_FILE = ROOT / "keys" / "monday_key"
MASTER_DIR = ROOT.parent / "Master-data"

API_URL = "https://api.monday.com/v2"
API_VERSION = "2026-07"  # pinned so a future schema change doesn't silently break this

api_token = KEY_FILE.read_text().strip()

headers = {
    "Authorization": api_token,
    "Content-Type": "application/json",
    "API-Version": API_VERSION,
}

ALLOWED_BOARD_NAMES = {
    "ROCKS | 2025",
    "2026 STEWARDSHIP TRACKER",
    "Onboarding",
    "Onboarding(Master Sheet)",
    "Facilities",
    "Larry Outreach/Testimonials",
    "Projects",
    "Renewals",
    "RACI Chart",
    "Larry's Notes Carrier Party 2025",
    "Fall 2025",
    "Project Plan",
}

# Always confidential, no matter what Monday currently reports for the board.
FORCE_LEADERSHIP = {
    "ROCKS | 2025",
    "2026 STEWARDSHIP TRACKER",
}


def classify(board_name, board_kind, permissions):
    if board_name in FORCE_LEADERSHIP:
        return "leadership"
    if board_kind == "private" or permissions == "owners":
        return "leadership"
    return "regular"


def run_query(query, variables=None):
    body = {"query": query}
    if variables:
        body["variables"] = variables
    resp = requests.post(API_URL, headers=headers, json=body)
    data = resp.json()
    if "errors" in data:
        print(f"  GraphQL errors: {data['errors']}")
    return data.get("data", {})


# =========================
# 1. Find every board matching an approved name (paginated), and pull
#    board_kind + permissions so confidentiality can be auto-detected
# =========================

all_boards = []
page = 1
while True:
    data = run_query("""
    query ($page: Int!) {
      boards (limit: 100, page: $page) {
        id
        name
        state
        items_count
        board_kind
        permissions
      }
    }
    """, variables={"page": page})
    batch = data.get("boards", [])
    if not batch:
        break
    all_boards.extend(batch)
    page += 1

if not all_boards:
    print(
        "\nABORTING: the boards() query returned nothing at all -- this means "
        "the API call itself failed (bad token, GraphQL error, network issue), "
        "not that no boards matched. Check the 'GraphQL errors' line above. "
        "Not touching Monday_Tasks.xlsx so the last good pull isn't overwritten."
    )
    raise SystemExit(1)

matched_boards = [
    b for b in all_boards
    if b["name"] in ALLOWED_BOARD_NAMES and b["state"] == "active"
]

print(f"Scanned {len(all_boards)} total boards. Matched {len(matched_boards)} against the approved list:\n")

seen_names = {}
for b in matched_boards:
    seen_names.setdefault(b["name"], []).append(b)

for name in ALLOWED_BOARD_NAMES:
    matches = seen_names.get(name, [])
    if not matches:
        print(f"  MISSING -- no active board found named '{name}' (renamed? archived?)")
        continue
    for b in matches:
        category = classify(name, b["board_kind"], b["permissions"])
        forced = " (forced)" if name in FORCE_LEADERSHIP else ""
        dup = f"  [duplicate name, {len(matches)} boards match]" if len(matches) > 1 else ""
        print(
            f"  '{name}' -> board {b['id']}  "
            f"board_kind={b['board_kind']}, permissions={b['permissions']}  "
            f"=> {category}{forced}{dup}"
        )

if not matched_boards:
    print(
        "\nABORTING: 0 of the approved board names matched anything in this "
        "account (every one printed MISSING above). That's almost certainly a "
        "problem with the query or token, not every board getting renamed at "
        "once. Not touching Monday_Tasks.xlsx so the last good pull isn't "
        "overwritten."
    )
    raise SystemExit(1)

# =========================
# 2. Pull every item on each matched board, following cursor pagination
#    all the way through (not just a sample), and verify the count
# =========================

rows = []
column_rows = []

for b in matched_boards:
    board_id = b["id"]
    board_name = b["name"]
    category = classify(board_name, b["board_kind"], b["permissions"])
    expected_count = b["items_count"]

    items_seen = 0
    cursor = None

    while True:
        if cursor is None:
            data = run_query("""
            query ($id: [ID!]) {
              boards (ids: $id) {
                items_page (limit: 100) {
                  cursor
                  items {
                    id
                    name
                    url
                    group { title }
                    column_values {
                      type
                      text
                      column { title }
                    }
                  }
                }
              }
            }
            """, variables={"id": [board_id]})
            page_data = (data.get("boards") or [{}])[0].get("items_page", {})
        else:
            data = run_query("""
            query ($cursor: String!) {
              next_items_page (cursor: $cursor, limit: 100) {
                cursor
                items {
                  id
                  name
                  url
                  group { title }
                  column_values {
                    type
                    text
                    column { title }
                  }
                }
              }
            }
            """, variables={"cursor": cursor})
            page_data = data.get("next_items_page", {})

        items = page_data.get("items", [])
        if not items:
            break

        for item in items:
            items_seen += 1

            status = None
            due_date = None
            people_cols = []
            item_group = item["group"]["title"] if item.get("group") else None

            for cv in item["column_values"]:
                # Full dump, every column regardless of type -- including
                # free text. The privacy control is the "category" tag
                # (leadership vs. regular), stamped identically on this row
                # no matter the column type, not the column type itself.
                # See the module docstring: build-employee-monday-tasks.py
                # filters on this same field to exclude leadership rows.
                # Blank values are kept too (as None) since "empty" is
                # itself a meaningful bucket in Monday's own dashboards.
                column_rows.append({
                    "board_name": board_name,
                    "category": category,
                    "group_name": item_group,
                    "item_id": item["id"],
                    "item_name": item["name"],
                    "column_title": cv["column"]["title"],
                    "column_type": cv["type"],
                    "column_text": cv["text"],
                })

                if cv["type"] == "status" and status is None and cv["text"]:
                    status = cv["text"]
                elif cv["type"] in ("date", "timeline") and due_date is None and cv["text"]:
                    due_date = cv["text"]
                elif cv["type"] == "people" and cv["text"]:
                    people_cols.append((cv["column"]["title"], cv["text"]))

            if people_cols:
                for role, person_name in people_cols:
                    rows.append({
                        "board_name": board_name,
                        "category": category,
                        "group_name": item_group,
                        "item_id": item["id"],
                        "item_name": item["name"],
                        "item_url": item["url"],
                        "role": role,
                        "person_name": person_name,
                        "status": status,
                        "due_date": due_date,
                    })
            else:
                # No assignee at all -- keep the item so nothing silently disappears
                rows.append({
                    "board_name": board_name,
                    "category": category,
                    "group_name": item_group,
                    "item_id": item["id"],
                    "item_name": item["name"],
                    "item_url": item["url"],
                    "role": None,
                    "person_name": None,
                    "status": status,
                    "due_date": due_date,
                })

        cursor = page_data.get("cursor")
        if not cursor:
            break

    flag = "" if items_seen == expected_count else f"  ** MISMATCH: expected {expected_count} **"
    print(f"  {board_name} (id {board_id}) [{category}]: pulled {items_seen} items{flag}")

# =========================
# 3. Save -- two sheets: "Tasks" (per-person, unchanged shape) and
#    "Item_Columns" (every column value on every item, one row per
#    item+column pair, free text included). Item_Columns is what the
#    knowledge-file builders read to auto-generate a status/leaderboard-
#    style summary per board (from just the status/dropdown/checkbox rows)
#    without hardcoding any column name. Every row here -- whatever the
#    column type -- carries the same "category" tag as the board it came
#    from, which is what build-employee-monday-tasks.py filters on to keep
#    leadership content, free text included, out of Employee-data.
# =========================

tasks_df = pd.DataFrame(rows)
columns_df = pd.DataFrame(column_rows)

MASTER_DIR.mkdir(parents=True, exist_ok=True)
output_path = MASTER_DIR / "Monday_Tasks.xlsx"
with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
    tasks_df.to_excel(writer, sheet_name="Tasks", index=False)
    columns_df.to_excel(writer, sheet_name="Item_Columns", index=False)

print(f"\nWrote {len(tasks_df)} task rows and {len(columns_df)} column-value rows to {output_path}")
if "category" in tasks_df.columns:
    print(f"Leadership rows: {len(tasks_df[tasks_df['category'] == 'leadership'])}")
    print(f"Regular rows: {len(tasks_df[tasks_df['category'] == 'regular'])}")
    print(f"Rows with no assignee: {len(tasks_df[tasks_df['person_name'].isna()])}")
    print("\nSample:")
    print(tasks_df.head(10))
