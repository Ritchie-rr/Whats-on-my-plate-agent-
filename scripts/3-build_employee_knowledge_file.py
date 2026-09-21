"""
Build the Leadership-free knowledge file for a broader-access Copilot agent.

Reads Employee_Dashboard.xlsx (Rocks, Milestones, Users sheets -- already
scrubbed of Leadership-department rows by build_employee_dashboard.py) AND
Monday_Tasks.xlsx (already scrubbed of the "leadership" category by
build-employee-monday-tasks.py) from the Employee-data folder, and writes
Whats_On_My_Plate_Employee_Knowledge.md to that same folder, one section
per person. Same format as the master knowledge file, so Copilot retrieval
matches the same natural questions ("what's on my plate" / "what is Amy
working on").

This is the file to point a wider-audience agent at -- one that shouldn't
see Leadership's rocks, milestones, issues, or Monday.com tasks (currently
the ROCKS | 2025 and 2026 STEWARDSHIP TRACKER boards). The master
knowledge file (Whats_On_My_Plate_Knowledge.md, in Master-data, built by
2-build_knowledge_file.py) still includes everyone, including Leadership,
so Leadership's own briefing isn't broken.

Also reads the "Item_Columns" sheet of Monday_Tasks.xlsx (already scrubbed
of leadership rows by build-employee-monday-tasks.py) and adds the same
auto-generated status-summary section as the master file, but only for
whatever non-confidential boards have status-style columns -- so this
still adapts automatically when a new column/tab is added to an
already-approved board, without leaking anything from a leadership board.

Run after build_employee_dashboard.py and build-employee-monday-tasks.py:
    python 3-build_employee_knowledge_file.py
"""

from datetime import datetime, timezone
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EMPLOYEE_DIR = ROOT.parent / "Employee-data"

SOURCE = EMPLOYEE_DIR / "Employee_Dashboard.xlsx"
MONDAY_SOURCE = EMPLOYEE_DIR / "Monday_Tasks.xlsx"
OUTPUT = EMPLOYEE_DIR / "Whats_On_My_Plate_Employee_Knowledge.md"

rocks = pd.read_excel(SOURCE, sheet_name="Rocks")
milestones = pd.read_excel(SOURCE, sheet_name="Milestones")

try:
    monday_tasks = pd.read_excel(MONDAY_SOURCE, sheet_name="Tasks")
except (FileNotFoundError, ValueError):
    print(
        f"WARNING: {MONDAY_SOURCE} not found (or missing its 'Tasks' sheet) -- "
        "run build-employee-monday-tasks.py first. Continuing without Monday.com tasks."
    )
    monday_tasks = pd.DataFrame(columns=[
        "board_name", "category", "group_name", "item_id", "item_name",
        "item_url", "role", "person_name", "status", "due_date"
    ])

try:
    monday_columns = pd.read_excel(MONDAY_SOURCE, sheet_name="Item_Columns")
except (FileNotFoundError, ValueError):
    monday_columns = pd.DataFrame(columns=[
        "board_name", "category", "group_name", "item_id", "item_name",
        "column_title", "column_type", "column_text"
    ])

now = datetime.now(timezone.utc)


def fdate(v):
    d = pd.to_datetime(v, errors="coerce", utc=True)
    return d.strftime("%B %d, %Y") if pd.notna(d) else "no due date"


def overdue_tag(v):
    d = pd.to_datetime(v, errors="coerce", utc=True)
    if pd.isna(d):
        return ""
    if d < now:
        return " (OVERDUE)"
    if (d - now).days <= 7:
        return " (due within 7 days)"
    return ""


def status_word(s):
    return {
        "ON_TRACK": "on track",
        "OFF_TRACK": "off track",
        "AT_RISK": "at risk",
        "DONE": "done",
        "COMPLETE": "complete",
    }.get(str(s), str(s).replace("_", " ").lower())


