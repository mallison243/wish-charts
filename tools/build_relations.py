# tools/build_relations.py  (expects headers: WISH, Date, Same As)
import csv, json, re
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

CSV_IN = Path(__file__).resolve().parents[1] / "charts.csv"
RELATIONS_OUT = Path(__file__).resolve().parents[1] / "relations.json"

DATE_FORMATS = ["%d-%b-%y", "%m/%d/%Y", "%Y-%m-%d"]
DIGITS = re.compile(r"^\d+$")

def parse_date(s):
    s = (s or "").strip()
    for fmt in DATE_FORMATS:
        try: return datetime.strptime(s, fmt)
        except: pass
    return None

def is_wish(s):
    return bool(DIGITS.match(s)) and 5 <= len(s) <= 7 and not s.startswith("0")

def norm_digits(s): return re.sub(r"[^0-9]", "", (s or ""))

rows = []
with open(CSV_IN, "r", newline="", encoding="utf-8-sig") as f:
    r = csv.DictReader(f)
    needed = {"WISH","Date","Same As"}
    missing = [c for c in needed if c not in r.fieldnames]
    if missing:
        raise SystemExit(f"charts.csv missing required header(s): {missing}. Present: {r.fieldnames}")

    for row in r:
        wish = norm_digits(row["WISH"])
        if not is_wish(wish): 
            # skip rows without a valid WISH id
            continue
        date = parse_date(row["Date"])
        same_tokens = []
        for tok in re.split(r"[,\s;]+", row.get("Same As","")):
            d = norm_digits(tok)
            if is_wish(d) and d != wish:
                same_tokens.append(d)
        rows.append({"wish": wish, "date": date, "same_as": same_tokens})

# Build graph
G = defaultdict(set)
for r in rows:
    w = r["wish"]
    G[w]  # ensure node
    for o in r["same_as"]:
        G[w].add(o); G[o].add(w)

# Components
visited, comps = set(), []
for n in G:
    if n in visited: continue
    comp, dq = [], deque([n])
    visited.add(n)
    while dq:
        u = dq.popleft(); comp.append(u)
        for v in G[u]:
            if v not in visited:
                visited.add(v); dq.append(v)
    comps.append(comp)

# Index rows + dates
by_wish = {}
for r in rows:
    # keep the most recent date if multiple rows mention same WISH
    d = r["date"]
    if r["wish"] not in by_wish or ((d or datetime.min) > (by_wish[r["wish"]] or datetime.min)):
        by_wish[r["wish"]] = d

def rdate(w): return by_wish.get(w)

families, wish_to_family = [], {}
for i, comp in enumerate(comps):
    comp_sorted = sorted(comp, key=lambda w: (rdate(w) is None, rdate(w) or datetime.min))
    latest = max(comp, key=lambda w: (rdate(w) or datetime.min))
    for w in comp: wish_to_family[w] = i
    families.append({"members": comp_sorted, "latest": latest})

dates = {w: (rdate(w).strftime("%Y-%m-%d") if rdate(w) else None) for w in by_wish}

json.dump({"families": families, "wish_to_family": wish_to_family, "dates": dates},
          open(RELATIONS_OUT, "w", encoding="utf-8"), indent=2)
print(f"Wrote {RELATIONS_OUT} with {len(families)} families and {len(by_wish)} charts")
