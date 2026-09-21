import requests
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MASTER_DIR = ROOT.parent / "Master-data"
KEY_FILE = ROOT / "keys" / "ninety_key"

# =========================
# AUTH
# =========================

api_token = KEY_FILE.read_text().strip()

headers = {
    "Authorization": f"Bearer {api_token}"
}

# =========================
# GET ROCKS
# =========================

body = {
    "sortField": "dueDate",
    "sortDirection": "DESC",
    "pageSize": 100,
    "pageIndex": 0
}

response = requests.post(
    "https://api.public.ninety.io/v1/rocks/query",
    headers=headers,
    json=body
)

data = response.json()

# =========================
# BUILD ROCKS + MILESTONES
# =========================

rock_rows = []
milestone_rows = []

for team_id, rocks in data.items():

    for rock in rocks:

        rock_rows.append({
            "title": rock.get("title"),
            "status": rock.get("statusCode"),
            "quarter": rock.get("quarter"),
            "due_date": rock.get("dueDate"),
            "level": rock.get("levelCode"),
            "owner": rock.get("userId"),
            "team_id": rock.get("teamId"),
            "completed": rock.get("completed")
        })

        for ms in rock.get("milestones", []):

            milestone_rows.append({
                "rock_title": rock.get("title"),
                "milestone_title": ms.get("title"),
                "owner": ms.get("ownedByUserId"),
                "due_date": ms.get("dueDate"),
                "team_id": ms.get("teamId"),
                "completed": ms.get("isDone")
            })

# =========================
# GET ISSUES
# =========================

issue_rows = []

for page in range(50):

    issues_body = {
        "sortField": "createdDate",
        "sortDirection": "DESC",
        "pageSize": 100,
        "pageIndex": page
    }

    issues_response = requests.post(
        "https://api.public.ninety.io/v1/issues/query",
        headers=headers,
        json=issues_body
    )

    issues_data = issues_response.json()
    issues_items = issues_data.get("items", [])

    if not issues_items:
        break

    for issue in issues_items:

        issue_rows.append({
            "title": issue.get("title"),
            "description": issue.get("description"),
            "priority": issue.get("priority"),
            "interval": issue.get("intervalCode"),
            "owner": issue.get("userId"),
            "team_id": issue.get("teamId"),
            "created_by": issue.get("createdBy"),
            "created_date": issue.get("createdDate"),
            "completed": issue.get("completed"),
            "completed_date": issue.get("completedDate"),
            "archived": issue.get("archived")
        })

# =========================
# DATAFRAMES
# =========================

# Explicit columns so the merges below don't KeyError if Ninety returns zero items
rocks_df = pd.DataFrame(rock_rows, columns=[
    "title", "status", "quarter", "due_date", "level", "owner", "team_id", "completed"
])

milestones_df = pd.DataFrame(milestone_rows, columns=[
    "rock_title", "milestone_title", "owner", "due_date", "team_id", "completed"
])

issues_df = pd.DataFrame(issue_rows, columns=[
    "title", "description", "priority", "interval", "owner", "team_id",
    "created_by", "created_date", "completed", "completed_date", "archived"
])

# =========================
# OWNER + DEPARTMENT LOOKUP
# (both tabs live in the shared data/ID_Decoder.xlsx)
# =========================

owners = pd.read_excel(
    DATA_DIR / "ID_Decoder.xlsx",
    sheet_name="Users"
)

try:
    departments = pd.read_excel(
        DATA_DIR / "ID_Decoder.xlsx",
        sheet_name="Departments"
    )[["team_id", "department_name"]].rename(
        columns={"department_name": "department"}
    )
except ValueError:
    print(
        "WARNING: 'Departments' sheet not found in ID_Decoder.xlsx yet -- "
        "run build-ninety-team-lookup.py first. Continuing without a department column."
    )
    departments = pd.DataFrame(columns=["team_id", "department"])


rocks_df = rocks_df.merge(
    owners,
    left_on="owner",
    right_on="owner_id",
    how="left"
).merge(
    departments,
    on="team_id",
    how="left"
)

milestones_df = milestones_df.merge(
    owners,
    left_on="owner",
    right_on="owner_id",
    how="left"
).merge(
    departments,
    on="team_id",
    how="left"
)

issues_df = issues_df.merge(
    owners,
    left_on="owner",
    right_on="owner_id",
    how="left"
).merge(
    departments,
    on="team_id",
    how="left"
)

# =========================
# SAVE EVERYTHING
# (this is the MASTER file -- includes Leadership rocks/milestones/issues.
# Lives in the Master-data folder, a sibling of this Code folder.
# See build_employee_dashboard.py for the Leadership-scrubbed version.)
# =========================

MASTER_DIR.mkdir(parents=True, exist_ok=True)

with pd.ExcelWriter(
    MASTER_DIR / "Master_Ninety_Dashboard.xlsx",
    engine="openpyxl"
) as writer:

    rocks_df.to_excel(
        writer,
        sheet_name="Rocks",
        index=False
    )

    milestones_df.to_excel(
        writer,
        sheet_name="Milestones",
        index=False
    )

    issues_df.to_excel(
        writer,
        sheet_name="Issues",
        index=False
    )

    owners.to_excel(
        writer,
        sheet_name="Users",
        index=False
    )

print(f"Done! Wrote {MASTER_DIR / 'Master_Ninety_Dashboard.xlsx'}")

print("\nRock Count:", len(rocks_df))
print("Milestone Count:", len(milestones_df))
print("Issue Count:", len(issues_df))

print("\nSample Rocks:")
print(
    rocks_df[
        ["title", "owner_name", "status", "level", "department"]
    ].head()
)

print("\nSample Milestones:")
print(
    milestones_df[
        ["rock_title", "milestone_title", "owner_name", "completed", "department"]
    ].head()
)

print("\nSample Issues:")
print(
    issues_df[
        ["title", "owner_name", "priority", "completed", "department"]
    ].head()
)