def build_status_summary(columns_df):
    """One section per Monday board that has at least one status/dropdown/
    checkbox column -- a breakdown of how many items sit at each value.
    Discovered entirely from the data (board names, column names, and
    values are never hardcoded), so a new status column -- or a brand-new
    dashboard/view built on top of it in Monday -- appears here the next
    time the pipeline runs without anyone touching this script. Only
    non-leadership boards ever reach this function in the employee file,
    since build-employee-monday-tasks.py already dropped leadership rows."""
    out = []
    if columns_df.empty:
        return out
    categorical = columns_df[columns_df["column_type"].isin(
        ["status", "dropdown", "checkbox"]
    )]
    if categorical.empty:
        return out

    out.append("## Monday.com board status summaries")
    out.append("")
    out.append(
        "Rollup counts for every status-style field on each non-Leadership "
        "Monday.com board in scope, refreshed on every pipeline run -- this "
        "is the same information as Monday's own dashboard views (leader "
        "boards, schedule/status charts), just in text form."
    )
    out.append("")

    for board_name in sorted(categorical["board_name"].dropna().unique()):
        board_cols = categorical[categorical["board_name"] == board_name]
        total_items = board_cols["item_id"].nunique()
        out.append(f"### {board_name}")
        out.append("")
        out.append(f"{total_items} items tracked on this board.")
        out.append("")
        for col_title in sorted(board_cols["column_title"].dropna().unique()):
            col_data = board_cols[board_cols["column_title"] == col_title]
            values = col_data["column_text"].fillna("(empty)")
            values = values.replace("", "(empty)")
            counts = values.value_counts()
            parts = ", ".join(f"{val} ({n})" for val, n in counts.items())
            out.append(f"- {col_title}: {parts}.")
        out.append("")

    return out


lines = [
    "# What's on everyone's plate — Ninety rocks/milestones and Monday.com tasks (Employee view)",
    "",
    f"Data as of {now.strftime('%A, %B %d, %Y at %H:%M UTC')}. "
    "This document lists every person's quarterly rocks and the "
    "milestones they own in Ninety (EOS), plus their tasks from Monday.com "
    "boards, excluding Leadership-only content from both sources. A rock "
    "is a quarterly priority. A milestone is a step toward completing a "
    "rock; a person can own milestones under someone else's rock, "
    "including department rocks. Monday.com tasks show which role the "
    "person has on that item (for example Responsible, Accountable, or "
    "Consulted on the RACI Chart board) and which board it's from.",
    "",
]

lines.extend(build_status_summary(monday_columns))

names = sorted(
    set(rocks["owner_name"].dropna())
    | set(milestones["owner_name"].dropna())
    | set(monday_tasks["person_name"].dropna())
)

for name in names:
    my_rocks = rocks[(rocks["owner_name"] == name) & (~rocks["completed"])]
    my_ms = milestones[
        (milestones["owner_name"] == name) & (~milestones["completed"])
    ]
    my_monday = monday_tasks[monday_tasks["person_name"] == name]
    if my_rocks.empty and my_ms.empty and my_monday.empty:
        continue

    lines.append(f"## {name}")
    lines.append("")

    if not my_rocks.empty:
        lines.append(f"{name}'s rocks (quarterly priorities):")
        for _, r in my_rocks.sort_values("due_date").iterrows():
            lvl = "" if str(r["level"]) == "USER" else f" [{str(r['level']).lower()} rock]"
            lines.append(
                f"- {r['title']}{lvl} — {status_word(r['status'])}, "
                f"due {fdate(r['due_date'])}{overdue_tag(r['due_date'])}."
            )
        lines.append("")

    if not my_ms.empty:
        lines.append(f"{name}'s milestones:")
        rock_owner = dict(zip(rocks["title"], rocks["owner_name"]))
        for _, m in my_ms.sort_values("due_date").iterrows():
            ro = rock_owner.get(m["rock_title"])
            ctx = f"part of the rock \"{m['rock_title']}\""
            if ro and ro != name:
                ctx += f" owned by {ro}"
            lines.append(
                f"- {m['milestone_title']} — due {fdate(m['due_date'])}"
                f"{overdue_tag(m['due_date'])} ({ctx})."
            )
        lines.append("")

    if not my_monday.empty:
        lines.append(f"{name}'s Monday.com tasks:")
        for _, t in my_monday.sort_values("board_name").iterrows():
            role = f" ({t['role']})" if pd.notna(t["role"]) else ""
            status = f" — {t['status']}" if pd.notna(t["status"]) else ""
            due = f", due {t['due_date']}" if pd.notna(t["due_date"]) else ""
            lines.append(
                f"- {t['item_name']}{role}{status}{due} "
                f"(board: {t['board_name']})."
            )
        lines.append("")

# Completed work, briefly, so "what did X finish" is answerable
done_rocks = rocks[rocks["completed"] == True]  # noqa: E712
if not done_rocks.empty:
    lines.append("## Completed rocks")
    lines.append("")
    for _, r in done_rocks.iterrows():
        lines.append(f"- {r['owner_name']}: {r['title']} (completed).")
    lines.append("")

EMPLOYEE_DIR.mkdir(parents=True, exist_ok=True)

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

people = len([n for n in names])
print(f"Wrote {OUTPUT}: {people} people, "
      f"{len(rocks)} rocks, {len(milestones)} milestones, "
      f"{len(monday_tasks)} Monday.com task rows, "
      f"{len(monday_columns)} Monday.com column-value rows (Leadership excluded)")
