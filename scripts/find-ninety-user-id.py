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
    "content-type": "application/json"
}

owner_lookup = {}

for page in range(50):

    body = {
        "pageSize": 100,
        "pageIndex": page
    }

    response = requests.post(
        "https://api.public.ninety.io/v1/scorecard/kpis/query",
        headers=headers,
        json=body
    )

    data = response.json()

    items = data.get("items", [])

    if not items:
        break

    for item in items:

        uid = item.get("userId")
        uname = item.get("userFullName")

        if uid and uname:
            owner_lookup[uid] = uname

print(f"Found {len(owner_lookup)} users\n")

for uid, uname in sorted(owner_lookup.items()):
    print(uid, "->", uname)

users_df = pd.DataFrame(
    owner_lookup.items(),
    columns=["owner_id", "owner_name"]
)

# Write only the "Users" tab -- if ID_Decoder.xlsx already exists (e.g. it
# already has a "Departments" tab from build-ninety-team-lookup.py), append/replace
# just this sheet instead of wiping the whole workbook.
mode = "a" if os.path.exists(DECODER_FILE) else "w"
kwargs = {"if_sheet_exists": "replace"} if mode == "a" else {}

with pd.ExcelWriter(DECODER_FILE, engine="openpyxl", mode=mode, **kwargs) as writer:
    users_df.to_excel(writer, sheet_name="Users", index=False)

print(f"\nSaved to {DECODER_FILE} (sheet: Users)")