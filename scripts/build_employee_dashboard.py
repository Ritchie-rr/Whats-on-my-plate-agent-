"""
Build the Employee Dashboard -- a copy of Master_Ninety_Dashboard.xlsx with
any Leadership-department rocks, milestones, and issues stripped out, since
that content can be confidential. Everyone else's rows pass through as-is.

Reads from the Master-data folder, writes to the Employee-data folder --
both siblings of this Code folder -- so each type of data lives in its own
place with its own (eventual) SharePoint permissions.

Matches on department name rather than a hardcoded team_id, so it still
works if the "** Leadership Team" name in Ninety gets cleaned up later.

Run after 1-Ninety-dashboard.py:
    python build_employee_dashboard.py
"""

import re
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER_DIR = ROOT.parent / "Master-data"
EMPLOYEE_DIR = ROOT.parent / "Employee-data"

SOURCE = MASTER_DIR / "Master_Ninety_Dashboard.xlsx"
OUTPUT = EMPLOYEE_DIR / "Employee_Dashboard.xlsx"


def is_leadership(department_name):
    if not isinstance(department_name, str):
        return False
    normalized = re.sub(r"[^a-z]", "", department_name.lower())
    return "leadership" in normalized


rocks = pd.read_excel(SOURCE, sheet_name="Rocks")
milestones = pd.read_excel(SOURCE, sheet_name="Milestones")
issues = pd.read_excel(SOURCE, sheet_name="Issues")
users = pd.read_excel(SOURCE, sheet_name="Users")

rocks_before = len(rocks)
milestones_before = len(milestones)
issues_before = len(issues)

rocks = rocks[~rocks["department"].apply(is_leadership)]
milestones = milestones[~milestones["department"].apply(is_leadership)]
issues = issues[~issues["department"].apply(is_leadership)]

EMPLOYEE_DIR.mkdir(parents=True, exist_ok=True)

with pd.ExcelWriter(OUTPUT, engine="openpyxl") as writer:
    rocks.to_excel(writer, sheet_name="Rocks", index=False)
    milestones.to_excel(writer, sheet_name="Milestones", index=False)
    issues.to_excel(writer, sheet_name="Issues", index=False)
    users.to_excel(writer, sheet_name="Users", index=False)

print(f"Wrote {OUTPUT}")
print(f"Rocks: {rocks_before} -> {len(rocks)} "
      f"(removed {rocks_before - len(rocks)} Leadership rocks)")
print(f"Milestones: {milestones_before} -> {len(milestones)} "
      f"(removed {milestones_before - len(milestones)} Leadership milestones)")
print(f"Issues: {issues_before} -> {len(issues)} "
      f"(removed {issues_before - len(issues)} Leadership issues)")
