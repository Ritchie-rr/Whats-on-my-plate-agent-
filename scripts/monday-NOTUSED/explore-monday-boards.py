"""
Exploratory probe for the Monday.com API -- NOT part of the daily pipeline.

Purpose: we don't yet know the real shape of the active Monday boards (how
many there are, what columns/groups they use, what a "task" looks like).
This script just asks Monday and prints what comes back, so we can design
the real pull script (and the ID_Decoder person-matching approach) based on
actual data instead of guesses.

Monday's API is GraphQL, not REST: everything is a single POST to
https://api.monday.com/v2 with a "query" string in the JSON body, and the
raw token (no "Bearer " prefix) in the Authorization header.

Run manually:
    python explore-monday-boards.py
"""

import json
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # monday/ -> scripts/ -> Code/
KEY_FILE = ROOT / "keys" / "monday_key"

API_URL = "https://api.monday.com/v2"

api_token = KEY_FILE.read_text().strip()

headers = {
    "Authorization": api_token,
    "Content-Type": "application/json",
}


def run_query(query, variables=None):
    body = {"query": query}
    if variables:
        body["variables"] = variables
    resp = requests.post(API_URL, headers=headers, json=body)
    data = resp.json()
    if "errors" in data:
        print(f"  GraphQL errors: {json.dumps(data['errors'], indent=2)}")
    return data.get("data", {})


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# =========================
# 1. Who is this token as?
# =========================

section("1. Identity check (me)")

me = run_query("{ me { id name email account { id name } } }")
print(json.dumps(me, indent=2))

# =========================
# 2. What boards can this token see?
# =========================

section("2. All visible boards")

boards_data = run_query("""
{
  boards (limit: 100) {
    id
    name
    state
    board_kind
    items_count
    workspace {
      id
      name
    }
  }
}
""")

boards = boards_data.get("boards", [])
print(f"Found {len(boards)} board(s):\n")
for b in boards:
    ws = b.get("workspace") or {}
    print(f"  [{b['id']}] {b['name']}  "
          f"(state={b['state']}, kind={b['board_kind']}, "
          f"items={b['items_count']}, workspace={ws.get('name')})")

if not boards:
    print("No boards returned -- check that monday_key is a valid personal "
          "API token and that this user has access to at least one board.")
    raise SystemExit(0)

# =========================
# 3. For each active board: what columns and groups does it use?
# =========================

section("3. Columns + groups per board")

board_ids = [b["id"] for b in boards if b["state"] == "active"]

structure_data = run_query("""
query ($ids: [ID!]) {
  boards (ids: $ids) {
    id
    name
    columns {
      id
      title
      type
    }
    groups {
      id
      title
    }
  }
}
""", variables={"ids": board_ids})

for b in structure_data.get("boards", []):
    print(f"\n-- {b['name']} (id {b['id']}) --")
    print("  Columns:")
    for c in b["columns"]:
        print(f"    {c['id']:<20} {c['title']:<25} type={c['type']}")
    print("  Groups:")
    for g in b["groups"]:
        print(f"    {g['id']:<20} {g['title']}")

# =========================
# 4. Sample items (first 5 per board) with their column values
# =========================

section("4. Sample items per board (first 5, with column values)")

for bid in board_ids:
    sample = run_query("""
    query ($id: [ID!]) {
      boards (ids: $id) {
        name
        items_page (limit: 5) {
          items {
            id
            name
            group { title }
            column_values {
              id
              text
              type
              column {
                title
              }
            }
          }
        }
      }
    }
    """, variables={"id": [bid]})

    for b in sample.get("boards", []):
        print(f"\n-- Sample items from {b['name']} --")
        items = b.get("items_page", {}).get("items", [])
        if not items:
            print("  (no items on this board)")
        for item in items:
            print(f"  Item: {item['name']}  (group: {item['group']['title']})")
            for cv in item["column_values"]:
                if cv["text"]:
                    print(f"    {cv['column']['title']:<20} ({cv['type']}): {cv['text']}")

print("\nDone. Review the output above -- especially section 3 (columns) and "
      "section 4 (sample items) -- to figure out which column holds the "
      "assignee/owner (usually a 'people' type column) and which board(s) "
      "actually represent account-manager work.")
