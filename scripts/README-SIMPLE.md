# Stewardship Knowledge Script — Quick Start

**4-build_stewardship_knowledge_file.py** reads every client's Cover page
(meeting date, attendees) and Timeline tab (upcoming milestones) out of
Stewardships - Documents, and writes
`Whats_On_My_Plate_Stewardship_Knowledge.md` into BOTH this project's
Master-data AND Employee-data folders (identical file in both — see
README-DETAILED.md for why), for the Copilot agent(s) to use.

Requires Python 3 and the `openpyxl` package.

Want more detail on how it finds the files, or what to do if something
looks off? See **README-DETAILED.md** in this same folder.

## Without an IDE (Command Prompt / Terminal)

1. Open Command Prompt (search "cmd" in the Start menu).
2. Navigate to this folder (in File Explorer, click the address bar on
   this `scripts` folder, copy it, then paste it into `cd "..."` below):
   ```
   cd "<paste the folder path here>"
   ```
3. (First time only) install the one dependency:
   ```
   pip install openpyxl
   ```
4. Run it:
   ```
   python 4-build_stewardship_knowledge_file.py
   ```

## With an IDE (e.g. VS Code, PyCharm)

1. Open this `scripts` folder in the IDE.
2. Open `4-build_stewardship_knowledge_file.py`.
3. Click the "Run" button (or press the IDE's run shortcut, e.g. the ▶
   in VS Code's top-right corner).
4. Check the Output/Terminal panel in the IDE for the results.

## Notes

- Only reads files in Stewardships - Documents — never edits anything
  there.
- Works no matter which computer or account runs it, as long as OneDrive
  is signed in and syncing the Stewardships site.
- Not part of the daily pipeline yet — run it manually whenever you want
  a fresh copy of the knowledge file.
