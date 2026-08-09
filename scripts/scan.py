#!/usr/bin/env python3
"""scan.py - the packaging gate. Exits nonzero if any real entity survives in a twin.

USAGE
    python scan.py dirty/substitution_map.json worlds/my-twin

Scans every file's text content AND every filename under the twin dir (task.json and
manifest.json included) for every "real" string in the substitution map (length >= 4,
and only where fake differs from real). Any hit: prints it and exits 1 - nothing with
a hit may ship. This gate is code on purpose: an instruction a model might skip is not
a privacy guarantee.
"""

import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sub_map = json.loads(Path(sys.argv[1]).read_text())
    twin = Path(sys.argv[2])
    reals = [e["real"] for e in sub_map["entities"]
             if len(e["real"]) >= 4 and e["real"] != e.get("fake")]
    hits = []
    targets = [twin] if twin.is_file() else twin.rglob("*")
    for p in targets:
        if not p.is_file():
            continue
        content = p.read_bytes().decode("utf-8", errors="ignore")
        for real in reals:
            if real in content or real in p.name:
                hits.append((str(p.relative_to(twin)), real))
    if hits:
        for path, real in hits:
            print(f"LEAK: '{real}' in {path}")
        sys.exit(f"FAILED - {len(hits)} real entities survived; do not ship this twin")
    print(f"clean - {len(reals)} entities scanned, zero survivors in {twin}")


if __name__ == "__main__":
    main()
