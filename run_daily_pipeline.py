"""
Daily pipeline: pull Ninety -> build dashboards -> build knowledge docs
(including the stewardship knowledge file). This is the ONLY script you
need to run. See SETUP_README.md for full setup instructions.

Monday.com is no longer pulled by this pipeline -- Monday data is now
read live through an MCP connector instead of a daily xlsx snapshot.
2-build_knowledge_file.py still reads Master-data/Monday_Tasks.xlsx if
one happens to be present (from a manual run of pull-monday-tasks.py),
but nothing here creates or refreshes that file anymore.

Folder layout (three siblings under the SharePoint-synced project root):
    Code/                                       this folder -- run this script
        keys/ninety_key                         Ninety API token
        keys/pipeline.log                       every run logs here
        run_daily_pipeline.py                   this file
        scripts/                                all worker .py files
        scripts/monday/                         Monday.com scripts (manual use only, not run daily)
        data/ID_Decoder.xlsx                    shared ID lookup (Users/Departments)
    Master-data/                                Master (includes Leadership)
        Master_Ninety_Dashboard.xlsx
        Whats_On_My_Plate_Knowledge.md
        Whats_On_My_Plate_Stewardship_Knowledge.md
    Employee-data/                              Employee (Leadership excluded)
        Employee_Dashboard.xlsx
        Whats_On_My_Plate_Employee_Knowledge.md
        Whats_On_My_Plate_Stewardship_Knowledge.md

Because Master-data/ and Employee-data/ are themselves folders inside the
SharePoint-synced library, writing into them IS publishing -- there's no
separate copy-to-SharePoint step anymore. Point each Copilot agent's
knowledge source at the matching folder.
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ============ CONFIG ============

PULL_SCRIPT = "scripts/1-Ninety-dashboard.py"
EMPLOYEE_SCRIPT = "scripts/build_employee_dashboard.py"
BUILD_SCRIPT = "scripts/2-build_knowledge_file.py"
EMPLOYEE_BUILD_SCRIPT = "scripts/3-build_employee_knowledge_file.py"
STEWARDSHIP_BUILD_SCRIPT = "scripts/4-build_stewardship_knowledge_file.py"

USER_LOOKUP_SCRIPT = "scripts/find-ninety-user-id.py"
TEAM_LOOKUP_SCRIPT = "scripts/build-ninety-team-lookup.py"
ID_DECODER_FILE = "data/ID_Decoder.xlsx"

# Monday.com is no longer pulled here -- see module docstring above.
# scripts/monday/pull-monday-tasks.py and build-employee-monday-tasks.py
# still exist for manual/ad-hoc use, just not called from this pipeline.

# ================================

HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent
MASTER_DIR = PROJECT_ROOT / "Master-data"
EMPLOYEE_DIR = PROJECT_ROOT / "Employee-data"

MASTER_KNOWLEDGE_FILE = MASTER_DIR / "Whats_On_My_Plate_Knowledge.md"
EMPLOYEE_KNOWLEDGE_FILE = EMPLOYEE_DIR / "Whats_On_My_Plate_Employee_Knowledge.md"
STEWARDSHIP_KNOWLEDGE_FILE = MASTER_DIR / "Whats_On_My_Plate_Stewardship_Knowledge.md"
STEWARDSHIP_EMPLOYEE_FILE = EMPLOYEE_DIR / "Whats_On_My_Plate_Stewardship_Knowledge.md"

KEYS_DIR = HERE / "keys"
KEYS_DIR.mkdir(exist_ok=True)  # so a fresh checkout can log even before keys are added
LOG = KEYS_DIR / "pipeline.log"


def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def preflight():
    problems = []
    for label, fname in [("PULL_SCRIPT", PULL_SCRIPT),
                         ("EMPLOYEE_SCRIPT", EMPLOYEE_SCRIPT),
                         ("BUILD_SCRIPT", BUILD_SCRIPT),
                         ("EMPLOYEE_BUILD_SCRIPT", EMPLOYEE_BUILD_SCRIPT),
                         ("STEWARDSHIP_BUILD_SCRIPT", STEWARDSHIP_BUILD_SCRIPT),
                         ("USER_LOOKUP_SCRIPT", USER_LOOKUP_SCRIPT),
                         ("TEAM_LOOKUP_SCRIPT", TEAM_LOOKUP_SCRIPT),
                         ("Ninety API key file", "keys/ninety_key")]:
        if not (HERE / fname).exists():
            problems.append(f"  - {label}: '{fname}' not found in {HERE}")
    if not (HERE / "data").exists():
        problems.append(f"  - 'data' folder not found in {HERE}")
    if not MASTER_DIR.exists():
        problems.append(f"  - Master-data folder not found: {MASTER_DIR}")
    if not EMPLOYEE_DIR.exists():
        problems.append(f"  - Employee-data folder not found: {EMPLOYEE_DIR}")

    if problems:
        log("PRE-FLIGHT FAILED — fix the CONFIG block at the top, or the folder layout:")
        for p in problems:
            log(p)
        py_files = sorted(str(p.relative_to(HERE)) for p in HERE.rglob("*.py"))
        log(f"Python files actually found under {HERE}: {py_files}")
        sys.exit(1)
    log("Pre-flight OK: all scripts, key, and folders found.")


def run_step(name, script):
    log(f"START {name} ({script})")
    result = subprocess.run(
        [sys.executable, str(HERE / script)],
        capture_output=True, text=True, cwd=HERE,
    )
    if result.stdout.strip():
        log(result.stdout.strip())
    if result.returncode != 0:
        log(f"FAILED {name}: {result.stderr.strip()[:500]}")
        sys.exit(1)
    log(f"DONE {name}")


def ensure_id_decoder():
    """First-time setup: build data/ID_Decoder.xlsx if it doesn't exist yet,
    so a fresh checkout of this project can run end-to-end from just this
    one script. Once it exists, rebuild it manually (via the two lookup
    scripts) only when people or teams actually change -- not every day."""
    if (HERE / ID_DECODER_FILE).exists():
        return
    log(f"{ID_DECODER_FILE} not found -- building it now (first-time setup).")
    run_step("Build user lookup", USER_LOOKUP_SCRIPT)
    run_step("Build team lookup", TEAM_LOOKUP_SCRIPT)


def main():
    preflight()
    ensure_id_decoder()
    run_step("Ninety pull", PULL_SCRIPT)
    run_step("Build employee dashboard", EMPLOYEE_SCRIPT)
    run_step("Build knowledge doc", BUILD_SCRIPT)
    run_step("Build employee knowledge doc", EMPLOYEE_BUILD_SCRIPT)
    run_step("Build stewardship knowledge doc", STEWARDSHIP_BUILD_SCRIPT)

    if not MASTER_KNOWLEDGE_FILE.exists():
        log(f"FAILED: {BUILD_SCRIPT} ran but {MASTER_KNOWLEDGE_FILE} is missing.")
        sys.exit(1)
    log(f"Master knowledge file is current: {MASTER_KNOWLEDGE_FILE}")

    if not EMPLOYEE_KNOWLEDGE_FILE.exists():
        log(f"FAILED: {EMPLOYEE_BUILD_SCRIPT} ran but {EMPLOYEE_KNOWLEDGE_FILE} is missing.")
        sys.exit(1)
    log(f"Employee knowledge file is current: {EMPLOYEE_KNOWLEDGE_FILE}")

    if not STEWARDSHIP_KNOWLEDGE_FILE.exists():
        log(f"FAILED: {STEWARDSHIP_BUILD_SCRIPT} ran but {STEWARDSHIP_KNOWLEDGE_FILE} is missing.")
        sys.exit(1)
    if not STEWARDSHIP_EMPLOYEE_FILE.exists():
        log(f"FAILED: {STEWARDSHIP_BUILD_SCRIPT} ran but {STEWARDSHIP_EMPLOYEE_FILE} is missing.")
        sys.exit(1)
    log(f"Stewardship knowledge file is current in both Master-data and Employee-data.")

    log("Pipeline complete. All files were written straight into the "
        "SharePoint-synced Master-data/Employee-data folders -- OneDrive "
        "will sync them from here.")


if __name__ == "__main__":
    main()
