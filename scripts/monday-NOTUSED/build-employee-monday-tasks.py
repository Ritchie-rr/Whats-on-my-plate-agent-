"""
Build the Employee-safe view of Monday.com tasks.

Reads both sheets of Master-data/Monday_Tasks.xlsx (written by
pull-monday-tasks.py) -- "Tasks" (per-person) and "Item_Columns" (every
column value on every item) -- and drops every row tagged
category == "leadership" (currently the ROCKS | 2025 and
2026 STEWARDSHIP TRACKER boards) from both, since that can be
confidential. Everything else ("regular") passes through unchanged into
Employee-data/Monday_Tasks.xlsx, keeping the same two-sheet shape so the
employee knowledge-file builder can generate the same auto status summary
for whatever non-confidential boards have status-style columns.

Run after pull-monday-tasks.py:
    python build-employee-monday-tasks.py
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # monday/ -> scripts/ -> Code/
MASTER_DIR = ROOT.parent / "Master-data"
EMPLOYEE_DIR = ROOT.parent / "Employee-data"

SOURCE = MASTER_DIR / "Monday_Tasks.xlsx"
OUTPUT = EMPLOYEE_DIR / "Monday_Tasks.xlsx"

tasks = pd.read_excel(SOURCE, sheet_name="Tasks")
try:
    columns = pd.read_excel(SOURCE, sheet_name="Item_Columns")
except ValueError:
    # Older Monday_Tasks.xlsx from before the Item_Columns sheet existed.
    print(f"WARNING: {SOURCE} has no 'Item_Columns' sheet yet -- re-run "
          "pull-monday-tasks.py first. Continuing with an empty one.")
    columns = pd.DataFrame(columns=[
        "board_name", "category", "group_name", "item_id", "item_name",
        "column_title", "column_type", "column_text"
    ])

tasks_before, columns_before = len(tasks), len(columns)
tasks = tasks[tasks["category"] != "leadership"]
columns = columns[columns["category"] != "leadership"]

EMPLOYEE_DIR.mkdir(parents=True, exist_ok=True)
with pd.ExcelWriter(OUTPUT, engine="openpyxl") as writer:
    tasks.to_excel(writer, sheet_name="Tasks", index=False)
    columns.to_excel(writer, sheet_name="Item_Columns", index=False)

print(f"Wrote {OUTPUT}")
print(f"Task rows: {tasks_before} -> {len(tasks)} (removed {tasks_before - len(tasks)} leadership rows)")
print(f"Column-value rows: {columns_before} -> {len(columns)} (removed {columns_before - len(columns)} leadership rows)")
