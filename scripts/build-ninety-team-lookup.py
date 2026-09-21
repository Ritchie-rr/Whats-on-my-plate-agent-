import os
import requests
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
KEY_FILE = ROOT / "keys" / "ninety_key"

DECODER_FILE = DATA_DIR / "ID_Decoder.xlsx"

api_token = KEY_FILE.read_text().strip()

headers = {
    "Authorization": f"Bearer {api_token}",
    "accept": "application/json",
    "content-type": "application/json",
}

BASE = "https://api.public.ninety.io/v1"

team_lookup = {}    # team_id -> team_name (department name)
team_members = {}   # team_id -> set of owner names seen on that team's measurables

# =========================
# 1. Teams the API token's user directly belongs to
#    GET /v1/teams -> [{ "id": "...", "name": "..." }, ...]
# =========================

resp = requests.get(f"{BASE}/teams", headers=headers)

if resp.status_code == 200:
    for team in resp.json():
        tid = team.get("id")
        tname = team.get("name")
        if tid and tname:
            team_lookup[tid] = tname
else:
    print(f"GET /teams -> {resp.status_code}: {resp.text[:300]}")

# =========================
# 2. Teams referenced on Measurables
#    POST /v1/scorecard/kpis/query -> each item has a "teams": [{id, name}]
#    array plus userId/userFullName. This catches departments beyond the
#    ones the token's own user belongs to, and tells us who's on each one.
# =========================

for page in range(50):

    body = {"pageSize": 100, "pageIndex": page}

    resp = requests.post(
        f"{BASE}/scorecard/kpis/query",
        headers=headers,
        json=body
    )

    data = resp.json()
    items = data.get("items", [])

    if not items:
        break

    for item in items:

        owner_name = item.get("userFullName")

        for team in item.get("teams", []):

            tid = team.get("id")
            tname = team.get("name")

            if tid and tname:
                team_lookup.setdefault(tid, tname)

                if owner_name:
                    team_members.setdefault(tid, set()).add(owner_name)

print(f"Found {len(team_lookup)} teams (departments)\n")

for tid, tname in sorted(team_lookup.items(), key=lambda x: x[1]):
    members = ", ".join(sorted(team_members.get(tid, []))) or "(no members seen via measurables)"
    print(f"{tname}  ->  {tid}")
    print(f"    members seen: {members}\n")

# =========================
# 3. Cross-check against rocks/milestones team_ids so nothing is missed
#    (rocks/milestones carry teamId even when no measurable references it)
# =========================

rock_team_ids = set()

resp = requests.post(
    f"{BASE}/rocks/query",
    headers=headers,
    json={"sortField": "dueDate", "sortDirection": "DESC", "pageSize": 100, "pageIndex": 0}
)

rocks_data = resp.json()

for team_id, rocks in rocks_data.items():
    rock_team_ids.add(team_id)
    for rock in rocks:
        if rock.get("teamId"):
            rock_team_ids.add(rock.get("teamId"))
        for ms in rock.get("milestones", []):
            if ms.get("teamId"):
                rock_team_ids.add(ms.get("teamId"))

unresolved = sorted(t for t in rock_team_ids if t and t not in team_lookup)

# =========================
# 4. Save: Departments + Unresolved (team_ids seen but not yet named)
# =========================

teams_df = pd.DataFrame(
    [
        (tid, tname, ", ".join(sorted(team_members.get(tid, []))))
        for tid, tname in team_lookup.items()
    ],
    columns=["team_id", "department_name", "members_seen"]
).sort_values("department_name")

unresolved_df = pd.DataFrame({"team_id": unresolved})


def write_sheet(sheet_name, df):
    """Write one sheet into the shared ID_Decoder.xlsx without wiping
    other tabs (e.g. the "Users" tab written by find-ninety-user-id.py)."""
    mode = "a" if os.path.exists(DECODER_FILE) else "w"
    kwargs = {"if_sheet_exists": "replace"} if mode == "a" else {}
    with pd.ExcelWriter(DECODER_FILE, engine="openpyxl", mode=mode, **kwargs) as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)


write_sheet("Departments", teams_df)
write_sheet("Unresolved", unresolved_df)

print(f"\nSaved {len(teams_df)} departments to {DECODER_FILE} (sheet: Departments)")

if unresolved:
    print(
        f"{len(unresolved)} team_id(s) appear on rocks/milestones but have no "
        f"name yet -- see the 'Unresolved' sheet in {DECODER_FILE} and name "
        f"them manually: {unresolved}"
    )
