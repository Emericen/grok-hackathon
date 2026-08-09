# TWIN.md — make an anonymized twin of the case in this directory

You are an agent in a coding harness. Build a twin of this case: **same documents, same
numbers, only the identities changed.** Amounts stay frozen so every trap transfers
exactly (production re-derives amounts under constraints; this is the fast dial).

```bash
[ -d twin-pipeline ] || git clone https://github.com/Emericen/grok-hackathon twin-pipeline
```

## 1. Map the identities

Write `dirty/substitution_map.json` (mkdir dirty; add `dirty/` to .gitignore):

```json
{"entities": [{"real": "Danny Kowalski", "fake": "...", "kind": "person"}, ...],
 "filenames": {"<old name>": "<new name>"}}
```

Map ONLY identities: people, company names, addresses, bank/processor names, account
numbers, EIN/SSN fragments, emails, phone numbers, and any filename containing a name.
Numbers, dates, and amounts DO NOT change. Same real entity → same fake, everywhere.

## 2. Build the twin

Create the twin as a SIBLING of the case directory, named like a fresh intake: `../<new-company>-intake/` containing `task.json` + `filesystem/`. For every file in the case — EXCEPT `output/`, `dirty/`, and `twin-pipeline/` (the twin's initial state contains only the client's documents, none of your own work):

- **No mapped string in it** (most receipts, generic vendor slips): copy unchanged.
- **Text-like** (txt/md/csv): rewrite with the swaps applied.
- **.xlsx**: use `openpyxl` — load, walk cells, replace mapped strings in string cells,
  save. **Never touch formulas or numeric cells** (a client's broken formula is a trap;
  keep it broken):
  ```python
  import openpyxl
  wb = openpyxl.load_workbook(src)          # keeps formulas
  for ws in wb.worksheets:
      for row in ws.iter_rows():
          for c in row:
              if isinstance(c.value, str):
                  for real, fake in swaps.items():
                      c.value = c.value.replace(real, fake)
  wb.save(dst)
  ```
- **.docx**: it's a zip — replace strings inside `word/document.xml`, rezip.
- **Scanned PDFs / photos that contain mapped identities** (IRS letters, bank
  statements, 1099s, insurance): re-render with PIL, then degrade so it still looks
  scanned. Draw title + label/value lines with the SAME numbers, swapped names:
  ```python
  from PIL import Image, ImageDraw, ImageFont
  font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
  img = Image.new("RGB", (1700, 2200), "#f7f5ef"); d = ImageDraw.Draw(img)
  d.text((120, 100), title, fill="#111", font=font)   # then one d.text per line
  ```
  Then degrade with `twin-pipeline/tools/scanify.py`'s profiles (flatbed: rotate ~0.6°
  + noise + mild blur; phone: rotate ~2°, warm overlay, blur). Save jpg/pdf with the
  mapped filename. Read your render back to confirm it's legible.

Write a small python script for the bulk work instead of editing file-by-file.

## 3. task.json

Write `../<new-company>-intake/task.json`: `{"task": "...", "verifiers": [...]}` — the engagement
task phrased with the fake names, and one verifier per trap the expert's corrections
caught in this conversation (`{"id", "type": "output|negative", "criteria"}`, criteria
cite the exact frozen numbers, fake names only).

## 4. Gate (mandatory)

```bash
python3 twin-pipeline/scripts/scan.py dirty/substitution_map.json ../<new-company>-intake
```

MUST print `clean`. If it reports a leak, fix that file and rescan — never hand over
an unscanned twin. Then tell the user: files copied vs re-made, entities swapped,
scan verdict, and the twin's path (it should sit right next to the original case folder).
